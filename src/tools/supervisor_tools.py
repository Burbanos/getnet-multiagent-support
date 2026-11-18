"""Supervisor tools for delegating tasks to specialist sub-agents or escalating."""
from typing import Any

from langchain_core.tools import tool

from src.tools.agent_tools import escalate_to_human


@tool
def ask_knowledge_agent(question: str) -> str:
    """Delega ao Knowledge Agent uma pergunta autocontida sobre produtos, taxas, prazos, regras e procedimentos da Getnet (páginas oficiais), inclusive como usar, ativar ou encontrar uma função da maquininha, clima, câmbio (PTAX) ou notícias. Não tem dados da conta do lojista nem o catálogo de códigos de recusa de transação."""
    return ""


@tool
def ask_support_agent(request: str) -> str:
    """Delega ao Customer Support Agent um pedido autocontido que só as ferramentas de conta respondem: vendas e depósitos do próprio lojista, diagnóstico técnico da maquininha dele (conexão, sinal, Wi-Fi) e transações de cartão recusadas, incluindo o significado de um código de recusa de transação (o catálogo de códigos fica nessa ferramenta, mesmo sem uma transação específica). Erro mostrado em tela de configuração, rede, atualização ou inicialização da maquininha não é código de recusa."""
    return ""


SUPERVISOR_TOOLS: list[Any] = [ask_knowledge_agent, ask_support_agent, escalate_to_human]
SUPERVISOR_TOOLS_BY_NAME: dict[str, Any] = {t.name: t for t in SUPERVISOR_TOOLS}
