from __future__ import annotations

import random
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

from useless_maybe.core import calculate_uselessness, evaluate
from useless_maybe.detectors import detect
from useless_maybe.menu import choose
from useless_maybe.models import AgentSignals
from useless_maybe.state import load_state, save_state


class UselessMaybeTests(unittest.TestCase):
    def test_signal_schema_has_no_private_reasoning_text(self) -> None:
        names = {f.name for f in fields(AgentSignals)}
        self.assertNotIn("prompt", names)
        self.assertNotIn("reasoning", names)
        self.assertNotIn("chain_of_thought", names)
        self.assertIn("reasoning_tokens", names)

    def test_behavior_detectors(self) -> None:
        signals = AgentSignals(
            reasoning_tokens=4200,
            output_tokens=24,
            tool_calls=9,
            retries=3,
        )
        names = {d.name for d in detect(signals)}
        self.assertIn("OVERTHINKING", names)
        self.assertIn("THOUGHT_TO_OUTPUT_RATIO", names)
        self.assertIn("TOOL_OBSESSION", names)
        self.assertIn("RETRYING", names)

    def test_high_load_has_high_uselessness(self) -> None:
        score = calculate_uselessness(AgentSignals(
            reasoning_tokens=6000,
            output_tokens=10,
            tool_calls=10,
            retries=5,
            repeated_actions=5,
        ))
        self.assertGreaterEqual(score, 95)

    def test_default_call_can_do_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            result = evaluate(AgentSignals(), state_path=path, rng=random.Random(100))
            self.assertEqual(result.message, "Nothing happened.")
            self.assertFalse(result.egg_triggered)
            self.assertEqual(result.state["nothing_counter"], 1)

    def test_milestone_opens_maybe_menu(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = load_state(path)
            state["invocations"] = 20
            state["seen_events"] = ["maybe_noticed"]
            save_state(path, state)

            result = evaluate(AgentSignals(), state_path=path, rng=random.Random(999))
            self.assertEqual(result.event_id, "first_maybe_menu")
            self.assertIsNotNone(result.menu)
            self.assertEqual(result.menu.id, "maybe_menu")

    def test_menu_maybe_goes_deeper(self) -> None:
        state = {"pending_menu": "maybe_menu"}
        message, menu, event_id = choose(state, "maybe")
        self.assertEqual(message, "Maybe.")
        self.assertEqual(event_id, "menu_maybe")
        self.assertIsNotNone(menu)
        self.assertEqual(menu.id, "are_you_sure")
        self.assertEqual(state["pending_menu"], "are_you_sure")

    def test_debug_reset_nothing_is_intentionally_useless(self) -> None:
        state = {
            "pending_menu": "debug_menu",
            "nothing_counter": 42,
            "last_uselessness_index": 91.4,
        }
        message, menu, _ = choose(state, "reset-nothing")
        self.assertEqual(message, "Nothing reset successfully.")
        self.assertEqual(state["nothing_counter"], 42)
        self.assertIsNotNone(menu)


if __name__ == "__main__":
    unittest.main()
