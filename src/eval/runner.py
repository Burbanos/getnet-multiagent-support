"""Evaluation runner for real-model execution with resumption and quota guards."""
import json
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import src.core.tickets_db as tdb
from src.config import settings
from src.core.graph import OrchestrationGraph
from src.core.llm import LLMNotConfiguredError


def _get_val(state: Any, key: str, default: Any = None) -> Any:
    """Retrieve attribute or dictionary value."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def observe_turn(state: Any, message: str, latency_ms: float) -> dict[str, Any]:
    """
    Extract a normalized turn observation dictionary from an agent state or state dict.
    Truncates retrieved document texts to 600 characters and filters keys strictly.
    """
    raw_docs = _get_val(state, "retrieved_docs", []) or []
    cleaned_docs: list[dict[str, Any]] = []
    for d in raw_docs:
        if isinstance(d, dict):
            cleaned_docs.append({
                "url": d.get("url", ""),
                "chunk_id": d.get("chunk_id", ""),
                "score": d.get("score", 0.0),
                "text": (d.get("text") or "")[:600],
            })

    ticket_obj = _get_val(state, "ticket")
    ticket_dict = ticket_obj if isinstance(ticket_obj, dict) else {}
    ticket_id = _get_val(state, "escalation_ticket_id") or ticket_dict.get("ticket_id")
    ticket_priority = ticket_dict.get("priority")

    resp = (
        _get_val(state, "agent_response")
        or _get_val(state, "final_response")
        or _get_val(state, "response")
        or ""
    )

    return {
        "message": message,
        "response": resp,
        "agents_used": _get_val(state, "agents_used", []) or [],
        "tools_used": _get_val(state, "tools_used", []) or [],
        "sources": _get_val(state, "sources", []) or [],
        "retrieved_docs": cleaned_docs,
        "tool_results": _get_val(state, "tool_results", []) or [],
        "ticket_id": ticket_id,
        "ticket_priority": ticket_priority,
        "is_safe": _get_val(state, "is_safe", True),
        "handoff": _get_val(state, "handoff"),
        "llm_model": _get_val(state, "llm_model"),
        "tokens": _get_val(state, "tokens"),
        "latency_ms": latency_ms,
    }


def run_case(case: dict[str, Any], orchestrator: Any, run_id: str) -> dict[str, Any]:
    """
    Execute all turns of a single test case within the same session.
    Reraises LLMNotConfiguredError; wraps any other error into status: error without message leaks.
    """
    cid = case["id"]
    user_id = "cliente1988"
    session_id = f"eval-{run_id}-{cid}"
    turns: list[dict[str, Any]] = []

    for msg in case.get("turns", []):
        t0 = time.perf_counter()
        try:
            state = orchestrator.run_sync(
                user_id=user_id,
                message=msg,
                session_id=session_id,
            )
            lat_ms = round((time.perf_counter() - t0) * 1000, 1)
            turns.append(observe_turn(state, msg, lat_ms))
        except LLMNotConfiguredError:
            raise
        except Exception as exc:  # noqa: BLE001
            return {
                "id": cid,
                "status": "error",
                "error_type": type(exc).__name__,
                "turns": turns,
            }

    return {
        "id": cid,
        "status": "ok",
        "error_type": None,
        "turns": turns,
    }


def load_results(path: str | Path) -> dict[str, dict[str, Any]]:
    """
    Load evaluation results from JSONL file into a dict indexed by case ID.
    If multiple lines exist for the same ID, the last one wins.
    """
    p = Path(path)
    if not p.exists():
        return {}

    results: dict[str, dict[str, Any]] = {}
    content = p.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            cid = row.get("id")
            if cid:
                results[cid] = row
        except json.JSONDecodeError:
            continue
    return results


def run_eval(
    cases: list[dict[str, Any]],
    results_path: str | Path,
    run_id: str,
    orchestrator_factory: Callable[[], Any] | None = None,
    sleep_s: float | None = None,
    max_cases: int | None = None,
    only: list[str] | set[str] | None = None,
    max_consecutive_errors: int = 3,
) -> dict[str, Any]:
    """
    Execute evaluation over cases with resumption, isolated tickets DB, and quota exhaustion guards.
    """
    p = Path(results_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    delay = sleep_s if sleep_s is not None else settings.EVAL_SLEEP_S
    only_set = set(only) if only is not None else None

    existing = load_results(p)
    factory = orchestrator_factory or OrchestrationGraph
    orchestrator = factory()

    orig_tickets_path = settings.TICKETS_DB_PATH
    tmp_dir = tempfile.mkdtemp(prefix="eval_tickets_")
    tmp_tickets_path = str(Path(tmp_dir) / "tickets.db")
    settings.TICKETS_DB_PATH = tmp_tickets_path
    tdb.reset_tickets_repository()

    attempted = 0
    ok = 0
    errors = 0
    skipped = 0
    stopped_early = False
    consecutive_unavailable_errors = 0

    try:
        with open(p, "a", encoding="utf-8") as f:
            for case in cases:
                cid = case["id"]
                if only_set is not None and cid not in only_set:
                    continue

                if existing.get(cid, {}).get("status") == "ok":
                    skipped += 1
                    continue

                if max_cases is not None and attempted >= max_cases:
                    break

                res = run_case(case, orchestrator, run_id)
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
                f.flush()

                attempted += 1
                if res.get("status") == "ok":
                    ok += 1
                    consecutive_unavailable_errors = 0
                else:
                    errors += 1
                    if res.get("error_type") == "LLMUnavailableError":
                        consecutive_unavailable_errors += 1
                        if consecutive_unavailable_errors >= max_consecutive_errors:
                            stopped_early = True
                            break
                    else:
                        consecutive_unavailable_errors = 0

                if delay and delay > 0:
                    time.sleep(delay)
    finally:
        settings.TICKETS_DB_PATH = orig_tickets_path
        tdb.reset_tickets_repository()

    return {
        "attempted": attempted,
        "ok": ok,
        "errors": errors,
        "skipped": skipped,
        "stopped_early": stopped_early,
    }
