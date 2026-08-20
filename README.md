# AI Server TE Troubleshooting Workbench

一個以 Streamlit 展示的 AI 伺服器測試工程工作台。專案使用模擬 DUT（Device Under
Test）與測試治具，示範測試前檢查、測試程式執行、故障注入、交叉驗證、問題分流與檢測
報告產生。

## 專案定位

本專案不是硬體維修工具，也不宣稱能從軟體 log 直接確認硬體 root cause。它的責任是：

```text
Detect → Reproduce → Isolate → Collect Evidence → Recommend Checks → Report
```

也就是協助 TE 將測試結果區分為 DUT、fixture、環境、firmware 或尚無法判定的問題，並保留
足夠證據供硬體、韌體、製造或客戶端工程師繼續處理。

## 職缺對應

| TE 工作內容 | 本專案對應能力 |
|---|---|
| 產線測試程式開發與管理 | 版本化 Test Plan、模組化測試與結構化結果 |
| 產品測試導入與問題解決 | DUT／station／firmware 設定與 fault scenarios |
| 客戶端及工廠端問題分析 | Evidence-based troubleshooting 與可下載報告 |
| 治具規劃與導入 | Fixture readiness、calibration 與 golden sample 檢查 |
| 產線軟體自動化 | 批次執行、timeout、retry、結果彙整與報告產生 |

職缺參考：[台灣就業通－緯創資通自動化測試／測試工程師](https://job.taiwanjobs.gov.tw/internet/index/JobDetail.aspx?EMPLOYER_ID=122234&HIRE_ID=14205955&R2=11)

## MVP 操作流程

```text
Fixture Precheck
       ↓
Select DUT + Test Plan
       ↓
Run 4 Simulated Tests
       ↓
PASS / FAIL / BLOCKED
       ↓
Cross-validation Troubleshooting
       ↓
Markdown / HTML Report
```

第一版只模擬四個代表性測試：

- BMC connectivity
- Firmware version
- GPU device count
- CPU temperature

並提供至少五種故障情境：

- `bmc_timeout`
- `firmware_mismatch`
- `gpu_missing`
- `temperature_high`
- `fixture_network_down`

## 結果邊界

允許的分類包含：

```text
PASS
FAIL_REPRODUCIBLE
BLOCKED_BY_FIXTURE
SUSPECTED_HARDWARE
SUSPECTED_FIRMWARE
SUSPECTED_NETWORK
INCONCLUSIVE
```

`SUSPECTED_*` 只是有證據支持的調查方向，不是已確認的 root cause。

## 預計技術

- Python 3.12+
- Streamlit
- 標準函式庫 dataclasses／JSON／HTML
- pytest
- Ruff
- GitHub Actions

## 開發階段

- Phase 1：需求、MVP 邊界、架構與驗收標準
- Phase 2：DUT／Fixture／Test Plan 模型與 synthetic scenarios
- Phase 3：測試執行器與 fault injection
- Phase 4：交叉驗證 troubleshooting engine
- Phase 5：Markdown／HTML 檢測報告
- Phase 6：Streamlit UI 與端到端測試
- Phase 7：GitHub、CI、Streamlit Cloud 與人工 demo

詳細規格請見 [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)，架構請見
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。
