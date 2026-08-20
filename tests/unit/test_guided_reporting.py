from dataclasses import replace

import pytest

from ai_server_te_workbench.conversation import ConversationController
from ai_server_te_workbench.knowledge import SymptomCategory
from ai_server_te_workbench.reporting import (
    GuidedReportDocument,
    render_guided_html,
    render_guided_markdown,
)


def resolved_session():
    controller = ConversationController()
    session = controller.start(
        "AI Server X1",
        "網路連不上",
        SymptomCategory.NETWORK_UNREACHABLE,
        0.82,
    )
    for answer in ("bmc", "yes", "yes"):
        session = controller.answer(session, answer)
    return session


def test_guided_markdown_and_html_share_session_and_transcript_values() -> None:
    session = resolved_session()
    document = GuidedReportDocument(session)
    markdown = render_guided_markdown(document)
    html = render_guided_html(document)

    values = (
        session.session_id,
        session.server_model,
        session.raw_problem,
        session.symptom_category.value,
        session.outcome.value,
        session.resolution_id,
        *[turn.step_id for turn in session.transcript],
        *[turn.evidence_id for turn in session.transcript],
    )
    for value in values:
        assert value in markdown
        assert value in html
    assert "synthetic demo data" in markdown
    assert "root cause" in html


def test_guided_html_escapes_user_supplied_model_and_problem() -> None:
    session = replace(
        resolved_session(),
        server_model="<script>model</script>",
        raw_problem="<img src=x onerror=alert(1)>",
    )

    html = render_guided_html(GuidedReportDocument(session))

    assert "<script>model" not in html
    assert "&lt;script&gt;model" in html
    assert "<img src=x" not in html


def test_active_session_cannot_generate_final_report() -> None:
    session = ConversationController().start(
        "Model X",
        "GPU missing",
        SymptomCategory.GPU_MISSING,
        0.82,
    )

    with pytest.raises(ValueError, match="active"):
        GuidedReportDocument(session)


@pytest.mark.parametrize("renderer", [render_guided_markdown, render_guided_html])
def test_guided_renderers_reject_wrong_document_type(renderer) -> None:
    with pytest.raises(TypeError, match="GuidedReportDocument"):
        renderer("invalid")
