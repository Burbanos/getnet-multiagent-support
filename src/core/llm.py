"""Rules-based fallback engine supporting offline execution and tool calling."""
import json
import logging
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

logger = logging.getLogger("multiagent.llm")


class RulesFallbackEngine:
    """
    Rules-based fallback engine that performs Tool Calling and ReAct observation-synthesis.
    Provides a deterministic execution engine in offline / test environments.
    """

    def __init__(self):
        logger.info("Operating in rules fallback engine mode.")

    def decide_or_synthesize(
        self,
        messages: list[BaseMessage],
        user_id: str = "cliente1988"
    ) -> AIMessage:
        """
        Decision step:
        1. If last message is HumanMessage: decide whether to invoke a tool (emit AIMessage with tool_calls)
           or answer directly.
        2. If last message is ToolMessage: observe tool output and synthesize grounded final answer.
        """
        if not messages:
            return AIMessage(content="Olá! Como posso ajudar você com suas soluções Getnet hoje?")

        last_message = messages[-1]

        # Case 1: Observation step -> Last message was a tool result
        if isinstance(last_message, ToolMessage):
            return self._synthesize_from_tool_observation(messages, user_id)

        # Case 2: User input step -> Decide whether to call a tool or respond
        if isinstance(last_message, HumanMessage):
            user_text = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
            return self._decide_tool_call_or_reply(user_text, messages, user_id)

        # Fallback
        return AIMessage(content="Posso ajudar com dúvidas sobre máquinas Getnet, extrato de liquidação, Pix ou suporte técnico.")

    async def a_decide_or_synthesize(
        self,
        messages: list[BaseMessage],
        user_id: str = "cliente1988"
    ) -> AIMessage:
        return self.decide_or_synthesize(messages, user_id=user_id)

    def _decide_tool_call_or_reply(
        self,
        user_text: str,
        messages: list[BaseMessage],
        user_id: str
    ) -> AIMessage:
        """Analyze intent and emit structured tool_call or direct response."""
        lower_msg = user_text.lower()
        call_id = f"call_{uuid.uuid4().hex[:8]}"

        # 1. Human Escalation Intent
        escalation_patterns = [
            r"\b(falar\s+com\s+(um\s+)?atendente)\b",
            r"\b(atendente\s+humano)\b",
            r"\b(atendimento\s+humano)\b",
            r"\b(especialista\s+humano)\b",
            r"\b(operador\s+humano)\b",
            r"\b(falar\s+com\s+(um\s+)?humano)\b",
            r"\b(falar\s+com\s+uma\s+pessoa)\b",
            r"\b(human\s+operator)\b",
            r"\b(ouvidoria)\b",
            r"\b(procon)\b",
            r"\b(processo\s+judicial|abrir\s+processo|entrar\s+na\s+justi[cç]a)\b",
        ]
        if any(re.search(pat, lower_msg) for pat in escalation_patterns):
            logger.info("Rules engine decided tool_call: escalate_to_human")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "escalate_to_human",
                    "args": {"user_id": user_id, "reason": user_text},
                    "id": call_id
                }]
            )

        # 2. Declined Transaction Lookups (prioritized before hardware connectivity)
        decline_patterns = [
            r"\b(recusa|recusad[ao]s?|declined?)\b",
            r"\b(c[oó]digo\s+(de\s+)?recusa|c[oó]digo\s+51|erro\s+51)\b",
            r"\b(transa[cç][aã]o\s+(recusada|negada|n[aã]o\s+passou|n[aã]o\s+autorizada|com\s+erro|falhou))\b",
            r"\b(erro\s+de\s+transa[cç][aã]o)\b",
            r"\b(cart[aã]o\s+(recusado|negado|rejeitado|n[aã]o\s+autorizado))\b",
            r"\b(venda\s+(recusada|negada|n[aã]o\s+passou|n[aã]o\s+autorizada))\b",
            r"\b(n[aã]o\s+autorizad[ao]|saldo\s+insuficiente)\b",
            r"\b(decline\s+error|transaction\s+declined)\b",
        ]
        if any(re.search(pat, lower_msg) for pat in decline_patterns):
            code_match = re.search(r"\b(51|05|57|12)\b", lower_msg)
            code = code_match.group(1) if code_match else "51"
            logger.info(f"Rules engine decided tool_call: diagnose_declined_transaction (code={code})")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "diagnose_declined_transaction",
                    "args": {"user_id": user_id, "error_code": code},
                    "id": call_id
                }]
            )

        # 3. Settlement & Yesterday Sales
        settlement_patterns = [
            r"\b(ontem|yesterday)\b",
            r"\b(vendas?\s+de\s+ontem)\b",
            r"\b(dep[oó]sito\s+(das\s+vendas|de\s+ontem))\b",
            r"\b(quando\s+(vai\s+)?cair\s+(o\s+)?dinheiro)\b",
            r"\b(quanto\s+(dinheiro\s+)?(eu\s+)?tenho\s+para\s+receber)\b",
            r"\b(previs[aã]o\s+de\s+dep[oó]sito)\b",
            r"\b(extrato\s+de\s+liquida[cç][aã]o)\b",
            r"\b(liquida[cç][aã]o\s+financeira)\b",
            r"\b(saldo\s+a\s+receber)\b",
        ]
        if any(re.search(pat, lower_msg) for pat in settlement_patterns):
            logger.info("Rules engine decided tool_call: get_settlement_status")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "get_settlement_status",
                    "args": {"user_id": user_id},
                    "id": call_id
                }]
            )

        # 4. Terminal Connectivity & Hardware Diagnostics
        terminal_patterns = [
            r"\b(n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect(a|ando|ou))\b",
            r"\b(n[aã]o\s+consigo\s+conectar|n[aã]o\s+quer\s+conectar)\b",
            r"\b(won't\s+connect|wont\s+connect|cannot\s+connect|can't\s+connect)\b",
            r"\b(sem\s+(sinal|conex[aã]o|internet|rede))\b",
            r"\b(sinal\s+do\s+chip|chip\s+da\s+m[aá]quina|sinal\s+m[oó]vel|sinal\s+fraco)\b",
            r"\b(m[aá]quina|maquininha|pos|terminal)\b.*(offline|n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|defeito|travad[ao]|problema\s+de\s+conex[aã]o)",
            r"\b(offline|n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|defeito|travad[ao]|problema\s+de\s+conex[aã]o).*(m[aá]quina|maquininha|pos|terminal)\b",
            r"\b(erro\s+de\s+(internet|conex[aã]o|rede)|falha\s+de\s+(internet|conex[aã]o|rede)|problema\s+de\s+(internet|conex[aã]o|rede))\b",
            r"\b(problema\s+na\s+(m[aá]quina|maquininha|internet|conex[aã]o))\b",
            r"\b(problema\s+de\s+internet\s+na\s+maquininha)\b",
            r"\b(conectando\s+na\s+internet|conectar\s+na\s+internet|conectar\s+ao\s+wi-?fi)\b.*(n[aã]o|problema|erro|falha|como|ajuda)",
            r"\b(n[aã]o|problema|erro|falha|como|ajuda).*(conectando\s+na\s+internet|conectar\s+na\s+internet|conectar\s+ao\s+wi-?fi)\b",
        ]
        if any(re.search(pat, lower_msg) for pat in terminal_patterns):
            logger.info("Rules engine decided tool_call: diagnose_terminal")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "diagnose_terminal",
                    "args": {"user_id": user_id},
                    "id": call_id
                }]
            )

        # 5. External Web Search (real-time public information: weather, exchange rates)
        web_search_patterns = [
            r"\b(weather|previs[aã]o\s+do\s+tempo|tempo\s+em|clima\s+em)\b",
            r"\b(porto\s+alegre|rio\s+de\s+janeiro|s[aã]o\s+paulo)\b.*(tempo|clima|chuva|graus|weather|temperatura)",
            r"\b(euro|d[oó]lar|dollar|c[aâ]mbio|exchange\s+rate|cota[cç][aã]o)\b",
        ]
        if any(re.search(pat, lower_msg) for pat in web_search_patterns):
            logger.info("Rules engine decided tool_call: search_web")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_web",
                    "args": {"query": user_text},
                    "id": call_id
                }]
            )

        # 6. Direct Conversational Greetings (No tool needed)
        greeting_patterns = [
            r"^(ol[aá]|oi|bom\s+dia|boa\s+tarde|boa\s+noite|tudo\s+bem|como\s+vai)\b"
        ]
        if any(re.search(pat, lower_msg) for pat in greeting_patterns) and len(lower_msg.split()) <= 4:
            logger.info("Rules engine responding directly to greeting (no tool needed).")
            return AIMessage(
                content=(
                    "Olá! Sou o assistente inteligente de suporte da Getnet. "
                    "Posso consultar o status das suas vendas de ontem, diagnosticar sua maquininha, "
                    "verificar motivos de recusa de transações ou tirar dúvidas sobre nossos produtos e taxas. "
                    "Como posso ajudar você hoje?"
                )
            )

        # 7. Knowledge Base Search (Default for domain questions & multi-turn product inquiries)
        prior_human_msgs = []
        last_ai_idx = -1
        for idx, m in enumerate(messages[:-1]):
            if isinstance(m, AIMessage):
                last_ai_idx = idx

        if last_ai_idx != -1:
            for m in messages[:last_ai_idx + 1]:
                if isinstance(m, HumanMessage) and m.content and str(m.content).strip():
                    prior_human_msgs.append(str(m.content).strip())

        search_query = user_text
        if prior_human_msgs:
            search_query = f"{prior_human_msgs[-1]} {user_text}"

        logger.info(f"Rules engine decided tool_call: search_knowledge_base for query '{search_query}'")
        return AIMessage(
            content="",
            tool_calls=[{
                "name": "search_knowledge_base",
                "args": {"query": search_query},
                "id": call_id
            }]
        )

    def _synthesize_from_tool_observation(
        self,
        messages: list[BaseMessage],
        user_id: str
    ) -> AIMessage:
        """Observe tool result messages and synthesize final grounded response."""
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        if not tool_messages:
            return AIMessage(content="Informações operacionais consultadas com sucesso no sistema Getnet.")

        latest_tool_msg = tool_messages[-1]
        raw_content = latest_tool_msg.content

        try:
            data = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
        except (json.JSONDecodeError, TypeError):
            return AIMessage(content=f"Resultado da consulta operacional:\n\n{raw_content}")

        if "yesterday_sales" in data:
            return AIMessage(content=self._format_settlement(data))

        if "troubleshooting_steps" in data:
            return AIMessage(content=self._format_terminal_troubleshooting(data))

        if "code_details" in data or "latest_declined_transaction" in data:
            return AIMessage(content=self._format_declined_transaction(data))

        if "ticket_id" in data:
            return AIMessage(content=self._format_escalation_ticket(data))

        if "results" in data and ("status" in data or "query" in data):
            if "documents" in data or ("status" in data and data.get("status") in ["success", "abstain"] and "documents" in data):
                return AIMessage(content=self._format_knowledge_response(data, messages=messages))
            else:
                return AIMessage(content=self._format_web_search_response(data))

        if "documents" in data:
            return AIMessage(content=self._format_knowledge_response(data, messages=messages))

        return AIMessage(content=f"Consulta executada com sucesso:\n\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    def _format_settlement(self, data: dict[str, Any]) -> str:
        sales = data.get("yesterday_sales", {})
        total_tx = sales.get("total_transactions", 0)
        gross = sales.get("gross_amount_brl", 0.0)
        net = sales.get("net_amount_brl", 0.0)
        deposit_time = sales.get("estimated_deposit_time", "Até as 20h00")
        dest_account = sales.get("destination_account", "Conta cadastrada no Santander")

        return (
            f"Verifiquei as suas vendas de ontem no sistema Getnet:\n\n"
            f"• **Total transacionado**: R$ {gross:,.2f} ({total_tx} transações)\n"
            f"• **Valor líquido a receber**: R$ {net:,.2f}\n"
            f"• **Previsão de depósito**: **Hoje, {deposit_time}** (D+1 útil)\n"
            f"• **Conta de destino**: {dest_account}\n\n"
            f"O depósito está programado e segue o fluxo padrão de liquidação financeira da sua conta."
        )

    def _format_terminal_troubleshooting(self, data: dict[str, Any]) -> str:
        model = data.get("terminal_model", "Terminal Getnet")
        serial = data.get("serial_number", "GET-883921")
        operator = data.get("sim_operator", "Claro/Vivo")
        signal = data.get("signal_level", "fraco")
        diagnosis = data.get("diagnosis", "Sinal móvel instável.")
        steps = data.get("troubleshooting_steps", [])

        steps_formatted = "\n".join([f"• {s.lstrip('0123456789. -')}" for s in steps]) if steps else "• Reinicie o terminal."

        return (
            f"Identifiquei que sua máquina {model} (Série {serial}) está com sinal de chip móvel {signal} (operadora {operator}). "
            f"{diagnosis}\n\n"
            f"Siga este passo a passo para reiniciar e restabelecer a conexão (Wi-Fi ou chip):\n\n"
            f"{steps_formatted}"
        )

    def _format_declined_transaction(self, data: dict[str, Any]) -> str:
        code = data.get("queried_code", "")
        details = data.get("code_details", {})
        title = details.get("title", "")
        cause = details.get("cause", "")
        action = details.get("recommended_action", "")
        last_txn = data.get("latest_declined_transaction") or data.get("last_declined_transaction", {})
        txn_id = last_txn.get("transaction_id", "")
        amount = last_txn.get("amount_brl", 0.0)
        brand = last_txn.get("card_brand", "")

        return (
            f"Analisando a sua última transação recusada (Código {code} - {title}):\n\n"
            f"• **Transação**: {txn_id} no valor de R$ {amount:,.2f} ({brand})\n"
            f"• **Motivo da recusa**: {cause}\n"
            f"• **O que fazer**: {action}"
        )

    def _format_escalation_ticket(self, data: dict[str, Any]) -> str:
        ticket_id = data.get("ticket_id", "GET-TKT-PENDING")
        tracking_endpoint = data.get("tracking_endpoint", f"/tickets/{ticket_id}")
        reason = data.get("reason", "Atendimento humano")

        return (
            f"Registrei o seu chamado de atendimento humano no sistema Getnet:\n\n"
            f"• **Protocolo do Chamado**: **{ticket_id}**\n"
            f"• **Status**: Aberto (Aguardando especialista humano)\n"
            f"• **Motivo registrado**: {reason}\n"
            f"• **Acompanhamento**: Você pode verificar o andamento a qualquer momento pelo endpoint `{tracking_endpoint}` ou informando o protocolo à equipe de suporte."
        )

    def _format_knowledge_response(
        self,
        data: dict[str, Any],
        messages: list[BaseMessage] | None = None
    ) -> str:
        documents = data.get("documents", [])

        if documents:
            primary = documents[0]
            title = primary.get("title", "Getnet Documentação")
            content = primary.get("content", "")
            url = primary.get("url", "https://www.getnet.com.br")

            return (
                f"De acordo com a documentação oficial da Getnet (**{title}**):\n\n"
                f"{content}\n\n"
                f"Fonte oficial: {url}"
            )

        return (
            data.get("message")
            or "Não foram encontradas informações oficiais sobre este assunto nos manuais e documentações cadastrados da Getnet."
        )

    def _format_web_search_response(self, data: dict[str, Any]) -> str:
        query = data.get("query", "sua consulta")
        status = data.get("status", "unavailable")

        if status == "unavailable" or not data.get("results"):
            return (
                f"Informamos que a consulta externa de informações em tempo real sobre '{query}' "
                "está temporariamente indisponível no momento. Por favor, tente novamente em instantes."
            )

        snippets = data.get("results", [])
        formatted = []
        for s in snippets:
            t = s.get("title", "")
            b = s.get("snippet", "")
            u = s.get("url", "")
            formatted.append(f"• **{t}** — {b} (Fonte: {u})")

        body = "\n".join(formatted)
        return f"Resultados da pesquisa web sobre '{query}':\n\n{body}"


_rules_engine_instance: RulesFallbackEngine | None = None


def get_rules_engine() -> RulesFallbackEngine:
    """Dependency getter for Rules Fallback Engine."""
    global _rules_engine_instance
    if _rules_engine_instance is None:
        _rules_engine_instance = RulesFallbackEngine()
    return _rules_engine_instance


get_supervisor_llm = get_rules_engine
LLMClient = RulesFallbackEngine
get_llm = get_rules_engine
