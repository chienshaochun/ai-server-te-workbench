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

自由文字入口完全在 App 內以可測試的規則與關鍵詞比對，選擇核准的 troubleshooting 入口。
輸入內容不會傳送到外部 API；低信心或無法辨識時，系統會要求使用者自行確認最接近的問題
類別，不會憑空生成硬體根因。

## 常見問題如何定義

公開 demo 內建 24 個具體模式，共代表 138 筆虛構聚合案例，涵蓋：

- 單台 BMC timeout、同站所有機器離線、link down、IP conflict 與 VLAN 差異。
- 問題跟著 DUT 或留在 station。
- Firmware baseline、GPU enumeration 與 temperature／airflow 情境。
- 無法上電、卡在 POST、上電後自行關機。
- DIMM inventory、記憶體容量與 ECC error。
- NVMe 未辨識、RAID degraded 與 storage I/O timeout。
- Local OS、PXE deployment、no boot device 與 kernel panic。
- 每個模式的案例數、resolved 數、第一個建議檢查與模擬解法。

這些數字不是實際客戶資料、維修紀錄或不重複使用者人數。未來接上持久化案例庫並取得合法
匿名資料後，才能計算真實常見問題統計。

底層測試執行器另模擬四個代表性自動測試：

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

瀏覽器開啟 Streamlit 顯示的 local URL。公開 demo 的常見問題使用模擬案例；
重新啟動 app 後，本次 session 累積的案例不會被永久保存。

### Streamlit Community Cloud

此版本沒有外部 API 或資料庫依賴，不需要在 **Settings → Secrets** 設定金鑰。Streamlit Cloud
只要以 Python 3.12 安裝本 repository，即可直接啟動 `app.py`。

## 未來保留項目

若未來取得合適的真實匿名案例與成本／安全需求，再評估持久化案例庫、model-specific knowledge
pack 或 LLM 輔助。這些目前都不在實作範圍；核心流程會繼續由可重現的規則、使用者觀察與
Golden Sample／Cross-station evidence 控制。

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
- Phase 6E：24 種模擬常見情境、9 類離線分流與 138 筆透明虛構聚合案例
- Phase 7：GitHub、CI、Streamlit Cloud 與人工 demo

詳細規格請見 [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)，架構請見
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，逐步問答設計請見
[`docs/CONVERSATION_DESIGN.md`](docs/CONVERSATION_DESIGN.md)。
