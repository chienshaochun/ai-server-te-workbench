import pytest

from ai_server_te_workbench.conversation import (
    common_issues_for_model,
    normalize_model_family,
    summarize_case_history,
)
from ai_server_te_workbench.knowledge import (
    CaseOutcome,
    CaseRecord,
    SymptomCategory,
    synthetic_case_history,
)
from ai_server_te_workbench.knowledge.generic_ai_server import GENERIC_MODEL_FAMILY


def summary_by_category(category: SymptomCategory):
    return next(
        summary
        for summary in summarize_case_history(synthetic_case_history(), GENERIC_MODEL_FAMILY)
        if summary.symptom_category is category
    )


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("AI Server X1", "AI_SERVER_X1"),
        (" Dell PowerEdge-R760xa ", "DELL_POWEREDGE_R760XA"),
        ("HGX_B200", "HGX_B200"),
    ],
)
def test_model_family_normalization_is_stable(model: str, expected: str) -> None:
    assert normalize_model_family(model) == expected


def test_network_history_exposes_case_counts_and_resolution_ratio() -> None:
    summary = summary_by_category(SymptomCategory.NETWORK_UNREACHABLE)

    assert summary.similar_case_count == 6
    assert summary.resolved_case_count == 5
    assert summary.dominant_resolution_id == "restore_station_network_path"
    assert summary.dominant_resolution_count == 4
    assert summary.resolution_consistency == pytest.approx(0.8)
    assert summary.is_common is True
    assert summary.synthetic is True


def test_frequency_alone_does_not_make_under_sampled_issue_common() -> None:
    summary = summary_by_category(SymptomCategory.GPU_MISSING)

    assert summary.resolved_case_count == 2
    assert summary.resolution_consistency == 1.0
    assert summary.is_common is False


def test_common_dropdown_contains_only_threshold_qualified_categories() -> None:
    summaries = common_issues_for_model(synthetic_case_history(), "Unlisted Server 9000")

    assert [item.symptom_category for item in summaries] == [
        SymptomCategory.NETWORK_UNREACHABLE,
        SymptomCategory.ONE_UNIT_ONLY,
        SymptomCategory.FIRMWARE_MISMATCH,
        SymptomCategory.TEMPERATURE_HIGH,
    ]
    assert all(item.model_family == GENERIC_MODEL_FAMILY for item in summaries)


def test_model_without_history_falls_back_to_labeled_generic_synthetic_data() -> None:
    summaries = common_issues_for_model(synthetic_case_history(), "Vendor Model 123")

    assert summaries
    assert all(item.synthetic for item in summaries)
    assert all(item.model_family == GENERIC_MODEL_FAMILY for item in summaries)


def test_exact_model_history_is_preferred_over_generic_fallback() -> None:
    exact_records = tuple(
        CaseRecord(
            model_family="MODEL_X",
            symptom_category=SymptomCategory.GPU_MISSING,
            resolution_id="model_x_gpu_fix",
            outcome=CaseOutcome.RESOLVED,
            synthetic=False,
        )
        for _ in range(3)
    )
    records = (*synthetic_case_history(), *exact_records)

    summaries = common_issues_for_model(records, "Model X")

    assert len(summaries) == 1
    assert summaries[0].model_family == "MODEL_X"
    assert summaries[0].symptom_category is SymptomCategory.GPU_MISSING
    assert summaries[0].synthetic is False


def test_common_thresholds_are_explicitly_configurable() -> None:
    summaries = summarize_case_history(
        synthetic_case_history(),
        GENERIC_MODEL_FAMILY,
        minimum_resolved=2,
        minimum_consistency=1.0,
    )
    gpu = next(item for item in summaries if item.symptom_category is SymptomCategory.GPU_MISSING)

    assert gpu.is_common is True


def test_resolved_case_requires_resolution_identifier() -> None:
    with pytest.raises(ValueError, match="resolution_id"):
        CaseRecord(
            model_family="MODEL_X",
            symptom_category=SymptomCategory.UNKNOWN,
            resolution_id=None,
            outcome=CaseOutcome.RESOLVED,
        )


@pytest.mark.parametrize("model", ["", "---", "   "])
def test_model_family_requires_letters_or_numbers(model: str) -> None:
    with pytest.raises(ValueError):
        normalize_model_family(model)
