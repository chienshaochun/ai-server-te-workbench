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

自由文字入口採用混合式架構：使用者可選擇 OpenAI API 協助理解自然語言；模型只能回傳固定
schema 並選擇核准的 troubleshooting 入口。API 未設定、額度用完、逾時或回應未通過本地驗證
時，系統自動改用可測試的規則與關鍵詞比對。兩種模式都不能把推測描述成硬體根因。

排查中的 AI 問答只會解釋目前核准步驟及已記錄 evidence，不會替使用者提交結果、跳轉流程、
控制硬體或執行修復。

## 常見問題如何定義

公開 demo 內建 12 個具體模式，共代表 72 筆 fictional case aggregates，涵蓋：

- 單台 BMC timeout、同站所有機器離線、link down、IP conflict 與 VLAN 差異。
- 問題跟著 DUT 或留在 station。
- Firmware baseline、GPU enumeration 與 temperature／airflow 情境。
- 每個模式的案例數、resolved 數、第一個建議檢查與模擬解法。

這些數字不是實際客戶資料、維修紀錄或不重複使用者人數。未來接上持久化案例庫並取得合法
匿名資料後，才能計算真實常見問題統計。

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
- OpenAI Responses API（optional）
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

### 啟用本機 AI 輔助

複製範例 Secrets 並填入自己的 key，請勿提交 `secrets.toml`：

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
notepad .streamlit\secrets.toml
```

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5.6-luna"
```

沒有 key 時 app 仍能完整執行 deterministic 流程。AI 選項預設關閉；每個瀏覽器 session 最多
呼叫 5 次，且 API request 使用 `store=False`。這只是 portfolio demo 的成本護欄，不是完整的
跨使用者 rate limit；公開部署仍應設定 API 使用預算與監控。

若畫面顯示「額度不足或速率限制」，請到 OpenAI Platform 檢查 **Billing** 與 **Usage**。建立
API key 不代表帳號已具有可用 API 額度；在額度可用前，app 會安全地維持 deterministic 模式。

實作依據：[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
與 [API key 安全實務](https://developers.openai.com/api/docs/guides/production-best-practices#api-keys)。

### Streamlit Community Cloud

在 app 的 **Settings → Secrets** 加入相同兩個欄位。不要把 key 放入 GitHub、README、前端輸入
框或任何會顯示在瀏覽器的程式碼。部署後先以少量測試確認 API 權限與使用量。

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
- Phase 6E：12 種 synthetic patterns、可選 LLM triage、安全 fallback 與 AI advisory report
- Phase 7：GitHub、CI、Streamlit Cloud 與人工 demo

詳細規格請見 [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)，架構請見
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，逐步問答設計請見
[`docs/CONVERSATION_DESIGN.md`](docs/CONVERSATION_DESIGN.md)。
