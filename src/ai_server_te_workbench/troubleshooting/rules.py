"""Conservative troubleshooting rules that report suspicions, never confirmed root cause."""

from __future__ import annotations

from ai_server_te_workbench.models import (
    Confidence,
    PrecheckStatus,
    TroubleshootingAssessment,
    TroubleshootingClassification,
)
from ai_server_te_workbench.troubleshooting.matrix import TroubleshootingMatrix, build_matrix


def assess_runs(primary, golden=None, repeated=None) -> TroubleshootingAssessment:
    matrix = build_matrix(primary, golden, repeated)
    evidence_ids = _evidence_ids(matrix)

    if matrix.primary.precheck.status is PrecheckStatus.BLOCKED:
        return _assessment(
            TroubleshootingClassification.BLOCKED_BY_FIXTURE,
            "Primary station readiness checks failed before DUT measurements began.",
            evidence_ids,
            Confidence.HIGH,
        )

    if not matrix.primary_symptoms:
        return TroubleshootingAssessment(
            classification=TroubleshootingClassification.PASS,
            observation="All primary DUT measurements satisfied the test plan.",
            evidence_ids=evidence_ids,
            possible_causes=(),
            verification_steps=(),
            confidence=Confidence.HIGH,
        )

    if matrix.golden is not None and matrix.golden.precheck.status is PrecheckStatus.BLOCKED:
        return _assessment(
            TroubleshootingClassification.BLOCKED_BY_FIXTURE,
            "Golden-sample validation was blocked by the primary station readiness state.",
            evidence_ids,
            Confidence.HIGH,
        )

    if matrix.golden_symptoms:
        if set(matrix.golden_symptoms) & set(matrix.primary_symptoms):
            return _assessment(
                TroubleshootingClassification.BLOCKED_BY_FIXTURE,
                "The DUT and golden sample showed a shared symptom on the same station.",
                evidence_ids,
                Confidence.MEDIUM,
            )
        return _assessment(
            TroubleshootingClassification.INCONCLUSIVE,
            "The DUT and golden sample produced different symptoms on the same station.",
            evidence_ids,
            Confidence.LOW,
        )

    if matrix.repeated_symptoms is not None:
        if matrix.repeated_symptoms == ():
            return _assessment(
                TroubleshootingClassification.INCONCLUSIVE,
                "The original symptom did not reproduce on the second ready station.",
                evidence_ids,
                Confidence.LOW,
            )
        if not matrix.repeated_same_symptoms:
            return _assessment(
                TroubleshootingClassification.INCONCLUSIVE,
                "The second station produced a different symptom from the primary run.",
                evidence_ids,
                Confidence.LOW,
            )
        if matrix.golden_passed:
            return _suspected_dut_assessment(matrix, evidence_ids, Confidence.HIGH)
        return _assessment(
            TroubleshootingClassification.FAIL_REPRODUCIBLE,
            "The same DUT symptom reproduced on two ready stations without a golden comparison.",
            evidence_ids,
            Confidence.MEDIUM,
        )

    if matrix.golden_passed:
        return _suspected_dut_assessment(matrix, evidence_ids, Confidence.MEDIUM)

    return _assessment(
        TroubleshootingClassification.INCONCLUSIVE,
        "The primary DUT has a symptom, but no valid isolation comparison is available.",
        evidence_ids,
        Confidence.LOW,
    )


def _suspected_dut_assessment(
    matrix: TroubleshootingMatrix,
    evidence_ids: tuple[str, ...],
    confidence: Confidence,
) -> TroubleshootingAssessment:
    symptoms = set(matrix.primary_symptoms)
    if symptoms == {"firmware_version"}:
        classification = TroubleshootingClassification.SUSPECTED_FIRMWARE
        observation = "The DUT firmware mismatch remained isolated from a passing golden sample."
    elif symptoms == {"bmc_connectivity"}:
        classification = TroubleshootingClassification.SUSPECTED_NETWORK
        observation = "The DUT BMC communication symptom was absent from the golden sample."
    elif symptoms and symptoms <= {"gpu_device_count", "cpu_temperature"}:
        classification = TroubleshootingClassification.SUSPECTED_HARDWARE
        observation = "The DUT hardware-facing symptom was absent from the golden sample."
    else:
        classification = TroubleshootingClassification.FAIL_REPRODUCIBLE
        observation = "The DUT-specific symptom was absent from the golden sample."
    return _assessment(classification, observation, evidence_ids, confidence)


def _assessment(
    classification: TroubleshootingClassification,
    observation: str,
    evidence_ids: tuple[str, ...],
    confidence: Confidence,
) -> TroubleshootingAssessment:
    causes, steps = _guidance(classification)
    return TroubleshootingAssessment(
        classification=classification,
        observation=observation,
        evidence_ids=evidence_ids,
        possible_causes=causes,
        verification_steps=steps,
        confidence=confidence,
    )


def _guidance(
    classification: TroubleshootingClassification,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    guidance = {
        TroubleshootingClassification.BLOCKED_BY_FIXTURE: (
            ("Station network, power, interface, calibration, or test-program path",),
            ("Restore station readiness and rerun the golden sample before judging the DUT",),
        ),
        TroubleshootingClassification.SUSPECTED_FIRMWARE: (
            ("Incorrect firmware image, configuration, or incomplete update",),
            ("Verify approved image checksum and reflash procedure, then rerun the test plan",),
        ),
        TroubleshootingClassification.SUSPECTED_NETWORK: (
            ("DUT BMC network path, BMC service, or BMC firmware",),
            ("Inspect link state and addressing, then test BMC access with an approved tool",),
        ),
        TroubleshootingClassification.SUSPECTED_HARDWARE: (
            ("Device seating, power delivery, cooling contact, sensor path, or component",),
            ("Power down safely and perform the listed physical inspection before retesting",),
        ),
        TroubleshootingClassification.FAIL_REPRODUCIBLE: (
            ("Persistent DUT-specific issue or test-plan compatibility issue",),
            ("Collect platform logs and compare configuration with the approved golden unit",),
        ),
        TroubleshootingClassification.INCONCLUSIVE: (
            ("Intermittent behavior, conflicting evidence, or incomplete comparison",),
            ("Repeat with a ready station and golden sample while preserving all evidence",),
        ),
    }
    return guidance[classification]


def _evidence_ids(matrix: TroubleshootingMatrix) -> tuple[str, ...]:
    identifiers: list[str] = []
    for run in (matrix.primary, matrix.golden, matrix.repeated):
        if run is None:
            continue
        for evidence in (
            *run.precheck.evidence,
            *(e for result in run.results for e in result.evidence),
        ):
            if evidence.id not in identifiers:
                identifiers.append(evidence.id)
    return tuple(identifiers)
