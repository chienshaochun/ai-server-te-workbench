"""Validated symptom matrix for DUT, golden-sample, and cross-station runs."""

from __future__ import annotations

from dataclasses import dataclass

from ai_server_te_workbench.models import DeviceRole, ResultStatus, TestRun


@dataclass(frozen=True)
class TroubleshootingMatrix:
    primary: TestRun
    golden: TestRun | None
    repeated: TestRun | None
    primary_symptoms: tuple[str, ...]
    golden_symptoms: tuple[str, ...] | None
    repeated_symptoms: tuple[str, ...] | None

    @property
    def golden_passed(self) -> bool:
        return self.golden_symptoms == ()

    @property
    def repeated_same_symptoms(self) -> bool:
        return (
            self.repeated_symptoms is not None and self.repeated_symptoms == self.primary_symptoms
        )


def build_matrix(
    primary: TestRun,
    golden: TestRun | None = None,
    repeated: TestRun | None = None,
) -> TroubleshootingMatrix:
    if not isinstance(primary, TestRun):
        raise TypeError("primary must be a TestRun")
    if primary.dut.role is not DeviceRole.DUT:
        raise ValueError("primary run must use a DUT")

    if golden is not None:
        _validate_comparison_run(golden, "golden")
        if golden.dut.role is not DeviceRole.GOLDEN_SAMPLE:
            raise ValueError("golden run must use a golden sample")
        if golden.fixture.station_id != primary.fixture.station_id:
            raise ValueError("golden run must use the primary station")
        _require_same_plan(primary, golden)

    if repeated is not None:
        _validate_comparison_run(repeated, "repeated")
        if repeated.dut.role is not DeviceRole.DUT:
            raise ValueError("repeated run must use a DUT")
        if repeated.dut.serial_number != primary.dut.serial_number:
            raise ValueError("repeated run must use the primary DUT")
        if repeated.fixture.station_id == primary.fixture.station_id:
            raise ValueError("repeated run must use a different station")
        _require_same_plan(primary, repeated)

    return TroubleshootingMatrix(
        primary=primary,
        golden=golden,
        repeated=repeated,
        primary_symptoms=_symptoms(primary),
        golden_symptoms=_symptoms(golden) if golden is not None else None,
        repeated_symptoms=_symptoms(repeated) if repeated is not None else None,
    )


def _validate_comparison_run(run: object, field_name: str) -> None:
    if not isinstance(run, TestRun):
        raise TypeError(f"{field_name} must be a TestRun")


def _require_same_plan(primary: TestRun, comparison: TestRun) -> None:
    primary_plan = (
        primary.test_plan.id,
        primary.test_plan.version,
        tuple(case.id for case in primary.test_plan.cases),
    )
    comparison_plan = (
        comparison.test_plan.id,
        comparison.test_plan.version,
        tuple(case.id for case in comparison.test_plan.cases),
    )
    if comparison_plan != primary_plan:
        raise ValueError("comparison runs must use the same test plan")


def _symptoms(run: TestRun) -> tuple[str, ...]:
    return tuple(
        result.test_case_id
        for result in run.results
        if result.status in (ResultStatus.FAIL, ResultStatus.ERROR)
    )
