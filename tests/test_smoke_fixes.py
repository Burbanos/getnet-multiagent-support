"""Offline tests for Phase 13C smoke-test fixes (goal-only plan, out_of_scope cost, terminal serial)."""
from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.core.graph import OUT_OF_SCOPE_MESSAGE, OrchestrationGraph
from src.core.tickets_db import _get_message_text
from src.tools.terminal_tools import diagnose_terminal_connectivity
from tests.fakes import ScriptedChatModel


def test_supervisor_plan_prompt_omits_delegate() -> None:
    sup = ScriptedChatModel(responses=[AIMessage(content="O código 05 indica contato com o emissor.")])
    planner = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "TurnPlan",
                        "args": {
                            "reply_language": "pt",
                            "scope": "support",
                            "escalation_request": "none",
                            "action_confirmation": "none",
                            "steps": [{"goal": "Explain decline code 05", "delegate": "knowledge"}],
                        },
                        "id": "p1",
                    }
                ],
            )
        ]
    )
    orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())
    st = orch.run_sync("cliente1988", "O que significa código 05 em venda recusada?", session_id="s-goal-only")

    sys_prompt = _get_message_text(sup.received[0][0])
    plan_section = sys_prompt.split("[Plan for this turn]")[-1]
    assert "Explain decline code 05" in plan_section
    assert "knowledge:" not in plan_section
    assert "delegate" not in plan_section
    # Delegate still preserved in metadata plan record
    assert (st.plan or {}).get("steps") == [{"goal": "Explain decline code 05", "delegate": "knowledge"}]


def test_out_of_scope_records_model_and_computes_non_null_cost() -> None:
    plan_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": "en",
                    "scope": "out_of_scope",
                    "escalation_request": "none",
                    "action_confirmation": "none",
                    "steps": [],
                },
                "id": "p_oos",
            }
        ],
    )
    plan_call.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}

    class FakeGeminiPlanner(ScriptedChatModel):
        model_name: str = "gemini-3.5-flash-lite"

    orch = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[]),
        planner_model=FakeGeminiPlanner(responses=[plan_call]),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync("cliente1988", "Write a short poem.", session_id="s-oos-cost")

    assert st.agent_response == OUT_OF_SCOPE_MESSAGE["en"]
    assert st.llm_model == "gemini-3.5-flash-lite"
    assert st.tokens == {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    assert st.estimated_cost_usd is not None and st.estimated_cost_usd > 0


def test_diagnose_terminal_returns_not_found_for_other_serial() -> None:
    res_bad = diagnose_terminal_connectivity("cliente1988", terminal_serial="GET-000000")
    assert res_bad == {"status": "not_found", "error": "terminal_not_found"}

    res_ok = diagnose_terminal_connectivity("cliente1988", terminal_serial="GET-883921")
    assert res_ok["status"] == "success"
    assert res_ok["serial_number"] == "GET-883921"
