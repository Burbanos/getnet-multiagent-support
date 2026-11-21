"""Offline tests for the pre-send Verifier agent and graph replan loop (Phase 13B)."""
from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agents.verifier import Verifier
from src.config import settings
from src.core.graph import VERIFIER_ABSTENTION_MESSAGE, OrchestrationGraph
from src.core.tickets_db import _get_message_text
from tests.fakes import ScriptedChatModel


def _plan_msg(
    lang: str = "pt",
    esc: str = "none",
    steps: list[dict[str, str]] | None = None,
) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": lang,
                    "scope": "support",
                    "escalation_request": esc,
                    "steps": [{"goal": "Check settings screen error 05", "delegate": "support"}]
                    if steps is None
                    else steps,
                },
                "id": "call_plan",
            }
        ],
    )


def _verdict_msg(verdicts: list[dict[str, Any]], usage: dict[str, int] | None = None) -> AIMessage:
    msg = AIMessage(
        content="",
        tool_calls=[{"name": "Verification", "args": {"verdicts": verdicts}, "id": "call_ver"}],
    )
    if usage is not None:
        msg.usage_metadata = usage
    return msg


class _RaisingModel(ScriptedChatModel):
    exc_factory: Any = Field(default=None)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        raise self.exc_factory()


def test_verifier_passes_on_first_round() -> None:
    sup = ScriptedChatModel(responses=[AIMessage(content="Não encontrei detalhes desse erro na tela de rede.")])
    planner = ScriptedChatModel(responses=[_plan_msg()])
    ver = ScriptedChatModel(
        responses=[
            _verdict_msg(
                [{"step": 1, "verdict": "answered", "note": ""}],
                usage={"input_tokens": 18, "output_tokens": 6, "total_tokens": 24},
            )
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id="s-ver-pass", message="Erro 05 na tela de rede.")
    assert st.agent_response == "Não encontrei detalhes desse erro na tela de rede."
    assert st.verification is not None
    assert st.verification["status"] == "passed"
    assert st.verification["replans"] == 0
    assert len(st.verification["rounds"]) == 1
    assert (st.tokens_by_agent or {}).get("Verifier") == {"input_tokens": 18, "output_tokens": 6, "total_tokens": 24}


def test_verifier_unit_rejects_mismatched_count_or_numbering() -> None:
    steps = [{"goal": "g1", "delegate": "knowledge"}, {"goal": "g2", "delegate": "support"}]
    r_count = Verifier(ScriptedChatModel(responses=[_verdict_msg([{"step": 1, "verdict": "answered", "note": ""}])])).verify(
        "q", steps, "e", "d"
    )
    assert r_count.status == "invalid"
    assert r_count.error_type == "step_mismatch"

    r_num = Verifier(
        ScriptedChatModel(
            responses=[
                _verdict_msg(
                    [
                        {"step": 1, "verdict": "answered", "note": ""},
                        {"step": 3, "verdict": "answered", "note": ""},
                    ]
                )
            ]
        )
    ).verify("q", steps, "e", "d")
    assert r_num.status == "invalid"
    assert r_num.error_type == "step_mismatch"


def test_verifier_replans_once_and_removes_first_draft_from_history() -> None:
    bad_draft = "O código 05 significa recusa do emissor."
    good_draft = "Não tenho informações sobre o erro 05 exibido na tela de rede."
    sup = ScriptedChatModel(responses=[AIMessage(content=bad_draft), AIMessage(content=good_draft)])
    ver = ScriptedChatModel(
        responses=[
            _verdict_msg(
                [{"step": 1, "verdict": "evidence_does_not_apply", "note": "screen error not declined sale"}],
                usage={"input_tokens": 20, "output_tokens": 5, "total_tokens": 25},
            ),
            _verdict_msg(
                [{"step": 1, "verdict": "answered", "note": ""}],
                usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            ),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=ScriptedChatModel(responses=[_plan_msg()]),
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id="s-ver-replan", message="Erro 05 na tela de rede.")

    assert st.agent_response == good_draft
    assert st.verification is not None
    assert st.verification["status"] == "passed_after_replan"
    assert st.verification["replans"] == 1
    assert len(st.verification["rounds"]) == 2
    assert (st.tokens_by_agent or {}).get("Verifier") == {"input_tokens": 30, "output_tokens": 10, "total_tokens": 40}

    assert len(sup.received) == 2
    second_sys = _get_message_text(sup.received[1][0])
    assert "[Verification before sending]" in second_sys
    assert "evidence_does_not_apply" in second_sys
    assert "screen error not declined sale" in second_sys

    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-ver-replan"}})
    stored = [_get_message_text(m) for m in (snap.values or {}).get("messages") or []]
    assert bad_draft not in stored
    assert good_draft in stored
    assert not any("[Verification before sending]" in txt for txt in stored)


def test_verifier_abstains_after_two_failures_in_plan_language() -> None:
    sup_pt = ScriptedChatModel(responses=[AIMessage(content="Rascunho 1"), AIMessage(content="Rascunho 2")])
    ver_pt = ScriptedChatModel(
        responses=[
            _verdict_msg([{"step": 1, "verdict": "unsupported_claim", "note": "no source"}]),
            _verdict_msg([{"step": 1, "verdict": "not_answered", "note": "still wrong"}]),
        ]
    )
    st_pt = OrchestrationGraph(
        chat_model=sup_pt,
        planner_model=ScriptedChatModel(responses=[_plan_msg(lang="pt")]),
        verifier_model=ver_pt,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-abs-pt", message="Erro 05")
    assert st_pt.agent_response == VERIFIER_ABSTENTION_MESSAGE["pt"]
    assert (st_pt.verification or {}).get("status") == "abstained"

    sup_en = ScriptedChatModel(responses=[AIMessage(content="Draft 1"), AIMessage(content="Draft 2")])
    ver_en = ScriptedChatModel(
        responses=[
            _verdict_msg([{"step": 1, "verdict": "unsupported_claim", "note": "no source"}]),
            _verdict_msg([{"step": 1, "verdict": "unsupported_claim", "note": "still no source"}]),
        ]
    )
    st_en = OrchestrationGraph(
        chat_model=sup_en,
        planner_model=ScriptedChatModel(responses=[_plan_msg(lang="en")]),
        verifier_model=ver_en,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-abs-en", message="Error 05?")
    assert st_en.agent_response == VERIFIER_ABSTENTION_MESSAGE["en"]
    assert (st_en.verification or {}).get("status") == "abstained"


def test_verifier_invalid_or_error_fails_open_keeping_draft() -> None:
    draft = "Rascunho mantido quando o verificador falha."
    st_invalid = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=draft)]),
        planner_model=ScriptedChatModel(responses=[_plan_msg()]),
        verifier_model=ScriptedChatModel(responses=[AIMessage(content="not a tool call")]),
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-inv", message="Erro 05")
    assert st_invalid.agent_response == draft
    assert (st_invalid.verification or {}).get("status") == "invalid"

    st_err = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=draft)]),
        planner_model=ScriptedChatModel(responses=[_plan_msg()]),
        verifier_model=_RaisingModel(exc_factory=lambda: RuntimeError("verifier down")),
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-err", message="Erro 05")
    assert st_err.agent_response == draft
    assert (st_err.verification or {}).get("status") == "error"
    assert (st_err.verification or {}).get("error_type") == "RuntimeError"


def test_verifier_skipped_when_no_plan_no_steps_or_ticket_created() -> None:
    ver_unused = ScriptedChatModel(responses=[])
    st_no_steps = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Olá!")]),
        planner_model=ScriptedChatModel(responses=[_plan_msg(steps=[])]),
        verifier_model=ver_unused,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-nosteps", message="Oi")
    assert (st_no_steps.verification or {}).get("status") == "skipped"
    assert ver_unused.received == []

    st_ticket = OrchestrationGraph(
        chat_model=ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "escalate_to_human", "args": {"reason": "pedido", "priority": "standard"}, "id": "e1"}
                    ],
                ),
                AIMessage(content="Chamado registrado para a equipe humana."),
            ]
        ),
        planner_model=ScriptedChatModel(responses=[_plan_msg(esc="asked_for_human")]),
        verifier_model=ver_unused,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-tkt", message="Quero falar com um atendente.")
    assert (st_ticket.verification or {}).get("status") == "skipped"
    assert ver_unused.received == []

    st_no_plan = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Sem plano.")]),
        planner_model=_RaisingModel(exc_factory=lambda: RuntimeError("planner down")),
        verifier_model=ver_unused,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-ver-noplan", message="Oi")
    assert (st_no_plan.verification or {}).get("status") == "skipped"
    assert ver_unused.received == []


def test_verifier_uses_only_current_turn_tool_evidence() -> None:
    sup = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "ask_support_agent", "args": {"request": "saldo"}, "id": "s1"}],
            ),
            AIMessage(content="SALDO_TURNO_1_EVIDENCIA_9911"),
            AIMessage(content="Saldo do turno 1 é R$ 3.367,20."),
            AIMessage(content="Resposta do turno 2 sem ferramentas."),
        ]
    )
    planner = ScriptedChatModel(responses=[_plan_msg(), _plan_msg()])
    ver = ScriptedChatModel(
        responses=[
            _verdict_msg([{"step": 1, "verdict": "answered", "note": ""}]),
            _verdict_msg([{"step": 1, "verdict": "answered", "note": ""}]),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    orch.run_sync(user_id="cliente1988", session_id="s-ver-turns", message="Quanto vendi ontem?")
    orch.run_sync(user_id="cliente1988", session_id="s-ver-turns", message="E o erro 05 na tela?")

    assert len(ver.received) == 2
    ev1 = _get_message_text(ver.received[0][-1])
    ev2 = _get_message_text(ver.received[1][-1])
    assert "SALDO_TURNO_1_EVIDENCIA_9911" in ev1
    assert "SALDO_TURNO_1_EVIDENCIA_9911" not in ev2


def test_verifier_disabled_via_setting_marks_disabled(monkeypatch: Any) -> None:
    from src.config import settings

    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)
    ver = ScriptedChatModel(responses=[])
    orch = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Ok.")]),
        planner_model=ScriptedChatModel(responses=[_plan_msg()]),
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id="s-ver-off", message="Oi")
    assert (st.verification or {}).get("status") == "disabled"
    assert ver.received == []


@pytest.fixture(autouse=True)
def _verifier_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests exercise the verifier, which is off by default since the Phase 15 ablation."""
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", True)
