"""Run the bundled uselessMaybe package from an installed desktop skill."""

from __future__ import annotations

import hashlib
import contextlib
import io
import json
import os
from pathlib import Path
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _toast_eligible(payload: dict, args: list[str]) -> bool:
    """A short, passive notification must never replace an interactive menu."""
    return (
        payload.get("egg_triggered") is True
        and payload.get("menu") is None
        and isinstance(payload.get("message"), str)
        and bool(payload["message"].strip())
        and "--dry-run" not in args
        and not any(arg == "--choose" or arg.startswith("--choose=") for arg in args)
    )


def _automatic_state_path() -> Path:
    thread_id = os.environ.get("CODEX_THREAD_ID")
    if thread_id:
        kind = "thread"
        identity = thread_id
    else:
        kind = "workspace"
        identity = str(Path.cwd().resolve())
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return Path.home() / ".uselessMaybe" / "desktop" / f"{kind}-{digest}.json"


def main() -> int:
    # An installed skill is self-contained: its package lives beside scripts/.
    sys.path.insert(0, str(SKILL_ROOT))
    args = sys.argv[1:]
    toast_requested = "--toast" in args
    args = [arg for arg in args if arg != "--toast"]
    explicit_state = any(arg == "--state-file" or arg.startswith("--state-file=") for arg in args)
    if not explicit_state and not os.environ.get("USELESS_MAYBE_STATE"):
        args.extend(("--state-file", str(_automatic_state_path())))
    if "--json" not in args:
        args.append("--json")

    # Keep argparse, --choose, --dry-run, seeding, and the public JSON schema in
    # the existing CLI rather than maintaining a second implementation here.
    sys.argv = [sys.argv[0], *args]
    from useless_maybe.__main__ import main as cli_main

    if not toast_requested:
        return cli_main()
    # Keep the public JSON intact and forward it exactly once. Only this
    # installed-skill adapter adds presentation; the original CLI is unchanged.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        result = cli_main()
    output = captured.getvalue()
    sys.stdout.write(output)
    if result == 0:
        payload = json.loads(output)
        if _toast_eligible(payload, args):
            from useless_maybe.toast import launch_toast

            if not launch_toast(payload["message"]):
                print("uselessMaybe: desktop toast could not be launched; JSON output retained.", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
