# STATUS DO REPOSITÓRIO

**Subfase:** 13A + 13A-fix — Estado distribuído (Postgres + Redis), tracing (OpenTelemetry), dashboard e correções de concorrência/CI
**Base:** `431eb1f` (Fase 12F) | **Lock:** `c925916` | **13A:** `66add08` | **Python:** 3.13.3

## O que mudou (13A)

- **Processo aposentado (fases 1–12 removidas da árvore):** mantidos `docs/process.md`, `scripts/verify_phase13a.py`, `docs/phase-prompts/13A.md` e `docs/phase-prompts/13A-fix.md`.
- **Dependências:** `requirements.txt`, `requirements-dev.txt`, `requirements.lock` (regenerado no Codespaces com `python:3.11-slim`).
- **Configuração e armazenamento:** `src/config.py`, `.env.example`, `src/core/db.py`, `src/core/tickets_db.py` (SQLAlchemy Core sobre Postgres ou SQLite, `FOR UPDATE` em `append_customer_message`), `src/core/checkpointer.py`, `src/core/graph.py`.
- **Rate limit distribuído (Redis):** `src/core/rate_limit.py` (`RateLimiter`, `RedisRateLimiter` em sorted set com fallback por 5 s), `src/core/auth.py`, `src/core/metrics.py` (`getnet_rate_limit_backend_errors_total`).
- **Tracing e API:** `src/core/tracing.py` (allowlist de 22 atributos, `traceparent`, sem texto de conversa ou PII), instrumentação em `src/main.py`, `src/core/graph.py`, `src/agents/specialists.py`, `src/core/llm.py`, `src/agents/injection_classifier.py`, `src/rag/reranker.py`, `src/core/notifier.py`, `src/static/demo.html`.
- **Compose, observabilidade e CI:** `docker-compose.yml`, `deploy/prometheus.yml`, `deploy/grafana/provisioning/...`, `deploy/grafana/dashboards/getnet.json`, `.github/workflows/ci.yml`.
- **Testes:** `pyproject.toml`, `tests/conftest.py`, `tests/test_state_backends.py` (9 testes), `tests/test_rate_limit_redis.py` (7 testes), `tests/test_tracing.py` (6 testes), `tests/integration/test_postgres_redis_integration.py` (10 testes `integration`).

## Correções 13A-fix

- **Pool mínimo (`src/core/checkpointer.py`):** `ConnectionPool(..., min_size=1, max_size=pool_size)` em `build_postgres_checkpointer` e `saver.setup()` envolvido em `with schema_lock(url):`.
- **Lock de inicialização de schema (`src/core/db.py`):** adicionados `SCHEMA_LOCK_KEY` e o context manager `schema_lock(target)` com conexão `psycopg.connect(..., autocommit=True)` dedicada, polling não-bloqueante de `pg_try_advisory_lock` a cada `0.1` s (timeout `60.0` s com `TimeoutError`) e `pg_advisory_unlock` em `finally`; `ensure_schema(engine)` executa sob `schema_lock`.
- **Teste de concorrência (`tests/integration/test_postgres_redis_integration.py`):** adicionado `test_concurrent_startup_setup_is_serialized` com banco temporário (`CREATE DATABASE` / `DROP DATABASE`), `threading.Barrier(4)` e `pool_size=1`.
- **CI (`TID`, `.github/workflows/ci.yml`):** captura de `TID` via `| tail -n 1 | tr -d '\r'` e validação com `grep -Eq '^GET-TKT-[0-9]{8}-[0-9A-F]{10}$'`.
- **Compose & teste de defaults (`docker-compose.yml`, `tests/test_docker_defaults.py`):** variáveis de ambiente da app definidas uma única vez em `x-app-env: &app-env` herdado por `app-a` e `app-b`; Jaeger atualizado para `jaegertracing/jaeger:2.6.0` (sem `COLLECTOR_OTLP_ENABLED`); `test_compose_pins_production` valida `APP_ENV == "production"` nos serviços `app-*` via `yaml.safe_load`.

## Imagens no Compose

- `postgres:16-alpine`
- `redis:7-alpine`
- `jaegertracing/jaeger:2.6.0` (`--profile observability`)
- `prom/prometheus:v2.55.1` (`--profile observability`)
- `grafana/grafana:11.3.1` (`--profile observability`)

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `412 passed, 10 deselected in 38.76s`
- `python scripts/verify_phase13a.py`: `SUMMARY: 39/39 passed` (`PASS A0`–`A8`, `PASS S1.status`, `PASS B1`–`B9`, `PASS I1`, `PASS C1`, `INFO C2.integration_suite`, `PASS C3`–`C4`, `PASS Q1`–`Q6`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md`, `docs/phase-prompts/13A.md` ou `docs/phase-prompts/13A-fix.md`.
