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
        KnowledgeEntry(
            category=SymptomCategory.POWER_OR_POST_FAILURE,
            title_zh="無法上電或卡在 POST",
            description_zh="先區分供電路徑、電源狀態與 POST 階段，再收集 BMC／POST evidence。",
            strong_keywords=(
                "無法上電",
                "不能開機",
                "按電源沒反應",
                "卡在post",
                "卡在 post",
                "no power",
                "power on failure",
                "stuck at post",
            ),
            weak_keywords=("上電", "電源", "power", "post"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.MEMORY_ERROR,
            title_zh="記憶體容量缺少或 ECC 錯誤",
            description_zh="核對 DIMM inventory、BMC memory log 與錯誤是否跟著 DIMM 或 slot。",
            strong_keywords=(
                "記憶體少一條",
                "記憶體容量不符",
                "dimm missing",
                "dimm 不見",
                "ecc error",
                "ecc 錯誤",
                "uncorrectable memory",
            ),
            weak_keywords=("記憶體", "memory", "dimm", "ecc"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.STORAGE_FAILURE,
            title_zh="NVMe／磁碟未辨識或 RAID 降級",
            description_zh="核對 storage inventory、RAID 狀態與裝置錯誤，再以核准方式交換路徑。",
            strong_keywords=(
                "nvme 不見",
                "硬碟不見",
                "磁碟未辨識",
                "raid degraded",
                "raid 降級",
                "disk missing",
                "storage timeout",
            ),
            weak_keywords=("nvme", "硬碟", "磁碟", "storage", "raid", "disk"),
        ),
        KnowledgeEntry(
            category=SymptomCategory.OS_BOOT_FAILURE,
            title_zh="OS／PXE 無法開機",
            description_zh="先確認 boot target、PXE／image baseline，再區分部署環境與 DUT 問題。",
            strong_keywords=(
                "os 無法開機",
                "作業系統進不去",
                "pxe 失敗",
                "pxe boot failure",
                "找不到開機裝置",
                "no boot device",
                "kernel panic",
            ),
            weak_keywords=("boot", "pxe", "os", "kernel"),
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
