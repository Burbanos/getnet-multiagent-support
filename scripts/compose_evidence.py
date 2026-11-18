"""Live Docker Compose multi-replica & observability evidence runner (Codespaces / CI helper)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

TEST_CARD_SPACED = "4111 1111 1111 1111"
TEST_CARD_DIGITS = "4111111111111111"
TEST_CPF_FORMATTED = "529.982.247-25"
TEST_CPF_DIGITS = "52998224725"
_BYTEA_HEX_RE = re.compile(r"\\\\x([0-9a-fA-F]+)")


def scan_pii(text: str) -> dict[str, int]:
    """Count occurrences of the synthetic test card and CPF literals in text."""
    return {
        "card_spaced": text.count(TEST_CARD_SPACED),
        "card_digits": text.count(TEST_CARD_DIGITS),
        "cpf_formatted": text.count(TEST_CPF_FORMATTED),
        "cpf_digits": text.count(TEST_CPF_DIGITS),
    }


def scan_dump(dump_text: str, marker: str) -> dict[str, Any]:
    """Scan pg_dump COPY text and decoded \\\\x hex bytea blobs for PII and marker."""
    totals = {k: 0 for k in ("card_spaced", "card_digits", "cpf_formatted", "cpf_digits")}
    marker_count = 0
    bytea_values = 0

    def _collect(chunk: str) -> None:
        nonlocal marker_count
        for key, count in scan_pii(chunk).items():
            totals[key] += count
        if marker:
            marker_count += chunk.count(marker)

    def _replace_bytea(match: re.Match[str]) -> str:
        nonlocal bytea_values
        bytea_values += 1
        hex_str = match.group(1)
        if len(hex_str) % 2 == 1:
            hex_str = hex_str[:-1]
        decoded = bytes.fromhex(hex_str).decode("utf-8", errors="replace")
        _collect(decoded)
        return " "

    plain_text = _BYTEA_HEX_RE.sub(_replace_bytea, dump_text)
    _collect(plain_text)
    return {
        "pii": totals,
        "marker": marker_count,
        "bytea_values": bytea_values,
    }


def make_api_keys() -> tuple[dict[str, str], str]:
    """Generate five distinct scenario API keys and build their SHA-256 API_KEYS specification."""
    specs = (
        ("conversation", "cliente1988", "customer"),
        ("ticket", "cliente1988", "customer"),
        ("pii", "cliente1988", "customer"),
        ("rate_limit", "cliente_rl", "customer"),
        ("operator", "operador_evidencia", "operator"),
    )
    keys: dict[str, str] = {}
    entries: list[str] = []
    for scenario, user_id, role in specs:
        raw_key = secrets.token_hex(16)
        keys[scenario] = raw_key
        digest = hashlib.sha256(raw_key.encode()).hexdigest()
        entries.append(f"{digest}:{user_id}:{role}")
    return keys, ";".join(entries)


def render_env(pg_password: str, api_keys_spec: str) -> str:
    """Render the temporary Compose .env file without persisting GEMINI_API_KEY to disk."""
    return (
        "\n".join([
            f"POSTGRES_PASSWORD={pg_password}",
            f"API_KEYS={api_keys_spec}",
            "RATE_LIMIT_PER_MINUTE=6",
            "TRACING_EXPORTER=otlp",
        ])
        + "\n"
    )


def ticket_checks(
    patch_status: int,
    patch_body: dict[str, Any],
    messages_after_patch: list[dict[str, Any]],
    audit_actions: list[str],
) -> dict[str, bool]:
    """Evaluate cross-replica ticket update and immediate operator delivery on PATCH."""
    across = patch_status == 200 and isinstance(patch_body, dict) and patch_body.get("status") == "answered"
    resume = patch_body.get("resume") if isinstance(patch_body, dict) else None
    resume_ok = isinstance(resume, dict) and resume.get("status") == "resumed"
    delivered_audit = "ticket_reply_delivered" in (audit_actions or [])
    assistant_msgs = sum(
        1 for msg in (messages_after_patch or []) if isinstance(msg, dict) and msg.get("role") == "assistant"
    )
    delivered = across and resume_ok and delivered_audit and assistant_msgs >= 2
    return {
        "ticket_across_replicas": across,
        "reply_delivered": delivered,
    }


def _zero_pii(counts: dict[str, int]) -> bool:
    return all(v == 0 for v in counts.values())


def summarize_trace(payload: dict[str, Any], marker: str) -> dict[str, Any]:
    """Summarize Jaeger /api/traces/<id> payload without retaining full span values."""
    data = payload.get("data") or []
    if not data:
        return {
            "trace_id": None,
            "span_count": 0,
            "span_names": [],
            "attribute_keys": [],
            "services": [],
            "marker_in_attributes": False,
        }

    trace = data[0] or {}
    spans = trace.get("spans") or []
    processes = trace.get("processes") or {}

    span_names: set[str] = set()
    attr_keys: set[str] = set()
    marker_found = False

    for sp in spans:
        op = sp.get("operationName")
        if op:
            span_names.add(str(op))
        for tag in sp.get("tags") or []:
            key = tag.get("key")
            if key:
                attr_keys.add(str(key))
            val = tag.get("value")
            if marker and val is not None and marker in str(val):
                marker_found = True
        for log_entry in sp.get("logs") or []:
            for field in log_entry.get("fields") or []:
                val = field.get("value")
                if marker and val is not None and marker in str(val):
                    marker_found = True

    services = {
        str(proc["serviceName"])
        for proc in processes.values()
        if isinstance(proc, dict) and proc.get("serviceName")
    }

    return {
        "trace_id": trace.get("traceID"),
        "span_count": len(spans),
        "span_names": sorted(span_names),
        "attribute_keys": sorted(attr_keys),
        "services": sorted(services),
        "marker_in_attributes": marker_found,
    }


def _http_json(
    method: str,
    url: str,
    *,
    api_key: str | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 45.0,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    headers: dict[str, str] = {"Accept": "application/json"}
    data_bytes: bytes | None = None
    if api_key:
        headers["X-API-Key"] = api_key
    if body is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return resp.status, resp_headers, parsed
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw_error": raw[:300]}
        return exc.code, resp_headers, parsed
    except Exception as exc:  # noqa: BLE001
        return 0, {}, {"error": type(exc).__name__}


def _run_cmd(cmd: list[str], *, capture: bool = True, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def _trace_id_from_traceparent(traceparent: str | None) -> str | None:
    if not traceparent:
        return None
    parts = traceparent.strip().split("-")
    if len(parts) >= 2 and len(parts[1]) == 32:
        return parts[1]
    return None


def _extract_turn_record(port: int, http_status: int, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    meta = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    return {
        "port": port,
        "http_status": http_status,
        "x_trace_id": headers.get("x-trace-id"),
        "traceparent": headers.get("traceparent"),
        "action": meta.get("action"),
        "ticket_id": (meta.get("ticket") or {}).get("ticket_id") if isinstance(meta.get("ticket"), dict) else None,
        "handoff": meta.get("handoff"),
        "agents_used": meta.get("agents_used") or [],
        "tools_used": meta.get("tools_used") or [],
        "response": str(body.get("response") or "")[:600],
    }


def _collect_compose_ps() -> list[dict[str, str]]:
    res = _run_cmd(["docker", "compose", "--profile", "observability", "ps", "--format", "json"])
    if res.returncode != 0 or not res.stdout.strip():
        return []
    raw = res.stdout.strip()
    entries: list[dict[str, Any]] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            entries = [e for e in parsed if isinstance(e, dict)]
        elif isinstance(parsed, dict):
            entries = [parsed]
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    entries.append(obj)
            except json.JSONDecodeError:
                continue
    return [
        {
            "service": str(e.get("Service") or e.get("Name") or ""),
            "image": str(e.get("Image") or ""),
            "state": str(e.get("State") or e.get("Status") or ""),
        }
        for e in entries
    ]


def _poll_jaeger_trace(trace_id: str | None, timeout_s: float = 30.0) -> tuple[bool, dict[str, Any]]:
    if not trace_id:
        return False, {"error": "missing_trace_id"}
    deadline = time.monotonic() + timeout_s
    last_payload: dict[str, Any] = {}
    url = f"http://localhost:16686/api/traces/{trace_id}"
    while True:
        status, _, payload = _http_json("GET", url, timeout=5.0)
        if status == 200 and isinstance(payload, dict) and payload.get("data"):
            first = payload["data"][0] or {}
            if first.get("spans"):
                return True, payload
            last_payload = payload
        if time.monotonic() >= deadline:
            return False, last_payload
        time.sleep(2.0)


def _wait_health(port: int, timeout_s: float = 30.0) -> tuple[int, dict[str, Any]]:
    deadline = time.monotonic() + timeout_s
    while True:
        status, _, body = _http_json("GET", f"http://localhost:{port}/health", timeout=5.0)
        if status == 200:
            return status, body
        if time.monotonic() >= deadline:
            return status, body
        time.sleep(1.0)


def _render_report_md(report: dict[str, Any]) -> str:
    checks = report["checks"]
    passed = sum(1 for v in checks.values() if v)
    lines: list[str] = [
        f"# Evidência de Integração e Observabilidade ({report['run_id']})",
        "",
        f"- **Data UTC:** `{report['timestamp_utc']}`",
        f"- **Commit:** `{report['git_commit']}` (árvore suja: `{'sim' if report['git_dirty'] else 'não'}`)",
        f"- **Checks:** **{passed}/{len(checks)}** aprovados",
        "",
        "## Verificações (`checks`)",
        "",
        "| Check | Resultado |",
        "| :--- | :--- |",
    ]
    for name, val in checks.items():
        lines.append(f"| `{name}` | {'PASS' if val else 'FAIL'} |")

    lines.extend([
        "",
        "## Serviços (`docker compose ps`)",
        "",
        "| Serviço | Imagem | Estado |",
        "| :--- | :--- | :--- |",
    ])
    for svc in report.get("compose_ps") or []:
        lines.append(f"| `{svc['service']}` | `{svc['image']}` | `{svc['state']}` |")

    health = report.get("health") or {}
    lines.extend([
        "",
        "## Saúde das réplicas",
        "",
        "| Réplica | Porta | HTTP | Ambiente | Estado | Rate Limit | Tracing |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for key in ("app_a", "app_b"):
        h = health.get(key) or {}
        lines.append(
            f"| `{h.get('replica')}` | {h.get('port')} | {h.get('http_status')} | "
            f"`{h.get('environment')}` | `{h.get('state_backend')}` | `{h.get('rate_limit_backend')}` | "
            f"`{h.get('tracing_exporter')}` |"
        )

    conv = report.get("conversation_across_replicas") or {}
    tkt = report.get("ticket_across_replicas") or {}
    pii = report.get("pii") or {}
    rl = report.get("rate_limit") or {}
    tr = report.get("traces") or {}

    lines.extend([
        "",
        "## Resumo dos cenários",
        "",
        f"- **Troca entre réplicas:** Turno 1 (`app-a`: status action=`{((conv.get('turn1') or {}).get('action') or {}).get('status')}`), "
        f"Turno 2 (`app-b`: status action=`{((conv.get('turn2') or {}).get('action') or {}).get('status')}`), "
        f"mensagens na sessão=`{conv.get('session_message_count')}`, "
        f"`/replacements` em `app-a`/`app-b`=`{conv.get('replacements_seen_a')}`/`{conv.get('replacements_seen_b')}`, "
        f"eventos de auditoria=`{conv.get('audit_event_count')}`.",
        f"- **Chamado entre réplicas:** criação em `app-b` (`{tkt.get('ticket_id')}`), PATCH em `app-a` "
        f"(HTTP `{tkt.get('patch_http_status')}`, resume=`{tkt.get('patch_resume_status')}`), "
        f"mensagens após PATCH em `app-b`=`{tkt.get('messages_after_patch_count')}`, "
        f"eventos de auditoria=`{tkt.get('audit_event_count')}`.",
        f"- **Varredura de PII:** `pg_dump` ({pii.get('pg_dump_bytes')} bytes, bytea={pii.get('pg_bytea_values')}, marcador={pii.get('pg_marker_count')}, pii={pii.get('pg_pii')}); "
        f"logs (`{pii.get('logs_bytes')}` bytes, marcador={pii.get('logs_marker_count')}, pii={pii.get('logs_pii')}).",
        f"- **Limite compartilhado:** primeiros 6 status=`{rl.get('initial_statuses')}`, 7º em 8001=HTTP `{rl.get('seventh_status')}` "
        f"(Retry-After=`{rl.get('seventh_retry_after')}`).",
        f"- **Traces no Jaeger:** conversa (`{(tr.get('conversation_turn1') or {}).get('summary', {}).get('span_count')}` spans), "
        f"PII (`{(tr.get('pii_turn') or {}).get('summary', {}).get('span_count')}` spans, "
        f"`marker_in_attributes={(tr.get('pii_turn') or {}).get('summary', {}).get('marker_in_attributes')}`).",
        "",
    ])
    return "\n".join(lines)


def run_compose_evidence(run_id: str) -> int:
    """Execute the end-to-end Docker Compose verification and persist JSON/Markdown reports."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        print("Error: GEMINI_API_KEY environment variable is required.", file=sys.stderr)
        return 2

    git_commit = _run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    git_dirty = bool(_run_cmd(["git", "status", "--porcelain"]).stdout.strip())

    env_path = ROOT / ".env"
    had_env = env_path.exists()
    orig_env = env_path.read_text(encoding="utf-8") if had_env else ""

    pg_password = secrets.token_hex(16)
    keys, api_keys_spec = make_api_keys()
    temp_env = render_env(pg_password, api_keys_spec)

    report: dict[str, Any] = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "compose_ps": [],
        "health": {},
        "conversation_across_replicas": {},
        "ticket_across_replicas": {},
        "pii": {},
        "rate_limit": {},
        "traces": {},
        "checks": {
            "replicas_healthy": False,
            "conversation_across_replicas": False,
            "ticket_across_replicas": False,
            "reply_delivered": False,
            "rate_limit_shared": False,
            "pii_absent_postgres": False,
            "pii_absent_logs": False,
            "trace_exported": False,
            "trace_private": False,
        },
        "error": None,
    }

    try:
        env_path.write_text(temp_env, encoding="utf-8", newline="\n")
        if hasattr(os, "chmod"):
            os.chmod(env_path, 0o600)

        up = _run_cmd(["docker", "compose", "--profile", "observability", "up", "-d", "--build", "--wait"], capture=False)
        if up.returncode != 0:
            raise RuntimeError(f"docker compose up failed with exit code {up.returncode}")

        report["compose_ps"] = _collect_compose_ps()

        # Step 3: Health
        h_a_st, h_a = _wait_health(8000)
        h_b_st, h_b = _wait_health(8001)
        report["health"] = {
            "app_a": {
                "port": 8000,
                "http_status": h_a_st,
                "replica": h_a.get("replica"),
                "environment": h_a.get("environment"),
                "state_backend": h_a.get("state_backend"),
                "rate_limit_backend": h_a.get("rate_limit_backend"),
                "tracing_exporter": h_a.get("tracing_exporter"),
            },
            "app_b": {
                "port": 8001,
                "http_status": h_b_st,
                "replica": h_b.get("replica"),
                "environment": h_b.get("environment"),
                "state_backend": h_b.get("state_backend"),
                "rate_limit_backend": h_b.get("rate_limit_backend"),
                "tracing_exporter": h_b.get("tracing_exporter"),
            },
        }
        report["checks"]["replicas_healthy"] = (
            h_a_st == 200
            and h_b_st == 200
            and h_a.get("replica") == "app-a"
            and h_b.get("replica") == "app-b"
            and h_a.get("environment") == "production"
            and h_b.get("environment") == "production"
            and h_a.get("state_backend") == "postgres"
            and h_b.get("state_backend") == "postgres"
            and h_a.get("rate_limit_backend") == "redis"
            and h_b.get("rate_limit_backend") == "redis"
        )

        # Step 4: Conversation across replicas (propose on app-a, confirm on app-b)
        conv_session = f"compose-conv-{run_id}-{uuid.uuid4().hex[:8]}"
        conv_key = keys["conversation"]
        op_key = keys["operator"]
        t1_st, t1_hdr, t1_body = _http_json(
            "POST",
            "http://localhost:8000/chat",
            api_key=conv_key,
            body={
                "message": "Minha maquininha GET-883921 está com a tela quebrada e quero trocar.",
                "session_id": conv_session,
            },
        )
        t2_st, t2_hdr, t2_body = _http_json(
            "POST",
            "http://localhost:8001/chat",
            api_key=conv_key,
            body={"message": "Sim, pode solicitar a troca.", "session_id": conv_session},
        )
        t1_rec = _extract_turn_record(8000, t1_st, t1_hdr, t1_body)
        t2_rec = _extract_turn_record(8001, t2_st, t2_hdr, t2_body)
        conv_trace_id = _trace_id_from_traceparent(t1_hdr.get("traceparent"))

        sess_st, _, sess_body = _http_json(
            "GET",
            f"http://localhost:8000/sessions/{urllib.parse.quote(conv_session)}/messages",
            api_key=conv_key,
        )
        rep_b_st, _, rep_b_body = _http_json("GET", "http://localhost:8001/replacements", api_key=conv_key)
        rep_a_st, _, rep_a_body = _http_json("GET", "http://localhost:8000/replacements", api_key=conv_key)

        req_id = (t2_rec.get("action") or {}).get("request_id") if isinstance(t2_rec.get("action"), dict) else None
        audit_conv_st = 0
        audit_conv_body: dict[str, Any] = {}
        if req_id:
            audit_conv_st, _, audit_conv_body = _http_json(
                "GET",
                f"http://localhost:8000/audit?target_id={urllib.parse.quote(str(req_id))}",
                api_key=op_key,
            )

        reps_a = [r.get("request_id") for r in (rep_a_body.get("replacements") or [])]
        reps_b = [r.get("request_id") for r in (rep_b_body.get("replacements") or [])]
        report["conversation_across_replicas"] = {
            "session_id": conv_session,
            "turn1": t1_rec,
            "turn2": t2_rec,
            "session_messages_http_status": sess_st,
            "session_message_count": len(sess_body.get("messages") or []),
            "replacements_http_status_a": rep_a_st,
            "replacements_http_status_b": rep_b_st,
            "replacements_seen_a": bool(req_id and req_id in reps_a),
            "replacements_seen_b": bool(req_id and req_id in reps_b),
            "request_id": req_id,
            "audit_http_status": audit_conv_st,
            "audit_event_count": len(audit_conv_body.get("events") or []),
            "audit_actions": [e.get("action") for e in (audit_conv_body.get("events") or [])],
        }
        report["checks"]["conversation_across_replicas"] = bool(
            t1_st == 200
            and t2_st == 200
            and isinstance(t1_rec.get("action"), dict)
            and t1_rec["action"].get("status") == "pending_confirmation"
            and isinstance(t2_rec.get("action"), dict)
            and t2_rec["action"].get("status") == "executed"
            and req_id
            and req_id in reps_a
            and req_id in reps_b
            and sess_st == 200
            and len(sess_body.get("messages") or []) >= 4
            and audit_conv_st == 200
            and len(audit_conv_body.get("events") or []) >= 1
        )

        # Step 5: Ticket across replicas
        tkt_session = f"compose-tkt-{run_id}-{uuid.uuid4().hex[:8]}"
        tkt_key = keys["ticket"]
        tk1_st, tk1_hdr, tk1_body = _http_json(
            "POST",
            "http://localhost:8001/chat",
            api_key=tkt_key,
            body={"message": "Quero falar com um atendente humano, por favor.", "session_id": tkt_session},
        )
        tk1_rec = _extract_turn_record(8001, tk1_st, tk1_hdr, tk1_body)
        ticket_id = tk1_rec.get("ticket_id")
        op_reply = "Olá, analisamos seu chamado e concluímos o atendimento."
        patch_st = 0
        patch_body: dict[str, Any] = {}
        if ticket_id:
            patch_st, _, patch_body = _http_json(
                "PATCH",
                f"http://localhost:8000/tickets/{urllib.parse.quote(str(ticket_id))}",
                api_key=op_key,
                body={"reply": op_reply},
            )
        tkt_sess_st, _, tkt_sess_body = _http_json(
            "GET",
            f"http://localhost:8001/sessions/{urllib.parse.quote(tkt_session)}/messages",
            api_key=tkt_key,
        )
        messages_after_patch = list(tkt_sess_body.get("messages") or []) if tkt_sess_st == 200 else []
        tk2_st, tk2_hdr, tk2_body = _http_json(
            "POST",
            "http://localhost:8001/chat",
            api_key=tkt_key,
            body={"message": "Alguma novidade?", "session_id": tkt_session},
        )
        tk2_rec = _extract_turn_record(8001, tk2_st, tk2_hdr, tk2_body)

        audit_tkt_st = 0
        audit_tkt_body: dict[str, Any] = {}
        if ticket_id:
            audit_tkt_st, _, audit_tkt_body = _http_json(
                "GET",
                f"http://localhost:8001/audit?target_id={urllib.parse.quote(str(ticket_id))}",
                api_key=op_key,
            )

        tkt_audit_actions = [str(e.get("action")) for e in (audit_tkt_body.get("events") or []) if e.get("action")]
        tkt_eval = ticket_checks(patch_st, patch_body, messages_after_patch, tkt_audit_actions)
        report["ticket_across_replicas"] = {
            "session_id": tkt_session,
            "ticket_id": ticket_id,
            "turn1": tk1_rec,
            "patch_http_status": patch_st,
            "patch_status": patch_body.get("status"),
            "patch_resume_status": (patch_body.get("resume") or {}).get("status")
            if isinstance(patch_body.get("resume"), dict)
            else None,
            "messages_after_patch_http_status": tkt_sess_st,
            "messages_after_patch_count": len(messages_after_patch),
            "turn2": tk2_rec,
            "audit_http_status": audit_tkt_st,
            "audit_event_count": len(audit_tkt_body.get("events") or []),
            "audit_actions": tkt_audit_actions,
        }
        report["checks"]["ticket_across_replicas"] = bool(
            tk1_st == 200 and ticket_id and tkt_eval["ticket_across_replicas"]
        )
        report["checks"]["reply_delivered"] = bool(
            tk1_st == 200 and ticket_id and tk2_st == 200 and tkt_eval["reply_delivered"]
        )

        # Step 6: PII persistence vs masking & log hygiene
        marker = f"evpii-{run_id}-{uuid.uuid4().hex[:10]}"
        pii_session = f"compose-pii-{run_id}-{uuid.uuid4().hex[:8]}"
        pii_st, pii_hdr, _ = _http_json(
            "POST",
            "http://localhost:8000/chat",
            api_key=keys["pii"],
            body={
                "message": f"Meu cartão {TEST_CARD_SPACED} e CPF {TEST_CPF_FORMATTED} ref {marker}",
                "session_id": pii_session,
            },
        )
        pii_trace_id = _trace_id_from_traceparent(pii_hdr.get("traceparent"))

        dump_res = _run_cmd(["docker", "compose", "exec", "-T", "postgres", "pg_dump", "-U", "getnet", "-d", "getnet", "--data-only"])
        dump_text = dump_res.stdout or ""
        pg_scan = scan_dump(dump_text, marker)
        pg_pii = pg_scan["pii"]
        pg_marker_count = pg_scan["marker"]

        logs_res = _run_cmd(["docker", "compose", "logs", "--no-color", "app-a", "app-b"])
        logs_text = (logs_res.stdout or "") + "\n" + (logs_res.stderr or "")
        logs_pii = scan_pii(logs_text)
        logs_marker_count = logs_text.count(marker)

        report["pii"] = {
            "http_status": pii_st,
            "pg_dump_bytes": len(dump_text.encode("utf-8")),
            "pg_bytea_values": pg_scan["bytea_values"],
            "pg_marker_count": pg_marker_count,
            "pg_pii": pg_pii,
            "logs_bytes": len(logs_text.encode("utf-8")),
            "logs_marker_count": logs_marker_count,
            "logs_pii": logs_pii,
        }
        report["checks"]["pii_absent_postgres"] = (
            pii_st == 200 and dump_res.returncode == 0 and pg_marker_count >= 1 and _zero_pii(pg_pii)
        )
        report["checks"]["pii_absent_logs"] = (
            logs_res.returncode == 0 and logs_marker_count == 0 and _zero_pii(logs_pii)
        )

        # Step 7: Shared rate limit across 8000 / 8001 (limit = 6)
        rl_session = f"compose-rl-{run_id}-{uuid.uuid4().hex[:8]}"
        rl_key = keys["rate_limit"]
        ports = [8000, 8001, 8000, 8001, 8000, 8001]
        initial_statuses: list[int] = []
        for port in ports:
            st, _, _ = _http_json(
                "POST",
                f"http://localhost:{port}/chat",
                api_key=rl_key,
                body={"message": "oi", "session_id": rl_session},
            )
            initial_statuses.append(st)
        seventh_st, seventh_hdr, _ = _http_json(
            "POST",
            "http://localhost:8001/chat",
            api_key=rl_key,
            body={"message": "oi", "session_id": rl_session},
        )
        retry_after = seventh_hdr.get("retry-after")
        report["rate_limit"] = {
            "initial_ports": ports,
            "initial_statuses": initial_statuses,
            "seventh_port": 8001,
            "seventh_status": seventh_st,
            "seventh_retry_after": retry_after,
        }
        report["checks"]["rate_limit_shared"] = (
            all(s == 200 for s in initial_statuses) and seventh_st == 429 and bool(retry_after)
        )

        # Step 8: Exported traces in Jaeger
        ok_conv, conv_trace_payload = _poll_jaeger_trace(conv_trace_id, timeout_s=30.0)
        ok_pii, pii_trace_payload = _poll_jaeger_trace(pii_trace_id, timeout_s=30.0)

        conv_summary = summarize_trace(conv_trace_payload, marker)
        pii_summary = summarize_trace(pii_trace_payload, marker)
        conv_trace_pii = scan_pii(json.dumps(conv_trace_payload, ensure_ascii=False))
        pii_trace_pii = scan_pii(json.dumps(pii_trace_payload, ensure_ascii=False))

        report["traces"] = {
            "conversation_turn1": {
                "found": ok_conv,
                "trace_id": conv_trace_id,
                "summary": conv_summary,
                "scan_pii": conv_trace_pii,
            },
            "pii_turn": {
                "found": ok_pii,
                "trace_id": pii_trace_id,
                "summary": pii_summary,
                "scan_pii": pii_trace_pii,
            },
        }
        report["checks"]["trace_exported"] = bool(
            ok_conv
            and ok_pii
            and conv_summary["span_count"] > 0
            and pii_summary["span_count"] > 0
            and "chat.request" in conv_summary["span_names"]
            and "chat.request" in pii_summary["span_names"]
        )
        report["checks"]["trace_private"] = bool(
            ok_conv
            and ok_pii
            and _zero_pii(conv_trace_pii)
            and _zero_pii(pii_trace_pii)
            and not conv_summary["marker_in_attributes"]
            and not pii_summary["marker_in_attributes"]
        )

    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    finally:
        _run_cmd(["docker", "compose", "--profile", "observability", "down", "-v"])
        if had_env:
            env_path.write_text(orig_env, encoding="utf-8", newline="\n")
        elif env_path.exists():
            env_path.unlink()

    out_dir = ROOT / "reports/integration"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{run_id}.json"
    out_md = out_dir / f"{run_id}.md"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    out_md.write_text(_render_report_md(report), encoding="utf-8", newline="\n")

    all_passed = all(report["checks"].values()) and report["error"] is None
    print(json.dumps(report["checks"], ensure_ascii=False))
    return 0 if all_passed else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Docker Compose integration and observability evidence capture."""
    parser = argparse.ArgumentParser(description="Capture multi-replica Docker Compose integration evidence.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Bring up Compose stack with observability and capture evidence report.")
    run_p.add_argument("--run-id", required=True, help="Output report basename under reports/integration/.")

    args = parser.parse_args(argv)
    if args.command == "run":
        return run_compose_evidence(args.run_id)
    return 1


if __name__ == "__main__":
    sys.exit(main())
