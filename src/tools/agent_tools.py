"""Typed agent tools with Pydantic schemas for the LangGraph Supervisor."""
import datetime as dt
import json
import logging
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

import src.rag.retriever as rag_retriever
from src.core import notifier
from src.core.log_context import exc_brief
from src.core.tickets_db import get_tickets_repository
from src.tools.balance_tools import (
    get_declined_transaction_details,
    get_settlement_and_sales_status,
)
from src.tools.public_data import (
    FX_SOURCE,
    fetch_exchange_rate,
    fetch_weather,
)
from src.tools.terminal_tools import diagnose_terminal_connectivity
from src.tools.web_search import web_search_tool

logger = logging.getLogger("multiagent.tools")
# httpx logs every request URL (city, currency, dates) at INFO: keep it at WARNING so queries never reach the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)


@tool
def get_settlement_status(config: RunnableConfig) -> str:
    """
    Consulta a liquidação financeira de vendas de ontem e saldo a receber do lojista Getnet.
    Use sempre que o usuário perguntar sobre:
    - Vendas de ontem e valores a receber
    - Previsão de horário do depósito bancário (D+1)
    - Extrato de liquidação financeira e conta de destino cadastrada
    - Saldo disponível para antecipação
    """
    user_id = config["configurable"]["user_id"]
    logger.info("[Tool: get_settlement_status] invoked")
    result = get_settlement_and_sales_status(user_id=user_id)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def diagnose_declined_transaction(error_code: str | None = None, config: RunnableConfig = None) -> str:
    """
    Diagnostica motivos de transações recusadas na maquininha Getnet e orienta o lojista.
    Use sempre que o usuário relatar:
    - Transação recusada ou venda não aprovada no cartão
    - Código de erro de recusa (ex: Código 51 saldo insuficiente, Código 05 não autorizada)
    - Dúvidas sobre o motivo de recusa pelo banco emissor e o que fazer

    Args:
        error_code: Código numérico opcional da recusa (ex: '51').
    """
    user_id = config["configurable"]["user_id"]
    logger.info(f"[Tool: diagnose_declined_transaction] invoked (error_code_given={bool(error_code)})")
    result = get_declined_transaction_details(user_id=user_id, error_code=error_code)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def diagnose_terminal(serial_number: str | None = None, config: RunnableConfig = None) -> str:
    """
    Realiza diagnóstico técnico e de conectividade nas maquininhas Getnet (Get Smart, Get Clássica, etc.).
    Use sempre que o usuário relatar:
    - Maquininha não conecta à internet ou erro de conexão
    - Sinal fraco ou instabilidade no chip 3G/4G
    - Dificuldades para conectar na rede Wi-Fi
    - Necessidade de passo a passo para reiniciar o terminal

    Args:
        serial_number: Número de série do terminal (opcional).
    """
    user_id = config["configurable"]["user_id"]
    logger.info(f"[Tool: diagnose_terminal] invoked (serial_given={bool(serial_number)})")
    result = diagnose_terminal_connectivity(user_id=user_id, terminal_serial=serial_number)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def search_knowledge_base(query: str) -> str:
    """
    Busca trechos das páginas oficiais da Getnet com URL e data de coleta.
    Retorna status 'success' com documentos relevantes, 'abstain' caso não encontre
    informações suficientes acima do limiar de relevância, ou 'unavailable' caso o serviço esteja indisponível.

    Args:
        query: Pergunta ou termos de busca sobre produtos, serviços e políticas Getnet.
    """
    logger.info(f"[Tool: search_knowledge_base] invoked (query_chars={len(query)})")
    try:
        retriever = rag_retriever.get_knowledge_retriever()
        result = retriever.search(query)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Tool: search_knowledge_base] Error querying knowledge retriever: {exc_brief(exc)}")
        return json.dumps(
            {
                "status": "unavailable",
                "query": query,
                "documents": [],
                "error": type(exc).__name__,
            },
            ensure_ascii=False,
            indent=2,
        )


@tool
def get_weather_forecast(city: str, country_code: str | None = None, days: int = 3) -> str:
    """
    Previsão do tempo e condição atual de uma cidade pela API Open-Meteo, com unidade, data de referência e URL da fonte.
    Use para qualquer pergunta sobre clima, temperatura, chuva ou previsão do tempo. Nunca use search_web para clima.

    Args:
        city: Nome da cidade (ex.: 'Porto Alegre').
        country_code: Código ISO de 2 letras do país, quando conhecido (ex.: 'BR').
        days: Número de dias de previsão, de 1 a 7 (padrão 3).
    """
    result = fetch_weather(city, country_code, days)
    logger.info(f"[Tool: get_weather_forecast] invoked (status={result['status']})")
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def get_exchange_rate(currency: str, date: str | None = None) -> str:
    """
    Cotação PTAX de fechamento do Banco Central do Brasil (taxa de referência, em reais por unidade da moeda), com data e URL da fonte.
    Use para qualquer pergunta sobre câmbio ou cotação de moeda estrangeira (dólar, euro etc.). Nunca use search_web para câmbio.

    Args:
        currency: Código ISO de 3 letras da moeda (ex.: 'USD', 'EUR').
        date: Data no formato AAAA-MM-DD; omita para a cotação de fechamento mais recente.
    """
    if not date or not date.strip():
        result = fetch_exchange_rate(currency)
    else:
        try:
            parsed = dt.date.fromisoformat(date.strip())
            result = fetch_exchange_rate(currency, parsed)
        except ValueError:
            result = {
                "status": "invalid_request",
                "source": FX_SOURCE,
                "source_url": None,
                "error": "invalid_date",
            }
    logger.info(f"[Tool: get_exchange_rate] invoked (status={result['status']})")
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def search_web(query: str) -> str:
    """
    Busca pública na web via DuckDuckGo, para informação externa que nenhuma outra ferramenta cobre (por exemplo, notícias).
    Nunca use para clima ou câmbio: para isso existem get_weather_forecast e get_exchange_rate. Nunca use para produtos da Getnet.

    Args:
        query: Consulta a ser realizada na internet.
    """
    logger.info(f"[Tool: search_web] invoked (query_chars={len(query)})")
    result = web_search_tool(query=query, max_results=3)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def escalate_to_human(
    reason: str,
    priority: Literal["standard", "high"] = "standard",
    config: RunnableConfig = None,
) -> str:
    """
    Registra um chamado formal de transbordo e atendimento humano no banco de dados do sistema.
    Use quando:
    - O usuário solicitar expressamente falar com atendente, pessoa, especialista ou operador humano
    - Houver reclamação formal em ouvidoria, Procon ou ação regulatória (use priority='high')
    - A solicitação do usuário não puder ser resolvida por nenhuma das ferramentas disponíveis

    Args:
        reason: Motivo detalhado do encaminhamento ao time humano de atendimento.
        priority: Prioridade do atendimento humano ('standard' ou 'high'). Use 'high' para Procon, ouvidoria ou urgências críticas.
    """
    cfg = config.get("configurable", {}) if config else {}
    user_id = cfg.get("user_id", "")
    session_id = cfg.get("session_id")
    transcript = cfg.get("transcript")

    logger.info(f"[Tool: escalate_to_human] priority={priority}, reason_chars={len(reason)}")
    try:
        repo = get_tickets_repository()
        ticket = repo.create_ticket(
            user_id=user_id,
            reason=reason,
            priority=priority,
            session_id=session_id,
            transcript=transcript,
        )
        try:
            notify_result = notifier.get_notifier().notify(ticket)
            repo.record_notification(ticket["ticket_id"], notify_result.status)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Operator notification failed cleanly: {exc_brief(exc)}")
        return json.dumps(ticket, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to persist escalation ticket: {exc_brief(exc)}")
        return json.dumps({"status": "error", "error": "ticket_persistence_failed"}, ensure_ascii=False)


ALL_TOOLS: list[Any] = [
    get_settlement_status,
    diagnose_declined_transaction,
    diagnose_terminal,
    search_knowledge_base,
    get_weather_forecast,
    get_exchange_rate,
    search_web,
    escalate_to_human,
]

TOOLS_BY_NAME: dict[str, Any] = {tool_fn.name: tool_fn for tool_fn in ALL_TOOLS}
