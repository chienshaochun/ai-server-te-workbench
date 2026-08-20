"""Validated canonical document shared by every output format."""

from __future__ import annotations

from dataclasses import dataclass

from ai_server_te_workbench.models import (
    Evidence,
    TestRun,
    TroubleshootingAssessment,
)


SIMULATOR_NOTICE = "本報告由模擬器產生，不代表真實硬體診斷；分類僅供測試工程排查與驗證。"


@dataclass(frozen=True)
class LabeledRun:
    label: str
    run: TestRun

    def __post_init__(self) -> None:
        if not isinstance(self.label, str):
            raise TypeError("label must be text")
        if not self.label.strip():
            raise ValueError("label cannot be empty")
        if not isinstance(self.run, TestRun):
            raise TypeError("run must be a TestRun")


@dataclass(frozen=True)
class ReportDocument:
    title: str
    simulator_notice: str
    generated_at: str
    runs: tuple[LabeledRun, ...]
    assessment: TroubleshootingAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title is required")
        if not isinstance(self.simulator_notice, str) or not self.simulator_notice.strip():
            raise ValueError("simulator_notice is required")
        if not isinstance(self.generated_at, str) or not self.generated_at.strip():
            raise ValueError("generated_at is required")
        if isinstance(self.runs, list):
            object.__setattr__(self, "runs", tuple(self.runs))
        if not isinstance(self.runs, tuple) or not self.runs:
            raise ValueError("at least one labeled run is required")
        if not all(isinstance(item, LabeledRun) for item in self.runs):
            raise TypeError("runs must contain only LabeledRun values")
        labels = tuple(item.label for item in self.runs)
        if len(labels) != len(set(labels)):
            raise ValueError("run labels must be unique")
        if not isinstance(self.assessment, TroubleshootingAssessment):
            raise TypeError("assessment must be a TroubleshootingAssessment")

        available_evidence = {item.id for item in self.evidence}
        missing = set(self.assessment.evidence_ids) - available_evidence
        if missing:
            raise ValueError(
                "report is missing evidence referenced by assessment: " + ", ".join(sorted(missing))
            )

    @property
    def primary(self) -> TestRun:
        return self.runs[0].run

    @property
    def evidence(self) -> tuple[Evidence, ...]:
        unique: dict[str, Evidence] = {}
        for labeled_run in self.runs:
            run = labeled_run.run
            for item in run.precheck.evidence:
                unique.setdefault(item.id, item)
            for result in run.results:
                for item in result.evidence:
                    unique.setdefault(item.id, item)
        return tuple(unique.values())


def build_report_document(
    primary: TestRun,
    assessment: TroubleshootingAssessment,
    *,
    golden: TestRun | None = None,
    repeated: TestRun | None = None,
) -> ReportDocument:
    if not isinstance(primary, TestRun):
        raise TypeError("primary must be a TestRun")
    if not isinstance(assessment, TroubleshootingAssessment):
        raise TypeError("assessment must be a TroubleshootingAssessment")
    if golden is not None and not isinstance(golden, TestRun):
        raise TypeError("golden must be a TestRun")
    if repeated is not None and not isinstance(repeated, TestRun):
        raise TypeError("repeated must be a TestRun")

    runs = [LabeledRun("Primary DUT", primary)]
    if golden is not None:
        runs.append(LabeledRun("Golden Sample", golden))
    if repeated is not None:
        runs.append(LabeledRun("Cross-station DUT", repeated))
    return ReportDocument(
        title="AI Server TE 檢測報告",
        simulator_notice=SIMULATOR_NOTICE,
        generated_at=primary.started_at,
        runs=tuple(runs),
        assessment=assessment,
    )


def display_value(value: object) -> str:
    if value is None:
        return "—"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)
