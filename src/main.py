"""FastAPI HTTP service exposing the Multi-Agent Support System API."""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import logger, settings
from src.core.auth import Principal, auth_mode, authenticate, validate_auth_config
from src.core.graph import get_orchestrator
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    LLMUnavailableError,
)


class ChatRequest(BaseModel):
    """Chat request payload containing message and optional session ID."""
    message: str = Field(..., description="Message payload to be evaluated by the multi-agent graph", min_length=1)
    user_id: str | None = Field(default=None, description="Optional merchant or customer identifier to verify against credential")
    session_id: str | None = Field(default=None, description="Conversational thread/session ID for persistent multi-turn memory", min_length=1, max_length=64)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Qual a diferença entre a Get Clássica e a Get Smart?",
                "session_id": "sess-user-001",
            },
        },
    }


class AgentMetadata(BaseModel):
    """Telemetry and trace metadata for graph execution."""
    agent_type: str = Field(default="SupervisorAgent", description="Final agent that synthesized the response")
    routed_by: str = Field(default="SupervisorAgent", description="Supervisor ReAct orchestration engine")
    session_id: str = Field(default="", description="Conversational session ID")
    trace_id: str = Field(default="", description="Unique UUID trace identifier for observability")
    agents_used: list[str] = Field(default_factory=lambda: ["SupervisorAgent"], description="Specialist agents invoked during execution")
    tools_used: list[str] = Field(default_factory=list, description="Tools invoked during pipeline execution")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, description="Structured ReAct tool invocations")
    execution_time_ms: float = Field(..., description="Total execution latency in milliseconds")
    sources: list[str] = Field(default_factory=list, description="Referenced URLs or knowledge base documents")
    retrieved_docs: list[dict[str, Any]] = Field(default_factory=list, description="Vector retrieval results with cosine similarity")
    ticket: dict[str, Any] | None = Field(default=None, description="Persisted support ticket if escalation occurred")
    llm_model: str | None = Field(default=None, description="Model identifier that produced the final response")
    tokens: dict[str, int] | None = Field(default=None, description="Token usage estimation")
    tokens_by_agent: dict[str, dict[str, int]] | None = Field(default=None, description="Token usage broken down by agent")
    estimated_cost_usd: float | None = Field(default=None, description="Estimated execution cost in USD")
    debug_details: dict[str, Any] | None = Field(default=None, description="Diagnostic payload")


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
    llm_configured: bool
    guardrails_enabled: bool
    auth_mode: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_config()
    get_orchestrator()
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
        "architecture": f"Supervisor ReAct with Tool Calling & SqliteSaver ({settings.CHECKPOINT_DB_PATH}, thread user_id:session_id)",
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "chat_endpoint": "/chat",
        "interactive_demo": "/demo",
        "tickets_endpoint": "/tickets",
    }


@app.get("/demo", response_class=FileResponse, tags=["Demo"])
@app.get("/ui", response_class=FileResponse, tags=["Demo"])
async def demo_ui():
    demo_file = STATIC_DIR / "demo.html"
    if demo_file.exists():
        return FileResponse(str(demo_file))
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Arquivo de interface interativa (demo.html) não encontrado.",
    )


@app.get("/health", response_model=HealthResponse, tags=["Observability"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        environment=settings.APP_ENV,
        llm_configured=bool(settings.GEMINI_API_KEY),
        guardrails_enabled=settings.ENABLE_GUARDRAILS,
        auth_mode=auth_mode(),
    )


@app.get("/agents", tags=["Architecture"])
async def list_agents():
    return {
        "architecture": "LangGraph Supervisor Workflow",
        "orchestrator": {
            "name": "SupervisorAgent",
            "model_reference": "Google Gemini Flash (Function Calling)",
            "checkpointer": f"SqliteSaver at {settings.CHECKPOINT_DB_PATH} (thread user_id:session_id)",
            "safety": "GuardrailAgent (PII sanitization & prompt injection defense)",
        },
        "agents": [
            {
                "name": "SupervisorAgent",
                "role": "LangGraph Supervisor Orchestrator with Function Calling",
                "tools": [
                    "get_settlement_status",
                    "diagnose_declined_transaction",
                    "diagnose_terminal",
                    "search_knowledge_base",
                    "search_web",
                    "escalate_to_human",
                ],
            },
            {
                "name": "GuardrailAgent",
                "role": "PII Masking & Safety Guardrail",
                "tools": ["sanitize_pii", "regex_safety_evaluator"],
            },
        ],
        "tools": [
            {
                "name": "get_settlement_status",
                "specialist": "CustomerSupportSpecialist",
                "description": "Consulta liquidação financeira e previsão de depósito D+1",
                "schema": "get_settlement_status()",
            },
            {
                "name": "diagnose_declined_transaction",
                "specialist": "CustomerSupportSpecialist",
                "description": "Diagnostica recusas de cartão (código 51 saldo, código 05, etc.)",
                "schema": "diagnose_declined_transaction(error_code: Optional[str])",
            },
            {
                "name": "diagnose_terminal",
                "specialist": "HardwareSpecialist",
                "description": "Diagnóstico de conectividade Wi-Fi e chip 3G/4G do terminal",
                "schema": "diagnose_terminal(serial_number: Optional[str])",
            },
            {
                "name": "search_knowledge_base",
                "specialist": "KnowledgeSpecialist",
                "description": "RAG vetorial semântico (páginas oficiais Getnet)",
                "schema": "search_knowledge_base(query: str)",
            },
            {
                "name": "search_web",
                "specialist": "WebSearchSpecialist",
                "description": "Busca web em tempo real (DuckDuckGo) para clima e câmbio",
                "schema": "search_web(query: str)",
            },
            {
                "name": "escalate_to_human",
                "specialist": "HumanOversightSpecialist",
                "description": "Geração e persistência de ticket em SQLite (tickets.db)",
                "schema": "escalate_to_human(reason: str)",
            },
        ],
    }


@app.get("/tickets/{ticket_id}", tags=["Tickets"])
async def get_ticket_endpoint(
    ticket_id: str,
    principal: Annotated[Principal, Depends(authenticate)],
):
    """Retrieve details for a persisted support ticket by ticket ID."""
    from src.core.tickets_db import get_tickets_repository
    repo = get_tickets_repository()
    ticket = repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket com protocolo '{ticket_id}' não foi encontrado.",
        )
    if principal.role == "customer" and ticket["user_id"] != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket com protocolo '{ticket_id}' não foi encontrado.",
        )
    return ticket


@app.get("/tickets", tags=["Tickets"])
async def list_tickets_endpoint(
    user_id: str | None = None,
    limit: int = 50,
    principal: Annotated[Principal, Depends(authenticate)] = None,  # type: ignore[assignment]
):
    """List recent persisted human escalation tickets from SQLite tickets.db."""
    from src.core.tickets_db import get_tickets_repository
    if principal.role == "customer":
        if user_id is not None and user_id != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied.",
            )
        filter_user = principal.user_id
    else:
        filter_user = user_id

    repo = get_tickets_repository()
    tickets = repo.list_tickets(user_id=filter_user, limit=limit)
    return {"count": len(tickets), "tickets": tickets}


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"])
@app.post("/api/v1/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"])
def chat_endpoint(
    payload: ChatRequest,
    response: Response,
    principal: Annotated[Principal, Depends(authenticate)],
):
    trace_id = f"trc-{uuid.uuid4().hex[:12]}"
    response.headers["X-Trace-Id"] = trace_id

    if payload.user_id is not None and payload.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id does not match the authenticated credential.",
        )

    active_session = payload.session_id or uuid.uuid4().hex
    try:
        orchestrator = get_orchestrator()
        state = orchestrator.run_sync(
            user_id=principal.user_id,
            message=payload.message,
            session_id=active_session,
            trace_id=trace_id,
        )

        metadata = AgentMetadata(
            agent_type="SupervisorAgent",
            routed_by="SupervisorAgent",
            session_id=state.session_id or active_session,
            trace_id=trace_id,
            llm_model=getattr(state, "llm_model", None),
            agents_used=getattr(state, "agents_used", ["SupervisorAgent"]),
            tools_used=state.tools_used,
            tool_calls=state.tool_calls,
            execution_time_ms=state.execution_time_ms,
            sources=state.sources,
            retrieved_docs=state.retrieved_docs,
            ticket=state.ticket,
            tokens=getattr(state, "tokens", None),
            tokens_by_agent=getattr(state, "tokens_by_agent", None),
            estimated_cost_usd=getattr(state, "estimated_cost_usd", None),
            debug_details={
                "session_id": state.session_id or active_session,
                "trace_id": trace_id,
                "is_safe": state.is_safe,
                "safety_violations": state.safety_violations,
                "escalate_to_human": state.escalate_to_human,
                "ticket_id": state.escalation_ticket_id,
                "tools_used": state.tools_used,
            },
        )

        return ChatResponse(
            response=state.agent_response or "Não foi possível processar sua solicitação no momento.",
            agent="SupervisorAgent",
            user_id=principal.user_id,
            metadata=metadata,
        )

    except LLMConfigurationError as exc:
        logger.exception(f"LLM misconfigured [trace_id={trace_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM misconfigured: check LLM_PROVIDER, LLM_MODEL and the provider API key.",
            headers={"X-Trace-Id": trace_id},
        ) from exc
    except LLMNotConfiguredError as exc:
        logger.exception(f"LLM not configured [trace_id={trace_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM not configured: set GEMINI_API_KEY.",
            headers={"X-Trace-Id": trace_id},
        ) from exc
    except LLMUnavailableError as exc:
        logger.exception(f"LLM provider unavailable [trace_id={trace_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider unavailable, please retry.",
            headers={"X-Trace-Id": trace_id},
        ) from exc
    except Exception as exc:
        logger.exception(f"Unhandled error processing message from user '{principal.user_id}' [trace_id={trace_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error. Reference: {trace_id}",
            headers={"X-Trace-Id": trace_id},
        ) from exc
