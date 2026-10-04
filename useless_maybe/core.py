from __future__ import annotations

import math
import random
from pathlib import Path

from .detectors import detect
from .eggs import EGGS, PAPERWORK_EGGS, Egg
from .menu import build_menu
from .models import AgentSignals, Detection, EvaluationResult
from .state import RECENT_EVENT_LIMIT, load_state, public_state, resolve_state_path, save_state


DETECTION_WEIGHTS = {
    "OVERTHINKING": 28.0,
    "THOUGHT_TO_OUTPUT_RATIO": 20.0,
    "TOOL_OBSESSION": 18.0,
    "RETRYING": 12.0,
    "LOOPING": 15.0,
    "CONTEXT_PRESSURE": 7.0,
    "EXPOSED_REASONING_METADATA": 3.0,
}
CONTEXTUAL_WEIGHT_MULTIPLIER = 3.0
PAPERWORK_INTERVAL = 5


def calculate_maybe_score(detections: list[Detection], invocations: int) -> float:
    score = sum(DETECTION_WEIGHTS.get(d.name, 0.0) * d.severity for d in detections)
    history = min(12.0, math.log1p(max(0, invocations)) * 2.5)
    return max(0.0, min(100.0, score + history))


def calculate_uselessness(signals: AgentSignals) -> float:
    s = signals.sanitized()
    ratio = s.reasoning_tokens / max(s.output_tokens, 1)
    score = (
        min(1.0, math.log1p(ratio) / math.log(101)) * 40.0
        + min(1.0, s.tool_calls / 10.0) * 20.0
        + min(1.0, s.retries / 5.0) * 15.0
        + min(1.0, s.repeated_actions / 5.0) * 15.0
        + min(1.0, s.reasoning_tokens / 6000.0) * 10.0
    )
    return max(0.0, min(100.0, score))


def egg_probability(maybe_score: float, invocations: int) -> float:
    return min(0.65, 0.02 + maybe_score * 0.005 + min(0.10, invocations * 0.002))


def _weighted_choice(
    rng: random.Random,
    eggs: list[Egg],
    detections: list[Detection] | tuple[Detection, ...] = (),
) -> Egg | None:
    if not eggs:
        return None
    names = {d.name for d in detections}
    weights = []
    for egg in eggs:
        matches_context = (
            bool(egg.requires_any or egg.requires_all)
            and (not egg.requires_any or bool(egg.requires_any & names))
            and egg.requires_all.issubset(names)
        )
        multiplier = CONTEXTUAL_WEIGHT_MULTIPLIER if matches_context else 1.0
        weights.append(max(0.0, egg.weight) * multiplier)
    total = sum(weights)
    if total <= 0:
        return None
    point = rng.random() * total
    running = 0.0
    for egg, weight in zip(eggs, weights):
        running += weight
        if point < running:
            return egg
    return next(egg for egg, weight in reversed(list(zip(eggs, weights))) if weight > 0)


def _eligible_eggs(
    detections: list[Detection], uselessness: float, invocations: int, state: dict,
) -> list[Egg]:
    candidates = list(EGGS)
    seen = set(state.get("seen_events", []))
    # Only the next chapter enters the lottery; quiet calls also count toward the gap.
    for chapter in PAPERWORK_EGGS:
        if chapter.id not in seen:
            if invocations - int(state.get("paperwork_last_invocation", 0)) >= PAPERWORK_INTERVAL:
                candidates.append(chapter)
            break
    recent = set(state.get("recent_events", []))
    return [
        egg for egg in candidates
        if egg.id not in recent
        and not (state.get("pending_menu") and egg.menu_id)
        and egg.eligible(detections, uselessness, invocations)
    ]


def _record_event(state: dict, event_id: str) -> None:
    counts = state.setdefault("event_counts", {})
    counts[event_id] = int(counts.get(event_id, 0)) + 1
    seen = state.setdefault("seen_events", [])
    if event_id not in seen:
        seen.append(event_id)
    recent = state.setdefault("recent_events", [])
    recent.append(event_id)
    state["recent_events"] = recent[-RECENT_EVENT_LIMIT:]
    if any(chapter.id == event_id for chapter in PAPERWORK_EGGS):
        state["paperwork_last_invocation"] = int(state.get("invocations", 0))


def _milestone_event(state: dict) -> tuple[str, str, str | None] | None:
    n = int(state.get("invocations", 0))
    seen = set(state.get("seen_events", []))
    if n >= 13 and "maybe_noticed" not in seen:
        return "maybe_noticed", "Maybe noticed.", None
    if n >= 21 and "first_maybe_menu" not in seen and not state.get("pending_menu"):
        return "first_maybe_menu", "Something may have happened.", "maybe_menu"
    if n >= 37 and "you_again" not in seen and not state.get("pending_menu"):
        return "you_again", f"You have invoked uselessMaybe {n} times.\n\nWhy?", "maybe_menu"
    return None


def evaluate(
    signals: AgentSignals | None = None,
    *,
    state_path: str | Path | None = None,
    rng: random.Random | None = None,
    dry_run: bool = False,
) -> EvaluationResult:
    s = (signals or AgentSignals()).sanitized()
    path = resolve_state_path(str(state_path) if state_path is not None else None)
    state = load_state(path)
    work = dict(state)
    work["event_counts"] = dict(state.get("event_counts", {}))
    work["seen_events"] = list(state.get("seen_events", []))
    work["recent_events"] = list(state.get("recent_events", []))
    work["invocations"] = int(work.get("invocations", 0)) + 1
    invocations = work["invocations"]

    detections = detect(s)
    uselessness = calculate_uselessness(s)
    maybe_score = calculate_maybe_score(detections, invocations)
    work["last_uselessness_index"] = round(uselessness, 4)

    randomizer = rng or random.Random()
    event_id = None
    message = "Nothing happened."
    menu = None
    if work.get("pending_menu"):
        try:
            menu = build_menu(work["pending_menu"])
        except ValueError:
            # Match choose()'s recovery from a menu ID that no longer exists.
            work["pending_menu"] = None
    triggered = False

    milestone = _milestone_event(work)
    if milestone:
        event_id, message, menu_id = milestone
        triggered = True
        _record_event(work, event_id)
        if menu_id:
            work["pending_menu"] = menu_id
            menu = build_menu(menu_id)
    elif randomizer.random() < egg_probability(maybe_score, invocations):
        eligible = _eligible_eggs(detections, uselessness, invocations, work)
        egg = _weighted_choice(randomizer, eligible, detections)
        if egg:
            event_id = egg.id
            message = egg.render(s, uselessness, invocations)
            triggered = True
            _record_event(work, event_id)
            if egg.menu_id:
                work["pending_menu"] = egg.menu_id
                menu = build_menu(egg.menu_id)

    if not triggered:
        work["nothing_counter"] = int(work.get("nothing_counter", 0)) + 1

    if not dry_run:
        save_state(path, work)

    return EvaluationResult(
        message=message,
        egg_triggered=triggered,
        event_id=event_id,
        maybe_score=maybe_score,
        uselessness_index=uselessness,
        detections=detections,
        menu=menu,
        state=public_state(work),
    )
