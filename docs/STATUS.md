# STATUS DO REPOSITÓRIO

**Subfase:** 13C — Correções do smoke, troca de maquininha com confirmação e auditoria, console do operador e corpus
**Base:** `96d6894` (13B + smoke do holdout 3) | **Python:** 3.13.3

## O que mudou

- **Aposentadoria da 13B:** removidos via `git rm` `docs/phase-prompts/13B.md` e `scripts/verify_phase13b.py`; adicionados `docs/phase-prompts/13C.md`, `scripts/verify_phase13c.py`, `data/eval/cases_actions.jsonl` e os prompts atualizados em `src/prompts/`.
- **Correções do smoke ([planner.py](src/agents/planner.py), [graph.py](src/core/graph.py), [terminal_tools.py](src/tools/terminal_tools.py)):** `[Plan for this turn]` agora passa só o objetivo (`N. <goal>`) sem `delegate`; turnos `out_of_scope` (e qualquer turno com tokens sem `llm_model`) registram o modelo do planner para calcular `estimated_cost_usd`; `diagnose_terminal_connectivity` devolve `{"status": "not_found", "error": "terminal_not_found"}` quando `terminal_serial` não pertence ao lojista.
- **Troca de maquininha com confirmação, idempotência e auditoria ([db.py](src/core/db.py), [actions_db.py](src/core/actions_db.py), [tickets_db.py](src/core/tickets_db.py), [agent_tools.py](src/tools/agent_tools.py), [supervisor_tools.py](src/tools/supervisor_tools.py), [specialists.py](src/agents/specialists.py), [state.py](src/core/state.py), [runner.py](src/eval/runner.py), [cases.py](src/eval/cases.py), [metrics.py](src/core/metrics.py)):**
  - `TurnPlan` ganha `action_confirmation` (`none|confirmed|declined`); tabelas `pending_actions`, `terminal_replacements` (com índice único parcial `status = 'requested'` em `serial_number`) e `audit_events` (ator em `actor_hash` e `details` restrito à allowlist).
  - `ActionsRepository` com `propose_terminal_replacement`, `confirm` (`SELECT ... FOR UPDATE`, guarda `same_turn`, expiração e `already_requested`), `decline` (chamado deterministicamente no `planner`), `list_replacements`, `list_audit` e `record_audit`.
  - `request_terminal_replacement` (Support Agent, `sanitize_pii` e limite de 300 chars) e `confirm_pending_action` (Supervisor, portão fail-closed no `_tools_node`). Campo `action` em `AgentState`, `AgentMetadata` e `observe_turn`. Auditoria completa do ciclo de vida dos chamados (`ticket_created` `merchant`/`system`, `ticket_updated`, `ticket_replied`, `ticket_reply_delivered`).
- **API e Console do operador ([main.py](src/main.py), [operator.html](src/static/operator.html), [demo.html](src/static/demo.html)):** novos `GET /audit`, `GET /replacements` e `GET /operator` (arquivo único sem dependências externas, chave só em memória, DOM via `createElement`/`textContent`, atualização a cada 15 s) com link em `/` e `/demo`.
- **Corpus ([ingest.py](src/rag/ingest.py), [pages.jsonl](data/corpus/pages.jsonl), [manifest.json](data/corpus/manifest.json), [README.md](data/corpus/README.md)):** adicionados `--only URL`, status `redirect_duplicate` em `STATUSES`, extração corrigida e recoleta parcial das três URLs (`ok: 32`, `redirect_duplicate: 1`).
- **Testes:** novos [test_actions_repository.py](tests/test_actions_repository.py) (10), [test_write_action_flow.py](tests/test_write_action_flow.py) (8), [test_audit_and_operator.py](tests/test_audit_and_operator.py) (8), [test_ingest_extract.py](tests/test_ingest_extract.py) (4), [test_smoke_fixes.py](tests/test_smoke_fixes.py) (3), 2 testes Postgres novos em [test_postgres_redis_integration.py](tests/integration/test_postgres_redis_integration.py) e ajustes mínimos permitidos nos 3 arquivos existentes.

## Causa do texto vazio no corpus

- As páginas `https://site.getnet.com.br/` e `https://site.getnet.com.br/link-de-pagamento/` são WordPress renderizado no servidor sem tag `<main>` e com múltiplos `<article>` curtos usadas apenas em cards auxiliares (3 cards de 123–229 caracteres na home e 4 cards de 76–111 caracteres no Link de Pagamento), enquanto o conteúdo principal (6.383 caracteres na home e 3.351 no Link de Pagamento após remover menus, cabeçalhos e rodapés) fica no restante do `<body>`. O seletor antigo (`main or article or body`) escolhia o primeiro pequeno `<article>`, gerando menos de 300 caracteres (`no_content`). Já `.../pagamentos-pelo-whatsapp/` retorna HTTP 301 para `.../link-de-pagamento/` e passou a ser registrado como `redirect_duplicate`.

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `481 passed, 12 deselected in 46.26s`
- `python scripts/verify_phase13c.py`: `SUMMARY: 31/31 passed` (`PASS A0`–`A8`, `PASS S1.status`, `PASS C1`–`C3`, `PASS G1`–`G6`, `PASS E1`–`E3`, `PASS R1`–`R3`, `PASS Q1`–`Q6`, `INFO Q7.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/13C.md`.
