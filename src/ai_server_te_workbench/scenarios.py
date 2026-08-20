"""Deterministic synthetic devices, fixtures, and fault scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_server_te_workbench.models import (
    Comparison,
    DeviceRole,
    DeviceUnderTest,
    Fixture,
    TestCase,
    TestPlan,
)


class FaultScenario(str, Enum):
    NONE = "none"
    BMC_TIMEOUT = "bmc_timeout"
    FIRMWARE_MISMATCH = "firmware_mismatch"
    GPU_MISSING = "gpu_missing"
    TEMPERATURE_HIGH = "temperature_high"
    FIXTURE_NETWORK_DOWN = "fixture_network_down"


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    dut: DeviceUnderTest
    fixture: Fixture
    fault: FaultScenario

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("scenario id must be text")
        if not self.id or not all(character.isalnum() or character in "_-" for character in self.id):
            raise ValueError("scenario id contains unsupported characters")
        if not isinstance(self.description, str):
            raise TypeError("scenario description must be text")
        if not self.description.strip():
            raise ValueError("scenario description cannot be empty")
        if not isinstance(self.dut, DeviceUnderTest):
            raise TypeError("dut must be a DeviceUnderTest")
        if not isinstance(self.fixture, Fixture):
            raise TypeError("fixture must be a Fixture")
        if not isinstance(self.fault, FaultScenario):
            raise TypeError("fault must be a FaultScenario")


def standard_test_plan() -> TestPlan:
    return TestPlan(
        id="AI-SERVER-BRINGUP",
        version="1.0.0",
        cases=(
            TestCase(
                id="bmc_connectivity",
                name="BMC connectivity",
                comparison=Comparison.EQUALS,
                expected=True,
                timeout_seconds=5,
                max_retries=1,
            ),
            TestCase(
                id="firmware_version",
                name="Firmware version",
                comparison=Comparison.EQUALS,
                expected="1.2.0",
            ),
            TestCase(
                id="gpu_device_count",
                name="GPU device count",
                comparison=Comparison.EQUALS,
                expected=4,
            ),
            TestCase(
                id="cpu_temperature",
                name="CPU temperature",
                comparison=Comparison.MAXIMUM,
                expected=85.0,
            ),
        ),
    )


def built_in_scenarios() -> tuple[Scenario, ...]:
    ready_fixture = _fixture("FIXTURE-01", "STATION-01")
    return (
        Scenario(
            id="healthy_dut",
            description="A healthy production DUT on a ready fixture.",
            dut=_dut("DUT-0001"),
            fixture=ready_fixture,
            fault=FaultScenario.NONE,
        ),
        Scenario(
            id="golden_sample",
            description="A known-good unit used for fixture cross-validation.",
            dut=_dut("GOLDEN-0001", role=DeviceRole.GOLDEN_SAMPLE),
            fixture=ready_fixture,
            fault=FaultScenario.NONE,
        ),
        Scenario(
            id="bmc_timeout",
            description="The DUT BMC cannot be reached on a ready station.",
            dut=_dut("DUT-0002", bmc_reachable=False),
            fixture=ready_fixture,
            fault=FaultScenario.BMC_TIMEOUT,
        ),
        Scenario(
            id="firmware_mismatch",
            description="The DUT firmware does not match the test plan requirement.",
            dut=_dut("DUT-0003", firmware_version="1.1.0"),
            fixture=ready_fixture,
            fault=FaultScenario.FIRMWARE_MISMATCH,
        ),
        Scenario(
            id="gpu_missing",
            description="One expected GPU is not enumerated by the DUT.",
            dut=_dut("DUT-0004", gpu_count=3),
            fixture=ready_fixture,
            fault=FaultScenario.GPU_MISSING,
        ),
        Scenario(
            id="temperature_high",
            description="The CPU temperature exceeds the test plan maximum.",
            dut=_dut("DUT-0005", cpu_temperature_c=96.0),
            fixture=ready_fixture,
            fault=FaultScenario.TEMPERATURE_HIGH,
        ),
        Scenario(
            id="fixture_network_down",
            description="The station network is unavailable before DUT testing begins.",
            dut=_dut("DUT-0006"),
            fixture=_fixture("FIXTURE-02", "STATION-02", network_ready=False),
            fault=FaultScenario.FIXTURE_NETWORK_DOWN,
        ),
    )


def _dut(
    serial_number: str,
    *,
    firmware_version: str = "1.2.0",
    bmc_reachable: bool = True,
    gpu_count: int = 4,
    cpu_temperature_c: float = 62.0,
    role: DeviceRole = DeviceRole.DUT,
) -> DeviceUnderTest:
    return DeviceUnderTest(
        serial_number=serial_number,
        model="AI-SERVER-X1",
        firmware_version=firmware_version,
        bmc_reachable=bmc_reachable,
        gpu_count=gpu_count,
        cpu_temperature_c=cpu_temperature_c,
        role=role,
    )


def _fixture(
    fixture_id: str,
    station_id: str,
    *,
    network_ready: bool = True,
) -> Fixture:
    return Fixture(
        fixture_id=fixture_id,
        station_id=station_id,
        network_ready=network_ready,
        power_ready=True,
        bmc_interface_ready=True,
        calibration_valid=True,
    )
