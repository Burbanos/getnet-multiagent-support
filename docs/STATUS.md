# STATUS DO REPOSITÓRIO

**Subfase:** 13D-1 — Auditoria transacional, isolamento da avaliação, importação do anotador e script de evidência do Compose
**Base:** `5a2ff9b` (13C + índice reconstruído) | **Python:** 3.13.3

## O que mudou

- **Aposentadoria da 13C:** removidos via `git rm` `docs/phase-prompts/13C.md` e `scripts/verify_phase13c.py`; incluído `*.xlsx` em `.gitignore`.
- **Auditoria transacional e fail-closed ([actions_db.py](src/core/actions_db.py), [tickets_db.py](src/core/tickets_db.py), [graph.py](src/core/graph.py)):** criada `insert_audit(conn, ...)` usada por `ActionsRepository.record_audit` e dentro das transações de `create_ticket`, `update_ticket` e `mark_delivered` (sem `try/except`, desfazendo a operação se a auditoria falhar); `_abstention_check_node` agora envia `actor_type="system"` no escalonamento automático; falhas de `ActionsRepository.confirm`/`decline` agora são fail-closed (`action.status == "error"`, `action_unavailable`, `confirm_pending_action` fora de `tools_used`, log apenas com `type(exc).__name__`).
- **Isolamento por caso na avaliação ([runner.py](src/eval/runner.py)):** `run_eval` isola cada caso em arquivo SQLite próprio, zera `settings.DATABASE_URL`, reinicia os repositórios de chamados e ações antes/depois de cada caso e restaura `TICKETS_DB_PATH` e `DATABASE_URL` no `finally`.
- **Planilha do anotador e concordância ([annotator.py](src/eval/annotator.py), [__main__.py](src/eval/__main__.py)):** leitura de `.xlsx` apenas com biblioteca padrão (`zipfile` + XML), validação completa com coleta de todos os erros sem gravar nada, exportação de `answers.csv`, `comments.csv` e `declaration.json` via `human-import`, e cálculo de concordância/kappa/divergências em `raters.json` e `raters.md` via `human-raters`.
- **Declaração de execuções e relatório nomeado ([run_context.py](src/eval/run_context.py), [__main__.py](src/eval/__main__.py), [hybrid_eval.py](src/rag/hybrid_eval.py)):** subcomando `context` acrescentando entradas novas sem alterar existentes; `hybrid_eval report --name` gravando `reports/<NOME>.{json,md}` sem sobrescrever `retrieval_hybrid.*`.
- **Evidência do Compose ([compose_evidence.py](scripts/compose_evidence.py)):** `scan_pii`, `summarize_trace` e subcomando `run --run-id` com fluxo multi-réplica, PII, rate limit compartilhado, Jaeger e relatório em `reports/integration/`.
- **Testes:** novos [test_audit_transactions.py](tests/test_audit_transactions.py) (4), [test_eval_isolation.py](tests/test_eval_isolation.py) (3), [test_annotator_import.py](tests/test_annotator_import.py) (6), [test_raters_and_context.py](tests/test_raters_and_context.py) (4), [test_compose_evidence.py](tests/test_compose_evidence.py) (3) e 1 teste de rollback Postgres em [test_postgres_redis_integration.py](tests/integration/test_postgres_redis_integration.py).

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `501 passed, 13 deselected in 66.73s`
- `python scripts/verify_phase13d1.py`: `SUMMARY: 29/29 passed` (`PASS A0`–`A5`, `PASS S1.status`, `PASS T1`–`T10`, `PASS G1`–`G2`, `PASS R1`–`R4`, `PASS Q1`–`Q6`, `INFO Q7.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/13D-1.md`.
