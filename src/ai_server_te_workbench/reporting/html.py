"""Dependency-free standalone HTML report renderer."""

from html import escape

from ai_server_te_workbench.models import ResultStatus
from ai_server_te_workbench.reporting.document import ReportDocument, display_value


def render_html(document: ReportDocument) -> str:
    if not isinstance(document, ReportDocument):
        raise TypeError("document must be a ReportDocument")

    run_rows = "".join(
        _row(
            item.label,
            item.run.run_id,
            item.run.dut.serial_number,
            item.run.dut.model,
            item.run.dut.role.value,
            item.run.fixture.station_id,
            item.run.fixture.fixture_id,
            item.run.precheck.status.value,
            item.run.status.value,
        )
        for item in document.runs
    )
    test_rows = "".join(
        _row(
            item.label,
            result.test_case_id,
            result.status.value,
            display_value(result.expected),
            display_value(result.actual),
            str(result.attempts),
            str(result.duration_ms),
        )
        for item in document.runs
        for result in item.run.results
    )
    failures = [
        (item.label, result)
        for item in document.runs
        for result in item.run.results
        if result.status is not ResultStatus.PASS
    ]
    failure_items = (
        "".join(
            "<li><strong>"
            f"{escape(label)} / {escape(result.test_case_id)}</strong>: "
            f"{escape(result.status.value)}, expected <code>{escape(display_value(result.expected))}</code>, "
            f"actual <code>{escape(display_value(result.actual))}</code></li>"
            for label, result in failures
        )
        or "<li>無</li>"
    )
    evidence_rows = "".join(
        _row(
            item.id,
            item.source,
            item.observation,
            display_value(item.expected),
            display_value(item.actual),
        )
        for item in document.evidence
    ) or _row("—", "—", "無異常 evidence", "—", "—")
    assessment = document.assessment

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(document.title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #172033; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }}
    th, td {{ border: 1px solid #ccd3df; padding: .55rem; text-align: left; vertical-align: top; }}
    th {{ background: #edf2f8; }}
    .notice {{ border-left: 4px solid #d97706; background: #fff7ed; padding: .8rem 1rem; }}
    code {{ background: #eef2f7; padding: .1rem .3rem; }}
  </style>
</head>
<body>
  <h1>{escape(document.title)}</h1>
  <p class="notice">⚠️ {escape(document.simulator_notice)}</p>
  <h2>執行環境</h2>
  <ul>
    <li>Application: <code>ai-server-te-workbench</code></li>
    <li>Mode: <code>deterministic simulator</code></li>
    <li>Generated at: <code>{escape(document.generated_at)}</code></li>
    <li>Test plan: <code>{escape(document.primary.test_plan.id)}</code> version <code>{escape(document.primary.test_plan.version)}</code></li>
  </ul>
  <h2>DUT 與治具</h2>
  <table><thead>{_head("Run", "Run ID", "Serial", "Model", "Role", "Station", "Fixture", "Precheck", "Run status")}</thead><tbody>{run_rows}</tbody></table>
  <h2>Test Summary</h2>
  <table><thead>{_head("Run", "Test case", "Status", "Expected", "Actual", "Attempts", "Duration (ms)")}</thead><tbody>{test_rows}</tbody></table>
  <h2>Failures</h2><ul>{failure_items}</ul>
  <h2>Evidence</h2>
  <table><thead>{_head("Evidence ID", "Source", "Observation", "Expected", "Actual")}</thead><tbody>{evidence_rows}</tbody></table>
  <h2>Troubleshooting Assessment</h2>
  <ul>
    <li>Classification: <code>{escape(assessment.classification.value)}</code></li>
    <li>Confidence: <code>{escape(assessment.confidence.value)}</code></li>
    <li>Evidence IDs: <code>{escape(", ".join(assessment.evidence_ids) or "—")}</code></li>
  </ul>
  <h3>Observation</h3><p>{escape(assessment.observation)}</p>
  <h3>Possible Causes</h3>{_html_list(assessment.possible_causes)}
  <h3>Verification Steps</h3>{_html_list(assessment.verification_steps)}
</body>
</html>
"""


def _head(*values: str) -> str:
    return "<tr>" + "".join(f"<th>{escape(value)}</th>" for value in values) + "</tr>"


def _row(*values: str) -> str:
    return "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>"


def _html_list(values: tuple[str, ...]) -> str:
    items = "".join(f"<li>{escape(value)}</li>" for value in values) or "<li>無</li>"
    return f"<ul>{items}</ul>"
