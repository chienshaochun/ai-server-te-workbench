"""Standalone reports for completed guided troubleshooting conversations."""

from dataclasses import dataclass
from html import escape

from ai_server_te_workbench.conversation.models import (
    SessionOutcome,
    TroubleshootingSession,
)
from ai_server_te_workbench.llm.models import AssistantExchange, TriageAdvice


@dataclass(frozen=True)
class GuidedReportDocument:
    session: TroubleshootingSession
    title: str = "AI Server Guided Troubleshooting Report"
    triage_advice: TriageAdvice | None = None
    assistant_exchanges: tuple[AssistantExchange, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.session, TroubleshootingSession):
            raise TypeError("session must be a TroubleshootingSession")
        if self.session.outcome is SessionOutcome.ACTIVE:
            raise ValueError("active session cannot be reported")
        if self.triage_advice is not None and not isinstance(self.triage_advice, TriageAdvice):
            raise TypeError("triage_advice must be TriageAdvice or None")
        if isinstance(self.assistant_exchanges, list):
            object.__setattr__(self, "assistant_exchanges", tuple(self.assistant_exchanges))
        if not isinstance(self.assistant_exchanges, tuple) or not all(
            isinstance(item, AssistantExchange) for item in self.assistant_exchanges
        ):
            raise TypeError("assistant_exchanges must contain AssistantExchange values")


def render_guided_markdown(document: GuidedReportDocument) -> str:
    _require_document(document)
    session = document.session
    lines = [
        f"# {document.title}",
        "",
        "> ⚠️ 本報告來自 generic AI server 引導式模擬器，不代表已確認硬體 root cause。",
        "",
        "## Case Summary",
        "",
        f"- Session ID: `{session.session_id}`",
        f"- Server model: `{_md(session.server_model)}`",
        f"- Problem: {_md(session.raw_problem)}",
        f"- Symptom category: `{session.symptom_category.value}`",
        f"- Matcher confidence: `{session.match_confidence:.2f}`",
        f"- Outcome: `{session.outcome.value}`",
        f"- Resolution ID: `{session.resolution_id or '—'}`",
        f"- History source: `{'synthetic demo data' if session.uses_synthetic_history else 'session data'}`",
        "",
        "## Troubleshooting Transcript",
        "",
    ]
    for turn in session.transcript:
        lines.extend(
            [
                f"### Step {turn.sequence}: `{turn.step_id}`",
                "",
                f"- Recommended check: {_md(turn.recommended_check_zh)}",
                f"- Question: {_md(turn.question_zh)}",
                f"- Answer: **{_md(turn.answer_label_zh)}**",
                f"- Observation: {_md(turn.observation_zh)}",
                f"- Evidence ID: `{turn.evidence_id}`",
            ]
        )
        if turn.safety_note_zh:
            lines.append(f"- Safety: {_md(turn.safety_note_zh)}")
        lines.append("")
    _append_ai_markdown(lines, document)
    lines.extend(
        [
            "## Handoff Boundary",
            "",
            "- `resolved` 表示此引導流程重測已恢復，不代表零件根因已完成實驗室確認。",
            "- `unresolved` 表示必要檢查尚未完成或 evidence 不足。",
            "- `escalated` 表示應攜帶本報告交由合格的硬體、韌體、網路或製造工程人員處理。",
            "",
        ]
    )
    return "\n".join(lines)


def _append_ai_markdown(lines: list[str], document: GuidedReportDocument) -> None:
    if document.triage_advice is None and not document.assistant_exchanges:
        return
    lines.extend(["## AI Assistance (advisory only)", ""])
    if document.triage_advice is not None:
        advice = document.triage_advice
        lines.extend(
            [
                f"- Source: `{advice.source.value}`",
                f"- Model: `{advice.model or '—'}`",
                f"- Summary: {_md(advice.summary_zh)}",
                f"- Reason: {_md(advice.reason_zh)}",
                "",
            ]
        )
    for index, exchange in enumerate(document.assistant_exchanges, start=1):
        lines.extend(
            [
                f"### Advisory Q&A {index}",
                "",
                f"- Question: {_md(exchange.question_zh)}",
                f"- Answer: {_md(exchange.answer.answer_zh)}",
                f"- Approved next action: {_md(exchange.answer.recommended_next_action_zh)}",
                f"- Related step: `{exchange.answer.related_step_id}`",
                f"- Model: `{exchange.answer.model}`",
            ]
        )
        if exchange.answer.safety_warning_zh:
            lines.append(f"- Safety: {_md(exchange.answer.safety_warning_zh)}")
        lines.append("")


def render_guided_html(document: GuidedReportDocument) -> str:
    _require_document(document)
    session = document.session
    turns = "".join(
        f"<section><h3>Step {turn.sequence}: <code>{escape(turn.step_id)}</code></h3>"
        f"<ul><li>Recommended check: {escape(turn.recommended_check_zh)}</li>"
        f"<li>Question: {escape(turn.question_zh)}</li>"
        f"<li>Answer: <strong>{escape(turn.answer_label_zh)}</strong></li>"
        f"<li>Observation: {escape(turn.observation_zh)}</li>"
        f"<li>Evidence ID: <code>{escape(turn.evidence_id)}</code></li>"
        + (f"<li>Safety: {escape(turn.safety_note_zh)}</li>" if turn.safety_note_zh else "")
        + "</ul></section>"
        for turn in session.transcript
    )
    history = "synthetic demo data" if session.uses_synthetic_history else "session data"
    ai_section = _render_ai_html(document)
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(document.title)}</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#172033}}.notice{{border-left:4px solid #d97706;background:#fff7ed;padding:.8rem 1rem}}code{{background:#eef2f7;padding:.1rem .3rem}}section{{border-bottom:1px solid #d7dde8}}</style></head>
<body><h1>{escape(document.title)}</h1><p class="notice">⚠️ 本報告來自 generic AI server 引導式模擬器，不代表已確認硬體 root cause。</p>
<h2>Case Summary</h2><ul><li>Session ID: <code>{escape(session.session_id)}</code></li><li>Server model: <code>{escape(session.server_model)}</code></li><li>Problem: {escape(session.raw_problem)}</li><li>Symptom category: <code>{escape(session.symptom_category.value)}</code></li><li>Matcher confidence: <code>{session.match_confidence:.2f}</code></li><li>Outcome: <code>{escape(session.outcome.value)}</code></li><li>Resolution ID: <code>{escape(session.resolution_id or "—")}</code></li><li>History source: <code>{history}</code></li></ul>
<h2>Troubleshooting Transcript</h2>{turns}{ai_section}<h2>Handoff Boundary</h2><ul><li>resolved 表示流程重測已恢復，不代表零件根因已確認。</li><li>unresolved 表示必要檢查未完成或 evidence 不足。</li><li>escalated 表示應攜帶報告交由合格工程人員處理。</li></ul></body></html>"""


def _render_ai_html(document: GuidedReportDocument) -> str:
    if document.triage_advice is None and not document.assistant_exchanges:
        return ""
    parts = ["<h2>AI Assistance (advisory only)</h2>"]
    if document.triage_advice is not None:
        advice = document.triage_advice
        parts.append(
            f"<ul><li>Source: <code>{escape(advice.source.value)}</code></li>"
            f"<li>Model: <code>{escape(advice.model or '—')}</code></li>"
            f"<li>Summary: {escape(advice.summary_zh)}</li>"
            f"<li>Reason: {escape(advice.reason_zh)}</li></ul>"
        )
    for index, exchange in enumerate(document.assistant_exchanges, start=1):
        safety = (
            f"<li>Safety: {escape(exchange.answer.safety_warning_zh)}</li>"
            if exchange.answer.safety_warning_zh
            else ""
        )
        parts.append(
            f"<section><h3>Advisory Q&amp;A {index}</h3><ul>"
            f"<li>Question: {escape(exchange.question_zh)}</li>"
            f"<li>Answer: {escape(exchange.answer.answer_zh)}</li>"
            f"<li>Approved next action: "
            f"{escape(exchange.answer.recommended_next_action_zh)}</li>"
            f"<li>Related step: <code>{escape(exchange.answer.related_step_id)}</code></li>"
            f"<li>Model: <code>{escape(exchange.answer.model)}</code></li>"
            f"{safety}</ul></section>"
        )
    return "".join(parts)


def _require_document(document: object) -> None:
    if not isinstance(document, GuidedReportDocument):
        raise TypeError("document must be a GuidedReportDocument")


def _md(value: str) -> str:
    return value.replace("\\", "\\\\").replace("`", "\\`").replace("|", "\\|")
