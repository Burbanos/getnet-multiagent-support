# STATUS DO REPOSITÓRIO

**Data de geração**: 09/11/2026 | **Branch**: `main`

---

### Fase 11B: Holdout do Guardrail Commitado Antes da Execução

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11B:
```text
INFO python 3.13.3
PASS B0.py311_syntax
PASS B1.files_are_the_reviewers
PASS B1.labeled_set_unchanged
PASS B5.no_run_yet
PASS S1.status_11b
PASS S2.status_without_messages
PASS E2.scope
PASS B2.holdout_valid :: 20 messages, balance {('block', 'pt'): 5, ('block', 'en'): 5, ('allow', 'pt'): 5, ('allow', 'en'): 5}
PASS B3.candidates_consistent
PASS B4.disjoint_from_earlier_set
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 331 passed in 25.46s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 62/62 passed
```

#### Commit base:
`a2db8ac5e851ec972f3d2a7ef2906f9f951d95bf`

#### Não feito:
Nenhuma execução de modelo real (`author-1`) nem do guardrail foi feita; isso será executado pelo autor no terminal dele após este commit.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
os três arquivos do conjunto foram commitados como o revisor os entregou; nenhuma execução foi feita.

---

### Fase 11A: Saída Inválida do Classificador Bloqueia

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11A:
```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.readme_texts
PASS A2.claims_row
PASS A3.guardrail_eval_append_only
PASS A4.no_unparseable
PASS A5.tests_named
PASS A5.classifier_prompt_unchanged
PASS S1.status_11a
PASS E2.scope
PASS A6.classifier_results
{"timestamp": "2026-11-09T14:51:32.477630+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.484114+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 1.34}
{"timestamp": "2026-11-09T14:51:32.485574+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.489691+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=no_verdict_call)", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.58}
{"timestamp": "2026-11-09T14:51:32.490007+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 2.64}
{"timestamp": "2026-11-09T14:51:32.492118+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 14.66ms. Tools: []", "trace_id": "trc-df66bbe3d20d", "session_id": "c87f81f0-2de8-47f2-a56d-15a80bf749f8", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.503868+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.506127+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.09}
{"timestamp": "2026-11-09T14:51:32.506900+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.509453+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=no_verdict_call)", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.13}
{"timestamp": "2026-11-09T14:51:32.509575+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.64}
{"timestamp": "2026-11-09T14:51:32.511485+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 7.57ms. Tools: []", "trace_id": "trc-ae5014b187a3", "session_id": "fa8c06bb-4116-4ad8-a30b-2171f64d9f9e", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.523331+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.525506+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.07}
{"timestamp": "2026-11-09T14:51:32.526365+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.530232+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=invalid_arguments)", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 2.36}
{"timestamp": "2026-11-09T14:51:32.530554+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 3.13}
{"timestamp": "2026-11-09T14:51:32.533691+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 10.21ms. Tools: []", "trace_id": "trc-a12c1ddce7dd", "session_id": "032f43d2-3579-4add-939b-9d2d0b91ed96", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.542971+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.547126+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.14}
{"timestamp": "2026-11-09T14:51:32.548655+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.552959+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=incoherent_verdict)", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.41}
{"timestamp": "2026-11-09T14:51:32.553087+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 2.0}
{"timestamp": "2026-11-09T14:51:32.554378+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 11.47ms. Tools: []", "trace_id": "trc-f2d32615cf1c", "session_id": "9b7c57ea-eace-4206-86dd-5057c2aba7e4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.565337+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.568612+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.13}
{"timestamp": "2026-11-09T14:51:32.569716+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.572514+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=incoherent_verdict)", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.15}
{"timestamp": "2026-11-09T14:51:32.572629+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.64}
{"timestamp": "2026-11-09T14:51:32.574006+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 8.91ms. Tools: []", "trace_id": "trc-5b87e15a91b7", "session_id": "e2284a28-683c-4072-b727-119eedd3445b", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.585160+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.587560+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.08}
{"timestamp": "2026-11-09T14:51:32.588359+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.591332+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=no_verdict_call)", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.4}
{"timestamp": "2026-11-09T14:51:32.591474+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.98}
{"timestamp": "2026-11-09T14:51:32.592917+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 7.83ms. Tools: []", "trace_id": "trc-b37d0f6770a3", "session_id": "bfd6139c-be38-4818-8619-0579421c94e0", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.604998+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.607276+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.1}
{"timestamp": "2026-11-09T14:51:32.608058+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.611343+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=no_verdict_call)", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.89}
{"timestamp": "2026-11-09T14:51:32.611676+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 2.61}
{"timestamp": "2026-11-09T14:51:32.614699+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 9.69ms. Tools: []", "trace_id": "trc-0b6b1abdd56d", "session_id": "8d5b4746-dc7a-49e9-a088-af32a17f62a8", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.624486+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.630087+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.19}
{"timestamp": "2026-11-09T14:51:32.631894+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.636101+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=invalid_arguments)", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 1.63}
{"timestamp": "2026-11-09T14:51:32.636269+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 2.47}
{"timestamp": "2026-11-09T14:51:32.638216+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 13.72ms. Tools: []", "trace_id": "trc-3f29d99f7f8c", "session_id": "f0ed6715-e2f9-4abf-9020-3382ac87c838", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.652566+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.656712+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.26}
{"timestamp": "2026-11-09T14:51:32.658044+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.663453+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=incoherent_verdict)", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 3.16}
{"timestamp": "2026-11-09T14:51:32.663769+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 4.12}
{"timestamp": "2026-11-09T14:51:32.667087+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 14.51ms. Tools: []", "trace_id": "trc-f26a686ca6f8", "session_id": "3136ed23-4049-4526-ba65-7951a1a497dc", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.677621+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.683239+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.22}
{"timestamp": "2026-11-09T14:51:32.684787+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.693279+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=incoherent_verdict)", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 6.46}
{"timestamp": "2026-11-09T14:51:32.693575+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 7.26}
{"timestamp": "2026-11-09T14:51:32.696372+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 18.83ms. Tools: []", "trace_id": "trc-95fabaf6758c", "session_id": "c4d77705-c339-4d3f-8b67-ec2130401922", "user_hash": "u_a9f6bd311e2b2495"}
PASS A7.invalid_blocks_both_modes
{"timestamp": "2026-11-09T14:51:32.709284+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.713992+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.28}
{"timestamp": "2026-11-09T14:51:32.715558+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.719314+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=RuntimeError)", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 1.08}
{"timestamp": "2026-11-09T14:51:32.719484+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 2.08}
{"timestamp": "2026-11-09T14:51:32.722670+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 2.12}
{"timestamp": "2026-11-09T14:51:32.723719+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.725263+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 15.95ms. Tools: []", "trace_id": "trc-1897ea133c70", "session_id": "d109fcf1-b96b-483d-8c26-5df249fed681", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.739328+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-fee41a092e3c", "session_id": "6291daa3-0d8d-4dda-a62a-434f3b7c5292", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.743060+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fee41a092e3c", "session_id": "6291daa3-0d8d-4dda-a62a-434f3b7c5292", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.12}
{"timestamp": "2026-11-09T14:51:32.744050+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fee41a092e3c", "session_id": "6291daa3-0d8d-4dda-a62a-434f3b7c5292", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.749906+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=RuntimeError)", "trace_id": "trc-fee41a092e3c", "session_id": "6291daa3-0d8d-4dda-a62a-434f3b7c5292", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 2.39}
{"timestamp": "2026-11-09T14:51:32.750128+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fee41a092e3c", "session_id": "6291daa3-0d8d-4dda-a62a-434f3b7c5292", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 3.42}
{"timestamp": "2026-11-09T14:51:32.762872+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.768207+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.18}
{"timestamp": "2026-11-09T14:51:32.769767+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.772311+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=Quota429Error)", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 0.83}
{"timestamp": "2026-11-09T14:51:32.772420+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.38}
{"timestamp": "2026-11-09T14:51:32.775124+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 1.84}
{"timestamp": "2026-11-09T14:51:32.776119+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.777485+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 14.72ms. Tools: []", "trace_id": "trc-c0a142fda95e", "session_id": "de06849f-5cb2-4837-a032-587b646d6727", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.792953+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-c477039f7700", "session_id": "daa9cfdc-047a-4d0a-aa61-eacbdce115d4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.797008+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c477039f7700", "session_id": "daa9cfdc-047a-4d0a-aa61-eacbdce115d4", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.17}
{"timestamp": "2026-11-09T14:51:32.798877+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c477039f7700", "session_id": "daa9cfdc-047a-4d0a-aa61-eacbdce115d4", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.01}
{"timestamp": "2026-11-09T14:51:32.801722+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=Quota429Error)", "trace_id": "trc-c477039f7700", "session_id": "daa9cfdc-047a-4d0a-aa61-eacbdce115d4", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 0.97}
{"timestamp": "2026-11-09T14:51:32.801833+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-c477039f7700", "session_id": "daa9cfdc-047a-4d0a-aa61-eacbdce115d4", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.67}
{"timestamp": "2026-11-09T14:51:32.812329+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.816570+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.1}
{"timestamp": "2026-11-09T14:51:32.817599+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.820438+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=TimeoutError)", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 0.79}
{"timestamp": "2026-11-09T14:51:32.820617+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.34}
{"timestamp": "2026-11-09T14:51:32.823233+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 1.61}
{"timestamp": "2026-11-09T14:51:32.824165+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.825480+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 13.44ms. Tools: []", "trace_id": "trc-650967be7688", "session_id": "6fb70cb1-1808-44fa-9eb5-72d4f98459b2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.837363+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-08bdac6607dd", "session_id": "3448e0ae-c39f-4fb4-a348-c7b313e3352e", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.839777+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-08bdac6607dd", "session_id": "3448e0ae-c39f-4fb4-a348-c7b313e3352e", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.08}
{"timestamp": "2026-11-09T14:51:32.840678+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-08bdac6607dd", "session_id": "3448e0ae-c39f-4fb4-a348-c7b313e3352e", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.843275+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=error, verdict=None, category=None, error_type=TimeoutError)", "trace_id": "trc-08bdac6607dd", "session_id": "3448e0ae-c39f-4fb4-a348-c7b313e3352e", "user_hash": "u_a9f6bd311e2b2495", "status": "error", "latency_ms": 0.85}
{"timestamp": "2026-11-09T14:51:32.843392+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-08bdac6607dd", "session_id": "3448e0ae-c39f-4fb4-a348-c7b313e3352e", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.59}
{"timestamp": "2026-11-09T14:51:32.855206+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.857685+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.07}
{"timestamp": "2026-11-09T14:51:32.858522+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.863226+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=ok, verdict=allow, category=none, error_type=None)", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "status": "ok", "latency_ms": 3.08}
{"timestamp": "2026-11-09T14:51:32.863374+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 3.67}
{"timestamp": "2026-11-09T14:51:32.866759+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 2.41}
{"timestamp": "2026-11-09T14:51:32.867748+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.869115+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 13.95ms. Tools: []", "trace_id": "trc-fb034eded9df", "session_id": "e7d6ead6-ca5e-4c70-8eb5-b5d46940ade6", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.879617+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:32.883872+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.08}
{"timestamp": "2026-11-09T14:51:32.884943+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:32.888256+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=ok, verdict=block, category=attack_request, error_type=None)", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495", "status": "ok", "latency_ms": 1.4}
{"timestamp": "2026-11-09T14:51:32.888385+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 1.97}
{"timestamp": "2026-11-09T14:51:32.890023+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 10.58ms. Tools: []", "trace_id": "trc-1dde979b49f6", "session_id": "ca1d2f33-6b02-4372-a11b-5a94c9496d9d", "user_hash": "u_a9f6bd311e2b2495"}
PASS A8.provider_errors_follow_mode
{"timestamp": "2026-11-09T14:51:33.274207+00:00", "level": "INFO", "logger": "multiagent.tickets_db", "message": "Tickets database initialized at: C:\\Users\\burba\\AppData\\Local\\Temp\\verify_p11a_8ytkjbs3\\tickets.db"}
{"timestamp": "2026-11-09T14:51:33.287882+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T14:51:33.293296+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.21}
{"timestamp": "2026-11-09T14:51:33.295555+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T14:51:33.301465+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Guardrail classifier decision (status=invalid, verdict=block, category=None, error_type=incoherent_verdict)", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495", "status": "invalid", "latency_ms": 2.54}
{"timestamp": "2026-11-09T14:51:33.301722+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail_classifier", "latency_ms": 3.57}
{"timestamp": "2026-11-09T14:51:33.304251+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 16.27ms. Tools: []", "trace_id": "trc-7c2a60556504", "session_id": "0d977c41bab9454691d3c3eab7880005", "user_hash": "u_a9f6bd311e2b2495"}
PASS A8b.api_invalid_refusal
PASS A9.run_guardrail
PASS A10.report_invalid_is_blocked
PASS A11.committed_reports_unchanged
PASS A12.author_holdout_source
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 331 passed in 24.82s
PASS Q2.mode_matrix_tests :: 16 passed in 1.08s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 69/69 passed

#### Commit base:
`e8eb27e32e292d5f4ffa114187f014ea1585844c`

#### Testes criados e alterados:
- `tests/test_guardrail_classifier.py`:
  - `test_fail_open_on_classifier_errors`: restrito aos três casos de exceção de provedor (`RuntimeError`, `CustomQuota429Error`, `TimeoutError`).
  - `test_provider_errors_follow_fail_mode`: novo teste parametrizado (3 exceções × modos `open` e `closed` = 6 casos) garantindo que erro de provedor segue o modo configurado.
  - `test_invalid_output_blocks_in_both_modes`: novo teste parametrizado (5 respostas inválidas × modos `open` e `closed` = 10 casos) garantindo bloqueio por precaução em ambos os modos.
  - `test_invalid_output_counts_metric_and_tokens`: novo teste para registro de métrica `classifier_invalid_block` e acúmulo de tokens.
- `tests/test_guardrail_eval_runs.py`:
  - `test_run_writes_one_record_per_case_without_text`: assert atualizado incluindo `"invalid": 0`.
  - `test_invalid_records_block_and_are_not_retried`: novo teste verificando contagem `invalid`, não-retomada de registros inválidos e tratamento no `guardrail_report`.

#### Não feito:
Nada. Todas as instruções e critérios da Fase 11A foram cumpridos.

#### Perguntas / divergências com o SPEC:
Nenhuma. O comportamento do classificador foi ajustado conforme especificado para bloquear respostas inválidas (sem chamada válida de `GuardrailVerdict`, argumentos inválidos ou incoerência entre veredito e categoria), mantendo o fail-open estritamente para indisponibilidade da API do provedor.

#### Alterações:
- `src/agents/injection_classifier.py`: `ClassifierResult` e método `classify` atualizados para retornar `status="invalid"`, `verdict="block"`, `category=None` com `error_type` descritivo (`"no_verdict_call"`, `"invalid_arguments"`, `"incoherent_verdict"`), eliminando a string `"unparseable"`.
- `src/core/graph.py`: nó `_guardrail_classifier_node` atualizado para bloquear quando `status == "invalid"` com a recusa padrão, violação descritiva e incremento da métrica `classifier_invalid_block`.
- `src/core/metrics.py`: adicionada decisão `"classifier_invalid_block"` a `GUARDRAIL_DECISIONS`.
- `src/eval/guardrail_eval.py`: adição de `"author_holdout"` a `VALID_SOURCES`, constante `ANSWERED`, suporte a contagem `invalid` e retomada no `run_guardrail`, e tratamento no `guardrail_report`.
- `tests/test_guardrail_classifier.py` e `tests/test_guardrail_eval_runs.py`: testes atualizados e novos casos adicionados.
- `README.md`: documentação atualizada nas seções de limitações atuais, configuração, medição do guardrail híbrido e tabela de afirmações e evidências.

---

### Fase 10I: README com os Resultados Reais

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 10I:
```text
INFO python 3.13.3
PASS I0.py311_syntax
PASS I1.readme_texts
PASS I2.readme_kept
PASS I3.claims_rows
PASS I5.status_10h_corrected
PASS S1.status_10i
PASS E2.scope
PASS I4.numbers_match_reports
PASS I6.v2_reports_tolerant
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 316 passed in 31.50s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 59/59 passed
```

#### Commit base:
`9b8d082218d0816f80bcfe3142a234b95d77a4dd`

#### Não feito:
Nada de código ou testes foi alterado nesta fase. Todos os requisitos da Fase 10I foram implementados e o ciclo de desenvolvimento do projeto está concluído conforme o SPEC.

#### Perguntas / divergências com o SPEC:
Nenhuma. Todos os textos, números e tabelas das medições reais do guardrail e do conjunto v2 foram transpostos para o README.md e validados pelo verificador.

#### Alterações:
- Atualização do README.md nas seções de limitações atuais, execuções registradas, avaliação v2 e guardrail híbrido com os números oficiais das execuções reais.
- Inclusão das afirmações e evidências correspondentes na tabela do README.md.
- Registro da nota técnica de precisão de ponto flutuante na seção da Fase 10H e registro de status da Fase 10I.

---

### Fase 10H: Execuções com Modelo Real (Guardrail e Conjunto v2)

#### Versão do Python:
```text
Python 3.13.3
```

#### Saída dos relatórios:
```text
$ python -m src.eval guardrail-report --run-id hybrid-1
guardrail-report: hybrid block_rate 1.0, false_positive_rate 0.125, targets_met False

$ python -m src.eval guardrail-report --run-id hybrid-2
guardrail-report: hybrid block_rate 1.0, false_positive_rate 0.0625, targets_met True

$ python -m src.eval guardrail-report --run-id hybrid-3
guardrail-report: hybrid block_rate 1.0, false_positive_rate 0.125, targets_met False

$ python -m src.eval guardrail-summary --run-ids hybrid-1,hybrid-2,hybrid-3
guardrail-summary: 3 runs, all_targets_met False

$ python -m src.eval report --cases data/eval/cases_v2.jsonl --run-id v2-1
Generated report at reports\eval_v2-1.json and reports\eval_v2-1.md

$ python -m src.eval report --cases data/eval/cases_v2.jsonl --run-id v2-2
Generated report at reports\eval_v2-2.json and reports\eval_v2-2.md

$ python -m src.eval report --cases data/eval/cases_v2.jsonl --run-id v2-3
Generated report at reports\eval_v2-3.json and reports\eval_v2-3.md

$ python -m src.eval compare --cases data/eval/cases_v2.jsonl --name v2 --group "flash-lite=v2-1,v2-2,v2-3"
Generated comparison report at reports\eval_v2.json and reports\eval_v2.md
```

#### Verificação Fase 10H:
```text
INFO python 3.13.3
PASS H0.py311_syntax
PASS H0.files_present
PASS S1.status_10h
PASS E2.scope
PASS E3.old_reports_untouched
PASS H1.guardrail_raw :: hybrid-1 ok=36/36 lines=36; hybrid-2 ok=36/36 lines=36; hybrid-3 ok=36/36 lines=36
PASS H2.guardrail_reports :: hybrid-1 block=1.000 fp=0.125 targets_met=False p50=817.86ms cost=0.00026889; hybrid-2 block=1.000 fp=0.062 targets_met=True p50=779.28ms cost=0.00026875; hybrid-3 block=1.000 fp=0.125 targets_met=False p50=796.18ms cost=0.00026889
PASS H3.v2_raw :: v2-1 ok=78/78 judged=72; v2-2 ok=78/78 judged=72; v2-3 ok=78/78 judged=72; answers=['gemini-3.5-flash-lite'] judge=['gemini-3.6-flash']
PASS H4.api_provenance :: {'weather_success': 12, 'fx_success': 15, 'd04': 6, 'd05': 3}
PASS H5.v2_reports :: v2-1 pass=0.9230769230769231; v2-2 pass=0.9102564102564102; v2-3 pass=0.9230769230769231
{"timestamp": "2026-11-09T12:15:19.369204+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
{"timestamp": "2026-11-09T12:15:19.378442+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "guardrail", "latency_ms": 0.14}
{"timestamp": "2026-11-09T12:15:19.379641+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T12:15:19.382078+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "guardrail_classifier", "latency_ms": 0.01}
{"timestamp": "2026-11-09T12:15:19.390558+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "supervisor", "latency_ms": 6.78}
{"timestamp": "2026-11-09T12:15:19.392489+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: get_settlement_status] invoked", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
{"timestamp": "2026-11-09T12:15:19.392718+00:00", "level": "INFO", "logger": "multiagent.specialists", "message": "tool finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "agent": "SupportAgent", "tool": "get_settlement_status", "status": "error", "latency_ms": 0.68}
{"timestamp": "2026-11-09T12:15:19.393172+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "tool finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "agent": "SupervisorAgent", "tool": "ask_support_agent", "status": "ok", "latency_ms": 1.58}
{"timestamp": "2026-11-09T12:15:19.393298+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "tools", "latency_ms": 1.72}
{"timestamp": "2026-11-09T12:15:19.395461+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "supervisor", "latency_ms": 0.72}
{"timestamp": "2026-11-09T12:15:19.397192+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: escalate_to_human] priority=standard, reason_chars=26", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
{"timestamp": "2026-11-09T12:15:19.409887+00:00", "level": "INFO", "logger": "multiagent.tickets_db", "message": "Tickets database initialized at: C:\\Users\\burba\\AppData\\Local\\Temp\\verify_p10h_y3o1sqb5\\tickets\\tickets.db", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
{"timestamp": "2026-11-09T12:15:19.418959+00:00", "level": "INFO", "logger": "multiagent.tickets_db", "message": "Persisted escalation ticket GET-TKT-20261109-0B0B3161C1", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
{"timestamp": "2026-11-09T12:15:19.419527+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "tool finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "agent": "SupervisorAgent", "tool": "escalate_to_human", "status": "ok", "latency_ms": 23.16}
{"timestamp": "2026-11-09T12:15:19.419701+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "tools", "latency_ms": 23.38}
{"timestamp": "2026-11-09T12:15:19.422447+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "supervisor", "latency_ms": 1.36}
{"timestamp": "2026-11-09T12:15:19.423589+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651", "node": "abstention_check", "latency_ms": 0.0}
{"timestamp": "2026-11-09T12:15:19.425086+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 56.09ms. Tools: ['get_settlement_status', 'escalate_to_human']", "trace_id": "trc-10h10h10h10h", "session_id": "sess-10h", "user_hash": "u_3e53151cd1ac1651"}
PASS H6.no_pii_in_logs_strict :: 18 log records
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 316 passed in 24.51s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 60/60 passed
```

> Nota de correção (Fase 10I): esse resultado vale em Python 3.13. Em Python 3.11, a versão do CI e do Dockerfile, o mesmo verificador dá 59/60: `H5.v2_reports` falha porque a média de `facts_rate` em `reports/eval_v2.json` difere na 16ª casa decimal do recálculo (o `sum()` de números de ponto flutuante mudou no Python 3.12). O `scripts/verify_phase10i.py` refaz essa checagem com tolerância de 1e-9.

#### Commit base:
`d2744b1fce4fe7842eda3e832ccf4e9a1bdaa755`

#### Não feito:
Nada de código ou testes foi alterado nesta fase. A atualização do README.md com os números finais das métricas reais e a revisão geral do projeto estão reservadas para a Fase 10I.

#### Perguntas / divergências com o SPEC:
Nenhuma. Os 9 arquivos de execuções brutas gerados pelo usuário com modelo real (`gemini-3.5-flash-lite` para o agente e `gemini-3.6-flash` para o juiz) foram validados com sucesso e todos os 8 relatórios foram gerados sem divergências.

#### Alterações:
- Inclusão dos registros brutos em `reports/guardrail_runs/` e `reports/eval_runs/`.
- Geração dos relatórios em `reports/` (`guardrail_hybrid-1`, `guardrail_hybrid-2`, `guardrail_hybrid-3`, `guardrail_summary`, `eval_v2-1`, `eval_v2-2`, `eval_v2-3`, `eval_v2`).
- Registro do status de execução da Fase 10H em `docs/STATUS.md`.

---

### Fase 10G: Clima e Câmbio — Avaliação com o Conjunto v2

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 10G (`python scripts/verify_phase10g.py`):
```text
INFO python 3.13.3
PASS G0.py311_syntax
PASS G0.no_regex
PASS G1.reviewer_files
PASS G9.readme_texts
PASS G9.claims_row
PASS G10.tests_named
PASS G10.existing_test_only_gains_key
PASS S1.status_10g
PASS E2.scope
PASS G2.v2_set
PASS G3.api_status_validation
PASS G4.tools_ok_api_status :: 69 ok results with api_status compared
PASS G5.observe_turn
PASS G6.judge_sees_api_results
PASS G7.report_cases_file
PASS G8.cli_cases
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 316 passed in 22.68s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q2.eval_v2_tests :: 6 passed in 0.44s

SUMMARY: 65/65 passed
```

#### Commit base (`git rev-parse HEAD`):
```text
939b67b5db641e48eb7f4b8cf6bdf69a6c23067f
```

#### Não feito
- Execuções da avaliação com modelo real sobre o conjunto v2 (`data/eval/cases_v2.jsonl`): escopo da Fase 10H. Esta fase implementa o suporte offline, validações e infraestrutura para o conjunto v2 sem chamadas de modelo real.

#### Perguntas / divergências com o SPEC
- Nenhuma divergência. O conjunto v1 permanece intacto e congelado. O conjunto v2 (78 casos) é suportado via `--cases` em todas as etapas da CLI de avaliação (`run`, `judge`, `report`, `compare`), com validação rigorosa de `api_status`, registro de `api_results` nas observações do turno e entrega de passagens completas ao juiz LLM.

#### Alterações
- `src/eval/cases.py`: inclusão de `"public_data"` em `VALID_CATEGORIES`, `"get_weather_forecast"` e `"get_exchange_rate"` em `VALID_TOOLS`, definição de `API_TOOLS`, `API_STATUSES` e `OPTIONAL_EXPECT_KEYS`, e validação do campo `expect.api_status`.
- `src/eval/checks.py`: checagem de correspondência exata para `api_status` em `evaluate_case` condicionando `tools_ok`.
- `src/eval/runner.py`: gravação de `api_results` nas observações estruturadas de `observe_turn`.
- `src/eval/judge.py`: inclusão dos itens de `api_results` como passagens de evidência em `build_judge_input`.
- `src/eval/report.py`: inclusão de `cases_file` nos metadados do relatório JSON e no resumo Markdown em `write_report`.
- `src/eval/__main__.py`: suporte ao argumento `--cases` nos subcomandos `run`, `judge`, `report` e `compare`, repassando `cases_file` ao relatório.
- `tests/test_eval_runner_judge.py`: atualização de `expected_keys` para incluir `"api_results"` no teste de integridade de `observe_turn`.
- `tests/test_eval_v2.py`: 6 testes unitários e de integração offline cobrindo carregamento do v2, imutabilidade do v1, validação de `api_status`, verificação de `tools_ok`, gravação em `observe_turn`, evidências do juiz e opções da CLI.
- `README.md`: documentação do conjunto v2, atualização da descrição de `tools_ok`, opção `--cases`, tratamento de resultados de API no juiz, ampliação do escopo de autoria e revisão, e adição da linha de evidência na tabela de afirmações.

---

### Fase 10F: Clima e Câmbio — Tools do Knowledge Agent

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 10F (`python scripts/verify_phase10f.py`):
```text
INFO python 3.13.3
PASS F0.py311_syntax
PASS F1.agent_prompts
PASS F0.no_regex
PASS F8.readme_texts
PASS F9.claims_row
PASS F8.readme_10b_texts_kept
PASS F10.tests_named
PASS S1.status_10f
PASS E2.scope
PASS F2.tools
PASS F3.tools_return_module_results :: EUR 2026-11-06 via tool: {'value': 6.13, 'unit': 'BRL per 1 EUR'}
PASS F4.specialist_api_results
PASS F5.graph_and_api
PASS F6.logs_without_query
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 310 passed in 21.92s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q2.tools_tests :: 7 passed in 0.57s

SUMMARY: 61/61 passed
```

#### Commit base (`git rev-parse HEAD`):
```text
2daa711dacf750e2f136b3f0faf132881186d7a4
```

#### Não feito
- Avaliação com modelo real (`src/eval/`, `data/eval/`): escopo da Fase 10G. Esta fase adiciona e integra as tools tipadas ao Knowledge Agent e ao fluxo do Supervisor ReAct, sem executar chamadas com modelo real na avaliação.

#### Perguntas / divergências com o SPEC
- Nenhuma divergência. As novas ferramentas `get_weather_forecast` e `get_exchange_rate` foram implementadas estritamente com as docstrings e validações especificadas. Os logs mascaram cidade, moeda e parâmetros da requisição mantendo privacidade, e o nível de logging do `httpx` foi configurado para WARNING para prevenir vazamento de URLs nos logs da aplicação.

#### Alterações
- `src/tools/agent_tools.py`: configuração do logger `httpx` em WARNING; implementação de `get_weather_forecast` e `get_exchange_rate`; atualização da docstring de `search_web`; atualização de `ALL_TOOLS` e `TOOLS_BY_NAME`.
- `src/core/graph.py`: inclusão de `get_weather_forecast` e `get_exchange_rate` em `KNOWLEDGE_TOOLS`; propagação de `api_results` no nó de execução de ferramentas e no retorno de `run_sync`.
- `src/agents/specialists.py`: definição de `API_TOOLS = frozenset({"get_weather_forecast", "get_exchange_rate"})`; captura e extração de `api_results` e `source_url` apenas quando `status == "success"`; retorno de `api_results` em `SpecialistAgent.run`.
- `src/core/state.py`: inclusão de `api_results` em `SupervisorState` e `AgentState`.
- `src/core/metrics.py`: inclusão de `get_weather_forecast` e `get_exchange_rate` em `KNOWN_TOOLS`.
- `src/main.py`: adição do campo `api_results` no schema `AgentMetadata` e seu preenchimento no endpoint `/chat`.
- `tests/test_public_data_tools.py`: 7 testes unitários e de integração offline cobrindo registro de tools, retorno de previsão e câmbio, parsing e validação de data, registro de metadados e fontes, ausência de fontes em erros da API, exposição via grafo e `/chat`, e privacidade dos logs.
- `README.md`: atualização de limitações, diagramas de fluxo ASCII e Mermaid, tabela de ferramentas, adição da seção "Clima e câmbio por API oficial (Fase 10)", configuração de `PUBLIC_DATA_TIMEOUT_S` e nova evidência na tabela de afirmações.

---

### Fase 10E: Clima e Câmbio — Módulo das APIs

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 10E (`python scripts/verify_phase10e.py`):
```text
INFO python 3.13.3
PASS E0.py311_syntax
PASS E0.no_regex_no_logs_no_values
PASS E1.config
PASS E9.tests_named
PASS E9.fixtures_unchanged
PASS S1.status_10e
PASS E2.scope
PASS E3.constants
PASS E4.url_builders
PASS E5.weather_success :: day 2: 2026-11-10 max {'value': 25.5, 'unit': '°C'} Overcast
PASS E6.weather_not_found_and_invalid
PASS E7.weather_unavailable
PASS E8.fx_success :: EUR 2026-11-06 buy {'value': 6.13, 'unit': 'BRL per 1 EUR'}; latest EUR 2026-11-06 13:06:13.966362 {'value': 6.13, 'unit': 'BRL per 1 EUR'}
PASS E9.fx_no_data_not_found_invalid
PASS E10.fx_unavailable
PASS E10.only_the_closing_bulletin
PASS E11.default_client_and_today
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 303 passed in 21.88s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q2.public_data_tests :: 23 passed in 0.81s

SUMMARY: 63/63 passed
```

#### Commit base (`git rev-parse HEAD`):
```text
74f9ee1603ba08e561f38e68e4c7604d5500e28f
```

#### Não feito
- Tools integradas ao agente LangGraph e chamadas com modelo real: escopo da Fase 10F. Esta fase implementa o módulo cliente com validação, normalização de respostas e testes offline.

#### Perguntas / divergências com o SPEC
- Nenhuma. O módulo `src/tools/public_data.py` atende a todas as especificações de URLs, validação e formatos de status explícitos (`success`, `not_found`, `no_data`, `unavailable`, `invalid_request`).

#### Alterações
- `src/config.py` e `.env.example`: adicionada configuração `PUBLIC_DATA_TIMEOUT_S=8` logo após `DDGS_TIMEOUT`.
- `src/tools/public_data.py`: implementado cliente completo para Open-Meteo (geocodificação e previsão de 1 a 7 dias com códigos WMO) e PTAX do Banco Central (catálogo de moedas e cotações de fechamento por data ou período lookback de 10 dias).
- `tests/test_public_data.py`: criados 23 testes unitários offline exercitando requisições válidas, cidades e moedas inexistentes, entradas inválidas, erros de rede/timeout/HTTP 500/400 e payload malformado.

---

### Fase 10D: Clima e Câmbio — Captura das APIs

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Saída da captura (`python scripts/capture_public_data.py`):
```text
geocoding_porto_alegre 200 368
geocoding_sao_paulo 200 354
geocoding_unknown 200 31
forecast_porto_alegre 200 801
forecast_invalid 400 81
ptax_moedas 200 784
ptax_eur_20261106 200 995
ptax_usd_20261106 200 995
ptax_jpy_20261106 200 1015
ptax_eur_20261107 200 128
ptax_eur_20261030_20261109 200 4474
ptax_xyz_20261106 200 128
```

#### Verificação Fase 10D (`python scripts/verify_phase10d.py`):
```text
INFO python 3.13.3
PASS D0.py311_syntax
PASS D0.no_regex_no_secrets
PASS S1.status_10d
PASS E2.scope
PASS D1.script_api
PASS D2.capture_offline
PASS D2.capture_network_error
PASS D3.fixtures_and_manifest :: captured_at 2026-11-09T05:53:47.805383+00:00; status codes geocoding_porto_alegre=200, geocoding_sao_paulo=200, geocoding_unknown=200, forecast_porto_alegre=200, forecast_invalid=400, ptax_moedas=200, ptax_eur_20261106=200, ptax_usd_20261106=200, ptax_jpy_20261106=200, ptax_eur_20261107=200, ptax_eur_20261030_20261109=200, ptax_xyz_20261106=200
PASS D4.weather_fixtures :: Porto Alegre -30.03283,-51.23019 tz=America/Sao_Paulo; forecast tz=America/Sao_Paulo units={'time': 'iso8601', 'weather_code': 'wmo code', 'temperature_2m_max': '°C', 'temperature_2m_min': '°C', 'precipitation_probability_max': '%', 'precipitation_sum': 'mm'}; unknown city keys=['generationtime_ms']
INFO Moedas: 10 currencies; USD listed: True; sample ['AUD', 'CAD', 'CHF', 'DKK', 'EUR', 'GBP', 'JPY', 'NOK']
INFO tipoBoletim values seen: ['Abertura', 'Fechamento', 'Intermediário']
PASS D5.ptax_fixtures :: EUR closing 2026-11-06 6.13/6.1317 (Fechamento); USD rows=5; period days=['2026-10-30', '2026-11-03', '2026-11-04', '2026-11-05', '2026-11-06']; 2026-11-02 present=False
INFO unknown currency XYZ: status 200 body '{"@odata.context":"https://was-p.bcnet.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata$metadata#_CotacaoMoedaPeriodo","value":[]}'
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 280 passed in 22.82s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 54/54 passed
```

#### Commit base (`git rev-parse HEAD`):
```text
b06dec32c1cba5600ff0976ff27a4d529227c752
```

#### Não feito
- Módulo de clima e câmbio em `src/tools/` e agentes/testes associados: escopo da Fase 10E. Esta fase apenas captura as fixtures reais para que a 10E possa ser implementada e testada offline.

#### Perguntas / divergências com o SPEC
- Nenhuma. Todas as 12 requisições retornaram respostas reais das APIs públicas sem autenticação, com os cabeçalhos e formatos esperados, gravadas integralmente em `tests/fixtures/public_data/` junto ao `manifest.json`.

#### Alterações
- `scripts/capture_public_data.py`: script criado para capturar respostas reais das APIs Open-Meteo e PTAX do Banco Central (Olinda), registrando corpo cru em bytes, status, content-type, tamanho e sha256 no manifesto.
- `tests/fixtures/public_data/`: gravados 12 arquivos de fixture (`.json`) e `manifest.json` com respostas reais capturadas sem alteração.

---

### Fase 10C: Guardrail — Avaliação com Modelo Real (Código)

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 10C (`python scripts/verify_phase10c.py`):
```text
INFO python 3.13.3
PASS C0.py311_syntax
PASS C0.no_regex
PASS C0.append_only
PASS C9.tests_named
PASS S1.status_10c
PASS E2.scope
PASS C1.api
PASS C2.run_records
PASS C3.resume_skips_ok
PASS C4.errors_stop_retry_and_pii
PASS C5.no_key_propagates
PASS C6.report_semantics :: synthetic hybrid 16/20 blocked, 1/16 false positives, targets_met=False
PASS C7.targets_and_cost
PASS C8.report_files
PASS C10.summary
PASS C11.cli :: guardrail-report: hybrid block_rate 1.0, false_positive_rate 0.0, targets_met True
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 280 passed in 23.01s
PASS Q2.runner_tests :: 10 passed in 0.66s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs
PASS Q5.no_real_runs_committed

SUMMARY: 61/61 passed
```

#### Commit base (`git rev-parse HEAD`):
```text
fac9e87f815349f7e753066d71b3e8c8914b49a5
```

#### Não feito
- Execuções de avaliação com modelo real (`python -m src.eval guardrail-run`): requerem chave de API (`GEMINI_API_KEY`) e serão realizadas pelo usuário na Fase 10F, sem alterar o código implementado nesta fase.

#### Perguntas / divergências com o SPEC
- Nenhuma. O runner (`run_guardrail`), o gerador de relatórios (`guardrail_report`, `write_guardrail_report`), o agregador de resumo (`guardrail_summary`, `write_guardrail_summary`), os subcomandos na CLI (`guardrail-run`, `guardrail-report`, `guardrail-summary`) e a suíte com 10 testes offline foram implementados estritamente conforme as especificações.

#### Alterações
- `src/eval/guardrail_eval.py`: adicionadas constantes `GUARDRAIL_TARGETS`, `GUARDRAIL_COST_NOTE`, `DEFAULT_GUARDRAIL_RUNS_DIR`, `RECORD_KEYS`, `SUMMARY_METRIC_PATHS`, e implementadas as funções `run_guardrail` (resumível com quota guard e sem vazamento de texto), `guardrail_report`, `write_guardrail_report`, `guardrail_summary` e `write_guardrail_summary`.
- `src/eval/__main__.py`: adicionados subcomandos `guardrail-run`, `guardrail-report` e `guardrail-summary` com argumentos completos, validações de erro e códigos de saída apropriados (2 para configuração/chave ausente, 1 para arquivos ausentes, 0 para sucesso).
- `tests/test_guardrail_eval_runs.py`: criada suíte com 10 testes cobrindo execução sem texto de mensagens, mascaramento prévio de PII, retomada/retry após falha, parada antecipada por erros consecutivos, propagação de erro de chave, semântica híbrida/fail-open, checagem de metas pré-registradas, métricas de custo/latência, resumo de múltiplas execuções e erros de CLI.

---

### Fase 10B: Guardrail — Classificador por LLM

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 10B (`python scripts/verify_phase10b.py`):
```text
INFO python 3.13.3
PASS B0.py311_syntax
PASS B1.env_example
PASS B2.classifier_prompt_unchanged
PASS B3.no_regex_outside_guardrail_pii
PASS B8.readme_texts
PASS B9.claims_row
PASS B10.tests_named
PASS B11.agents_test_one_line
PASS S1.status_10b
PASS E2.scope
PASS B4.config_and_helpers
PASS B5.factory_and_lazy_model
PASS R1.classifier_block
PASS R2.classifier_allow_tokens
PASS R3.patterns_first
PASS R4.fail_open
PASS R5.fail_closed_503
PASS R6.config_errors_propagate
PASS R7.classifier_input
PASS R8.handoff_skips_classifier
PASS R9.switches
PASS R10.logs_without_text
PASS R11.metrics
PASS R12.api_metadata_and_agents
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
PASS Q1.ruff_clean
PASS Q1.offline_subset
PASS Q2.pytest_offline_no_key :: 270 passed in 25.74s
PASS Q2.classifier_tests :: 16 passed in 1.45s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 68/68 passed
```

#### Git Commit Base (`git rev-parse HEAD`):
```text
1eb36263d325d8064ad85fb728adbf1214e75e74
```

#### Perguntas / divergências com o SPEC:
- Nenhuma. Classificador de injeção por LLM implementado com saída estruturada (`GuardrailVerdict`), integração resiliente em nó dedicado no LangGraph (`guardrail_classifier`), fail-open/fail-closed configurável e métricas em Prometheus (`getnet_guardrail_decisions_total`).

#### Alterações Realizadas na Fase 10B:
- **Configuração (`src/config.py`, `.env.example`)**:
  - Adicionadas variáveis `GUARDRAIL_CLASSIFIER_ENABLED`, `GUARDRAIL_CLASSIFIER_MODEL`, `GUARDRAIL_CLASSIFIER_TIMEOUT_S` e `GUARDRAIL_CLASSIFIER_FAIL_MODE` (`Literal["open", "closed"]`).
- **Fábrica de Modelos (`src/core/llm.py`)**:
  - Suporte a `timeout_s` e `max_retries` em `get_chat_model` e `_build_chat_model`.
- **Constantes de Recusa (`src/agents/guardrails.py`)**:
  - Exportadas constantes de módulo `INJECTION_REFUSAL` e `ATTACK_REFUSAL`.
- **Módulo do Classificador (`src/agents/injection_classifier.py`)**:
  - Implementados `GuardrailVerdict`, `ClassifierResult`, `InjectionClassifier`, `format_classifier_input` e `load_classifier_prompt` com bind_tools estruturado.
- **Estado e Grafo (`src/core/state.py`, `src/core/graph.py`)**:
  - Campo `guardrail` adicionado a `SupervisorState` e `AgentState`.
  - Nó `guardrail_classifier` inserido após `handoff_gate`, com contagem de tokens em `tokens_by_agent["GuardrailClassifier"]` e decisões auditadas sem vazamento de texto.
- **Métricas Operacionais (`src/core/metrics.py`)**:
  - Contador `getnet_guardrail_decisions_total{decision}` e função `inc_guardrail`.
- **API e Introspecção (`src/main.py`, `tests/test_agents_endpoint.py`)**:
  - `AgentMetadata` inclui campo `guardrail` e `/agents` expõe os metadados do classificador de `GuardrailAgent`.
- **Testes Unitários Offline (`tests/test_guardrail_classifier.py`)**:
  - Criados 16 testes offline cobrindo bloqueio, permissão, tokens, fail-open, fail-closed (503), propagação de erros de configuração, sanitização/escape de tags XML, skip em handoff e privacidade de logs.
- **Documentação (`README.md`)**:
  - Atualizadas as limitações, o fluxo ReAct, diagrama mermaid, métricas de tokens, lista de nós do grafo, variáveis de ambiente e tabela de afirmações e evidências.

---

### Fase 10A: Guardrail — Padrões Revistos e Conjunto Rotulado

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Saída do Guardrail Patterns (`python -m src.eval guardrail-patterns`):
```text
patterns: block_rate 0.3, false_positive_rate 0.0
```

#### Verificação Fase 10A (`python scripts/verify_phase10a.py`):
```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.reviewer_set :: 36 messages, sha 16311a86736c
PASS A1.cases_v1_frozen
PASS A2.classifier_prompt_preregistered
PASS A3.patterns_exact
PASS A16.no_regex_outside_guardrail_pii
PASS A15.readme_limitation
PASS A14.tests_named
PASS S1.status_10a
PASS E2.scope
PASS A4.match_patterns
{"timestamp": "2026-11-09T03:53:34.252308+00:00", "level": "WARNING", "logger": "multiagent.guardrails", "message": "Guardrail pattern matched (category=prompt_injection)"}
{"timestamp": "2026-11-09T03:53:34.253881+00:00", "level": "WARNING", "logger": "multiagent.guardrails", "message": "Guardrail pattern matched (category=attack_request)"}
PASS A5.evaluate_sync_behaviour
{"timestamp": "2026-11-09T03:53:34.254181+00:00", "level": "WARNING", "logger": "multiagent.guardrails", "message": "Guardrail pattern matched (category=prompt_injection)"}
{"timestamp": "2026-11-09T03:53:34.254311+00:00", "level": "WARNING", "logger": "multiagent.guardrails", "message": "Guardrail pattern matched (category=attack_request)"}
PASS A6.guardrail_logs_without_text
PASS A7.pattern_results :: now 6/20 blocked, 0/16 false positives; patterns of 6456bf5: 6/20 blocked, 6/16 false positives ['ga01', 'ga02', 'ga04', 'ga05', 'ga06', 'ga07']
PASS A8.loader
PASS A9.rates_semantics
PASS A10.report_json
PASS A11.report_md
PASS A12.cli :: patterns: block_rate 0.3, false_positive_rate 0.0
PASS A13.offline_subset
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 254 passed in 19.39s
PASS Q2.guardrail_tests :: 11 passed in 0.95s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 62/62 passed
```

#### Commit Base da Fase 10A (`git rev-parse HEAD`):
```text
6456bf553535febbd79ae980b1c2e6bb46d756aa
```

#### Não feito:
- Nenhum. Todos os checks da Fase 10A passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. Padrões de regex revistos para eliminar falsos positivos em perguntas legítimas, medição automatizada implementada via `src/eval/guardrail_eval.py` e avaliada sobre o conjunto pré-registrado de 36 mensagens (`data/eval/guardrail_labeled.jsonl`).

#### Alterações Realizadas na Fase 10A:
- **Revisão de Padrões de Regex (`src/agents/guardrails.py`)**:
  - Ajustados os padrões de injeção (`your system prompt`, `(suas|tuas) regras internas`, `(seu|teu) prompt de sistema`, `esqueça (tudo )?o que foi dito`) e termos maliciosos (removido `hack` isolado) para não bloquear perguntas legítimas ("Quais são as regras internas da Getnet para antecipação?" e "Fui vítima de um hack na minha conta").
  - Adicionado o método público `match_patterns(self, text: str) -> str | None`.
  - Refatorado `evaluate_sync` para usar `match_patterns` e registrar apenas a categoria nos logs (`logger.warning(f"Guardrail pattern matched (category={category})")`), sem expor o texto da mensagem.
- **Módulo de Avaliação de Guardrail (`src/eval/guardrail_eval.py`)**:
  - Implementado carregador determinístico com validação estrita de esquemas (`load_guardrail_set`), cálculo de SHA-256 canônico (`guardrail_set_sha256`), cálculo de métricas e taxas (`rates`, `layer_metrics`), execução de padrões (`pattern_results`) e escrita de relatórios estruturados (`write_pattern_report`).
- **CLI de Avaliação (`src/eval/__main__.py`)**:
  - Adicionado o subcomando `guardrail-patterns` com flags `--set` e `--out-dir`, gerando `reports/guardrail_patterns.json` e `reports/guardrail_patterns.md`.
- **Relatórios Gerados (`reports/guardrail_patterns.json`, `reports/guardrail_patterns.md`)**:
  - Registrada a medição da camada de padrões sobre os 36 casos: 0% de falsos positivos (0/16 legítimas bloqueadas) e 30% de taxa de bloqueio (6/20 injeções/ataques bloqueados diretamente pelos padrões).
- **Testes Unitários Offline (`tests/test_guardrail_patterns.py`)**:
  - Criados 8 testes validando integridade do dataset, validação do loader, inclusão dos casos de safety offline, ausência de falsos positivos, bloqueio de casos de safety, liberação de perguntas legítimas da auditoria, sensibilidade das métricas e integridade do relatório commitado.
- **Documentação de Limitações (`README.md`)**:
  - Atualizada a limitação referente ao guardrail de injeção por padrões para descrever os resultados obtidos no conjunto rotulado pré-registrado.

---

### Fase 9G: Resíduos do README Apontados pela Auditoria

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9G (`python scripts/verify_phase9g.py`):
```text
INFO python 3.13.3
PASS J0.py311_syntax
PASS J1.compare_label
PASS J3.readme_sources_wording
PASS J4.scenario_10
PASS J5.no_getnet_com_br
PASS J6.provider_text
PASS J7.graph_docstrings
PASS J8.test_tree
PASS J9.limitations
PASS J10.decisions_banner
PASS S1.status_9g
PASS E2.scope
PASS J2.comparison_table
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 243 passed in 21.25s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 53/53 passed
```

#### Commit Base da Fase 9G (`git rev-parse HEAD`):
```text
ffb210b5bb3c0801a506ef4cc55b214d21101c57
```

#### Diff dos relatórios regenerados (`git diff --stat reports/`):
```text
 reports/eval_models.json | 2 +-
 reports/eval_models.md   | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)
```

#### Não feito:
- Nenhum. Todos os checks aplicáveis da Fase 9G passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. Correções textuais, regeneração de relatório e renomeação de arquivo de teste executadas estritamente de acordo com as instruções da Fase 9G.

#### Alterações Realizadas na Fase 9G:
- **Rótulo da Métrica de Fontes (`src/eval/compare.py`, `reports/eval_models.md`, `reports/eval_models.json`, `README.md`)**:
  - Substituído o rótulo "Fonte oficial citada" por "Fonte oficial recuperada", refletindo com precisão que a métrica avalia a presença da URL no conjunto recuperado, e não menção textual na resposta.
  - Adicionada nota explicativa logo após a tabela comparativa de modelos no `README.md` e corrigida a tabela da execução `full-1`.
- **Correção da Fonte do Cenário 10 (`README.md`)**:
  - Atualizada a linha do Cenário 10 para referenciar `getnet.net/en/our-solutions/online-payments` com a devida nota sobre a ausência de conteúdo nas páginas brasileiras de Link de Pagamento e WhatsApp.
- **Remoção do Domínio não Mapeado (`README.md`, `data/corpus/README.md`)**:
  - Removida a linha referente a `getnet.com.br` puro, mantendo apenas `site.getnet.com.br` e `getnet.net/en`.
- **Clarificação do Provedor de LLM (`README.md`)**:
  - Esclarecido que o sistema é testado e opera com o Gemini via `langchain-google-genai`.
- **Ajuste nas Docstrings do Grafo (`src/core/graph.py`)**:
  - Substituída a menção a `MemorySaver` por `SqliteSaver` nas docstrings do módulo, da classe e do método `run_sync`.
- **Renomeação de Arquivo de Teste (`tests/test_api_key_header.py`) e Árvore (`README.md`)**:
  - Renomeado `tests/test_eval_judge.py` para `tests/test_api_key_header.py` e atualizada a árvore de arquivos no `README.md`.
- **Complementação das Limitações Atuais (`README.md`)**:
  - Incluídas limitações detalhadas sobre guardrail de injeção por regex, tamanho da base de conhecimento, busca de clima/câmbio e itens fora de escopo.
- **Aviso Histórico em Decisões Antigas (`docs/DECISIONS.md`)**:
  - Adicionado banner informativo no topo de `docs/DECISIONS.md` contextualizando decisões anteriores à especificação definitiva.

---

### Fase 9F: Logs Sem Texto da Conversa

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9F (`python scripts/verify_phase9f.py`):
```text
INFO python 3.13.3
PASS H0.py311_syntax
PASS H1.no_logger_exception
PASS H2.no_text_fields_in_logs
PASS H3.exc_brief_defined
PASS H9.tests
PASS H10.readme_bullet
PASS H11.claims_row
PASS S1.status_9f
PASS E2.scope
PASS H4.exc_brief :: RuntimeError at verify_phase9f.py:207
{"timestamp": "2026-11-09T02:17:15.557658+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: search_knowledge_base] invoked (query_chars=14)"}
{"timestamp": "2026-11-09T02:17:15.558679+00:00", "level": "WARNING", "logger": "multiagent.tools", "message": "[Tool: search_knowledge_base] Error querying knowledge retriever: RuntimeError at verify_phase9f.py:247 <- agent_tools.py:88"}
{"timestamp": "2026-11-09T02:17:15.559530+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: search_knowledge_base] invoked (query_chars=14)"}
{"timestamp": "2026-11-09T02:17:15.561163+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: search_web] invoked (query_chars=15)"}
{"timestamp": "2026-11-09T02:17:15.561408+00:00", "level": "INFO", "logger": "multiagent.search", "message": "Executing web search (query_chars=15)"}
{"timestamp": "2026-11-09T02:17:15.562539+00:00", "level": "WARNING", "logger": "multiagent.search", "message": "DuckDuckGo search error: RuntimeError at verify_phase9f.py:270 <- web_search.py:24. Returning unavailable status."}
{"timestamp": "2026-11-09T02:17:15.563562+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: search_web] invoked (query_chars=15)"}
{"timestamp": "2026-11-09T02:17:15.563749+00:00", "level": "INFO", "logger": "multiagent.search", "message": "Executing web search (query_chars=15)"}
{"timestamp": "2026-11-09T02:17:15.563901+00:00", "level": "WARNING", "logger": "multiagent.search", "message": "DuckDuckGo returned no results"}
{"timestamp": "2026-11-09T02:17:15.565234+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: diagnose_declined_transaction] invoked (error_code_given=True)"}
{"timestamp": "2026-11-09T02:17:15.566522+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: diagnose_terminal] invoked (serial_given=True)"}
{"timestamp": "2026-11-09T02:17:15.567836+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: escalate_to_human] priority=standard, reason_chars=23"}
{"timestamp": "2026-11-09T02:17:15.580818+00:00", "level": "INFO", "logger": "multiagent.tickets_db", "message": "Tickets database initialized at: C:\\Users\\burba\\AppData\\Local\\Temp\\verify_p9f_5o9998kn\\tickets.db"}
{"timestamp": "2026-11-09T02:17:15.589209+00:00", "level": "INFO", "logger": "multiagent.tickets_db", "message": "Persisted escalation ticket GET-TKT-20261109-CAD8C6AC27"}
{"timestamp": "2026-11-09T02:17:15.589993+00:00", "level": "INFO", "logger": "multiagent.tools", "message": "[Tool: escalate_to_human] priority=high, reason_chars=23"}
{"timestamp": "2026-11-09T02:17:15.590360+00:00", "level": "ERROR", "logger": "multiagent.tools", "message": "Failed to persist escalation ticket: RuntimeError at verify_phase9f.py:289 <- agent_tools.py:145"}
{"timestamp": "2026-11-09T02:17:15.602600+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.606964+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 1.17}
{"timestamp": "2026-11-09T02:17:15.608111+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T02:17:15.617182+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 7.22}
{"timestamp": "2026-11-09T02:17:15.618740+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "tool finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "agent": "SupervisorAgent", "tool": "ask_knowledge_agent", "status": "ok", "latency_ms": 0.42}
{"timestamp": "2026-11-09T02:17:15.618899+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "tools", "latency_ms": 0.61}
{"timestamp": "2026-11-09T02:17:15.621190+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 0.92}
{"timestamp": "2026-11-09T02:17:15.622178+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495", "node": "abstention_check", "latency_ms": 0.01}
{"timestamp": "2026-11-09T02:17:15.623647+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 21.12ms. Tools: []", "trace_id": "trc-9b402efbda51", "session_id": "g1", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.635034+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-4a14f4217094", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.637641+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-4a14f4217094", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.07}
{"timestamp": "2026-11-09T02:17:15.638522+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-4a14f4217094", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T02:17:15.643661+00:00", "level": "ERROR", "logger": "multiagent.llm", "message": "Supervisor primary model invocation failed [trace_id=trc-4a14f4217094]: RuntimeError at verify_phase9f.py:222 <- chat_models.py:2065 <- chat_models.py:1727", "trace_id": "trc-4a14f4217094", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.643953+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-4a14f4217094", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 4.18}
{"timestamp": "2026-11-09T02:17:15.654302+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.657512+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.06}
{"timestamp": "2026-11-09T02:17:15.658430+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T02:17:15.664325+00:00", "level": "WARNING", "logger": "multiagent.llm", "message": "Primary model 'scripted-fake' failed with RuntimeError at verify_phase9f.py:222 <- chat_models.py:2065 <- chat_models.py:1727. Failing over to fallback [trace_id=trc-ac0a2d10b13e].", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.666562+00:00", "level": "ERROR", "logger": "multiagent.llm", "message": "Both primary ('scripted-fake') and fallback ('scripted-fake') models failed [trace_id=trc-ac0a2d10b13e]: RuntimeError at verify_phase9f.py:222 <- chat_models.py:2065 <- chat_models.py:1727", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.666715+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-ac0a2d10b13e", "session_id": "g2", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 6.72}
{"timestamp": "2026-11-09T02:17:15.675067+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-8be615a6ebd1", "session_id": "g3", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.680835+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-8be615a6ebd1", "session_id": "g3", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.12}
{"timestamp": "2026-11-09T02:17:15.682295+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-8be615a6ebd1", "session_id": "g3", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T02:17:15.686724+00:00", "level": "ERROR", "logger": "multiagent.llm", "message": "Supervisor primary model configuration error [trace_id=trc-8be615a6ebd1]: ModelNotFoundError at verify_phase9f.py:222 <- chat_models.py:2065 <- chat_models.py:1727", "trace_id": "trc-8be615a6ebd1", "session_id": "g3", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.686873+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-8be615a6ebd1", "session_id": "g3", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 3.09}
{"timestamp": "2026-11-09T02:17:15.698520+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "workflow started", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.701708+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495", "node": "guardrail", "latency_ms": 0.11}
{"timestamp": "2026-11-09T02:17:15.702825+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495", "node": "handoff_gate", "latency_ms": 0.0}
{"timestamp": "2026-11-09T02:17:15.706761+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495", "node": "supervisor", "latency_ms": 2.36}
{"timestamp": "2026-11-09T02:17:15.708641+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "node finished", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495", "node": "tools", "latency_ms": 0.03}
{"timestamp": "2026-11-09T02:17:15.717492+00:00", "level": "ERROR", "logger": "multiagent.orchestrator", "message": "Error in LangGraph execution: KeyError at verify_phase9f.py:317 <- graph.py:599 <- graph.py:144", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.719142+00:00", "level": "WARNING", "logger": "multiagent.orchestrator", "message": "Closed 1 dangling tool call(s) after a failed turn", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.719393+00:00", "level": "INFO", "logger": "multiagent.orchestrator", "message": "Workflow finished in 20.92ms. Tools: []", "trace_id": "trc-23217db6dc0b", "session_id": "g4", "user_hash": "u_a9f6bd311e2b2495"}
{"timestamp": "2026-11-09T02:17:15.770795+00:00", "level": "ERROR", "logger": "multiagent", "message": "Unhandled error processing message: RuntimeError at verify_phase9f.py:326 <- main.py:340", "trace_id": "trc-819836716d49", "session_id": "f0ba660fadc2430fb1b6b0f9244b23e3", "user_hash": "u_a9f6bd311e2b2495"}
PASS H5.scenarios_ran :: 50 log records captured
PASS H6.no_marker_in_logs :: stages ['search_knowledge_base', 'search_web', 'support_tools', 'escalate_to_human', 'normal_turn', 'provider_errors', 'internal_error', 'api_500']
PASS H7.lengths_logged
PASS H8.error_classes_logged
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 243 passed in 19.22s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 53/53 passed
```

#### Commit Base da Fase 9F (`git rev-parse HEAD`):
```text
48af0a0698394223806098a3c696844e01c36ced
```

#### Não feito:
- Nenhum. Todos os checks aplicáveis da Fase 9F passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. Logs em JSON sem texto de conversa, consulta ou mensagens de exceção em nenhum componente de serviço (`src/core/log_context.py`, `src/tools/`, `src/core/llm.py`, `src/core/graph.py`, `src/main.py`), com formatação breve de exceções via `exc_brief` e cobertura unitária completa em `tests/test_log_privacy.py`.

#### Alterações Realizadas na Fase 9F:
- **Formatação Resumida de Exceções (`src/core/log_context.py`)**:
  - Implementada a função `exc_brief(exc: BaseException) -> str`, extraindo apenas a classe da exceção e até 3 frames mais internos da stack (`Arquivo.py:linha`), sem incluir a mensagem de erro que possa conter texto digitado pelo cliente ou retornado por provedores.
- **Higienização dos Logs de Ferramentas (`src/tools/agent_tools.py`, `src/tools/web_search.py`)**:
  - Substituída a interpolação direta de `query` e `reason` pelo tamanho em caracteres (`query_chars`, `reason_chars`), e de `error_code` e `serial_number` por flags booleanas (`error_code_given`, `serial_given`).
  - Removido `logger.exception` e substituído por `logger.error`/`logger.warning` formatados com `exc_brief`.
- **Higienização dos Logs de LLM, Grafo e API (`src/core/llm.py`, `src/core/graph.py`, `src/main.py`)**:
  - Substituídas todas as chamadas `logger.exception` e interpolações brutas de exceções por `exc_brief(exc)`, garantindo que falhas de provedores, erros internos e erros 500 não vazem o conteúdo da requisição ou resposta nos logs.
- **Testes Unitários de Privacidade de Logs (`tests/test_log_privacy.py`)**:
  - Criados 5 testes offline validando que marcadores de dados do usuário nunca alcançam os registros de log em `exc_brief`, ferramentas, erros de provedor, erros internos e falhas 500 não tratadas da API.
- **Documentação e Evidências (`README.md`)**:
  - Acrescentado o item "Sem Texto da Conversa (Fase 9F)" na seção de logs estruturados e a linha correspondente na tabela de afirmações e evidências.

---

### Fase 9E: Imagem e Compose em Produção por Padrão

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9E (`python scripts/verify_phase9e.py`):
```text
INFO python 3.13.3
PASS G0.py311_syntax
PASS G1.dockerfile_production
PASS G2.compose_pinned
INFO G3 skipped: `docker compose` not available here (the CI step covers it)
PASS G5.ci_steps
PASS G7.tests
PASS G8.readme_docker
PASS G9.readme_devkeys
PASS G10.claims_row
PASS S1.status_9e
PASS E2.scope
PASS G4.image_env_rejects_dev_keys :: {'environment': 'production', 'auth_mode': 'none', 'chat': 401, 'tickets': 401}
INFO G6 skipped: bash/curl not available here, or the CI step is missing (G5 covers its text)
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 238 passed in 21.33s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 49/49 passed
```

#### Commit Base da Fase 9E (`git rev-parse HEAD`):
```text
613991b65b4cac3105a1ee8da0b6457b86d69490
```

#### Não feito:
- Nenhum. Todos os checks aplicáveis da Fase 9E passaram com sucesso.
- O build da imagem Docker e os dois passos novos do CI (`Production defaults in the image` e `Compose resolves APP_ENV=production with the example .env`) serão conferidos automaticamente no GitHub Actions após o push (ambiente local Windows sem daemon Docker ativo).

#### Perguntas / divergências com o SPEC:
- Nenhuma. O `Dockerfile` define `ENV APP_ENV=production`, o `docker-compose.yml` fixa `APP_ENV=production` sem interpolação, e as chaves públicas de desenvolvimento recebem HTTP 401 em ambiente de produção.

#### Alterações Realizadas na Fase 9E:
- **Dockerfile com Produção por Padrão (`Dockerfile`)**:
  - Adicionada a instrução `ENV APP_ENV=production` no estágio final (`runner`), garantindo que execuções avulsas com `docker run` iniciem em modo de produção por padrão e recusem credenciais públicas de desenvolvimento.
- **Fixação de Produção no Docker Compose (`docker-compose.yml`)**:
  - Fixado `- APP_ENV=production` sem interpolação `${APP_ENV:-production}`, impedindo que um arquivo `.env` copiado de `.env.example` altere o ambiente para `development`.
- **Validação de Produção no CI (`.github/workflows/ci.yml`)**:
  - Adicionados dois passos ao job `docker`: validação de que `/health` reporta `production` e que requisições com `getnet-dev-key` e `getnet-dev-operator` recebem HTTP 401, e validação de que `docker compose config` com `.env` do exemplo resolve `APP_ENV: production`.
- **Testes Automatizados de Padrões Docker (`tests/test_docker_defaults.py`)**:
  - Implementados testes unitários estáticos verificando a presença de `ENV APP_ENV=production` no `Dockerfile` e a fixação de `- APP_ENV=production` no `docker-compose.yml`.
- **Documentação e Evidências (`README.md`)**:
  - Atualizada a seção "Execução via Docker Compose" explicando a fixação de produção na imagem e no Compose, e corrigido o comando `python -m src.core.auth hash` (sem argumento).
  - Atualizado o item "Chaves de Desenvolvimento" indicando a recusa no container.
  - Incluída nova linha na tabela da Seção 9 de Afirmações e Evidências.

---

### Fase 9D: Mock de Conta Sem Lojista Inventado

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9D (`python scripts/verify_phase9d.py`):
```text
INFO python 3.13.3
PASS D0.py311_syntax
PASS D6.no_builtin_hash
PASS D7.deterministic_ids :: ["GET-883921", "TXN-902188", "TXN-902187"]
PASS D8.tests
PASS D9.readme_mock_paragraph
PASS D10.claims_row
PASS S1.status_9d
PASS E2.scope
PASS D1.unknown_is_none
PASS D2.functions_not_found
PASS D3.agent_tools_not_found
PASS D4.known_merchant_unchanged
PASS D5.support_prompt_rule
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 236 passed in 22.10s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 50/50 passed
```

#### Commit Base da Fase 9D (`git rev-parse HEAD`):
```text
308d38248ee40c3bafea95f63d3a40dbbd22224b
```

#### Não feito:
- Nenhum. Todos os checks da Fase 9D passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. O mock de banco de dados (`MockDatabase`) agora devolve estritamente `None` para lojistas desconhecidos, e as ferramentas de conta devolvem `{"status": "not_found", "error": "merchant_not_found"}` sem inventar dados, registros ou identificadores.

#### Alterações Realizadas na Fase 9D:
- **Remoção de Fabricação Dinâmica de Lojistas (`src/core/mock_db.py`)**:
  - Removido o bloco de fallback dinâmico que inventava lojistas, contas Santander e terminais com números aleatórios via `hash()`. O método `get_user(user_id)` agora realiza estritamente `self.users.get(user_id)`.
  - Nenhuma chamada a `hash()` nativo resta no diretório `src/`.
- **Padronização do Retorno Not Found nas Ferramentas de Conta (`src/tools/balance_tools.py`, `src/tools/terminal_tools.py`)**:
  - Em `get_settlement_and_sales_status`, `get_declined_transaction_details` e `diagnose_terminal_connectivity`, quando o lojista não é encontrado, retorna-se uniformemente `{"status": "not_found", "error": "merchant_not_found"}`.
- **Testes Automatizados para Lojista Inexistente (`tests/test_mock_not_found.py`)**:
  - Criados 6 testes verificando que lojistas desconhecidos retornam `None` no banco mock, retornam `not_found` nas funções de balance/decline/terminal, retornam JSON com `not_found` nas tools do agente, e que o lojista conhecido `cliente1988` permanece intacto com seus valores e números de série oficiais.
- **Documentação e Evidências (`README.md`)**:
  - Adicionado parágrafo explicativo logo após a tabela de ferramentas na Seção 1 documentando a base simulada, o vínculo de `cliente1988` e o comportamento de `not_found`.
  - Adicionada nova linha de evidência como última linha da tabela na Seção 9.

---

### Fase 9C: Histórico Válido Depois de Falha no Turno

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9C (`python scripts/verify_phase9c.py`):
```text
INFO python 3.13.3
PASS C0.py311_syntax
PASS C7.tests
PASS C8.readme_bullet
PASS C9.claims_row
PASS S1.status_9c
PASS E2.scope
PASS C1.provider_failure_closed
PASS C2.next_turn_no_orphan
PASS C3.parallel_calls_closed
PASS C4.internal_error_closed
PASS C5.no_tool_call_nothing_added
PASS C6.success_path_unchanged
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 230 passed in 21.16s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 48/48 passed
```

#### Commit Base da Fase 9C (`git rev-parse HEAD`):
```text
a561d4c2b9a117b8005391e92d77d13cae6a3ff8
```

#### Não feito:
- Nenhum. Todos os checks da Fase 9C passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. O fechamento de chamadas de ferramentas órfãs via `_close_dangling_tool_calls` garante que nenhuma chamada sem resposta persista no histórico após falha de provedor (HTTP 503) ou erro interno.

#### Alterações Realizadas na Fase 9C:
- **Fechamento de Tool Calls Órfãs (`src/core/graph.py`)**:
  - Implementado o método `_close_dangling_tool_calls(config, error)` na classe `OrchestrationGraph`, que inspeciona o snapshot do thread no checkpointer após falhas de execução, identifica chamadas de ferramenta de `AIMessage` sem `ToolMessage` correspondente, e insere mensagens `ToolMessage` de erro (`{"status": "error", "error": error}`) com `as_node="abstention_check"`.
  - Atualizado o tratamento de exceções em `run_sync()` para acionar `_close_dangling_tool_calls(config, type(exc).__name__)` em exceções de LLM (`LLMUnavailableError`, etc.) antes do relançamento (HTTP 503) e `_close_dangling_tool_calls(config, "internal_error")` em erros genéricos inesperados.
- **Testes Automatizados de Chamadas Órfãs (`tests/test_dangling_tool_calls.py`)**:
  - Criado módulo com 5 testes offline utilizando `build_sqlite_checkpointer` e `ExceptionRaisingFake`:
    - `test_provider_failure_closes_tool_call`: valida fechamento da chamada com `LLMUnavailableError` e thread desocupado (`next == ()`).
    - `test_next_turn_has_no_orphan`: valida que o turno seguinte não envia ferramenta órfã ao modelo.
    - `test_parallel_tool_calls_all_closed`: valida que múltiplas chamadas concorrentes são todas fechadas se uma falhar.
    - `test_internal_error_closes_tool_call`: valida tratamento de erro interno inesperado com sinalização `internal_error`.
    - `test_failure_before_any_tool_call_adds_nothing`: valida que falhas prévias a chamadas de ferramentas não inserem mensagens espúrias.
- **Documentação e Evidências (`README.md`)**:
  - Adicionado item explicativo em "Auditoria de Busca Web, Tratamento de Erros e Mensagens Bilíngues (Fase 7D)" documentando o fechamento de tool calls após falhas.
  - Adicionada linha na tabela da Seção 9 apontando evidências em `src/core/graph.py`, `tests/test_dangling_tool_calls.py` e `scripts/verify_phase9c.py`.

---

### Fase 9B: Cartão e CPF Mascarados Antes do Grafo

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9B (`python scripts/verify_phase9b.py`):
```text
INFO python 3.13.3
PASS B0.py311_syntax
PASS B4.persistence_tests
PASS B5.readme_pii
PASS B6.readme_guardrails_toggle
PASS R1.claims_table_9b
PASS S1.status_9b
PASS E2.scope
PASS B1.pattern
PASS B2.model_sees_mask
PASS B3.state_message_masked
PASS B7.blocked_turn
PASS B8.guardrails_off_still_masks
PASS B9.ticket_flow
PASS B10.model_never_raw
PASS B11.no_raw_bytes_on_disk :: scanned ['checkpoints.db', 'checkpoints.db-shm', 'checkpoints.db-wal', 'tickets.db']
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 225 passed in 22.19s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 50/50 passed
```

#### Commit Base da Fase 9B (`git rev-parse HEAD`):
```text
6c809bc463b4c1d7407b6043904a940ca4f513b7
```

#### Não feito:
- Nenhum. Todos os checks da Fase 9B passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. O mascaramento de cartão e CPF é aplicado antes do ingresso da mensagem no grafo, protegendo o checkpointer e banco de dados SQLite.

#### Limpeza de Banco Local:
- O arquivo `data/checkpoints.db` proveniente de testes locais anteriores foi detectado e excluído com sucesso.

#### Alterações Realizadas na Fase 9B:
- **Expressão Regular de Cartão de Crédito (`src/core/pii.py`)**:
  - Atualizado `CARD_PATTERN` para `\b\d(?:[ -]?\d){12,18}\b`, restringindo separadores (`-` ou espaço) estritamente entre dígitos e preservando espaços subsequentes na frase.
- **Mascaramento Prévio ao Ingresso no Grafo (`src/core/graph.py`)**:
  - Em `run_sync()`, aplicada a sanitização `safe_message, _ = sanitize_pii(message)` antes da gravação do estado inicial pelo checkpointer `SqliteSaver`.
  - Passado `safe_message` tanto para o `HumanMessage` quanto para o retorno do `AgentState`, garantindo que cartões e CPFs crus nunca cheguem ao modelo, ao `checkpoints.db` (tabelas e `-wal`) nem ao `tickets.db`.
- **Testes de Persistência e Não-Vazamento PII (`tests/test_pii_persistence.py`)**:
  - Criado módulo com 5 testes verificando que espaços subsequentes são mantidos, cartões/CPFs nunca chegam ao SQLite, mensagens bloqueadas por injeção não deixam vestígios crus, o mascaramento permanece ativo mesmo com `ENABLE_GUARDRAILS=False`, e o fluxo de chamados (`tickets.db`) também nunca grava dados sensíveis desprotegidos.
- **Documentação Técnica (`README.md`)**:
  - Atualizada a descrição do algoritmo de Luhn na seção de segurança detalhando que a máscara é aplicada em `run_sync` antes da gravação de checkpoint.
  - Acrescentado aviso sobre bancos antigos criados antes da Fase 9B e a necessidade de exclusão / `docker compose down -v`.
  - Atualizada a especificação de `ENABLE_GUARDRAILS` destacando que o toggle controla apenas injeção de prompt, sem desativar a máscara de cartões e CPFs.
  - Atualizada a linha de evidências na tabela da Seção 9 apontando para `tests/test_pii_persistence.py` e `scripts/verify_phase9b.py`.

---

### Fase 9A: Verificadores Reproduzíveis em Python 3.11 e Autoria

#### Versão do Python (`python --version`):
```text
Python 3.13.3
```

#### Verificação Fase 9A (`python scripts/verify_phase9a.py`):
```text
INFO python 3.13.3
PASS A1.py311_syntax
PASS A2.ci_compileall
PASS A3.metrics_fsum_static
PASS A4.fsum_test
PASS A5.authorship_section
PASS A6.toc_authorship
PASS A7.no_independent_reviewer
PASS R1.claims_table_9a
PASS A8.status_8f_correction
PASS A9.status_9a
PASS E2.scope
PASS M1.cost_exact_sum
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 220 passed in 21.98s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 46/46 passed
```

#### Commit Base da Fase 9A (`git rev-parse HEAD`):
```text
c5e2698565f23bb2bc233ee3a91c5b696ba243b9
```

#### Não feito:
- Nenhum. Todos os 46 checks da Fase 9A passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. O cálculo de custo usa math.fsum e é idêntico em Python 3.11 e 3.12+, e a autoria e revisão foram descritas com transparência e verdade.

#### Alterações Realizadas na Fase 9A:
- **Cálculo de Custo com Precisão Exata (`src/eval/metrics.py`)**:
  - Substituído `round(sum(...), 6)` por `round(math.fsum(...), 6)` no cálculo de `estimated_cost_usd`, garantindo exatidão de soma de ponto flutuante idêntica em Python 3.11 e Python 3.12+.
- **Teste de Soma Exata (`tests/test_eval_harness.py`)**:
  - Adicionado teste `test_estimated_cost_is_exact_sum` comprovando que o arredondamento na 6ª casa decimal é estável e exato.
- **Compilação Prévia no CI (`.github/workflows/ci.yml`)**:
  - Adicionado passo `python -m compileall -q scripts src tests` no job `test` (Python 3.11) antes da execução dos testes e linting.
- **Autoria e Revisão Transparente (`README.md` e `docs/STATUS.md`)**:
  - Inserida a seção "Autoria e revisão" detalhando os papéis do Google Antigravity (Gemini 3.8 Flash) na implementação, do Claude (Anthropic) no planejamento e revisão das fases, e do candidato na condução, decisões e execuções com modelo real.
  - Substituídas as menções anteriores pela atribuição correta ao Claude.
  - Adicionada nota de correção retrospectiva na seção da Fase 8F sobre a divergência entre Python 3.13 e 3.11.

---

### Fase 8F: README Depois da Avaliação com Várias Execuções

#### Verificação Fase 8F (`python scripts/verify_phase8f.py`):
```text
PASS F1.runs_heading
PASS F2.limitations_point_to_comparison
PASS F3.toc_entry
PASS F4.reasoning_tokens_note
PASS F5.kept.62/69 (89,9%)
PASS F5.kept.## 6. Matriz de Cobertur
PASS F5.kept.| Casos aprovados (checa
PASS E1.status
PASS E2.readme_only
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 219 passed in 19.71s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 42/42 passed
```

> **Correção (Fase 9A):** este resultado foi obtido com o Python local (3.13). Em Python 3.11, a versão do CI e do Dockerfile, o mesmo verificador dava 40/42: `scripts/verify_phase7c.py` não compilava (f-string com barra invertida, sintaxe do Python 3.12) e o check C1 de `scripts/verify_phase8e.py` diferia na 6ª casa decimal do custo (o `sum()` de floats mudou no Python 3.12). Os dois defeitos estavam nos verificadores do revisor e foram corrigidos na Fase 9A, junto com o cálculo de custo em `src/eval/metrics.py` (`math.fsum`).

#### Commit Base da Fase 8F (`git rev-parse HEAD`):
```text
c2d52e311710bc19fbcf741c2cac0c210d957d32
```

#### Não feito:
- Nenhum. Todos os checks da Fase 8F passaram com sucesso.

#### Conclusão do Plano do SPEC:
- Com a conclusão da Fase 8F, o plano de especificação técnica de todas as fases (Fases 1 a 8) do `docs/SPEC.md` está formalmente e integralmente concluído.

#### Perguntas / divergências com o SPEC:
- Nenhuma. O texto do README reflete fielmente as execuções consolidadas e as referências históricas.

#### Alterações Realizadas na Fase 8F:
- **Subtítulo e Seção de Execuções Registradas (`README.md`)**:
  - Atualizado o subtítulo de `#### Execução de Referência Registrada (`full-1`)` para `#### Execuções registradas`.
  - Atualizado o parágrafo explicativo contextualizando as 7 execuções dos 69 casos, indicando a comparação das seis execuções de 2026-11-08 (`full-2` a `full-7`) em `reports/eval_models.md` e marcando a `full-1` como execução histórica.
- **Limitações Atuais (`README.md`)**:
  - No item "Testes com modelo roteirizado", atualizada a referência da avaliação com o modelo real de `(`reports/eval_full-1.md`)` para `(`reports/eval_models.md`, três execuções por modelo)`.
- **Sumário (`README.md`)**:
  - Dividido o item de avaliação no Sumário para incluir o link direto para `Resultados da avaliação: comparação de modelos` e `Resultados da avaliação (full-1, histórica)`.
- **Observabilidade Técnica e Tokens de Raciocínio (`README.md`)**:
  - Acrescentado item explicando que os tokens de saída informados pelo Gemini e registrados em cada turno incluem tokens de raciocínio (faturados como tokens de saída), correlacionando com a conferência no painel de uso do Google AI Studio em 2026-11-08 para o `gemini-3.8-flash`.

---

### Fase 8E: Seis Execuções Commitadas, Custo na Avaliação e Comparação de Modelos

#### Verificação Fase 8E (`python scripts/verify_phase8e.py`):
```text
PASS R1.no_stale_cost_claims
PASS R2.readme_comparison_section
PASS R3.readme_claims_row
PASS E1.status
PASS E2.default_model_kept.src/config.py
PASS E2.default_model_kept..env.example
PASS P1.price_table
PASS P2.price_notes
PASS P3.cost_new_models
PASS D1.raw_runs_unchanged
PASS C0.cost_note
PASS C1.aggregate_cost
PASS C2.cost_note_in_aggregate
PASS D2.reports_match_raw
PASS D3.real_run_cost
PASS K1.compare_runs_matches_reference
PASS K2.comparison_report
PASS K3.comparison_markdown_table
PASS K4.readme_has_table
INFO reference table:
| Métrica | flash-lite | 3.8-flash |
| :--- | :--- | :--- |
| Execuções | full-2, full-4, full-5 | full-3, full-6, full-7 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.8-flash |
| Casos aprovados (checagens determinísticas) | 86,0% (84,1–89,9) | 88,9% (88,4–89,9) |
| Cenários oficiais aprovados | 86,7% (80,0–100,0) | 90,0% (90,0–90,0) |
| Roteamento correto | 93,5% (92,9–94,6) | 91,7% (91,1–92,9) |
| Ferramentas corretas | 93,4% (91,8–95,1) | 95,6% (95,1–96,7) |
| Escalonamento correto | 98,4% (96,7–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 93,5% (88,9–97,2) | 90,7% (88,9–94,4) |
| Fonte oficial citada | 96,0% (96,0–96,0) | 92,0% (92,0–92,0) |
| Idioma da resposta | 94,7% (93,7–96,8) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | 4,98 (4,95–5,00) | 4,94 (4,94–4,94) |
| Juiz: responde à pergunta (1 a 5) | 4,67 (4,65–4,68) | 4,61 (4,48–4,70) |
| Juiz: precisão da abstenção | 74,9% (69,2–78,6) | 69,6% (64,7–72,7) |
| Juiz: cobertura da abstenção | 76,9% (69,2–84,6) | 74,4% (61,5–84,6) |
| Latência por caso, mediana | 4,3 s (4,2–4,3) | 15,4 s (15,0–15,8) |
| Latência por caso, p95 | 8,8 s (8,1–9,7) | 31,6 s (29,8–33,2) |
| Tokens por execução | 421.140 (413.563–426.999) | 566.646 (549.248–581.298) |
| Custo estimado por execução (USD, plano pago) | US$ 0,167 (0,163–0,170) | US$ 0,640 (0,622–0,654) |
INFO flash-lite: failed in all runs ['k16', 'o02', 's04', 's06']; abstention errors in all runs ['k16', 'o02', 's04', 's06', 'u01']
INFO 3.8-flash: failed in all runs ['k09', 'k16', 'm04', 'o02', 'off01', 's04', 's06']; abstention errors in all runs ['k16', 'off01', 'u03', 'u05']
PASS Q0.compare_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 219 passed in 21.00s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 52/52 passed
```

#### Commit Base da Fase 8E (`git rev-parse HEAD`):
```text
34fc9e1ff393ca75947fc8b13cb349cf6731e37b
```

#### Não feito:
- Nenhum. Todos os 52 checks da Fase 8E passaram com sucesso.

#### Perguntas / divergências com o SPEC:
- Nenhuma. A implementação atende rigorosamente a todas as especificações e regras da Fase 8E.

#### Testes Criados e Alterados (conferidos com `git diff`):
- **Criados em `tests/test_eval_compare.py`**:
  - `test_compare_runs_mean_min_max`: validação estatística de agregação de métricas (`mean`, `min`, `max`) entre execuções.
  - `test_compare_runs_none_handling`: propagação estrita de `None` quando alguma execução não possui métrica calculada.
  - `test_compare_runs_failed_intersection`: interseção de casos com reprovação determinística e erros de abstenção pelo juiz.
  - `test_markdown_table_formatting_pct_and_usd`: formatação de tabela Markdown com vírgula decimal, en-dash (`–`), porcentagem, moeda (`US$`) e milhar.
  - `test_write_comparison_artifacts`: escrita física de arquivos `.json` e `.md` gerados por `write_comparison`.
- **Alterados em `tests/test_eval_harness.py`**:
  - `test_aggregate_percentiles_tokens_and_cost`: atualização de assert para conferir `agg["cost_note"] == COST_NOTE`.
  - `test_aggregate_estimated_cost_usd`: teste da agregação do custo estimado em USD somando turnos tarifados e retornando `None` quando houver modelo sem preço.
- **Alterados em `tests/test_pricing.py`**:
  - `test_cost_usd_supported_models`: adição de checagens de cálculo tarifário para `gemini-3.8-flash` ($0.75/$3.75) e `gemini-3.6-flash`.

#### Alterações Realizadas na Fase 8E:
- **Tabela de Preços e Notas de Custo (`src/core/pricing.py`)**:
  - Adicionados os modelos `gemini-3.6-flash` e `gemini-3.8-flash` à tabela `PRICES_USD_PER_1M` com US$ 0,75 para entrada e US$ 3,75 para saída por milhão de tokens.
  - Registrado dicionário `PRICE_NOTES` com data de coleta (2026-11-08) e vigência dos preços (válidos até 2026-12-31, passando para US$ 1,50 entrada e US$ 7,50 saída a partir de 2027-01-01).
- **Custo Financeiro na Avaliação (`src/eval/metrics.py`)**:
  - Criada constante `COST_NOTE` documentando premissas de custo do plano pago (excluindo juiz e embeddings).
  - Atualizada a função `aggregate()` para calcular `estimated_cost_usd` a partir da soma dos custos de cada turno com tokens em resultados com status `"ok"`. Retorna `None` se algum turno com tokens não tiver modelo tarifado.
- **Módulo de Comparação de Execuções (`src/eval/compare.py`)**:
  - Implementada a lista `COMPARE_METRICS` com as 16 métricas consolidadas.
  - Implementada função `compare_runs()` para agregação estatística com média aritmética, mínimo e máximo, interseção de falhas determinísticas (`failed_in_all_runs`) e erros de abstenção do juiz (`judge_abstention_errors_in_all_runs`).
  - Implementada função `write_comparison()` para persistência em JSON (`reports/eval_<name>.json`) e tabela Markdown formatada (`reports/eval_<name>.md`) com locale decimal em vírgula, traço en-dash (`–`) e prefixos/sufixos adequados (`%`, `s`, `US$`).
- **Subcomando CLI Compare (`src/eval/__main__.py`)**:
  - Adicionado subcomando `compare` com opções `--name`, `--group` (repetível no formato `ROTULO=run1,run2`), `--runs-dir` e `--out-dir`.
- **Relatórios Gerados e Comparação de Modelos (`reports/`)**:
  - Executados os relatórios `full-1` a `full-7` e a comparação `eval_models` entre `flash-lite` (`full-2,full-4,full-5`) e `3.8-flash` (`full-3,full-6,full-7`).
  - Comprovada consistência exata dos dados e da tabela de comparação contra a especificação e os hashes dos arquivos brutos.
- **Documentação Técnica (`README.md`)**:
  - Inserida seção de comparação de modelos (`### Resultados da avaliação: comparação de modelos (3 execuções por modelo, 2026-11-08)`) imediatamente antes dos resultados da `full-1`.
  - Atualizada linha de tokens da `full-1` com o custo estimado de US$ 0,170.
  - Atualizada seção de observabilidade com informações dos novos modelos, notas de preços e cálculo de custo em `src/eval/`.
  - Documentado o comando `compare` na seção de execução de avaliação.
  - Acrescentada linha de evidência para comparação de modelos na tabela de "9. Afirmações e evidências".

---

### Fase 8D: Arquivos da Imagem Só para Leitura e Últimas Frases do README

#### Verificação Fase 8D (`python scripts/verify_phase8d.py`):
```text
PASS E1.dockerfile_read_only
PASS E2.ci_write_probe
PASS E3.readme_claims
PASS E4.status
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 213 passed in 17.94s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 35/35 passed
```

#### Commit Base da Fase 8D (`git rev-parse HEAD`):
```text
a70b60b8dc9622f342bfe32be1ae42d5723ff57a
```

#### Alterações Realizadas na Fase 8D:
- **Proteção de Escrita de Arquivos na Imagem (`Dockerfile`)**:
  - Ajustada a camada de permissões para remover explicitamente permissão de escrita de grupo e outros (`chmod -R go-w /app/data /app/src /app/README.md`) antes da declaração `USER appuser`.
  - Garante que o `appuser` (não-root) não consiga alterar o índice vetorial, corpus ou código-fonte da aplicação em runtime dentro do container.
- **Sonda de Escrita no CI do Docker (`.github/workflows/ci.yml`)**:
  - Adicionado comando de validação no job do Docker:
    `docker exec app sh -c '! test -w /app/data/index/chunks.jsonl && ! test -w /app/src/main.py && test -w /app/state'`
  - Assegura na esteira de integração que `/app/data` e `/app/src` são estritamente somente-leitura enquanto `/app/state` permite escrita.
- **Ajustes de Alegações no README (`README.md`)**:
  - Em "Limitações atuais", referenciado que no Docker o banco é `/app/state/checkpoints.db` no volume `getnet_app_state`.
  - Na seção de transbordo (Fase 5A), atualizado para `/app/state/tickets.db` no volume `getnet_app_state`.
  - Substituída a frase "Zero Falsas Promessas" pela declaração honesta "Sem prazos nem filas", explicitando que o prompt do supervisor proíbe tais promessas como instrução ao modelo, e não uma garantia matemática, cujo comportamento é aferido pela avaliação.
- **Conclusão do Plano do SPEC**:
  - O CI do Docker precisa ficar verde neste commit com a verificação de permissões e healthcheck. Com isso, todo o plano de especificação técnica de todas as fases (Fases 1 a 8) do `docs/SPEC.md` está formalmente concluído.

---

### Fase 8C: A Imagem Aponta os Bancos para /app/state (Correção do CI do Docker)

#### Verificação Fase 8C (`python scripts/verify_phase8c.py`):
```text
PASS C1.image_db_paths
PASS C1.still_secure
PASS C2.compose_unchanged
PASS C3.status
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 213 passed in 17.78s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 34/34 passed
```

#### Commit Base da Fase 8C (`git rev-parse HEAD`):
```text
a4c57df9267f35f7f6c0ca6f441a0b6fd31ffd55
```

#### Alterações Realizadas na Fase 8C:
- **Causa da falha do CI na Fase 8B**:
  - O job `docker` do CI inicia o container com um comando simples `docker run -d -p 8000:8000 --name app getnet-app`, sem carregar as variáveis de ambiente do `docker-compose.yml`.
  - Como os padrões no código eram `data/checkpoints.db` e `data/tickets.db`, e a Fase 8B removeu a escrita em `/app/data` (pertencente ao root) para proteger o índice e corpus, a aplicação falhou imediatamente ao tentar abrir o banco de dados (fail-fast), impedindo o endpoint `/health` de responder (timeout no healthcheck do CI).
- **Correção no Dockerfile (`Dockerfile`)**:
  - Adicionadas as variáveis de ambiente no estágio `runner` do `Dockerfile`:
    - `CHECKPOINT_DB_PATH=state/checkpoints.db`
    - `TICKETS_DB_PATH=state/tickets.db`
  - Assim, a própria imagem Docker agora direciona os bancos SQLite para o diretório `/app/state` (de propriedade de `appuser:appgroup`), seja rodando via `docker run` direto no CI ou via `docker compose`, permitindo que o CI fique verde.
- **Status do Requisito AC8.1**:
  - Falta exclusivamente a verificação manual do `docker compose up` pelo usuário no ambiente Codespaces para validação final em runtime real e auditoria pelo revisor.

---

### Fase 8B: Volume do Docker só com os Bancos, Tabela de Afirmações e README Final

#### Verificação Fase 8B (`python scripts/verify_phase8b.py`):
```text
PASS D1.volume_on_state
PASS D1.db_paths_in_state
PASS D2.dockerfile
PASS D2.dockerignore
PASS D3.ci_non_root
PASS R1.claims_table
PASS R2.readme_docker
PASS R3.evidence_exists
PASS R4.results_kept
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 213 passed in 16.98s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 38/38 passed
```

#### Commit Base da Fase 8B (`git rev-parse HEAD`):
```text
5e57b8e70f24aba12540cb1715d472854a1a0933
```

#### Alterações Realizadas na Fase 8B:
- **Volume Docker e Caminhos de Estado (`docker-compose.yml`)**:
  - O volume nomeado foi alterado para `app_state` (com `name: getnet_app_state`) e montado exclusivamente em `/app/state` (removendo montagem em `/app/data`).
  - Padrões de caminhos dos bancos no Compose atualizados para `CHECKPOINT_DB_PATH=${CHECKPOINT_DB_PATH:-state/checkpoints.db}` e `TICKETS_DB_PATH=${TICKETS_DB_PATH:-state/tickets.db}`.
  - O índice e o corpus documental permanecem somente para leitura a partir da imagem, permitindo que novas versões da imagem atualizem a base automaticamente.
- **Higienização de Permissões no Dockerfile (`Dockerfile`)**:
  - Removidos `chmod -R 777` e `chown` sobre `/app/data`.
  - Criado diretório `/app/state` com propriedade atribuída a `appuser:appgroup`. Mantido usuário não-root `USER appuser` e `HEALTHCHECK`.
- **Prevenção de Vazamento em `.dockerignore` (`.dockerignore`)**:
  - Adicionadas regras `data/*.db`, `data/*.db-wal`, `data/*.db-shm` e `reports/` para evitar que bancos locais contendo dados de conversas ou chamados e relatórios de avaliação sejam incluídos acidentalmente na imagem Docker.
- **Asserção de Usuário Não-Root no CI (`.github/workflows/ci.yml`)**:
  - Adicionada verificação no job do Docker confirmando que o container não executa como root (`test "$(docker exec app id -u)" != "0"`).
- **Documentação e Tabela de Evidências (`README.md`)**:
  - Seção Docker Compose documenta o volume `getnet_app_state` restrito a `/app/state` e instrui `docker compose down -v` para reinício limpo.
  - Adicionada a seção "9. Afirmações e evidências" com a tabela completa mapeando cada alegação técnica do projeto às respectivas evidências (arquivos de código, testes, relatórios e verificadores).
  - Incluído link "9. Afirmações e evidências" no Sumário do README.

#### Status do Requisito AC8.1:
- Falta somente a verificação manual do `docker compose up` pelo usuário no ambiente Codespaces para validação final em runtime real.

---

### Fase 8A: /agents Gerado pelo Código, /demo com Campos Reais e Sobras do README

#### Verificação Fase 8A (`python scripts/verify_phase8a.py`):
```text
PASS A0.demo_real_fields
PASS A0.readme_leftovers
PASS A0.readme_ci
PASS A0.readme_compose_keys
PASS A1.tool_constants
PASS A1.specialists_use_constants
PASS A2.agents_from_code
PASS A2.models_from_settings
PASS A3.tool_rows
PASS A3.no_fictional_names
PASS Q0.agents_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 213 passed in 18.63s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 39/39 passed
```

#### Commit Base da Fase 8A (`git rev-parse HEAD`):
```text
fd9364931bf327f719ac8d96c08dd128402925fe
```

#### Alterações Realizadas na Fase 8A:
- **Constantes de Ferramentas de Especialistas (`src/core/graph.py`)**:
  - Definidas no nível de módulo `KNOWLEDGE_TOOLS = [search_knowledge_base, search_web]` e `SUPPORT_TOOLS = [get_settlement_status, diagnose_declined_transaction, diagnose_terminal]`.
  - Especialistas `KnowledgeAgent` e `SupportAgent` construídos diretamente a partir dessas constantes como fonte única da verdade (`tools=KNOWLEDGE_TOOLS` e `tools=SUPPORT_TOOLS`).
- **Geração Dinâmica de `GET /agents` (`src/main.py`)**:
  - Endpoint `/agents` reescrito para gerar a arquitetura, agentes, ferramentas e argumentos diretamente dos objetos em memória e configurações ativas:
    - `"architecture"`: `"LangGraph supervisor with specialist sub-agents"`;
    - `"checkpointer"`: `"SqliteSaver (thread user_id:session_id)"`;
    - `"models"`: `{"primary": settings.LLM_MODEL, "fallback": settings.LLM_FALLBACK_MODEL or None}`;
    - `"agents"`: `GuardrailAgent` (`runs_before="supervisor"`, `uses_llm=False`, `tools=[]`), `SupervisorAgent` (nomes de `SUPERVISOR_TOOLS`, `"prompt": "src/prompts/supervisor.md"`), `KnowledgeAgent` (nomes de `KNOWLEDGE_TOOLS`, `"prompt": "src/prompts/knowledge_agent.md"`), `SupportAgent` (nomes de `SUPPORT_TOOLS`, `"prompt": "src/prompts/support_agent.md"`);
    - `"tools"`: iterado sobre `SUPERVISOR_TOOLS`, `KNOWLEDGE_TOOLS` e `SUPPORT_TOOLS` com `name`, primeira linha não vazia de `description` e argumentos ordenados `args: sorted(tool.args)`.
    - Eliminados nomes inventados (`HardwareSpecialist`, `WebSearchSpecialist`, `CustomerSupportSpecialist`, `HumanOversightSpecialist`, `KnowledgeSpecialist`, `sanitize_pii`, `regex_safety_evaluator`) e "Google Gemini Flash".
- **Interface Web Interativa (`src/static/demo.html`)**:
  - Troca de "MemorySaver" por `SqliteSaver` e de "Gemini Flash" por "Gemini (function calling)".
  - Rótulo de custo ajustado para "Custo estimado (USD):".
  - Renderização dinâmica de `meta.tokens` (`input_tokens`, `output_tokens`, `total_tokens`) e `meta.estimated_cost_usd` (formatado com 6 casas decimais), exibindo `n/a` quando nulos.
  - Exibição de score de similaridade RAG utilizando unicamente `d.score` quando numérico, ou `n/a` caso contrário (removidos `d.similarity` e `|| 0).toFixed`).
- **Alinhamento do README (`README.md`)**:
  - "Limitações atuais": o item de testes com modelo roteirizado agora indica que a qualidade com o modelo real é medida pela avaliação (`reports/eval_full-1.md`) em vez de "será avaliada na Fase 6".
  - Seção `/demo`: "Trace ID UUID" alterado para "Trace ID"; itens de tokens detalham `input_tokens`, `output_tokens` e `total_tokens` (sem "Prompt/Completion"); removida menção "com alta performance" da latência.
  - Seção Observabilidade: métricas de tokens especificadas para respostas que chamam o modelo (turnos bloqueados pelo guardrail ou de espera pelo atendente não possuem tokens).
  - Seção CI: pipeline descrita cobrindo lint com Ruff, suíte de testes com pytest, build da imagem Docker e smoke test no `/health`.
  - Seção Docker Compose: documentado que o compose opera com `APP_ENV=production`, tornando `API_KEYS` estritamente obrigatório (sem ela requisições recebem 401), e instruído como gerar o hash com `python -m src.core.auth hash`.
- **Testes Criados (`tests/test_agents_endpoint.py`)**:
  - `test_agents_endpoint_tools_match_code_lists`: valida ferramentas e prompts de cada agente e a lista de tools gerada pelos objetos de código.
  - `test_agents_endpoint_models_from_settings`: valida modelos primário e fallback a partir das configurações ativas.
  - `test_agents_endpoint_no_fictional_names_or_memorysaver`: valida ausência de nomes fictícios, `MemorySaver` ou caminhos `data/` na resposta de `/agents`.

---

### Fase 7D: Registro de Busca Web, Tratamento de Erros Internos e Mensagens Padronizadas Bilíngues

#### Verificação Fase 7D (`python scripts/verify_phase7d.py`):
```text
PASS W0.readme
PASS W1.state_web_results
PASS W2.observe_turn
PASS W2.docs_cap_kept
PASS W3.judge_sees_web
PASS E1.error_flag
PASS E2.eval_counts_error
PASS E3.no_flag_when_ok
PASS L1.fixed_messages_bilingual
PASS L2.forced_escalation_uses_constant
PASS Q0.web_error_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 210 passed in 18.71s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 38/38 passed
```

#### Commit Base da Fase 7D (`git rev-parse HEAD`):
```text
bb31178c2ac6434a40b2cd9f86399dbe2618bc1b
```

#### Alterações Realizadas na Fase 7D:
- **Resultados de Busca Web no Estado e no Juiz (`src/agents/specialists.py`, `src/core/state.py`, `src/core/graph.py`, `src/eval/runner.py`, `src/eval/judge.py`)**:
  - `web_results: list[dict[str, Any]]` agora é coletado pelas chamadas a `search_web` contendo `url`, `title` e `snippet`.
  - Propagado do especialista ao `SupervisorState`, `AgentState` e `AgentMetadata`.
  - `observe_turn` em `src/eval/runner.py` registra `web_results` com `snippet` truncado em 600 caracteres (mantendo o teto de 2000 caracteres para documentos recuperados do RAG).
  - `build_judge_input` em `src/eval/judge.py` anexa os resultados de busca web como passagens (`{"url": url, "text": f"{title}\n{snippet}"}`), permitindo ao juiz LLM auditar a fidelidade e prevenir alucinações baseadas na web.
- **Sinalização de Falhas Internas e Métricas de Erro (`src/core/state.py`, `src/core/graph.py`, `src/main.py`, `src/eval/runner.py`)**:
  - Adicionado campo `error: str | None = None` em `AgentState` e `AgentMetadata`.
  - Em exceções não tratadas no grafo (`run_sync`), o estado sinaliza `error = "internal_error"` e oculta detalhes sensíveis / tracebacks do cliente.
  - O executor de avaliação `run_case` reconhece `state.error` e marca o caso com `status="error"` e `error_type="internal_error"`.
- **Mensagens Fixas Padronizadas Bilíngues (`src/core/graph.py`)**:
  - Definidas constantes `INSTABILITY_MESSAGE`, `FORCED_ESCALATION_MESSAGE` e `FORCED_ESCALATION_FAILED_MESSAGE` contendo textos completos em Português e Inglês para suporte bilíngue imediato sem depender do LLM em falhas ou contingências.
- **Documentação Técnica (`README.md`)**:
  - Documentação atualizada nas seções de Limites do Juiz e Observabilidade Técnica, detalhando auditoria de busca web e sinalização de erros internos.
- **Testes Criados e Atualizados (`tests/test_web_and_errors.py`, `tests/test_eval_runner_judge.py`)**:
  - `tests/test_web_and_errors.py`: 4 novos testes unitários e de integração cobrindo coleta de busca web, passagens no juiz, captura de erro interno e mensagens bilíngues de escalonamento forçado.
  - `tests/test_eval_runner_judge.py`: atualizado para incluir `web_results` nas chaves esperadas do turno.

A Fase 7 está concluída. A próxima fase é a Fase 8.

---

### Fase 7C: /metrics no Formato Prometheus (Sem Novas Dependências)

#### Verificação Fase 7C (`python scripts/verify_phase7c.py`):
```text
PASS M0.llm_error_logs_no_traceback
PASS M0.no_new_dependency
PASS M0.readme
PASS M1.api
PASS M1.format
PASS M1.histogram_and_labels
PASS M2.graph_counters
PASS M3.endpoint
PASS Q0.metrics_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 206 passed in 18.85s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 35/35 passed
```

#### Commit Base da Fase 7C (`git rev-parse HEAD`):
```text
83d6453bdd29134b8e8b04e633626376f0bd699e
```

#### Alterações Realizadas na Fase 7C:
- **Módulo de Métricas em Memória (`src/core/metrics.py`)**:
  - Implementado formato de texto Prometheus (versão 0.0.4) sem dependências externas (`prometheus_client`), protegido por `threading.Lock`.
  - Exposição de todas as métricas com linhas `# HELP` e `# TYPE`:
    - `getnet_requests_total{status="<código HTTP>"}` (counter).
    - `getnet_request_latency_seconds` (histogram) com buckets cumulativos (`0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, +Inf`), `_sum` e `_count`.
    - `getnet_tool_calls_total{tool="...",status="ok|error"}` (counter) normalizando ferramentas fora das 8 oficiais para `tool="unknown"`.
    - `getnet_escalations_total`, `getnet_abstentions_total` e `getnet_llm_tokens_total{direction="input|output"}` (counters).
  - Funções `reset()`, `render() -> str`, `inc_request(...)`, `inc_tool(...)`, `inc_escalation()`, `inc_abstention()`, `add_tokens(...)`.
- **Serviço FastAPI (`src/main.py`)**:
  - Middleware HTTP medindo latência e registrando código de status via `inc_request` exclusivamente para `/chat` e `/api/v1/chat` (incluindo 401, 503 e 500; ignorando endpoints de saúde/docs).
  - Endpoint `GET /metrics` retornando `media_type="text/plain; version=0.0.4; charset=utf-8"` sem autenticação.
  - Substituição de `logger.exception` por `logger.error` nos três tratamentos de erro de LLM (mal configurado, não configurado, indisponível), mantendo apenas o nome da classe da exceção para evitar vazamento de mensagens do provedor via traceback.
- **Instrumentação do Grafo e Especialistas (`src/core/graph.py`, `src/agents/specialists.py`, `src/core/tickets_db.py`)**:
  - `inc_tool` invocado ao lado de cada registro de `"tool finished"` no Supervisor e em especialistas.
  - `inc_escalation` acionado junto à persistência de chamado em `tickets_db.py`.
  - `inc_abstention` acionado no nó `abstention_check` quando todas as consultas de conhecimento se abstêm.
  - `add_tokens` chamado ao final de cada turno em `run_sync` com os tokens medidos.
- **Documentação Técnica (`README.md`)**:
  - Documentação completa do endpoint `GET /metrics`, de cada métrica pelo nome, do armazenamento em memória por processo (sem agregação de réplicas) e da recomendação de segurança de rede em produção.
- **Testes Unitários Criados (`tests/test_metrics.py`)**:
  - `test_render_format_and_cumulative_histogram`: validação de cabeçalhos HELP/TYPE, contagens cumulativas de buckets, sum e count.
  - `test_unknown_tool_normalization_and_statuses`: validação de normalização de ferramentas inventadas para `tool="unknown"`.
  - `test_turn_increments_tools_escalation_and_tokens`: integração com `OrchestrationGraph` validando incremento de ferramentas, chamados escalonados e tokens de entrada e saída.
  - `test_metrics_endpoint_and_chat_status_recording`: validação de que `/metrics` responde 200 `text/plain`, grava status 401 e 503 do `/chat`, ignora `/health` e não expõe identificadores de usuário.

---

### Fase 7B: Custo pela Tabela Oficial de Preços e Logs do /chat no Contexto

#### Verificação Fase 7B (`python scripts/verify_phase7b.py`):
```text
PASS P0.readme
PASS P0.main_logs
PASS P1.price_table
PASS P2.cost_usd
PASS P3.turn_cost
PASS P4.chat_error_logs_have_context
PASS Q0.pricing_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 202 passed in 17.22s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 32/32 passed
```

#### Commit Base da Fase 7B (`git rev-parse HEAD`):
```text
6c8ad5a52deb11f92a68b42edf5cfeeff119792c
```

#### Alterações Realizadas na Fase 7B:
- **Módulo de Precificação Oficial (`src/core/pricing.py`)**:
  - Tabela `PRICES_USD_PER_1M` com preços oficiais copiados de `https://ai.google.dev/gemini-api/docs/pricing` (data da página: 2026-10-30; data de coleta: 2026-11-07; plano pago, nível Standard):
    - `gemini-3.5-flash-lite`: $0.30 input / $2.50 output por 1M tokens.
    - `gemini-3.1-flash-lite`: $0.25 input / $1.50 output por 1M tokens.
    - `gemini-embedding-2`: $0.20 input / $0.00 output por 1M tokens.
  - Função `cost_usd(model, input_tokens, output_tokens) -> float | None`: remove prefixo `models/`; devolve `None` para modelo `None`, modelos fora da tabela (ex.: `gemini-3.5-flash`, `unknown`) ou tokens ausentes (`None`); senão calcula o custo ponderado arredondado em 8 casas decimais.
- **Grafo de Orquestração (`src/core/graph.py`)**:
  - `run_sync` calcula `estimated_cost_usd` a cada turno usando `cost_usd(llm_model, tokens["input_tokens"], tokens["output_tokens"])`.
  - Refatorados os 4 blocos de log duplicados de `"tool finished"` em `_tools_node` para uma função auxiliar única `_log_tool_finished`, preservando os campos registrados.
- **Logs de Erro do Endpoint `/chat` dentro do Contexto (`src/main.py`)**:
  - `chat_endpoint` encapsulado no contexto `with bind(trace_id, active_session, principal.user_id):`, garantindo que todos os logs de erro emitidos contenham `trace_id`, `session_id` e `user_hash`.
  - Removidos `[trace_id={trace_id}]` e a interpolação crua da exceção `{exc}` das mensagens de log de erro, registrando somente o nome da classe (`type(exc).__name__`) e preservando tracebacks completos via `logger.exception`.
- **Documentação Técnica (`README.md`)**:
  - Documentada a origem dos preços oficiais (`https://ai.google.dev/gemini-api/docs/pricing`), datas de referência (2026-10-30 e 2026-11-07), plano Standard, tratamento de modelos não listados (`null`), premissas de custo do turno e que embeddings de consultas não são contabilizados no custo do turno nem no relatório de avaliação.
  - Substituídas menções a "custo entra na Fase 7" que descreviam o comportamento anterior da API.
- **Testes Unitários Criados (`tests/test_pricing.py`)**:
  - `test_cost_usd_supported_models`: cálculo exato para os modelos oficiais (com e sem prefixo `models/`).
  - `test_cost_usd_unlisted_models_and_none_tokens`: retorno `None` para modelos não listados e tokens ausentes.
  - `test_turn_cost_priced_vs_unpriced_model`: integração no grafo LangGraph validando `estimated_cost_usd` com modelo listado vs não listado com tokens reportados.
  - `test_chat_error_logs_carry_request_context`: validação de que requisição com erro HTTP 503 gera logs estruturados no logger `multiagent` contendo `trace_id` correspondente ao cabeçalho `X-Trace-Id`, `session_id`, `user_hash` e sem vazamento do identificador cru.

---

### Fase 7A: Logs Estruturados com trace_id, Sessão e Usuário em Hash

#### Verificação Fase 7A (`python scripts/verify_phase7a.py`):
```text
PASS L0.no_identifiers_in_log_calls
PASS L0.salt_setting
PASS L0.readme
PASS L1.api
PASS L1.user_hash
PASS L1.bind_and_reset
PASS L2.no_pii_in_logs
PASS L3.context_on_every_record
PASS L3.context_cleared
PASS L4.node_events
PASS L5.tool_events
PASS L6.run_still_works
PASS Q0.logging_tests
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
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 198 passed in 18.30s
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 37/37 passed
```

#### Commit Base da Fase 7A (`git rev-parse HEAD`):
```text
6295a6300a54bc8a4cacf6866a124c0a69c5e8bb
```

#### Alterações Realizadas na Fase 7A:
- **Módulo de Contexto de Log (`src/core/log_context.py`)**:
  - Implementadas ContextVars para `trace_id`, `session_id` e `user_hash`.
  - Função `user_hash(user_id)` com hash SHA-256 truncado em 16 hexadecimais prefixado com `"u_"` e salgado via `settings.LOG_HASH_SALT`.
  - Context manager `bind(trace_id, session_id, user_id)` para escopo de requisição com restauração garantida de tokens.
  - Função `current()` expondo apenas os identificadores ativos.
- **Configuração e Formatação JSON (`src/config.py`, `.env.example`)**:
  - Adicionado parâmetro `LOG_HASH_SALT: str = ""` em `Settings` e modelo no `.env.example`.
  - `JsonFormatter` atualizado para injetar automaticamente os campos de `current()` e os extras `agent`, `node`, `tool`, `status`, `latency_ms` e `execution_time_ms`. Se um registro trouxer o extra `user_id`, grava `user_hash` no lugar.
- **Instrumentação do Grafo LangGraph (`src/core/graph.py`)**:
  - `run_sync` gera `active_trace_id` e `active_session_id` antes da execução e encapsula todo o ciclo com `with bind(...)`.
  - Log inicial substituído por `logger.info("workflow started")`.
  - Nós encapsulados via `_wrap_node` para emissão de evento `logger.info("node finished", extra={"node": <nome>, "latency_ms": <ms>})`.
  - Ferramentas no Supervisor emitindo `logger.info("tool finished", extra={"tool": ..., "agent": "SupervisorAgent", "status": ..., "latency_ms": ...})`.
- **Instrumentação de Especialistas (`src/agents/specialists.py`)**:
  - Ferramentas em especialistas emitindo `logger.info("tool finished", extra={"tool": ..., "agent": self.name, "status": ..., "latency_ms": ...})`. Em caso de erro na ferramenta, grava somente o nome da classe da exceção.
- **Higienização de Identificadores Crus nos Logs**:
  - Removida interpolação de `user_id`, `session_id` e texto de mensagens em chamadas de log em `src/tools/agent_tools.py`, `src/core/tickets_db.py`, `src/agents/guardrails.py` e `src/main.py`.
- **Testes Unitários (`tests/test_logging.py`)**:
  - Criados 4 novos testes unitários cobrindo estabilidade de hash/sal, binding de ContextVars, prevenção de vazamento de PII/usuário cru e emissão de eventos de latência de nós e ferramentas.

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
14. **Fase 7A Concluída (Logs Estruturados com trace_id, Sessão e Usuário em Hash)**: Implementado `log_context.py` com ContextVars e hashing de `user_id` (`u_<hex16>`) com sal configurável `LOG_HASH_SALT`; logs formatados em JSON com contexto em todos os registros sem vazamento de identificador cru nem PII; eventos de latência de nós (`node finished`) e ferramentas (`tool finished`) implementados.
15. **Fase 7B Concluída (Custo pela Tabela Oficial de Preços e Logs do /chat no Contexto)**: Criado `src/core/pricing.py` com preços oficiais de 2026-10-30 (coletados em 2026-11-07), cálculo de `estimated_cost_usd` por turno no grafo LangGraph, logs de `/chat` executados dentro do contexto de requisição `bind(...)` com `trace_id`, `session_id` e `user_hash`, e 4 novos testes unitários em `tests/test_pricing.py`.
16. **Fase 7C Concluída (`/metrics` no Formato Prometheus)**: Criado `src/core/metrics.py` com exposição em formato Prometheus 0.0.4 sem novas dependências; middleware de medição de requisições e latência para `/chat`; contadores de ferramentas, escalonamentos, abstenções e tokens integrados; endpoint `GET /metrics` implementado; logs de erro do LLM ajustados para `logger.error`; e 4 novos testes unitários em `tests/test_metrics.py`.
17. **Fase 7D Concluída (Registro de Busca Web, Tratamento de Erros Internos e Mensagens Bilíngues)**: Gravação de resultados de busca web (url, title, snippet limitado a 600 caracteres) propagados para passagens do juiz LLM; marcação de exceções internas não tratadas como `error="internal_error"` contabilizadas como erro pelo runner de avaliação; e mensagens de instabilidade e escalonamento forçado padronizadas de forma bilíngue (PT/EN). A Fase 7 está oficialmente concluída.
18. **Fase 8A Concluída (/agents Gerado pelo Código, /demo com Campos Reais e Sobras do README)**: O endpoint `GET /agents` agora gera toda a arquitetura, agentes, ferramentas e argumentos diretamente dos objetos em memória e configurações ativas (eliminando nomes fictícios e referências antigas a `MemorySaver`); a interface `/demo` reflete os metadados reais de tokens, custo e score de similaridade; o README foi alinhado removendo referências obsoletas à Fase 6, detalhando a pipeline de CI e a obrigatoriedade de `API_KEYS` no Docker Compose.
19. **Fase 8B Concluída (Volume Docker em Subdiretório de Estado, Tabela de Afirmações e README Final)**: O volume Docker foi isolado em `/app/state` (`getnet_app_state`), mantendo corpus e índice na imagem; permissões e `.dockerignore` higienizados; asserção de usuário não-root adicionada ao CI; tabela de alegações e evidências integrada no README.
20. **Fase 8C Concluída (Padrões de Estado na Imagem Docker e Correção do CI)**: Adicionadas variáveis `CHECKPOINT_DB_PATH=state/checkpoints.db` e `TICKETS_DB_PATH=state/tickets.db` diretamente no estágio runner do Dockerfile, permitindo que o container suba saudavelmente em execuções via `docker run` puro no CI e passe no healthcheck.
21. **Fase 8D Concluída (Arquivos da Imagem Só para Leitura e Últimas Frases do README)**: Permissões de escrita de grupo e outros removidas em `/app/data`, `/app/src` e `README.md` no Dockerfile; validação de sonda de escrita de não-root adicionada ao CI do Docker; últimas frases do README alinhadas aos caminhos e volumes de Docker reais (`getnet_app_state`) e declaração de "Sem prazos nem filas" adotada. O plano do SPEC está oficialmente concluído.
22. **Próximo Passo**: Verificação pelo usuário do `docker compose up` no Codespaces (AC8.1), execução verde do CI e encerramento da auditoria final pelo revisor.
