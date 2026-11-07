"""Supervisor tools for delegating tasks to specialist sub-agents or escalating."""
from typing import Any

from langchain_core.tools import tool

from src.tools.agent_tools import escalate_to_human


@tool
def ask_knowledge_agent(question: str) -> str:
    """Delega ao Knowledge Agent uma pergunta autocontida sobre produtos Getnet ou informação pública em tempo real."""
    return ""


@tool
def ask_support_agent(request: str) -> str:
    """Delega ao Customer Support Agent um pedido autocontido sobre a conta do próprio lojista."""
    return ""


SUPERVISOR_TOOLS: list[Any] = [ask_knowledge_agent, ask_support_agent, escalate_to_human]
SUPERVISOR_TOOLS_BY_NAME: dict[str, Any] = {t.name: t for t in SUPERVISOR_TOOLS}
