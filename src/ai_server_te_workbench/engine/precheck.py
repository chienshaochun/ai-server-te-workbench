"""Station readiness checks that prevent fixture problems from becoming DUT failures."""

from ai_server_te_workbench.models import (
    Evidence,
    Fixture,
    FixturePrecheckResult,
    PrecheckStatus,
)


_CHECK_LABELS = {
    "network_ready": "Station network is unavailable",
    "power_ready": "Fixture power is unavailable",
    "bmc_interface_ready": "BMC interface is unavailable",
    "calibration_valid": "Fixture calibration is invalid or expired",
}


def precheck_fixture(fixture: Fixture) -> FixturePrecheckResult:
    if not isinstance(fixture, Fixture):
        raise TypeError("fixture must be a Fixture")

    failures = tuple(
        Evidence(
            id=f"E-FIXTURE-{field_name}",
            source=f"fixture:{fixture.fixture_id}",
            observation=observation,
            expected=True,
            actual=False,
        )
        for field_name, observation in _CHECK_LABELS.items()
        if not getattr(fixture, field_name)
    )
    status = PrecheckStatus.BLOCKED if failures else PrecheckStatus.READY
    return FixturePrecheckResult(status=status, evidence=failures)
