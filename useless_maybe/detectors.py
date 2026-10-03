from __future__ import annotations

from .models import AgentSignals, Detection


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def detect(signals: AgentSignals) -> list[Detection]:
    s = signals.sanitized()
    out: list[Detection] = []
    ratio = s.reasoning_tokens / max(s.output_tokens, 1)

    if s.reasoning_tokens >= 1800 and ratio >= 8:
        severity = _clamp(((s.reasoning_tokens - 1800) / 5000) * 0.5 + ((ratio - 8) / 60) * 0.5)
        out.append(Detection("OVERTHINKING", max(0.2, severity), "Large observable reasoning metadata produced a comparatively small output."))

    if ratio >= 20 and s.reasoning_tokens >= 400:
        out.append(Detection("THOUGHT_TO_OUTPUT_RATIO", _clamp((ratio - 20) / 100 + 0.25), f"Observable reasoning/output ratio is {ratio:.1f}:1."))

    if s.tool_calls >= 6:
        out.append(Detection("TOOL_OBSESSION", max(0.2, _clamp((s.tool_calls - 5) / 10)), f"{s.tool_calls} tool calls were reported."))

    if s.retries >= 2:
        out.append(Detection("RETRYING", max(0.2, _clamp((s.retries - 1) / 5)), f"{s.retries} retries were reported."))

    if s.repeated_actions >= 3:
        out.append(Detection("LOOPING", max(0.2, _clamp((s.repeated_actions - 2) / 5)), f"{s.repeated_actions} repeated equivalent actions were reported."))

    if s.context_tokens >= 60000:
        out.append(Detection("CONTEXT_PRESSURE", _clamp((s.context_tokens - 60000) / 140000 + 0.25), f"Context size was reported as {s.context_tokens} tokens."))

    if s.visible_reasoning and s.reasoning_tokens > 0:
        out.append(Detection("EXPOSED_REASONING_METADATA", _clamp(s.reasoning_tokens / 6000), "Caller explicitly marked reasoning metadata as visible."))

    return out
