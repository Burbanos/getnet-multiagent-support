"""Customer Support Agent resolving operational inquiries using custom tools."""
import json
import logging
from src.core.state import AgentState, AgentRole
from src.tools.balance_tools import (
    get_settlement_and_sales_status,
    get_declined_transaction_details,
)
from src.tools.terminal_tools import diagnose_terminal_connectivity
from src.core.llm import get_llm

logger = logging.getLogger("multiagent.support")


class CustomerSupportAgent:
    """Support agent executing account queries and hardware diagnostics."""

    def __init__(self):
        self.llm = get_llm()

    async def execute(self, state: AgentState) -> AgentState:
        message = state.message.lower()
        user_id = state.user_id
        intent = state.intent or (state.route.intent if state.route else "")

        if intent == "diagnose_decline" or any(w in message for w in [
            "recusa", "recusada", "decline", "51", "negada", "rejeitada", "não passou", "nao passou",
            "transação recusada", "transacao recusada", "não autorizada", "nao autorizada", "saldo insuficiente",
            "código de recusa", "codigo de recusa", "erro de transação", "erro de transacao"
        ]):
            tool_name = "get_declined_transaction_details"
            result = get_declined_transaction_details(user_id=user_id)
        elif intent == "check_settlement" or any(w in message for w in [
            "ontem", "yesterday", "deposit", "depósito", "deposito", "depositado", "saldo", "quando cai", "quanto tenho"
        ]):
            tool_name = "get_settlement_and_sales_status"
            result = get_settlement_and_sales_status(user_id=user_id)
        elif intent == "troubleshoot_terminal" or any(w in message for w in [
            "não conecta", "nao conecta", "não está conectando", "sem conexão", "sem conexao", "sem sinal", "chip",
            "offline", "erro de internet", "falha de internet", "problema de conexão", "problema de conexao"
        ]):
            tool_name = "diagnose_terminal_connectivity"
            result = diagnose_terminal_connectivity(user_id=user_id)
        else:
            tool_name = "diagnose_terminal_connectivity"
            result = diagnose_terminal_connectivity(user_id=user_id)

        state.tools_used.append(tool_name)
        state.tool_results.append(result)

        system_prompt = (
            "Você é o Agente de Suporte ao Cliente da Getnet. "
            "Você tem acesso aos dados operacionais do lojista (vendas, máquinas de cartão e transações). "
            "Seja atencioso, empático, claro e forneça orientações práticas e imediatas para solucionar a questão."
        )

        user_prompt = (
            f"ID do Lojista: {user_id}\n"
            f"Mensagem do Lojista: {state.message}\n\n"
            f"Dados operacionais consultados via ferramenta ({tool_name}):\n"
            f"{json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
            "Elabore uma resposta amigável, clara e bem estruturada, informando os valores e passos práticos ao lojista:"
        )

        response_text = await self.llm.generate_text(user_prompt, system_prompt=system_prompt)
        state.agent_response = response_text
        state.final_agent = AgentRole.CUSTOMER_SUPPORT
        return state
