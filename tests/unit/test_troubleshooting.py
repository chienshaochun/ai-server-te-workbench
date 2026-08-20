from dataclasses import replace

import pytest

from ai_server_te_workbench.adapters import MockDeviceAdapter, MockFault, MockFaultKind
from ai_server_te_workbench.engine import TestRunner as Runner
from ai_server_te_workbench.models import (
    Confidence,
    DeviceRole,
    RunStatus,
    TroubleshootingClassification,
)
from ai_server_te_workbench.scenarios import Scenario, built_in_scenarios, standard_test_plan
from ai_server_te_workbench.troubleshooting import assess_runs, build_matrix


def scenario_by_id(scenario_id: str) -> Scenario:
    return next(scenario for scenario in built_in_scenarios() if scenario.id == scenario_id)


def execute(scenario_id: str):
    scenario = scenario_by_id(scenario_id)
    faults = ()
    if scenario_id == "bmc_timeout":
        faults = (MockFault("bmc_connectivity", MockFaultKind.TIMEOUT, repeat=2),)
    return Runner().run(
        scenario.dut,
        scenario.fixture,
        standard_test_plan(),
        MockDeviceAdapter(scenario.dut, faults),
    )


def healthy_golden(primary_run):
    golden = scenario_by_id("golden_sample")
    return Runner().run(
        golden.dut,
        primary_run.fixture,
        standard_test_plan(),
        MockDeviceAdapter(golden.dut),
    )


def repeat_on_second_station(primary_run, *, healthy: bool = False):
    second_fixture = replace(
        primary_run.fixture,
        fixture_id="FIXTURE-SECOND",
        station_id="STATION-SECOND",
    )
    repeated_dut = primary_run.dut
    if healthy:
        repeated_dut = replace(
            primary_run.dut,
            firmware_version="1.2.0",
            bmc_reachable=True,
            gpu_count=4,
            cpu_temperature_c=62.0,
        )
    faults = ()
    if not healthy and primary_run.results[0].status.value == "error":
        faults = (MockFault("bmc_connectivity", MockFaultKind.TIMEOUT, repeat=2),)
    return Runner().run(
        repeated_dut,
        second_fixture,
        standard_test_plan(),
        MockDeviceAdapter(repeated_dut, faults),
    )


def test_passing_primary_run_requires_no_isolation_comparison() -> None:
    assessment = assess_runs(execute("healthy_dut"))

    assert assessment.classification is TroubleshootingClassification.PASS
    assert assessment.confidence is Confidence.HIGH
    assert assessment.possible_causes == ()
    assert assessment.verification_steps == ()


def test_fixture_precheck_failure_is_not_reported_as_dut_failure() -> None:
    assessment = assess_runs(execute("fixture_network_down"))

    assert assessment.classification is TroubleshootingClassification.BLOCKED_BY_FIXTURE
    assert assessment.confidence is Confidence.HIGH
    assert "E-FIXTURE-network_ready" in assessment.evidence_ids


def test_failed_dut_without_comparison_remains_inconclusive() -> None:
    assessment = assess_runs(execute("gpu_missing"))

    assert assessment.classification is TroubleshootingClassification.INCONCLUSIVE
    assert assessment.confidence is Confidence.LOW


@pytest.mark.parametrize(
    ("scenario_id", "classification"),
    [
        ("firmware_mismatch", TroubleshootingClassification.SUSPECTED_FIRMWARE),
        ("gpu_missing", TroubleshootingClassification.SUSPECTED_HARDWARE),
        ("temperature_high", TroubleshootingClassification.SUSPECTED_HARDWARE),
        ("bmc_timeout", TroubleshootingClassification.SUSPECTED_NETWORK),
    ],
)
def test_passing_golden_sample_isolates_test_specific_dut_path(
    scenario_id: str,
    classification: TroubleshootingClassification,
) -> None:
    primary = execute(scenario_id)
    assessment = assess_runs(primary, golden=healthy_golden(primary))

    assert assessment.classification is classification
    assert assessment.confidence is Confidence.MEDIUM
    assert assessment.observation
    assert assessment.possible_causes
    assert assessment.verification_steps


def test_shared_golden_and_dut_symptom_points_back_to_station_path() -> None:
    primary = execute("gpu_missing")
    golden = scenario_by_id("golden_sample")
    failing_golden_dut = replace(golden.dut, gpu_count=3)
    golden_run = Runner().run(
        failing_golden_dut,
        primary.fixture,
        standard_test_plan(),
        MockDeviceAdapter(failing_golden_dut),
    )

    assessment = assess_runs(primary, golden=golden_run)

    assert assessment.classification is TroubleshootingClassification.BLOCKED_BY_FIXTURE
    assert assessment.confidence is Confidence.MEDIUM
    assert len(assessment.evidence_ids) == 2


def test_same_symptom_on_two_stations_is_reproducible_without_golden() -> None:
    primary = execute("gpu_missing")
    repeated = repeat_on_second_station(primary)

    matrix = build_matrix(primary, repeated=repeated)
    assessment = assess_runs(primary, repeated=repeated)

    assert matrix.repeated_same_symptoms is True
    assert assessment.classification is TroubleshootingClassification.FAIL_REPRODUCIBLE
    assert assessment.confidence is Confidence.MEDIUM


def test_golden_pass_plus_cross_station_reproduction_raises_confidence() -> None:
    primary = execute("gpu_missing")
    assessment = assess_runs(
        primary,
        golden=healthy_golden(primary),
        repeated=repeat_on_second_station(primary),
    )

    assert assessment.classification is TroubleshootingClassification.SUSPECTED_HARDWARE
    assert assessment.confidence is Confidence.HIGH
    assert len(assessment.evidence_ids) == 2


def test_symptom_that_does_not_reproduce_remains_inconclusive() -> None:
    primary = execute("gpu_missing")
    assessment = assess_runs(primary, repeated=repeat_on_second_station(primary, healthy=True))

    assert assessment.classification is TroubleshootingClassification.INCONCLUSIVE
    assert assessment.confidence is Confidence.LOW


def test_golden_comparison_requires_golden_role_on_same_station() -> None:
    primary = execute("gpu_missing")
    not_golden = replace(primary, dut=replace(primary.dut, role=DeviceRole.DUT))

    with pytest.raises(ValueError, match="golden sample"):
        build_matrix(primary, golden=not_golden)


def test_repeated_comparison_requires_same_dut_on_different_station() -> None:
    primary = execute("gpu_missing")

    with pytest.raises(ValueError, match="different station"):
        build_matrix(primary, repeated=primary)


def test_primary_failure_and_all_comparison_evidence_remain_traceable() -> None:
    primary = execute("firmware_mismatch")
    repeated = repeat_on_second_station(primary)
    assessment = assess_runs(
        primary,
        golden=healthy_golden(primary),
        repeated=repeated,
    )

    assert primary.status is RunStatus.FAIL
    assert len(assessment.evidence_ids) == 2
    assert len(set(assessment.evidence_ids)) == 2
