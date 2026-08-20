from dataclasses import FrozenInstanceError

import pytest

from ai_server_te_workbench.models import (
    Comparison,
    DeviceUnderTest,
    Evidence,
    Fixture,
    ResultStatus,
    TestCase as DomainTestCase,
    TestPlan as DomainTestPlan,
    TestResult as DomainTestResult,
)


def make_dut(**overrides: object) -> DeviceUnderTest:
    values = {
        "serial_number": "DUT-1000",
        "model": "AI-SERVER-X1",
        "firmware_version": "1.2.0",
        "bmc_reachable": True,
        "gpu_count": 4,
        "cpu_temperature_c": 60.0,
    }
    values.update(overrides)
    return DeviceUnderTest(**values)


def make_fixture(**overrides: object) -> Fixture:
    values = {
        "fixture_id": "FIXTURE-01",
        "station_id": "STATION-01",
        "network_ready": True,
        "power_ready": True,
        "bmc_interface_ready": True,
        "calibration_valid": True,
    }
    values.update(overrides)
    return Fixture(**values)


def make_case(case_id: str = "bmc_connectivity") -> DomainTestCase:
    return DomainTestCase(
        id=case_id,
        name="BMC connectivity",
        comparison=Comparison.EQUALS,
        expected=True,
    )


def make_evidence() -> Evidence:
    return Evidence(
        id="E-BMC-01",
        source="mock_bmc",
        observation="BMC did not respond",
        expected=True,
        actual=False,
    )


def test_fixture_is_ready_only_when_every_station_check_passes() -> None:
    assert make_fixture().ready is True
    assert make_fixture(network_ready=False).ready is False
    assert make_fixture(calibration_valid=False).ready is False


def test_domain_models_are_immutable() -> None:
    dut = make_dut()

    with pytest.raises(FrozenInstanceError):
        dut.gpu_count = 3


@pytest.mark.parametrize("serial", ["", "has space", "bad/slash"])
def test_dut_rejects_invalid_serial_numbers(serial: str) -> None:
    with pytest.raises(ValueError):
        make_dut(serial_number=serial)


@pytest.mark.parametrize("gpu_count", [-1, 33])
def test_dut_rejects_gpu_count_outside_simulator_range(gpu_count: int) -> None:
    with pytest.raises(ValueError):
        make_dut(gpu_count=gpu_count)


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), 201.0])
def test_dut_rejects_invalid_temperature(temperature: float) -> None:
    with pytest.raises(ValueError):
        make_dut(cpu_temperature_c=temperature)


def test_boolean_fields_reject_integer_substitutes() -> None:
    with pytest.raises(TypeError):
        make_fixture(network_ready=1)


def test_maximum_comparison_requires_numeric_expected_value() -> None:
    with pytest.raises(TypeError):
        DomainTestCase(
            id="temperature",
            name="Temperature",
            comparison=Comparison.MAXIMUM,
            expected="85",
        )


@pytest.mark.parametrize("timeout", [0, -1, 301])
def test_test_case_rejects_invalid_timeout(timeout: int) -> None:
    with pytest.raises(ValueError):
        DomainTestCase(
            id="bmc",
            name="BMC",
            comparison=Comparison.EQUALS,
            expected=True,
            timeout_seconds=timeout,
        )


def test_test_plan_normalizes_case_list_to_immutable_tuple() -> None:
    plan = DomainTestPlan(id="PLAN-1", version="1.0", cases=[make_case()])

    assert isinstance(plan.cases, tuple)


def test_test_plan_rejects_duplicate_case_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        DomainTestPlan(id="PLAN-1", version="1.0", cases=(make_case(), make_case()))


def test_non_pass_result_requires_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence"):
        DomainTestResult(
            test_case_id="bmc_connectivity",
            status=ResultStatus.FAIL,
            expected=True,
            actual=False,
            duration_ms=50,
            attempts=1,
        )


def test_result_normalizes_evidence_list_to_tuple() -> None:
    result = DomainTestResult(
        test_case_id="bmc_connectivity",
        status=ResultStatus.FAIL,
        expected=True,
        actual=False,
        duration_ms=50,
        attempts=2,
        evidence=[make_evidence()],
    )

    assert isinstance(result.evidence, tuple)
    assert result.evidence[0].actual is False


def test_pass_result_can_be_recorded_without_failure_evidence() -> None:
    result = DomainTestResult(
        test_case_id="bmc_connectivity",
        status=ResultStatus.PASS,
        expected=True,
        actual=True,
        duration_ms=10,
        attempts=1,
    )

    assert result.status is ResultStatus.PASS
