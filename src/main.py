"""FastAPI HTTP service exposing the Multi-Agent Support System API."""
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi import Path as FastAPIPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import logger, settings
from src.core import metrics
from src.core.auth import Principal, auth_mode, authenticate, validate_auth_config
from src.core.graph import KNOWLEDGE_TOOLS, SUPPORT_TOOLS, get_orchestrator
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    LLMUnavailableError,
)
from src.core.log_context import bind, exc_brief
from src.core.tickets_db import TicketTransitionError, get_tickets_repository
from src.tools.supervisor_tools import SUPERVISOR_TOOLS


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
    handoff: dict[str, Any] | None = Field(default=None, description="Human escalation handoff status")
    guardrail: dict[str, Any] | None = Field(default=None, description="Guardrail layers and classifier verdict (no message text)")
    llm_model: str | None = Field(default=None, description="Model identifier that produced the final response")
    tokens: dict[str, int] | None = Field(default=None, description="Token usage estimation")
    tokens_by_agent: dict[str, dict[str, int]] | None = Field(default=None, description="Token usage broken down by agent")
    estimated_cost_usd: float | None = Field(default=None, description="Estimated execution cost in USD")
    web_results: list[dict[str, Any]] = Field(default_factory=list, description="Web search results if search_web was used")
    api_results: list[dict[str, Any]] = Field(default_factory=list, description="Results of the weather and exchange-rate APIs used in the turn")
    error: str | None = Field(default=None, description="Internal error flag if execution failed")
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


class TicketUpdate(BaseModel):
    """Payload for operator updating ticket status and reply."""
    status: str | None = Field(default=None, description="New ticket status (in_progress, answered, closed)")
    reply: str | None = Field(default=None, min_length=1, max_length=4000, description="Operator response message")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_config()
    get_orchestrator()
    get_tickets_repository()
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


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/chat", "/api/v1/chat"):
        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            latency_s = time.perf_counter() - start_time
            metrics.inc_request(status_code, latency_s)
    return await call_next(request)


STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["General"])
async def root():
    return {
        "service": "Getnet Multi-Agent Support System",
        "version": "2.0.0",
        "architecture": "Supervisor ReAct with Tool Calling & SqliteSaver (thread user_id:session_id)",
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "chat_endpoint": "/chat",
        "interactive_demo": "/demo",
        "tickets_endpoint": "/tickets",
        "metrics_endpoint": "/metrics",
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


@app.get("/metrics", tags=["Observability"])
def metrics_endpoint() -> Response:
    return Response(
        content=metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/agents", tags=["Architecture"])
async def list_agents():
    all_tools = [*SUPERVISOR_TOOLS, *KNOWLEDGE_TOOLS, *SUPPORT_TOOLS]
    return {
        "architecture": "LangGraph supervisor with specialist sub-agents",
        "checkpointer": "SqliteSaver (thread user_id:session_id)",
        "models": {
            "primary": settings.LLM_MODEL,
            "fallback": settings.LLM_FALLBACK_MODEL or None,
        },
        "agents": [
            {
                "name": "GuardrailAgent",
                "runs_before": "supervisor",
                "uses_llm": settings.GUARDRAIL_CLASSIFIER_ENABLED,
                "tools": [],
                "classifier": {
                    "enabled": settings.GUARDRAIL_CLASSIFIER_ENABLED,
                    "model": settings.GUARDRAIL_CLASSIFIER_MODEL or settings.LLM_MODEL,
                    "prompt": "src/prompts/guardrail_classifier.md",
                    "fail_mode": settings.GUARDRAIL_CLASSIFIER_FAIL_MODE,
                    "structured_output": "GuardrailVerdict",
                },
            },
            {
                "name": "SupervisorAgent",
                "prompt": "src/prompts/supervisor.md",
                "tools": [t.name for t in SUPERVISOR_TOOLS],
            },
            {
                "name": "KnowledgeAgent",
                "prompt": "src/prompts/knowledge_agent.md",
                "tools": [t.name for t in KNOWLEDGE_TOOLS],
            },
            {
                "name": "SupportAgent",
                "prompt": "src/prompts/support_agent.md",
                "tools": [t.name for t in SUPPORT_TOOLS],
            },
        ],
        "tools": [
            {
                "name": t.name,
                "description": (t.description or "").strip().splitlines()[0],
                "args": sorted(t.args),
            }
            for t in all_tools
        ],
    }


@app.patch("/tickets/{ticket_id}", tags=["Tickets"])
def patch_ticket_endpoint(
    ticket_id: str,
    payload: TicketUpdate,
    principal: Annotated[Principal, Depends(authenticate)],
):
    """Update ticket status or record operator reply. Operator role only."""
    if principal.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only operators can update tickets.",
        )

    if payload.status is None and payload.reply is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Either status or reply must be provided.",
        )

    try:
        repo = get_tickets_repository()
        updated = repo.update_ticket(
            ticket_id,
            status=payload.status,
            reply=payload.reply,
            operator_id=principal.user_id,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket com protocolo '{ticket_id}' não foi encontrado.",
            )
    except TicketTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    resume_res: dict[str, Any] | None = None
    if payload.reply is not None:
        try:
            resume_res = get_orchestrator().resume_after_operator(ticket_id)
        except Exception as exc:  # noqa: BLE001
            err_cls = type(exc).__name__
            logger.error(f"Operator resume failed cleanly in PATCH /tickets: {exc_brief(exc)}")
            resume_res = {"status": "failed", "error_type": err_cls}
        updated = repo.get_ticket(ticket_id) or updated

    return {**updated, "resume": resume_res}


@app.get("/tickets/{ticket_id}", tags=["Tickets"])
async def get_ticket_endpoint(
    ticket_id: str,
    principal: Annotated[Principal, Depends(authenticate)],
):
    """Retrieve details for a persisted support ticket by ticket ID."""
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
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: int = 50,
    principal: Annotated[Principal, Depends(authenticate)] = None,  # type: ignore[assignment]
):
    """List recent persisted human escalation tickets."""
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
    tickets = repo.list_tickets(user_id=filter_user, status=status_filter, limit=limit)
    return {"count": len(tickets), "tickets": tickets}


@app.get("/sessions/{session_id}/messages", tags=["Chat"])
def get_session_messages_endpoint(
    session_id: Annotated[str, FastAPIPath(..., min_length=1, max_length=64)],
    principal: Annotated[Principal, Depends(authenticate)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """Return customer and final assistant messages for the authenticated customer's session."""
    if principal.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can inspect session messages.",
        )
    msgs = get_orchestrator().session_messages(principal.user_id, session_id, limit=limit)
    return {"session_id": session_id, "messages": msgs}


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
    with bind(trace_id, active_session, principal.user_id):
        try:
            orchestrator = get_orchestrator()
            state = orchestrator.run_sync(
                user_id=principal.user_id,
                message=payload.message,
                session_id=active_session,
                trace_id=trace_id,
            )

            handoff_data = getattr(state, "handoff", None)
            handoff_status = (handoff_data or {}).get("status")
            agent_type = "HumanHandoff" if handoff_status in ("pending", "delivered") else "SupervisorAgent"

            metadata = AgentMetadata(
                agent=agent_type,
                agent_type=agent_type,
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
                handoff=handoff_data,
                guardrail=getattr(state, "guardrail", None),
                tokens=getattr(state, "tokens", None),
                tokens_by_agent=getattr(state, "tokens_by_agent", None),
                estimated_cost_usd=getattr(state, "estimated_cost_usd", None),
                web_results=getattr(state, "web_results", []) or [],
                api_results=getattr(state, "api_results", []) or [],
                error=getattr(state, "error", None),
                debug_details={
                    "session_id": state.session_id or active_session,
                    "trace_id": trace_id,
                    "is_safe": state.is_safe,
                    "safety_violations": state.safety_violations,
                    "escalate_to_human": state.escalate_to_human,
                    "ticket_id": state.escalation_ticket_id,
                    "tools_used": state.tools_used,
                    "handoff": handoff_data,
                },
            )

            return ChatResponse(
                response=state.agent_response or "Não foi possível processar sua solicitação no momento.",
                agent=agent_type,
                user_id=principal.user_id,
                metadata=metadata,
            )

        except LLMConfigurationError as exc:
            logger.error(f"LLM misconfigured: {type(exc).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM misconfigured: check LLM_PROVIDER, LLM_MODEL and the provider API key.",
                headers={"X-Trace-Id": trace_id},
            ) from exc
        except LLMNotConfiguredError as exc:
            logger.error(f"LLM not configured: {type(exc).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM not configured: set GEMINI_API_KEY.",
                headers={"X-Trace-Id": trace_id},
            ) from exc
        except LLMUnavailableError as exc:
            logger.error(f"LLM provider unavailable: {type(exc).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider unavailable, please retry.",
                headers={"X-Trace-Id": trace_id},
            ) from exc
        except Exception as exc:
            logger.error(f"Unhandled error processing message: {exc_brief(exc)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error. Reference: {trace_id}",
                headers={"X-Trace-Id": trace_id},
            ) from exc
