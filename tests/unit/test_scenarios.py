import pytest

from ai_server_te_workbench.models import Comparison, DeviceRole
from ai_server_te_workbench.scenarios import (
    FaultScenario,
    Scenario,
    built_in_scenarios,
    standard_test_plan,
)


def scenario_by_id(scenario_id: str) -> Scenario:
    return next(scenario for scenario in built_in_scenarios() if scenario.id == scenario_id)


def test_standard_plan_contains_four_required_ai_server_checks() -> None:
    plan = standard_test_plan()

    assert [case.id for case in plan.cases] == [
        "bmc_connectivity",
        "firmware_version",
        "gpu_device_count",
        "cpu_temperature",
    ]
    assert plan.cases[-1].comparison is Comparison.MAXIMUM
    assert plan.cases[-1].expected == 85.0


def test_scenario_catalog_contains_baselines_and_five_faults() -> None:
    scenarios = built_in_scenarios()

    assert len(scenarios) == 7
    assert len({scenario.id for scenario in scenarios}) == len(scenarios)
    assert {scenario.fault for scenario in scenarios} == set(FaultScenario)


def test_golden_sample_is_explicitly_distinguished_from_dut() -> None:
    golden = scenario_by_id("golden_sample")

    assert golden.dut.role is DeviceRole.GOLDEN_SAMPLE
    assert golden.fixture.ready is True


@pytest.mark.parametrize(
    ("scenario_id", "attribute", "expected"),
    [
        ("bmc_timeout", "bmc_reachable", False),
        ("firmware_mismatch", "firmware_version", "1.1.0"),
        ("gpu_missing", "gpu_count", 3),
        ("temperature_high", "cpu_temperature_c", 96.0),
    ],
)
def test_dut_fault_scenarios_change_the_expected_measurement(
    scenario_id: str, attribute: str, expected: object
) -> None:
    scenario = scenario_by_id(scenario_id)

    assert getattr(scenario.dut, attribute) == expected
    assert scenario.fixture.ready is True


def test_fixture_network_fault_blocks_station_readiness() -> None:
    scenario = scenario_by_id("fixture_network_down")

    assert scenario.dut.bmc_reachable is True
    assert scenario.fixture.network_ready is False
    assert scenario.fixture.ready is False


def test_scenario_rejects_unvalidated_fault_value() -> None:
    healthy = scenario_by_id("healthy_dut")

    with pytest.raises(TypeError, match="FaultScenario"):
        Scenario(
            id="invalid",
            description="Invalid fault representation",
            dut=healthy.dut,
            fixture=healthy.fixture,
            fault="none",
        )
