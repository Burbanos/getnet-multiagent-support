"""FastAPI HTTP service exposing the Multi-Agent Support System API."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import settings, logger
from src.core.graph import get_orchestrator
from src.agents.knowledge import get_retriever


class ChatRequest(BaseModel):
    """Chat request payload containing user identifier, message, and optional session ID."""
    message: str = Field(..., description="Message payload to be evaluated by the multi-agent graph", min_length=1)
    user_id: str = Field(default="cliente1988", description="Unique merchant or customer identifier", min_length=1)
    session_id: Optional[str] = Field(default=None, description="Conversational thread/session ID for persistent multi-turn memory")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Qual a diferença entre a Get Clássica e a Get Smart?",
                "user_id": "cliente1988",
                "session_id": "sess-user-001"
            }
        }
    }


class AgentMetadata(BaseModel):
    """Telemetry and trace metadata for graph execution."""
    agent_type: str = Field(default="SupervisorAgent", description="Final agent that synthesized the response")
    routed_by: str = Field(default="SupervisorAgent", description="Supervisor ReAct orchestration engine")
    decision_engine: str = Field(default="rules_fallback", description="Engine used for decision/routing")
    session_id: str = Field(default="", description="Conversational session ID")
    trace_id: str = Field(default="", description="Unique UUID trace identifier for observability")
    tools_used: List[str] = Field(default_factory=list, description="Tools invoked during pipeline execution")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Structured ReAct tool invocations")
    execution_time_ms: float = Field(..., description="Total execution latency in milliseconds")
    sources: List[str] = Field(default_factory=list, description="Referenced URLs or knowledge base documents")
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list, description="ChromaDB vector retrieval results with cosine similarity")
    ticket: Optional[Dict[str, Any]] = Field(default=None, description="Persisted support ticket if escalation occurred")
    tokens: Optional[Dict[str, int]] = Field(default=None, description="Token usage estimation")
    estimated_cost_usd: Optional[float] = Field(default=None, description="Estimated execution cost in USD")
    debug_details: Optional[Dict[str, Any]] = Field(default=None, description="Diagnostic payload")


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> Optional[str]:
    """
    Validate optional X-API-Key header.
    Defaults to accepting 'getnet-dev-key' or omitted header for frictionless local/docker execution.
    Rejects unauthorized keys with HTTP 401.
    """
    configured_key = getattr(settings, "API_KEY", "getnet-dev-key")
    valid_keys = {"getnet-dev-key", configured_key}
    if x_api_key is not None and x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida. Forneça uma chave autorizada no cabeçalho 'X-API-Key'."
        )
    return x_api_key


class ChatResponse(BaseModel):
    """Chat response payload."""
    response: str = Field(..., description="Synthesized agent response")
    agent: str = Field(default="SupervisorAgent", description="Identifier of the executing supervisor agent")
    user_id: str = Field(..., description="Merchant or customer identifier")
    metadata: AgentMetadata = Field(..., description="Execution telemetry and audit trail")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    llm_provider: str
    guardrails_enabled: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Getnet Multi-Agent Support System API",
    description="Multi-agent support system for Getnet merchants with Supervisor ReAct architecture, RAG, operational tools, and safety guardrails.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["General"])
async def root():
    return {
        "service": "Getnet Multi-Agent Support System",
        "version": "2.0.0",
        "architecture": "Supervisor ReAct with Tool Calling & MemorySaver",
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "chat_endpoint": "/chat",
        "interactive_demo": "/demo",
        "tickets_endpoint": "/tickets"
    }


@app.get("/demo", response_class=FileResponse, tags=["Demo"])
@app.get("/ui", response_class=FileResponse, tags=["Demo"])
async def demo_ui():
    demo_file = STATIC_DIR / "demo.html"
    if demo_file.exists():
        return FileResponse(str(demo_file))
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Arquivo de interface interativa (demo.html) não encontrado."
    )


@app.get("/health", response_model=HealthResponse, tags=["Observability"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        environment=settings.APP_ENV,
        llm_provider=settings.LLM_PROVIDER,
        guardrails_enabled=settings.ENABLE_GUARDRAILS,
    )


@app.get("/agents", tags=["Architecture"])
async def list_agents():
    return {
        "architecture": "LangGraph Supervisor Workflow",
        "orchestrator": {
            "name": "SupervisorAgent",
            "model_reference": "Rules fallback (fallback por regras)",
            "checkpointer": "MemorySaver (thread-scoped multi-turn state)",
            "safety": "GuardrailAgent (PII sanitization & prompt injection defense)"
        },
        "agents": [
            {"name": "SupervisorAgent", "role": "LangGraph Supervisor Orchestrator (fallback por regras)", "tools": ["decide_or_synthesize"]},
            {"name": "GuardrailAgent", "role": "PII Masking & Safety Guardrail", "tools": ["sanitize_pii", "regex_safety_evaluator"]}
        ],
        "tools": [
            {
                "name": "get_settlement_status",
                "specialist": "CustomerSupportSpecialist",
                "description": "Consulta liquidação financeira e previsão de depósito D+1",
                "schema": "get_settlement_status(user_id: str)"
            },
            {
                "name": "diagnose_declined_transaction",
                "specialist": "CustomerSupportSpecialist",
                "description": "Diagnostica recusas de cartão (código 51 saldo, código 05, etc.)",
                "schema": "diagnose_declined_transaction(user_id: str, error_code: Optional[str])"
            },
            {
                "name": "diagnose_terminal",
                "specialist": "HardwareSpecialist",
                "description": "Diagnóstico de conectividade Wi-Fi e chip 3G/4G do terminal",
                "schema": "diagnose_terminal(user_id: str, serial_number: Optional[str])"
            },
            {
                "name": "search_knowledge_base",
                "specialist": "KnowledgeSpecialist",
                "description": "RAG semântico ChromaDB (artigos Getnet)",
                "schema": "search_knowledge_base(query: str)"
            },
            {
                "name": "search_web",
                "specialist": "WebSearchSpecialist",
                "description": "Busca web em tempo real (DuckDuckGo) para clima e câmbio",
                "schema": "search_web(query: str)"
            },
            {
                "name": "escalate_to_human",
                "specialist": "HumanOversightSpecialist",
                "description": "Geração e persistência de ticket em SQLite (tickets.db)",
                "schema": "escalate_to_human(user_id: str, reason: str)"
            }
        ]
    }


@app.get("/tickets/{ticket_id}", tags=["Tickets"], dependencies=[Depends(verify_api_key)])
async def get_ticket_endpoint(ticket_id: str):
    """Retrieve details for a persisted support ticket by ticket ID."""
    from src.core.tickets_db import get_tickets_repository
    repo = get_tickets_repository()
    ticket = repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket com protocolo '{ticket_id}' não foi encontrado."
        )
    return ticket


@app.get("/tickets", tags=["Tickets"], dependencies=[Depends(verify_api_key)])
async def list_tickets_endpoint(limit: int = 50):
    """List recent persisted human escalation tickets from SQLite tickets.db."""
    from src.core.tickets_db import get_tickets_repository
    repo = get_tickets_repository()
    tickets = repo.list_tickets(limit=limit)
    return {"count": len(tickets), "tickets": tickets}


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"], dependencies=[Depends(verify_api_key)])
@app.post("/api/v1/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"], dependencies=[Depends(verify_api_key)])
def chat_endpoint(payload: ChatRequest):
    try:
        orchestrator = get_orchestrator()
        state = orchestrator.run_sync(
            user_id=payload.user_id,
            message=payload.message,
            session_id=payload.session_id
        )

        active_session = state.session_id or payload.session_id or payload.user_id

        metadata = AgentMetadata(
            agent_type="SupervisorAgent",
            routed_by="SupervisorAgent",
            decision_engine="rules_fallback",
            session_id=active_session,
            trace_id=state.trace_id or "",
            tools_used=state.tools_used,
            tool_calls=state.tool_calls,
            execution_time_ms=state.execution_time_ms,
            sources=state.sources,
            retrieved_docs=state.retrieved_docs,
            ticket=state.ticket,
            tokens=None,
            estimated_cost_usd=None,
            debug_details={
                "session_id": active_session,
                "trace_id": state.trace_id,
                "is_safe": state.is_safe,
                "safety_violations": state.safety_violations,
                "escalate_to_human": state.escalate_to_human,
                "ticket_id": state.escalation_ticket_id,
                "tools_used": state.tools_used,
                "decision_engine": "rules_fallback"
            }
        )

        return ChatResponse(
            response=state.agent_response or "Não foi possível processar sua solicitação no momento.",
            agent="SupervisorAgent",
            user_id=state.user_id,
            metadata=metadata,
        )

    except Exception as exc:
        logger.exception(f"Unhandled error processing message from user '{payload.user_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no processamento multi-agente: {str(exc)}"
        )
