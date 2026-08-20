import pytest

from ai_server_te_workbench.adapters import MockDeviceAdapter, MockFault, MockFaultKind
from ai_server_te_workbench.engine import TestRunner as Runner
from ai_server_te_workbench.models import (
    Comparison,
    ResultStatus,
    RunStatus,
    TestCase as DomainTestCase,
    TestPlan as DomainTestPlan,
)
from ai_server_te_workbench.scenarios import Scenario, built_in_scenarios, standard_test_plan


def scenario_by_id(scenario_id: str) -> Scenario:
    return next(scenario for scenario in built_in_scenarios() if scenario.id == scenario_id)


def run_scenario(scenario_id: str):
    scenario = scenario_by_id(scenario_id)
    faults = ()
    if scenario_id == "bmc_timeout":
        faults = (MockFault("bmc_connectivity", MockFaultKind.TIMEOUT, repeat=2),)
    adapter = MockDeviceAdapter(scenario.dut, faults=faults)
    run = Runner().run(scenario.dut, scenario.fixture, standard_test_plan(), adapter)
    return run, adapter


def test_healthy_dut_runs_four_cases_in_plan_order() -> None:
    run, adapter = run_scenario("healthy_dut")

    assert run.status is RunStatus.PASS
    assert [result.test_case_id for result in run.results] == [
        "bmc_connectivity",
        "firmware_version",
        "gpu_device_count",
        "cpu_temperature",
    ]
    assert all(result.status is ResultStatus.PASS for result in run.results)
    assert adapter.call_count() == 4
    assert run.started_at.endswith("+00:00")


@pytest.mark.parametrize(
    ("scenario_id", "failed_case", "actual"),
    [
        ("firmware_mismatch", "firmware_version", "1.1.0"),
        ("gpu_missing", "gpu_device_count", 3),
        ("temperature_high", "cpu_temperature", 96.0),
    ],
)
def test_dut_fault_produces_one_evidenced_failure(
    scenario_id: str, failed_case: str, actual: object
) -> None:
    run, _ = run_scenario(scenario_id)
    failures = [result for result in run.results if result.status is ResultStatus.FAIL]

    assert run.status is RunStatus.FAIL
    assert len(failures) == 1
    assert failures[0].test_case_id == failed_case
    assert failures[0].actual == actual
    assert len(failures[0].evidence) == 1


def test_fixture_failure_blocks_all_dut_measurements() -> None:
    run, adapter = run_scenario("fixture_network_down")

    assert run.status is RunStatus.BLOCKED
    assert all(result.status is ResultStatus.BLOCKED for result in run.results)
    assert adapter.call_count() == 0
    assert all(result.evidence for result in run.results)


def test_transient_timeout_recovers_on_retry_and_keeps_evidence() -> None:
    scenario = scenario_by_id("healthy_dut")
    adapter = MockDeviceAdapter(
        scenario.dut,
        faults=(MockFault("bmc_connectivity", MockFaultKind.TIMEOUT),),
    )

    run = Runner().run(scenario.dut, scenario.fixture, standard_test_plan(), adapter)
    bmc_result = run.results[0]

    assert run.status is RunStatus.PASS
    assert bmc_result.status is ResultStatus.PASS
    assert bmc_result.attempts == 2
    assert len(bmc_result.evidence) == 1
    assert "timeout" in bmc_result.evidence[0].observation


def test_permanent_timeout_exhausts_retry_and_returns_error() -> None:
    run, adapter = run_scenario("bmc_timeout")
    bmc_result = run.results[0]

    assert run.status is RunStatus.ERROR
    assert bmc_result.status is ResultStatus.ERROR
    assert bmc_result.attempts == 2
    assert len(bmc_result.evidence) == 2
    assert adapter.call_count("bmc_connectivity") == 2


def test_unknown_test_case_becomes_structured_error_instead_of_crashing() -> None:
    scenario = scenario_by_id("healthy_dut")
    plan = DomainTestPlan(
        id="UNKNOWN-PLAN",
        version="1.0",
        cases=(
            DomainTestCase(
                id="unknown_sensor",
                name="Unknown sensor",
                comparison=Comparison.EQUALS,
                expected=True,
            ),
        ),
    )

    run = Runner().run(
        scenario.dut,
        scenario.fixture,
        plan,
        MockDeviceAdapter(scenario.dut),
    )

    assert run.status is RunStatus.ERROR
    assert run.results[0].status is ResultStatus.ERROR
    assert "no adapter reader" in run.results[0].evidence[0].observation


def test_runner_rejects_object_without_hardware_adapter_contract() -> None:
    scenario = scenario_by_id("healthy_dut")

    with pytest.raises(TypeError, match="DeviceAdapter"):
        Runner().run(scenario.dut, scenario.fixture, standard_test_plan(), object())
