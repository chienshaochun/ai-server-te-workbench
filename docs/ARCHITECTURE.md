# Architecture

## 設計原則

1. **Evidence before diagnosis**：先保存 observation，再提出 suspected cause。
2. **Fixture before DUT**：先證明測試環境可用，才判定產品結果。
3. **Deterministic core**：測試與 troubleshooting 規則可重現、可單元測試。
4. **UI is an adapter**：Streamlit 只負責互動，不承載 domain logic。
5. **Hardware boundary**：MVP 只使用 mock adapter，未來真實協定不改動核心模型。
6. **One verifiable step at a time**：問答系統每次只建議一個能回填結果的檢查動作。
7. **No invented model knowledge**：未知 server 型號使用 generic knowledge pack，不虛構廠商規格。
8. **Offline by default**：主流程不依賴外部 API、付費額度或網路連線。
9. **Low-confidence confirmation**：本地 matcher 不確定時由使用者選擇類別，不猜測 root cause。

## 系統流程

```text
Streamlit UI
    ↓
Application Service
    ├── Issue Matcher
    ├── Offline Knowledge Pack
    ├── Conversation Controller
    ├── Common Issue Statistics
    ├── Fixture Precheck
    ├── Test Runner
    ├── Troubleshooting Engine
    └── Report Builder
           ↓
Domain Models + Evidence
           ↑
Mock Device Adapter
```

## 建議目錄

```text
ai-server-te-workbench/
├── app.py
├── pyproject.toml
├── src/ai_server_te_workbench/
│   ├── models.py
│   ├── scenarios.py
│   ├── knowledge/
│   │   ├── models.py
│   │   └── generic_ai_server.py
│   ├── conversation/
│   │   ├── matcher.py
│   │   ├── controller.py
│   │   └── statistics.py
│   ├── llm/
│   │   ├── models.py
│   │   ├── service.py
│   │   └── openai_advisor.py
│   ├── adapters/
│   │   ├── base.py
│   │   └── mock.py
│   ├── engine/
│   │   ├── precheck.py
│   │   └── runner.py
│   ├── troubleshooting/
│   │   ├── matrix.py
│   │   └── rules.py
│   └── reporting/
│       ├── markdown.py
│       └── html.py
├── tests/
│   ├── unit/
│   └── integration/
├── data/
│   ├── scenarios/
│   └── synthetic_cases.json
└── docs/
```

## 核心資料契約

### DUT

```text
serial_number
model
firmware_version
bmc_reachable
gpu_count
cpu_temperature_c
```

### Fixture

```text
fixture_id
station_id
network_ready
power_ready
bmc_interface_ready
calibration_valid
```

### TestCase

```text
id
name
timeout_seconds
max_retries
expected
```

### TestResult

```text
test_case_id
status: PASS | FAIL | BLOCKED | ERROR
expected
actual
duration_ms
attempts
evidence
```

### TroubleshootingAssessment

```text
classification
observation
evidence_ids
possible_causes
verification_steps
confidence
```

### TroubleshootingSession

```text
session_id
server_model
raw_problem
symptom_category
current_step_id
transcript[]: question | answer | observation | recommendation | evidence_ids
outcome: ACTIVE | RESOLVED | UNRESOLVED | ESCALATED
resolution_id
```

### CommonIssueSummary

```text
model_family
symptom_category
similar_case_count
resolved_case_count
dominant_resolution_id
dominant_resolution_count
resolution_consistency
is_common
```

## 問答層與測試層的關係

```text
使用者描述「這台連不上，另一台可以」
             ↓
Issue Matcher → network_unreachable + one_unit_only clues
             ↓
Conversation Controller 提出交換 cable／port／station 的單一步驟
             ↓
使用者回填結果 → transcript evidence
             ↓
需要模擬量測時呼叫既有 Test Runner／Golden／Cross-station engine
             ↓
Assessment + conversation transcript → Report Builder
```

自由文字由本地 Issue Matcher 處理。Matcher 依審核過的 strong／weak keywords 計分，回傳
category、confidence 與 matched terms；低信心時固定進入 `unknown_category`，由使用者確認核准
入口。真正的分流仍由使用者回答、量測 evidence 與交叉驗證規則決定。

## 離線分流邊界

```text
User description（max 1000 chars）
             ↓
Local keyword scoring
             ↓
Confidence threshold
 high ↓                  low → Category confirmation
Approved category-to-step mapping
             ↓
Conversation Controller
```

- Matcher 只能選擇 `SymptomCategory` enum 中的類別。
- `START_STEPS` 是唯一 category-to-step mapping，controller 初始化時驗證所有 step reference。
- Knowledge pack 不能新增任意 shell、IPMI、Redfish 或硬體控制動作。
- 使用者文字只留在當次 Streamlit session 與下載報告，不會傳送到第三方服務。
- 未來即使評估 LLM，也不得取代 deterministic controller 或安全邊界。

## 交叉驗證矩陣

```text
Original DUT fails + Golden passes on same station
→ Suspect DUT path

Original DUT fails + Golden also fails on same station
→ Suspect fixture / environment / test program

Original DUT fails on two ready stations + Golden passes
→ Suspected hardware or firmware; use test-specific evidence to refine

Original DUT passes after retry only
→ Intermittent; keep evidence and avoid confirmed diagnosis

Evidence conflicts or required comparison is absent
→ INCONCLUSIVE
```

## Hardware adapter boundary

核心只依賴抽象的 `DeviceAdapter`：

```text
get_bmc_status()
get_firmware_version()
get_gpu_count()
get_cpu_temperature()
```

MVP 實作 `MockDeviceAdapter`。未來若有合法設備與測試環境，才新增 Redfish、IPMI、SSH
或 Serial adapter；這些 adapter 必須各自處理 timeout、authentication 與 command allowlist。

## 主要風險

- 模擬過度理想化：以 fault injection、conflicting evidence 與 inconclusive cases 緩解。
- 將 correlation 當 root cause：資料模型與報告用詞強制使用 suspected／possible。
- UI 與邏輯耦合：所有核心流程先以無 UI 測試驗證。
- 自由文字被錯誤理解：使用明確信心門檻，低信心時要求使用者確認 symptom category。
- 常見問題統計被誤解為使用者人數：只顯示匿名 case count，synthetic data 明確標示。
- 治具能力被誇大：明確標示 readiness simulator，不宣稱完成實體治具設計。
