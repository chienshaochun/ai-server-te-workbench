"""Pure state transitions for guided troubleshooting sessions."""

from dataclasses import replace
from uuid import uuid4

from ai_server_te_workbench.conversation.models import (
    ConversationTurn,
    DiagnosticStep,
    SessionOutcome,
    TroubleshootingSession,
)
from ai_server_te_workbench.conversation.statistics import normalize_model_family
from ai_server_te_workbench.knowledge.generic_flows import START_STEPS, generic_flow_steps
from ai_server_te_workbench.knowledge.models import CaseOutcome, CaseRecord, SymptomCategory


class ConversationController:
    def __init__(self, steps: tuple[DiagnosticStep, ...] | None = None) -> None:
        steps = generic_flow_steps() if steps is None else steps
        if not isinstance(steps, tuple) or not steps:
            raise ValueError("steps must contain at least one DiagnosticStep")
        if not all(isinstance(step, DiagnosticStep) for step in steps):
            raise TypeError("steps must contain only DiagnosticStep values")
        if len({step.id for step in steps}) != len(steps):
            raise ValueError("step IDs must be unique")
        self._steps = {step.id: step for step in steps}
        self._validate_references()

    def start(
        self,
        server_model: str,
        raw_problem: str,
        symptom_category: SymptomCategory,
        match_confidence: float,
        *,
        uses_synthetic_history: bool = True,
    ) -> TroubleshootingSession:
        if not isinstance(symptom_category, SymptomCategory):
            raise TypeError("symptom_category must be a SymptomCategory")
        start_step = START_STEPS[symptom_category]
        if start_step not in self._steps:
            raise ValueError(f"missing start step {start_step}")
        return TroubleshootingSession(
            session_id=f"SESSION-{uuid4()}",
            server_model=server_model,
            raw_problem=raw_problem,
            symptom_category=symptom_category,
            match_confidence=match_confidence,
            current_step_id=start_step,
            transcript=(),
            outcome=SessionOutcome.ACTIVE,
            uses_synthetic_history=uses_synthetic_history,
        )

    def current_step(self, session: TroubleshootingSession) -> DiagnosticStep | None:
        self._require_session(session)
        if session.current_step_id is None:
            return None
        return self._steps[session.current_step_id]

    def answer(self, session: TroubleshootingSession, answer_id: str) -> TroubleshootingSession:
        self._require_session(session)
        if session.outcome is not SessionOutcome.ACTIVE:
            raise ValueError("terminal session cannot accept another answer")
        if not isinstance(answer_id, str):
            raise TypeError("answer_id must be text")
        step = self._steps[session.current_step_id]
        try:
            branch = next(branch for branch in step.branches if branch.answer_id == answer_id)
        except StopIteration as error:
            allowed = ", ".join(branch.answer_id for branch in step.branches)
            raise ValueError(f"answer_id must be one of: {allowed}") from error

        sequence = len(session.transcript) + 1
        turn = ConversationTurn(
            sequence=sequence,
            step_id=step.id,
            question_zh=step.question_zh,
            recommended_check_zh=step.recommended_check_zh,
            answer_id=branch.answer_id,
            answer_label_zh=branch.answer_label_zh,
            observation_zh=branch.observation_zh,
            evidence_id=f"E-{session.session_id}-Q{sequence}-{step.evidence_tag}",
            safety_note_zh=step.safety_note_zh,
        )
        category = branch.category_override or session.symptom_category
        if branch.next_step_id is not None:
            return replace(
                session,
                symptom_category=category,
                current_step_id=branch.next_step_id,
                transcript=(*session.transcript, turn),
            )
        return replace(
            session,
            symptom_category=category,
            current_step_id=None,
            transcript=(*session.transcript, turn),
            outcome=branch.outcome,
            resolution_id=branch.resolution_id,
        )

    def _validate_references(self) -> None:
        for step in self._steps.values():
            for branch in step.branches:
                if branch.next_step_id is not None and branch.next_step_id not in self._steps:
                    raise ValueError(
                        f"step {step.id} references missing step {branch.next_step_id}"
                    )

    def _require_session(self, session: object) -> None:
        if not isinstance(session, TroubleshootingSession):
            raise TypeError("session must be a TroubleshootingSession")
        if session.current_step_id is not None and session.current_step_id not in self._steps:
            raise ValueError("session references an unknown current step")


def case_record_from_session(
    session: TroubleshootingSession, *, synthetic: bool = False
) -> CaseRecord:
    if not isinstance(session, TroubleshootingSession):
        raise TypeError("session must be a TroubleshootingSession")
    if session.outcome is SessionOutcome.ACTIVE:
        raise ValueError("active session cannot become a case record")
    outcome = {
        SessionOutcome.RESOLVED: CaseOutcome.RESOLVED,
        SessionOutcome.UNRESOLVED: CaseOutcome.UNRESOLVED,
        SessionOutcome.ESCALATED: CaseOutcome.ESCALATED,
    }[session.outcome]
    return CaseRecord(
        model_family=normalize_model_family(session.server_model),
        symptom_category=session.symptom_category,
        resolution_id=session.resolution_id,
        outcome=outcome,
        synthetic=synthetic,
    )
