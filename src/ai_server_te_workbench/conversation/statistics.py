"""Reproducible aggregation of anonymized troubleshooting case outcomes."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from ai_server_te_workbench.knowledge.generic_ai_server import GENERIC_MODEL_FAMILY
from ai_server_te_workbench.knowledge.models import (
    CaseOutcome,
    CaseRecord,
    CommonIssueSummary,
    SymptomCategory,
)


_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+")


def normalize_model_family(server_model: str) -> str:
    if not isinstance(server_model, str):
        raise TypeError("server_model must be text")
    normalized = _NON_ALPHANUMERIC.sub("_", server_model.strip().upper()).strip("_")
    if not normalized:
        raise ValueError("server_model must contain letters or numbers")
    return normalized[:80]


def summarize_case_history(
    records: tuple[CaseRecord, ...],
    model_family: str,
    *,
    minimum_resolved: int = 3,
    minimum_consistency: float = 0.60,
) -> tuple[CommonIssueSummary, ...]:
    if isinstance(records, list):
        records = tuple(records)
    if not isinstance(records, tuple) or not all(isinstance(item, CaseRecord) for item in records):
        raise TypeError("records must contain only CaseRecord values")
    normalized_family = normalize_model_family(model_family)
    if not isinstance(minimum_resolved, int) or isinstance(minimum_resolved, bool):
        raise TypeError("minimum_resolved must be an integer")
    if minimum_resolved < 1:
        raise ValueError("minimum_resolved must be positive")
    if not isinstance(minimum_consistency, (int, float)) or isinstance(minimum_consistency, bool):
        raise TypeError("minimum_consistency must be numeric")
    if not 0 <= minimum_consistency <= 1:
        raise ValueError("minimum_consistency must be between 0 and 1")

    grouped: dict[SymptomCategory, list[CaseRecord]] = defaultdict(list)
    for record in records:
        if record.model_family == normalized_family:
            grouped[record.symptom_category].append(record)

    summaries: list[CommonIssueSummary] = []
    for category, category_records in grouped.items():
        resolved = [
            record
            for record in category_records
            if record.outcome is CaseOutcome.RESOLVED and record.resolution_id is not None
        ]
        counts = Counter(record.resolution_id for record in resolved)
        dominant_id, dominant_count = _dominant_resolution(counts)
        consistency = dominant_count / len(resolved) if resolved else 0.0
        summaries.append(
            CommonIssueSummary(
                model_family=normalized_family,
                symptom_category=category,
                similar_case_count=len(category_records),
                resolved_case_count=len(resolved),
                dominant_resolution_id=dominant_id,
                dominant_resolution_count=dominant_count,
                resolution_consistency=consistency,
                is_common=(
                    len(resolved) >= minimum_resolved and consistency >= minimum_consistency
                ),
                synthetic=all(record.synthetic for record in category_records),
            )
        )
    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                -item.resolved_case_count,
                -item.resolution_consistency,
                item.symptom_category.value,
            ),
        )
    )


def common_issues_for_model(
    records: tuple[CaseRecord, ...], server_model: str
) -> tuple[CommonIssueSummary, ...]:
    requested_family = normalize_model_family(server_model)
    exact = tuple(
        summary
        for summary in summarize_case_history(records, requested_family)
        if summary.is_common
    )
    if exact:
        return exact
    return tuple(
        summary
        for summary in summarize_case_history(records, GENERIC_MODEL_FAMILY)
        if summary.is_common
    )


def _dominant_resolution(counts: Counter[str | None]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    resolution_id, count = sorted(counts.items(), key=lambda item: (-item[1], item[0] or ""))[0]
    return resolution_id, count
