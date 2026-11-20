# STATUS DO REPOSITÓRIO

**Subfase:** 15B — Tokens de curta duração, notificação SSE ao lojista, alertas com runbook, descoberta na central/PDFs e 2ª amostra humana
**Base:** `fba3306` (fim da 15A) | **Python:** 3.13.3

## O que mudou (15B)

- **Aposentadoria da 15A e dependências:** removidos via `git rm` `docs/phase-prompts/15A.md` e `scripts/verify_phase15a.py`; `pypdf>=6,<8` adicionado em `requirements-dev.txt`.
- **Tokens de curta duração e rotação:** HS256 JWT (`src/core/tokens.py`), refresh tokens opacos com hash SHA-256 e detecção de reuso por família (`src/core/refresh_tokens.py`, tabela `refresh_tokens` em `src/core/db.py`), expiração opcional `:YYYY-MM-DD` em `API_KEYS` (`src/core/auth.py`), endpoints `/auth/token`, `/auth/refresh` e `/auth/revoke` (`src/main.py`), exigência de Bearer em produção e troca/renovação em memória JS em `/demo` e `/operator`.
- **Notificação SSE ao lojista entre réplicas:** `InMemoryEventBroker` e `RedisEventBroker` (`src/core/events.py`), publicação em `PATCH /tickets/{ticket_id}` sem texto de resposta, stream `GET /sessions/{session_id}/events` (`src/main.py`) e assinante SSE em `/demo`.
- **Alertas, métricas e runbook:** 11 regras em `deploy/alerts.yml`, testes promtool (disparo + silêncio por regra) em `deploy/alerts_test.yml`, `rule_files` em `deploy/prometheus.yml`, montagem em `docker-compose.yml`, runbook em pt-BR (`docs/RUNBOOK.md`) e 6 novas métricas exportadas desde a inicialização (`src/core/metrics.py`).
- **Portão de cobertura em confirmações:** `_plan_coverage_node` (`src/core/graph.py`) retorna `skipped` quando `action_confirmation != "none"`.
- **CI e evidência Compose:** `.github/workflows/ci.yml` inclui `promtool check/test rules`, troca de tokens e SSE entre réplicas; `scripts/compose_evidence.py` ganhou 8 checagens de produção/SSE.
- **Corpus e retrieval:** `extract_pdf_text()` e `Ingestor.discover()` (`--discover` CLI em `src/rag/ingest.py`), `--dataset` e subcomando `embed` em `src/rag/hybrid_eval.py`.
- **2ª amostra humana cega e calibração:** `write_human_sample2()` (`src/eval/human_validation.py`) gerou 40 itens (`g01`–`g40`, 20 reprovados / 20 aprovados, sem `answers.csv`) em `reports/human_validation_2/`; `run_judge_calibration` e relatórios aceitam múltiplos runs e avaliador único (`src/eval/judge_calibration.py`).
- **Novos testes (42 testes em 8 arquivos):** `test_tokens.py` (10), `test_refresh_tokens.py` (7), `test_auth_endpoints.py` (7), `test_events_sse.py` (5), `test_alerts.py` (3), `test_ingest_discovery.py` (5), `test_human_sample2.py` (3) e `test_coverage_confirmation.py` (2), além da limpeza em `tests/conftest.py`.

## Descoberta de corpus (`python -m src.rag.ingest --discover`)

- **URLs avaliadas (381):** `collected`: 97, `already_in_corpus`: 23, `out_of_scope`: 239, `off_allowlist`: 22 (`data/corpus/discovery.json`).
- **Novos registros em `data/corpus/pages.jsonl` (97):** 95 `ok` (90 HTML `/get-ajuda-*` e 5 PDFs em `/wp-content/uploads/`), 1 `redirect_duplicate`, 1 `http_error`, 0 `internal_document` armazenado.
- **Integridade:** as 33 linhas iniciais de `pages.jsonl` e `data/index/` permaneceram inalteradas; `manifest.json` totaliza 130 registros (127 `ok`).

## Verificações (`python scripts/verify_phase15b.py`)

```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS A4.frozen
PASS A5.existing_tests_only_grow
PASS S1.status
PASS A6.no_case_ids_in_code
PASS A7.dependencies
PASS K1.access_token_roundtrip
PASS K2.access_token_rejections
PASS K3.signing_key_rotation
PASS K4.production_refuses_weak_signing_keys
PASS K5.refresh_rotation_and_reuse
PASS K6.auth_endpoints_development
PASS K7.production_bearer_only_and_key_expiry
PASS K8.api_key_expiry_format
PASS K9.tokens_never_logged
PASS N1.event_broker_isolated_and_cross_replica
PASS N2.operator_reply_publishes_event_without_text
PASS N3.sse_endpoint
PASS AL1.alert_rules_and_runbook
PASS AL2.alert_metrics_exported_from_start
PASS AL3.rule_unit_tests_and_wiring
INFO AL4.promtool :: promtool not found: run by the reviewer and by CI
PASS C1.coverage_skipped_on_confirmation_turns
PASS D1.discovery_records
PASS D2.discovery_report_and_manifest
PASS D3.discovery_caps
PASS D4.corpus_committed :: 95 new ok records (5 PDF)
PASS E1.retrieval_dataset_option
PASS H1.second_sample_blind_and_balanced
PASS H2.second_sample_committed
PASS H3.calibration_on_second_sample
PASS W1.ci_compose_evidence_env
PASS G1.write_action_gate_unchanged
PASS G2.no_message_text_in_logs
PASS R1.production_fail_fast
PASS R2.trace_and_span_privacy
PASS R3.no_raw_pii_in_checkpoints
PASS R4.probes_left_tree_clean
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 584 passed, 13 deselected in 104.27s (0:01:44)
PASS Q6.new_tests_written :: {'tests/test_tokens.py': 10, 'tests/test_refresh_tokens.py': 7, 'tests/test_auth_endpoints.py': 7, 'tests/test_events_sse.py': 5, 'tests/test_alerts.py': 3, 'tests/test_ingest_discovery.py': 5, 'tests/test_human_sample2.py': 3, 'tests/test_coverage_confirmation.py': 2}
PASS Q8.legacy_modules_without_gate_justified :: 5 modules: ['tests.test_escalation_gate', 'tests.test_language_enforcement', 'tests.test_planner', 'tests.test_verifier_node', 'tests.test_write_action_flow']
PASS Q5.offline_eval
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data

SUMMARY: 47/47 passed
```

## Perguntas / divergências

- **Colisão de regex em `H1.second_sample_blind_and_balanced` (resolvida pelo revisor):** `scripts/verify_phase15b.py` foi atualizado pelo revisor para ignorar os cabeçalhos dos itens (`### gNN`) e a frase que cita o intervalo `g01` a `g40` antes de procurar vazamentos de `case_id` em `form.md`, passando `47/47`.
- **`AL4.promtool` e `Q7.integration_suite`:** ficam para execução no CI e no ambiente do revisor (`promtool`, `TEST_DATABASE_URL` e `TEST_REDIS_URL` não estão configurados localmente).
