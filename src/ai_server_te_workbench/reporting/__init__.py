"""Canonical report document plus Markdown and standalone HTML renderers."""

from ai_server_te_workbench.reporting.document import (
    LabeledRun,
    ReportDocument,
    build_report_document,
)
from ai_server_te_workbench.reporting.html import render_html
from ai_server_te_workbench.reporting.guided import (
    GuidedReportDocument,
    render_guided_html,
    render_guided_markdown,
)
from ai_server_te_workbench.reporting.markdown import render_markdown

__all__ = [
    "LabeledRun",
    "GuidedReportDocument",
    "ReportDocument",
    "build_report_document",
    "render_html",
    "render_guided_html",
    "render_guided_markdown",
    "render_markdown",
]
