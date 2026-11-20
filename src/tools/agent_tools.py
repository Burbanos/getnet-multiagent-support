"""Typed agent tools with Pydantic schemas for the LangGraph Supervisor."""
import datetime as dt
import json
import logging
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

import src.rag.retriever as rag_retriever
from src.core import notifier
from src.core.actions_db import get_actions_repository
from src.core.log_context import exc_brief
from src.core.mock_db import get_mock_db
from src.core.pii import sanitize_pii
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
def diagnose_declined_transaction(
    code_context: Literal["declined_sale", "terminal_screen", "app", "unknown"],
    error_code: str | None = None,
    config: RunnableConfig = None,
) -> str:
    """
    Diagnostica motivos de transações recusadas na maquininha Getnet e orienta o lojista.
    Use sempre que o usuário relatar:
    - Transação recusada ou venda não aprovada no cartão
    - Código de erro de recusa (ex: Código 51 saldo insuficiente, Código 05 não autorizada)
    - Dúvidas sobre o motivo de recusa pelo banco emissor e o que fazer
    Não use para erros exibidos em telas de configuração, rede, atualização ou inicialização da maquininha:
    o catálogo cobre só códigos de recusa de transação de cartão.

    Args:
        code_context: Onde o código apareceu: 'declined_sale' (venda/pagamento recusado no cartão),
            'terminal_screen' (tela da maquininha fora de venda: configuração, rede, Wi-Fi, atualização,
            inicialização), 'app' (app ou portal Getnet) ou 'unknown' (não informado no pedido).
        error_code: Código numérico opcional da recusa (ex: '51').
    """
    if code_context in ("terminal_screen", "app"):
        queried = error_code.strip() if error_code else None
        logger.info(
            "[Tool: diagnose_declined_transaction] not_applicable "
            f"(code_context={code_context}, error_code_given={bool(queried)})"
        )
        return json.dumps(
            {
                "status": "not_applicable",
                "code_context": code_context,
                "queried_code": queried,
                "reason": (
                    "o catálogo cobre apenas códigos de recusa de transação de cartão; "
                    "o código não veio de uma venda recusada"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )

    user_id = config["configurable"]["user_id"]
    logger.info(
        "[Tool: diagnose_declined_transaction] invoked "
        f"(code_context={code_context}, error_code_given={bool(error_code)})"
    )
    result = get_declined_transaction_details(user_id=user_id, error_code=error_code)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def diagnose_terminal(
    serial_number: str | None = None,
    screen_error_code: str | None = None,
    config: RunnableConfig = None,
) -> str:
    """
    Realiza diagnóstico técnico e de conectividade nas maquininhas Getnet (Get Smart, Get Clássica, etc.).
    Use sempre que o usuário relatar:
    - Maquininha não conecta à internet ou erro de conexão
    - Sinal fraco ou instabilidade no chip 3G/4G
    - Dificuldades para conectar na rede Wi-Fi
    - Necessidade de passo a passo para reiniciar o terminal
    - Código exibido na tela da maquininha fora de venda (informe screen_error_code)

    Args:
        serial_number: Número de série do terminal (opcional).
        screen_error_code: Código de erro exibido na tela da maquininha fora de venda (opcional).
    """
    user_id = config["configurable"]["user_id"]
    clean_code = screen_error_code.strip() if isinstance(screen_error_code, str) else ""
    logger.info(
        "[Tool: diagnose_terminal] invoked "
        f"(serial_given={bool(serial_number)}, screen_error_code_given={bool(clean_code)})"
    )
    result = diagnose_terminal_connectivity(
        user_id=user_id,
        terminal_serial=serial_number,
        screen_error_code=screen_error_code,
    )
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
def request_terminal_replacement(serial_number: str, reason: str, config: RunnableConfig = None) -> str:
    """
    Propõe a solicitação de troca de uma maquininha do lojista. Apenas cria a proposta para confirmação
    no próximo turno; nenhum pedido é aberto até que o lojista confirme.

    Args:
        serial_number: Número de série da maquininha do lojista (ex.: 'GET-883921').
        reason: Motivo resumido da troca sem dados pessoais.
    """
    cfg = config.get("configurable", {}) if config else {}
    user_id = str(cfg.get("user_id") or "")
    session_id = str(cfg.get("session_id") or "default")
    trace_id = str(cfg.get("trace_id") or "")
    clean_serial = serial_number.strip()

    user = get_mock_db().get_user(user_id)
    terminals = (user or {}).get("terminals", [])
    matched = next((t for t in terminals if t.get("serial_number") == clean_serial), None)
    actions_repo = get_actions_repository()

    if user is None or matched is None:
        actions_repo.record_audit(
            actor_type="merchant",
            actor_id=user_id or "unknown",
            action="replacement_proposal_rejected",
            target_type="terminal",
            target_id=clean_serial or "unknown",
            outcome="not_found",
            details={"serial_number": clean_serial, "reason_code": "terminal_not_found"},
            trace_id=trace_id or None,
        )
        return json.dumps({"status": "not_found", "error": "terminal_not_found"}, ensure_ascii=False, indent=2)

    open_req = actions_repo.get_open_replacement(clean_serial)
    if open_req is not None:
        actions_repo.record_audit(
            actor_type="merchant",
            actor_id=user_id,
            action="replacement_proposal_rejected",
            target_type="terminal_replacement",
            target_id=open_req["request_id"],
            outcome="already_requested",
            details={"serial_number": clean_serial, "request_id": open_req["request_id"], "status": "requested"},
            trace_id=trace_id or None,
        )
        return json.dumps(
            {
                "status": "already_requested",
                "request_id": open_req["request_id"],
                "serial_number": clean_serial,
            },
            ensure_ascii=False,
            indent=2,
        )

    safe_reason, _ = sanitize_pii(reason or "")
    clean_reason = safe_reason.strip()[:300] or "troca de maquininha"
    logger.info(f"[Tool: request_terminal_replacement] invoked (serial_given={bool(clean_serial)}, reason_chars={len(clean_reason)})")
    proposal = actions_repo.propose_terminal_replacement(
        user_id=user_id,
        session_id=session_id,
        serial_number=clean_serial,
        reason=clean_reason,
        trace_id=trace_id,
        ttl_minutes=30,
    )
    return json.dumps(
        {
            "status": "pending_confirmation",
            "action_id": proposal["action_id"],
            "serial_number": proposal["serial_number"],
            "model": matched.get("model"),
            "reason": clean_reason,
            "expires_in_minutes": 30,
            "message": "Nothing was requested yet: the merchant must confirm in the next message.",
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def escalate_to_human(
    reason: str,
    priority: Literal["standard", "high"] = "standard",
    config: RunnableConfig = None,
) -> str:
    """
    Registra um chamado formal de transbordo e atendimento humano no banco de dados do sistema.
    Use quando:
    - O lojista pede para falar com uma pessoa/atendente ou para abrir um chamado
    - O lojista registra reclamação formal (Procon, ouvidoria, Banco Central, justiça) (use priority='high')
    - O lojista aceita a oferta do assistente de abrir um chamado

    Args:
        reason: Motivo detalhado do encaminhamento ao time humano de atendimento.
        priority: Prioridade do atendimento humano ('standard' ou 'high'). Use 'high' para Procon, ouvidoria ou urgências críticas.
    """
    cfg = config.get("configurable", {}) if config else {}
    user_id = cfg.get("user_id", "")
    session_id = cfg.get("session_id")
    transcript = cfg.get("transcript")
    actor_type = cfg.get("actor_type", "merchant")

    logger.info(f"[Tool: escalate_to_human] priority={priority}, reason_chars={len(reason)}")
    try:
        repo = get_tickets_repository()
        ticket = repo.create_ticket(
            user_id=user_id,
            reason=reason,
            priority=priority,
            session_id=session_id,
            transcript=transcript,
            actor_type=actor_type,
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
    request_terminal_replacement,
]

TOOLS_BY_NAME: dict[str, Any] = {tool_fn.name: tool_fn for tool_fn in ALL_TOOLS}
