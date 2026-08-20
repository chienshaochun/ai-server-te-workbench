"""Validated contracts for optional LLM-assisted troubleshooting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ai_server_te_workbench.knowledge import SymptomCategory


class AdviceSource(str, Enum):
    DETERMINISTIC = "deterministic"
    OPENAI = "openai"


@dataclass(frozen=True)
class TriageAdvice:
    category: SymptomCategory
    confidence: float
    summary_zh: str
    observations: tuple[str, ...]
    missing_information: tuple[str, ...]
    recommended_step_id: str
    reason_zh: str
    safety_warning_zh: str | None
    source: AdviceSource
    model: str | None = None
    fallback_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.category, SymptomCategory):
            raise TypeError("category must be a SymptomCategory")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be numeric")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        _text(self.summary_zh, "summary_zh")
        _text(self.recommended_step_id, "recommended_step_id")
        _text(self.reason_zh, "reason_zh")
        for field_name in ("observations", "missing_information"):
            value = getattr(self, field_name)
            if isinstance(value, list):
                value = tuple(value)
                object.__setattr__(self, field_name, value)
            if not isinstance(value, tuple) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise TypeError(f"{field_name} must contain non-empty text")
        if self.safety_warning_zh is not None:
            _text(self.safety_warning_zh, "safety_warning_zh")
        if not isinstance(self.source, AdviceSource):
            raise TypeError("source must be an AdviceSource")
        if self.model is not None:
            _text(self.model, "model")
        if self.fallback_reason is not None:
            _text(self.fallback_reason, "fallback_reason")
        if self.source is AdviceSource.OPENAI and self.model is None:
            raise ValueError("OpenAI advice requires model metadata")

    @property
    def used_llm(self) -> bool:
        return self.source is AdviceSource.OPENAI


@dataclass(frozen=True)
class AssistantAnswer:
    answer_zh: str
    recommended_next_action_zh: str
    safety_warning_zh: str | None
    related_step_id: str
    model: str

    def __post_init__(self) -> None:
        for field_name in (
            "answer_zh",
            "recommended_next_action_zh",
            "related_step_id",
            "model",
        ):
            _text(getattr(self, field_name), field_name)
        if self.safety_warning_zh is not None:
            _text(self.safety_warning_zh, "safety_warning_zh")


@dataclass(frozen=True)
class AssistantExchange:
    question_zh: str
    answer: AssistantAnswer

    def __post_init__(self) -> None:
        _text(self.question_zh, "question_zh")
        if not isinstance(self.answer, AssistantAnswer):
            raise TypeError("answer must be an AssistantAnswer")


def _text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
