# STATUS DO REPOSITÓRIO

**Data de geração**: 09/11/2026 | **Branch**: `main`

## Resumo

- O sistema foi construído em fases. Cada fase tem um prompt em `docs/phase-prompts/`, um verificador em `scripts/verify_phase*.py` (roda sem chave de API e reroda os verificadores anteriores) e um commit próprio; o CI roda ruff, pytest, o build da imagem e um smoke test em `/health` a cada push.
- Fases 1 a 8: supervisor com function calling, RAG sobre páginas oficiais, autenticação, memória, transbordo humano, avaliação com juiz, observabilidade e Docker.
- Fase 9: correções da auditoria simulada (cartão e CPF fora do disco, chamada de ferramenta órfã, mock sem conta inventada, imagem em produção, logs sem texto da conversa).
- Fase 10: clima e câmbio por API, guardrail híbrido (padrões e classificador por LLM), conjunto de avaliação v2 e execuções com modelo real.
- Fase 11: resposta inválida do classificador passa a bloquear; holdout do guardrail commitado antes da única execução (`author-1`); o runner registra a camada do guardrail por turno; tier e modelos nos relatórios; documentação reorganizada.
- Resultados vigentes: README e `reports/`. Resultados antigos: `docs/history.md`.
- Registro completo de cada fase (saída bruta dos verificadores, testes, perguntas ao SPEC): `docs/status-history.md`.

---

### Fase 12C: Notificação do Operador, Retomada e Corte do Histórico

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 12C:
```text
INFO python 3.13.3
PASS C0.py311_syntax
PASS C1.supervisor_prompt
PASS C2.env_example
PASS C9.demo_polls
PASS C10.tests_written :: 14 tests
PASS C13.author_files_not_committed :: 3 author file(s) present, uncommitted
PASS E2.scope
PASS C12.decisions_untouched
PASS C11.status
PASS C2.settings
PASS C3.notifier
PASS C5.ticket_columns
PASS C4.tool_notifies
PASS C6.operator_resume
PASS C6.gate_releases_delivered
PASS C8.history_trim
PASS C7.api
PASS C7.api_end_to_end
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q0.verify_phase11g
PASS Q0.verify_phase12a
PASS Q0.verify_phase12b
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 375 passed in 35.63s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 78/78 passed
```

#### Commit base:
`d1d92511d17eeaf082f1f6238d49647392908abb`

#### Não feito:
Nada pendente nesta subfase.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
Adicionados `src/core/notifier.py` (`NotificationResult`, `build_payload`, `OperatorNotifier`, `get_notifier`, `reset_notifier`) e a suíte `tests/test_operator_hitl.py` (14 testes offline); adicionadas `OPERATOR_WEBHOOK_URL`, `OPERATOR_WEBHOOK_TIMEOUT_S`, `PUBLIC_BASE_URL` e `MAX_HISTORY_MESSAGES` em `src/config.py` e `.env.example`; adicionada a métrica `getnet_operator_notifications_total{status}` em `src/core/metrics.py`; adicionadas as colunas/migração `notified_at`/`notification_status` e `record_notification` em `src/core/tickets_db.py`; conectada notificação best-effort pós-persistência em `escalate_to_human` (`src/tools/agent_tools.py`); adicionados `operator_event` em `src/core/state.py`, entrada condicional `START` -> `operator_resume` -> `supervisor`, liberação no `handoff_gate` para tickets já entregues, `resume_after_operator` (com fallback verbatim e `_close_dangling_tool_calls`), `session_messages` e `_trim_history` com `RemoveMessage` em `src/core/graph.py`; atualizados `PATCH /tickets/{ticket_id}` e adicionado `GET /sessions/{session_id}/messages` em `src/main.py`; implementado polling em `/sessions/{id}/messages` no cliente `src/static/demo.html`.

### Fase 12B: Busca Híbrida com Reranker

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 12B:
```text
INFO python 3.13.3
PASS B0.py311_syntax
PASS B1.reranker_prompt_preregistered
PASS B1.no_regex_new_code
PASS B10.no_runs_yet
PASS E2.scope
PASS B12.decisions_untouched
PASS B11.status
PASS B6.env_example
PASS B13.tests_written :: 13 tests
PASS B6.settings
PASS B2.bm25_matches_reference
PASS B3.reranker_outcomes
PASS B4.dense_path_unchanged
PASS B5.hybrid_matches_reference :: 40 reranker calls, 8 gated
PASS B5.fallback_to_dense
PASS B7.rerank_log
PASS B7.production_wiring
PASS B8.rerank_tokens_in_knowledge_usage
PASS B9.measurement_module
PASS B9.cli
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q0.verify_phase11g
PASS Q0.verify_phase12a
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 361 passed in 44.32s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 79/79 passed
```

#### Commit base:
`70d4b1ea793aadffe4bf01ca3117186220036e9e`

#### Não feito:
Nada pendente nesta subfase (as execuções com modelo real `rerank-1` a `rerank-3` e a geração de `reports/retrieval_hybrid.*` ficam a cargo do autor após o commit).

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
Adicionados `src/rag/lexical.py` (`fold`, `tokenize`, `BM25Index`), `src/rag/reranker.py` (`LLMReranker`, `RerankVerdict`, `PassageRelevance`, `RerankResult`, `format_rerank_input`, `load_reranker_prompt`), `src/rag/hybrid_eval.py` (`load_inputs`, `build_retriever`, `run_hybrid`, `dense_baseline`, `metrics`, `hybrid_report` e CLI `run`/`report`) e a suíte `tests/test_hybrid_retrieval.py` (13 testes offline); adicionado `VectorIndex.scores` em `src/rag/index.py`; atualizado `src/rag/retriever.py` com busca híbrida (portão semântico + fusão RRF denso/BM25 + reranker por LLM + fallback denso) preservando o caminho `reranker=None` idêntico ao anterior e ligando `get_knowledge_retriever()`; adicionadas as 7 configurações `RAG_RERANK_*`/`RAG_*` em `src/config.py` e `.env.example`; somados os tokens de uso do reranker ao `specialist_usage` de `KnowledgeAgent` em `src/agents/specialists.py`.

### Fase 12A: Amostra para Validação Humana e Holdout de Roteamento

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 12A:
```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.provider_branches_removed
PASS A2.readme_one_sentence
PASS A3.routing_holdout
PASS E2.scope
PASS A12.decisions_untouched
PASS A11.status
PASS A10.unsupported_providers
PASS A4.module_api
PASS A5.sample_recomputed :: eligible 72, allocation {'escalation': 2, 'knowledge': 9, 'multi_intent': 1, 'multi_turn': 3, 'off_topic': 2, 'pii': 1, 'public_data': 5, 'support': 4, 'uncovered': 3, 'web': 0}
PASS A5.functions_match_reference
PASS A6.generated_by_cli
PASS A7.form_blind_and_complete :: 125940 chars
PASS A8.answers_template
PASS A8.no_answers_yet
PASS A9.agreement_matches_reference
PASS A9.cli_agreement
PASS A13.tests_written :: 10 tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q0.verify_phase11g
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 348 passed in 29.19s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 76/76 passed
```

#### Commit base:
`d2de4ffa84a1c9c0917ef1ba8dffa961a6132c75`

#### Não feito:
Nada pendente nesta subfase (preenchimento do `answers.csv` e execução de `human-agreement` ficam a cargo do autor após o commit).

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
Ramos `openai` e `anthropic` removidos de `src/core/llm.py`, `tests/test_providers.py` e `README.md`; módulo `src/eval/human_validation.py`, subcomandos `human-sample` e `human-agreement` em `src/eval/__main__.py`, amostra cega gerada em `reports/human_validation/` (`sample.json`, `form.md`, `answers_template.csv`) e suíte `tests/test_human_validation.py` adicionada.

### Fase 11G: README Reorganizado

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11G:
```text
Python 3.13.3
INFO python 3.13.3
PASS G0.py311_syntax
PASS G1.readme_from_prompt :: 286 lines
PASS G2.structure
PASS G3.claims_evidence :: 22 rows, 82 paths
PASS G6.tier_and_models
PASS G7.authorship
PASS G9.history_unchanged
PASS G10.status
PASS E2.scope
PASS G8.2c.S3
PASS G8.3c.S5
PASS G8.3c.S5.48x
PASS G8.5a.S3
PASS G8.5b.S1
PASS G8.5c.S1
PASS G8.6a.S1
PASS G8.6b.S2
PASS G8.6c.S1
PASS G8.6c.S1.run
PASS G8.6c.S2
PASS G8.6d.S3
PASS G8.6e.S1-S2
PASS G8.6f.C4
PASS G8.6f.C5
PASS G8.6f.C6
PASS G8.6f.C8
PASS G8.7a.L0
PASS G8.7b.P0
PASS G8.7c.M0
PASS G8.7d.W0
PASS G8.8a.A0.ci
PASS G8.8a.A0.compose
PASS G8.8b.R2
PASS G8.8b.R4
PASS G8.8d.E3
PASS G8.8e.R2
PASS G8.8e.R3
PASS G8.8f.F1
PASS G8.8f.F2
PASS G8.8f.F4
PASS G8.8f.F5
PASS G8.9b.B5
PASS G8.9b.B6
PASS G8.9b.R1
PASS G8.9c.C8
PASS G8.9d.D9
PASS G8.9e.G8
PASS G8.9e.G9
PASS G8.9f.H10
PASS G8.9g.J2
PASS G8.9g.J3
PASS G8.9g.J3.full1
PASS G8.9g.J4
PASS G8.9g.J6
PASS G8.9g.J8
PASS G8.10i.I2
PASS G8.10i.I3
PASS G8.11a.A1
PASS G8.11a.A2
PASS G8.11a.A1.failopen
PASS G8.old_wording_gone
PASS G4.numbers_match_reports
PASS G5.demo_matches_records :: 6 transcripts
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 338 passed in 25.85s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 120/120 passed
ba480dfcb4579d98b591c6eebadbcc9c1e846d2c
```

#### Commit base:
`ba480dfcb4579d98b591c6eebadbcc9c1e846d2c`

#### Não feito:
Nada pendente.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
README.md reorganizado conforme o texto ditado em docs/phase-prompts/11G.md; resultados vigentes mantidos, histórico preservado em docs/history.md.

### Fase 11F: Registro por Fase e Resultados Antigos Movidos

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11F:
```text
INFO python 3.13.3
PASS F0.py311_syntax
PASS F1.status_history :: 4109 lines
PASS F2.history
PASS F3.status_summary
PASS F4.old_status_checks_on_history
PASS F5.no_candidato
PASS E2.scope
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 338 passed in 24.73s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 63/63 passed
```

#### Commit base:
`c6a3aeb899556b77fa994614da7adf9f78d148ef`

#### Não feito:
Nada pendente.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
O registro detalhado por fase foi movido de `docs/STATUS.md` para `docs/status-history.md`; os resultados históricos foram movidos do `README.md` para `docs/history.md`; o topo de `docs/STATUS.md` foi substituído pelo resumo gerado pelo script.

