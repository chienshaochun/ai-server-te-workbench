import json
from types import SimpleNamespace

import pytest

from ai_server_te_workbench.conversation import ConversationController
from ai_server_te_workbench.knowledge import SymptomCategory, match_case_patterns
from ai_server_te_workbench.llm import (
    AdviceSource,
    HybridTriageService,
    LLMServiceError,
    OpenAIAdvisor,
    TriageAdvice,
    deterministic_triage,
)


class FakeResponses:
    def __init__(self, payload: dict[str, object], *, model: str = "test-model") -> None:
        self.payload = payload
        self.model = model
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.payload), model=self.model)


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def valid_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "symptom_category": "network_unreachable",
        "confidence": 0.88,
        "summary_zh": "同一網路路徑只有這台 BMC 無法連線。",
        "observations": ["同一個 port", "其他設備正常"],
        "missing_information": ["是否已交換網路線"],
        "recommended_step_id": "net_scope",
        "reason_zh": "先區分 DUT 與 station network path。",
        "safety_warning_zh": "",
    }
    payload.update(overrides)
    return payload


def test_deterministic_triage_remains_available_without_llm() -> None:
    advice = HybridTriageService().analyze(
        "Model X", "這台可以但另一台不行", use_llm=True
    )

    assert advice.source is AdviceSource.DETERMINISTIC
    assert advice.category is SymptomCategory.ONE_UNIT_ONLY
    assert advice.recommended_step_id == "unit_baseline"


def test_openai_advisor_uses_responses_strict_schema_and_disables_storage() -> None:
    responses = FakeResponses(valid_payload())
    advisor = OpenAIAdvisor("test-key", client=FakeClient(responses))

    advice = advisor.analyze(
        "Model X",
        "同一個 port 其他機器正常，只有這台 BMC timeout",
        match_case_patterns("同一個 port 其他機器正常，只有這台 BMC timeout"),
    )

    assert advice.source is AdviceSource.OPENAI
    assert advice.model == "test-model"
    assert advice.category is SymptomCategory.NETWORK_UNREACHABLE
    request = responses.calls[0]
    assert request["store"] is False
    assert request["reasoning"] == {"effort": "none"}
    assert request["text"]["format"]["strict"] is True
    assert request["text"]["format"]["type"] == "json_schema"
    assert "test-key" not in json.dumps(request, ensure_ascii=False)


def test_mismatched_ai_route_is_rejected_and_hybrid_falls_back() -> None:
    responses = FakeResponses(valid_payload(recommended_step_id="gpu_enum"))
    advisor = OpenAIAdvisor("test-key", client=FakeClient(responses))

    advice = HybridTriageService(advisor).analyze(
        "Model X", "這台 BMC 網路連不上", use_llm=True
    )

    assert advice.source is AdviceSource.DETERMINISTIC
    assert advice.category is SymptomCategory.NETWORK_UNREACHABLE
    assert advice.recommended_step_id == "net_scope"
    assert advice.fallback_reason is not None


def test_provider_failure_never_breaks_the_troubleshooting_entry() -> None:
    class FailingAdvisor:
        def analyze(self, server_model, problem, patterns):
            raise LLMServiceError("temporary failure")

    advice = HybridTriageService(FailingAdvisor()).analyze(
        "Model X", "firmware version 不符", use_llm=True
    )

    assert advice.source is AdviceSource.DETERMINISTIC
    assert advice.category is SymptomCategory.FIRMWARE_MISMATCH
    assert advice.fallback_reason == "temporary failure"


def test_step_question_answer_cannot_route_to_a_different_step() -> None:
    responses = FakeResponses(
        {
            "answer_zh": "先比較同一路徑上的 Golden Sample。",
            "recommended_next_action_zh": "執行目前畫面上的檢查。",
            "safety_warning_zh": "",
            "related_step_id": "gpu_enum",
        }
    )
    advisor = OpenAIAdvisor("test-key", client=FakeClient(responses))
    controller = ConversationController()
    session = controller.start(
        "Model X",
        "BMC 網路連不上",
        SymptomCategory.NETWORK_UNREACHABLE,
        0.9,
    )
    step = controller.current_step(session)
    assert step is not None

    with pytest.raises(LLMServiceError, match="超出"):
        advisor.answer_question(session, step, "為什麼要做這個測試？")


def test_triage_advice_validates_confidence_and_openai_model_metadata() -> None:
    with pytest.raises(ValueError, match="between"):
        TriageAdvice(
            category=SymptomCategory.UNKNOWN,
            confidence=1.5,
            summary_zh="待確認",
            observations=(),
            missing_information=(),
            recommended_step_id="unknown_category",
            reason_zh="資料不足",
            safety_warning_zh=None,
            source=AdviceSource.DETERMINISTIC,
        )

    advice = deterministic_triage("完全無法辨識的新現象")
    assert advice.category is SymptomCategory.UNKNOWN
    assert advice.recommended_step_id == "unknown_category"
