"""Integration tests against real PostgreSQL and Redis (skipped by default; fail if URLs missing)."""
from __future__ import annotations

import concurrent.futures
import os
import uuid

import psycopg
import pytest
import redis
from langchain_core.messages import AIMessage
from sqlalchemy import text
from sqlalchemy.engine import make_url

from src.core import db
from src.core.checkpointer import build_postgres_checkpointer
from src.core.graph import OrchestrationGraph
from src.core.rate_limit import RedisRateLimiter
from src.core.tickets_db import TicketsRepository, TicketTransitionError
from tests.fakes import ScriptedChatModel

pytestmark = pytest.mark.integration


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    return url


@pytest.fixture(scope="session")
def pg_test_url() -> str:
    """Create a dedicated temporary PostgreSQL database for this integration test session."""
    base_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    redis_url = os.environ.get("TEST_REDIS_URL", "").strip()
    if not base_url or not redis_url:
        pytest.fail("TEST_DATABASE_URL and TEST_REDIS_URL must be set to run integration tests")

    db_name = f"getnet_int_{uuid.uuid4().hex[:10]}"
    admin_url = _psycopg_url(base_url)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{db_name}"')

    target_url = make_url(base_url).set(database=db_name).render_as_string(hide_password=False)
    try:
        yield target_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')


@pytest.fixture(scope="session")
def redis_test_url() -> str:
    url = os.environ.get("TEST_REDIS_URL", "").strip()
    if not url or not os.environ.get("TEST_DATABASE_URL", "").strip():
        pytest.fail("TEST_DATABASE_URL and TEST_REDIS_URL must be set to run integration tests")
    return url


def test_postgres_ticket_lifecycle(pg_test_url: str) -> None:
    repo = TicketsRepository(pg_test_url)
    try:
        created = repo.create_ticket(
            user_id="pg-user-1",
            reason="falha na integração",
            priority="high",
            session_id="pg-sess-1",
            transcript=[{"role": "user", "content": "preciso de ajuda"}],
        )
        tid = created["ticket_id"]
        fetched = repo.get_ticket(tid)
        assert fetched is not None and fetched["status"] == "open"

        prog = repo.update_ticket(tid, status="in_progress", operator_id="op-pg")
        assert prog is not None and prog["status"] == "in_progress"

        ans = repo.update_ticket(tid, reply="Resolvido pela equipe.", operator_id="op-pg")
        assert ans is not None and ans["status"] == "answered"

        closed = repo.update_ticket(tid, status="closed", operator_id="op-pg")
        assert closed is not None and closed["status"] == "closed"
    finally:
        repo.engine.dispose()


def test_postgres_concurrent_update_conflict_raises(pg_test_url: str) -> None:
    repo_a = TicketsRepository(pg_test_url)
    repo_b = TicketsRepository(pg_test_url)
    try:
        tid = repo_a.create_ticket(user_id="pg-user-2", reason="concorrência")["ticket_id"]
        u1 = repo_a.update_ticket(tid, status="in_progress", operator_id="op-a")
        assert u1 is not None and u1["status"] == "in_progress"

        with pytest.raises(TicketTransitionError):
            repo_b.update_ticket(tid, status="open", operator_id="op-b")
    finally:
        repo_a.engine.dispose()
        repo_b.engine.dispose()


def test_postgres_mark_delivered_idempotent_across_two_engines(pg_test_url: str) -> None:
    repo_a = TicketsRepository(pg_test_url)
    repo_b = TicketsRepository(pg_test_url)
    try:
        tid = repo_a.create_ticket(user_id="pg-user-3", reason="entrega")["ticket_id"]
        repo_a.update_ticket(tid, reply="OK", operator_id="op-a")

        first = repo_a.mark_delivered(tid)
        second = repo_b.mark_delivered(tid)
        assert (first, second) == (True, False)
    finally:
        repo_a.engine.dispose()
        repo_b.engine.dispose()


def test_postgres_append_customer_message_concurrent_threads(pg_test_url: str) -> None:
    repo_a = TicketsRepository(pg_test_url)
    repo_b = TicketsRepository(pg_test_url)
    try:
        tid = repo_a.create_ticket(user_id="pg-user-4", reason="mensagens simultâneas")["ticket_id"]

        def send_a() -> bool:
            return repo_a.append_customer_message(tid, "msg-thread-a")

        def send_b() -> bool:
            return repo_b.append_customer_message(tid, "msg-thread-b")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(send_a)
            f2 = pool.submit(send_b)
            assert f1.result() is True
            assert f2.result() is True

        stored = repo_a.get_ticket(tid)
        assert stored is not None
        contents = {m["content"] for m in stored["transcript"]}
        assert contents == {"msg-thread-a", "msg-thread-b"}
    finally:
        repo_a.engine.dispose()
        repo_b.engine.dispose()


def test_postgres_checkpointer_continuity_across_separate_pools(pg_test_url: str) -> None:
    cp_a = build_postgres_checkpointer(pg_test_url, pool_size=2)
    cp_b = build_postgres_checkpointer(pg_test_url, pool_size=2)
    try:
        g_a = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Turno 1 ok.")]), checkpointer=cp_a)
        g_b = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Turno 2 ok.")]), checkpointer=cp_b)

        sid = f"pg-cont-{uuid.uuid4().hex[:8]}"
        res1 = g_a.run_sync(user_id="merchant-a", session_id=sid, message="Oi, primeira mensagem")
        res2 = g_b.run_sync(user_id="merchant-a", session_id=sid, message="Segunda mensagem")

        assert "Turno 1" in res1.agent_response
        assert "Turno 2" in res2.agent_response

        hist = g_b.session_messages(user_id="merchant-a", session_id=sid)
        assert [m["content"] for m in hist] == [
            "Oi, primeira mensagem",
            "Turno 1 ok.",
            "Segunda mensagem",
            "Turno 2 ok.",
        ]
    finally:
        cp_a.conn.close()
        cp_b.conn.close()


def test_postgres_checkpointer_isolates_users_with_same_session_id(pg_test_url: str) -> None:
    cp_a = build_postgres_checkpointer(pg_test_url, pool_size=2)
    cp_b = build_postgres_checkpointer(pg_test_url, pool_size=2)
    try:
        g_a = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Resp A.")]), checkpointer=cp_a)
        g_b = OrchestrationGraph(chat_model=ScriptedChatModel(responses=[AIMessage(content="Resp B.")]), checkpointer=cp_b)

        shared_sid = f"shared-{uuid.uuid4().hex[:8]}"
        g_a.run_sync(user_id="user-alpha", session_id=shared_sid, message="Segredo do Alpha")
        g_b.run_sync(user_id="user-beta", session_id=shared_sid, message="Pergunta do Beta")

        hist_a = [m["content"] for m in g_a.session_messages(user_id="user-alpha", session_id=shared_sid)]
        hist_b = [m["content"] for m in g_b.session_messages(user_id="user-beta", session_id=shared_sid)]
        assert "Segredo do Alpha" in hist_a and "Pergunta do Beta" not in hist_a
        assert "Pergunta do Beta" in hist_b and "Segredo do Alpha" not in hist_b
    finally:
        cp_a.conn.close()
        cp_b.conn.close()


def test_postgres_never_persists_raw_card_or_cpf_in_any_column(pg_test_url: str) -> None:
    cp = build_postgres_checkpointer(pg_test_url, pool_size=2)
    repo = TicketsRepository(pg_test_url)
    card_fmt, card_raw = "4111 1111 1111 1111", "4111111111111111"
    cpf_fmt, cpf_raw = "529.982.247-25", "52998224725"
    try:
        model = ScriptedChatModel(responses=[AIMessage(content="Atendimento registrado sem dados sensíveis.")])
        g = OrchestrationGraph(chat_model=model, checkpointer=cp)
        sid = f"pii-{uuid.uuid4().hex[:8]}"
        g.run_sync(user_id="pii-user", session_id=sid, message=f"Cartão {card_fmt} e CPF {cpf_fmt}")
        repo.create_ticket(
            user_id="pii-user",
            reason="teste pii",
            session_id=sid,
            transcript=[{"role": "user", "content": "Cartão [CARTAO_OCULTO] CPF [CPF_OCULTO]"}],
        )

        with repo.engine.connect() as conn:
            cols = conn.execute(
                text(
                    "SELECT table_name, column_name, data_type "
                    "FROM information_schema.columns WHERE table_schema = 'public'"
                )
            ).all()
            for tbl, col, dtype in cols:
                expr = f"encode({col}, 'escape')" if dtype == "bytea" else f"CAST({col} AS TEXT)"
                rows = conn.execute(text(f"SELECT {expr} FROM {tbl} WHERE {col} IS NOT NULL")).all()
                for (val,) in rows:
                    text_val = str(val)
                    for secret in (card_fmt, card_raw, cpf_fmt, cpf_raw):
                        assert secret not in text_val, f"Raw PII leaked into {tbl}.{col}"
    finally:
        cp.conn.close()
        repo.engine.dispose()


def test_redis_real_shared_rate_limiter(redis_test_url: str) -> None:
    prefix = f"getnet:int:{uuid.uuid4().hex[:8]}:"
    client_a = redis.Redis.from_url(redis_test_url, socket_timeout=2.0, socket_connect_timeout=2.0)
    client_b = redis.Redis.from_url(redis_test_url, socket_timeout=2.0, socket_connect_timeout=2.0)
    try:
        lim_a = RedisRateLimiter(client_a, 3, prefix=prefix)
        lim_b = RedisRateLimiter(client_b, 3, prefix=prefix)
        assert [lim_a.hit("merchant"), lim_b.hit("merchant"), lim_a.hit("merchant")] == [None, None, None]
        wait = lim_b.hit("merchant")
        assert wait is not None and 0 < wait <= 60.0
    finally:
        for k in client_a.scan_iter(f"{prefix}*"):
            client_a.delete(k)
        client_a.close()
        client_b.close()


def test_postgres_ensure_schema_adds_missing_column(pg_test_url: str) -> None:
    engine = db.make_engine(pg_test_url, pool_size=2)
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS tickets"))
            conn.execute(
                text(
                    "CREATE TABLE tickets ("
                    "id SERIAL PRIMARY KEY, "
                    "ticket_id TEXT UNIQUE NOT NULL, "
                    "user_id TEXT NOT NULL, "
                    "reason TEXT NOT NULL, "
                    "status TEXT NOT NULL DEFAULT 'open', "
                    "priority TEXT NOT NULL DEFAULT 'standard', "
                    "channel TEXT NOT NULL DEFAULT 'ai_chat', "
                    "created_at TEXT NOT NULL, "
                    "updated_at TEXT NOT NULL)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO tickets (ticket_id, user_id, reason, created_at, updated_at) "
                    "VALUES ('GET-TKT-PGOLD', 'u-old', 'antigo', '2026-01-01', '2026-01-01')"
                )
            )
        db.ensure_schema(engine)
        with engine.connect() as conn:
            cols = {
                r[0]
                for r in conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'tickets'"
                    )
                ).all()
            }
            assert {
                "session_id",
                "transcript",
                "operator_reply",
                "delivered_at",
                "notified_at",
                "notification_status",
            } <= cols
    finally:
        engine.dispose()
