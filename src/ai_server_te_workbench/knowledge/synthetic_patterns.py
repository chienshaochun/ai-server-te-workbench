"""Transparent aggregated patterns representing 72 fictional troubleshooting cases."""

from ai_server_te_workbench.conversation.matcher import match_issue
from ai_server_te_workbench.knowledge.models import (
    PatternMatch,
    SymptomCategory as C,
    SyntheticCasePattern,
)


def synthetic_case_patterns() -> tuple[SyntheticCasePattern, ...]:
    return (
        _p(
            "bmc_single_dut_timeout",
            "單台 BMC timeout",
            "同一個 port 其他機器正常，只有這台 BMC timeout",
            C.NETWORK_UNREACHABLE,
            ("bmc", "timeout", "只有這台", "其他機器正常"),
            ("single DUT", "golden passes", "BMC path"),
            "先在同一 cable／port 驗證 Golden Sample。",
            "correct_bmc_config",
            "修正 BMC IP、VLAN 或 service 設定後重測。",
            12,
            10,
        ),
        _p(
            "station_all_units_offline",
            "同站所有機器都無法連線",
            "這個 station 換了三台都 ping 不到",
            C.NETWORK_UNREACHABLE,
            ("都連不上", "所有機器", "station", "ping 不到"),
            ("multiple DUTs", "same station", "shared failure"),
            "用 Golden Sample 確認 station cable、port 與 VLAN。",
            "restore_station_network_path",
            "修復 station switch port、VLAN 或 cable path。",
            9,
            8,
        ),
        _p(
            "physical_link_down",
            "更換 cable 後 link 恢復",
            "網路孔沒有 link light，換線後正常",
            C.NETWORK_UNREACHABLE,
            ("link light", "link down", "換線", "cable"),
            ("physical link down", "known-good cable available"),
            "交換 known-good cable 與 switch port。",
            "replace_network_cable",
            "更換不良 cable 或修復實體 port path。",
            7,
            7,
        ),
        _p(
            "duplicate_ip_intermittent",
            "IP conflict 造成間歇斷線",
            "BMC 有時連得到有時 timeout，懷疑 IP 重複",
            C.NETWORK_UNREACHABLE,
            ("間歇", "有時", "ip conflict", "ip 重複"),
            ("intermittent", "link up", "address conflict"),
            "核對 ARP、租約與 approved BMC IP。",
            "remove_duplicate_ip",
            "移除重複 IP 並重新驗證連線穩定性。",
            6,
            5,
        ),
        _p(
            "vlan_after_station_move",
            "換站後 VLAN 不一致",
            "server 換到另一站後 BMC 就連不上",
            C.NETWORK_UNREACHABLE,
            ("換站", "另一站", "vlan", "移動"),
            ("worked before move", "new station"),
            "比較新舊 station 的 VLAN 與 switch port profile。",
            "restore_vlan_profile",
            "套用 approved VLAN／port profile。",
            5,
            4,
        ),
        _p(
            "failure_follows_dut",
            "問題跟著 DUT 到第二站",
            "這台不行但另一台可以，換 station 還是一樣",
            C.ONE_UNIT_ONLY,
            ("這台不行", "另一台可以", "換 station", "還是一樣"),
            ("golden passes", "cross-station reproduces"),
            "執行 Golden Sample 與 cross-station A/B swap。",
            "isolate_dut_with_swap",
            "完成 DUT-path isolation 並依失敗 test case 升級。",
            8,
            6,
        ),
        _p(
            "failure_stays_station",
            "問題留在原 station",
            "失敗機到另一站會過，Golden 在原站也失敗",
            C.ONE_UNIT_ONLY,
            ("另一站會過", "原站", "golden", "也失敗"),
            ("DUT passes elsewhere", "golden fails original station"),
            "先修復原 fixture／environment／test program。",
            "repair_station_path",
            "修復 station path 後用 Golden Sample 驗證。",
            6,
            5,
        ),
        _p(
            "firmware_after_update",
            "更新後 firmware baseline 不符",
            "更新 firmware 後測試版本不符合 golden baseline",
            C.FIRMWARE_MISMATCH,
            ("更新後", "firmware", "版本不符", "baseline"),
            ("post-update", "checksum mismatch"),
            "比對 approved image checksum、版本與設定。",
            "restore_approved_firmware",
            "依核准流程恢復 firmware image 與設定。",
            5,
            5,
        ),
        _p(
            "gpu_count_seven_of_eight",
            "預期 8 張只辨識 7 張 GPU",
            "lspci 只看到 7/8 張 GPU",
            C.GPU_MISSING,
            ("7/8", "gpu", "少一張", "lspci"),
            ("one GPU missing", "persistent after cold restart"),
            "先 cold restart 並核對 power state，再安全斷電檢查。",
            "recheck_gpu_power_and_seating",
            "由合格人員處理 GPU seating／power 後重測。",
            4,
            3,
        ),
        _p(
            "gpu_recovers_cold_restart",
            "Cold restart 後 GPU 恢復",
            "warm reboot 少 GPU，完全斷電再開就恢復",
            C.GPU_MISSING,
            ("warm reboot", "cold restart", "斷電", "恢復"),
            ("warm-only failure", "cold restart recovers"),
            "比較 warm reboot 與 cold restart enumeration。",
            "recover_gpu_enumeration",
            "記錄 power-state 相關間歇問題並升級 firmware 分析。",
            3,
            3,
        ),
        _p(
            "airflow_obstruction",
            "Airflow obstruction 導致高溫",
            "idle 溫度過高而且風扇進風被擋住",
            C.TEMPERATURE_HIGH,
            ("idle", "溫度過高", "airflow", "風扇"),
            ("high at idle", "airflow abnormal"),
            "在 approved idle condition 檢查 fan 與 airflow。",
            "restore_airflow",
            "清除 airflow obstruction 並以相同條件重測。",
            4,
            4,
        ),
        _p(
            "load_dependent_temperature",
            "Workload 條件造成溫度差異",
            "壓力測試才高溫，idle 正常",
            C.TEMPERATURE_HIGH,
            ("壓力測試", "高溫", "idle 正常", "workload"),
            ("load dependent", "idle normal"),
            "先對齊 workload、sensor 與 temperature limit。",
            "normalize_test_load",
            "對齊 test load 與判定條件後重新量測。",
            3,
            2,
        ),
    )


def match_case_patterns(problem: str, limit: int = 3) -> tuple[PatternMatch, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    normalized = problem.casefold()
    category = match_issue(problem).category
    matches = []
    for pattern in synthetic_case_patterns():
        terms = tuple(term for term in pattern.keywords if term.casefold() in normalized)
        score = min(1.0, (0.35 if pattern.symptom_category is category else 0.0) + 0.2 * len(terms))
        if score > 0:
            matches.append(PatternMatch(pattern, score, terms))
    return tuple(
        sorted(matches, key=lambda item: (-item.score, -item.pattern.case_count, item.pattern.id))[
            :limit
        ]
    )


def _p(
    id, title, problem, category, keywords, conditions, check, resolution, summary, cases, resolved
):
    return SyntheticCasePattern(
        id,
        title,
        problem,
        category,
        keywords,
        conditions,
        check,
        resolution,
        summary,
        cases,
        resolved,
    )
