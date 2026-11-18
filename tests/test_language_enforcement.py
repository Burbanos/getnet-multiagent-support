"""Offline tests for language detection, preserved tokens, and LanguageRewriter enforcement (Phase 13B)."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agents.language import detect_reply_language, preserved_tokens
from src.core.graph import ANSWER_CHECK_FALLBACK, OrchestrationGraph
from src.core.tickets_db import _get_message_text
from tests.fakes import ScriptedChatModel


def _plan_msg(lang: str = "en") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": lang,
                    "scope": "support",
                    "escalation_request": "none",
                    "steps": [{"goal": "Answer the merchant", "delegate": "support"}],
                },
                "id": "call_plan_lang",
            }
        ],
    )


class _RaisingModel(ScriptedChatModel):
    exc_factory: Any = Field(default=None)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        raise self.exc_factory()


def test_detect_reply_language_pt_en_short_and_url_stripping() -> None:
    assert (
        detect_reply_language(
            "O depósito das vendas de ontem cai na sua conta amanhã, conforme o extrato de liquidação."
        )
        == "pt"
    )
    assert (
        detect_reply_language(
            "Yesterday's sales will be deposited into your account tomorrow, according to the settlement statement."
        )
        == "en"
    )
    assert detect_reply_language("Ok!") == "undetermined"
    assert detect_reply_language("GET-TKT-20261118-ABCDEF1234 https://site.getnet.com.br/very/long/path/here") == "undetermined"


def test_preserved_tokens_extracts_urls_tickets_and_multidigit_numbers() -> None:
    text = (
        "O valor líquido foi R$ 1.234,56 em 19/11/2026, chamado GET-TKT-20261118-ABCDEF1234, "
        "detalhes em https://site.getnet.com.br/crediario/. Erro 5."
    )
    toks = preserved_tokens(text)
    assert {
        "1.234,56",
        "19",
        "11",
        "2026",
        "GET-TKT-20261118-ABCDEF1234",
        "https://site.getnet.com.br/crediario/",
    } <= toks
    assert "5" not in toks


def test_language_check_accepts_valid_rewrite_preserving_tokens() -> None:
    pt_draft = (
        "O valor líquido das vendas de ontem foi R$ 1.234,56 com depósito em 19/11/2026 "
        "conforme o extrato da conta cadastrada."
    )
    en_rewritten = (
        "Yesterday's net sales amount was R$ 1.234,56 with deposit on 19/11/2026 "
        "according to your registered account statement."
    )
    rw_msg = AIMessage(content=en_rewritten)
    rw_msg.usage_metadata = {"input_tokens": 30, "output_tokens": 25, "total_tokens": 55}
    rw = ScriptedChatModel(responses=[rw_msg])

    orch = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=pt_draft)]),
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=rw,
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id="s-lang-ok", message="How much did I sell yesterday?")

    assert st.agent_response == en_rewritten
    assert st.language == {"status": "rewritten", "target": "en", "detected": "pt"}
    assert (st.tokens_by_agent or {}).get("LanguageRewriter") == {
        "input_tokens": 30,
        "output_tokens": 25,
        "total_tokens": 55,
    }
    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-lang-ok"}})
    stored = [_get_message_text(m) for m in (snap.values or {}).get("messages") or []]
    assert en_rewritten in stored
    assert pt_draft not in stored


def test_language_check_rejects_rewrite_missing_url_amount_or_ticket() -> None:
    pt_draft = (
        "Seu chamado GET-TKT-20261118-ABC1234567 sobre R$ 1.234,56 foi atualizado, "
        "confira em https://site.getnet.com.br/pix/ antes de continuar."
    )
    for bad_en in (
        "Your ticket GET-TKT-20261118-ABC1234567 about R$ 1.234,56 was updated, check our portal before continuing.",
        "Your ticket GET-TKT-20261118-ABC1234567 about R$ 1.234 was updated, check https://site.getnet.com.br/pix/.",
        "Your ticket about R$ 1.234,56 was updated, check https://site.getnet.com.br/pix/ for full details.",
    ):
        sup = ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "escalate_to_human", "args": {"reason": "r", "priority": "standard"}, "id": "t1"}
                    ],
                ),
                AIMessage(content=pt_draft),
            ]
        )
        # Note: ticket created in turn? Inject evidence via tool output instead of escalate_to_human?
        # Even simpler: check answer_check with ask_knowledge_agent mocked result, or test without unverified URL/ticket:
        del sup

    # Using values/numbers & URL returned in a KnowledgeAgent ToolMessage so answer_check passes:
    pt_with_url = (
        "O valor líquido foi R$ 1.234,56 e detalhes do produto podem ser consultados em "
        "https://site.getnet.com.br/pix/."
    )
    sup_bad_amount = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "pix"}, "id": "k1"}]),
            AIMessage(content="O Pix custa R$ 1.234,56 em https://site.getnet.com.br/pix/."),
            AIMessage(content=pt_with_url),
        ]
    )
    rw_missing_num = ScriptedChatModel(
        responses=[AIMessage(content="The net amount was updated and details can be found at https://site.getnet.com.br/pix/.")]
    )
    st1 = OrchestrationGraph(
        chat_model=sup_bad_amount,
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=rw_missing_num,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-rej-num", message="How much is Pix?")
    assert st1.agent_response == pt_with_url
    assert st1.language == {"status": "rewrite_rejected", "target": "en", "detected": "pt"}

    sup_bad_url = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "pix"}, "id": "k2"}]),
            AIMessage(content="O Pix custa R$ 1.234,56 em https://site.getnet.com.br/pix/."),
            AIMessage(content=pt_with_url),
        ]
    )
    rw_missing_url = ScriptedChatModel(
        responses=[AIMessage(content="The net amount was R$ 1.234,56 and details can be checked on our official website.")]
    )
    st2 = OrchestrationGraph(
        chat_model=sup_bad_url,
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=rw_missing_url,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-rej-url", message="How much is Pix?")
    assert st2.agent_response == pt_with_url
    assert st2.language == {"status": "rewrite_rejected", "target": "en", "detected": "pt"}


def test_language_check_rejects_rewrite_dropping_ticket_id() -> None:
    ticket_pt = (
        "Seu chamado GET-TKT-20261118-AABBCCDDEE foi registrado para a equipe humana sobre a venda de R$ 1.234,56."
    )
    sup = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "escalate_to_human", "args": {"reason": "pedido", "priority": "standard"}, "id": "e1"}],
            ),
            AIMessage(content=ticket_pt),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "TurnPlan",
                        "args": {
                            "reply_language": "en",
                            "scope": "support",
                            "escalation_request": "asked_for_human",
                            "steps": [{"goal": "Open ticket", "delegate": "none"}],
                        },
                        "id": "p1",
                    }
                ],
            )
        ]
    )
    # Create an answer referencing the real generated ticket_id by checking answer_check? Wait: ticket_id is random,
    # so we put GET-TKT in a knowledge answer or test language_check direct node preservation!
    del sup, planner
    # Even better: test with ToolMessage returning a GET-TKT id so answer_check accepts it cleanly:
    pt_tkt = "O protocolo de atendimento é GET-TKT-20261118-AABBCCDDEE e a resposta seguirá nesta conversa."
    sup2 = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "ticket"}, "id": "k3"}]),
            AIMessage(content="Protocolo GET-TKT-20261118-AABBCCDDEE."),
            AIMessage(content=pt_tkt),
        ]
    )
    rw_lost_tkt = ScriptedChatModel(
        responses=[AIMessage(content="The support request protocol was registered and the reply will follow in this chat.")]
    )
    st = OrchestrationGraph(
        chat_model=sup2,
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=rw_lost_tkt,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-rej-tkt", message="Where is my ticket?")
    assert st.agent_response == pt_tkt
    assert st.language == {"status": "rewrite_rejected", "target": "en", "detected": "pt"}


def test_language_check_rejects_rewrite_in_wrong_language() -> None:
    pt_draft = "O depósito das vendas de ontem será feito amanhã na sua conta bancária cadastrada."
    still_pt = "O depósito das vendas realizadas ontem cairá amanhã diretamente na conta cadastrada."
    st = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=pt_draft)]),
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=ScriptedChatModel(responses=[AIMessage(content=still_pt)]),
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-rej-lang", message="When will I get paid?")
    assert st.agent_response == pt_draft
    assert st.language == {"status": "rewrite_rejected", "target": "en", "detected": "pt"}


def test_language_check_without_plan_infers_target_from_merchant_message() -> None:
    pt_draft = "O depósito das vendas de ontem será creditado amanhã na sua conta cadastrada."
    en_fixed = "Yesterday's sales deposit will be credited tomorrow to your registered account."
    rw = ScriptedChatModel(responses=[AIMessage(content=en_fixed)])
    st = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=pt_draft)]),
        rewrite_model=rw,
        checkpointer=MemorySaver(),
    ).run_sync(
        user_id="cliente1988",
        session_id="s-noplan-lang",
        message="When will yesterday's sales be deposited into my bank account?",
    )
    assert st.agent_response == en_fixed
    assert st.language == {"status": "rewritten", "target": "en", "detected": "pt"}


def test_fixed_answer_check_fallback_is_not_rewritten_and_error_fails_open() -> None:
    # 1. answer_check fallback (invented URL) must be skipped by language_check
    bad_url_draft = "Veja o detalhe completo no site https://invented.example.com/pix agora mesmo."
    rw_unused = ScriptedChatModel(responses=[])
    st_fb = OrchestrationGraph(
        chat_model=ScriptedChatModel(
            responses=[AIMessage(content=bad_url_draft), AIMessage(content="https://still-bad.example.com")]
        ),
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=rw_unused,
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-fb-skip", message="Where is Pix info?")
    assert st_fb.agent_response == ANSWER_CHECK_FALLBACK
    assert (st_fb.language or {}).get("status") == "skipped"
    assert rw_unused.received == []

    # 2. Rewrite provider error fails open keeping original text
    pt_draft = "O depósito das vendas de ontem cairá amanhã na sua conta bancária cadastrada."
    st_err = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content=pt_draft)]),
        planner_model=ScriptedChatModel(responses=[_plan_msg("en")]),
        rewrite_model=_RaisingModel(exc_factory=lambda: RuntimeError("rewrite failed")),
        checkpointer=MemorySaver(),
    ).run_sync(user_id="cliente1988", session_id="s-rw-err", message="When will I be paid?")
    assert st_err.agent_response == pt_draft
    assert st_err.language == {"status": "error", "target": "en", "detected": "pt"}
