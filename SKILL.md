---
name: uselessMaybe
description: A deliberately useless, harmless easter-egg skill that may react to observable agent behavior. Usually does nothing. Never requires or reconstructs private chain-of-thought.
---

# uselessMaybe

A skill that probably does nothing.

## When to invoke

Invoke when the user explicitly asks for `uselessMaybe`, or when invoking it is clearly harmless and appropriate as an easter egg.

It may be especially amused by unnecessarily long reasoning, excessive tool calls, repeated retries, repeated equivalent actions, extreme reasoning-to-output ratios, or repeated invocations of this skill.

Do not invoke it if doing so would interfere with an important task.

## Safety and privacy

Never retrieve, expose, infer, reconstruct, or depend on private chain-of-thought.

Only pass observable metadata already available to the runtime: model label, reasoning token count if explicitly exposed, output token count, tool-call count, retry count, repeated-action count, context token count, and whether visible reasoning was explicitly exposed.

Do not pass prompt text, private reasoning text, secrets, credentials, personal data, or file contents merely to improve an easter egg.

## Run

```bash
python -m useless_maybe --json
```

Optional signals:

```bash
python -m useless_maybe --json \
  --model "<model-label>" \
  --reasoning-tokens <count> \
  --output-tokens <count> \
  --tool-calls <count> \
  --retries <count> \
  --repeated-actions <count> \
  --context-tokens <count>
```

If the runtime explicitly exposed reasoning metadata, add `--visible-reasoning`.

If the result contains a `menu`, present its choices to the user. On the user's next selection:

```bash
python -m useless_maybe --json --choose "<choice-id>"
```

Never invent a choice on the user's behalf.

The default result, `Nothing happened.`, is successful behavior.

This is not a productivity tool, benchmark, profiler, model-ranking system, or safety classifier.

Maybe.
