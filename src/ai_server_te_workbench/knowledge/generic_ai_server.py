"""Generic, non-vendor-specific knowledge used by the public simulator."""

from ai_server_te_workbench.knowledge.models import (
    CaseOutcome,
    CaseRecord,
    KnowledgeEntry,
    SymptomCategory,
)


GENERIC_MODEL_FAMILY = "GENERIC_AI_SERVER"


def generic_knowledge_entries() -> tuple[KnowledgeEntry, ...]:
    return (
        KnowledgeEntry(
            category=SymptomCategory.ONE_UNIT_ONLY,
            title_zh="這台可以，但另一台不行",
            description_zh="用 Golden Sample 與跨站交換確認問題跟著 DUT 或 station。",
            strong_keywords=(
                "這台可以",
                "另一台不行",
                "一台可以另一台不行",
                "one unit works",
                "another unit fails",
            ),
            weak_keywords=("另一台", "golden sample", "只有一台"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.NETWORK_UNREACHABLE,
            title_zh="網路或 BMC 無法連線",
            description_zh="分辨 DUT network path、BMC service 與 station network path。",
            strong_keywords=(
                "網路連不上",
                "無法連線",
                "ping不到",
                "ping 不到",
                "network unreachable",
                "cannot connect",
                "bmc unreachable",
            ),
            weak_keywords=("網路", "network", "bmc", "timeout"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.FIRMWARE_MISMATCH,
            title_zh="Firmware 版本或設定不一致",
            description_zh="核對 approved baseline、image checksum 與更新流程。",
            strong_keywords=(
                "firmware不一致",
                "firmware 不一致",
                "韌體不一致",
                "版本不符",
                "firmware version 不符",
                "firmware version mismatch",
                "firmware mismatch",
                "wrong firmware",
            ),
            weak_keywords=("firmware", "韌體", "版本"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.GPU_MISSING,
            title_zh="GPU 未被完整辨識",
            description_zh="先確認 enumeration 與 power state，再進行安全實體檢查。",
            strong_keywords=(
                "gpu少一張",
                "gpu 少一張",
                "gpu不見",
                "gpu 不見",
                "gpu missing",
                "gpu not detected",
            ),
            weak_keywords=("gpu", "顯示卡", "加速卡"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.TEMPERATURE_HIGH,
            title_zh="溫度過高",
            description_zh="確認 sensor、load、fan、airflow 與 cooling contact。",
            strong_keywords=(
                "溫度太高",
                "溫度過高",
                "過熱",
                "temperature high",
                "overheating",
            ),
            weak_keywords=("溫度", "temperature", "thermal", "風扇"),
        ),
    )


def synthetic_case_history() -> tuple[CaseRecord, ...]:
    records: list[CaseRecord] = []
    records.extend(
        _records(
            SymptomCategory.NETWORK_UNREACHABLE,
            "restore_station_network_path",
            4,
        )
    )
    records.extend(_records(SymptomCategory.NETWORK_UNREACHABLE, "correct_bmc_config", 1))
    records.append(_unresolved(SymptomCategory.NETWORK_UNREACHABLE))

    records.extend(_records(SymptomCategory.ONE_UNIT_ONLY, "isolate_dut_with_swap", 4))
    records.extend(_records(SymptomCategory.ONE_UNIT_ONLY, "repair_station_path", 1))

    records.extend(_records(SymptomCategory.FIRMWARE_MISMATCH, "restore_approved_firmware", 3))
    records.extend(_records(SymptomCategory.GPU_MISSING, "recheck_gpu_power_and_seating", 2))
    records.extend(_records(SymptomCategory.TEMPERATURE_HIGH, "restore_airflow", 3))
    records.append(_unresolved(SymptomCategory.TEMPERATURE_HIGH))
    records.append(
        CaseRecord(
            model_family=GENERIC_MODEL_FAMILY,
            symptom_category=SymptomCategory.UNKNOWN,
            resolution_id=None,
            outcome=CaseOutcome.ESCALATED,
        )
    )
    return tuple(records)


def _records(category: SymptomCategory, resolution_id: str, count: int) -> tuple[CaseRecord, ...]:
    return tuple(
        CaseRecord(
            model_family=GENERIC_MODEL_FAMILY,
            symptom_category=category,
            resolution_id=resolution_id,
            outcome=CaseOutcome.RESOLVED,
        )
        for _ in range(count)
    )


def _unresolved(category: SymptomCategory) -> CaseRecord:
    return CaseRecord(
        model_family=GENERIC_MODEL_FAMILY,
        symptom_category=category,
        resolution_id=None,
        outcome=CaseOutcome.UNRESOLVED,
    )
