import pytest

from ai_server_te_workbench.knowledge import (
    SymptomCategory,
    match_case_patterns,
    synthetic_case_patterns,
)


def test_library_represents_72_transparent_synthetic_cases() -> None:
    patterns = synthetic_case_patterns()

    assert len(patterns) == 12
    assert sum(pattern.case_count for pattern in patterns) == 72
    assert len({pattern.id for pattern in patterns}) == len(patterns)
    assert all(pattern.resolved_count <= pattern.case_count for pattern in patterns)


def test_library_covers_every_supported_non_unknown_category() -> None:
    categories = {pattern.symptom_category for pattern in synthetic_case_patterns()}

    assert categories == set(SymptomCategory) - {SymptomCategory.UNKNOWN}


def test_specific_bmc_description_returns_relevant_top_three_patterns() -> None:
    matches = match_case_patterns("同一個 port 其他機器正常，只有這台 BMC timeout")

    assert len(matches) == 3
    assert matches[0].pattern.id == "bmc_single_dut_timeout"
    assert matches[0].score > matches[1].score
    assert "bmc" in matches[0].matched_terms


def test_cross_station_description_prioritizes_dut_following_pattern() -> None:
    matches = match_case_patterns("這台不行但另一台可以，換 station 還是一樣")

    assert matches[0].pattern.id == "failure_follows_dut"
    assert matches[0].pattern.symptom_category is SymptomCategory.ONE_UNIT_ONLY


def test_pattern_match_limit_is_validated() -> None:
    with pytest.raises(ValueError, match="positive"):
        match_case_patterns("網路連不上", limit=0)
