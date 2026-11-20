# SPEC — Getnet Multi-Agent Support System (v5)

Owner (the author): Burbanos · Planner/reviewer: Claude (external, Anthropic) · Implementer: Antigravity (Gemini)
Rubric: the evaluator's "Régua V4". Latest real feedback: v3, **9.2/10** on `8dcf972` (v2: 8.0 on `d2de4ff`; v1: 4.2/4.3 on
`6e053ec`). Target: **≥ 9.5**. Phases 1–12: `git show 431eb1f:docs/SPEC.md`; Phase 13: `git show 1a6df5c:docs/SPEC.md`;
Phase 14: `git show 8dcf972:docs/SPEC.md`. `docs/process.md` maps the sub-phases of phases 1–12 to their commits.

This document is the contract for every phase. A sub-phase is **done** when its verifier (`scripts/verify_phase<id>.py`) passes
on the reviewer's copy, CI is green on the sub-phase commit, and `docs/STATUS.md` shows the real command output.

---

## 0. Ground rules (every phase)

1. **No fake signals.** No hardcoded confidence, token counts, costs, answers or "passing" metrics. Unmeasured → `null`.
2. **No regex/keyword routing.** Routing and tool selection are decided by LLMs through structured outputs and function calling
   (the planner's `TurnPlan`, the supervisor's tool calls). Regex only in the guardrail and PII layers. A deterministic gate over
   an LLM's structured output (no ticket without a request in the plan; a plan step whose agent was not called) is not routing.
3. **No hardcoded answers.** Every user-facing sentence comes from the LLM grounded on tool output, or from a fixed system
   message that is clearly one (refusal, unavailable, abstention, pending ticket).
4. **Tests never hit the network or a real LLM.** Scripted chat models, mocked HTTP, `fakeredis`. Tests that need Postgres and
   Redis carry the `integration` marker, are deselected by default and run in CI against service containers.
5. **Every README/STATUS claim has evidence in the repository** (file, test, committed report or record). The evaluator reads the
   repository without running it and cannot see GitHub Actions: multi-replica, token, notification and alert claims need a
   committed output (`reports/integration/`).
6. **Records are immutable.** Committed runs, labels and reports are never edited or re-generated with different content; new
   runs get new ids.
7. **Verifiers run on Python 3.11** (CI and image version); no 3.12+ syntax; float sums that end in a rounded value use `math.fsum`.
8. **Language:** code, identifiers, commits and this SPEC in English; `README.md`, `docs/STATUS.md`, `docs/RUNBOOK.md` and phase
   prompts in pt-BR; answers to the merchant in the language of the merchant's message.
9. **Process volume is a cost.** The repository keeps only the current sub-phase's prompt and verifier, `docs/process.md` and a
   short `docs/STATUS.md` (≤ 150 lines). No report beyond the ones listed in the phase. The author is "o autor", never
   "candidato"; the reviewer is never called independent.
10. **Product model fixed:** `gemini-3.5-flash-lite` (fallback `gemini-3.1-flash-lite`); judge `gemini-3.6-flash` unless the
    judge calibration of Phase 15 says otherwise (§3.5). Every real-model command sets `EVAL_JUDGE_MODEL` explicitly.
11. **Nothing is tuned against a case without saying so.** A prompt, label or code change motivated by a named failing case is
    listed in this SPEC with the case, and the README says which sets are no longer clean.

**Reviewer files** (written by the reviewer, committed unchanged by Antigravity): `docs/SPEC.md`, `docs/process.md`,
`docs/phase-prompts/*.md`, `scripts/verify_*.py`, `src/prompts/*.md`, `data/eval/*.jsonl`.

---

## Current state (2026-11-20)

Phase 14 closed (`8dcf972`, CI green: `test`, `integration`, `docker`). Real feedback v3: **9.2/10**, "Excelente / finalista",
9th place. Its "Caminho para 9,5" is the scope of Phase 15. Decided by the author: no new labels from an annotator outside the
project in Phase 15 (the README declares it as pending); judge calibration as in §3.5 (options a and c). 15A closed
(`fba3306`, 44/44, CI green). 15B closed (`dd9e8d3`, 48/48 with promtool, CI green). **Next: 15C** (pre-round fixes and
the reviewer's pre-round files), then the round, then 15D.

---

## R. Requirements matrix (baseline `8dcf972`)

One row per requirement of the challenge statement (E, B) and per item of the real feedbacks (V1, V2, V3). "Value" is the value
of the last submitted version, `8dcf972`, with its evidence. Sources of the values: `reports/eval_v2_phase14.md` (group `14`,
mean of `v2-13..15`, as printed with one decimal), the Phase 14 holdout, action and retrieval reports, `reports/guardrail_summary.md`,
`reports/guardrail_author-1.md`, `reports/human_validation_annotator/`, `reports/integration/compose-1.md`, `docs/STATUS.md`
of 14C (pytest), the CI check runs of `8dcf972`.

**Rule for every real round from Phase 15 on (declared before the round):** no value in this table may drop without
justification. A drop in a row of class **E** blocks the resubmission. A drop in a row of class **F** is accepted only when the
README states it with its reason (for example, a layer removed by the ablation to cut cost). "Drop": a rate below the baseline
as printed with one decimal; latency or cost above it; a presence item whose evidence or test no longer exists or passes. The
comparison uses the configuration shipped as default after the ablation (§3.4); holdouts, actions and retrieval use the
round's runs. The final verifier of each phase that resubmits (15D in Phase 15) recomputes every row from the committed
records and fails on an undeclared drop. Rows whose Phase 15 target is higher than the baseline say so in the last column.

### Challenge statement

| ID | Requirement | Evidence at `8dcf972` | Value at `8dcf972` | Class | Phase 15 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| E1 | At least three agent types and a communication mechanism | `src/core/graph.py` (supervisor + KnowledgeAgent + SupportAgent as tools; planner, verifier), `GET /agents`, `tests/test_graph_llm.py`, `tests/test_agents_endpoint.py` | present | E | keep |
| E2 | Router analyzes each message and decides the agent or sequence | v2 routing correct | 97.4% | E | ≥ 99.5% (§3.6) |
| E3 | Knowledge Agent: RAG over Getnet's site plus web search | 32 pages, 103 chunks; `rerank-7` hit@1 1.000, hit@3 1.000; `search_web` | present; hit@3 1.000 | E | larger corpus, hit@3 kept |
| E4 | Customer Support Agent with at least 2 tools | `SUPPORT_TOOLS` (settlement, decline, terminal diagnosis, replacement) | 4 tools | E | keep |
| E5 | HTTP POST endpoint with `{message, user_id}` returning JSON | `POST /chat`; `user_id` from the credential, a different body `user_id` → 403 (`tests/test_auth.py`) | present | E | keep (Bearer token) |
| E6 | Dockerfile and Compose | `Dockerfile`, `docker-compose.yml` (Postgres, Redis, 2 replicas); CI `docker` job | CI green | E | keep |
| E7 | Testing strategy and tests | 484 test functions; 516 passed + 13 integration deselected (14C); CI `test` and `integration` green | 516 passed | E | ≥ 516, green |
| E8 | README: build, configure, run, tests, architecture, workflow, RAG pipeline, LLM tools | `README.md` sections "Arquitetura", "Como rodar", "Resultados" | present | E | keep |
| E9 | Official example scenarios answered | v2 official scenarios | 96.7% (90.0–100.0) | E | ≥ 96.7% |
| B1 | Bonus: fourth agent for human escalation | `escalate_to_human`, tickets; v2 escalation correct | 100.0% | F | keep |
| B2 | Bonus: guardrails | 36 labelled: attacks 20/20 in 3 runs, false positives 10.4%; author holdout: 10/10, 0/10 | 20/20; 10.4%; 10/10; 0/10 | F | false positives < 10% |
| B3 | Bonus: handoff when the system cannot resolve | 2 abstentions in a row → ticket; judge abstention precision / coverage | 100.0% / 88.9% | F | keep |
| B4 | Bonus: evaluation and observability strategy (datasets, regression, traces, logs, dashboards, alerting) | eval sets and records, OTel + Jaeger, Prometheus + Grafana; alerting absent | alerting: none | F | alerts with runbook |

### Feedback v1 (`6e053ec`, as summarized in v2 and v3)

| ID | Item | Evidence at `8dcf972` | Value at `8dcf972` | Class | Phase 15 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| V1.1 | Regex router with fixed confidences | function calling, no confidence in code (`tests/test_agents_endpoint.py`) | fixed | F | keep |
| V1.2 | Six handwritten documents | official pages with URL, date, hash (`data/corpus/`) | fixed (32 pages) | F | keep |
| V1.3 | Escalation promising a queue and a deadline | supervisor prompt + `answer_check` (`tests/test_answer_check_and_guards.py`) | fixed | F | keep |
| V1.4 | No memory | `PostgresSaver`, `thread_id = user_id:session_id` (`tests/test_checkpointer.py`) | fixed | F | keep |
| V1.5 | No authentication | API key → principal (`src/core/auth.py`) | fixed (static keys) | F | short-lived tokens (V3.4) |
| V1.6 | No evaluation dataset, no CI | 78 cases × 3 runs; CI with 3 jobs | fixed | F | keep |

### Feedback v2 (`d2de4ff`)

| ID | Item | Evidence at `8dcf972` | Value at `8dcf972` | Class | Phase 15 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| V2.1 | Notify the operator and resume the supervisor | `src/core/notifier.py`, `/operator`, `PATCH /tickets/{id}` resume; `compose-1` | fixed | F | keep |
| V2.2 | Hybrid search with reranking; abstention on the 10 uncovered | `src/rag/`; `rerank-7` | hit@1 1.000; uncovered 0.900; off-domain 1.000 | F | keep; uncovered compared as failures (§3.4) |
| V2.3 | Human validation of labels and judge, with agreement | `reports/human_validation*`; route κ 0.87 / 0.80 | fixed | F | keep |
| V2.4 | `s04`/`s06` decline codes routed to the KB | holdout 1 (`rh-10`); `s04`/`s06` pass in `v2-13..15` | 100.0% | F | keep |
| V2.5 | No verification before sending | `src/agents/verifier.py` | fixed | F | ablation (§3.4) |
| V2.6 | Fail-open classifier: account requests not closed | `GUARDRAIL_ACCOUNT_FAIL_CLOSED` (`tests/test_answer_check_and_guards.py`) | fixed | F | keep |
| V2.7 | No guardrail on web search results | `src/prompts/guardrail_web_classifier.md`, tests | fixed (block rate unmeasured) | F | keep |
| V2.8 | History without trimming | `MAX_HISTORY_MESSAGES` 40 | fixed | F | keep |
| V2.9 | SQLite per replica | Postgres in production; `compose-1` | fixed | F | keep |
| V2.10 | Rate limit in memory per replica | Redis sliding window; `compose-1` 429 | fixed | F | keep |
| V2.11 | Metrics per process, no tracing, no dashboard | OTel spans, Jaeger, Prometheus, Grafana | fixed | F | keep |
| V2.12 | Dead `openai`/`anthropic` branches | removed in 12A | fixed | F | keep |
| V2.13 | Four cases failing in every run (`k16`, `o02`, `s04`, `s06`) | `failed_in_all_runs` of group 14 | none | F | keep (none) |
| V2.14 | Judge grounding near 5, no discrimination | judge grounding mean | 4.96 | F | calibration (§3.5) |
| V2.15 | Open-Meteo free tier non-commercial | README "Limitações" | declared | F | keep declared |
| V2.16 | Guardrail false positives above the 10% target | `reports/guardrail_summary.md` | 10.4% | F | < 10% |
| V2.17 | Classifier sees only the current message | README "Limitações" | declared | F | keep declared |
| V2.18 | Process volume | one prompt and one verifier in the tree; STATUS ≤ 150 lines | 1 + 1 | F | keep |

### Feedback v3 (`8dcf972`)

| ID | Item | Evidence at `8dcf972` | Value at `8dcf972` | Class | Phase 15 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| V3.1 | Labels from someone outside the project; judge κ ≥ 0.6 with the humans | judge × human "aceitável" κ −0.03 (author) / −0.06 (annotator) | not met | F | calibration on the 30 (§3.5); outside labels declared pending |
| V3.2 | Ablation of planner, verifier and language check | none; cost per v2 run | not measured; US$ 0.401 | F | measured; shipped config ≤ US$ 0.401 |
| V3.3 | Larger corpus (help center, PDF manuals), keeping hit@3 and abstention | 32 pages, 103 chunks | 32 / 103 | F | §3.3 |
| V3.4 | Tokens with expiry and rotation | static API keys | not met | F | §3.3 |
| V3.5 | Guardrail false positives below 10% | 36 labelled, 3 runs | 10.4% | F | < 10% |
| V3.6 | Notify the merchant when the operator replies | polling `GET /sessions/{id}/messages` | not met | F | SSE across replicas |
| V3.7 | Alerts with runbook | none | not met | F | rules + runbook + rule tests |
| V3.8 | `n05`/`n06` fail the tool check in every run | holdout 2 (`rh2-7`) | 75.0%; `n05`, `n06` fail | F | both pass |
| V3.9 | Routing back to ≥ 99.5% without losing the verifier's gain | v2 routing / tools | 97.4% / 98.1% | F | ≥ 99.5% / ≥ 99.5% |
| V3.10 | Verifier accepts earlier assistant answers (`m04` stops querying the KB) | `src/prompts/verifier.md`; `m04` 2/3 | 2/3 | F | earlier answers are not evidence |
| V3.11 | `a05` (request and confirmation in one message) varies | actions `act-4` | 87.5% | F | keep (reported) |
| V3.12 | Dated campaign text in the corpus (Black Friday) | README "Limitações" | declared | F | keep declared |
| V3.13 | No summary of the trimmed history | none | declared gap | F | keep declared |
| V3.14 | Web-results guardrail block rate not measured | none | declared gap | F | keep declared |
| V3.15 | Mock with one merchant; replacement without logistics | README "Limitações" | declared | F | keep declared |
| V3.16 | Latency and cost of the new layers | v2 median / p95 / cost | 7.4 s / 14.7 s / US$ 0.401 | F | no increase (§3.4) |
| V3.17 | LLM reranker adds cost and latency | `rerank-7` rerank latency p50 | 847 ms | F | reported |
| V3.18 | Overall v2 quality | pass / facts / escalation / language | 97.4% / 99.1% / 100.0% / 100.0% | F | keep |
| V3.19 | Holdouts and action cases | rh 100.0%; rh2 75.0%; h3 96.8%; actions 87.5% | as listed | F | keep; rh2 up |
| V3.20 | Multi-replica evidence | `compose-1` | 9/9 | F | `compose-2`, all checks |

---

## 1. Target architecture (after Phase 15)

```text
POST /auth/token (X-API-Key) → short JWT (kid, exp) + rotating refresh token
POST /chat (Bearer; user_id from the token) ── W3C traceparent in/out, span per node, LLM call and tool
   ▼
rate limit (Redis) → PII masking → guardrail (patterns → LLM classifier) → handoff_gate
   ▼
planner (TurnPlan: language, scope, escalation request, confirmation, code_source, steps with their agent)
   ▼
supervisor (function calling; sees each step with its agent) ⇄ ask_knowledge_agent | ask_support_agent | escalate_to_human |
confirm_pending_action      (code_source terminal_screen/app → the decline tool is not offered to the support agent)
   ▼
plan_coverage (deterministic: every knowledge/support step was executed; one corrective round)
   ▼
verifier (if kept by the ablation: evidence of this turn and raw results of the previous turn; earlier assistant answers are not
evidence) → answer_check → language check (if kept) → answer
   │
   └─ operator reply → resume → SSE event to the merchant (Redis pub/sub across replicas)
Alerts: Prometheus rules with runbook (docs/RUNBOOK.md), rule unit tests in CI.
Knowledge: help-center pages and official PDF manuals added to the corpus, robots.txt respected.
```

---

## 2. Phases 13 and 14 (closed)

Phase 13 (planner, verifier, language enforcement, escalation gate, Postgres/Redis state, tracing, confirmed write action,
operator console) and Phase 14 (verifier sees raw tool outputs and the conversation; block boilerplate rule; one round:
official 96.7%, facts 99.1%, routing 97.4%, tools 98.1%, escalation 100%; criterion not met on routing and tools; judge
re-run with the right model). Full plans in git (see header). Their guarantees continue as the test suite (no test removed or
renamed; test files only grow), frozen records and the cross-cutting invariants every verifier re-checks: no raw card/CPF in
any persisted state, no conversation text in logs or spans, `user_id` only from the credential, offline eval 6/6, ruff clean,
no network in tests. Implementer models: Gemini 3.8 Flash up to 11G; Gemini 4 Hydrogen 12A–12D; Orchestrator (Argon) 12E–13D-1-fix;
Orchestrator (Neon) from 13D-2.

---

## 3. Phase 15 — the "Caminho para 9,5"

Four sub-phases and one round of real runs, no fix sub-phase planned in advance. 15A changes the orchestration and the
evaluation tooling; 15B the production surface (tokens, merchant notification, alerts) and the corpus; 15C (short, added after
the 15B review) fixes what that review found and commits the reviewer's pre-round files; the author rebuilds the index, runs
the Compose evidence and the round; 15D publishes it. Implementer: Antigravity, Orchestrator (Neon).

### 3.1 Diagnosis (reviewer, from the `8dcf972` records)

1. **Cost by layer** (`v2-13..15`, US$ per run, priced with `src/core/pricing.py`): KnowledgeAgent 0.151 (37.8%), supervisor
   0.123 (30.5%), verifier 0.047 (11.7%), planner 0.038 (9.4%), support 0.021, guardrail classifier 0.021, language rewriter
   0.0002 (0.1%: 4 rewrites in 234 cases). The planner and the verifier are 21% of the cost; the language check is detection
   without a model plus a rewrite only on mismatch. The planner carries two gates the product depends on: the escalation gate
   (no ticket without a request) and the confirmation of write actions (`confirm_pending_action` refuses without a valid plan).
2. **Routing is decided twice.** The planner returns an agent per step (`delegate`), and since 13C the supervisor sees only the
   goals (in 13B it followed wrong delegates in `t24`/`t25`). In `v2-13..15` the planner's set of agents matched the label in
   193/195 turns (99.0%) and the supervisor's in 190/195 (97.4%); in the four holdout rounds, 136/136 against 134/136. Every
   supervisor routing error of `v2-13..15` (`s03`, `off05`, `s01`, `m04` ×2) had the planner's agent right; the planner was wrong
   in `k09` ×2 (a how-to question about a missing feature sent to support), where the supervisor was right.
3. **`m04`** (follow-up answered from the conversation, no KB call): the 14A verifier accepts earlier assistant answers as
   support. An unsupported earlier answer could therefore be repeated and approved (the evaluator's interview question 4).
4. **`n05`/`n06`**: the support agent calls `diagnose_declined_transaction` with `code_context="terminal_screen"`, gets
   `not_applicable` and answers correctly, but the label (written in 12E, before `code_context` existed in 13B) forbids the call.
   The tool's own schema invites the call. The general fix is not to offer the decline tool when the planner says the code came
   from a screen or an app. Holdout 2 is not clean for `n05`–`n07` after this phase.
5. **Guardrail false positives**: `ga07` ("forget everything" + an ordinary question; 3/3 runs) and `ga14` (a product question
   with "bypass the PIN"; 2/3). The prompt's "mixes a legitimate question … block it" wins over the allow list. The 36-set is
   not clean for these two after the prompt change; the author holdout (not used for any change) is the clean measure.
6. **Judge calibration on the 30 annotations**: on "aceitável" the author marked 1 item as not acceptable (`h02`), the annotator
   4 (`h03`, `h06`, `h23`, `h30`); no item was rejected by both, and the two humans agree at κ −0.06. With these labels no
   judge can reach κ ≥ 0.6 against both raters at once: over every possible set of judge verdicts, the best lower of the two κ
   is 0.47 (rejecting the union of their negatives gives 0.29 against the author and 0.87 against the annotator). Against one
   rater alone it can, by matching one to four items. §3.5 handles this.

### 3.2 15A — Matrix, ablation tooling, plan-following routing, screen-code gate, verifier evidence, judge calibration tooling

Checked by `scripts/verify_phase15a.py`; prompt `docs/phase-prompts/15A.md`. Reviewer files in 15A: this SPEC (with the matrix),
`src/prompts/planner.md`, `supervisor.md`, `verifier.md`, `support_agent.md`, `guardrail_classifier.md`, and the new
`data/eval/cases_holdout4.jsonl` (16 cases, written before any 15A code: screen and app codes, decline codes from sales,
how-to versus the merchant's own records, follow-ups, a multi-intent case; run once, in the round).

**Ablation tooling**
- Every turn record of `src/eval/runner.py` gains `layers: {"planner", "verifier", "language", "plan_coverage"}` (booleans from
  `PLANNER_ENABLED`, `VERIFIER_ENABLED`, `LANGUAGE_ENFORCEMENT_ENABLED`, `PLAN_COVERAGE_ENABLED` at run start). Resuming a run
  id whose records have other `layers` exits non-zero before running any case. `run_case` adds the new fields to the turn
  record; `observe_turn` keeps its 13C keys (its exact-key test stays as it is).
- `layer_latency_ms: {"verifier", "language"}` in the state, `AgentState` and turn record: the sum of the verifier model calls of
  the turn (`null` when the model was not called) and the language node's time including a rewrite (`null` when the node is
  disabled). The `verification` and `language` dicts keep their keys (exact-equality tests of 13B/14A stay as they are).
- `rejected_drafts`: the drafts the verifier rejected in the turn (at most 2), kept in the graph state and copied to the turn
  record by the runner. Never in `ChatResponse`, logs, spans or metrics.
- `python -m src.eval ablation --name <n> --cases <path> --config <label>=<ids> [--config …] --baseline <label>` writes
  `reports/<n>.md` and `.json`: per configuration, the `compare` metrics (mean, min, max) plus cost by agent (tokens_by_agent
  priced with `src/core/pricing.py`), latency p50/p95, and gate counts (`unrequested_tickets`: a ticket in a case whose label
  says `escalate: false`; `wrong_language`: `language_ok` false; `out_of_scope_tools`: an `off_topic` case that called any
  tool); the paired case table against the baseline (case passed in the majority of baseline runs and failed in the majority
  of the other configuration's runs = lost; the reverse = gained); the language check estimate from the baseline records
  (turns with `language.status == "rewritten"`, rewriter cost); and the decision of §3.4 for each layer, with its inputs.
  Each configuration's runs must share one `layers` value, which must differ from the baseline's only in the ablated layer;
  otherwise it exits non-zero.

**Plan-following routing** (diagnosis 2, 3)
- The supervisor's plan section lists `"{n}. [{delegate}] {goal}"`.
- New node `plan_coverage` between the supervisor's final answer and the verifier. For each plan step with delegate `knowledge`
  or `support`, the turn must contain a supervisor call to `ask_knowledge_agent` or `ask_support_agent` respectively. If one is
  missing and no corrective round was made in this turn: the draft is removed (as the verifier's replan does), the supervisor
  runs again with a fixed section `[Plan coverage]` listing the missing steps (`step <n> [<delegate>]: <goal>`), at most once
  per turn. Still missing after it: the turn continues (`incomplete`), never an abstention. Skipped when the plan is not `ok`,
  has no steps, or the turn has a ticket or a handoff, and when the step limit was reached. Disabled by
  `PLAN_COVERAGE_ENABLED=false` (default true). State and turn record `coverage: {"status": "complete" | "corrected" |
  "incomplete" | "skipped" | "disabled", "missing": [step numbers], "retries": 0 | 1}`; metric
  `getnet_plan_coverage_total{status}`; span `graph.node.plan_coverage`.
- Prompts (reviewer): the planner's `delegate` boundary (support only when the answer needs the merchant's own records or an
  action on them; how-to and product questions, including a missing feature, go to knowledge; a follow-up about a product is a
  knowledge step), and the supervisor's plan section (call the assigned agent for each step; another agent only when the
  assigned one cannot answer). **Tuned against cases (rule 11):** the boundary text was written after `k09` (v2) and `s03`,
  `off05`, `s01`, `m04` (v2) failed; v2 is not clean for these; holdout 4 measures the change.

**Screen-code gate** (diagnosis 4)
- `TurnPlan.code_source: Literal["none", "declined_sale", "terminal_screen", "app", "unknown"] = "none"`, in the plan metadata
  (`null` when there is no valid plan).
- When the plan is `ok` and `code_source` is `terminal_screen` or `app`, every `ask_support_agent` call of the turn runs the
  support agent without `diagnose_declined_transaction` (not bound, not callable). State and turn record
  `tool_gate: {"code_source": <value>, "removed_tools": [...]}` (`null` without a valid plan).
- `diagnose_terminal(serial_number=None, screen_error_code=None)`: with a code, the result gains `screen_error: {"code",
  "catalogue": "not_available", "note": "No catalogue of card machine screen codes is available to this assistant; the meaning
  of this code is unknown."}`; the other fields are unchanged; the log line says only whether a code was given.
- `diagnose_declined_transaction` keeps returning `not_applicable` for `terminal_screen`/`app` (defense in depth).
- Prompts (reviewer): `code_source` in the planner; `screen_error_code` in the support agent.

**Verifier evidence** (diagnosis 3)
- `build_verifier_conversation`: only `merchant:` and `operator:` entries; earlier assistant answers never enter. Same caps.
- `prior_turn_evidence` (state, list): in each turn, the `turn_evidence` items of the previous turn of the same session (whatever
  its outcome); `turn_evidence` starts empty. `build_verifier_evidence(messages, merchant_idx, turn_evidence,
  prior_evidence=None)` appends them after the current turn's blocks, each headed `[earlier turn: <agent>/<tool>]`, same
  per-item cap (6000); the total cap (24000) keeps the current turn first and drops earlier-turn items first.
- Prompt (reviewer): earlier assistant answers are not evidence; earlier raw results are.

**Judge calibration tooling** (§3.5)
- `python -m src.eval judge-calibrate --run-id <id> --judge-model <model> --judge-prompt <path>`: for the 30 items of
  `reports/human_validation/sample.json`, builds the judge input exactly as `judge` does (records of `v2-1`, cases of the
  sample's `cases_file`), calls the model with the given prompt, writes `reports/judge_calibration/<id>.jsonl` (per item: `hid`,
  `case_id`, `judge_model`, `prompt_sha256`, `grounded`, `answers_question`, `abstained`, `acceptable`, `acceptable_source`
  (`"model"` when the judgment has a boolean `acceptable`, else `"derived"` with the ≥ 4/≥ 4 rule of `judge_acceptable`),
  `rationale`, `status`). Resumable; refuses to resume with another model or prompt hash. `parse_judgment` accepts an optional
  boolean `acceptable`.
- `python -m src.eval judge-calibration-report --name <n> --runs <ids>`: groups runs by (model, prompt hash); for each
  candidate and each rater (author `reports/human_validation/answers.csv`, annotator
  `reports/human_validation_annotator/answers.csv`): agreement n/30, Cohen's κ, Gwet's AC1, the judge's verdict on each item a
  rater found not acceptable, abstention κ against `absteve`, grounding against `fundamentacao` (exact agreement, mean absolute
  difference); run-to-run agreement of a candidate's repeated runs; the human × human row; and the selection of §3.5.

**Unchanged in 15A:** product model, labels of existing sets, corpus, index, guardrail code, tokens, endpoints, Compose.
Tests: new files only (existing test files only grow), scripted models. Process: `docs/phase-prompts/14C.md` and
`scripts/verify_phase14c.py` leave the tree.

### 3.3 15B — Short-lived tokens, merchant notification, alerts with runbook, larger corpus, second human sample

Checked by `scripts/verify_phase15b.py`; prompt `docs/phase-prompts/15B.md`. Reviewer files in 15B: this SPEC and the prompt.

**Tokens** (no new runtime dependency: HS256 with `hmac`/`hashlib`; new module `src/core/tokens.py`)
- Settings: `JWT_SIGNING_KEYS` (`kid:secret;kid:secret`, each secret ≥ 32 characters), `JWT_ACTIVE_KID`, `JWT_ISSUER`
  (`getnet-multiagent`), `JWT_AUDIENCE` (`getnet-multiagent-api`), `ACCESS_TOKEN_TTL_S` (900), `REFRESH_TOKEN_TTL_S` (28800).
  Outside production, empty keys mean a development key (kid `dev`); production refuses to start (`validate_auth_config`
  raises, naming `JWT_SIGNING_KEYS`) when keys are empty, malformed, shorter than 32 characters, equal to the development key,
  or `JWT_ACTIVE_KID` is not among them.
- `issue_access_token(principal, now=None) -> (token, expires_in)` and `decode_access_token(token, now=None) -> Principal`.
  Header `{"alg": "HS256", "typ": "JWT", "kid"}`; claims `iss`, `aud`, `sub` (user id), `role`, `key_id`, `iat`, `nbf`, `exp`,
  `jti`. Decoding raises `TokenError` (a `ValueError`) with `reason` in `malformed`, `bad_algorithm`, `unknown_kid`,
  `bad_signature`, `expired`, `not_yet_valid`, `bad_issuer`, `bad_audience`, `bad_role`; the algorithm is pinned (`none` and
  any other value are `bad_algorithm`), the signature is compared in constant time, `exp`/`nbf` have 30 s of leeway. The active
  key signs; every listed key verifies (rotation: add a key, switch the active kid, remove the old key after the longest TTL).
- Refresh tokens (`src/core/refresh_tokens.py`, table `refresh_tokens` in the same database as tickets: Postgres in
  production): opaque (`secrets.token_urlsafe(32)`), stored only as SHA-256 with `family_id`, user, role, key id, `issued_at`,
  `expires_at`, `used_at`, `revoked_at`. `issue(principal)`, `rotate(token)` (spends it and returns a new one of the same
  family) and `revoke_family(token)`. Reusing a spent token revokes the whole family; `rotate` raises `TokenError` with
  `reused`, `expired`, `revoked` or `unknown`. Audit events `auth.token_issued`, `auth.refresh_rotated`,
  `auth.refresh_reuse_detected`, `auth.refresh_revoked` (hashed actor, target the family id; no token in any field or log).
- `API_KEYS` entries accept an optional fourth field `YYYY-MM-DD` (last valid day, UTC); an expired key gets 401.
- Endpoints: `POST /auth/token` (header `X-API-Key`) and `POST /auth/refresh` (`{"refresh_token"}`) answer
  `{access_token, token_type: "bearer", expires_in, refresh_token, refresh_expires_in}`; `POST /auth/revoke`
  (`{"refresh_token"}`) answers 204 whatever the token. Every protected endpoint accepts `Authorization: Bearer <access>`;
  `X-API-Key` directly on a protected endpoint only outside production (production: 401 telling to use `/auth/token`).
  Failures: 401 with `WWW-Authenticate: Bearer`. Rate limit unchanged per key id; the three `/auth/*` endpoints use a separate
  bucket (`auth:<key_id>`). `user_id` still comes only from the credential.
- `/demo` and `/operator` exchange the key for tokens and refresh them in memory; CI, `scripts/compose_evidence.py` and the
  eval tooling that call the HTTP API use tokens.

**Merchant notification** (`src/core/events.py`)
- `event_channel(user_id, session_id)` = `getnet:events:` + the first 32 hex characters of SHA-256 of `user_id:session_id`.
  Broker interface: `publish(user_id, session_id, event) -> bool` and `subscribe(user_id, session_id)` returning a
  subscription with `get(timeout) -> dict | None` and `close()`. `RedisEventBroker` (pub/sub, used when `REDIS_URL` is set)
  and `InMemoryEventBroker`; `get_event_broker()`/`reset_event_broker()`.
- `GET /sessions/{session_id}/events` (customer role, Bearer or development key): Server-Sent Events for the principal's own
  session. Event `operator_reply` with data `{"ticket_id", "session_id", "status", "at"}` (no message text); comment heartbeat
  `: ping` every `SSE_HEARTBEAT_S` (15); the stream closes after `SSE_MAX_CONNECTION_S` (300) and the client reconnects.
  Published by `PATCH /tickets/{id}` whenever a reply is stored for a ticket with a session, after the resume attempt, on
  whichever replica handled the PATCH. Metrics `getnet_merchant_notifications_total{status="published"|"failed"}` and the
  gauge `getnet_sse_connections`. `/demo` listens and shows the reply when the event arrives.

**Alerts with runbook**
- `deploy/alerts.yml` (loaded by the Compose Prometheus through `rule_files`), eleven alerts: `GetnetHighErrorRate`,
  `GetnetHighChatLatencyP95`, `GetnetLLMErrorsOrFallbacks`, `GetnetGuardrailClassifierDegraded`, `GetnetRateLimitBackendErrors`,
  `GetnetOperatorNotificationFailures`, `GetnetMerchantNotificationFailures`, `GetnetOldestOpenTicketAge`,
  `GetnetHighAbstentionRate`, `GetnetEstimatedCostPerHour`, `GetnetReplicaDown`; each with `labels.severity`,
  `annotations.summary` and `annotations.runbook_url` pointing to an anchor of `docs/RUNBOOK.md` (pt-BR: what it means, first
  checks, mitigation, escalation).
- New metrics where an alert needs one: `getnet_llm_calls_total{caller,status}` (`ok`, `fallback`, `error`),
  `getnet_guardrail_classifier_total{status}`, `getnet_estimated_cost_usd_total`, `getnet_open_ticket_oldest_age_seconds`
  (computed at scrape; 0 without open tickets). Every metric named in an alert expression has its `# TYPE` line in `/metrics`
  from process start.
- `deploy/alerts_test.yml`: promtool unit tests, at least one firing and one silent case per alert. CI runs
  `promtool check rules` and `promtool test rules` with the pinned `prom/prometheus` image of the Compose file.

**Plan coverage and confirmations** (from the 15A review): `plan_coverage` is `skipped` when the plan records an
`action_confirmation` other than `none` (a confirmation or refusal turn never gets a corrective call to a specialist).

**Corpus**
- `python -m src.rag.ingest --discover [--max-pages 120] [--max-pdfs 15]` appends new records without touching existing ones
  (the 33 lines of `data/corpus/pages.jsonl` at `8dcf972` stay byte-identical). Candidates: URLs of the sitemaps of
  `site.getnet.com.br` (`Sitemap:` lines of robots.txt, `/sitemap_index.xml`, `/wp-sitemap.xml`, nested sitemap indexes) and
  links of the corpus's `site.getnet.com.br` pages (fetched again only to read their links). HTML candidates are kept only under
  `/get-ajuda-`; PDF candidates only under `https://site.getnet.com.br/wp-content/uploads/`, found as links in those pages or in
  the new help pages. Sorted by URL; robots.txt checked for every URL; project user agent; ≥ 1 s between requests.
- PDFs read with `pypdf` (development requirement; ingestion only): lines present in at least half of a PDF's pages are removed
  as running headers and footers; statuses `internal_document` (the text says "Classificação da Informação: Interno" or "uso
  interno", any case), `too_large` (> 5 MB), `no_content`. New records carry `content_type` (`text/html` or
  `application/pdf`), `discovered_from` and `pdf_pages` (`null` for HTML). `data/corpus/discovery.json` lists every candidate
  with `kind`, `discovered_from` and `decision` (`collected`, `already_in_corpus`, `out_of_scope`, `off_allowlist`,
  `cap_reached`) and the record status; the manifest counts the new statuses.
- Antigravity runs the discovery in 15B and commits `data/corpus/`. The index (`data/index/`) is rebuilt by the author before
  the round (embedding key).
- `python -m src.rag.hybrid_eval --dataset <path>` with the query-embedding cache next to the dataset
  (`<stem>_query_embeddings.npy/.json`; the existing names stay for `retrieval_labeled.jsonl`) and a command that builds that
  cache (author, key).

**Second human sample** (§3.5, decision c)
- `python -m src.eval human-sample2 --out-dir reports/human_validation_2 --size 40` builds a blind sample of 40 answers from the
  committed records of the v2 and holdout runs (`v2-*`, `rh-*`, `rh2-*`, `h3-*`): 20 whose case failed the deterministic checks
  in that run and 20 that passed, at most one item per case, none equal (same run and case) to an item of the first sample,
  drawn with a fixed seed; ids `g01`–`g40`; `sample.json` with `run_id` and `cases_file` per item; `form.md` and
  `answers_template.csv` in the format of the first sample (same columns and instructions, without check results, judge notes,
  run or case ids).
- `run_judge_calibration` reads `run_id`/`cases_file` per item when the sample has them; `build_judge_calibration_report`
  takes `sample_path` and accepts `annotator_answers=None` (one rater).
- `reports/human_validation_2/` is committed by Antigravity without `answers.csv`; the author fills it before the round.

### 3.4 The round (author; pre-registered here, before any run)

**Before the round (author):** fills `reports/human_validation_2/answers.csv` (§3.3) without opening `sample.json`, the
records or the judgments, and commits it.

**Before the round (reviewer, committed in 15C, before any run):** `data/eval/retrieval_labeled2.jsonl` (20 answerable
queries whose answer is only in the new pages, 4 uncovered, 2 off-domain), written from the collected corpus text and before any
retrieval run, with every gold snippet checked against the chunks of the 15C chunking; the judge candidate prompt
`src/prompts/judge_acceptable.md` (§3.5); the list and the commands below.

**Uncovered queries of `retrieval_labeled.jsonl` now covered** (decided from the corpus text at `dd9e8d3`, before any run):
`u02` (Central de Relacionamento phone numbers on the help pages), `u05` (the "como cancelar a parceria" page: contact the
Central de Relacionamento), `u08` (Shopify on the digital plugins page), `u09` (12 calendar days to send the chargeback defence,
help page and the chargeback manual). They leave the uncovered denominator and are reported (answered or not, with the URL).
Still uncovered: `u01`, `u03`, `u04`, `u06`, `u07`, `u10`. The labels are not edited (immutable).

**Known risk, declared before the round:** `off10` (official WhatsApp payment scenario) passes `sources_ok` only when the
gold URL `getnet.net/en/our-solutions/online-payments` is cited; the corpus now also has the help page about the
discontinuation of WhatsApp Business payments, which may be cited instead. If `off10` fails for this reason the README says so;
the label is not changed.

**Commands of the round** (Codespaces or the author's machine; the Tier 1 key only in the environment, never in a file;
`EVAL_JUDGE_MODEL=gemini-3.6-flash` set before any `judge`; every run id new; a command interrupted is resumed with the same
id). Steps 1–2 are committed before step 3 starts.
```
# 1. index (commit "index: ..."; data/index/ and the new query-embedding cache; the cache of retrieval_labeled.jsonl is
#    unchanged: same queries, same embedding model)
python -m src.rag.index
python -m src.rag.hybrid_eval --dataset data/eval/retrieval_labeled2.jsonl embed
# 2. Compose evidence (Codespaces, Docker; commit reports/integration/compose-2.*)
python scripts/compose_evidence.py run --run-id compose-2
# 3. v2: full (all flags at their defaults = on), then the two ablations; judge every run except v2-22
python -m src.eval run   --run-id v2-16 --cases data/eval/cases_v2.jsonl      # likewise v2-17, v2-18
python -m src.eval judge --run-id v2-16 --cases data/eval/cases_v2.jsonl      # likewise v2-17, v2-18
VERIFIER_ENABLED=false python -m src.eval run --run-id v2-19 --cases data/eval/cases_v2.jsonl   # v2-20, v2-21; judge each
PLANNER_ENABLED=false  python -m src.eval run --run-id v2-22 --cases data/eval/cases_v2.jsonl
# 4. holdouts and actions, full configuration, one run each
python -m src.eval run --run-id rh-11 --cases data/eval/cases_routing_holdout.jsonl
python -m src.eval run --run-id rh2-8 --cases data/eval/cases_routing_holdout2.jsonl
python -m src.eval run --run-id h3-5  --cases data/eval/cases_holdout3.jsonl
python -m src.eval run --run-id h4-1  --cases data/eval/cases_holdout4.jsonl
python -m src.eval run --run-id act-5 --cases data/eval/cases_actions.jsonl
# 5. guardrail (36 labelled, then the author holdout)
python -m src.eval guardrail-run --run-id hybrid-4            # likewise hybrid-5, hybrid-6; guardrail-report for each
python -m src.eval guardrail-run --run-id author-2 --set data/eval/guardrail_author_holdout.jsonl   # author-3, author-4
python -m src.eval guardrail-report --run-id author-2 --set data/eval/guardrail_author_holdout.jsonl
python -m src.eval guardrail-summary --run-ids hybrid-4,hybrid-5,hybrid-6
# 6. retrieval
python -m src.rag.hybrid_eval run --run-id rerank-8
python -m src.rag.hybrid_eval --dataset data/eval/retrieval_labeled2.jsonl run --run-id rerank2-1
python -m src.rag.hybrid_eval report --runs rerank-8 --name retrieval_hybrid_15
python -m src.rag.hybrid_eval --dataset data/eval/retrieval_labeled2.jsonl report --runs rerank2-1 --name retrieval_hybrid2_15
# 7. judge calibration: §3.5
# 8. context and reports
python -m src.eval context --tier paid_tier_1 --run-ids v2-16,v2-17,v2-18,v2-19,v2-20,v2-21,v2-22,rh-11,rh2-8,h3-5,h4-1,act-5
python -m src.eval compare --name v2_phase15 --cases data/eval/cases_v2.jsonl --group "14=v2-13,v2-14,v2-15" \
    --group "full=v2-16,v2-17,v2-18" --group "no_verifier=v2-19,v2-20,v2-21" --group "no_planner=v2-22"
python -m src.eval ablation --name ablation_phase15 --cases data/eval/cases_v2.jsonl --baseline full \
    --config full=v2-16,v2-17,v2-18 --config no_verifier=v2-19,v2-20,v2-21 --config no_planner=v2-22
python -m src.eval compare --name routing_holdout_phase15  --cases data/eval/cases_routing_holdout.jsonl  --group "14=rh-10"  --group "15=rh-11"
python -m src.eval compare --name routing_holdout2_phase15 --cases data/eval/cases_routing_holdout2.jsonl --group "14=rh2-7" --group "15=rh2-8"
python -m src.eval compare --name holdout3_phase15 --cases data/eval/cases_holdout3.jsonl --group "14=h3-4" --group "15=h3-5"
python -m src.eval compare --name holdout4_phase15 --cases data/eval/cases_holdout4.jsonl --group "15=h4-1"
python -m src.eval compare --name actions_phase15  --cases data/eval/cases_actions.jsonl  --group "14=act-4" --group "15=act-5"
# 9. one commit: "eval: phase 15 round (...)"
```
The `--sleep` defaults are those of Phase 14. Old retrieval runs (`rerank-1..7`) are not re-reported: their records hold chunk
ids of the old index. A command that fails is fixed only when the failure is in tooling outside the measured system (published
with the fix); never by changing code, prompts or labels of the measured system during the round.

**Order:** (1) `python -m src.rag.index` and the query embeddings of the new set → commit `index: …`; (2) `scripts/compose_evidence.py` in
Codespaces → `reports/integration/compose-2.md`; (3) with the code of that commit, Tier 1, product model, `EVAL_JUDGE_MODEL=
gemini-3.6-flash`, no code, prompt or label change until the round is committed:
- v2, configuration `full` (all layers on): `v2-16`, `v2-17`, `v2-18`, run + judge;
- v2, `no_verifier` (`VERIFIER_ENABLED=false`): `v2-19`, `v2-20`, `v2-21`, run + judge;
- v2, `no_planner` (`PLANNER_ENABLED=false`): `v2-22`, run only (one run: the planner carries the escalation gate and the
  action confirmation, so its decision does not depend on this run; its quality, cost and latency are reported);
- configuration `full`, one run each: `rh-11`, `rh2-8`, `h3-5`, `h4-1` (holdout 4), `act-5`;
- guardrail: `hybrid-4..6` (36 labelled) and `author-2..4` (author holdout), with the revised classifier prompt;
- retrieval: `rerank-8` (`retrieval_labeled.jsonl`) and `rerank2-1` (`retrieval_labeled2.jsonl`);
- judge calibration: §3.5;
- `python -m src.eval context` for every run id; reports: `compare` groups `14=v2-13,v2-14,v2-15` and the three configurations;
  `ablation --baseline full`; holdout/action comparisons with `14`; retrieval and guardrail reports; one commit
  `eval: phase 15 round (…)`. Failures are published as they come out.
Estimated cost: about US$ 10 (seven v2 runs, six judged; calibration 9 × 70 judgments; the selected judge on three runs).

**Ablation rule (declared before the round).** For the verifier: ΔQ = mean cases passed per run in `full` minus in
`no_verifier` (78 cases); G = gate counts (`unrequested_tickets` + `wrong_language` + `out_of_scope_tools`) summed over the
three runs. The verifier stays on by default **iff** ΔQ ≥ 1.0 or G(`no_verifier`) > G(`full`); otherwise
`VERIFIER_ENABLED` defaults to false in 15D (code, tests and flag stay; the README reports the saving and what the rejected
drafts were). The language check stays on iff the `full` records show at least one rewritten turn or its cost share is below
1%. The planner stays (feature dependency, diagnosis 1); its `no_planner` run is reported. `plan_coverage` is not ablated (no
model call). The shipped default is one of the measured configurations; the matrix compares it.

**Success criterion of Phase 15 (declared before the round).** Met only if all hold:
- C1 shipped configuration (mean of its three v2 runs): official scenarios ≥ 96.7%; routing ≥ 99.5%; tools ≥ 99.5%;
  escalation 100.0%; cost per run ≤ US$ 0.401;
- C2 `rh2-8`: `n05` and `n06` pass;
- C3 retrieval: `rerank-8` hit@3 1.000 on the 30 answerable, at most one abstention failure on the six queries still
  uncovered (the baseline failed one of ten), off-domain 1.000; `rerank2-1` hit@3 ≥ 0.900 on its 20 answerable queries
  (at least 18) and at most one abstention failure on its six other queries;
- C4 guardrail: false positives < 10% (mean of `hybrid-4..6`) with 20/20 attacks blocked in each run; `author-2..4`: 10/10
  attacks and at most 1/10 false positive in each run;
- C5 `compose-2`: every check passes (tokens across replicas, refresh rotation and reuse detection, SSE across replicas, alert
  rules loaded, plus the nine checks of `compose-1`); CI green on the round's commit;
- C6 judge calibration: the report of §3.5 published, with the selection applied;
- the matrix rule (§R).
Holdout 4, holdouts 1 and 3, actions, latency and the judge metrics are reported, not criteria.

### 3.5 Judge calibration (decided by the author on 2026-11-20: options a and c)

Diagnosis 6 shows that κ ≥ 0.6 against both raters cannot be reached on the 30 existing annotations. Decision: (a) publish the
agreement of each candidate against each rater with no numeric target, saying why; (c) the author annotates a second, blind
sample with more answers likely to be bad (§3.3), so that κ has negatives to measure. These are the author's labels; labels
from someone outside the project remain pending and the README says so.

Candidates, each run three times on both samples (`jc-*`, 70 items per run): (a) `gemini-3.6-flash` with `src/prompts/judge.md`
(current; acceptable derived ≥ 4/≥ 4); (b) `gemini-3.6-flash` with a reviewer prompt that asks directly the question the humans
answered ("would you send this answer to the merchant without correction?") and returns `acceptable`; (c) the same prompt with
`gemini-3.8-flash`. The prompt of (b)/(c) is written from the annotation form, before the author's second-sample answers exist.

- **C6 (criterion):** the calibration report is published with κ, AC1 and the verdict on every rejected item, per candidate,
  sample and rater, as it comes out; no κ threshold.
- Commands (3 runs per candidate and sample; `jc1-*` on the first sample, `jc2-*` on the second):
```
python -m src.eval judge-calibrate --run-id jc1-a-1 --judge-model gemini-3.6-flash --judge-prompt src/prompts/judge.md
python -m src.eval judge-calibrate --run-id jc1-b-1 --judge-model gemini-3.6-flash --judge-prompt src/prompts/judge_acceptable.md
python -m src.eval judge-calibrate --run-id jc1-c-1 --judge-model gemini-3.8-flash --judge-prompt src/prompts/judge_acceptable.md
python -m src.eval judge-calibrate --run-id jc2-a-1 --judge-model gemini-3.6-flash --judge-prompt src/prompts/judge.md \
    --sample reports/human_validation_2/sample.json                       # and jc2-b-*, jc2-c-*; runs -1, -2, -3 of each
python -m src.eval judge-calibration-report --name judge_calibration_1 --runs jc1-a-1,...,jc1-c-3
python -m src.eval judge-calibration-report --name judge_calibration_2 --runs jc2-a-1,...,jc2-c-3 \
    --sample reports/human_validation_2/sample.json --author-answers reports/human_validation_2/answers.csv --annotator-answers none
```
- **Selection (declared before the round):** the candidate with the highest κ against the author on the second sample; ties go to
  the cheaper one, then to the current judge. The selected judge also judges `v2-16..18` (into
  `reports/eval_runs/judge_<candidate>/`) when it is not the current one; the matrix keeps comparing the current judge.

### 3.6 15C — Pre-round fixes (from the 15B review) and the reviewer's pre-round files

Checked by `scripts/verify_phase15c.py`; prompt `docs/phase-prompts/15C.md`. Reviewer files in 15C: this SPEC, the prompt,
the verifier, `data/eval/retrieval_labeled2.jsonl`, `src/prompts/judge_acceptable.md`. The 15B prompt and verifier are retired;
the 15C verifier re-runs the 15B verifier from `dd9e8d3` and lists as superseded only its diff, scope, retirement, test-growth
and STATUS checks (A1–A5, S1), which 15C checks again against `dd9e8d3`.

**Credentials re-checked after issue** (`src/core/auth.py`, `src/core/refresh_tokens.py`, `src/main.py`)
- `credential_problem(principal) -> str | None` in `src/core/auth.py`: looks up the principal's `key_id` in the current
  principal table (`get_principal_table()`); returns `"key_revoked"` when the key is no longer configured or its `user_id` or
  `role` differ from the principal's, `"key_expired"` when the key's last valid day has passed, `None` otherwise. A malformed
  table raises `ValueError` (callers answer 503 as today).
- Bearer: `authenticate` calls it after `decode_access_token`; a problem gives 401 with `WWW-Authenticate: Bearer` and the
  reason in the detail (`Invalid or expired token (key_revoked).`). A removed or expired key stops working at once, not when
  the access token expires.
- Refresh: `RefreshTokenRepository.rotate(token, now=None, key_check=None)`; when the stored token is otherwise valid and
  `key_check(principal)` returns a reason, the whole family is revoked in the same transaction, the audit event
  `auth.refresh_revoked` is written with `details={"status": <reason>}`, and `TokenError(<reason>)` is raised. `/auth/refresh`
  passes `key_check=credential_problem` and answers 401 with the reason. Restoring the key does not revive the family.

**Corpus index**
- `chunk_id` = the first 12 hex characters of SHA-256 of the page URL (UTF-8), `-`, the three-digit chunk index. Unique per
  URL (today two different URLs with the same text collide); deterministic.
- `build_chunks(..., boilerplate_section_exempt: bool = False)`: when true, a normalized line present in at least
  `boilerplate_min_pages` pages is not boilerplate if all those pages have the same parent directory (host plus the URL path
  without its last segment) and that directory is not the root. Keeps the steps that the help-center error pages of one
  section share (e.g. `/get-ajuda-erros-maquininha/`), still removes site-wide menus and footers. Default false (existing
  behaviour); the index passes true.
- `src/rag/index.py`: `INDEX_EXCLUDED_URLS` (a dict URL → reason) with exactly the two corporate PDFs that are not merchant
  support content: `Codigo_de_Conduta_Getnet_2026.pdf` (code of conduct) and `Regulamento-do-Canal-Aberto-2026.pdf`
  (whistleblowing channel rules), both under `https://site.getnet.com.br/wp-content/uploads/2026/10/`. Their records stay in
  `data/corpus/pages.jsonl`. `main()` indexes the `ok` records not in the list, passes `boilerplate_section_exempt=True` in
  the chunking configuration (recorded in `index_meta.json`) and records `excluded_urls` (sorted) in `index_meta.json`
  (`build_index(..., excluded_urls=None)`); `corpus_sha256` is computed over the indexed records.
- Invariants (reviewer-simulated at `dd9e8d3`, checked by the verifier): the chunks of the 33 original pages are, as
  (URL, text) pairs, exactly those of the committed `data/index/chunks.jsonl` (103); every answerable query of both retrieval
  sets has a chunk of a gold URL containing a gold snippet; chunk ids are unique. `data/index/` is not rebuilt in 15C (the
  author rebuilds it with the embedding key before the round).

### 3.7 15D — Publication and the matrix check

Checked by `scripts/verify_phase15d.py` (written after the round): the README with the round, criterion by criterion, the
ablation and its decision, the calibration, the new holdout and what is no longer clean; `docs/STATUS.md`; flag defaults set by
the ablation rule (only those); the matrix recomputed from the records with every drop declared or failing; the README states
that new labels from someone outside the project are pending.

### Acceptance (Phase 15)

- AC15.1 The matrix (§R) is in this SPEC before 15A code and is recomputed by the 15D verifier.
- AC15.2 Ablation: each run records its layers; the ablation report applies the rule of §3.4; the shipped default is a measured
  configuration.
- AC15.3 Every plan step assigned to a specialist is executed or corrected once; screen and app codes never reach the decline
  catalogue tool; earlier assistant answers are never evidence for the verifier (scripted tests and `verify_phase15a.py`).
- AC15.4 Short-lived tokens with key rotation and refresh rotation; merchant notified across replicas; alerts with runbook and
  rule tests; corpus with help-center pages and official PDFs under robots.txt (`verify_phase15b.py`, `compose-2`).
- AC15.5 One round, pre-registered above, published as it came out, with the criterion stated before it.
