"""Immutable contracts for one-step-at-a-time troubleshooting conversations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_server_te_workbench.knowledge.models import SymptomCategory


class SessionOutcome(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class StepBranch:
    answer_id: str
    answer_label_zh: str
    observation_zh: str
    next_step_id: str | None = None
    outcome: SessionOutcome | None = None
    resolution_id: str | None = None
    category_override: SymptomCategory | None = None

    def __post_init__(self) -> None:
        _identifier(self.answer_id, "answer_id")
        _text(self.answer_label_zh, "answer_label_zh")
        _text(self.observation_zh, "observation_zh")
        if self.next_step_id is not None:
            _identifier(self.next_step_id, "next_step_id")
        if (self.next_step_id is None) == (self.outcome is None):
            raise ValueError("branch requires exactly one next step or terminal outcome")
        if self.outcome is not None:
            if (
                not isinstance(self.outcome, SessionOutcome)
                or self.outcome is SessionOutcome.ACTIVE
            ):
                raise ValueError("terminal outcome must be resolved, unresolved, or escalated")
        if self.resolution_id is not None:
            _identifier(self.resolution_id, "resolution_id")
        if self.outcome is SessionOutcome.RESOLVED and self.resolution_id is None:
            raise ValueError("resolved branch requires resolution_id")
        if self.category_override is not None and not isinstance(
            self.category_override, SymptomCategory
        ):
            raise TypeError("category_override must be a SymptomCategory")


@dataclass(frozen=True)
class DiagnosticStep:
    id: str
    category: SymptomCategory
    question_zh: str
    recommended_check_zh: str
    evidence_tag: str
    branches: tuple[StepBranch, ...]
    safety_note_zh: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.id, "step id")
        if not isinstance(self.category, SymptomCategory):
            raise TypeError("category must be a SymptomCategory")
        _text(self.question_zh, "question_zh")
        _text(self.recommended_check_zh, "recommended_check_zh")
        _identifier(self.evidence_tag, "evidence_tag")
        if isinstance(self.branches, list):
            object.__setattr__(self, "branches", tuple(self.branches))
        if not isinstance(self.branches, tuple) or not self.branches:
            raise ValueError("step requires at least one branch")
        if not all(isinstance(branch, StepBranch) for branch in self.branches):
            raise TypeError("branches must contain StepBranch values")
        answer_ids = tuple(branch.answer_id for branch in self.branches)
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("answer IDs must be unique within a step")
        if self.safety_note_zh is not None:
            _text(self.safety_note_zh, "safety_note_zh")


@dataclass(frozen=True)
class ConversationTurn:
    sequence: int
    step_id: str
    question_zh: str
    recommended_check_zh: str
    answer_id: str
    answer_label_zh: str
    observation_zh: str
    evidence_id: str
    safety_note_zh: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 1
        ):
            raise ValueError("sequence must be a positive integer")
        for field_name in (
            "step_id",
            "question_zh",
            "recommended_check_zh",
            "answer_id",
            "answer_label_zh",
            "observation_zh",
            "evidence_id",
        ):
            _text(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class TroubleshootingSession:
    session_id: str
    server_model: str
    raw_problem: str
    symptom_category: SymptomCategory
    match_confidence: float
    current_step_id: str | None
    transcript: tuple[ConversationTurn, ...]
    outcome: SessionOutcome
    resolution_id: str | None = None
    uses_synthetic_history: bool = True

    def __post_init__(self) -> None:
        _identifier(self.session_id, "session_id")
        _text(self.server_model, "server_model")
        _text(self.raw_problem, "raw_problem")
        if len(self.raw_problem) > 1000:
            raise ValueError("raw_problem cannot exceed 1000 characters")
        if not isinstance(self.symptom_category, SymptomCategory):
            raise TypeError("symptom_category must be a SymptomCategory")
        if not isinstance(self.match_confidence, (int, float)) or isinstance(
            self.match_confidence, bool
        ):
            raise TypeError("match_confidence must be numeric")
        if not 0 <= self.match_confidence <= 1:
            raise ValueError("match_confidence must be between 0 and 1")
        if isinstance(self.transcript, list):
            object.__setattr__(self, "transcript", tuple(self.transcript))
        if not isinstance(self.transcript, tuple) or not all(
            isinstance(turn, ConversationTurn) for turn in self.transcript
        ):
            raise TypeError("transcript must contain ConversationTurn values")
        if tuple(turn.sequence for turn in self.transcript) != tuple(
            range(1, len(self.transcript) + 1)
        ):
            raise ValueError("transcript sequence must be contiguous")
        if not isinstance(self.outcome, SessionOutcome):
            raise TypeError("outcome must be a SessionOutcome")
        if self.outcome is SessionOutcome.ACTIVE and self.current_step_id is None:
            raise ValueError("active session requires current_step_id")
        if self.outcome is not SessionOutcome.ACTIVE and self.current_step_id is not None:
            raise ValueError("terminal session cannot have current_step_id")
        if self.outcome is SessionOutcome.RESOLVED and self.resolution_id is None:
            raise ValueError("resolved session requires resolution_id")
        if not isinstance(self.uses_synthetic_history, bool):
            raise TypeError("uses_synthetic_history must be a bool")


def _text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _identifier(value: object, field_name: str) -> None:
    _text(value, field_name)
    assert isinstance(value, str)
    if not all(character.isalnum() or character in "_-" for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
