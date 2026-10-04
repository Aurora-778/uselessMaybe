from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_skill
from useless_maybe.state import default_state, save_state


class ToastPolicyTests(unittest.TestCase):
    def invoke(self, path: Path, *args: str):
        output = io.StringIO()
        with patch.object(sys, "argv", ["run_skill.py", "--state-file", str(path), "--hour", "12", *args]), \
                patch("useless_maybe.toast.launch_toast", return_value=True) as launcher, \
                contextlib.redirect_stdout(output):
            code = run_skill.main()
        self.assertEqual(code, 0)
        return json.loads(output.getvalue()), launcher

    def test_selected_egg_launches_once_and_preserves_public_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, original_launch = self.invoke(root / "plain.json", "--tool-calls", "8", "--seed", "162")
            toasted, toast_launch = self.invoke(root / "toast.json", "--tool-calls", "8", "--seed", "162", "--toast")
            self.assertEqual(original, toasted)
            self.assertEqual(toasted["event_id"], "tool_form")
            original_launch.assert_not_called()
            toast_launch.assert_called_once_with("Tool calls observed: 8.\nThe form has no field for results.")

    def test_launch_failure_retains_json_and_reports_on_stderr(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "toast.json"
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(sys, "argv", ["run_skill.py", "--state-file", str(path), "--hour", "12",
                                            "--tool-calls", "8", "--seed", "162", "--toast"]), \
                    patch("useless_maybe.toast.launch_toast", return_value=False) as launcher, \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = run_skill.main()
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["event_id"], "tool_form")
            self.assertEqual(payload["message"], "Tool calls observed: 8.\nThe form has no field for results.")
            launcher.assert_called_once_with(payload["message"])
            self.assertIn("JSON output retained", errors.getvalue())

    def test_nothing_and_dry_run_have_no_desktop_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nothing, quiet_launch = self.invoke(root / "nothing.json", "--seed", "100", "--toast")
            self.assertFalse(nothing["egg_triggered"])
            quiet_launch.assert_not_called()
            dry_path = root / "dry.json"
            preview, dry_launch = self.invoke(dry_path, "--tool-calls", "8", "--seed", "162", "--toast", "--dry-run")
            self.assertTrue(preview["egg_triggered"])
            self.assertFalse(dry_path.exists())
            dry_launch.assert_not_called()

    def test_pending_menu_is_not_replaced_by_a_toast(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "menu.json"
            state = default_state()
            state["pending_menu"] = "maybe_menu"
            save_state(path, state)
            result, launch = self.invoke(path, "--tool-calls", "8", "--seed", "162", "--toast")
            self.assertEqual(result["menu"]["id"], "maybe_menu")
            self.assertTrue(result["egg_triggered"])
            launch.assert_not_called()

    def test_explicit_menu_selection_keeps_its_chat_response(self):
        for choice_args in (("--choose", "maybe"), ("--choose=maybe",)):
            with self.subTest(choice_args=choice_args), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "menu.json"
                state = default_state()
                state["pending_menu"] = "only_maybe"
                save_state(path, state)
                result, launch = self.invoke(path, "--toast", *choice_args)
                self.assertEqual(result["event_id"], "menu_final_maybe")
                self.assertIsNone(result["menu"])
                self.assertEqual(result["message"], "Fine.\n\nNothing happened.")
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
