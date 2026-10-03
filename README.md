# uselessMaybe

> **A skill that probably does nothing.**

`uselessMaybe` is a deliberately non-essential agent skill. It watches only caller-provided, observable runtime signals — tool calls, retries, repeated actions, token counts, and explicitly exposed reasoning metadata — then decides whether something harmless happens.

Usually:

```text
Nothing happened.
```

Sometimes: an achievement, a strange sentence, a tiny frog, or a menu that looks more important than it is.

> It doesn't need to know what you're thinking.  
> It only needs to know that you thought too much.

## Rule zero

**Never depend on private chain-of-thought.**

The skill does not retrieve, reconstruct, infer, or store hidden reasoning. Prompt text and reasoning text are not needed or persisted.

## V0.1

- behavior-based easter egg probability
- Uselessness Index
- overthinking / looping / retry / tool-obsession detectors
- persistent Nothing Counter
- hidden multi-step Maybe Menu
- rare Debug Menu
- deterministic seeds for tests
- JSON output for agent integration
- zero third-party runtime dependencies

## Run

Python 3.10+:

```bash
python -m useless_maybe
```

With observable metadata:

```bash
python -m useless_maybe --json \
  --model "some-model" \
  --reasoning-tokens 4200 \
  --output-tokens 24 \
  --tool-calls 9 \
  --retries 3
```

If a menu appears:

```bash
python -m useless_maybe --choose maybe
```

Dry-run without changing state:

```bash
python -m useless_maybe --dry-run --json --seed 42 \
  --reasoning-tokens 5000 --output-tokens 12 --tool-calls 10
```

State defaults to `~/.uselessMaybe/state.json`. Override it with `USELESS_MAYBE_STATE` or `--state-file`.

## Signals

All are optional: `model`, `reasoning_tokens`, `output_tokens`, `tool_calls`, `retries`, `repeated_actions`, `context_tokens`, `visible_reasoning`, and caller-supplied `hour`.

There is intentionally no input for prompt text or hidden reasoning text.

## Install CLI

```bash
pip install -e .
useless-maybe
```

## Test

```bash
python -m unittest discover -s tests -v
```

Expected utility: approximately zero.

Maybe.
