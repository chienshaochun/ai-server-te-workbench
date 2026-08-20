from dataclasses import replace

import pytest

from ai_server_te_workbench.adapters import MockDeviceAdapter, MockFault, MockFaultKind
from ai_server_te_workbench.engine import TestRunner as Runner
from ai_server_te_workbench.reporting import (
    build_report_document,
    render_html,
    render_markdown,
)
from ai_server_te_workbench.scenarios import Scenario, built_in_scenarios, standard_test_plan
from ai_server_te_workbench.troubleshooting import assess_runs


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


def golden_run(primary):
    golden = scenario_by_id("golden_sample")
    return Runner().run(
        golden.dut,
        primary.fixture,
        standard_test_plan(),
        MockDeviceAdapter(golden.dut),
    )


def repeated_run(primary):
    fixture = replace(
        primary.fixture,
        fixture_id="FIXTURE-SECOND",
        station_id="STATION-SECOND",
    )
    return Runner().run(
        primary.dut,
        fixture,
        standard_test_plan(),
        MockDeviceAdapter(primary.dut),
    )


@pytest.mark.parametrize("renderer", [render_markdown, render_html])
def test_passing_report_contains_required_sections_and_disclaimer(renderer) -> None:
    primary = execute("healthy_dut")
    document = build_report_document(primary, assess_runs(primary))

    output = renderer(document)

    for required_text in (
        "AI Server TE 檢測報告",
        "模擬器產生",
        "執行環境",
        "DUT 與治具",
        "Test Summary",
        "Failures",
        "Evidence",
        "Troubleshooting Assessment",
        "Possible Causes",
        "Verification Steps",
    ):
        assert required_text in output


def test_failure_report_includes_measurement_evidence_and_assessment() -> None:
    primary = execute("temperature_high")
    assessment = assess_runs(primary)
    document = build_report_document(primary, assessment)

    markdown = render_markdown(document)

    assert "cpu_temperature" in markdown
    assert "96.0" in markdown
    assert "inconclusive" in markdown
    assert assessment.evidence_ids[0] in markdown
    assert assessment.possible_causes[0] in markdown
    assert assessment.verification_steps[0] in markdown


def test_cross_validation_report_requires_every_referenced_evidence_run() -> None:
    primary = execute("gpu_missing")
    golden = golden_run(primary)
    repeated = repeated_run(primary)
    assessment = assess_runs(primary, golden=golden, repeated=repeated)

    with pytest.raises(ValueError, match="missing evidence"):
        build_report_document(primary, assessment)

    document = build_report_document(
        primary,
        assessment,
        golden=golden,
        repeated=repeated,
    )
    assert [item.label for item in document.runs] == [
        "Primary DUT",
        "Golden Sample",
        "Cross-station DUT",
    ]
    assert set(assessment.evidence_ids) <= {item.id for item in document.evidence}


def test_markdown_and_html_include_same_canonical_report_values() -> None:
    primary = execute("firmware_mismatch")
    golden = golden_run(primary)
    assessment = assess_runs(primary, golden=golden)
    document = build_report_document(primary, assessment, golden=golden)

    markdown = render_markdown(document)
    html = render_html(document)
    canonical_values = (
        primary.run_id,
        primary.dut.serial_number,
        primary.fixture.station_id,
        primary.test_plan.id,
        assessment.classification.value,
        assessment.confidence.value,
        *[result.test_case_id for result in primary.results],
        *assessment.evidence_ids,
    )

    for value in canonical_values:
        assert value in markdown
        assert value in html


def test_html_escapes_device_values_instead_of_executing_markup() -> None:
    primary = execute("healthy_dut")
    hostile_dut = replace(primary.dut, model="<script>alert('x')</script>")
    primary = replace(primary, dut=hostile_dut)
    document = build_report_document(primary, assess_runs(primary))

    html = render_html(document)

    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html


def test_rendering_same_document_is_deterministic() -> None:
    primary = execute("gpu_missing")
    document = build_report_document(primary, assess_runs(primary))

    assert render_markdown(document) == render_markdown(document)
    assert render_html(document) == render_html(document)


def test_html_report_is_standalone_utf8_document() -> None:
    primary = execute("healthy_dut")
    html = render_html(build_report_document(primary, assess_runs(primary)))

    assert html.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in html
    assert html.rstrip().endswith("</html>")


@pytest.mark.parametrize("renderer", [render_markdown, render_html])
def test_renderers_reject_non_report_document(renderer) -> None:
    with pytest.raises(TypeError, match="ReportDocument"):
        renderer("not-a-document")
