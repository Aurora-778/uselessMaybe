"""Internal detached toast child; run directly only for a local preview."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from useless_maybe.toast import show_toast


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview the three-second uselessMaybe Windows toast")
    parser.add_argument("message", nargs="?", help="Toast message (local preview)")
    parser.add_argument("--message", dest="message_option", help="Message passed by the skill runner")
    parser.add_argument("--duration", type=float, default=3.0,
                        help="Local QA preview only: seconds visible (normal toast uses 3.0)")
    args = parser.parse_args(argv)
    text = args.message_option or args.message or "Nothing happened.\nProbably."
    try:
        return 0 if show_toast(text, args.duration) else 1
    except Exception as exc:
        # pythonw has no console; the parent JSON response remains unaffected.
        if args.message_option is None:
            print(f"Toast preview failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
