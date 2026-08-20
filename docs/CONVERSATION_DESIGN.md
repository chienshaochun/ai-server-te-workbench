# Guided Troubleshooting Conversation Design

## 產品目標

將模糊的 server 問題轉換成一連串可觀察、可回填、可追溯的 TE 檢查。系統不直接回答
「哪個零件壞了」，而是回答「下一個最有資訊價值且安全的檢查是什麼」。

## 使用者入口

使用者必須提供 server model，並選擇以下其中一種入口：

1. 從常見問題下拉選單選擇已聚合的 symptom。
2. 輸入自由文字，例如「網路連不上」或「這台不行但另一台可以」。

自由文字可勾選 AI 輔助理解。LLM 只輸出固定 category 與核准 start step；如果未勾選、沒有
API key、呼叫失敗或本地 allowlist 驗證失敗，系統使用 deterministic matcher。

未知型號只作為報告與案例分群資訊，第一版套用 `generic_ai_server` knowledge pack。除非未來加入
經驗證的 model-specific pack，否則 UI 不顯示該型號專屬 pin、firmware 或拆裝指示。

## 對話狀態

```text
NEW
 ↓
OPTIONAL_AI_TRIAGE → VALIDATE_ALLOWLIST → FALLBACK（必要時）
 ↓
NEEDS_CATEGORY_CONFIRMATION（僅低信心時）
 ↓
ASKING → WAITING_FOR_ANSWER → ASKING
                              ↓
               RESOLVED | UNRESOLVED | ESCALATED
```

每個 step 包含：

- `question`：要確認的單一事實。
- `allowed_answers`：Yes／No／Unknown 或有限選項。
- `recommended_check`：使用者現在要執行的一個動作。
- `safety_note`：需要斷電、ESD 或合格人員時顯示。
- `next_step_by_answer`：回答後的下一個 step。
- `evidence_tag`：寫入 transcript 與報告的 observation 類型。

## 第一版 symptom categories

### `network_unreachable`

1. 確認是 OS network 還是 BMC management network。
2. 確認同一 cable／port 上 Golden Sample 是否可連線。
3. 查看 physical link state，再確認 IP、VLAN、gateway 與 address conflict。
4. 交換 known-good cable／port；觀察問題跟著 DUT 還是 station path。
5. 若 station path 正常但 DUT BMC 仍不可達，分類為 `SUSPECTED_NETWORK` 並建議收集 BMC
   狀態與 firmware evidence，不宣稱 NIC 或主板已損壞。

### `one_unit_only`

1. 確認兩台是否使用相同 station、test plan、firmware baseline 與 cable path。
2. 將失敗 DUT 放到已知正常 station；將 Golden Sample 放到原 station。
3. 問題跟著 station：優先檢查 fixture／environment／test program。
4. 問題跟著 DUT：依失敗 test case 分流至 network、firmware、GPU 或 temperature flow。
5. 結果不一致或未完成交換：`INCONCLUSIVE`。

### 其他入口

- `firmware_mismatch`：核對 approved baseline、image checksum、設定與更新流程。
- `gpu_missing`：先核對 enumeration 與 power state，再由合格人員斷電檢查 seating／power。
- `temperature_high`：確認 sensor、load、fan 與 airflow，再由合格人員檢查 cooling contact。
- `unknown`：要求選擇最接近的 symptom 或標記 escalated，不生成 root cause。

## 常見問題統計

每筆匿名 case record 只保存標準化後的：

```text
model_family
symptom_category
resolution_id
outcome
```

不保存自由文字、server serial、客戶名稱或連線資訊。聚合公式：

```text
resolution_consistency = dominant_resolution_count / resolved_case_count
is_common = resolved_case_count >= 3 and resolution_consistency >= 0.60
```

公開 demo 的 initial history 與 12 個常見模式是 synthetic data，共代表 72 筆 fictional
aggregates；UI 必須顯示此限制。Phase 6 不加入帳號或持久化多人資料庫，因此這些數字代表
模擬案例筆數，不代表真實客戶資料或不重複使用者。

## 排查中的 AI 問答

AI 問答只接受目前 `DiagnosticStep`、已記錄 observation 與使用者問題。模型回傳的
`related_step_id` 必須等於目前 step，否則整個回答拒絕顯示。回答只能解釋為何執行目前檢查、
缺少什麼 evidence 或何時應升級處理；不能替使用者選擇 Yes／No、生成新 branch 或宣稱 root
cause。每個瀏覽器 session 最多 5 次 API 呼叫。

## 報告新增內容

現有 test run、fixture、evidence 與 assessment 之外，最終報告增加：

- 原始問題摘要與辨識後 symptom category。
- 逐步 question／answer／recommended check transcript。
- 使用者實際完成與未完成的檢查。
- session outcome 與 resolution ID。
- common issue 是否來自 synthetic history 的揭露。
- AI triage 的來源、模型、摘要、理由與 fallback 狀態。
- 使用者主動提出的 AI advisory Q&A，以及它所對應的核准 step。
