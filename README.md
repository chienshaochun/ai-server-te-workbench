# AI Server TE Troubleshooting Workbench

一個以 Streamlit 展示的 AI 伺服器測試工程問答工作台。使用者輸入 server 型號與遇到的
現象，系統會一次提出一個可驗證問題，引導使用者執行交換測試、記錄觀察、縮小問題範圍，
最後產生可追溯的檢測報告。底層使用模擬 DUT（Device Under Test）與測試治具，示範測試
前檢查、故障注入、交叉驗證與 evidence-based troubleshooting。

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


## MVP 操作流程

```text
輸入 Server 型號
       ↓
選擇常見問題，或輸入額外問題
       ↓
辨識症狀並一次詢問一個檢查問題
       ↓
使用者回填觀察結果／交換測試結果
       ↓
Fixture／DUT／Golden Sample／Cross-station 分流
       ↓
建議下一個檢查 → 解決／轉交／資訊不足
       ↓
Markdown / HTML 檢測報告
```

自由文字問答第一版採用可測試的規則與關鍵詞比對，不呼叫外部 LLM，也不把推測描述成硬體
根因。若辨識信心不足，系統會請使用者選擇問題類別，而不是自行猜測。

## 常見問題如何定義

常見問題以下列匿名案例統計排序：

- 相同 server family 與相似 symptom category 的案例數。
- 已標記為 resolved 的案例數。
- resolved 案例中，採用相同 resolution 的比例。
- MVP 預設門檻：至少 3 筆 resolved cases，且主要 resolution 占比至少 60%。

因 MVP 沒有使用者帳號，畫面呈現的是「案例數」，不會假裝成「不重複使用者人數」。公開
demo 使用明確標示的 synthetic history；未來接上持久化案例庫後，才可累積真實匿名統計。

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

## 本機啟動

```powershell
conda activate dev
cd C:\Users\ru03g\side_project\ai-server-te-workbench
python -m pip install -e .
python -m streamlit run app.py
```

瀏覽器開啟 Streamlit 顯示的 local URL。公開 demo 的 common issues 使用 synthetic history；
重新啟動 app 後，本次 session 累積的案例不會被永久保存。

## 開發階段

- Phase 1：需求、MVP 邊界、架構與驗收標準
- Phase 2：DUT／Fixture／Test Plan 模型與 synthetic scenarios
- Phase 3：測試執行器與 fault injection
- Phase 4：交叉驗證 troubleshooting engine
- Phase 5：Markdown／HTML 檢測報告
- Phase 6A：問答產品契約、常見問題定義與對話流程
- Phase 6B：問題辨識、knowledge pack 與常見案例統計
- Phase 6C：逐步問答 state machine 與 troubleshooting session
- Phase 6D：Streamlit UI、報告整合與端到端測試
- Phase 7：GitHub、CI、Streamlit Cloud 與人工 demo

詳細規格請見 [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)，架構請見
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，逐步問答設計請見
[`docs/CONVERSATION_DESIGN.md`](docs/CONVERSATION_DESIGN.md)。
