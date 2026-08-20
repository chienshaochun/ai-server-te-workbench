import pytest

from ai_server_te_workbench.knowledge import (
    SymptomCategory,
    match_case_patterns,
    synthetic_case_patterns,
)


def test_library_represents_138_transparent_synthetic_cases() -> None:
    patterns = synthetic_case_patterns()

    assert len(patterns) == 24
    assert sum(pattern.case_count for pattern in patterns) == 138
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


@pytest.mark.parametrize(
    ("problem", "pattern_id"),
    [
        ("server 按下 power button 完全不能上電，沒有 LED", "no_power_bad_pdu_path"),
        ("BIOS 顯示記憶體少一條，容量低於 approved BOM", "dimm_inventory_missing"),
        ("RAID 顯示 degraded 而且 member disk 狀態異常", "raid_virtual_disk_degraded"),
        ("換了 Golden Sample 還是 PXE boot failure", "pxe_fails_all_units"),
    ],
)
def test_new_hardware_and_boot_descriptions_match_expanded_patterns(
    problem: str, pattern_id: str
) -> None:
    assert match_case_patterns(problem)[0].pattern.id == pattern_id


def test_pattern_match_limit_is_validated() -> None:
    with pytest.raises(ValueError, match="positive"):
        match_case_patterns("網路連不上", limit=0)
