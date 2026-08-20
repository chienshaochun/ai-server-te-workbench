from ai_server_te_workbench.engine.precheck import precheck_fixture
from ai_server_te_workbench.models import Fixture, PrecheckStatus


def make_fixture(**overrides: bool) -> Fixture:
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


def test_ready_fixture_has_no_failure_evidence() -> None:
    result = precheck_fixture(make_fixture())

    assert result.status is PrecheckStatus.READY
    assert result.evidence == ()


def test_each_failed_station_check_produces_traceable_evidence() -> None:
    result = precheck_fixture(make_fixture(network_ready=False, calibration_valid=False))

    assert result.status is PrecheckStatus.BLOCKED
    assert len(result.evidence) == 2
    assert {item.id for item in result.evidence} == {
        "E-FIXTURE-network_ready",
        "E-FIXTURE-calibration_valid",
    }
    assert all(item.source == "fixture:FIXTURE-01" for item in result.evidence)


def test_precheck_rejects_non_fixture_input() -> None:
    try:
        precheck_fixture("FIXTURE-01")
    except TypeError as error:
        assert "Fixture" in str(error)
    else:
        raise AssertionError("non-Fixture input was accepted")
