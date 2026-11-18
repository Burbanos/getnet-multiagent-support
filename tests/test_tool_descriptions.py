"""Offline tests for Phase 12E tool description boundaries."""
from src.tools.agent_tools import diagnose_declined_transaction, diagnose_terminal
from src.tools.supervisor_tools import SUPERVISOR_TOOLS


def _supervisor_descriptions() -> dict[str, str]:
    return {tool.name: tool.description for tool in SUPERVISOR_TOOLS}


def test_ask_knowledge_agent_description_covers_terminal_functions() -> None:
    desc = _supervisor_descriptions()["ask_knowledge_agent"]
    assert "inclusive como usar, ativar ou encontrar uma função da maquininha" in desc
    assert "catálogo de códigos de recusa de transação" in desc


def test_ask_support_agent_description_bounds_terminal_diagnosis_and_screen_errors() -> None:
    desc = _supervisor_descriptions()["ask_support_agent"]
    assert "diagnóstico técnico da maquininha dele (conexão, sinal, Wi-Fi)" in desc
    assert desc.endswith(
        "Erro mostrado em tela de configuração, rede, atualização ou inicialização da maquininha não é código de recusa."
    )


def test_diagnose_declined_transaction_excludes_screen_errors_and_keeps_examples() -> None:
    exclusion = (
        "Não use para erros exibidos em telas de configuração, rede, atualização ou inicialização da maquininha:\n"
        "o catálogo cobre só códigos de recusa de transação de cartão."
    )
    assert exclusion in diagnose_declined_transaction.description
    assert "Código 05 não autorizada" in diagnose_declined_transaction.description
    assert "Não use para erros exibidos em telas de configuração" not in diagnose_terminal.description
