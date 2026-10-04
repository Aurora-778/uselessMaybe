from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from useless_maybe.state import default_state


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_skill.py"


class SkillRunnerTests(unittest.TestCase):
    def run_skill(
        self,
        script: Path,
        cwd: Path,
        home: Path,
        *args: str,
        thread_id: str | None = None,
        state_env: Path | None = None,
    ) -> dict:
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("CODEX_THREAD_ID", None)
        env.pop("USELESS_MAYBE_STATE", None)
        env["USERPROFILE"] = str(home)
        env["HOME"] = str(home)
        if thread_id is not None:
            env["CODEX_THREAD_ID"] = thread_id
        if state_env is not None:
            env["USELESS_MAYBE_STATE"] = str(state_env)
        result = subprocess.run(
            [sys.executable, "-I", str(script), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def automatic_path(home: Path, kind: str, identity: str) -> Path:
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        return home / ".uselessMaybe" / "desktop" / f"{kind}-{digest}.json"

    def test_runs_from_another_cwd_and_defaults_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cwd = base / "elsewhere"
            cwd.mkdir()
            home = base / "home"
            home.mkdir()
            result = self.run_skill(RUNNER, cwd, home, "--seed", "42", "--tool-calls", "9")
            self.assertIn("message", result)
            self.assertIn("event_id", result)
            self.assertEqual(result["state"]["invocations"], 1)
            self.assertTrue(self.automatic_path(home, "workspace", str(cwd.resolve())).exists())

    def test_minimal_copied_skill_is_independent_of_repo_and_pythonpath(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            skill = base / "installed-skill"
            (skill / "scripts").mkdir(parents=True)
            (skill / "useless_maybe").mkdir()
            shutil.copy2(ROOT / "SKILL.md", skill / "SKILL.md")
            shutil.copy2(RUNNER, skill / "scripts" / "run_skill.py")
            for module in (ROOT / "useless_maybe").glob("*.py"):
                shutil.copy2(module, skill / "useless_maybe" / module.name)
            cwd = base / "unrelated-workspace"
            cwd.mkdir()
            home = base / "home"
            home.mkdir()
            result = self.run_skill(skill / "scripts" / "run_skill.py", cwd, home, "--seed", "42")
            self.assertEqual(result["state"]["invocations"], 1)
            self.assertTrue(self.automatic_path(home, "workspace", str(cwd.resolve())).exists())

    def test_thread_state_follows_thread_and_workspace_fallback_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / "home"
            home.mkdir()
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            thread_a = "private-thread-id-A"
            thread_b = "private-thread-id-B"

            one = self.run_skill(RUNNER, first, home, thread_id=thread_a)
            two = self.run_skill(RUNNER, second, home, thread_id=thread_a)
            other = self.run_skill(RUNNER, first, home, thread_id=thread_b)
            self.assertEqual([one["state"]["invocations"], two["state"]["invocations"], other["state"]["invocations"]], [1, 2, 1])
            thread_path = self.automatic_path(home, "thread", thread_a)
            self.assertTrue(thread_path.exists())
            self.assertTrue(self.automatic_path(home, "thread", thread_b).exists())
            self.assertNotIn(thread_a, str(thread_path))
            self.assertNotIn(thread_a, json.dumps(two))

            workspace_one = self.run_skill(RUNNER, first, home)
            workspace_two = self.run_skill(RUNNER, second, home)
            self.assertEqual(workspace_one["state"]["invocations"], 1)
            self.assertEqual(workspace_two["state"]["invocations"], 1)
            self.assertTrue(self.automatic_path(home, "workspace", str(first.resolve())).exists())
            self.assertTrue(self.automatic_path(home, "workspace", str(second.resolve())).exists())

    def test_explicit_state_beats_environment_in_both_cli_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cwd = base / "cwd"
            cwd.mkdir()
            home = base / "home"
            home.mkdir()
            env_path = base / "environment.json"
            explicit_path = base / "explicit.json"

            from_env = self.run_skill(RUNNER, cwd, home, state_env=env_path)
            from_equals = self.run_skill(RUNNER, cwd, home, f"--state-file={explicit_path}", state_env=env_path)
            from_separate = self.run_skill(RUNNER, cwd, home, "--state-file", str(explicit_path), state_env=env_path)
            self.assertEqual(from_env["state"]["invocations"], 1)
            self.assertEqual(from_equals["state"]["invocations"], 1)
            self.assertEqual(from_separate["state"]["invocations"], 2)
            self.assertEqual(json.loads(env_path.read_text(encoding="utf-8"))["invocations"], 1)
            self.assertEqual(json.loads(explicit_path.read_text(encoding="utf-8"))["invocations"], 2)
            self.assertFalse((home / ".uselessMaybe").exists())

    def test_dry_run_does_not_create_or_change_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cwd = base / "cwd"
            cwd.mkdir()
            home = base / "home"
            home.mkdir()
            thread_id = "dry-run-thread"
            path = self.automatic_path(home, "thread", thread_id)

            preview = self.run_skill(RUNNER, cwd, home, "--dry-run", "--seed", "42", thread_id=thread_id)
            self.assertEqual(preview["state"]["invocations"], 1)
            self.assertFalse(path.exists())

            self.run_skill(RUNNER, cwd, home, thread_id=thread_id)
            original = path.read_bytes()
            second_preview = self.run_skill(RUNNER, cwd, home, "--dry-run", thread_id=thread_id)
            self.assertEqual(second_preview["state"]["invocations"], 2)
            self.assertEqual(path.read_bytes(), original)

    def test_choose_persists_menu_across_cwds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / "home"
            home.mkdir()
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            thread_id = "pending-menu-thread"
            path = self.automatic_path(home, "thread", thread_id)
            path.parent.mkdir(parents=True)
            state = default_state()
            state["pending_menu"] = "maybe_menu"
            path.write_text(json.dumps(state), encoding="utf-8")

            choice = self.run_skill(RUNNER, first, home, "--choose", "maybe", thread_id=thread_id)
            self.assertEqual(choice["event_id"], "menu_maybe")
            self.assertEqual(choice["menu"]["id"], "are_you_sure")
            self.assertEqual(choice["state"]["pending_menu"], "are_you_sure")
            next_call = self.run_skill(RUNNER, second, home, "--seed", "100", thread_id=thread_id)
            self.assertEqual(next_call["menu"]["id"], "are_you_sure")
            self.assertEqual(next_call["state"]["pending_menu"], "are_you_sure")
            final_choice = self.run_skill(RUNNER, second, home, "--choose", "yes", thread_id=thread_id)
            self.assertEqual(final_choice["event_id"], "menu_answer_accepted")
            self.assertIsNone(final_choice["state"]["pending_menu"])


if __name__ == "__main__":
    unittest.main()
