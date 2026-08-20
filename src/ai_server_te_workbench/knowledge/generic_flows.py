"""Conservative, vendor-neutral guided troubleshooting flows."""

from ai_server_te_workbench.conversation.models import (
    DiagnosticStep,
    SessionOutcome,
    StepBranch,
)
from ai_server_te_workbench.knowledge.models import SymptomCategory as C


def generic_flow_steps() -> tuple[DiagnosticStep, ...]:
    return (
        _step(
            "net_scope",
            C.NETWORK_UNREACHABLE,
            "要排查哪一種連線？",
            "確認問題發生於 BMC 管理網路或 OS data network。",
            "network_scope",
            [
                _next("bmc", "BMC 管理網路", "問題位於 BMC 管理介面。", "net_golden"),
                _next("os", "OS data network", "問題位於 OS data network。", "net_golden"),
                _end("unknown", "不確定", "目前無法確認受影響介面。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "net_golden",
            C.NETWORK_UNREACHABLE,
            "同一 cable 與 switch port 接已知正常機時可以連線嗎？",
            "使用 Golden Sample 驗證原 station network path。",
            "golden_network",
            [
                _next("yes", "可以", "Golden Sample 在原 network path 可連線。", "net_swap"),
                _next(
                    "no",
                    "不可以",
                    "Golden Sample 在原 network path 也無法連線。",
                    "net_station_retest",
                ),
                _end(
                    "unknown",
                    "尚未測試",
                    "尚未完成 Golden Sample 驗證。",
                    SessionOutcome.UNRESOLVED,
                ),
            ],
        ),
        _step(
            "net_swap",
            C.NETWORK_UNREACHABLE,
            "問題機改接 known-good cable／port 後可以連線嗎？",
            "將 DUT 接到已知正常的 cable 與 switch port。",
            "dut_network_swap",
            [
                _end(
                    "yes",
                    "可以",
                    "問題未跟著 DUT，原 station path 需處理。",
                    SessionOutcome.RESOLVED,
                    "restore_station_network_path",
                ),
                _next("no", "仍不可以", "問題跟著 DUT 到 known-good network path。", "net_config"),
                _end(
                    "unknown", "尚未測試", "尚未完成 DUT network swap。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _step(
            "net_config",
            C.NETWORK_UNREACHABLE,
            "Link state、IP、VLAN 與 gateway 都符合 approved baseline 嗎？",
            "核對 link state 與核准的 network configuration；不要輸入密碼。",
            "network_config",
            [
                _end(
                    "yes",
                    "全部符合",
                    "Station path 正常且設定符合，但 DUT 仍不可達。",
                    SessionOutcome.ESCALATED,
                ),
                _next(
                    "no",
                    "有不一致",
                    "發現 link 或 network configuration 不一致。",
                    "net_config_retest",
                ),
                _end(
                    "unknown",
                    "無法確認",
                    "缺少 network configuration evidence。",
                    SessionOutcome.UNRESOLVED,
                ),
            ],
        ),
        _step(
            "net_config_retest",
            C.NETWORK_UNREACHABLE,
            "修正設定後連線恢復嗎？",
            "依 approved baseline 修正設定後重新測試。",
            "network_retest",
            [
                _end(
                    "yes",
                    "已恢復",
                    "修正 network configuration 後恢復。",
                    SessionOutcome.RESOLVED,
                    "correct_network_config",
                ),
                _end(
                    "no",
                    "仍失敗",
                    "修正設定後仍不可達，需要收集 BMC／OS logs。",
                    SessionOutcome.ESCALATED,
                ),
                _end("unknown", "尚未重測", "尚未完成設定修正後重測。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "net_station_retest",
            C.NETWORK_UNREACHABLE,
            "修復 cable／port／VLAN path 後 Golden Sample 可以連線嗎？",
            "修復 station network path，再以 Golden Sample 重測。",
            "station_network_retest",
            [
                _end(
                    "yes",
                    "可以",
                    "修復 station network path 後 Golden Sample 恢復。",
                    SessionOutcome.RESOLVED,
                    "restore_station_network_path",
                ),
                _end(
                    "no",
                    "仍不可以",
                    "Station path 修復後 Golden Sample 仍失敗。",
                    SessionOutcome.ESCALATED,
                ),
                _end(
                    "unknown", "尚未重測", "尚未完成 station path 重測。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _step(
            "unit_baseline",
            C.ONE_UNIT_ONLY,
            "兩台是否使用相同 station、test plan、firmware baseline 與 cable path？",
            "先對齊兩台的測試條件，避免比較不同基準。",
            "unit_baseline",
            [
                _next("yes", "相同", "兩台測試條件一致。", "unit_golden"),
                _next("no", "不相同", "兩台測試條件不一致。", "unit_aligned_retest"),
                _end("unknown", "無法確認", "缺少可比較的測試基準。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "unit_aligned_retest",
            C.ONE_UNIT_ONLY,
            "對齊 baseline 後問題仍存在嗎？",
            "對齊 station、test plan、firmware 與 cable 後重測。",
            "aligned_retest",
            [
                _next("yes", "仍存在", "對齊 baseline 後差異仍存在。", "unit_golden"),
                _end(
                    "no",
                    "已消失",
                    "對齊 baseline 後兩台結果一致。",
                    SessionOutcome.RESOLVED,
                    "align_test_baseline",
                ),
                _end(
                    "unknown", "尚未重測", "尚未完成 baseline 對齊重測。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _step(
            "unit_golden",
            C.ONE_UNIT_ONLY,
            "Golden Sample 在失敗機原本的 station 上會通過嗎？",
            "在原 station 執行 Golden Sample，保留相同 test plan。",
            "golden_station",
            [
                _next("yes", "會通過", "Golden Sample 在原 station 通過。", "unit_cross_station"),
                _next("no", "也失敗", "Golden Sample 在原 station 也失敗。", "unit_station_retest"),
                _end(
                    "unknown", "尚未測試", "未完成 Golden Sample 比較。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _step(
            "unit_cross_station",
            C.ONE_UNIT_ONLY,
            "失敗 DUT 移到 known-good station 後仍出現相同問題嗎？",
            "在第二個 ready station 重跑同一 test plan。",
            "cross_station",
            [
                _end("yes", "仍失敗", "相同症狀跟著 DUT 到第二站。", SessionOutcome.ESCALATED),
                _end(
                    "no",
                    "通過",
                    "症狀未跟著 DUT，原 station path 可疑。",
                    SessionOutcome.RESOLVED,
                    "repair_station_path",
                ),
                _end(
                    "unknown", "尚未測試", "未完成 cross-station 比較。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _step(
            "unit_station_retest",
            C.ONE_UNIT_ONLY,
            "修復原 station 後 Golden Sample 會通過嗎？",
            "檢查 fixture、environment 與 test program 後重跑 Golden Sample。",
            "station_retest",
            [
                _end(
                    "yes",
                    "會通過",
                    "修復 station path 後 Golden Sample 通過。",
                    SessionOutcome.RESOLVED,
                    "repair_station_path",
                ),
                _end(
                    "no",
                    "仍失敗",
                    "修復後 Golden Sample 仍失敗，需要升級處理。",
                    SessionOutcome.ESCALATED,
                ),
                _end(
                    "unknown", "尚未重測", "尚未完成 station 修復重測。", SessionOutcome.UNRESOLVED
                ),
            ],
        ),
        _simple_resolution_flow(
            "fw_baseline",
            C.FIRMWARE_MISMATCH,
            "實際版本與 approved firmware baseline／checksum 一致嗎？",
            "核對版本、設定與 image checksum。",
            "firmware_baseline",
            "不一致",
            "一致",
            "fw_retest",
            "restore_approved_firmware",
        ),
        firmware_retest_step(),
        _step(
            "gpu_enum",
            C.GPU_MISSING,
            "Cold restart 後 GPU enumeration 仍少於預期嗎？",
            "依 approved 程序 cold restart，再核對 GPU count 與 power state。",
            "gpu_enumeration",
            [
                _next("yes", "仍缺少", "Cold restart 後 GPU 仍缺少。", "gpu_physical"),
                _end(
                    "no",
                    "已完整",
                    "Cold restart 後 GPU enumeration 恢復。",
                    SessionOutcome.RESOLVED,
                    "recover_gpu_enumeration",
                ),
                _end(
                    "unknown",
                    "尚未確認",
                    "尚未完成 GPU enumeration 重測。",
                    SessionOutcome.UNRESOLVED,
                ),
            ],
        ),
        _step(
            "gpu_physical",
            C.GPU_MISSING,
            "合格人員斷電檢查後，seating 或 power connection 有異常嗎？",
            "安全斷電並由合格人員檢查 GPU seating 與 power connection。",
            "gpu_physical",
            [
                _next("yes", "有異常並已處理", "發現並處理 seating 或 power 異常。", "gpu_retest"),
                _end(
                    "no",
                    "未發現異常",
                    "實體連接未見明顯異常，需要收集 platform logs。",
                    SessionOutcome.ESCALATED,
                ),
                _end("not_done", "未執行", "未執行安全實體檢查。", SessionOutcome.UNRESOLVED),
            ],
            "必須安全斷電、遵守 ESD 規範，並由合格人員執行；本 app 不控制硬體。",
        ),
        _terminal_retest(
            "gpu_retest",
            C.GPU_MISSING,
            "處理後 GPU count 恢復嗎？",
            "重新上電並執行 GPU enumeration test。",
            "gpu_retest",
            "recheck_gpu_power_and_seating",
        ),
        _step(
            "temp_idle",
            C.TEMPERATURE_HIGH,
            "在 approved idle condition 下溫度仍高於上限嗎？",
            "移除非必要 workload，核對 sensor 與 idle temperature。",
            "temperature_idle",
            [
                _next("yes", "仍過高", "Idle condition 下溫度仍超標。", "temp_airflow"),
                _end(
                    "no",
                    "已正常",
                    "移除 workload 後溫度恢復。",
                    SessionOutcome.RESOLVED,
                    "normalize_test_load",
                ),
                _end(
                    "unknown",
                    "無法確認",
                    "缺少 idle temperature evidence。",
                    SessionOutcome.UNRESOLVED,
                ),
            ],
        ),
        _step(
            "temp_airflow",
            C.TEMPERATURE_HIGH,
            "Fan、airflow 或散熱路徑有異常嗎？",
            "由合格人員檢查 fan、airflow obstruction 與 cooling path。",
            "thermal_path",
            [
                _next("yes", "有異常並已處理", "發現並處理 fan 或 airflow 異常。", "temp_retest"),
                _end(
                    "no",
                    "未發現異常",
                    "Airflow 未見異常，需要升級檢查 sensor 或 cooling contact。",
                    SessionOutcome.ESCALATED,
                ),
                _end("not_done", "未執行", "尚未完成安全散熱路徑檢查。", SessionOutcome.UNRESOLVED),
            ],
            "若需開啟機殼，必須安全斷電並由合格人員依 ESD 規範執行。",
        ),
        _terminal_retest(
            "temp_retest",
            C.TEMPERATURE_HIGH,
            "處理後 idle temperature 恢復正常嗎？",
            "重新量測相同 sensor 與 approved idle condition。",
            "temperature_retest",
            "restore_airflow",
        ),
        _step(
            "unknown_category",
            C.UNKNOWN,
            "最接近哪一類現象？",
            "選擇最接近的可驗證 symptom；若皆不符合則轉交。",
            "category_confirmation",
            [
                _route("network", "網路或 BMC 無法連線", C.NETWORK_UNREACHABLE, "net_scope"),
                _route("one_unit", "這台可以但另一台不行", C.ONE_UNIT_ONLY, "unit_baseline"),
                _route("firmware", "Firmware 不一致", C.FIRMWARE_MISMATCH, "fw_baseline"),
                _route("gpu", "GPU 缺少", C.GPU_MISSING, "gpu_enum"),
                _route("temperature", "溫度過高", C.TEMPERATURE_HIGH, "temp_idle"),
                _end(
                    "none", "皆不符合", "現有 knowledge pack 無適合入口。", SessionOutcome.ESCALATED
                ),
            ],
        ),
    )


START_STEPS = {
    C.NETWORK_UNREACHABLE: "net_scope",
    C.ONE_UNIT_ONLY: "unit_baseline",
    C.FIRMWARE_MISMATCH: "fw_baseline",
    C.GPU_MISSING: "gpu_enum",
    C.TEMPERATURE_HIGH: "temp_idle",
    C.UNKNOWN: "unknown_category",
}


def _step(id, category, question, check, tag, branches, safety=None):
    return DiagnosticStep(id, category, question, check, tag, tuple(branches), safety)


def _next(answer, label, observation, next_step):
    return StepBranch(answer, label, observation, next_step_id=next_step)


def _end(answer, label, observation, outcome, resolution=None):
    return StepBranch(answer, label, observation, outcome=outcome, resolution_id=resolution)


def _route(answer, label, category, next_step):
    return StepBranch(
        answer,
        label,
        f"使用者確認為 {category.value}。",
        next_step_id=next_step,
        category_override=category,
    )


def _terminal_retest(id, category, question, check, tag, resolution):
    return _step(
        id,
        category,
        question,
        check,
        tag,
        [
            _end("yes", "已恢復", "處理後重測恢復。", SessionOutcome.RESOLVED, resolution),
            _end("no", "仍異常", "處理後重測仍異常，需要升級。", SessionOutcome.ESCALATED),
            _end("unknown", "尚未重測", "尚未完成處理後重測。", SessionOutcome.UNRESOLVED),
        ],
    )


def _simple_resolution_flow(
    id, category, question, check, tag, negative_label, positive_label, retest_id, resolution
):
    return _step(
        id,
        category,
        question,
        check,
        tag,
        [
            _next("no", negative_label, "Firmware baseline 不一致。", retest_id),
            _end(
                "yes",
                positive_label,
                "Firmware 已符合 baseline，原問題需要其他 evidence。",
                SessionOutcome.ESCALATED,
            ),
            _end(
                "unknown",
                "無法確認",
                "缺少 firmware baseline evidence。",
                SessionOutcome.UNRESOLVED,
            ),
        ],
    )


def firmware_retest_step():
    return _terminal_retest(
        "fw_retest",
        C.FIRMWARE_MISMATCH,
        "恢復 approved firmware 後測試會通過嗎？",
        "依核准流程更新並重跑相同 test plan。",
        "firmware_retest",
        "restore_approved_firmware",
    )
