"""uselessMaybe: a skill that probably does nothing."""

from .core import evaluate
from .models import AgentSignals, EvaluationResult

__all__ = ["AgentSignals", "EvaluationResult", "evaluate"]
__version__ = "0.1.0"
