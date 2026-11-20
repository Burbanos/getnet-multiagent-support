"""Distributed OpenTelemetry tracing with strict attribute allowlist and no PII leakage."""
from __future__ import annotations

import socket
import threading
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import contextmanager, suppress
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.config import settings

ALLOWED_ATTRIBUTES: frozenset[str] = frozenset({
    "app.trace_id",
    "user.hash",
    "service.replica",
    "http.route",
    "http.status_code",
    "graph.node",
    "llm.caller",
    "llm.model",
    "llm.input_tokens",
    "llm.output_tokens",
    "llm.fallback_used",
    "llm.status",
    "tool.name",
    "tool.status",
    "agent.name",
    "ticket.id",
    "ticket.status",
    "ticket.priority",
    "guardrail.decision",
    "answer_check.status",
    "notification.status",
    "rate_limit.backend",
    "coverage.status",
})

_PROPAGATOR = TraceContextTextMapPropagator()
_lock = threading.Lock()
_provider: TracerProvider | None = None
_tracer: Any = None


def _filter_attributes(attrs: Mapping[str, Any] | None) -> dict[str, str | int | float | bool]:
    if not attrs:
        return {}
    out: dict[str, str | int | float | bool] = {}
    for k, v in attrs.items():
        if k in ALLOWED_ATTRIBUTES and v is not None and isinstance(v, (str, int, float, bool)):
            out[k] = v
    return out


def configure_tracing(exporter: SpanExporter | None = None, *, simple: bool = False) -> TracerProvider:
    """Create and activate the module's own TracerProvider (never mutates global trace provider)."""
    global _provider, _tracer
    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.instance.id": settings.REPLICA_NAME or socket.gethostname(),
        "deployment.environment": settings.APP_ENV,
    })
    provider = TracerProvider(resource=resource)

    active_exporter = exporter
    if active_exporter is None:
        kind = settings.TRACING_EXPORTER
        if kind == "console":
            active_exporter = ConsoleSpanExporter()
        elif kind == "otlp":
            endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.strip().rstrip("/")
            if endpoint:
                active_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
            else:
                active_exporter = OTLPSpanExporter()

    if active_exporter is not None:
        processor = SimpleSpanProcessor(active_exporter) if simple else BatchSpanProcessor(active_exporter)
        provider.add_span_processor(processor)

    with _lock:
        old_provider = _provider
        _provider = provider
        _tracer = provider.get_tracer("getnet.multiagent")
    if old_provider is not None:
        with suppress(Exception):
            old_provider.shutdown()
    return provider


def ensure_tracing() -> TracerProvider:
    """Ensure a module TracerProvider exists without overwriting an already configured one."""
    with _lock:
        if _provider is not None:
            return _provider
    return configure_tracing()


def shutdown_tracing() -> None:
    """Flush and shut down the active TracerProvider, resetting module tracing state."""
    global _provider, _tracer
    with _lock:
        old_provider = _provider
        _provider = None
        _tracer = None
    if old_provider is not None:
        with suppress(Exception):
            old_provider.shutdown()


@contextmanager
def span(
    name: str,
    attributes: Mapping[str, Any] | None = None,
    context: Any = None,
) -> Iterator[Any]:
    """Open an allowlist-filtered span; marks ERROR with exception class name only."""
    provider = ensure_tracing()
    with _lock:
        tracer = _tracer if _tracer is not None else provider.get_tracer("getnet.multiagent")

    filtered = _filter_attributes(attributes)
    with tracer.start_as_current_span(
        name,
        context=context,
        attributes=filtered,
        record_exception=False,
        set_status_on_exception=False,
    ) as active_span:
        try:
            yield active_span
        except BaseException as exc:
            active_span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise


def set_attributes(attrs: Mapping[str, Any]) -> None:
    """Set allowlist-filtered attributes on the currently active span, if valid."""
    current = trace.get_current_span()
    if current is None:
        return
    ctx = current.get_span_context()
    if ctx is None or not ctx.is_valid:
        return
    filtered = _filter_attributes(attrs)
    if filtered:
        current.set_attributes(filtered)


def extract_context(headers: Mapping[str, str] | None) -> Any:
    """Extract W3C traceparent context from incoming HTTP headers."""
    if not headers:
        return None
    carrier = {str(k).lower(): str(v) for k, v in headers.items()}
    return _PROPAGATOR.extract(carrier)


def inject_traceparent(headers: MutableMapping[str, str]) -> None:
    """Inject W3C traceparent header from the currently active span into outgoing headers."""
    _PROPAGATOR.inject(headers)


def current_trace_id() -> str | None:
    """Return the active span's 32-hex trace_id, or None when no valid span is active."""
    current = trace.get_current_span()
    if current is None:
        return None
    ctx = current.get_span_context()
    if ctx is None or not ctx.is_valid:
        return None
    return format(ctx.trace_id, "032x")
