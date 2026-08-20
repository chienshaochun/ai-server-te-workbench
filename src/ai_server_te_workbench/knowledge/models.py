"""Domain contracts for issue matching and anonymized case aggregation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class SymptomCategory(str, Enum):
    NETWORK_UNREACHABLE = "network_unreachable"
    ONE_UNIT_ONLY = "one_unit_only"
    FIRMWARE_MISMATCH = "firmware_mismatch"
    GPU_MISSING = "gpu_missing"
    TEMPERATURE_HIGH = "temperature_high"
    UNKNOWN = "unknown"


class CaseOutcome(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class KnowledgeEntry:
    category: SymptomCategory
    title_zh: str
    description_zh: str
    strong_keywords: tuple[str, ...]
    weak_keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.category, SymptomCategory):
            raise TypeError("category must be a SymptomCategory")
        _require_text(self.title_zh, "title_zh")
        _require_text(self.description_zh, "description_zh")
        for field_name in ("strong_keywords", "weak_keywords"):
            value = getattr(self, field_name)
            if isinstance(value, list):
                value = tuple(value)
                object.__setattr__(self, field_name, value)
            if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
                raise TypeError(f"{field_name} must contain only text")
            if any(not item.strip() for item in value):
                raise ValueError(f"{field_name} cannot contain empty keywords")
        if not self.strong_keywords:
            raise ValueError("at least one strong keyword is required")
        all_keywords = (*self.strong_keywords, *self.weak_keywords)
        if len(all_keywords) != len(set(keyword.casefold() for keyword in all_keywords)):
            raise ValueError("knowledge entry keywords must be unique")


@dataclass(frozen=True)
class IssueMatch:
    category: SymptomCategory
    confidence: float
    matched_terms: tuple[str, ...]
    alternatives: tuple[SymptomCategory, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.category, SymptomCategory):
            raise TypeError("category must be a SymptomCategory")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be numeric")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        for field_name in ("matched_terms", "alternatives"):
            value = getattr(self, field_name)
            if isinstance(value, list):
                object.__setattr__(self, field_name, tuple(value))
        if not isinstance(self.matched_terms, tuple) or not all(
            isinstance(item, str) and item for item in self.matched_terms
        ):
            raise TypeError("matched_terms must contain non-empty text")
        if not isinstance(self.alternatives, tuple) or not all(
            isinstance(item, SymptomCategory) for item in self.alternatives
        ):
            raise TypeError("alternatives must contain SymptomCategory values")
        if self.category in self.alternatives:
            raise ValueError("primary category cannot also be an alternative")

    @property
    def needs_confirmation(self) -> bool:
        return self.category is SymptomCategory.UNKNOWN or self.confidence < 0.60


@dataclass(frozen=True)
class CaseRecord:
    model_family: str
    symptom_category: SymptomCategory
    resolution_id: str | None
    outcome: CaseOutcome
    synthetic: bool = True

    def __post_init__(self) -> None:
        _require_identifier(self.model_family, "model_family")
        if not isinstance(self.symptom_category, SymptomCategory):
            raise TypeError("symptom_category must be a SymptomCategory")
        if self.resolution_id is not None:
            _require_identifier(self.resolution_id, "resolution_id")
        if not isinstance(self.outcome, CaseOutcome):
            raise TypeError("outcome must be a CaseOutcome")
        if self.outcome is CaseOutcome.RESOLVED and self.resolution_id is None:
            raise ValueError("resolved case requires resolution_id")
        if not isinstance(self.synthetic, bool):
            raise TypeError("synthetic must be a bool")


@dataclass(frozen=True)
class CommonIssueSummary:
    model_family: str
    symptom_category: SymptomCategory
    similar_case_count: int
    resolved_case_count: int
    dominant_resolution_id: str | None
    dominant_resolution_count: int
    resolution_consistency: float
    is_common: bool
    synthetic: bool

    def __post_init__(self) -> None:
        _require_identifier(self.model_family, "model_family")
        if not isinstance(self.symptom_category, SymptomCategory):
            raise TypeError("symptom_category must be a SymptomCategory")
        for field_name in (
            "similar_case_count",
            "resolved_case_count",
            "dominant_resolution_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field_name} must be an integer")
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.resolved_case_count > self.similar_case_count:
            raise ValueError("resolved cases cannot exceed similar cases")
        if self.dominant_resolution_count > self.resolved_case_count:
            raise ValueError("dominant resolution cannot exceed resolved cases")
        if self.dominant_resolution_id is not None:
            _require_identifier(self.dominant_resolution_id, "dominant_resolution_id")
        if not 0 <= self.resolution_consistency <= 1:
            raise ValueError("resolution_consistency must be between 0 and 1")
        if not isinstance(self.is_common, bool) or not isinstance(self.synthetic, bool):
            raise TypeError("is_common and synthetic must be bool values")


@dataclass(frozen=True)
class SyntheticCasePattern:
    id: str
    title_zh: str
    example_problem_zh: str
    symptom_category: SymptomCategory
    keywords: tuple[str, ...]
    observed_conditions: tuple[str, ...]
    recommended_first_check_zh: str
    dominant_resolution_id: str
    resolution_summary_zh: str
    case_count: int
    resolved_count: int

    def __post_init__(self) -> None:
        _require_identifier(self.id, "pattern id")
        _require_text(self.title_zh, "title_zh")
        _require_text(self.example_problem_zh, "example_problem_zh")
        if not isinstance(self.symptom_category, SymptomCategory):
            raise TypeError("symptom_category must be a SymptomCategory")
        for field_name in ("keywords", "observed_conditions"):
            value = getattr(self, field_name)
            if isinstance(value, list):
                value = tuple(value)
                object.__setattr__(self, field_name, value)
            if (
                not isinstance(value, tuple)
                or not value
                or not all(isinstance(item, str) and item.strip() for item in value)
            ):
                raise ValueError(f"{field_name} requires non-empty text values")
        _require_text(self.recommended_first_check_zh, "recommended_first_check_zh")
        _require_identifier(self.dominant_resolution_id, "dominant_resolution_id")
        _require_text(self.resolution_summary_zh, "resolution_summary_zh")
        for field_name in ("case_count", "resolved_count"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.case_count < 1 or self.resolved_count > self.case_count:
            raise ValueError("case counts are inconsistent")

    @property
    def resolution_rate(self) -> float:
        return self.resolved_count / self.case_count


@dataclass(frozen=True)
class PatternMatch:
    pattern: SyntheticCasePattern
    score: float
    matched_terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.pattern, SyntheticCasePattern):
            raise TypeError("pattern must be a SyntheticCasePattern")
        if not isinstance(self.score, (int, float)) or isinstance(self.score, bool):
            raise TypeError("score must be numeric")
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")
        if isinstance(self.matched_terms, list):
            object.__setattr__(self, "matched_terms", tuple(self.matched_terms))


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _require_identifier(value: object, field_name: str) -> None:
    _require_text(value, field_name)
    assert isinstance(value, str)
    if not all(character.isalnum() or character in "_-" for character in value):
        raise ValueError(f"{field_name} contains unsupported characters")
