"""Deterministic keyword scoring that chooses a conversation entry point."""

from __future__ import annotations

import re

from ai_server_te_workbench.knowledge.generic_ai_server import generic_knowledge_entries
from ai_server_te_workbench.knowledge.models import (
    IssueMatch,
    KnowledgeEntry,
    SymptomCategory,
)


_WHITESPACE = re.compile(r"\s+")


def match_issue(
    problem: str,
    entries: tuple[KnowledgeEntry, ...] | None = None,
) -> IssueMatch:
    if not isinstance(problem, str):
        raise TypeError("problem must be text")
    problem = problem.strip()
    if not problem:
        raise ValueError("problem cannot be empty")
    if len(problem) > 1000:
        raise ValueError("problem cannot exceed 1000 characters")
    entries = generic_knowledge_entries() if entries is None else entries
    if not isinstance(entries, tuple) or not entries:
        raise ValueError("entries must contain at least one KnowledgeEntry")
    if not all(isinstance(entry, KnowledgeEntry) for entry in entries):
        raise TypeError("entries must contain only KnowledgeEntry values")

    normalized = _normalize(problem)
    scores: list[tuple[float, KnowledgeEntry, tuple[str, ...]]] = []
    for entry in entries:
        matched_strong = tuple(
            keyword for keyword in entry.strong_keywords if _normalize(keyword) in normalized
        )
        matched_weak = tuple(
            keyword for keyword in entry.weak_keywords if _normalize(keyword) in normalized
        )
        score = 3.0 * len(matched_strong) + len(matched_weak)
        scores.append((score, entry, (*matched_strong, *matched_weak)))

    ranked = sorted(scores, key=lambda item: (-item[0], item[1].category.value))
    top_score, top_entry, matched_terms = ranked[0]
    if top_score == 0:
        return IssueMatch(
            category=SymptomCategory.UNKNOWN,
            confidence=0.0,
            matched_terms=(),
        )

    positive_alternatives = tuple(entry.category for score, entry, _ in ranked[1:] if score > 0)
    runner_up_score = ranked[1][0] if len(ranked) > 1 else 0.0
    confidence = _confidence(top_score)
    if runner_up_score and runner_up_score / top_score >= 0.75:
        confidence = min(confidence, 0.55)
    return IssueMatch(
        category=top_entry.category,
        confidence=confidence,
        matched_terms=matched_terms,
        alternatives=positive_alternatives,
    )


def _normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.casefold()).strip()


def _confidence(score: float) -> float:
    if score >= 6:
        return 0.95
    if score >= 3:
        return 0.82
    if score >= 2:
        return 0.65
    return 0.45
