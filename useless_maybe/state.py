from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


STATE_VERSION = 1
RECENT_EVENT_LIMIT = 5


def default_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "invocations": 0,
        "nothing_counter": 0,
        "event_counts": {},
        "seen_events": [],
        "recent_events": [],
        "paperwork_last_invocation": 0,
        "pending_menu": None,
        "last_uselessness_index": 0.0,
    }


def resolve_state_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("USELESS_MAYBE_STATE")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".uselessMaybe" / "state.json"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_state()

    base = default_state()
    if isinstance(data, dict):
        for key in base:
            if key in data:
                base[key] = data[key]
    recent = base["recent_events"]
    base["recent_events"] = (
        [event for event in recent if isinstance(event, str)][-RECENT_EVENT_LIMIT:]
        if isinstance(recent, list) else []
    )
    try:
        base["paperwork_last_invocation"] = max(0, int(base["paperwork_last_invocation"]))
    except (TypeError, ValueError, OverflowError):
        base["paperwork_last_invocation"] = 0
    return base


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "invocations": int(state.get("invocations", 0)),
        "nothing_counter": int(state.get("nothing_counter", 0)),
        "pending_menu": state.get("pending_menu"),
        "unique_eggs_seen": len(state.get("seen_events", [])),
    }
