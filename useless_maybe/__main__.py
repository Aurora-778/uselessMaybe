from __future__ import annotations

import argparse
import json
import random
import sys

from .core import evaluate
from .menu import choose
from .models import AgentSignals
from .state import load_state, public_state, resolve_state_path, save_state


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="useless-maybe", description="A skill that probably does nothing.")
    p.add_argument("--model")
    p.add_argument("--reasoning-tokens", type=int, default=0)
    p.add_argument("--output-tokens", type=int, default=0)
    p.add_argument("--tool-calls", type=int, default=0)
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--repeated-actions", type=int, default=0)
    p.add_argument("--context-tokens", type=int, default=0)
    p.add_argument("--visible-reasoning", action="store_true")
    p.add_argument("--hour", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--state-file")
    p.add_argument("--choose", help="Choose an option from a pending Maybe menu.")
    p.add_argument("--json", action="store_true", dest="json_output")
    p.add_argument("--dry-run", action="store_true")
    return p


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(payload["message"])
    menu = payload.get("menu")
    if menu:
        print()
        for option in menu["choices"]:
            print(f"[{option['id']}] {option['label']}")


def main() -> int:
    args = build_parser().parse_args()

    if args.choose is not None:
        path = resolve_state_path(args.state_file)
        state = load_state(path)
        message, menu, event_id = choose(state, args.choose)
        if not args.dry_run:
            save_state(path, state)
        emit({
            "message": message,
            "egg_triggered": True,
            "event_id": event_id,
            "menu": menu.to_dict() if menu else None,
            "state": public_state(state),
        }, args.json_output)
        return 0

    signals = AgentSignals(
        model=args.model,
        reasoning_tokens=args.reasoning_tokens,
        output_tokens=args.output_tokens,
        tool_calls=args.tool_calls,
        retries=args.retries,
        repeated_actions=args.repeated_actions,
        context_tokens=args.context_tokens,
        visible_reasoning=args.visible_reasoning,
        local_hour=args.hour,
    )
    rng = random.Random(args.seed) if args.seed is not None else None
    result = evaluate(signals, state_path=args.state_file, rng=rng, dry_run=args.dry_run)
    emit(result.to_dict(), args.json_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
