# STATUS DO REPOSITÓRIO

**Subfase:** 15A — Matriz, ablação, roteamento pelo plano, código de tela, evidência do verificador, calibração do juiz
**Base:** `8dcf972` (fim da Fase 14) | **Python:** 3.13.3

## O que mudou (15A)

- **Aposentadoria da 14C e arquivos do revisor:** removidos via `git rm` `docs/phase-prompts/14C.md` e `scripts/verify_phase14c.py`; preservados intactos `docs/SPEC.md`, `docs/phase-prompts/15A.md`, `scripts/verify_phase15a.py`, os prompts em `src/prompts/` e `data/eval/cases_holdout4.jsonl`.
- **Instrumentação de camadas e ablação:** `PLAN_COVERAGE_ENABLED=true` em `src/config.py` e `.env.example`; `layers`, `coverage`, `tool_gate`, `rejected_drafts` e `layer_latency_ms` (`verifier` e `language`, sem alterar `verification`/`language` nem `observe_turn`) gravados em `run_case` (`src/eval/runner.py`) com recusa (`ValueError`) ao retomar `layers` diferentes; `rejected_drafts` restrito ao estado e ao runner (nunca em `ChatResponse`, logs, spans ou métricas); novo módulo `src/eval/ablation.py` e subcomando CLI `ablation` (`src/eval/__main__.py`).
- **Roteamento pelo plano (`plan_coverage`):** prompt do supervisor passa a exibir `{n}. [{delegate}] {goal}`; novo nó `plan_coverage` entre supervisor e verificador (`src/core/graph.py`), com até uma rodada corretiva (`[Plan coverage]`), métrica `getnet_plan_coverage_total{status}` (`src/core/metrics.py`) e span `graph.node.plan_coverage` (`coverage.status` em `src/core/tracing.py`).
- **Portão de código de tela/app (`code_source`):** `TurnPlan.code_source` em `src/agents/planner.py`; `SpecialistAgent.run(..., excluded_tools=...)` (`src/agents/specialists.py`) oculta e bloqueia `diagnose_declined_transaction` no `SupportAgent` quando `code_source` é `terminal_screen` ou `app`, gravando `tool_gate`; `diagnose_terminal` (`src/tools/agent_tools.py`, `src/tools/terminal_tools.py`) aceita `screen_error_code` e retorna `screen_error` com `catalogue: "not_available"`.
- **Evidência do verificador:** `build_verifier_conversation` restringe o histórico a `merchant:` e `operator:`; estado ganha `prior_turn_evidence` (cópia do `turn_evidence` do turno anterior da sessão) passado a `build_verifier_evidence` em blocos `[earlier turn: <agent>/<tool>]` dentro do teto de 24.000 caracteres.
- **Calibração do juiz:** `parse_judgment` (`src/eval/judge.py`) aceita `acceptable` booleano opcional; novo módulo `src/eval/judge_calibration.py` e subcomandos CLI `judge-calibrate` e `judge-calibration-report` (`src/eval/__main__.py`), sem execuções reais nesta fase.
- **Testes:** novos `tests/test_plan_coverage.py` (6), `tests/test_screen_code_gate.py` (4), `tests/test_verifier_prior_evidence.py` (5), `tests/test_eval_layers.py` (4), `tests/test_ablation_report.py` (4) e `tests/test_judge_calibration.py` (4), além dos 4 ajustes/substituições permitidos em `test_verifier_evidence.py` e `test_smoke_fixes.py`.

## `LEGACY_NO_COVERAGE_MODULES` (`tests/conftest.py`)

Módulos legados em que testes existentes roteirizam o supervisor com resposta direta sem chamar o especialista indicado no plano (`delegate: "knowledge"` ou `"support"`), falhando se executados com `PLAN_COVERAGE_FORCE=1`:
- `tests.test_planner`: fixa plano com `delegate="knowledge"` e resposta direta sem chamada de especialista.
- `tests.test_verifier_node`: testa o nó verificador com respostas diretas do supervisor e passo delegando a especialista sem invocá-lo.
- `tests.test_escalation_gate`: usa plano padrão com `delegate="knowledge"` em cenários que testam apenas o portão de `escalate_to_human`.
- `tests.test_write_action_flow`: reutiliza `_plan(delegate="support")` em turnos de confirmação/recusa que chamam apenas `confirm_pending_action`.
- `tests.test_language_enforcement`: testa reescrita de idioma com plano padrão `delegate="support"` sem simular especialista antes do texto.

## Verificações (`python scripts/verify_phase15a.py`)

```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS A4.frozen
PASS A5.existing_tests_only_grow
PASS S1.status
PASS A6.no_case_tuning
PASS M1.requirements_matrix :: 57 rows
PASS P1.coverage_corrected_once
PASS P2.coverage_incomplete_no_loop
PASS P3.coverage_skipped_complete_disabled
PASS P4.coverage_metric
PASS T1.decline_tool_not_offered_for_screen_codes
PASS T2.gate_only_for_screen_and_app
PASS T3.no_plan_no_gate
PASS T4.diagnose_terminal_screen_code
PASS E1.conversation_without_assistant
PASS E2.previous_turn_raw_result_supports
PASS E3.earlier_assistant_answer_is_not_evidence
PASS E4.evidence_order_and_caps
PASS E5.prompt_contracts
PASS L1.turn_records_layers_latency_drafts
PASS L2.resume_with_other_layers_refused
PASS L3.rejected_drafts_only_in_eval_records
PASS AB1.ablation_report_lossy
PASS AB2.ablation_rule_switches_off
PASS AB3.mixed_layers_refused
PASS J1.calibration_records
PASS J2.resume_with_other_prompt_refused
PASS J3.calibration_report
PASS G1.write_action_gate_unchanged
PASS G2.no_message_evidence_or_draft_text_in_logs
PASS R1.production_fail_fast
PASS R2.trace_and_span_privacy
PASS R3.no_raw_pii_in_checkpoints
PASS R4.probes_left_tree_clean
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 542 passed, 13 deselected in 88.49s (0:01:28)
PASS Q6.new_tests_written :: {'tests/test_plan_coverage.py': 6, 'tests/test_screen_code_gate.py': 4, 'tests/test_verifier_prior_evidence.py': 5, 'tests/test_eval_layers.py': 4, 'tests/test_ablation_report.py': 4, 'tests/test_judge_calibration.py': 4}
PASS Q8.legacy_modules_without_gate_justified :: 5 modules: ['tests.test_escalation_gate', 'tests.test_language_enforcement', 'tests.test_planner', 'tests.test_verifier_node', 'tests.test_write_action_flow']
PASS Q5.offline_eval
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data

SUMMARY: 44/44 passed
```

## Perguntas / divergências

Nenhuma divergência em aberto com `docs/SPEC.md` ou `docs/phase-prompts/15A.md`.
