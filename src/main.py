"""FastAPI HTTP service exposing the Multi-Agent Support System API."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import settings, logger
from src.core.graph import get_orchestrator
from src.agents.knowledge import get_retriever


class ChatRequest(BaseModel):
    """Chat request payload containing user identifier and message."""
    message: str = Field(..., description="Message payload to be evaluated by the multi-agent graph", min_length=1)
    user_id: str = Field(..., description="Unique merchant or customer identifier", min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "What's the difference between the Get Clássica and the Get Smart?",
                "user_id": "cliente1988"
            }
        }
    }


class AgentMetadata(BaseModel):
    """Telemetry and trace metadata for graph execution."""
    agent_type: str = Field(..., description="Final agent that synthesized the response")
    routed_by: str = Field(default="RouterAgent", description="Routing decision agent")
    tools_used: List[str] = Field(default_factory=list, description="Tools invoked during pipeline execution")
    execution_time_ms: float = Field(..., description="Total execution latency in milliseconds")
    confidence: float = Field(default=1.0, description="Routing confidence score")
    sources: List[str] = Field(default_factory=list, description="Referenced URLs or knowledge base documents")
    debug_details: Optional[Dict[str, Any]] = Field(default=None, description="Diagnostic payload")


class ChatResponse(BaseModel):
    """Chat response payload."""
    response: str = Field(..., description="Synthesized agent response")
    agent: str = Field(..., description="Identifier of the executing agent")
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
    logger.info("Initializing multi-agent graph and knowledge retriever...")
    retriever = get_retriever()
    logger.info(f"Retriever initialized with {len(retriever.documents)} documents.")
    get_orchestrator()
    yield
    logger.info("Shutting down multi-agent service.")


app = FastAPI(
    title="Getnet Multi-Agent Support System API",
    description="Multi-agent support system for Getnet merchants with RAG, operational tools, and safety guardrails.",
    version="1.0.0",
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
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "chat_endpoint": "/chat",
        "interactive_demo": "/demo"
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
        version="1.0.0",
        environment=settings.APP_ENV,
        llm_provider=settings.LLM_PROVIDER,
        guardrails_enabled=settings.ENABLE_GUARDRAILS,
    )


@app.get("/agents", tags=["Architecture"])
async def list_agents():
    return {
        "architecture": "Hierarchical Multi-Agent Graph",
        "agents": [
            {
                "name": "GuardrailAgent",
                "role": "Input sanitization and injection detection",
                "tools": ["regex_safety_evaluator"]
            },
            {
                "name": "RouterAgent",
                "role": "Semantic intent classification and agent dispatching",
                "tools": ["intent_classifier"]
            },
            {
                "name": "KnowledgeAgent",
                "role": "Knowledge retrieval via ChromaDB and real-time web search",
                "tools": ["knowledge_retriever", "chromadb_vector_search", "web_search_tool"]
            },
            {
                "name": "CustomerSupportAgent",
                "role": "Account settlements, terminal connectivity, and transaction declines",
                "tools": [
                    "get_settlement_and_sales_status",
                    "diagnose_terminal_connectivity",
                    "get_declined_transaction_details"
                ]
            },
            {
                "name": "HumanEscalationAgent",
                "role": "Support ticket creation and operator escalation",
                "tools": ["create_escalation_ticket"]
            }
        ]
    }


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"])
@app.post("/api/v1/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK, tags=["Chat"])
async def chat_endpoint(payload: ChatRequest):
    try:
        orchestrator = get_orchestrator()
        state = await orchestrator.run(user_id=payload.user_id, message=payload.message)

        metadata = AgentMetadata(
            agent_type=state.final_agent.value if state.final_agent else "Unknown",
            routed_by=state.route.target_agent.value if state.route else "GuardrailAgent",
            tools_used=state.tools_used,
            execution_time_ms=state.execution_time_ms,
            confidence=state.route.confidence if state.route else 1.0,
            sources=state.sources,
            debug_details={
                "intent": state.route.intent if state.route else None,
                "is_safe": state.is_safe,
                "escalate_to_human": state.escalate_to_human,
                "ticket_id": state.escalation_ticket_id,
            }
        )

        return ChatResponse(
            response=state.agent_response or "Não foi possível processar sua solicitação no momento.",
            agent=state.final_agent.value if state.final_agent else "MultiAgentSystem",
            user_id=state.user_id,
            metadata=metadata,
        )

    except Exception as exc:
        logger.exception(f"Unhandled error processing message from user '{payload.user_id}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no processamento multi-agente: {str(exc)}"
        )
