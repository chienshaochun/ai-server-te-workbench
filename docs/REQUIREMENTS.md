# MVP Requirements

## 使用者

主要使用者是需要執行測試、判讀異常並回報工廠或客戶端的 TE 軟體測試工程師。

## 核心使用案例

1. 使用內建的正常 DUT 與 fixture 執行測試，取得 PASS 結果。
2. 注入單一故障，觀察對應測試失敗與原始 evidence。
3. Fixture precheck 未通過時中止產品判定，避免把站點問題誤判為 DUT failure。
4. 比較原 DUT、golden sample 與另一 station 的結果，縮小問題範圍。
5. 產生可交付給工廠端或客戶端的檢測報告。

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

### Reporting

- 報告包含 environment、fixture、DUT、test summary、failures、evidence、分類與建議檢查。
- 支援 Markdown 與單檔 HTML。
- 報告必須揭露 synthetic data 與 simulator 限制。

## 非功能需求

- 相同輸入必須得到相同分類與報告內容（執行時間欄位除外）。
- Domain、engine 與 troubleshooting 不得依賴 Streamlit。
- 所有測試邏輯可由 pytest 在無 UI 環境執行。
- 使用者輸入必須經過 schema 與範圍驗證。
- 不保存 token、密碼或真實客戶資料。

## 不在 MVP 範圍

- 真實硬體控制或電氣量測
- 自動修復硬體、firmware 或測試站
- LLM root-cause generation
- 使用者帳號與權限系統
- 資料庫、多人協作或即時產線串接
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
