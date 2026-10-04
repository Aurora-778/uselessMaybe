from __future__ import annotations

import io
import json
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from useless_maybe.__main__ import main
from useless_maybe.core import _weighted_choice, evaluate
from useless_maybe.eggs import Egg
from useless_maybe.menu import choose
from useless_maybe.models import Detection
from useless_maybe.state import default_state, load_state, public_state, save_state


class FixedRandom:
    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


class HumorFlowTests(unittest.TestCase):
    def test_old_state_migrates_internal_fields_and_keeps_public_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(json.dumps({
                "version": 1,
                "invocations": 3,
                "nothing_counter": 2,
                "event_counts": {"old_egg": 1},
                "seen_events": ["old_egg"],
                "pending_menu": None,
                "last_uselessness_index": 12.5,
            }), encoding="utf-8")

            state = load_state(path)

            self.assertEqual(state["recent_events"], [])
            self.assertEqual(state["paperwork_last_invocation"], 0)
            self.assertEqual(set(public_state(state)), {
                "invocations", "nothing_counter", "pending_menu", "unique_eggs_seen",
            })

    def test_recent_event_window_keeps_only_last_five_triggered_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            with patch("useless_maybe.core.PAPERWORK_EGGS", ()), patch(
                "useless_maybe.core.egg_probability", return_value=1.0,
            ):
                for index in range(6):
                    event_id = f"event-{index}"
                    with patch("useless_maybe.core.EGGS", (Egg(event_id, event_id),)):
                        result = evaluate(state_path=path, rng=random.Random(index))
                    self.assertEqual(result.event_id, event_id)

            state = load_state(path)
            self.assertEqual(state["recent_events"], [f"event-{i}" for i in range(1, 6)])
            self.assertNotIn("recent_events", public_state(state))

    def test_recent_only_candidate_falls_back_without_triggering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["recent_events"] = ["repeat"]
            save_state(path, state)

            with patch("useless_maybe.core.PAPERWORK_EGGS", ()), patch(
                "useless_maybe.core.EGGS", (Egg("repeat", "Repeat."),),
            ), patch("useless_maybe.core.egg_probability", return_value=1.0):
                result = evaluate(state_path=path, rng=random.Random(0))

            self.assertEqual(result.message, "Nothing happened.")
            self.assertFalse(result.egg_triggered)
            self.assertIsNone(result.event_id)
            self.assertEqual(load_state(path)["recent_events"], ["repeat"])

    def test_contextual_scenes_get_three_times_weight_and_generic_call_still_works(self) -> None:
        detection = Detection("LOOPING", 0.5, "test")
        generic_a = Egg("generic-a", "A.")
        generic_b = Egg("generic-b", "B.")

        for scene in (
            Egg("scene-any", "Scene.", requires_any=frozenset({"LOOPING"})),
            Egg("scene-all", "Scene.", requires_all=frozenset({"LOOPING"})),
        ):
            choices = [scene, generic_a, generic_b]
            self.assertEqual(
                _weighted_choice(FixedRandom(0.55), choices, [detection]).id,
                scene.id,
            )
            self.assertEqual(
                _weighted_choice(FixedRandom(0.65), choices, [detection]).id,
                "generic-a",
            )

        # The detections parameter remains optional for existing callers.
        self.assertEqual(
            _weighted_choice(
                FixedRandom(0.5),
                [Egg("small", "Small.", weight=1), Egg("large", "Large.", weight=3)],
            ).id,
            "large",
        )

    def test_paperwork_chapters_are_ordered_spaced_and_persisted(self) -> None:
        expected = {
            8: "paperwork_received",
            13: "paperwork_staffed",
            18: "paperwork_completed",
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            initial = default_state()
            initial["invocations"] = 7
            initial["seen_events"] = ["maybe_noticed"]
            save_state(path, initial)

            with patch("useless_maybe.core.EGGS", ()), patch(
                "useless_maybe.core.egg_probability", return_value=1.0,
            ):
                for invocation in range(8, 19):
                    result = evaluate(state_path=path, rng=random.Random(invocation))
                    if invocation in expected:
                        self.assertEqual(result.event_id, expected[invocation])
                        saved = json.loads(path.read_text(encoding="utf-8"))
                        self.assertEqual(saved["paperwork_last_invocation"], invocation)
                    else:
                        self.assertIsNone(result.event_id)

            saved_state = load_state(path)
            self.assertEqual(
                [event_id for event_id in expected.values() if event_id in saved_state["seen_events"]],
                list(expected.values()),
            )

    def test_pending_menu_is_returned_and_blocks_new_menus_at_all_four_levels(self) -> None:
        menu_ids = ("maybe_menu", "are_you_sure", "only_maybe", "debug_menu")
        for menu_id in menu_ids:
            with self.subTest(menu_id=menu_id), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "state.json"
                state = default_state()
                state["pending_menu"] = menu_id
                state["invocations"] = 20
                state["seen_events"] = ["maybe_noticed"]
                save_state(path, state)

                with patch("useless_maybe.core.EGGS", (
                    Egg("replacement_menu", "A different menu.", menu_id="debug_menu"),
                )), patch("useless_maybe.core.PAPERWORK_EGGS", ()), patch(
                    "useless_maybe.core.egg_probability", return_value=1.0,
                ):
                    result = evaluate(state_path=path, rng=random.Random(0))

                saved = load_state(path)
                self.assertEqual(result.message, "Nothing happened.")
                self.assertFalse(result.egg_triggered)
                self.assertIsNone(result.event_id)
                self.assertEqual(result.menu.id, menu_id)
                self.assertEqual(saved["pending_menu"], menu_id)
                self.assertNotIn("first_maybe_menu", saved["seen_events"])
                self.assertNotIn("first_maybe_menu", saved["event_counts"])

    def test_pending_menu_allows_non_menu_egg_and_keeps_current_menu(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["pending_menu"] = "are_you_sure"
            save_state(path, state)

            with patch("useless_maybe.core.EGGS", (Egg("side_note", "Side note."),)), patch(
                "useless_maybe.core.PAPERWORK_EGGS", (),
            ), patch("useless_maybe.core.egg_probability", return_value=1.0):
                result = evaluate(state_path=path, rng=random.Random(0))

            self.assertTrue(result.egg_triggered)
            self.assertEqual(result.event_id, "side_note")
            self.assertEqual(result.menu.id, "are_you_sure")
            self.assertEqual(result.state["pending_menu"], "are_you_sure")

    def test_blocked_menu_milestone_is_not_recorded_and_fires_after_menu_closes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["pending_menu"] = "maybe_menu"
            state["invocations"] = 20
            state["seen_events"] = ["maybe_noticed"]
            save_state(path, state)

            with patch("useless_maybe.core.EGGS", ()), patch(
                "useless_maybe.core.PAPERWORK_EGGS", (),
            ), patch("useless_maybe.core.egg_probability", return_value=1.0):
                waiting = evaluate(state_path=path, rng=random.Random(0))
                waiting_state = load_state(path)
                self.assertIsNone(waiting.event_id)
                self.assertEqual(waiting.menu.id, "maybe_menu")
                self.assertNotIn("first_maybe_menu", waiting_state["seen_events"])
                self.assertNotIn("first_maybe_menu", waiting_state["event_counts"])

                choose(waiting_state, "leave")
                save_state(path, waiting_state)
                resumed = evaluate(state_path=path, rng=random.Random(0))

            self.assertEqual(resumed.event_id, "first_maybe_menu")
            self.assertEqual(resumed.menu.id, "maybe_menu")

    def test_unknown_pending_menu_recovers_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["pending_menu"] = "retired_menu"
            save_state(path, state)

            with patch("useless_maybe.core.EGGS", ()), patch(
                "useless_maybe.core.PAPERWORK_EGGS", (),
            ), patch("useless_maybe.core.egg_probability", return_value=1.0):
                result = evaluate(state_path=path, rng=random.Random(0))

            self.assertFalse(result.egg_triggered)
            self.assertIsNone(result.event_id)
            self.assertIsNone(result.menu)
            self.assertIsNone(load_state(path)["pending_menu"])

    def test_dry_run_cli_json_keeps_public_schema_and_does_not_write_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["pending_menu"] = "debug_menu"
            save_state(path, state)
            before = path.read_bytes()
            output = io.StringIO()

            with patch("useless_maybe.core.EGGS", ()), patch(
                "useless_maybe.core.PAPERWORK_EGGS", (),
            ), patch("useless_maybe.core.egg_probability", return_value=1.0), patch.object(
                sys, "argv", ["useless-maybe", "--json", "--dry-run", "--state-file", str(path)],
            ), redirect_stdout(output):
                self.assertEqual(main(), 0)

            payload = json.loads(output.getvalue())
            self.assertEqual(set(payload), {
                "message", "egg_triggered", "event_id", "maybe_score", "uselessness_index",
                "detections", "menu", "state",
            })
            self.assertEqual(set(payload["state"]), {
                "invocations", "nothing_counter", "pending_menu", "unique_eggs_seen",
            })
            self.assertFalse(payload["egg_triggered"])
            self.assertIsNone(payload["event_id"])
            self.assertEqual(payload["message"], "Nothing happened.")
            self.assertEqual(payload["menu"]["id"], "debug_menu")
            self.assertEqual(path.read_bytes(), before)

    def test_triggered_paperwork_preview_does_not_consume_the_chapter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = default_state()
            state["invocations"] = 7
            state["recent_events"] = ["old_egg"]
            save_state(path, state)
            before = path.read_bytes()

            with patch("useless_maybe.core.EGGS", ()), patch(
                "useless_maybe.core.egg_probability", return_value=1.0,
            ):
                preview = evaluate(state_path=path, rng=random.Random(0), dry_run=True)
                self.assertEqual(preview.event_id, "paperwork_received")
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(load_state(path)["recent_events"], ["old_egg"])
                self.assertNotIn("paperwork_received", load_state(path)["seen_events"])
                self.assertEqual(load_state(path)["paperwork_last_invocation"], 0)
                committed = evaluate(state_path=path, rng=random.Random(0))

            self.assertEqual(committed.event_id, preview.event_id)
            self.assertEqual(load_state(path)["paperwork_last_invocation"], 8)


if __name__ == "__main__":
    unittest.main()
