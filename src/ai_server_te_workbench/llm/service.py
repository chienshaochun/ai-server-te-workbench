"""Hybrid triage service that fails safely to deterministic matching."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ai_server_te_workbench.conversation import match_issue
from ai_server_te_workbench.knowledge import PatternMatch, SymptomCategory, match_case_patterns
from ai_server_te_workbench.knowledge.generic_ai_server import generic_knowledge_entries
from ai_server_te_workbench.knowledge.generic_flows import START_STEPS
from ai_server_te_workbench.llm.models import AdviceSource, TriageAdvice


class LLMServiceError(RuntimeError):
    """Expected provider, parsing, or contract failure safe for fallback."""


class TriageAdvisor(Protocol):
    def analyze(
        self,
        server_model: str,
        problem: str,
        patterns: tuple[PatternMatch, ...],
    ) -> TriageAdvice: ...


class HybridTriageService:
    def __init__(self, advisor: TriageAdvisor | None = None) -> None:
        self._advisor = advisor

    def analyze(
        self,
        server_model: str,
        problem: str,
        *,
        use_llm: bool,
    ) -> TriageAdvice:
        fallback = deterministic_triage(problem)
        if not use_llm or self._advisor is None:
            return fallback
        try:
            advice = self._advisor.analyze(
                server_model,
                problem,
                match_case_patterns(problem),
            )
            _validate_route(advice)
            return advice
        except LLMServiceError as error:
            return replace(fallback, fallback_reason=str(error))


def deterministic_triage(problem: str) -> TriageAdvice:
    issue_match = match_issue(problem)
    category = SymptomCategory.UNKNOWN if issue_match.needs_confirmation else issue_match.category
    entry_by_category = {entry.category: entry for entry in generic_knowledge_entries()}
    if category is SymptomCategory.UNKNOWN:
        summary = "目前文字證據不足，先由使用者確認最接近的症狀類型。"
        missing = ("請確認問題最接近網路、單機差異、韌體、GPU 或溫度哪一類。",)
    else:
        summary = entry_by_category[category].description_zh
        missing = ()
    return TriageAdvice(
        category=category,
        confidence=issue_match.confidence,
        summary_zh=summary,
        observations=issue_match.matched_terms,
        missing_information=missing,
        recommended_step_id=START_STEPS[category],
        reason_zh="依本地 knowledge pack 的關鍵字與信心門檻選擇入口。",
        safety_warning_zh=None,
        source=AdviceSource.DETERMINISTIC,
    )


def validate_llm_route(advice: TriageAdvice) -> None:
    """Validate that AI output can only select an approved entry step."""

    _validate_route(advice)


def _validate_route(advice: TriageAdvice) -> None:
    expected_step = START_STEPS[advice.category]
    if advice.recommended_step_id != expected_step:
        raise LLMServiceError("AI 回傳的檢查入口不在核准路徑中，已改用 deterministic fallback。")
