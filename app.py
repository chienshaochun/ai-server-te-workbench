"""Streamlit entry point for the guided AI-server TE troubleshooting demo."""

import streamlit as st

from ai_server_te_workbench.conversation import (
    ConversationController,
    SessionOutcome,
    case_record_from_session,
    normalize_model_family,
)
from ai_server_te_workbench.knowledge import SymptomCategory, synthetic_case_history
from ai_server_te_workbench.knowledge import synthetic_case_patterns
from ai_server_te_workbench.llm import (
    DEFAULT_MODEL,
    AssistantExchange,
    HybridTriageService,
    LLMServiceError,
    OpenAIAdvisor,
)
from ai_server_te_workbench.reporting import (
    GuidedReportDocument,
    render_guided_html,
    render_guided_markdown,
)


st.set_page_config(page_title="AI Server TE Troubleshooting", page_icon="🛠️", layout="wide")

controller = ConversationController()
MAX_LLM_CALLS_PER_SESSION = 5


def optional_secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except FileNotFoundError:
        return None
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


api_key = optional_secret("OPENAI_API_KEY")
openai_model = optional_secret("OPENAI_MODEL") or DEFAULT_MODEL
advisor = OpenAIAdvisor(api_key, model=openai_model) if api_key else None
triage_service = HybridTriageService(advisor)

if "case_history" not in st.session_state:
    st.session_state.case_history = list(synthetic_case_history())
if "troubleshooting_session" not in st.session_state:
    st.session_state.troubleshooting_session = None
if "recorded_session_ids" not in st.session_state:
    st.session_state.recorded_session_ids = set()
if "triage_advice" not in st.session_state:
    st.session_state.triage_advice = None
if "assistant_exchanges" not in st.session_state:
    st.session_state.assistant_exchanges = []
if "llm_call_count" not in st.session_state:
    st.session_state.llm_call_count = 0
if "llm_session_enabled" not in st.session_state:
    st.session_state.llm_session_enabled = False

st.title("AI Server TE Guided Troubleshooting")
st.caption("一次完成一個可驗證步驟，保留 evidence，最後產生交接報告。")
st.warning(
    "這是 generic AI server 模擬器：不連接、不控制也不修復真實硬體；"
    "建議涉及拆機時必須安全斷電並由合格人員執行。"
)


def reset_session() -> None:
    st.session_state.troubleshooting_session = None
    st.session_state.triage_advice = None
    st.session_state.assistant_exchanges = []
    st.session_state.llm_session_enabled = False


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
    use_llm = False

    if entry_mode == "常見問題":
        pattern_by_label = {
            f"{pattern.title_zh}｜{pattern.case_count} synthetic cases｜"
            f"resolved {pattern.resolution_rate:.0%}": pattern
            for pattern in synthetic_case_patterns()
        }
        selected_label = st.selectbox(
            "常見問題（synthetic demo history）", tuple(pattern_by_label)
        )
        selected = pattern_by_label[selected_label]
        category = selected.symptom_category
        confidence = 1.0
        problem = selected.example_problem_zh
        st.markdown(f"**模擬現象：** {selected.example_problem_zh}")
        st.markdown(f"**建議先檢查：** {selected.recommended_first_check_zh}")
        st.info("這 72 筆是透明的 fictional case aggregates，不是真實使用者或客戶資料。")
    else:
        problem = st.text_area(
            "描述遇到的問題",
            placeholder="例如：同一個 port 上這台可以，但是另一台 BMC 連不上",
            max_chars=1000,
        )
        remaining_calls = MAX_LLM_CALLS_PER_SESSION - st.session_state.llm_call_count
        if advisor is None:
            st.info("目前使用 deterministic 模式；設定 OPENAI_API_KEY 後可選擇 AI 輔助理解。")
        elif remaining_calls <= 0:
            st.warning("此瀏覽器 session 的 AI 呼叫額度已用完，將使用 deterministic 模式。")
        else:
            use_llm = st.checkbox(
                "啟用 AI 輔助理解（會使用 OpenAI API 額度）",
                value=False,
            )
            st.caption(
                f"本 session 尚可呼叫 {remaining_calls} 次；AI 只選擇核准入口，不會直接診斷硬體。"
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
                if use_llm:
                    st.session_state.llm_call_count += 1
                with st.spinner("正在整理症狀與核准的排查入口…"):
                    advice = triage_service.analyze(
                        server_model,
                        problem,
                        use_llm=use_llm,
                    )
                st.session_state.triage_advice = advice
                st.session_state.llm_session_enabled = advice.used_llm
                category = advice.category
                confidence = advice.confidence
            st.session_state.troubleshooting_session = controller.start(
                server_model,
                problem,
                category,
                confidence,
                uses_synthetic_history=(
                    entry_mode == "常見問題"
                    or (
                        st.session_state.triage_advice is not None
                        and st.session_state.triage_advice.used_llm
                    )
                ),
            )
            st.rerun()
else:
    st.subheader("2. 逐步排查")
    col1, col2, col3 = st.columns(3)
    col1.metric("Server", session.server_model)
    col2.metric("Category", session.symptom_category.value)
    col3.metric("Outcome", session.outcome.value)

    triage_advice = st.session_state.triage_advice
    if triage_advice is not None:
        source_label = "OpenAI 輔助" if triage_advice.used_llm else "Deterministic fallback"
        with st.expander(f"問題理解｜{source_label}", expanded=True):
            st.write(triage_advice.summary_zh)
            st.caption(
                f"信心 {triage_advice.confidence:.0%}｜"
                f"核准入口 {triage_advice.recommended_step_id}｜"
                f"模型 {triage_advice.model or '未使用'}"
            )
            if triage_advice.observations:
                st.markdown(
                    "**辨識到的線索：** " + "、".join(triage_advice.observations)
                )
            if triage_advice.missing_information:
                st.markdown(
                    "**仍缺少的資訊：** "
                    + "、".join(triage_advice.missing_information)
                )
            st.markdown(f"**選擇理由：** {triage_advice.reason_zh}")
            if triage_advice.safety_warning_zh:
                st.warning(triage_advice.safety_warning_zh)
            if triage_advice.fallback_reason:
                st.warning(triage_advice.fallback_reason)

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
        if st.session_state.llm_session_enabled and advisor is not None:
            with st.expander("AI 輔助問答（只解釋目前步驟）", expanded=False):
                st.caption(
                    "AI 回答是 advisory，不會替你提交測試結果，也不能跳過核准流程。"
                )
                for exchange in st.session_state.assistant_exchanges:
                    st.markdown(f"**你：** {exchange.question_zh}")
                    st.markdown(f"**AI：** {exchange.answer.answer_zh}")
                    st.markdown(
                        f"**核准的下一動作：** "
                        f"{exchange.answer.recommended_next_action_zh}"
                    )
                    if exchange.answer.safety_warning_zh:
                        st.warning(exchange.answer.safety_warning_zh)
                    st.divider()
                remaining_calls = (
                    MAX_LLM_CALLS_PER_SESSION - st.session_state.llm_call_count
                )
                question = st.text_input(
                    "針對目前步驟提問",
                    placeholder="例如：為什麼要先用 Golden Sample？",
                    max_chars=500,
                    key=f"assistant_question_{step.id}",
                )
                if remaining_calls <= 0:
                    st.warning("此瀏覽器 session 的 AI 呼叫額度已用完。")
                elif st.button("詢問 AI", key=f"ask_ai_{step.id}"):
                    if not question.strip():
                        st.error("請先輸入問題。")
                    else:
                        st.session_state.llm_call_count += 1
                        try:
                            with st.spinner("AI 正在依目前 evidence 解釋…"):
                                answer = advisor.answer_question(session, step, question)
                        except LLMServiceError as error:
                            st.error(str(error))
                        else:
                            st.session_state.assistant_exchanges.append(
                                AssistantExchange(question, answer)
                            )
                            st.rerun()
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
        report = GuidedReportDocument(
            session,
            triage_advice=st.session_state.triage_advice,
            assistant_exchanges=tuple(st.session_state.assistant_exchanges),
        )
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
