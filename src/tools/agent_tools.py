"""Typed agent tools with Pydantic schemas for the LangGraph Supervisor."""
import json
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from src.agents.knowledge import get_retriever
from src.core.tickets_db import get_tickets_repository
from src.tools.balance_tools import (
    get_declined_transaction_details,
    get_settlement_and_sales_status,
)
from src.tools.terminal_tools import diagnose_terminal_connectivity
from src.tools.web_search import web_search_tool

logger = logging.getLogger("multiagent.tools")


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
    logger.info(f"[Tool: get_settlement_status] invoked for user_id={user_id}")
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
    logger.info(f"[Tool: diagnose_declined_transaction] invoked for user_id={user_id}, error_code={error_code}")
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
    logger.info(f"[Tool: diagnose_terminal] invoked for user_id={user_id}, serial={serial_number}")
    result = diagnose_terminal_connectivity(user_id=user_id, terminal_serial=serial_number)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def search_knowledge_base(query: str) -> str:
    """
    Busca semântica vetorial na base de conhecimento oficial de manuais e produtos da Getnet.
    Possui limiar de similaridade: se a dúvida não pertencer aos produtos Getnet, retorna abstenção.
    Use sempre para tirar dúvidas sobre:
    - Modelos de maquininhas Getnet (diferença entre Get Clássica e Get Smart, Get Mini, POS Digital)
    - Recebimento de vendas via Pix e necessidade de conta bancária
    - Como funciona a antecipação de recebíveis (automática vs avulsa)
    - Vendas no crediário e parcelamento em até 36x
    - Venda pelo WhatsApp com Link de Pagamento Getnet
    - Taxas, bobinas, cancelamento e estorno

    Args:
        query: Pergunta ou termos de busca sobre soluções e produtos Getnet.
    """
    logger.info(f"[Tool: search_knowledge_base] query='{query}'")
    retriever = get_retriever()
    docs = retriever.retrieve(query=query, top_k=3, threshold=0.20)

    if not docs:
        return json.dumps({
            "status": "abstain",
            "found": False,
            "query": query,
            "message": "Não foram encontradas informações oficiais sobre este assunto nos manuais e documentações cadastrados da Getnet.",
            "documents": []
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "success",
        "found": True,
        "query": query,
        "count": len(docs),
        "documents": [
            {
                "id": d.get("id"),
                "title": d.get("title"),
                "category": d.get("category"),
                "url": d.get("url"),
                "content": d.get("content"),
                "similarity": d.get("similarity", 0.0),
                "distance": d.get("distance", 0.0),
                "score": d.get("score", 0.0)
            }
            for d in docs
        ]
    }, ensure_ascii=False, indent=2)


@tool
def search_web(query: str) -> str:
    """
    Executa busca pública na web em tempo real via DuckDuckGo.
    Use estritamente para informações externas que não pertencem ao catálogo Getnet, como:
    - Previsão do tempo e clima em cidades (ex: Porto Alegre)
    - Cotação de moedas e câmbio em tempo real (Euro, Dólar)
    - Notícias e dados públicos externos atuais

    Args:
        query: Consulta a ser realizada na internet em tempo real.
    """
    logger.info(f"[Tool: search_web] query='{query}'")
    result = web_search_tool(query=query, max_results=3)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def escalate_to_human(reason: str, config: RunnableConfig) -> str:
    """
    Registra um chamado formal de transbordo e atendimento humano no banco de dados do sistema.
    Use quando:
    - O usuário solicitar expressamente falar com atendente, pessoa, especialista ou operador humano
    - Houver reclamação formal em ouvidoria, Procon ou ação regulatória
    - A solicitação do usuário não puder ser resolvida por nenhuma das ferramentas disponíveis

    Args:
        reason: Motivo detalhado do encaminhamento ao time humano de atendimento.
    """
    user_id = config["configurable"]["user_id"]
    logger.info(f"[Tool: escalate_to_human] user_id={user_id}, reason='{reason}'")
    repo = get_tickets_repository()
    ticket = repo.create_ticket(user_id=user_id, reason=reason)
    return json.dumps(ticket, ensure_ascii=False, indent=2)


ALL_TOOLS: list[Any] = [
    get_settlement_status,
    diagnose_declined_transaction,
    diagnose_terminal,
    search_knowledge_base,
    search_web,
    escalate_to_human,
]

TOOLS_BY_NAME: dict[str, Any] = {tool_fn.name: tool_fn for tool_fn in ALL_TOOLS}
