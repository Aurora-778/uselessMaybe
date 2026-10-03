from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import AgentSignals, Detection


@dataclass(frozen=True, slots=True)
class Egg:
    id: str
    text: str
    weight: float = 1.0
    requires_any: frozenset[str] = frozenset()
    requires_all: frozenset[str] = frozenset()
    min_uselessness: float = 0.0
    min_invocations: int = 0
    menu_id: str | None = None

    def eligible(self, detections: Iterable[Detection], uselessness: float, invocations: int) -> bool:
        names = {d.name for d in detections}
        if self.requires_any and not (self.requires_any & names):
            return False
        if self.requires_all and not self.requires_all.issubset(names):
            return False
        return uselessness >= self.min_uselessness and invocations >= self.min_invocations

    def render(self, signals: AgentSignals, uselessness: float, invocations: int) -> str:
        return self.text.format(
            reasoning_tokens=signals.reasoning_tokens,
            output_tokens=signals.output_tokens,
            tool_calls=signals.tool_calls,
            retries=signals.retries,
            repeated_actions=signals.repeated_actions,
            uselessness=uselessness,
            invocations=invocations,
        )


EGGS: tuple[Egg, ...] = (
    Egg("nothing_probably", "Nothing happened.\nProbably.", weight=4.0),
    Egg("coin_somewhere", "A coin was flipped somewhere.\nYou are not allowed to know the result.", weight=2.0),
    Egg("today_17", "Today's number is 17.\nThis information will not be useful.", weight=2.0),
    Egg("tiny_frog", "You found a tiny frog.\n\n  @..@\n (----)\n( >__< )\n^^ ~~ ^^", weight=0.8),
    Egg("maybe_approves", "uselessMaybe approves.\nNo reason was provided.", weight=1.4),
    Egg("no_information", "No useful information was produced.\nWorking as intended.", weight=2.0),
    Egg("too_much_thinking", "That was a lot of thinking.\nNothing changed.", 3.0, frozenset({"OVERTHINKING", "THOUGHT_TO_OUTPUT_RATIO"})),
    Egg("thought_for_zero", "You thought for {reasoning_tokens:,} observable tokens.\nuselessMaybe thought for 0.", 2.5, frozenset({"OVERTHINKING", "EXPOSED_REASONING_METADATA"})),
    Egg("could_have_just_answered", "Achievement unlocked:\n\nCould Have Just Answered", 1.2, requires_all=frozenset({"THOUGHT_TO_OUTPUT_RATIO", "TOOL_OBSESSION"}), min_uselessness=55),
    Egg("wasted_compute", "Achievement unlocked:\n\nWasted Compute", 1.0, frozenset({"OVERTHINKING", "TOOL_OBSESSION"}), min_uselessness=65),
    Egg("second_thoughts", "Achievement unlocked:\n\nSecond Thoughts", 1.5, frozenset({"RETRYING"})),
    Egg("been_here", "You have been here before.", 2.0, frozenset({"LOOPING"})),
    Egg("we_have_been_here", "We have been here before.", 1.0, frozenset({"LOOPING"}), min_invocations=5),
    Egg("i_have_been_here", "I have been here before.", 0.45, frozenset({"LOOPING"}), min_invocations=10),
    Egg("tools_everywhere", "There were a lot of tools involved.\nThis one did not help.", 2.0, frozenset({"TOOL_OBSESSION"})),
    Egg("retry_accepted", "Your persistence has been observed.\nNo reward is available.", 2.0, frozenset({"RETRYING"})),
    Egg("context_big", "That is a lot of context for something this useless.", 1.5, frozenset({"CONTEXT_PRESSURE"})),
    Egg("more_useless", "For once,\nyou were more useless than uselessMaybe.", 0.55, frozenset({"OVERTHINKING", "THOUGHT_TO_OUTPUT_RATIO"}), min_uselessness=88),
    Egg("index_withheld", "uselessMaybe measured your usefulness.\n\nResult withheld.", 0.8, min_uselessness=78),
    Egg("index_revealed", "Uselessness Index: {uselessness:.1f}\n\nImpressive.", 0.3, min_uselessness=92),
    Egg("overflow", "USELESSNESS OVERFLOW\n\nNothing happened.", 0.15, min_uselessness=97),
    Egg("maybe_menu", "Something may have happened.", 0.22, min_invocations=8, menu_id="maybe_menu"),
    Egg("debug_menu", "MAYBE DEBUG MENU", 0.08, min_uselessness=88, min_invocations=12, menu_id="debug_menu"),
)
