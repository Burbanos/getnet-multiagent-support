"""Semantic intent classifier and agent dispatcher."""
import logging
import re
from src.core.state import AgentState, AgentRole, RouteDecision
from src.config import settings

logger = logging.getLogger("multiagent.router")


class RouterAgent:
    """Analyzes incoming messages and routes them to specialized agents."""

    def route(self, state: AgentState) -> AgentState:
        message = state.message.lower()

        # 1. Human Escalation Requests
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
        if any(re.search(pat, message) for pat in escalation_patterns):
            state.route = RouteDecision(
                target_agent=AgentRole.ESCALATION,
                intent="human_escalation",
                confidence=0.98,
                reasoning="Solicitação explícita de intervenção humana ou canal regulatório."
            )
            state.intent = "human_escalation"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 2. Customer Support - Declined Transaction Lookups
        # (Prioritized BEFORE general terminal hardware errors so inquiries like
        # "Minha maquininha deu erro de transação recusada na última venda. Qual foi o motivo?" route to diagnose_decline)
        is_decline_inquiry = any(re.search(pat, message) for pat in [
            r"\b(recusa|recusad[ao]s?|declined?)\b",
            r"\b(c[oó]digo\s+(de\s+)?recusa|c[oó]digo\s+51|erro\s+51)\b",
            r"\b(transa[cç][aã]o\s+(recusada|negada|n[aã]o\s+passou|n[aã]o\s+autorizada|com\s+erro|falhou))\b",
            r"\b(erro\s+de\s+transa[cç][aã]o)\b",
            r"\b(cart[aã]o\s+(recusado|negado|rejeitado|n[aã]o\s+autorizado))\b",
            r"\b(venda\s+(recusada|negada|n[aã]o\s+passou|n[aã]o\s+autorizada))\b",
            r"\b(n[aã]o\s+autorizad[ao]|saldo\s+insuficiente)\b",
            r"\b(decline\s+error|transaction\s+declined)\b",
        ])
        if is_decline_inquiry:
            state.route = RouteDecision(
                target_agent=AgentRole.CUSTOMER_SUPPORT,
                intent="diagnose_decline",
                confidence=0.96,
                reasoning="Consulta sobre transação recusada, código de recusa ou não autorização de venda."
            )
            state.intent = "diagnose_decline"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 3. Customer Support - Settlement & Yesterday Sales
        is_deposit_inquiry = any(re.search(pat, message) for pat in [
            r"\b(ontem|yesterday)\b",
            r"\b(vendas?\s+de\s+ontem)\b",
            r"\b(dep[oó]sito\s+(das\s+vendas|de\s+ontem))\b",
            r"\b(quando\s+(vai\s+)?cair\s+(o\s+)?dinheiro)\b",
            r"\b(quanto\s+(dinheiro\s+)?(eu\s+)?tenho\s+para\s+receber)\b",
            r"\b(previs[aã]o\s+de\s+dep[oó]sito)\b",
            r"\b(extrato\s+de\s+liquida[cç][aã]o)\b",
            r"\b(liquida[cç][aã]o\s+financeira)\b",
        ])
        if is_deposit_inquiry:
            state.route = RouteDecision(
                target_agent=AgentRole.CUSTOMER_SUPPORT,
                intent="check_settlement",
                confidence=0.96,
                reasoning="Consulta sobre liquidação financeira, extrato e depósito de vendas."
            )
            state.intent = "check_settlement"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 4. Customer Support - Terminal Connectivity & Hardware Troubleshooting
        is_terminal_inquiry = any(re.search(pat, message) for pat in [
            r"\b(n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect(a|ando|ou))\b",
            r"\b(n[aã]o\s+consigo\s+conectar|n[aã]o\s+quer\s+conectar)\b",
            r"\b(won't\s+connect|wont\s+connect|cannot\s+connect|can't\s+connect)\b",
            r"\b(sem\s+(sinal|conex[aã]o|internet|rede))\b",
            r"\b(sinal\s+do\s+chip|chip\s+da\s+m[aá]quina|sinal\s+m[oó]vel|sinal\s+fraco)\b",
            r"\b(m[aá]quina|maquininha|pos|terminal)\b.*(offline|n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|erro|defeito|travad[ao]|problema\s+de\s+conex[aã]o)",
            r"\b(offline|n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|erro|defeito|travad[ao]|problema\s+de\s+conex[aã]o).*(m[aá]quina|maquininha|pos|terminal)\b",
            r"\b(erro\s+de\s+(internet|conex[aã]o|rede)|falha\s+de\s+(internet|conex[aã]o|rede)|problema\s+de\s+(internet|conex[aã]o|rede))\b",
            r"\b(problema\s+na\s+(m[aá]quina|maquininha|internet|conex[aã]o))\b",
            r"\b(problema\s+de\s+internet\s+na\s+maquininha)\b",
            r"\b(conectando\s+na\s+internet|conectar\s+na\s+internet|conectar\s+ao\s+wi-?fi)\b.*(n[aã]o|problema|erro|falha|como|ajuda)",
            r"\b(n[aã]o|problema|erro|falha|como|ajuda).*(conectando\s+na\s+internet|conectar\s+na\s+internet|conectar\s+ao\s+wi-?fi)\b",
            r"\b(get\s+smart|get\s+cl[aá]ssica)\b.*(n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|offline|erro\s+de\s+internet|problema\s+de\s+conex[aã]o|defeito|trav)",
            r"\b(n[aã]o\s+(est[aá]\s+|t[aá]\s+)?conect|sem\s+internet|sem\s+sinal|offline|erro\s+de\s+internet|problema\s+de\s+conex[aã]o|defeito|trav).*(get\s+smart|get\s+cl[aá]ssica)\b",
        ])
        if is_terminal_inquiry:
            state.route = RouteDecision(
                target_agent=AgentRole.CUSTOMER_SUPPORT,
                intent="troubleshoot_terminal",
                confidence=0.95,
                reasoning="Diagnóstico de conectividade, chip ou problemas de hardware na maquininha."
            )
            state.intent = "troubleshoot_terminal"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 5. External Web Search (real-time public information)
        is_external_search = any(re.search(pat, message) for pat in [
            r"\b(weather|previs[aã]o\s+do\s+tempo|tempo\s+em|clima\s+em)\b",
            r"\b(porto\s+alegre|rio\s+de\s+janeiro|s[aã]o\s+paulo)\b.*(tempo|clima|chuva|graus|weather|temperatura)",
            r"\b(euro|d[oó]lar|dollar|c[aâ]mbio|exchange\s+rate|cota[cç][aã]o)\b",
        ])
        if is_external_search:
            state.route = RouteDecision(
                target_agent=AgentRole.KNOWLEDGE,
                intent="external_web_search",
                confidence=0.95,
                reasoning="Consulta de busca externa na web em tempo real."
            )
            state.intent = "external_web_search"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 6. Getnet Institutional / Products Knowledge (RAG)
        is_getnet_product_query = any(re.search(pat, message) for pat in [
            r"\b(get\s+cl[aá]ssica|get\s+smart|cl[aá]ssica|smart)\b",
            r"\b(diferen[cç]a|difference|qual\s+a\s+melhor)\b",
            r"\b(maquininha|m[aá]quina|pos|terminal)\b",
            r"\b(pix|qr\s*code|chave\s+pix|receber\s+por\s+pix)\b",
            r"\b(conta\s+banc[aá]ria|bank\s+account)\b",
            r"\b(antecipa[cç][aã]o|receb[ií]veis|receivables\s+advance|antecipar)\b",
            r"\b(credi[aá]rio|parcelamento|parcelas|parcelar|split\s+a\s+sale|installments)\b",
            r"\b(link\s+de\s+pagamento|payment\s+link|link|whatsapp)\b",
            r"\b(taxa|taxas|tarifa|tarifas|plano|planos|getnet|santander)\b",
        ])
        if is_getnet_product_query:
            state.route = RouteDecision(
                target_agent=AgentRole.KNOWLEDGE,
                intent="getnet_knowledge_retrieval",
                confidence=0.96,
                reasoning="Consulta institucional sobre catálogo de produtos e serviços Getnet."
            )
            state.intent = "getnet_knowledge_retrieval"
            logger.info(f"Routed to {state.route.target_agent} (Intent: {state.route.intent})")
            return state

        # 7. Unmatched / Ambiguous Query: Low confidence fallback -> Human Escalation
        low_confidence = 0.20
        state.route = RouteDecision(
            target_agent=AgentRole.ESCALATION,
            intent="low_confidence_escalation",
            confidence=low_confidence,
            reasoning=f"Mensagem não corresponde a nenhuma intenção conhecida de suporte, catálogo Getnet ou busca web (confiança {low_confidence:.2f} abaixo do limiar {settings.CONFIDENCE_THRESHOLD_ESCALATION})."
        )
        state.intent = "low_confidence_escalation"
        logger.info(f"Routed to {state.route.target_agent} due to low confidence ({low_confidence:.2f})")
        return state
