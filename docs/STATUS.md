# STATUS DO REPOSITÓRIO
**Subfase:** 15D | **Base:** `6492e8b` | **Python:** 3.13.3
**O que mudou:** aposentados `15C2.md`/`verify_phase15c2.py`; `TurnPlan.terminal_issue`, `SUPPORT_STEP_GOALS` e `apply_delegate_rule` (`planner.py`, `graph.py`); `VERIFIER_ENABLED=False` (`config.py`, `.env.example`, fixture em 5 testes); `--judge-model`/`--judge-prompt`/`--judge-dir`, `prompt_sha256`, recusa de juiz misto e `acceptable` no `compare` (`judge.py`, `__main__.py`, `metrics.py`, `compare.py`); chave `"auth"` e `auth_checks` em `compose_evidence.py`/`test_compose_evidence.py`; novos `test_delegate_rule.py` (6), `test_judge_selection.py` (3) e `test_compose_auth_checks.py` (2).
## Verificações (`python scripts/verify_phase15d.py`)
```text
PASS A0.py311_syntax
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS A4.data_and_reports_unchanged
PASS A5.existing_tests_only_allowed_edits
PASS T1.verifier_tests_opt_in_only
PASS T2.compose_test_edit
PASS S1.status
PASS A6.no_case_ids_in_code
PASS Q6.new_tests_written :: {'tests/test_delegate_rule.py': 6, 'tests/test_judge_selection.py': 3, 'tests/test_compose_auth_checks.py': 2}
PASS P1.apply_delegate_rule
PASS P2.planner_applies_rule
{"timestamp": "2026-11-21T17:40:34.281178+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-21T17:40:34.286641+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 1.38, "otel_trace_id": "7cbde2639922016b554a5f434eb7497d"}
{"timestamp": "2026-11-21T17:40:34.287871+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.06, "otel_trace_id": "91274fdd0147236ec05d87d808467e8a"}
{"timestamp": "2026-11-21T17:40:34.289697+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 0.12, "otel_trace_id": "d46d10072b03f058497db61617a6dc5a"}
{"timestamp": "2026-11-21T17:40:34.294690+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Planner decision (status=ok, scope=support, reply_language=en, escalation_request=none, steps=1)", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "status": "ok", "latency_ms": 2.12, "otel_trace_id": "60c19f21b846734841e25f06ed1f08d2"}
{"timestamp": "2026-11-21T17:40:34.294872+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "planner", "latency_ms": 3.5, "otel_trace_id": "60c19f21b846734841e25f06ed1f08d2"}
{"timestamp": "2026-11-21T17:40:34.300390+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 4.39, "otel_trace_id": "5152be3f5e3a35c93ede14d16df5d211"}
{"timestamp": "2026-11-21T17:40:34.302768+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: diagnose_declined_transaction] invoked (code_context=declined_sale, error_code_given=True)", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "otel_trace_id": "846390f802243d2f50ea9dc732ee4d29"}
{"timestamp": "2026-11-21T17:40:34.303121+00:00", "level": "INFO", "logger": "multiagent.specialists", "message": "tool finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "agent": "SupportAgent", "tool": "diagnose_declined_transaction", "status": "ok", "latency_ms": 0.86, "otel_trace_id": "846390f802243d2f50ea9dc732ee4d29"}
{"timestamp": "2026-11-21T17:40:34.303856+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "tool finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "agent": "SupervisorAgent", "tool": "ask_support_agent", "status": "ok", "latency_ms": 2.13, "otel_trace_id": "846390f802243d2f50ea9dc732ee4d29"}
{"timestamp": "2026-11-21T17:40:34.303981+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "tools", "latency_ms": 2.42, "otel_trace_id": "846390f802243d2f50ea9dc732ee4d29"}
{"timestamp": "2026-11-21T17:40:34.307770+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 2.12, "otel_trace_id": "6ae578d6dcc2dce2af62b6c89ee98e36"}
{"timestamp": "2026-11-21T17:40:34.309429+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "plan coverage finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "status": "complete", "otel_trace_id": "01e0f5e0ddce8d4e84c398d1b10df91e"}
{"timestamp": "2026-11-21T17:40:34.309562+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "plan_coverage", "latency_ms": 0.26, "otel_trace_id": "01e0f5e0ddce8d4e84c398d1b10df91e"}
{"timestamp": "2026-11-21T17:40:34.310573+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "verifier finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "status": "disabled", "otel_trace_id": "af0a90422eaf0e42d42898c7f56ac8e2"}
{"timestamp": "2026-11-21T17:40:34.310674+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "verifier", "latency_ms": 0.14, "otel_trace_id": "af0a90422eaf0e42d42898c7f56ac8e2"}
{"timestamp": "2026-11-21T17:40:34.312439+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "answer check", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "status": "passed", "failed": [], "otel_trace_id": "9b09de47cc6fd0574a711fefe972e31c"}
{"timestamp": "2026-11-21T17:40:34.312674+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "answer_check", "latency_ms": 0.34, "otel_trace_id": "9b09de47cc6fd0574a711fefe972e31c"}
{"timestamp": "2026-11-21T17:40:34.313482+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "language check finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "status": "disabled", "otel_trace_id": "d5b0b6b1991e80727c06dd302477a5cc"}
{"timestamp": "2026-11-21T17:40:34.313583+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "language_check", "latency_ms": 0.13, "otel_trace_id": "d5b0b6b1991e80727c06dd302477a5cc"}
{"timestamp": "2026-11-21T17:40:34.314330+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.05, "otel_trace_id": "049d271f17c72cd68a2ad43baff63645"}
{"timestamp": "2026-11-21T17:40:34.316778+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 35.7ms. Tools: ['diagnose_declined_transaction']", "trace_id": "trc-b960dc2c7583", "session_id": "s-15d-a82cfc", "user_hash": "u_a9f6bd311e2b2495"}
PASS P3.graph_uses_corrected_plan
PASS P4.verifier_off_by_default
Judge 'jt-1': attempted=2, ok=2, errors=0, skipped=0, stopped_early=False
Resumption is supported: simply run the command again to continue from where it stopped.
PASS J1.judge_cli_model_prompt_dir
PASS J2.judge_refuses_mixed_judges
Generated comparison report at C:\Users\burba\AppData\Local\Temp\verify_p15d_pqb3cv11\cmp\eval_v2_phase15.json and C:\Users\burba\AppData\Local\Temp\verify_p15d_pqb3cv11\cmp\eval_v2_phase15.md
PASS J3.compare_unchanged_without_acceptable
Generated comparison report at C:\Users\burba\AppData\Local\Temp\verify_p15d_pqb3cv11\cmp\eval_acc_probe.json and C:\Users\burba\AppData\Local\Temp\verify_p15d_pqb3cv11\cmp\eval_acc_probe.md
PASS J4.compare_acceptable_row_and_judge_dir
PASS H1.compose_auth_key_isolated
PASS X1.index_matches_corpus :: 361 chunks
PASS H2.second_sample_answers_committed
PASS R4.probes_left_tree_clean
INFO python 3.13.3
INFO AL4.promtool :: promtool not found: run by the reviewer and by CI
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
INFO P15B.A1.reviewer_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A2.retired_process_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A3.scope :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A4.frozen :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A5.existing_tests_only_grow :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.S1.status :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15C.P15B :: 15B failures inside the 15C re-run: ['D4.corpus_committed', 'H2.second_sample_committed'] (allowed: ['D4.corpus_committed', 'H2.second_sample_committed'])
INFO P15C.A1.reviewer_files :: superseded by 15D (fails)
INFO P15C.A2.retired_process_files :: superseded by 15D (fails)
INFO P15C.A3.scope :: superseded by 15D (fails)
INFO P15C.A4.index_and_corpus_unchanged :: superseded by 15D (fails)
INFO P15C.A5.existing_tests_unchanged :: superseded by 15D (fails)
INFO P15C.S1.status :: superseded by 15D (passes)
PASS P15C.previous_verifiers :: 15/21 pass
PASS Q2.test_count :: 607 passed

SUMMARY: 25/25 passed
```
## Perguntas / divergências
Nenhuma divergência em aberto com `docs/SPEC.md` (§3.7) ou `docs/phase-prompts/15D.md`. `AL4.promtool` e `Q7.integration_suite` ficam para execução no CI e no ambiente do revisor.
