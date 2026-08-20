# Architecture

## 設計原則

1. **Evidence before diagnosis**：先保存 observation，再提出 suspected cause。
2. **Fixture before DUT**：先證明測試環境可用，才判定產品結果。
3. **Deterministic core**：測試與 troubleshooting 規則可重現、可單元測試。
4. **UI is an adapter**：Streamlit 只負責互動，不承載 domain logic。
5. **Hardware boundary**：MVP 只使用 mock adapter，未來真實協定不改動核心模型。

## 系統流程

```text
Streamlit UI
    ↓
Application Service
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
│   └── scenarios/
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
- 為了 AI Server 名稱加入不必要 AI：MVP 不使用 LLM，先證明測試工程能力。
- 治具能力被誇大：明確標示 readiness simulator，不宣稱完成實體治具設計。
