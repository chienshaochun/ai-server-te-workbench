"""Validated, immutable domain models for simulated test engineering workflows."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum


JsonScalar = str | int | float | bool | None
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class DeviceRole(str, Enum):
    DUT = "dut"
    GOLDEN_SAMPLE = "golden_sample"


class Comparison(str, Enum):
    EQUALS = "equals"
    MAXIMUM = "maximum"


class ResultStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    ERROR = "error"


class PrecheckStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"


class RunStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    ERROR = "error"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TroubleshootingClassification(str, Enum):
    PASS = "pass"
    FAIL_REPRODUCIBLE = "fail_reproducible"
    BLOCKED_BY_FIXTURE = "blocked_by_fixture"
    SUSPECTED_HARDWARE = "suspected_hardware"
    SUSPECTED_FIRMWARE = "suspected_firmware"
    SUSPECTED_NETWORK = "suspected_network"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class DeviceUnderTest:
    serial_number: str
    model: str
    firmware_version: str
    bmc_reachable: bool
    gpu_count: int
    cpu_temperature_c: float
    role: DeviceRole = DeviceRole.DUT

    def __post_init__(self) -> None:
        _require_identifier(self.serial_number, "serial_number")
        _require_text(self.model, "model")
        _require_text(self.firmware_version, "firmware_version")
        _require_bool(self.bmc_reachable, "bmc_reachable")
        if not isinstance(self.gpu_count, int) or isinstance(self.gpu_count, bool):
            raise TypeError("gpu_count must be an integer")
        if self.gpu_count < 0 or self.gpu_count > 32:
            raise ValueError("gpu_count must be between 0 and 32")
        if not isinstance(self.cpu_temperature_c, (int, float)) or isinstance(
            self.cpu_temperature_c, bool
        ):
            raise TypeError("cpu_temperature_c must be numeric")
        temperature = float(self.cpu_temperature_c)
        if not math.isfinite(temperature) or not -100 <= temperature <= 200:
            raise ValueError("cpu_temperature_c is outside the supported simulator range")
        object.__setattr__(self, "cpu_temperature_c", temperature)
        if not isinstance(self.role, DeviceRole):
            raise TypeError("role must be a DeviceRole")


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    station_id: str
    network_ready: bool
    power_ready: bool
    bmc_interface_ready: bool
    calibration_valid: bool

    def __post_init__(self) -> None:
        _require_identifier(self.fixture_id, "fixture_id")
        _require_identifier(self.station_id, "station_id")
        for field_name in (
            "network_ready",
            "power_ready",
            "bmc_interface_ready",
            "calibration_valid",
        ):
            _require_bool(getattr(self, field_name), field_name)

    @property
    def ready(self) -> bool:
        return all(
            (
                self.network_ready,
                self.power_ready,
                self.bmc_interface_ready,
                self.calibration_valid,
            )
        )


@dataclass(frozen=True)
class TestCase:
    id: str
    name: str
    comparison: Comparison
    expected: JsonScalar
    timeout_seconds: float = 5.0
    max_retries: int = 0

    def __post_init__(self) -> None:
        _require_identifier(self.id, "test case id")
        _require_text(self.name, "test case name")
        if not isinstance(self.comparison, Comparison):
            raise TypeError("comparison must be a Comparison")
        _require_json_scalar(self.expected, "expected")
        if self.comparison == Comparison.MAXIMUM and not _is_number(self.expected):
            raise TypeError("maximum comparison requires a numeric expected value")
        if not isinstance(self.timeout_seconds, (int, float)) or isinstance(
            self.timeout_seconds, bool
        ):
            raise TypeError("timeout_seconds must be numeric")
        timeout = float(self.timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0 or timeout > 300:
            raise ValueError("timeout_seconds must be greater than 0 and at most 300")
        object.__setattr__(self, "timeout_seconds", timeout)
        if not isinstance(self.max_retries, int) or isinstance(self.max_retries, bool):
            raise TypeError("max_retries must be an integer")
        if not 0 <= self.max_retries <= 5:
            raise ValueError("max_retries must be between 0 and 5")


@dataclass(frozen=True)
class TestPlan:
    id: str
    version: str
    cases: tuple[TestCase, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.id, "test plan id")
        _require_text(self.version, "test plan version")
        if isinstance(self.cases, list):
            object.__setattr__(self, "cases", tuple(self.cases))
        if not isinstance(self.cases, tuple) or not self.cases:
            raise ValueError("test plan requires at least one test case")
        if not all(isinstance(case, TestCase) for case in self.cases):
            raise TypeError("cases must contain only TestCase values")
        identifiers = [case.id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("test plan cannot contain duplicate test case IDs")


@dataclass(frozen=True)
class Evidence:
    id: str
    source: str
    observation: str
    expected: JsonScalar = None
    actual: JsonScalar = None

    def __post_init__(self) -> None:
        _require_identifier(self.id, "evidence id")
        _require_text(self.source, "evidence source")
        _require_text(self.observation, "evidence observation")
        _require_json_scalar(self.expected, "expected")
        _require_json_scalar(self.actual, "actual")


@dataclass(frozen=True)
class TestResult:
    test_case_id: str
    status: ResultStatus
    expected: JsonScalar
    actual: JsonScalar
    duration_ms: int
    attempts: int
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.test_case_id, "test_case_id")
        if not isinstance(self.status, ResultStatus):
            raise TypeError("status must be a ResultStatus")
        _require_json_scalar(self.expected, "expected")
        _require_json_scalar(self.actual, "actual")
        if not isinstance(self.duration_ms, int) or isinstance(self.duration_ms, bool):
            raise TypeError("duration_ms must be an integer")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")
        if not isinstance(self.attempts, int) or isinstance(self.attempts, bool):
            raise TypeError("attempts must be an integer")
        if self.attempts <= 0:
            raise ValueError("attempts must be positive")
        if isinstance(self.evidence, list):
            object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(item, Evidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain only Evidence values")
        if self.status != ResultStatus.PASS and not self.evidence:
            raise ValueError("non-pass test results require evidence")


@dataclass(frozen=True)
class FixturePrecheckResult:
    status: PrecheckStatus
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, PrecheckStatus):
            raise TypeError("status must be a PrecheckStatus")
        if isinstance(self.evidence, list):
            object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(item, Evidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain only Evidence values")
        if self.status == PrecheckStatus.BLOCKED and not self.evidence:
            raise ValueError("blocked fixture precheck requires evidence")


@dataclass(frozen=True)
class TestRun:
    run_id: str
    started_at: str
    duration_ms: int
    dut: DeviceUnderTest
    fixture: Fixture
    test_plan: TestPlan
    precheck: FixturePrecheckResult
    results: tuple[TestResult, ...]

    def __post_init__(self) -> None:
        _require_identifier(self.run_id, "run_id")
        _require_text(self.started_at, "started_at")
        if not isinstance(self.duration_ms, int) or isinstance(self.duration_ms, bool):
            raise TypeError("duration_ms must be an integer")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")
        if not isinstance(self.dut, DeviceUnderTest):
            raise TypeError("dut must be a DeviceUnderTest")
        if not isinstance(self.fixture, Fixture):
            raise TypeError("fixture must be a Fixture")
        if not isinstance(self.test_plan, TestPlan):
            raise TypeError("test_plan must be a TestPlan")
        if not isinstance(self.precheck, FixturePrecheckResult):
            raise TypeError("precheck must be a FixturePrecheckResult")
        if isinstance(self.results, list):
            object.__setattr__(self, "results", tuple(self.results))
        if not isinstance(self.results, tuple) or not all(
            isinstance(item, TestResult) for item in self.results
        ):
            raise TypeError("results must contain only TestResult values")
        result_ids = tuple(result.test_case_id for result in self.results)
        plan_ids = tuple(case.id for case in self.test_plan.cases)
        if result_ids != plan_ids:
            raise ValueError("test results must match test plan order")

    @property
    def status(self) -> RunStatus:
        if self.precheck.status == PrecheckStatus.BLOCKED:
            return RunStatus.BLOCKED
        if any(result.status == ResultStatus.ERROR for result in self.results):
            return RunStatus.ERROR
        if any(result.status == ResultStatus.FAIL for result in self.results):
            return RunStatus.FAIL
        return RunStatus.PASS


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    if len(value) > 500:
        raise ValueError(f"{field_name} is too long")


def _require_identifier(value: object, field_name: str) -> None:
    _require_text(value, field_name)
    assert isinstance(value, str)
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} contains unsupported characters")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_json_scalar(value: object, field_name: str) -> None:
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise TypeError(f"{field_name} must be a JSON scalar")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
