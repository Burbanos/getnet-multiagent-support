# STATUS DO REPOSITÓRIO

**Subfase:** 13A — Estado distribuído (Postgres + Redis), tracing (OpenTelemetry) e dashboard
**Base:** `431eb1f` (Fase 12F) | **Lock:** `c925916` (após `5c6ec9d`) | **Python:** 3.13.3

## O que mudou

- **Processo aposentado (fases 1–12 removidas da árvore):** `docs/status-history.md`, verificadores anteriores em `scripts/verify_phase*.py` e prompts anteriores em `docs/phase-prompts/*.md`. Mantidos `docs/process.md`, `scripts/verify_phase13a.py` e `docs/phase-prompts/13A.md`.
- **Dependências:** `requirements.txt`, `requirements-dev.txt`, `requirements.lock` (regenerado no Codespaces com `python:3.11-slim`).
- **Configuração e armazenamento:** `src/config.py`, `.env.example`, `src/core/db.py` (novo: `is_postgres_url`, `make_engine`, `ensure_schema`, `ping`, `validate_state_config`), `src/core/tickets_db.py` (SQLAlchemy Core sobre Postgres ou SQLite, `FOR UPDATE` em `append_customer_message`), `src/core/checkpointer.py` (`build_postgres_checkpointer`, `build_checkpointer`, `checkpoint_backend`), `src/core/graph.py`.
- **Rate limit distribuído (Redis):** `src/core/rate_limit.py` (novo: `RateLimiter`, `RedisRateLimiter` com janela deslizante em sorted set e degradação controlada por 5 s), `src/core/auth.py`, `src/core/metrics.py` (`getnet_rate_limit_backend_errors_total`).
- **Tracing e API:** `src/core/tracing.py` (novo: allowlist de 22 atributos, `traceparent`, sem texto de conversa ou PII), instrumentação em `src/main.py` (`lifespan`, `/health` 503 se ping falhar, `/`, `/agents`, `/chat`, `PATCH /tickets/{id}`), `src/core/graph.py`, `src/agents/specialists.py`, `src/core/llm.py`, `src/agents/injection_classifier.py`, `src/rag/reranker.py`, `src/core/notifier.py`, `src/static/demo.html`.
- **Compose, observabilidade e CI:** `docker-compose.yml`, `deploy/prometheus.yml`, `deploy/grafana/provisioning/...`, `deploy/grafana/dashboards/getnet.json`, `.github/workflows/ci.yml`.
- **Testes:** `pyproject.toml`, `tests/conftest.py`, `tests/test_state_backends.py` (9 testes), `tests/test_rate_limit_redis.py` (7 testes), `tests/test_tracing.py` (6 testes), `tests/integration/test_postgres_redis_integration.py` (9 testes `integration`).

## Imagens no Compose

- `postgres:16-alpine`
- `redis:7-alpine`
- `jaegertracing/all-in-one:1.62.0` (`--profile observability`)
- `prom/prometheus:v2.55.1` (`--profile observability`)
- `grafana/grafana:11.3.1` (`--profile observability`)

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `412 passed, 9 deselected in 38.98s`
- `python scripts/verify_phase13a.py`: `SUMMARY: 35/35 passed` (`PASS A0`–`A8`, `PASS S1.status`, `PASS B1`–`B8`, `PASS I1`, `PASS C1`, `INFO C2.integration_suite`, `PASS C3`, `PASS Q1`–`Q6`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/13A.md`.
