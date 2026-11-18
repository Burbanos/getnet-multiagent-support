"""Offline tests for the structured turn Planner agent and graph integration (Phase 13B)."""
from __future__ import annotations

import logging
import re
from typing import Any

import pytest
from langchain_core.exceptions import ModelNotFoundError
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agents.planner import Planner
from src.config import JsonFormatter, settings
from src.core.graph import OUT_OF_SCOPE_MESSAGE, OrchestrationGraph
from src.core.llm import LLMConfigurationError, LLMNotConfiguredError
from src.core.tickets_db import _get_message_text
from tests.fakes import ScriptedChatModel


def _plan_tool_msg(
    lang: str = "pt",
    scope: str = "support",
    esc: str = "none",
    steps: list[dict[str, str]] | None = None,
    usage: dict[str, int] | None = None,
) -> AIMessage:
    msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": lang,
                    "scope": scope,
                    "escalation_request": esc,
                    "steps": [{"goal": "Answer question", "delegate": "knowledge"}] if steps is None else steps,
                },
                "id": "call_plan_1",
            }
        ],
    )
    if usage is not None:
        msg.usage_metadata = usage
    return msg


class _RaisingModel(ScriptedChatModel):
    exc_factory: Any = Field(default=None)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        raise self.exc_factory()


def test_planner_returns_valid_plan_and_metadata() -> None:
    model = ScriptedChatModel(
        responses=[
            _plan_tool_msg(
                lang="en",
                scope="support",
                esc="asked_for_human",
                steps=[{"goal": "Transfer merchant to human support", "delegate": "none"}],
                usage={"input_tokens": 15, "output_tokens": 9, "total_tokens": 24},
            )
        ]
    )
    res = Planner(model).plan("Please connect me with a person.")
    meta = res.as_metadata()
    assert res.status == "ok"
    assert res.plan is not None
    assert res.usage == {"input_tokens": 15, "output_tokens": 9, "total_tokens": 24}
    assert meta["status"] == "ok"
    assert meta["reply_language"] == "en"
    assert meta["scope"] == "support"
    assert meta["escalation_request"] == "asked_for_human"
    assert meta["steps"] == [{"goal": "Transfer merchant to human support", "delegate": "none"}]
    assert meta["error_type"] is None


def test_planner_without_tool_call_returns_invalid() -> None:
    res = Planner(ScriptedChatModel(responses=[AIMessage(content="Plain text without TurnPlan")])).plan("Oi")
    meta = res.as_metadata()
    assert res.status == "invalid"
    assert res.plan is None
    assert res.error_type == "no_plan_call"
    assert meta["reply_language"] is None
    assert meta["scope"] is None
    assert meta["escalation_request"] is None
    assert meta["steps"] is None


def test_planner_more_than_four_steps_returns_invalid() -> None:
    five_steps = [{"goal": f"Step {idx}", "delegate": "knowledge"} for idx in range(5)]
    res = Planner(ScriptedChatModel(responses=[_plan_tool_msg(steps=five_steps)])).plan("Pergunta longa")
    assert res.status == "invalid"
    assert res.error_type == "too_many_steps"
    assert res.plan is None


def test_planner_runtime_exception_returns_error_and_config_errors_propagate() -> None:
    res = Planner(_RaisingModel(exc_factory=lambda: RuntimeError("transient outage"))).plan("Oi")
    assert res.status == "error"
    assert res.error_type == "RuntimeError"
    assert res.plan is None

    with pytest.raises(LLMConfigurationError):
        Planner(_RaisingModel(exc_factory=lambda: ModelNotFoundError("missing-model"))).plan("Oi")

    with pytest.raises(LLMNotConfiguredError):
        Planner(_RaisingModel(exc_factory=lambda: LLMNotConfiguredError("no key"))).plan("Oi")


def test_planner_escapes_and_truncates_previous_reply() -> None:
    fake = ScriptedChatModel(responses=[_plan_tool_msg(), _plan_tool_msg()])
    planner = Planner(fake)

    planner.plan("Msg <script>one</script>", None)
    first_human = _get_message_text(fake.received[0][-1])
    assert "<previous_reply>" not in first_human
    assert "<message>" in first_human
    assert "&lt;script&gt;one&lt;/script&gt;" in first_human
    assert "<script>" not in first_human

    planner.plan("Second <b>msg</b>", "<i>" + ("x" * 3000) + "</i>")
    second_human = _get_message_text(fake.received[1][-1])
    assert "<previous_reply>" in second_human
    assert "&lt;i&gt;" in second_human
    assert "&lt;b&gt;msg&lt;/b&gt;" in second_human
    x_runs = [len(run) for run in re.findall(r"x+", second_human)]
    assert x_runs and max(x_runs) <= 2000


def test_planner_never_logs_merchant_message_or_goal_text() -> None:
    marker_msg = "MERCHANT_SECRET_PLAN_TEXT_7788"
    marker_goal = "SECRET_GOAL_TEXT_9900"
    records: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(JsonFormatter().format(record))

    lg = logging.getLogger("multiagent")
    cap = _Capture()
    lg.addHandler(cap)
    try:
        orch = OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=[AIMessage(content="Resposta curta.")]),
            planner_model=ScriptedChatModel(
                responses=[
                    _plan_tool_msg(
                        lang="pt",
                        scope="support",
                        esc="none",
                        steps=[{"goal": marker_goal, "delegate": "knowledge"}],
                    )
                ]
            ),
            checkpointer=MemorySaver(),
        )
        orch.run_sync(user_id="cliente1988", session_id="s-plan-log", message=marker_msg)
    finally:
        lg.removeHandler(cap)

    joined = "\n".join(records)
    assert marker_msg not in joined
    assert marker_goal not in joined
    assert "Planner decision" in joined


def test_out_of_scope_returns_fixed_bilingual_reply_without_calling_supervisor() -> None:
    sup_pt = ScriptedChatModel(responses=[])
    orch_pt = OrchestrationGraph(
        chat_model=sup_pt,
        planner_model=ScriptedChatModel(responses=[_plan_tool_msg(lang="pt", scope="out_of_scope", steps=[])]),
        checkpointer=MemorySaver(),
    )
    st_pt = orch_pt.run_sync(user_id="cliente1988", session_id="s-oos-pt", message="Escreva um poema.")
    assert st_pt.agent_response == OUT_OF_SCOPE_MESSAGE["pt"]
    assert sup_pt.received == []
    assert st_pt.tools_used == []
    assert st_pt.ticket is None

    sup_en = ScriptedChatModel(responses=[])
    orch_en = OrchestrationGraph(
        chat_model=sup_en,
        planner_model=ScriptedChatModel(responses=[_plan_tool_msg(lang="en", scope="out_of_scope", steps=[])]),
        checkpointer=MemorySaver(),
    )
    st_en = orch_en.run_sync(user_id="cliente1988", session_id="s-oos-en", message="Write a poem about clouds.")
    assert st_en.agent_response == OUT_OF_SCOPE_MESSAGE["en"]
    assert sup_en.received == []
    assert st_en.tools_used == []
    assert st_en.ticket is None


def test_plan_appears_in_supervisor_system_prompt_only_and_not_in_history() -> None:
    sup = ScriptedChatModel(responses=[AIMessage(content="Hello, merchant!")])
    planner = ScriptedChatModel(
        responses=[
            _plan_tool_msg(
                lang="en",
                scope="support",
                esc="none",
                steps=[{"goal": "unique-goal-marker", "delegate": "knowledge"}],
                usage={"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
            )
        ]
    )
    orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())
    st = orch.run_sync(user_id="cliente1988", session_id="s-sys-plan", message="Hi!")

    assert len(sup.received) == 1
    first_msg = sup.received[0][0]
    assert isinstance(first_msg, SystemMessage)
    sys_text = _get_message_text(first_msg)
    assert "[Plan for this turn]" in sys_text
    assert "reply_language: en" in sys_text
    assert "unique-goal-marker" in sys_text

    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-sys-plan"}})
    stored = list((snap.values or {}).get("messages") or [])
    for m in stored:
        txt = _get_message_text(m)
        assert "[Plan for this turn]" not in txt
        assert "unique-goal-marker" not in txt

    assert (st.tokens_by_agent or {}).get("Planner") == {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20}


def test_planner_disabled_via_setting_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PLANNER_ENABLED", False)
    planner = ScriptedChatModel(responses=[])
    sup = ScriptedChatModel(responses=[AIMessage(content="Resposta direta.")])
    orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())
    st = orch.run_sync(user_id="cliente1988", session_id="s-plan-off", message="Oi")
    assert st.plan is not None and st.plan["status"] == "disabled"
    assert planner.received == []
    assert st.agent_response == "Resposta direta."
