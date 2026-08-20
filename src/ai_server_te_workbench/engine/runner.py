"""Ordered test execution with fixture gating, retry, and evidence capture."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from time import perf_counter_ns
from uuid import uuid4

from ai_server_te_workbench.adapters.base import (
    DeviceAdapter,
    DeviceAdapterError,
    DeviceTimeoutError,
)
from ai_server_te_workbench.engine.precheck import precheck_fixture
from ai_server_te_workbench.models import (
    Comparison,
    DeviceUnderTest,
    Evidence,
    Fixture,
    JsonScalar,
    PrecheckStatus,
    ResultStatus,
    TestCase,
    TestPlan,
    TestResult,
    TestRun,
)


class TestRunner:
    def run(
        self,
        dut: DeviceUnderTest,
        fixture: Fixture,
        test_plan: TestPlan,
        adapter: DeviceAdapter,
    ) -> TestRun:
        if not isinstance(dut, DeviceUnderTest):
            raise TypeError("dut must be a DeviceUnderTest")
        if not isinstance(fixture, Fixture):
            raise TypeError("fixture must be a Fixture")
        if not isinstance(test_plan, TestPlan):
            raise TypeError("test_plan must be a TestPlan")
        if not isinstance(adapter, DeviceAdapter):
            raise TypeError("adapter must implement DeviceAdapter")

        run_started = perf_counter_ns()
        started_at = datetime.now(timezone.utc).isoformat()
        precheck = precheck_fixture(fixture)
        if precheck.status == PrecheckStatus.BLOCKED:
            results = tuple(
                TestResult(
                    test_case_id=case.id,
                    status=ResultStatus.BLOCKED,
                    expected=case.expected,
                    actual=None,
                    duration_ms=0,
                    attempts=1,
                    evidence=precheck.evidence,
                )
                for case in test_plan.cases
            )
        else:
            evidence_scope = f"{fixture.station_id}-{dut.serial_number}"
            results = tuple(
                self._execute_case(case, adapter, evidence_scope) for case in test_plan.cases
            )

        return TestRun(
            run_id=f"RUN-{uuid4()}",
            started_at=started_at,
            duration_ms=_elapsed_ms(run_started),
            dut=dut,
            fixture=fixture,
            test_plan=test_plan,
            precheck=precheck,
            results=results,
        )

    def _execute_case(
        self, case: TestCase, adapter: DeviceAdapter, evidence_scope: str
    ) -> TestResult:
        started = perf_counter_ns()
        prior_evidence: list[Evidence] = []

        for attempt in range(1, case.max_retries + 2):
            try:
                reader = _reader_for(case, adapter)
                actual = reader()
                status = _compare(case, actual)
                if status == ResultStatus.FAIL:
                    prior_evidence.append(
                        _measurement_evidence(
                            case, actual, adapter.source_name, attempt, evidence_scope
                        )
                    )
                return TestResult(
                    test_case_id=case.id,
                    status=status,
                    expected=case.expected,
                    actual=actual,
                    duration_ms=_elapsed_ms(started),
                    attempts=attempt,
                    evidence=tuple(prior_evidence),
                )
            except DeviceTimeoutError as error:
                prior_evidence.append(
                    _error_evidence(
                        case,
                        attempt,
                        adapter.source_name,
                        "timeout",
                        str(error),
                        evidence_scope,
                    )
                )
            except DeviceAdapterError as error:
                prior_evidence.append(
                    _error_evidence(
                        case,
                        attempt,
                        adapter.source_name,
                        "read-error",
                        str(error),
                        evidence_scope,
                    )
                )
            except (TypeError, ValueError) as error:
                prior_evidence.append(
                    _error_evidence(
                        case,
                        attempt,
                        adapter.source_name,
                        "invalid-data",
                        str(error),
                        evidence_scope,
                    )
                )
                break

        return TestResult(
            test_case_id=case.id,
            status=ResultStatus.ERROR,
            expected=case.expected,
            actual=None,
            duration_ms=_elapsed_ms(started),
            attempts=len(prior_evidence),
            evidence=tuple(prior_evidence),
        )


def _reader_for(case: TestCase, adapter: DeviceAdapter) -> Callable[[], JsonScalar]:
    readers: dict[str, Callable[[], JsonScalar]] = {
        "bmc_connectivity": adapter.get_bmc_status,
        "firmware_version": adapter.get_firmware_version,
        "gpu_device_count": adapter.get_gpu_count,
        "cpu_temperature": adapter.get_cpu_temperature,
    }
    try:
        return readers[case.id]
    except KeyError as error:
        raise DeviceAdapterError(f"no adapter reader is mapped for {case.id}") from error


def _compare(case: TestCase, actual: JsonScalar) -> ResultStatus:
    if case.comparison == Comparison.EQUALS:
        return ResultStatus.PASS if actual == case.expected else ResultStatus.FAIL
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        raise TypeError("maximum comparison received a non-numeric measurement")
    assert isinstance(case.expected, (int, float))
    return ResultStatus.PASS if actual <= case.expected else ResultStatus.FAIL


def _measurement_evidence(
    case: TestCase,
    actual: JsonScalar,
    source: str,
    attempt: int,
    evidence_scope: str,
) -> Evidence:
    return Evidence(
        id=f"E-{evidence_scope}-{case.id}-A{attempt}",
        source=source,
        observation=f"Measured value did not satisfy {case.comparison.value} requirement",
        expected=case.expected,
        actual=actual,
    )


def _error_evidence(
    case: TestCase,
    attempt: int,
    source: str,
    error_kind: str,
    detail: str,
    evidence_scope: str,
) -> Evidence:
    return Evidence(
        id=f"E-{evidence_scope}-{case.id}-A{attempt}",
        source=source,
        observation=f"{error_kind}: {detail}",
        expected=case.expected,
        actual=None,
    )


def _elapsed_ms(started_ns: int) -> int:
    return max(0, (perf_counter_ns() - started_ns) // 1_000_000)
