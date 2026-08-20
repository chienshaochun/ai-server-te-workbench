import pytest

from ai_server_te_workbench.conversation import match_issue
from ai_server_te_workbench.knowledge import KnowledgeEntry, SymptomCategory


@pytest.mark.parametrize(
    ("problem", "expected_category"),
    [
        ("這台 server 網路連不上", SymptomCategory.NETWORK_UNREACHABLE),
        ("BMC is network unreachable", SymptomCategory.NETWORK_UNREACHABLE),
        ("這台可以但另一台不行", SymptomCategory.ONE_UNIT_ONLY),
        ("firmware version 不符", SymptomCategory.FIRMWARE_MISMATCH),
        ("GPU 少一張，系統看不到", SymptomCategory.GPU_MISSING),
        ("CPU 溫度太高", SymptomCategory.TEMPERATURE_HIGH),
    ],
)
def test_problem_text_maps_to_supported_conversation_entry(
    problem: str, expected_category: SymptomCategory
) -> None:
    match = match_issue(problem)

    assert match.category is expected_category
    assert match.needs_confirmation is False
    assert match.matched_terms


def test_comparative_dut_clues_outrank_generic_network_word() -> None:
    match = match_issue("這台可以，另一台不行，而且兩台都接同一個 network")

    assert match.category is SymptomCategory.ONE_UNIT_ONLY
    assert match.confidence == 0.95
    assert SymptomCategory.NETWORK_UNREACHABLE in match.alternatives


def test_ambiguous_weak_keywords_require_user_confirmation() -> None:
    match = match_issue("firmware network 問題")

    assert match.needs_confirmation is True
    assert match.confidence < 0.60
    assert match.alternatives


def test_unrecognized_problem_never_invents_a_category() -> None:
    match = match_issue("開機後呈現一個從未定義的奇怪狀態")

    assert match.category is SymptomCategory.UNKNOWN
    assert match.confidence == 0.0
    assert match.needs_confirmation is True
    assert match.matched_terms == ()


@pytest.mark.parametrize("problem", ["", "   "])
def test_empty_problem_is_rejected(problem: str) -> None:
    with pytest.raises(ValueError, match="empty"):
        match_issue(problem)


def test_problem_length_is_bounded() -> None:
    with pytest.raises(ValueError, match="1000"):
        match_issue("x" * 1001)


def test_custom_knowledge_entries_are_validated_and_supported() -> None:
    entry = KnowledgeEntry(
        category=SymptomCategory.NETWORK_UNREACHABLE,
        title_zh="自訂網路入口",
        description_zh="測試用自訂入口",
        strong_keywords=("custom-link-down",),
    )

    match = match_issue("custom-link-down", entries=(entry,))

    assert match.category is SymptomCategory.NETWORK_UNREACHABLE
    assert match.confidence == 0.82


def test_duplicate_keywords_in_one_entry_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        KnowledgeEntry(
            category=SymptomCategory.GPU_MISSING,
            title_zh="GPU",
            description_zh="GPU test",
            strong_keywords=("GPU",),
            weak_keywords=("gpu",),
        )
