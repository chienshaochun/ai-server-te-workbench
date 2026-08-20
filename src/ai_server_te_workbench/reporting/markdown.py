"""Markdown report renderer."""

from ai_server_te_workbench.models import ResultStatus
from ai_server_te_workbench.reporting.document import ReportDocument, display_value


def render_markdown(document: ReportDocument) -> str:
    if not isinstance(document, ReportDocument):
        raise TypeError("document must be a ReportDocument")

    lines = [
        f"# {_md(document.title)}",
        "",
        f"> ⚠️ {_md(document.simulator_notice)}",
        "",
        "## 執行環境",
        "",
        "- Application: `ai-server-te-workbench`",
        "- Mode: `deterministic simulator`",
        f"- Generated at: `{_md(document.generated_at)}`",
        f"- Test plan: `{_md(document.primary.test_plan.id)}` "
        f"version `{_md(document.primary.test_plan.version)}`",
        "",
        "## DUT 與治具",
        "",
        "| Run | Run ID | Serial | Model | Role | Station | Fixture | Precheck | Run status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in document.runs:
        run = item.run
        lines.append(
            "| "
            + " | ".join(
                _md(value)
                for value in (
                    item.label,
                    run.run_id,
                    run.dut.serial_number,
                    run.dut.model,
                    run.dut.role.value,
                    run.fixture.station_id,
                    run.fixture.fixture_id,
                    run.precheck.status.value,
                    run.status.value,
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Test Summary",
            "",
            "| Run | Test case | Status | Expected | Actual | Attempts | Duration (ms) |",
            "|---|---|---|---|---|---:|---:|",
        ]
    )
    for item in document.runs:
        for result in item.run.results:
            lines.append(
                "| "
                + " | ".join(
                    _md(value)
                    for value in (
                        item.label,
                        result.test_case_id,
                        result.status.value,
                        display_value(result.expected),
                        display_value(result.actual),
                        str(result.attempts),
                        str(result.duration_ms),
                    )
                )
                + " |"
            )

    lines.extend(["", "## Failures", ""])
    failures = [
        (item.label, result)
        for item in document.runs
        for result in item.run.results
        if result.status is not ResultStatus.PASS
    ]
    if failures:
        for label, result in failures:
            lines.append(
                f"- **{_md(label)} / {_md(result.test_case_id)}**: "
                f"{_md(result.status.value)}, expected `{_md(display_value(result.expected))}`, "
                f"actual `{_md(display_value(result.actual))}`"
            )
    else:
        lines.append("- 無")

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Evidence ID | Source | Observation | Expected | Actual |",
            "|---|---|---|---|---|",
        ]
    )
    if document.evidence:
        for item in document.evidence:
            lines.append(
                "| "
                + " | ".join(
                    _md(value)
                    for value in (
                        item.id,
                        item.source,
                        item.observation,
                        display_value(item.expected),
                        display_value(item.actual),
                    )
                )
                + " |"
            )
    else:
        lines.append("| — | — | 無異常 evidence | — | — |")

    assessment = document.assessment
    lines.extend(
        [
            "",
            "## Troubleshooting Assessment",
            "",
            f"- Classification: `{_md(assessment.classification.value)}`",
            f"- Confidence: `{_md(assessment.confidence.value)}`",
            f"- Evidence IDs: `{_md(', '.join(assessment.evidence_ids) or '—')}`",
            "",
            "### Observation",
            "",
            _md(assessment.observation),
            "",
            "### Possible Causes",
            "",
            *_bullet_lines(assessment.possible_causes),
            "",
            "### Verification Steps",
            "",
            *_bullet_lines(assessment.verification_steps),
            "",
        ]
    )
    return "\n".join(lines)


def _bullet_lines(values: tuple[str, ...]) -> list[str]:
    return [f"- {_md(value)}" for value in values] if values else ["- 無"]


def _md(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")
