"""Streamlit entry point for the guided AI-server TE troubleshooting demo."""

import streamlit as st

from ai_server_te_workbench.conversation import (
    ConversationController,
    SessionOutcome,
    case_record_from_session,
    match_issue,
    normalize_model_family,
)
from ai_server_te_workbench.knowledge import SymptomCategory, synthetic_case_history
from ai_server_te_workbench.knowledge import synthetic_case_patterns
from ai_server_te_workbench.reporting import (
    GuidedReportDocument,
    render_guided_html,
    render_guided_markdown,
)


st.set_page_config(page_title="AI Server TE Troubleshooting", page_icon="🛠️", layout="wide")

controller = ConversationController()

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
        patterns = synthetic_case_patterns()
        pattern_by_label = {
            f"{pattern.title_zh}｜{pattern.case_count} synthetic cases｜"
            f"resolved {pattern.resolution_rate:.0%}": pattern
            for pattern in patterns
        }
        selected_label = st.selectbox("常見問題（synthetic demo history）", tuple(pattern_by_label))
        selected = pattern_by_label[selected_label]
        category = selected.symptom_category
        confidence = 1.0
        problem = selected.example_problem_zh
        st.markdown(f"**模擬現象：** {selected.example_problem_zh}")
        st.markdown(f"**建議先檢查：** {selected.recommended_first_check_zh}")
        total_cases = sum(pattern.case_count for pattern in patterns)
        st.info(f"這 {total_cases} 筆是透明的 fictional case aggregates，不是真實使用者或客戶資料。")
    else:
        problem = st.text_area(
            "描述遇到的問題",
            placeholder="例如：同一個 port 上這台可以，但是另一台 BMC 連不上",
            max_chars=1000,
        )
        st.info("自由文字會由本機關鍵字規則分類，不會傳送到外部 API。")

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
                uses_synthetic_history=entry_mode == "常見問題",
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
