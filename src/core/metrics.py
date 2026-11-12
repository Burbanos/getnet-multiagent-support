"""In-memory Prometheus metrics for Getnet Multi-Agent Support System.

Exposes metrics in Prometheus text exposition format (version 0.0.4)
without any external dependencies. Thread-safe via threading.Lock.
"""
from __future__ import annotations

import threading

# The known tools; any unrecognised tool name is recorded as "unknown"
KNOWN_TOOLS: frozenset[str] = frozenset({
    "ask_knowledge_agent",
    "ask_support_agent",
    "escalate_to_human",
    "search_knowledge_base",
    "get_weather_forecast",
    "get_exchange_rate",
    "search_web",
    "get_settlement_status",
    "diagnose_declined_transaction",
    "diagnose_terminal",
})

GUARDRAIL_DECISIONS: frozenset[str] = frozenset({
    "pattern_block",
    "classifier_block",
    "classifier_allow",
    "classifier_error_open",
    "classifier_error_closed",
    "classifier_invalid_block",
})

NOTIFICATION_STATUSES: frozenset[str] = frozenset({"sent", "failed", "disabled"})

# Cumulative histogram bucket thresholds
LATENCY_BUCKETS: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
LATENCY_BUCKET_STRS: tuple[str, ...] = ("0.5", "1.0", "2.0", "5.0", "10.0", "20.0", "30.0", "60.0", "+Inf")

_lock = threading.Lock()
_requests: dict[str, int] = {}
_latency_buckets: dict[str, int] = {b: 0 for b in LATENCY_BUCKET_STRS}
_latency_sum: float = 0.0
_latency_count: int = 0
_tool_calls: dict[tuple[str, str], int] = {}
_escalations_total: int = 0
_abstentions_total: int = 0
_tokens: dict[str, int] = {"input": 0, "output": 0}
_guardrail_decisions: dict[str, int] = {}
_notifications: dict[str, int] = {}


def reset() -> None:
    """Reset all in-memory counters and histogram buckets to zero."""
    global _latency_sum, _latency_count, _escalations_total, _abstentions_total
    with _lock:
        _requests.clear()
        _latency_buckets.clear()
        for b_str in LATENCY_BUCKET_STRS:
            _latency_buckets[b_str] = 0
        _latency_sum = 0.0
        _latency_count = 0
        _tool_calls.clear()
        _escalations_total = 0
        _abstentions_total = 0
        _tokens["input"] = 0
        _tokens["output"] = 0
        _guardrail_decisions.clear()
        _notifications.clear()


def inc_request(status_code: int | str, latency_s: float) -> None:
    """Increment the HTTP request counter and record request latency."""
    global _latency_sum, _latency_count
    st = str(status_code)
    lat = max(0.0, float(latency_s))
    with _lock:
        _requests[st] = _requests.get(st, 0) + 1
        _latency_count += 1
        _latency_sum += lat
        for b_val, b_str in zip(LATENCY_BUCKETS, LATENCY_BUCKET_STRS[:-1]):
            if lat <= b_val:
                _latency_buckets[b_str] = _latency_buckets.get(b_str, 0) + 1
        _latency_buckets["+Inf"] = _latency_buckets.get("+Inf", 0) + 1


def inc_tool(tool: str, status: str = "ok") -> None:
    """Increment the tool call counter for a known tool (or 'unknown')."""
    norm_tool = tool if tool in KNOWN_TOOLS else "unknown"
    norm_status = "error" if status == "error" else "ok"
    with _lock:
        key = (norm_tool, norm_status)
        _tool_calls[key] = _tool_calls.get(key, 0) + 1


def inc_escalation() -> None:
    """Increment the human escalation counter."""
    global _escalations_total
    with _lock:
        _escalations_total += 1


def inc_abstention() -> None:
    """Increment the knowledge abstention counter."""
    global _abstentions_total
    with _lock:
        _abstentions_total += 1


def inc_guardrail(decision: str) -> None:
    """Increment the guardrail decision counter."""
    norm = decision if decision in GUARDRAIL_DECISIONS else "unknown"
    with _lock:
        _guardrail_decisions[norm] = _guardrail_decisions.get(norm, 0) + 1


def inc_notification(status: str) -> None:
    """Increment the operator webhook notification counter."""
    norm = status if status in NOTIFICATION_STATUSES else "unknown"
    with _lock:
        _notifications[norm] = _notifications.get(norm, 0) + 1


def add_tokens(input_tokens: int | None, output_tokens: int | None) -> None:
    """Add LLM tokens to the direction counters (None counts as 0)."""
    inp = int(input_tokens or 0)
    out = int(output_tokens or 0)
    with _lock:
        _tokens["input"] += inp
        _tokens["output"] += out


def render() -> str:
    """Render all metrics in Prometheus text exposition format (version 0.0.4)."""
    with _lock:
        lines: list[str] = [
            "# HELP getnet_requests_total Total number of HTTP requests processed for chat endpoints.",
            "# TYPE getnet_requests_total counter",
        ]
        for st, count in sorted(_requests.items()):
            lines.append(f'getnet_requests_total{{status="{st}"}} {count}')

        lines.extend([
            "# HELP getnet_request_latency_seconds Request latency in seconds for chat endpoints.",
            "# TYPE getnet_request_latency_seconds histogram",
        ])
        for b_str in LATENCY_BUCKET_STRS:
            lines.append(f'getnet_request_latency_seconds_bucket{{le="{b_str}"}} {_latency_buckets.get(b_str, 0)}')
        sum_str = "0" if _latency_count == 0 else str(round(_latency_sum, 8))
        lines.append(f"getnet_request_latency_seconds_sum {sum_str}")
        lines.append(f"getnet_request_latency_seconds_count {_latency_count}")

        lines.extend([
            "# HELP getnet_tool_calls_total Total number of tool invocations.",
            "# TYPE getnet_tool_calls_total counter",
        ])
        for (tool, st), count in sorted(_tool_calls.items()):
            lines.append(f'getnet_tool_calls_total{{tool="{tool}",status="{st}"}} {count}')

        if _guardrail_decisions:
            lines.extend([
                "# HELP getnet_guardrail_decisions_total Total number of guardrail decisions.",
                "# TYPE getnet_guardrail_decisions_total counter",
            ])
            for dec, count in sorted(_guardrail_decisions.items()):
                lines.append(f'getnet_guardrail_decisions_total{{decision="{dec}"}} {count}')

        lines.extend([
            "# HELP getnet_operator_notifications_total Total number of operator webhook notifications.",
            "# TYPE getnet_operator_notifications_total counter",
        ])
        for st, count in sorted(_notifications.items()):
            lines.append(f'getnet_operator_notifications_total{{status="{st}"}} {count}')

        lines.extend([
            "# HELP getnet_escalations_total Total number of tickets escalated to human.",
            "# TYPE getnet_escalations_total counter",
            f"getnet_escalations_total {_escalations_total}",
            "# HELP getnet_abstentions_total Total number of turns where knowledge retrieval abstained.",
            "# TYPE getnet_abstentions_total counter",
            f"getnet_abstentions_total {_abstentions_total}",
            "# HELP getnet_llm_tokens_total Total number of LLM tokens processed.",
            "# TYPE getnet_llm_tokens_total counter",
            f'getnet_llm_tokens_total{{direction="input"}} {_tokens["input"]}',
            f'getnet_llm_tokens_total{{direction="output"}} {_tokens["output"]}',
        ])

        return "\n".join(lines) + "\n"
