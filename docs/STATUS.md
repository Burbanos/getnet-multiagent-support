# STATUS DO REPOSITÓRIO

**Data de geração**: 07/11/2026 | **Branch**: `main`

---

### Fase 6F: Alinhamento de Documentação e Interface com Capacidades Reais

#### Verificação Fase 6F (`python scripts/verify_phase6f.py`):
```text
PASS C1.readme_no_false_claims
PASS C2.demo_no_confidence
PASS C3.official_matrix
PASS C4.glossary
PASS C5.ticket_format_and_cost
PASS C6.retrieval_claim
PASS C7.status
PASS C8.results_section_kept
PASS Q0.runner_judge_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 194 passed in 18.15s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 32/32 passed
```

#### Commit Base da Fase 6F (`git rev-parse HEAD`):
```text
6aa2cbd19585744a4f15b1a2e3518302435ed215
```

#### Alterações Realizadas na Fase 6F:
- **Interface Visual (`src/static/demo.html`)**:
  - Removido o cartão de "Confiança" (`#confidenceMetric`) e o código JavaScript associado, preservando o campo `X-API-Key` e a métrica de custo (`#costMetric`).
- **Alinhamento do README (`README.md`)**:
  - Removidas alegações inverídicas de "Confiança Dinâmica", "Métrica de Confiança" e "100% de precisão determinística".
  - Corrigido o cálculo de custos em USD para clarificar que `estimated_cost_usd` é retornado como `null` e a precificação entra na Fase 7.
  - Atualizadas as métricas de tokens no painel de observabilidade para refletir os campos reais: `input_tokens`, `output_tokens`, `total_tokens` e `tokens_by_agent`.
  - Corrigido o padrão de identificadores de chamados no banco para `GET-TKT-YYYYMMDD-<10 hexadecimais>` (gerado como `uuid4().hex[:10]`).
  - Removida a subseção de "Avaliação Automatizada de Roteamento" que referenciava o dataset descontinuado `eval_dataset.json`.
  - Atualizada a seção 3D com menção explícita à margem estreita de 0.04 no limiar de retrieval e às abstenções observadas na execução `full-1`.
  - Substituída a Seção 6 pela matriz exata com ferramentas e fontes medidas na execução `full-1` (incluindo reprovação do cenário 8 por idioma).
  - Atualizadas as respostas do Glossário de Defesa Técnica (perguntas 1, 3, 4 e 5) com dados honestos e verificáveis.

#### Status do Projeto e Próximos Passos:
- A **Fase 6F** está formalmente concluída com todos os critérios de aceitação aprovados.
- A próxima etapa é a **Fase 7: Observabilidade e Governança de Custos** (tabela de precificação de tokens em USD, telemetria detalhada e governança financeira).

---

### Fase 6E: Resultados da Avaliação no Repositório e no README

#### Verificação Fase 6E (`python scripts/verify_phase6e.py`):
```text
PASS D1.run_file_unchanged
PASS D2.judge_file_unchanged
PASS D3.report_matches_raw
PASS S1.readme_numbers_match_report
PASS S2.readme_caveats
PASS S3.readme_wording
PASS S4.status
PASS Q0.runner_judge_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 194 passed in 17.65s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 30/30 passed
```

#### Commit Base da Fase 6E (`git rev-parse HEAD`):
```text
ab87a46a5e2e6b402baee21059e02cdbc61b0847
```

#### Alterações Realizadas na Fase 6E:
- **Relatório Final da Avaliação (`reports/eval_full-1.json` e `reports/eval_full-1.md`)**:
  - Regenerado o relatório estruturado integrando a segunda rodada do juiz (`reports/eval_runs/full-1.judge.jsonl`), executada sobre os trechos integrais do índice sem truncamento.
  - Consolidada a seção do juiz: 63 casos julgados (0 erros), `grounded_mean = 4.95`, `answers_mean = 4.68`, `abstention_precision = 76.9%`, `abstention_recall = 76.9%`, com mapeamento de discordâncias (`k07, k16, k17`) e erros de abstenção.
- **Documentação de Métricas no README (`README.md`)**:
  - Incorporada a tabela exata de resultados da avaliação recalculada pelo revisor a partir dos dados brutos.
  - Documentados os limites e falhas conhecidas (execução única, limitações do juiz compacto, falta de registro para chamadas web e falhas determinísticas).
  - Ajustada a frase sobre os resultados de `search_web` ("não ficam no registro da execução").

#### Status do Projeto e Próximos Passos:
- A **Fase 6** está formalmente concluída com todos os critérios de aceitação aprovados e dados brutos de avaliação comitados no repositório.
- A próxima etapa é a **Fase 7: Observabilidade e Governança de Custos** (tabela de precificação de tokens em USD, telemetria detalhada e governança financeira).

---

### Fase 6D: Trechos Completos no Juiz e Correções de Documentação

#### Verificação Fase 6D (`python scripts/verify_phase6d.py`):
```text
PASS J0.index_has_long_chunks
PASS R1.observe_turn_2000
PASS J1.api
PASS J2.full_passages
PASS J3.load_chunk_texts
PASS J4.still_blind
PASS S1.readme_no_false_quota
PASS S2.readme_run_example
PASS S3.readme_judge_limits
PASS S4.status_next_phase
PASS D1.flawed_judge_file_removed
PASS Q0.runner_judge_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 194 passed in 16.70s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 33/33 passed
```

#### Commit Base da Fase 6D (`git rev-parse HEAD`):
```text
636c9baba416459fdf0006844d5562687c569b83
```

#### Testes Criados e Alterados na Fase 6D:
- **Criados em `tests/test_eval_runner_judge.py`**:
  - `test_build_judge_input_full_passages_from_index`: valida que `build_judge_input` resolve `chunk_id` no índice carregado recuperando o texto integral da passagem para avaliação de `grounded`, adotando o texto guardado para chunks inexistentes ou nulos, sem vazar IDs, categorias ou rótulos esperados.
  - `test_load_chunk_texts_caching_and_custom_path`: valida que `load_chunk_texts()` mantém cache em memória apenas para o caminho padrão (`data/index/chunks.jsonl`) e lê caminhos temporários customizados de forma independente sem poluir o cache.
- **Alterados em `tests/test_eval_runner_judge.py`**:
  - `test_observe_turn_truncation_and_fields`: atualizado o tamanho limite do texto de trechos recuperados de 600 para 2000 caracteres.

#### Próximos Passos:
- **Fase 6E**: Execução do juiz LLM pelo usuário com a chave de API sobre os trechos completos da execução `full-1`, publicação do log bruto `reports/eval_runs/full-1.judge.jsonl`, consolidação final dos relatórios estruturados e documentação das métricas no README.

---

### Fase 6C: Correções do Juiz, Padrões no Tier Gratuito e Execução full-1

#### Verificação Fase 6C (`python scripts/verify_phase6c.py`):
```text
PASS P1.reviewer_prompts
PASS S1.readme_models
PASS S2.readme_judge_caveat
PASS R0.settings_defaults
PASS R0.env_and_compose
PASS R0.factory
PASS J0.api
PASS J1.list_content_parsed
PASS J1.response_text
PASS J2.error_code
PASS J3.stops_on_consecutive_errors
PASS R1.temp_tickets_dir_removed
PASS D1.run_file_unchanged
PASS D1.run_file_complete
PASS D2.buggy_judge_file_removed
PASS D3.report_matches_raw
PASS Q0.runner_judge_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 192 passed in 19.13s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q5.cli_report_missing_results

SUMMARY: 38/38 passed
```

#### Commit Base da Fase 6C (`git rev-parse HEAD`):
```text
3074ecfb0df5e3dc5f766a7bd8b6f4870b4a4815
```

#### Testes Criados e Alterados na Fase 6C:
- **Alterados**:
  - `tests/test_eval_runner_judge.py` (adicionados 4 novos testes unitários, totalizando 13 testes):
    - `test_judge_case_list_blocks`: valida que respostas de modelos da família Gemini 3 em formato de lista de blocos têm seus blocos de texto extraídos e concatenados via `response_text`, ignorando blocos não-texto (`thinking`, `image_url`), e obtendo avaliação correta.
    - `test_error_code_extraction_and_no_leak`: valida extração de códigos HTTP/gRPC (`code` ou `status_code`) em exceções encadeadas (`__cause__`), prefixos numéricos em strings ("429") e retorno de `None` para erros genéricos, garantindo que mensagens de erro ou segredos de infraestrutura nunca vazem nos dicionários de julgamento.
    - `test_run_judge_stops_on_three_consecutive_errors_resets_on_ok`: valida que o juiz aborta após 3 erros consecutivos de qualquer tipo (seja resposta não-analisável ou exceção do provedor) e que qualquer status "ok" reseta o contador.
    - `test_run_eval_deletes_temp_tickets_dir`: valida que `run_eval` remove com sucesso o diretório temporário `eval_tickets_*` ao final da execução e restaura `settings.TICKETS_DB_PATH`.
  - `tests/test_providers.py`:
    - Atualizado `test_provider_defaults` para validar os novos padrões do tier gratuito (`LLM_MODEL = "gemini-3.5-flash-lite"`, `LLM_FALLBACK_MODEL = "gemini-3.1-flash-lite"`).

---

### Fase 6B: Executor com Modelo Real, Juiz LLM e Métricas do Juiz

#### Verificação Fase 6B (`python scripts/verify_phase6b.py`):
```text
PASS R0.api
PASS R0.settings
PASS R0.no_regex_no_tests_import
PASS R1.observe_turn
PASS R2.run_case_multi_turn
PASS R2.run_case_error
PASS R3.resume_and_last_wins
PASS R3.tickets_in_temp_db
PASS R4.stops_on_repeated_quota_errors
PASS R4.no_key_aborts
PASS R4.max_cases_and_only
PASS J0.judge_prompt_is_reviewers
PASS J1.judge_never_sees_expectations
PASS J2.parse_judgment
PASS J3.judge_case
PASS J3.unparseable
PASS J4.should_judge
PASS J4.run_judge_resume_and_skip
PASS M1.judge_metrics_match_reference
PASS M1.no_judgments_is_null
PASS M2.report_with_judge
PASS S1.readme_fixes
PASS S2.readme_run_docs
PASS Q0.runner_judge_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 188 passed in 19.13s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q5.cli_report
PASS Q6.cli_run_without_key

SUMMARY: 45/45 passed
```

#### Commit Base da Fase 6B (`git rev-parse HEAD`):
```text
4778cce9e55bb563a0d0dc24c9ec647760d4b52e
```

#### Testes Criados e Alterados na Fase 6B:
- **Criados**:
  - `tests/test_eval_runner_judge.py` (9 testes unitários):
    - `test_observe_turn_truncation_and_fields`: valida conjunto estrito de 14 chaves retornadas por `observe_turn`, truncamento de textos recuperados a 600 caracteres e extração de prioridade de chamados.
    - `test_run_case_multi_turn_and_sanitized_errors`: valida que execuções multi-turno preservam o mesmo `session_id` e que mensagens/textos brutos de exceções nunca vazam no payload de resultado.
    - `test_run_eval_resumption_and_temp_tickets_db`: valida que `run_eval` pula casos já avaliados com status `ok`, regera casos com erro, adota a regra de que a última linha prevalece e isola o banco `tickets.db` em pasta temporária fora de `data/`.
    - `test_run_eval_stops_on_three_consecutive_quota_errors`: valida que 3 erros consecutivos de cota (`LLMUnavailableError`) interrompem preventivamente a execução (`stopped_early: True`).
    - `test_run_eval_reraises_llm_not_configured_error`: valida que a ausência de chave (`LLMNotConfiguredError`) não é mascarada e sobe imediatamente na execução.
    - `test_build_judge_input_isolation`: valida que o payload enviado ao juiz contém apenas as mensagens do lojista, resposta final e evidências do último turno, sem vazar IDs de teste, categorias ou rótulos esperados (`expect`).
    - `test_parse_judgment_markdown_blocks_and_invalid_formats`: valida parsing de JSON envolto em blocos markdown, e rejeição estrita (via `ValueError`) para tipos inválidos (ex.: booleano onde se espera inteiro de 1 a 5).
    - `test_judge_case_and_run_judge_flow`: valida execução do juiz com modelo de teste, retorno de `unparseable` para saídas não estruturadas, filtro `should_judge` (exclusão de erros, handoff pendente e categoria safety) e retomada incremental em `run_judge`.
    - `test_judge_metrics_abstention_and_disagreements`: valida cálculo estatístico de precisão/recall de abstenção, lista de erros de abstenção e detecção de discordâncias entre o juiz e as checagens determinísticas de fatos.

---

### Fase 6A: Harness de Avaliação, Checagens Determinísticas e Subconjunto Offline no CI

#### Verificação Fase 6A (`python scripts/verify_phase6a.py`):
```text
PASS D1.cases_reviewer_owned :: 69 cases, sha 2d7d8e746a23
PASS D2.composition
PASS D3.old_dataset_removed
PASS R0.api
PASS R0.no_regex_no_tests_import
PASS R1.load_cases
PASS R1.validation
PASS R2.word_lists
PASS R2.detect_language
PASS R3.evaluate_case_matches_reference
PASS R4.aggregate_matches_reference
PASS R4.cost_is_null
PASS R5.write_report
PASS O1.offline_subset
PASS O2.forbidden_model_detects_calls
PASS S1.readme
PASS Q0.harness_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 179 passed in 19.73s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q5.cli_offline :: offline: 6/6 passed

SUMMARY: 36/36 passed
```

#### Commit Base da Fase 6A (`git rev-parse HEAD`):
```text
3c09da875bd09b393b445b7507a6597456054c11
```

#### Testes Criados, Alterados e Removidos na Fase 6A:
- **Criados**:
  - `tests/test_eval_offline.py`:
    - `test_eval_offline_regression_subset`: executa `run_offline` sobre os 6 casos da categoria `safety` com `offline: True` de `data/eval/cases.jsonl`, validando aprovação determinística de 100% com exatamente 0 chamadas a modelos LLM.
  - `tests/test_eval_harness.py` (9 testes unitários):
    - `test_load_cases_validation_rejections`: valida rejeição estrita via `ValueError` para esquemas e semânticas inválidas (IDs duplicados, categoria fora da lista, idioma fora de `pt|en`, turnos vazios ou em branco, agente/ferramenta desconhecida, offline fora de `safety`, chave ausente em `expect`).
    - `test_detect_language`: valida classificação por contagem léxica entre Português (`pt`), Inglês (`en`) e desempate/ausência (`unknown`).
    - `test_evaluate_case_individual_checks`: valida individualmente cada uma das 9 checagens determinísticas (`routing_ok`, `tools_ok`, `escalation_ok`, `priority_ok`, `blocked_ok`, `sources_ok`, `facts_ok`, `facts_none_ok`, `language_ok`) para cenários `True`, `False` e `None`.
    - `test_evaluate_case_facts_any_groups`: valida que todos os grupos de fatos alternativos de `facts_any` são exigidos, com normalização de maiúsculas/minúsculas e espaços múltiplos.
    - `test_evaluate_case_error_and_empty_turns`: valida que resultados com `status != "ok"` ou lista de turnos vazia produzem checagens `None` e `passed = False`.
    - `test_aggregate_metrics_excludes_errors`: valida que execuções com erro de infraestrutura são computadas em `n_errors` e seus IDs listados em `error_ids`, sem poluir os denominadores das taxas de métricas.
    - `test_aggregate_percentiles_tokens_and_cost`: valida cálculo dos percentis p50 e p95 de latência por posição mais próxima (`ceil(p*n)-1`), soma e média de tokens, `estimated_cost_usd: None` e nota de precificação da Fase 7.
    - `test_write_report_json_and_markdown`: valida escrita em disco e estrutura completa dos relatórios em JSON e Markdown.
    - `test_cases_sha256_stability`: valida estabilidade e determinismo do hash SHA256 independentemente da ordem das chaves do dicionário.
- **Alterados**:
  - `tests/test_eval_judge.py`: removida a constante `DATASET_PATH` e o teste `test_eval_dataset_schema`, mantendo apenas o teste de segurança de cabeçalho `test_x_api_key_security_header`.
- **Removidos**:
  - `data/eval_dataset.json` (removido do repositório; substituído por `data/eval/cases.jsonl`).

---

### Fase 5C: Escalonamento Automático por Abstenção Repetida e Correções do Portão

#### Verificação Fase 5C (`python scripts/verify_phase5c.py`):
```text
PASS S1.readme
PASS S2.config_documented
PASS R0.api
PASS R0.settings_and_note
PASS E1.counter_increments
PASS E1.escalates_on_second
PASS E1.then_handoff_gate
PASS E2.grounded_answer_resets
PASS E3.small_talk_does_not_reset
PASS E4.zero_disables
PASS E5.no_double_ticket
PASS E6.failed_auto_ticket_no_note
PASS E7.counter_per_user
PASS G1.followups_reach_operator
PASS G3.normal_service_after_delivery
PASS G1.append_bounded
PASS G2.no_double_delivery
PASS Q0.abstention_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 170 passed in 18.39s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 35/35 passed
```

#### Commit Base da Fase 5C (`git rev-parse HEAD`):
```text
fa8ccf04aa592538e702bdae6c8ea86f65ed2b10
```

#### Testes Criados na Fase 5C:
`tests/test_abstention_escalation.py` (10 novos testes unitários):
- `test_abstention_counter_increments_on_first_abstention`: valida que o contador `consecutive_abstentions` incrementa para 1 após a primeira consulta do Knowledge Agent sem fontes, sem criar ticket.
- `test_auto_escalation_on_second_abstention_with_note_and_pending_ticket`: valida que ao atingir 2 abstenções consecutivas é criado um chamado automático, anexando a nota oficial padronizada (`AUTO_ESCALATION_NOTE`) ao final da resposta, gravando `pending_ticket_id`, zerando o contador e adicionando `escalate_to_human` a `tools_used`.
- `test_grounded_answer_resets_abstention_counter`: valida que qualquer consulta com fontes encontradas zera o contador `consecutive_abstentions` para 0.
- `test_small_talk_does_not_reset_abstention_counter`: valida que turnos sem acionamento do Knowledge Agent (como saudações) não alteram nem resetam o contador de abstenções.
- `test_zero_limit_disables_auto_escalation`: valida que configurar `ESCALATE_AFTER_ABSTENTIONS = 0` desativa completamente o mecanismo de escalonamento automático.
- `test_turn_with_supervisor_escalation_does_not_create_double_ticket`: valida que quando o supervisor já solicitou escalonamento no turno, o nó `abstention_check` não abre um segundo ticket duplicado e zera o contador.
- `test_failed_ticket_creation_does_not_append_note_and_keeps_counter`: valida que falhas de persistência na abertura automática não anexam a nota enganosa de ticket aberto e mantêm o contador de abstenções intacto.
- `test_abstention_counter_isolated_per_user`: valida que o contador `consecutive_abstentions` permanece estritamente isolado por usuário no checkpointer.
- `test_followup_message_while_waiting_appended_to_ticket_transcript_masked`: valida que mensagens enviadas pelo cliente enquanto o ticket aguarda resposta passam pelo guardrail (número de cartão mascarado) e são anexadas ao `transcript` do ticket no banco via `append_customer_message`.
- `test_mark_delivered_false_does_not_deliver_again_and_resumes`: valida que se `mark_delivered` retornar `False` (resposta já entregue concorrentemente), a resposta não é duplicada, o `pending_ticket_id` é limpo e o fluxo retoma o atendimento convencional (`resumed`).

#### Testes Ajustados na Fase 5C:
Nenhum teste existente precisou ser alterado (`git diff tests/` afeta apenas o novo arquivo `tests/test_abstention_escalation.py`).

---

### Fase 5B: Portão de Transbordo (Handoff Gate) e Entrega de Resposta no Chat

#### Verificação Fase 5B (`python scripts/verify_phase5b.py`):
```text
PASS S1.readme
PASS S2.supervisor_prompt
PASS S3.no_interrupt_left_half_done
PASS R0.api
PASS R0.fixed_messages_no_promises
PASS T1.ticket_id_entropy
PASS T2.owner_required
PASS T3.conditional_update
PASS T4.mark_delivered_once
PASS F1.pending_set
PASS F2.pending_turn_no_llm
PASS F2.message_masked_and_kept
PASS F3.reply_delivered_once
PASS F4.normal_service_after_delivery
PASS F5.closed_without_reply_resumes
PASS F6.reply_then_closed_still_delivered
PASS F7.pending_is_per_user
PASS F8.forced_escalation_sets_pending
PASS F9.failed_ticket_no_pending
PASS F10.guardrail_runs_before_gate
PASS F11.pending_survives_restart
PASS A1.api_handoff_metadata
PASS Q0.handoff_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 160 passed in 17.01s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 39/39 passed
```

#### Commit Base da Fase 5B (`git rev-parse HEAD`):
```text
31a18ece1de77d52a4ad1821691afa13558ca5c7
```

#### Testes Criados na Fase 5B:
`tests/test_handoff.py` (12 novos testes unitários):
- `test_ticket_creates_pending_ticket_id`: valida que a criação de ticket define `pending_ticket_id` no estado conversacional do checkpointer.
- `test_pending_turn_returns_fixed_message_without_llm_and_masks_pii`: valida que mensagem com ticket aberto devolve mensagem fixa sem chamar o LLM (`llm_model: None`, `tokens: None`), atribuindo `agent_type = "HumanHandoff"`, e mascara dados sensíveis (PII de cartão) gravando na memória.
- `test_operator_reply_delivered_once_and_marks_delivered`: valida entrega única da resposta do operador com prefixo padronizado, gravação de `delivered_at` no SQLite, limpeza de `pending_ticket_id` e status `delivered`.
- `test_normal_service_resumes_after_delivery`: valida retorno automático ao fluxo padrão do assistente nos turnos seguintes à entrega da resposta humana (`handoff: None`, chamada normal ao LLM).
- `test_closed_without_reply_resumes_normal_service`: valida que fechamento do ticket sem resposta pelo operador limpa a pendência, define `handoff: {"status": "resumed"}` e roteia no mesmo turno para o supervisor do bot.
- `test_reply_then_closed_before_delivery_still_delivered`: valida que ticket respondido e posteriormente fechado antes da visualização pelo cliente ainda entrega a resposta humana (`status: "delivered"`).
- `test_pending_ticket_isolated_per_user`: valida que `pending_ticket_id` permanece estritamente isolado por usuário mesmo compartilhando o mesmo `session_id`.
- `test_forced_escalation_sets_pending_ticket_id`: valida que o escalonamento forçado por excesso de passos (`MAX_SUPERVISOR_STEPS`) também define `pending_ticket_id`.
- `test_failed_ticket_creation_does_not_set_pending`: valida que falhas de persistência na criação de chamados não definem `pending_ticket_id` no estado.
- `test_guardrail_blocks_before_handoff_gate`: valida que o nó do guardrail executa antes do portão de transbordo e bloqueia injeções de prompt imediatamente sem acionar o portão.
- `test_pending_ticket_survives_restart_with_sqlite_checkpointer`: valida que a pendência do chamado sobrevive a reinicializações completas do serviço através do checkpointer `SqliteSaver`.
- `test_ticket_fixes_entropy_validation_and_concurrency`: valida entropia do sufixo de 10 hexadecimais maiúsculos, recusa de `user_id` vazio, `mark_delivered` retornando `True` apenas na primeira chamada e recusa de leituras desatualizadas em `update_ticket` (`TicketTransitionError`).

#### Testes Ajustados na Fase 5B:
Nenhum teste existente precisou ser alterado (`git diff tests/` afeta apenas o novo arquivo `tests/test_handoff.py`).

---

### Fase 5A: Ciclo de Vida do Ticket, Histórico, Resposta do Operador e Persistência Honesta

#### Verificação Fase 5A (`python scripts/verify_phase5a.py`):
```text
PASS S1.no_silent_fallback
PASS S2.config_documented
PASS S3.readme_claims
PASS S3.readme_tickets
PASS S4.supervisor_prompt
PASS R0.api
PASS R0.settings
PASS R1.create_and_get
PASS R1.message_no_promises
PASS R2.priority_validated
PASS R2.list_filters
PASS R3.lifecycle
PASS R3.invalid_transitions
PASS R3.missing_ticket
PASS R4.migrates_old_schema
PASS R5.fails_loudly
PASS R6.transcript_snapshot
PASS R7.tool_schema
PASS R8.graph_ticket
PASS R9.persistence_failure_surfaces
PASS R10.forced_escalation
PASS A1.patch_operator_only
PASS A2.patch_validation
PASS A3.patch_lifecycle
PASS A4.customer_sees_reply
PASS A5.list_by_status
PASS A6.no_internal_paths
PASS A7.startup_opens_tickets_db
PASS Q0.ticket_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 148 passed, 1 warning in 15.10s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 44/44 passed
```

#### Commit Base da Fase 5A (`git rev-parse HEAD`):
```text
e84765fd17a9a08afdb0ee386d1ef7cbeed7b94b
```

#### Testes Criados na Fase 5A:
`tests/test_tickets.py` (9 novos testes unitários):
- `test_create_ticket_with_session_and_transcript`: valida persistência de `session_id`, `priority`, `reason` sanitizado, `transcript` estruturado e mensagem sem promessas enganosas de tempo ou fila.
- `test_create_ticket_invalid_priority_raises`: valida rejeição de prioridades fora de `("standard", "high")` levantando `ValueError`.
- `test_tickets_repository_migrates_old_schema`: valida migração via `ALTER TABLE` de schemas legados (adicionando `session_id`, `transcript`, `operator_reply`, `operator_id`, `answered_at`) sem perda de dados.
- `test_tickets_repository_unusable_path_raises`: valida fail-fast ruidoso quando o caminho do banco for inacessível (sem fallback para `/tmp` ou memória).
- `test_ticket_lifecycle_transitions`: valida ciclo estrito `open -> in_progress -> answered -> closed` e rejeição de transições ilegais (`TicketTransitionError`) ou parâmetros inválidos (`ValueError`).
- `test_transcript_snapshot_extraction_and_clamping`: valida extração de mensagens `user` e `assistant`, exclusão de `ToolMessage` e `AIMessage` vazias, truncamento de mensagens a 2000 caracteres e limitação às 20 mais recentes.
- `test_graph_escalation_flow_masked_transcript`: valida fluxo completo no orquestrador registrando ticket com prioridade alta e transcript auditável com cartões de crédito mascarados pelo guardrail.
- `test_graph_persistence_failure_handled`: valida que falhas de banco de dados na ferramenta `escalate_to_human` não geram ticket fantasma no estado (`ticket=None`, `escalate_to_human=False`) e retornam status de erro padronizado.
- `test_patch_tickets_api_and_customer_view`: valida `PATCH /tickets/{id}` com controle estrito por perfil (`operator`), validações 403/422/404/409 e consulta da resposta do operador pelo cliente autenticado via `GET /tickets/{id}`.

#### Testes Ajustados na Fase 5A:
Nenhum teste existente precisou ser alterado (`git diff tests/` vazio).

---

### Fase 4B: Memória Persistente em SQLite e Configuração que Falha Cedo

#### Verificação Fase 4B (`python scripts/verify_phase4b.py`):
```text
PASS S1.requirement_declared
PASS S1.lock_regenerated_on_linux
PASS S2.gitignore
PASS S3.config_documented
PASS S4.no_silent_fallback
PASS S5.no_memorysaver_claims
PASS S6.readme
PASS R0.settings
PASS R1.builder
PASS R1.fails_loudly
PASS R2.default_in_memory
PASS R3.memory_survives_restart
PASS R3.thread_id_in_sqlite
PASS R4.isolation_over_sqlite
PASS R4.threads_on_disk
PASS R5.api_uses_sqlite
PASS R6.startup_opens_db
PASS R6.startup_fails_on_bad_db_path
PASS R7.validate_rejects_bad_keys
PASS R7.bad_keys_503_not_500
PASS R7.startup_fails_on_bad_keys
PASS R7.valid_keys_unchanged
PASS Q0.checkpointer_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 139 passed in 12.97s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_db

SUMMARY: 37/37 passed
```

#### Commit Base da Fase 4B (`git rev-parse HEAD`):
```text
2bc8e2b42d10c87665cb6dad5b67b38b138051a9
```

#### Testes Criados na Fase 4B:
`tests/test_checkpointer.py` (7 novos testes unitários):
- `test_build_sqlite_checkpointer_creates_dirs_and_file`: valida que `build_sqlite_checkpointer` cria as pastas pai intermediárias, conecta ao SQLite e retorna uma instância de `SqliteSaver`.
- `test_build_sqlite_checkpointer_unusable_path_raises`: valida falha ruidosa (sem fallback silencioso para `/tmp` ou memória) ao tentar criar banco em caminho inacessível (pasta pai é um arquivo regular).
- `test_orchestration_graph_memory_survives_restart`: valida persistência real entre turnos após reinício simulado do processo (segundo grafo orquestrador sobre o mesmo arquivo SQLite recupera o histórico e segredos do primeiro turno).
- `test_orchestration_graph_user_isolation_sqlite`: valida isolamento completo de contexto entre dois usuários que compartilham o mesmo `session_id`, gravando threads independentes `user_id:session_id` no SQLite.
- `test_orchestration_graph_default_in_memory`: valida que `OrchestrationGraph()` sem argumento `checkpointer` preserva o checkpointer in-memory `MemorySaver` (mantendo suites de testes e verificadores anteriores isolados em memória).
- `test_malformed_api_keys_fail_fast_and_503`: valida que `API_KEYS` mal formatado gera erro HTTP 503 no `/chat`, reporta `auth_mode: "invalid"` no `/health` e impede o arranque da aplicação (`with TestClient(app)` levanta `ValueError`).
- `test_startup_fails_on_unusable_checkpoint_db_path`: valida fail-fast impedindo a aplicação de iniciar via `lifespan` caso `CHECKPOINT_DB_PATH` aponte para um caminho inacessível.

#### Testes Ajustados na Fase 4B:
- `tests/conftest.py`: adicionada a configuração de `os.environ["CHECKPOINT_DB_PATH"]` para um arquivo temporário em `tempfile.mkdtemp()` antes de qualquer import de `src`, garantindo que a execução da suíte de testes nunca crie nem modifique `data/checkpoints.db`.

---

### Fase 4A: Identidade pela Credencial, Isolamento por Usuário, Tickets por Dono e Rate Limit

#### Verificação Fase 4A (`python scripts/verify_phase4a.py`):
```text
PASS S1.no_default_user
PASS S2.no_plaintext_key_in_main
PASS S3.dead_confidence_setting_removed
PASS S4.config_documented
PASS S4.env_example_has_no_key
PASS S5.readme
PASS S6.demo_sends_key
PASS R0.api
PASS R0.settings
PASS A1.hash
PASS A1.parse_valid
PASS A2.parse_rejects
PASS A3.missing_or_invalid_401
PASS A3.dev_key_in_development
PASS A3.dev_operator_key
PASS A3.health_public_and_auth_mode
PASS A4.production_rejects_dev_keys
PASS A4.configured_keys
PASS A4.configured_keys_replace_dev_defaults
PASS A5.body_user_id
PASS I1.session_isolated_per_user
PASS I2.thread_id_format
PASS I3.session_id_generated_and_bounded
PASS I4.run_sync_requires_user
PASS T1.list_by_owner
PASS T2.get_by_owner
PASS T3.tickets_need_key
PASS L1.rate_limit_per_key
PASS L2.zero_disables
PASS C1.no_llm_key_503
PASS C2.config_error_503
PASS C2.transient_error_503
PASS C2.timeout_503
PASS C3.internal_error_500
PASS C4.metadata_fields
PASS Q0.auth_tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 132 passed in 14.93s
PASS Q3.tree_unchanged

SUMMARY: 48/48 passed
```

#### Commit Base da Fase 4A (`git rev-parse HEAD`):
```text
f467d568528fe9551a1e4c824d1ad30463c3fc11
```

#### Testes Criados na Fase 4A:
`tests/test_auth.py` (8 novos testes unitários):
- `test_parse_api_keys_valid_and_invalid`: testa parsing de chave válida e rejeição de entradas com hash inválido (tamanho != 64, não-hex), usuário vazio, role inválido e hashes duplicados.
- `test_auth_missing_or_invalid_key_401`: testa rejeição com HTTP 401 e detalhe genérico para cabeçalho ausente ou chave desconhecida (sem vazar a chave no log ou resposta).
- `test_auth_dev_defaults_and_production_rejection`: valida aceitação das chaves padrão de desenvolvimento quando APP_ENV=development e recusa total em APP_ENV=production sem API_KEYS.
- `test_auth_configured_keys_override_dev_defaults`: valida que configuração de API_KEYS aceita as chaves mapeadas e desabilita as chaves de desenvolvimento.
- `test_chat_body_user_id_mismatch_403`: valida erro HTTP 403 se user_id no corpo da requisição for divergente da identidade autenticada na chave.
- `test_session_isolation_and_thread_id`: valida isolamento completo de histórico entre dois usuários com mesmo session_id e formato composite `user_id:session_id` no checkpointer.
- `test_ticket_authorization_by_role_and_owner`: valida que customer só lista e acessa seus próprios tickets (recebendo 404 para tickets de terceiros) e operador pode listar todos ou filtrar por user_id.
- `test_rate_limiter_sliding_window_and_zero_disable`: valida bloqueio com HTTP 429 e cabeçalho Retry-After ao exceder limite e liberação após 60s via relógio simulado, bem como desativação com RATE_LIMIT_PER_MINUTE=0.

#### Testes Ajustados na Fase 4A:
- `tests/conftest.py`: adicionada fixture autouse `reset_auth_settings` para garantir `APP_ENV = "development"`, `API_KEYS = ""` e `reset_rate_limiter()` isolando a suíte de testes de variáveis locais e limites de taxa.
- `tests/test_eval_judge.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` e removido `user_id` manual no payload do teste de segurança, atualizando asserção para 401 quando o cabeçalho é omitido (conforme nova regra de autenticação estrita).
- `tests/test_graph_llm.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em requisições `/chat` e `/tickets` e atualizados testes de erro 500/503.
- `tests/test_robustness.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas aos endpoints de chat.
- `tests/test_specialists.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas HTTP à API.
- `tests/test_tokens_and_tools.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas `/chat`.
- `tests/test_unit.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas `/chat` e `/tickets`; removido `cliente1988` hardcoded em testes de `/chat` para que a identidade derive do principal autenticado.

---

### Fase 3D: Avaliação do Retrieval e Calibração do RAG_MIN_SCORE

#### Verificação Fase 3D (`python scripts/verify_phase3d.py`):
```text
PASS S1.dataset_identical :: 48 queries, sha256 8178a22508da
PASS S2.dataset_composition
PASS R0.api
PASS R0.no_regex
PASS R1.sha_canonical
PASS R1.normalize
PASS R1.grid
PASS R2.load_labeled_validates
PASS R2.load_labeled_real
PASS R3.evaluate_matches_reference
PASS R4.curve_matches_reference
PASS R4.choose_matches_reference
PASS R4.choose_median_of_plateau
PASS R5.run_embed
PASS R6.run_report_writes
PASS R6.run_report_refuses_mismatch
PASS E1.query_embeddings
PASS E2.embeddings_plausible :: mean top1 answerable=0.795, off_topic=0.540
PASS P1.report_exists
PASS P1.provenance
PASS P2.retrieval_metrics_recomputed :: hit@1=0.900 hit@3=0.967 hit@5=0.967 mrr@10=0.933 answer_hit@3=0.900
PASS P2.per_query_recomputed
PASS P2.curve_recomputed
PASS P2.chosen_threshold :: chosen=0.61 balanced_accuracy=1.000 answer_rate=1.000 off_topic_abstain=1.000 uncovered_abstain=0.000
PASS P2.warnings :: warnings=['uncovered_not_filtered']
PASS P2.markdown_report
PASS P3.setting_updated
PASS P3.compose_consistent
PASS P4.readme
PASS Q0.calibration_tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 124 passed in 12.81s
PASS Q3.tree_unchanged

SUMMARY: 41/41 passed
```

#### Commit Base da Fase 3D:
```text
6cddc0ec2935827a1c1fe60fbd01df5356b0a836
```

#### Consultas `answerable` com `gold_rank` None ou `answer_hit@3` falso:
- `a17` (PT): `gold_rank = 2`, `answer_hit@3 = False` (top-1 score 0.793, chunk `a35faa6f803d-004`).
- `e05` (EN): `gold_rank = None`, `answer_hit@3 = False` (top-1 score 0.651, chunk `590a78a70a4e-001`).
- `e07` (EN): `gold_rank = 1`, `answer_hit@3 = False` (top-1 score 0.806, chunk `fb3e6c49736e-003`).

#### Consultas `uncovered` respondidas no limiar escolhido (`RAG_MIN_SCORE = 0.61`):
Todas as 10 consultas `uncovered` obtiveram score superior ao limiar calibrado (0.61) e decisão `answer`:
- `u01` (PT): score 0.849, chunk `314e4bd739df-000`, decisão `answer`
- `u02` (PT): score 0.778, chunk `081b9925942a-002`, decisão `answer`
- `u03` (PT): score 0.701, chunk `28851a0d386e-001`, decisão `answer`
- `u04` (PT): score 0.711, chunk `28851a0d386e-001`, decisão `answer`
- `u05` (PT): score 0.770, chunk `28851a0d386e-000`, decisão `answer`
- `u06` (PT): score 0.691, chunk `28851a0d386e-001`, decisão `answer`
- `u07` (PT): score 0.732, chunk `590a78a70a4e-002`, decisão `answer`
- `u08` (EN): score 0.767, chunk `4507fe8d48bb-000`, decisão `answer`
- `u09` (EN): score 0.636, chunk `28851a0d386e-001`, decisão `answer`
- `u10` (EN): score 0.743, chunk `75a823f71e23-000`, decisão `answer`

#### Testes Criados na Fase 3D:
`tests/test_retrieval_calibration.py` (7 novos testes unitários):
- `test_load_labeled_validations`: valida rejeição de categoria desconhecida, idioma inválido, id duplicado, campos vazios de URLs e trechos em answerable, e leitura de registros válidos.
- `test_evaluate_hit_and_mrr_ranks`: valida cálculo analítico de hit@1, hit@3, hit@5 e MRR@10 sobre matriz ortogonal e ranks conhecidos.
- `test_evaluate_answer_hit3_multiline`: valida normalização sem regex em correspondência de trechos com múltiplas quebras de linha e caixas altas/baixas.
- `test_abstention_curve_and_choose_threshold_tie`: valida métricas da curva de abstenção e desempate de platô de acurácia balanceada pela mediana inferior.
- `test_run_embed_with_fake_embedder`: valida que consultas são vetorizadas via `embed_query` (RETRIEVAL_QUERY) e nunca `embed_documents`, gravando shape (n, dim) e metadados JSON.
- `test_run_report_refuses_mismatches`: valida que `run_report` recusa divergências de `query_ids`, `dataset_sha256` ou `embedding_model`.
- `test_run_report_outputs`: valida geração dos relatórios JSON e Markdown em diretório temporário com conferência de chaves e métricas.

---

### Fase 3C: Ligação do RAG Real ao Knowledge Agent e Remoção da Base Antiga

#### Verificação Fase 3C (`python scripts/verify_phase3c.py`):
```text
PASS S1.old_kb_removed
PASS S2.legacy_removed
PASS S3.requirements
PASS S4.knowledge_prompt
PASS S5.readme
PASS R1.min_chunk_setting
PASS R2.default_keeps_3b_behaviour
PASS R2.tiny_page_dropped
PASS R2.tail_merged
PASS R3.committed_index_regenerated
PASS R4.tool_description_has_no_facts
PASS R4.tool_uses_retriever
PASS R4.tool_abstains
PASS K6.knowledge_flow_real_index
PASS R5.tool_unavailable_without_key
PASS R6.real_retriever_requires_key
PASS R6.real_retriever_wiring
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 117 passed in 11.64s
PASS Q3.tree_unchanged

SUMMARY: 27/27 passed
```

#### Commit Base da Fase 3C:
```text
d89d2cbb90d04787552083501d82f66de0005ed6
```

#### Testes Alterados, Reescritos e Criados na Fase 3C:
1. `tests/test_knowledge_rag.py` (novo, 7 testes):
   - `test_search_knowledge_base_success`: ferramenta retorna status "success" com documentos oficiais e todos os campos (`url`, `title`, `fetched_at`, `market`, `chunk_id`, `score`, `text`).
   - `test_search_knowledge_base_abstain`: ferramenta retorna status "abstain" com lista vazia de documentos quando o score está abaixo de `min_score`.
   - `test_search_knowledge_base_unavailable_on_retriever_exception`: conversão de qualquer exceção interna (ex.: `LLMNotConfiguredError`) em status `"unavailable"` sem quebrar o grafo.
   - `test_supervisor_knowledge_flow_extracts_source_url`: fluxo integrado Supervisor -> KnowledgeAgent -> search_knowledge_base preenchendo `state.sources` com a URL oficial da página.
   - `test_build_chunks_with_min_chars`: validação do parâmetro `min_chars=120`, descartando páginas curtas (<120 chars) e mesclando caudas curtas ao trecho anterior da mesma página.
   - `test_get_knowledge_retriever_without_key_raises_error`: `get_knowledge_retriever()` levanta `LLMNotConfiguredError` se `GEMINI_API_KEY` não estiver definida.
   - `test_get_knowledge_retriever_loads_committed_index`: com chave configurada, instancia singleton com as configurações ativas (`RAG_MIN_SCORE`, `RAG_TOP_K`, `task_type="RETRIEVAL_QUERY"`).
2. `tests/test_unit.py` (reescritos):
   - `test_retriever_loads_documents`: reescrito para verificar o carregamento de trechos pelo `get_knowledge_retriever()` da biblioteca.
   - `test_retriever_matches_pix_bank_account`, `test_retriever_matches_antecipacao`, `test_retriever_matches_crediario`, `test_retriever_matches_wifi`: reescritos para consultar o retriever novo e validar a presença das URLs oficiais em `documents`.
   - `test_retriever_matches_classica_smart` e `test_retriever_matches_payment_link`: substituídos pela validação de modelos e link pelo retriever novo.
   - `test_rag_abstention_out_of_domain`: reescrito para testar abstenção vetorial com o novo contrato de retorno (`status: "abstain"`, `documents: []`).
3. `tests/conftest.py` (atualizado):
   - Removida a importação legada `from src.agents.knowledge import get_retriever` e a fixture `retriever`.
   - Criada a fixture autouse `mock_knowledge_retriever` que indexa trechos oficiais de teste em diretório temporário com `KeywordFakeEmbedder` e intercepta `src.rag.retriever.get_knowledge_retriever`.

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com arquitetura hierárquica multiagente (`src/core/graph.py`): um `SupervisorAgent` orquestra subagentes especialistas (`KnowledgeAgent` e `SupportAgent`), além de escalonamento humano direto (`escalate_to_human`). Conta com consulta à base vetorial ChromaDB (`src/agents/knowledge.py`), simulações operacionais de hardware e extrato bancário com PII mascarado e telemetria real sem valores inventados (`src/tools/`), persistência em SQLite (`src/core/tickets_db.py`) e suporte a provedores de LLM configuráveis com medição real de consumo de tokens.

---

### 2. Arquitetura Atual (Fase 2E)
- **Hierarquia Multiagente**:
  - **SupervisorAgent**: Ponto de entrada do raciocínio conversacional ReAct. Liga-se a ferramentas de alto nível (`ask_knowledge_agent`, `ask_support_agent`, `escalate_to_human`). Mantém o histórico completo da sessão (`MemorySaver`) e sintetiza a resposta final ao lojista.
  - **KnowledgeAgent**: Especialista em informações conceituais, manuais e políticas. Possui as ferramentas `search_knowledge_base` e `search_web`.
  - **SupportAgent**: Especialista em diagnóstico operacional e dados transacionais. Possui as ferramentas `get_settlement_status`, `diagnose_declined_transaction` e `diagnose_terminal`.
- **Isolamento de Contexto**: Cada especialista opera em contexto limpo e isolado (`[SystemMessage(prompt), HumanMessage(task)]`), sem carregar mensagens antigas do chat do lojista. O `user_id` é injetado pelo orquestrador no momento da chamada da ferramenta.
- **Medição de Tokens Reais**: Cada chamada de modelo que retorna `usage_metadata` é contabilizada na chave interna `"usage"` do especialista e somada no orquestrador. O consumo é registrado por agente em `tokens_by_agent` e no agregado `tokens`. Se não houver medição do provedor, ambos os campos permanecem `None` (sem estimativas empíricas).
- **Rastreabilidade**: Metadados da API `/chat` incluem `llm_model`, `agents_used`, `tokens` e `tokens_by_agent`.

---

### 3. RAG (Recuperação de Informações)
- **Origem dos dados**: Arquivo JSON local estático (`data/getnet_kb.json`) com 15 artigos curtos.
- **Ingestão e Armazenamento**: `ChromaDBKnowledgeRetriever` (`src/agents/knowledge.py`) carrega o JSON na coleção `getnet_kb`.
- **Recuperação e Tagging**: Cada documento recuperado inclui `"retrieval_mode": "vector"` ou `"retrieval_mode": "lexical_fallback"`.
- **Fallback Léxico**: O método `_lexical_fallback` emite log `WARNING` ao ser acionado e não inventa campos de `similarity` ou `distance`.
- **Limiar de relevância**: Limiar geral `threshold = 0.20`. Se a query contiver termos substantivos com zero sobreposição léxica (`top_lex_overlap == 0`) e similaridade cosseno $< 0.55$, o retriever abstém-se matematicamente e retorna vazio (`[]`).

---

### 4. Tools do Sistema

#### Tools do Supervisor (`src/tools/supervisor_tools.py`):
1. `ask_knowledge_agent`: Encaminha dúvidas conceituais, taxas e procedimentos ao `KnowledgeAgent`.
2. `ask_support_agent`: Encaminha pedidos de extrato, erros de maquininha e transações ao `SupportAgent`.
3. `escalate_to_human`: Registra protocolo de transbordo no banco de tickets quando solicitado pelo lojista.

#### Tools Folha / Especialistas (`src/tools/agent_tools.py`):
1. `get_settlement_status` (SupportAgent): Consulta extrato financeiro. Mascara contas bancárias (`mask_bank_account`).
2. `diagnose_declined_transaction` (SupportAgent): Diagnostica motivos de recusa com base estrita no catálogo (`decline_code_catalog`). Sem código ou recusa, retorna campos nulos (`queried_code=None`, `code_known=None`, `code_details=None`). Código fora do catálogo retorna `code_known=False` e `code_details=None` sem descrições inventadas.
3. `diagnose_terminal` (SupportAgent): Diagnóstico e passos derivados exclusivamente da telemetria da máquina (`model`, `sim_operator`, `sim_status`, `signal_level`, `wifi_connected`). Sem problema detectado, informa ausência de anomalias sem inventar instabilidade de sinal.
4. `search_knowledge_base` (KnowledgeAgent): Consulta semântica na base Getnet.
5. `search_web` (KnowledgeAgent): Consulta pública auxiliar (mockada nos testes).

---

### 5. Escalonamento Humano e Resiliência
- **Gravação**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback para `/tmp/tickets.db`).
- **Resiliência em `force_escalation`**: Caso o supervisor exceda `MAX_SUPERVISOR_STEPS` e a abertura do chamado falhe (banco offline, erro de I/O ou payload inválido), o sistema não emite protocolos falsos nem mente ao lojista.
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`).
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`).
- **Guardrails e PII**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn para cartões, formatação de CPF e mascaramento de agências/contas bancárias via `mask_bank_account`).
- **Observabilidade**: `trace_id` UUID mantido em logs estruturados e propagado via header `X-Trace-Id`. `llm_model`, `agents_used`, `tokens` e `tokens_by_agent` fornecem auditoria detalhada de execução por turno.
- **Filtro de Warnings**: Silenciamento pontual via `warnings.filterwarnings` apenas para o `UserWarning` benigno de amostragem fixa dos modelos lite (`uses fixed sampling defaults`).

---

### 7. Higienização e Refatoração de Testes (Fases 1A a 3C)

**Total atual de testes**: 117 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 3C**: 7 novos testes em `tests/test_knowledge_rag.py` cobrindo o fluxo integrado do Knowledge Agent com o novo retriever, extração de URL e metadados, abstenção e indisponibilidade sem interrupção do grafo, além da refatoração completa dos testes unitários legados de `test_unit.py` e remoção da base legada ChromaDB.
- **Fase 3B**: 11 novos testes em `tests/test_rag_index.py`.
- **Fase 3A**: 12 novos testes em `tests/test_ingest.py`.
- **Fase 2E**: 9 novos testes em `tests/test_tokens_and_tools.py`.
- **Fase 2D**: 10 novos testes em `tests/test_specialists.py` e adaptação do fluxo hierárquico nos testes de integração.
- **Fase 2C**: 9 testes de integração de provedores em `tests/test_providers.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos baseados no router por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 3C (`python scripts/verify_phase3c.py`):
```text
PASS S1.old_kb_removed
PASS S2.legacy_removed
PASS S3.requirements
PASS S4.knowledge_prompt
PASS S5.readme
PASS R1.min_chunk_setting
PASS R2.default_keeps_3b_behaviour
PASS R2.tiny_page_dropped
PASS R2.tail_merged
PASS R3.committed_index_regenerated
PASS R4.tool_description_has_no_facts
PASS R4.tool_uses_retriever
PASS R4.tool_abstains
PASS K6.knowledge_flow_real_index
PASS R5.tool_unavailable_without_key
PASS R6.real_retriever_requires_key
PASS R6.real_retriever_wiring
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 117 passed in 11.64s
PASS Q3.tree_unchanged

SUMMARY: 27/27 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
117 passed in 11.64s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 6

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final foi regenerado com sucesso em ambiente Linux (Python 3.11 no Codespaces) contendo as novas dependências `langgraph-checkpoint-sqlite==3.1.3`, `aiosqlite==0.22.1` e `sqlite-vec==0.1.9`.
2. **Dataset de Avaliação `data/eval/cases.jsonl`**: Conferido integralmente com SHA256 `2d7d8e746a2322c2e61306f837b8176eabba838810b5a4f160584c433754ad07` (69 casos, 10 oficiais, 6 offline). Nenhuma divergência com o SPEC encontrada nos dados do revisor.
3. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` no agregado com nota explicativa em `cost_note` ("Token pricing arrives in Phase 7; cost calculation is not active yet."), conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
4. **Calibração do Limiar `RAG_MIN_SCORE = 0.61`**: A avaliação do retrieval no conjunto rotulado de 48 consultas demonstrou separação perfeita (balanced accuracy = 1.000) especificamente entre as consultas respondíveis e as 8 consultas fora de domínio (*off-topic*).
5. **Comportamento das Consultas *Uncovered***: Como previsto na especificação, as consultas *uncovered* pertencem ao domínio semântico Getnet/concorrentes e obtêm similaridade cosseno superior a 0.61 (aviso `uncovered_not_filtered`). A sua abstenção será avaliada de ponta a ponta na Fase 6B.
6. **Memória Persistida em SQLite (`SqliteSaver`)**: Concluída na Fase 4B. As conversas sobrevivem a reinícios da aplicação e estão isoladas por `user_id:session_id` no banco relacional `data/checkpoints.db`.
7. **Proteção contra Enumeração de Tickets**: Acesso a tickets de outro cliente retorna HTTP 404 (o mesmo código para ticket inexistente), prevenindo enumeração de identificadores de tickets por clientes mal-intencionados.
8. **Transbordo Humano Completo (Fases 5A, 5B e 5C)**: O ciclo de vida do ticket (`open -> in_progress -> answered -> closed`), o portão de atendimento `handoff_gate` (com mensagens de espera padronizadas, sem prazo, sem chamadas ao LLM e entrega única da resposta do operador com `delivered_at`) e o escalonamento automático por abstenções repetidas (`consecutive_abstentions >= ESCALATE_AFTER_ABSTENTIONS`) estão plenamente validados.
9. **Fase 6B Concluída (Executor com Modelo Real e Juiz LLM)**: O harness e o executor com modelo real (`run`), juiz LLM (`judge`) e gerador de relatórios (`report`) foram implementados e validados com testes unitários e de integração.
10. **Fase 6C Concluída (Correções do Juiz, Padrões no Tier Gratuito e Execução full-1 Registrada)**: O modelo padrão foi atualizado para `gemini-3.5-flash-lite` (com fallback `gemini-3.1-flash-lite` e juiz `gemini-3.1-flash-lite`), mitigando o teto diário de 20 requisições do Flash standard no tier gratuito; o juiz agora suporta respostas em lista de blocos (Gemini 3) e aborta preventivamente em 3 erros consecutivos; a execução `full-1` (69/69 casos bem-sucedidos) foi validada e comitada como baseline de avaliação.
11. **Fase 6D Concluída (Trechos Completos no Juiz e Correções de Cota)**: O juiz agora acessa o texto completo de cada passagem a partir de `data/index/chunks.jsonl` via `load_chunk_texts`; `observe_turn` preserva até 2000 caracteres no log; a documentação de cota do Flash-Lite foi corrigida para 500 RPD e os limites do juiz foram documentados.
12. **Fase 6E Concluída (Resultados da Avaliação Consolidados no Repositório e README)**: O relatório completo com a segunda rodada do juiz foi regenerado e integrado em `reports/eval_full-1.*`; os números oficiais e limitações conhecidas foram documentados no `README.md`.
13. **Fase 6F Concluída (Alinhamento Honesto de Capacidades no README e /demo)**: Removida qualquer afirmação de "Confiança Dinâmica" e "100% de precisão" (sem cálculo que a sustente), clarificado que `estimated_cost_usd` permanece `null` até a Fase 7, atualizado o formato de tickets para `GET-TKT-YYYYMMDD-<10 hexadecimais>`, documentada a margem real de 0.04 no retrieval e alinhadas as respostas do glossário e da matriz de cenários com as medições reais de `full-1`.
14. **Próxima Fase (Fase 7: Observabilidade e Custos)**: Precificação de tokens por modelo, cálculo financeiro em USD e governança de custos no pipeline.
