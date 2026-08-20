"""Streamlit entry point for the guided AI-server TE troubleshooting demo."""

import streamlit as st

from ai_server_te_workbench.conversation import (
    ConversationController,
    SessionOutcome,
    case_record_from_session,
    common_issues_for_model,
    match_issue,
    normalize_model_family,
)
from ai_server_te_workbench.knowledge import SymptomCategory, synthetic_case_history
from ai_server_te_workbench.knowledge.generic_ai_server import generic_knowledge_entries
from ai_server_te_workbench.reporting import (
    GuidedReportDocument,
    render_guided_html,
    render_guided_markdown,
)


st.set_page_config(page_title="AI Server TE Troubleshooting", page_icon="🛠️", layout="wide")

controller = ConversationController()
entries = {entry.category: entry for entry in generic_knowledge_entries()}

if "case_history" not in st.session_state:
    st.session_state.case_history = list(synthetic_case_history())
if "troubleshooting_session" not in st.session_state:
    st.session_state.troubleshooting_session = None
if "recorded_session_ids" not in st.session_state:
    st.session_state.recorded_session_ids = set()

st.title("AI Server TE Guided Troubleshooting")
st.caption("一次完成一個可驗證步驟，保留 evidence，最後產生交接報告。")
st.warning(
    "這是 generic AI server 模擬器：不連接、不控制也不修復真實硬體；"
    "建議涉及拆機時必須安全斷電並由合格人員執行。"
)


def reset_session() -> None:
    st.session_state.troubleshooting_session = None


session = st.session_state.troubleshooting_session
if session is None:
    st.subheader("1. 建立問題")
    server_model = st.text_input(
        "Server 型號",
        placeholder="例如：AI Server X1（請勿輸入客戶名稱、序號或密碼）",
    )
    entry_mode = st.radio("問題入口", ("常見問題", "自由文字"), horizontal=True)
    category = SymptomCategory.UNKNOWN
    confidence = 0.0
    problem = ""

    if entry_mode == "常見問題":
        try:
            summaries = common_issues_for_model(
                tuple(st.session_state.case_history), server_model or "Generic"
            )
        except ValueError:
            summaries = common_issues_for_model(tuple(st.session_state.case_history), "Generic")
        summary_by_label = {
            f"{entries[item.symptom_category].title_zh}｜resolved {item.resolved_case_count} cases｜同一解法 {item.resolution_consistency:.0%}": item
            for item in summaries
        }
        selected_label = st.selectbox("常見問題（synthetic demo history）", tuple(summary_by_label))
        selected = summary_by_label[selected_label]
        category = selected.symptom_category
        confidence = 1.0
        problem = entries[category].title_zh
        st.info("這些數字是匿名 synthetic case count，不是不同使用者人數。")
    else:
        problem = st.text_area(
            "描述遇到的問題",
            placeholder="例如：同一個 port 上這台可以，但是另一台 BMC 連不上",
            max_chars=1000,
        )

    if st.button("開始逐步排查", type="primary", use_container_width=True):
        try:
            normalized_model = normalize_model_family(server_model)
        except (TypeError, ValueError):
            normalized_model = None
        if normalized_model is None:
            st.error("請先輸入 Server 型號。")
        elif not problem.strip():
            st.error("請先描述問題。")
        else:
            if entry_mode == "自由文字":
                issue_match = match_issue(problem)
                category = (
                    SymptomCategory.UNKNOWN
                    if issue_match.needs_confirmation
                    else issue_match.category
                )
                confidence = issue_match.confidence
            st.session_state.troubleshooting_session = controller.start(
                server_model,
                problem,
                category,
                confidence,
            )
            st.rerun()
else:
    st.subheader("2. 逐步排查")
    col1, col2, col3 = st.columns(3)
    col1.metric("Server", session.server_model)
    col2.metric("Category", session.symptom_category.value)
    col3.metric("Outcome", session.outcome.value)

    if session.transcript:
        with st.expander(f"已完成 {len(session.transcript)} 個步驟", expanded=False):
            for turn in session.transcript:
                st.markdown(
                    f"**{turn.sequence}. {turn.recommended_check_zh}**  \n"
                    f"回答：{turn.answer_label_zh}  \n觀察：{turn.observation_zh}"
                )

    if session.outcome is SessionOutcome.ACTIVE:
        step = controller.current_step(session)
        st.markdown(f"### 下一個檢查：{step.recommended_check_zh}")
        if step.safety_note_zh:
            st.error(f"安全要求：{step.safety_note_zh}")
        answer_by_label = {branch.answer_label_zh: branch.answer_id for branch in step.branches}
        selected_answer = st.radio(step.question_zh, tuple(answer_by_label))
        if st.button("提交這一步", type="primary"):
            st.session_state.troubleshooting_session = controller.answer(
                session, answer_by_label[selected_answer]
            )
            st.rerun()
    else:
        if session.session_id not in st.session_state.recorded_session_ids:
            st.session_state.case_history.append(case_record_from_session(session))
            st.session_state.recorded_session_ids.add(session.session_id)
        status_renderer = {
            SessionOutcome.RESOLVED: st.success,
            SessionOutcome.UNRESOLVED: st.warning,
            SessionOutcome.ESCALATED: st.error,
        }[session.outcome]
        status_renderer(
            f"流程結束：{session.outcome.value}"
            + (f"｜resolution: {session.resolution_id}" if session.resolution_id else "")
        )
        report = GuidedReportDocument(session)
        markdown = render_guided_markdown(report)
        html = render_guided_html(report)
        left, right = st.columns(2)
        left.download_button(
            "下載 Markdown 報告",
            markdown,
            file_name=f"{session.session_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        right.download_button(
            "下載 HTML 報告",
            html,
            file_name=f"{session.session_id}.html",
            mime="text/html",
            use_container_width=True,
        )
        with st.expander("預覽報告"):
            st.markdown(markdown)

    if st.button("開始新的問題"):
        reset_session()
        st.rerun()
