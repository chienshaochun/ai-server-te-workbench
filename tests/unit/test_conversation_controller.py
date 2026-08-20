import pytest

from ai_server_te_workbench.conversation import (
    ConversationController,
    SessionOutcome,
    case_record_from_session,
)
from ai_server_te_workbench.knowledge import CaseOutcome, SymptomCategory
from ai_server_te_workbench.knowledge.generic_flows import START_STEPS, generic_flow_steps


def start(category: SymptomCategory):
    return ConversationController().start(
        "AI Server X1",
        "測試問題",
        category,
        0.82,
    )


def answer_sequence(session, *answers: str):
    controller = ConversationController()
    for answer in answers:
        session = controller.answer(session, answer)
    return session


def test_every_supported_category_has_a_valid_start_step() -> None:
    controller = ConversationController()
    catalog_ids = {step.id for step in generic_flow_steps()}

    assert set(START_STEPS) == set(SymptomCategory)
    assert set(START_STEPS.values()) <= catalog_ids
    for category in SymptomCategory:
        session = start(category)
        assert controller.current_step(session).id == START_STEPS[category]


def test_network_problem_can_resolve_to_station_path_with_traceable_turns() -> None:
    session = answer_sequence(
        start(SymptomCategory.NETWORK_UNREACHABLE),
        "bmc",
        "yes",
        "yes",
    )

    assert session.outcome is SessionOutcome.RESOLVED
    assert session.resolution_id == "restore_station_network_path"
    assert len(session.transcript) == 3
    assert [turn.sequence for turn in session.transcript] == [1, 2, 3]
    assert len({turn.evidence_id for turn in session.transcript}) == 3


def test_network_problem_following_dut_is_escalated_not_called_hardware_failure() -> None:
    session = answer_sequence(
        start(SymptomCategory.NETWORK_UNREACHABLE),
        "bmc",
        "yes",
        "no",
        "yes",
    )

    assert session.outcome is SessionOutcome.ESCALATED
    assert session.resolution_id is None
    assert "Station path 正常" in session.transcript[-1].observation_zh


def test_one_unit_flow_uses_golden_sample_before_station_resolution() -> None:
    session = answer_sequence(
        start(SymptomCategory.ONE_UNIT_ONLY),
        "yes",
        "no",
        "yes",
    )

    assert session.outcome is SessionOutcome.RESOLVED
    assert session.resolution_id == "repair_station_path"
    assert session.transcript[1].step_id == "unit_golden"


def test_firmware_flow_resolves_only_after_retest() -> None:
    session = answer_sequence(
        start(SymptomCategory.FIRMWARE_MISMATCH),
        "no",
        "yes",
    )

    assert session.outcome is SessionOutcome.RESOLVED
    assert session.resolution_id == "restore_approved_firmware"
    assert session.transcript[-1].step_id == "fw_retest"


def test_gpu_physical_step_forces_safety_note_into_transcript() -> None:
    session = start(SymptomCategory.GPU_MISSING)
    session = answer_sequence(session, "yes")
    physical_step = ConversationController().current_step(session)

    assert physical_step.id == "gpu_physical"
    assert "安全斷電" in physical_step.safety_note_zh

    session = answer_sequence(session, "yes", "yes")
    assert session.outcome is SessionOutcome.RESOLVED
    assert "ESD" in session.transcript[1].safety_note_zh


def test_temperature_flow_can_resolve_after_airflow_retest() -> None:
    session = answer_sequence(
        start(SymptomCategory.TEMPERATURE_HIGH),
        "yes",
        "yes",
        "yes",
    )

    assert session.outcome is SessionOutcome.RESOLVED
    assert session.resolution_id == "restore_airflow"


def test_unknown_problem_routes_only_after_explicit_category_confirmation() -> None:
    session = start(SymptomCategory.UNKNOWN)
    session = answer_sequence(session, "network")

    assert session.outcome is SessionOutcome.ACTIVE
    assert session.symptom_category is SymptomCategory.NETWORK_UNREACHABLE
    assert session.current_step_id == "net_scope"
    assert "使用者確認" in session.transcript[0].observation_zh


def test_invalid_answer_does_not_mutate_existing_session() -> None:
    controller = ConversationController()
    session = start(SymptomCategory.NETWORK_UNREACHABLE)

    with pytest.raises(ValueError, match="answer_id"):
        controller.answer(session, "maybe")

    assert session.transcript == ()
    assert session.current_step_id == "net_scope"


def test_terminal_session_rejects_additional_answer() -> None:
    controller = ConversationController()
    session = answer_sequence(start(SymptomCategory.NETWORK_UNREACHABLE), "unknown")

    assert session.outcome is SessionOutcome.UNRESOLVED
    with pytest.raises(ValueError, match="terminal"):
        controller.answer(session, "yes")


def test_terminal_session_becomes_anonymized_case_record_without_raw_problem() -> None:
    session = answer_sequence(
        start(SymptomCategory.NETWORK_UNREACHABLE),
        "os",
        "yes",
        "yes",
    )

    record = case_record_from_session(session)

    assert record.model_family == "AI_SERVER_X1"
    assert record.symptom_category is SymptomCategory.NETWORK_UNREACHABLE
    assert record.outcome is CaseOutcome.RESOLVED
    assert record.resolution_id == "restore_station_network_path"
    assert record.synthetic is False
    assert not hasattr(record, "raw_problem")


def test_active_session_cannot_be_counted_as_completed_case() -> None:
    with pytest.raises(ValueError, match="active"):
        case_record_from_session(start(SymptomCategory.GPU_MISSING))
