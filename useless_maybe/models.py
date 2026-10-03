from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentSignals:
    """Observable metadata only. No prompt or hidden-reasoning text fields."""

    model: str | None = None
    reasoning_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    retries: int = 0
    repeated_actions: int = 0
    context_tokens: int = 0
    visible_reasoning: bool = False
    local_hour: int | None = None

    def sanitized(self) -> "AgentSignals":
        hour = self.local_hour
        if hour is not None:
            hour = max(0, min(23, int(hour)))
        return AgentSignals(
            model=self.model[:120] if self.model else None,
            reasoning_tokens=max(0, int(self.reasoning_tokens)),
            output_tokens=max(0, int(self.output_tokens)),
            tool_calls=max(0, int(self.tool_calls)),
            retries=max(0, int(self.retries)),
            repeated_actions=max(0, int(self.repeated_actions)),
            context_tokens=max(0, int(self.context_tokens)),
            visible_reasoning=bool(self.visible_reasoning),
            local_hour=hour,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Detection:
    name: str
    severity: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": round(self.severity, 3),
            "reason": self.reason,
        }


@dataclass(slots=True)
class Menu:
    id: str
    title: str
    choices: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "choices": self.choices}


@dataclass(slots=True)
class EvaluationResult:
    message: str
    egg_triggered: bool
    event_id: str | None
    maybe_score: float
    uselessness_index: float
    detections: list[Detection] = field(default_factory=list)
    menu: Menu | None = None
    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "egg_triggered": self.egg_triggered,
            "event_id": self.event_id,
            "maybe_score": round(self.maybe_score, 2),
            "uselessness_index": round(self.uselessness_index, 2),
            "detections": [d.to_dict() for d in self.detections],
            "menu": self.menu.to_dict() if self.menu else None,
            "state": self.state,
        }
