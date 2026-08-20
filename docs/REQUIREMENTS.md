# MVP Requirements

## 使用者

主要使用者是需要執行測試、判讀異常並回報工廠或客戶端的 TE 軟體測試工程師。

## 核心使用案例

1. 輸入 server 型號與自由文字問題，或從常見問題選單開始。
2. 系統一次提出一個可驗證問題，使用者回填觀察或交換測試結果。
3. 使用內建模擬 DUT 與 fixture 執行測試，取得結構化 evidence。
4. Fixture precheck 未通過時中止產品判定，避免把站點問題誤判為 DUT failure。
5. 比較原 DUT、golden sample 與另一 station 的結果，縮小問題範圍。
6. 將處理過程標記為 resolved、unresolved 或 escalated，產生檢測報告。

## 功能需求

### Fixture readiness

- 記錄 fixture ID、network、power、BMC interface 與 calibration 狀態。
- 任一必要項目未就緒時，受影響測試標示為 `BLOCKED_BY_FIXTURE`。
- BLOCKED 不得計入 DUT failure。

### Test execution

- Test Plan 必須具有 ID、版本與 ordered test cases。
- 每個 test case 定義 timeout、retry 與 expected condition。
- 每次執行保存 DUT、fixture、test plan、開始時間、duration 與 evidence。
- MVP 不呼叫真實 IPMI、Redfish、SSH、Serial 或任意 shell command。

### Troubleshooting

- 分開表示 observation、possible cause、verification step 與 confidence。
- 使用原 DUT、golden sample 與 cross-station 結果進行交叉驗證。
- 無足夠證據時必須回傳 `INCONCLUSIVE`。
- 規則不得把 `SUSPECTED_HARDWARE` 描述成 confirmed hardware failure。

### Guided Q&A

- 必須收集 server model 與問題描述；不得要求真實客戶名稱、帳號、密碼或序號。
- 自由文字先映射至 symptom category，低信心時要求使用者確認類別。
- 每次只顯示目前能回答的一個問題或一個實體檢查步驟。
- 每個分支保存 question、answer、observation、recommended check 與 evidence reference。
- 最低支援 network unreachable、one unit works but another fails、firmware mismatch、GPU
  missing、temperature high 與 unknown 六類入口。
- 建議涉及拆機或電氣操作時，必須要求安全斷電並交由合格人員執行。

### Optional LLM assistance

- 未設定 API key 時，所有入口與逐步排查仍可用 deterministic 模式完成。
- LLM triage 必須使用 structured output，且只能選擇既有 category 與 start step。
- 本地端必須再次驗證 category-to-step allowlist；失敗時自動使用 deterministic fallback。
- LLM 問答只能解釋目前 step，不得提交 answer、改變 session state 或產生新硬體指令。
- API request 不保存，輸入最多 1000 字、單次問答最多 500 字，並限制輸出 token。
- 公開 demo 每個瀏覽器 session 最多呼叫 5 次；production 需另加跨 session rate limit。

### Common issues

- 以 normalized model family、symptom category、resolution ID 與 resolved 狀態聚合案例。
- common issue 預設至少具有 3 筆 resolved cases，且主要 resolution 占比至少 60%。
- 下拉選單按 resolved case count、resolution consistency 與名稱穩定排序。
- MVP synthetic history 必須在 UI 與報告中標示為 demo data。
- 公開 demo 至少提供 12 個具體 synthetic patterns，共代表 72 筆 fictional aggregates。
- 沒有帳號系統時只能宣稱 case count，不得宣稱 unique user count。

### Reporting

- 報告包含 environment、fixture、DUT、test summary、failures、evidence、分類與建議檢查。
- 支援 Markdown 與單檔 HTML。
- 報告必須揭露 synthetic data 與 simulator 限制。
- 使用 LLM 時，報告必須保存來源、模型、advisory summary 與使用者主動提出的 AI 問答。

## 非功能需求

- 相同狀態與答案序列必須得到相同下一步、分類與報告內容（執行時間欄位除外）。
- Domain、engine 與 troubleshooting 不得依賴 Streamlit。
- 所有測試邏輯可由 pytest 在無 UI 環境執行。
- 使用者輸入必須經過 schema 與範圍驗證。
- 不保存 token、密碼或真實客戶資料。
- API key 必須來自 server-side secret，不得寫入 repository 或傳送到前端。

## 不在 MVP 範圍

- 真實硬體控制或電氣量測
- 自動修復硬體、firmware 或測試站
- LLM root-cause generation、自由產生維修命令或自動操作 state machine
- 使用者帳號與權限系統
- 持久化多人案例資料庫、使用者人數統計或即時產線串接
- 大規模製造排程與 MES 整合

## 10 項可量測驗收標準

1. 內建一個正常 DUT、一個 golden sample 與兩個 fixture scenarios。
2. Fixture precheck 能區分 READY 與 BLOCKED，且 BLOCKED 不計為 DUT FAIL。
3. BMC、firmware、GPU 與 temperature 四個測試皆產生結構化結果。
4. 五個指定 fault scenarios 都能穩定觸發預期 observation。
5. 每個非 PASS 結果至少包含一筆可定位的 evidence。
6. 交叉驗證能區分 suspected DUT、fixture／environment 與 inconclusive。
7. Troubleshooting output 分開保存 observation、possible causes 與 verification steps。
8. 同一次 run 能產生內容一致的 Markdown 與 HTML 報告。
9. Streamlit demo 可在不準備外部檔案的情況下完成一次正常與一次失敗流程。
10. 自動測試至少 25 項，CI 中 pytest 與 Ruff 均通過。
11. 使用者可由 common issue dropdown 或自由文字建立 troubleshooting session。
12. 支援至少六類 symptom 入口，且低信心文字不會直接產生 root-cause 結論。
13. 問答流程一次只前進一個 step，所有 answer 與 recommendation 都保存在 transcript。
14. common issue 統計可重現門檻、case count、resolved count 與主要 resolution ratio。
15. 最終 Markdown 與 HTML 報告包含問答 transcript、已執行檢查與 session outcome。
16. Streamlit demo 可完成 network unreachable 與 one-unit-only 兩條逐步問答流程。
17. OpenAI 回應的 category 與 step 不一致時，流程必須拒絕並退回 deterministic matcher。
18. 沒有 OpenAI key、API 失敗或達 session call cap 時，app 仍可完成排查與報告。
19. 常見問題選單包含 12 個透明 synthetic patterns，總 case count 為 72。
20. AI advisory 可進入 Markdown 與 HTML，且所有使用者與模型文字在 HTML 中正確 escape。
