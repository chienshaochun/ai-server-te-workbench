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
            "power_scope",
            C.POWER_OR_POST_FAILURE,
            "目前最接近哪一種電源或 POST 現象？",
            "觀察 power LED、PSU LED、風扇與最後可見的 POST code；不要拆機。",
            "power_scope",
            [
                _next("no_power", "按電源完全沒反應", "DUT 沒有可見上電反應。", "power_source"),
                _next("post", "有上電但卡在 POST", "DUT 已上電但 POST 未完成。", "post_baseline"),
                _next("shutdown", "上電後自行關機", "DUT 上電後非預期關機。", "power_source"),
                _end("unknown", "無法確認", "缺少 power／POST evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "power_source",
            C.POWER_OR_POST_FAILURE,
            "AC／PDU／power cable 與 PSU LED 在 Golden Sample 上都正常嗎？",
            "不開機殼，交換 approved cable／PDU outlet 並比較 PSU LED。",
            "power_source",
            [
                _end(
                    "yes",
                    "外部供電正常",
                    "Golden Sample 在相同外部供電路徑正常，但 DUT 仍異常。",
                    SessionOutcome.ESCALATED,
                ),
                _next(
                    "no",
                    "外部供電異常並已處理",
                    "發現 cable／PDU path 異常並完成核准處理。",
                    "power_retest",
                ),
                _end("unknown", "尚未測試", "尚未完成外部供電 A/B 驗證。", SessionOutcome.UNRESOLVED),
            ],
            "不得開啟 PSU 或帶電插拔內部元件；只執行現場核准的外部路徑交換。",
        ),
        _terminal_retest(
            "power_retest",
            C.POWER_OR_POST_FAILURE,
            "修復外部供電路徑後可正常上電嗎？",
            "以相同 test plan 重新上電並記錄 PSU／power LED。",
            "power_retest",
            "restore_external_power_path",
        ),
        _step(
            "post_baseline",
            C.POWER_OR_POST_FAILURE,
            "POST code、硬體配置與 approved baseline 是否一致？",
            "記錄最後 POST code，核對 approved BOM、firmware 與測試配置。",
            "post_baseline",
            [
                _next(
                    "no",
                    "配置不一致並已修正",
                    "發現測試配置或 baseline 不一致並完成核准修正。",
                    "post_retest",
                ),
                _end(
                    "yes",
                    "配置一致但仍卡住",
                    "POST 仍卡住且 baseline 一致，需要攜帶 POST／BMC logs 升級。",
                    SessionOutcome.ESCALATED,
                ),
                _end("unknown", "無法確認", "缺少 POST code 或 baseline evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _terminal_retest(
            "post_retest",
            C.POWER_OR_POST_FAILURE,
            "對齊 approved baseline 後 POST 可以完成嗎？",
            "重新上電並保留相同 POST code 與 BMC log 觀察方式。",
            "post_retest",
            "align_post_baseline",
        ),
        _step(
            "memory_evidence",
            C.MEMORY_ERROR,
            "Cold restart 後 DIMM inventory 或 ECC error 仍異常嗎？",
            "核對 BIOS／BMC memory inventory、容量與 ECC log，不先拆機。",
            "memory_inventory",
            [
                _next("yes", "仍異常", "Cold restart 後 memory evidence 仍異常。", "memory_baseline"),
                _end(
                    "no",
                    "已恢復",
                    "Cold restart 後 memory inventory 與 ECC 狀態恢復。",
                    SessionOutcome.RESOLVED,
                    "recover_memory_inventory",
                ),
                _end("unknown", "無法確認", "缺少 DIMM inventory 或 ECC evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "memory_baseline",
            C.MEMORY_ERROR,
            "DIMM BOM、插槽規則與 firmware baseline 都符合 approved configuration 嗎？",
            "比對 DIMM part／容量、population rule、BIOS 與 BMC baseline。",
            "memory_baseline",
            [
                _next(
                    "no",
                    "不一致並已對齊",
                    "發現 memory configuration 不一致並完成核准調整。",
                    "memory_retest",
                ),
                _next("yes", "全部符合", "Memory configuration 符合 baseline。", "memory_physical"),
                _end("unknown", "無法確認", "缺少 memory BOM 或 baseline evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "memory_physical",
            C.MEMORY_ERROR,
            "合格人員斷電檢查後，DIMM seating 或 slot path 有可處理異常嗎？",
            "安全斷電後依核准程序檢查 seating；不得自行更換未核准零件。",
            "memory_physical",
            [
                _next(
                    "yes",
                    "有異常並已處理",
                    "發現並處理 DIMM seating 或連接異常。",
                    "memory_retest",
                ),
                _end(
                    "no",
                    "未發現異常",
                    "Configuration 與 seating 無明顯異常，需要攜帶 ECC／BMC logs 升級。",
                    SessionOutcome.ESCALATED,
                ),
                _end("not_done", "未執行", "未完成安全實體檢查。", SessionOutcome.UNRESOLVED),
            ],
            "必須安全斷電、遵守 ESD 規範，並由合格人員依核准程序執行。",
        ),
        _terminal_retest(
            "memory_retest",
            C.MEMORY_ERROR,
            "處理後 DIMM inventory 與 ECC test 都恢復嗎？",
            "重新上電並執行相同 memory inventory／ECC test。",
            "memory_retest",
            "restore_memory_configuration",
        ),
        _step(
            "storage_scope",
            C.STORAGE_FAILURE,
            "目前最接近哪一種 storage 現象？",
            "區分裝置未辨識、RAID degraded 與 I/O timeout。",
            "storage_scope",
            [
                _next("missing", "NVMe／磁碟未辨識", "Storage device 未出現在 inventory。", "storage_baseline"),
                _next("raid", "RAID degraded", "RAID virtual disk 或 member 狀態異常。", "storage_baseline"),
                _next("io", "I/O timeout／測試失敗", "Storage inventory 存在但 I/O test 異常。", "storage_baseline"),
                _end("unknown", "無法確認", "缺少 storage symptom evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "storage_baseline",
            C.STORAGE_FAILURE,
            "裝置 inventory、firmware 與 RAID／test baseline 都一致嗎？",
            "核對 approved storage inventory、firmware、RAID policy 與 test plan。",
            "storage_baseline",
            [
                _next(
                    "no",
                    "不一致並已對齊",
                    "發現 storage baseline 不一致並完成核准修正。",
                    "storage_retest",
                ),
                _next("yes", "全部一致", "Storage baseline 一致但症狀仍存在。", "storage_physical"),
                _end("unknown", "無法確認", "缺少 storage inventory 或 baseline evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "storage_physical",
            C.STORAGE_FAILURE,
            "合格人員完成 approved A/B swap 後，是否找到 bay／cable／device path 異常？",
            "先確認資料可被覆寫；安全斷電後依核准程序交換 known-good path。",
            "storage_swap",
            [
                _next(
                    "yes",
                    "找到路徑異常並已處理",
                    "A/B swap 隔離出 storage path 並完成核准處理。",
                    "storage_retest",
                ),
                _end(
                    "no",
                    "仍無法隔離",
                    "Baseline 與 A/B swap 未能排除異常，需要攜帶 controller／device logs 升級。",
                    SessionOutcome.ESCALATED,
                ),
                _end("not_done", "未執行", "未完成 approved storage A/B swap。", SessionOutcome.UNRESOLVED),
            ],
            "Storage 測試可能破壞資料；未確認測試媒體與核准程序前不得初始化或重建 RAID。",
        ),
        _terminal_retest(
            "storage_retest",
            C.STORAGE_FAILURE,
            "處理後 inventory／RAID／I/O test 都恢復嗎？",
            "使用相同且核准的非生產資料測試重新驗證。",
            "storage_retest",
            "restore_storage_path",
        ),
        _step(
            "os_boot_scope",
            C.OS_BOOT_FAILURE,
            "問題發生在哪一種 boot path？",
            "確認是 local boot、PXE deployment 或載入 kernel 後失敗。",
            "boot_scope",
            [
                _next("local", "Local disk／OS 開不起來", "問題位於 local boot path。", "os_boot_baseline"),
                _next("pxe", "PXE 無法下載或開機", "問題位於 PXE deployment path。", "pxe_golden"),
                _next("kernel", "載入後 kernel panic", "Boot 已進入 OS loader／kernel 階段。", "os_boot_baseline"),
                _end("unknown", "無法確認", "缺少 boot stage evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "os_boot_baseline",
            C.OS_BOOT_FAILURE,
            "Boot order、UEFI mode、image 與 firmware 都符合 approved baseline 嗎？",
            "核對 boot target、UEFI／Secure Boot 設定、image checksum 與 firmware。",
            "boot_baseline",
            [
                _next(
                    "no",
                    "不一致並已對齊",
                    "發現 boot configuration 或 image baseline 不一致並完成核准修正。",
                    "os_boot_retest",
                ),
                _end(
                    "yes",
                    "全部一致但仍失敗",
                    "Boot baseline 一致但仍失敗，需要攜帶 console／kernel logs 升級。",
                    SessionOutcome.ESCALATED,
                ),
                _end("unknown", "無法確認", "缺少 boot configuration 或 image evidence。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _step(
            "pxe_golden",
            C.OS_BOOT_FAILURE,
            "Golden Sample 在相同 cable／port 與 PXE profile 能正常下載 image 嗎？",
            "用 Golden Sample 驗證 DHCP、TFTP／HTTP 與 deployment profile。",
            "pxe_golden",
            [
                _end(
                    "yes",
                    "可以",
                    "PXE station path 正常，問題跟著 DUT 或其設定。",
                    SessionOutcome.ESCALATED,
                ),
                _next(
                    "no",
                    "也不可以，環境已處理",
                    "Golden Sample 也失敗，已處理 PXE deployment path。",
                    "pxe_retest",
                ),
                _end("unknown", "尚未測試", "未完成 Golden Sample PXE 驗證。", SessionOutcome.UNRESOLVED),
            ],
        ),
        _terminal_retest(
            "os_boot_retest",
            C.OS_BOOT_FAILURE,
            "對齊 boot baseline 後 OS 可以正常啟動嗎？",
            "以相同 console 觀察點重新執行核准 boot test。",
            "os_boot_retest",
            "restore_boot_baseline",
        ),
        _terminal_retest(
            "pxe_retest",
            C.OS_BOOT_FAILURE,
            "修復 deployment path 後 Golden Sample 可以完成 PXE boot 嗎？",
            "以相同 cable／port 與 PXE profile 重新驗證。",
            "pxe_retest",
            "restore_pxe_path",
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
                _route("power", "無法上電或卡在 POST", C.POWER_OR_POST_FAILURE, "power_scope"),
                _route("memory", "記憶體容量或 ECC 異常", C.MEMORY_ERROR, "memory_evidence"),
                _route("storage", "NVMe／磁碟／RAID 異常", C.STORAGE_FAILURE, "storage_scope"),
                _route("boot", "OS／PXE 無法開機", C.OS_BOOT_FAILURE, "os_boot_scope"),
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
    C.POWER_OR_POST_FAILURE: "power_scope",
    C.MEMORY_ERROR: "memory_evidence",
    C.STORAGE_FAILURE: "storage_scope",
    C.OS_BOOT_FAILURE: "os_boot_scope",
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
