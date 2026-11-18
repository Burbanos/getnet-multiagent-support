# SPEC — Getnet Multi-Agent Support System (v4)

Owner (the author): Burbanos · Planner/reviewer: Claude (external, Anthropic) · Implementer: Antigravity (Gemini)
Rubric: the evaluator's "Régua V4". Latest real feedback: v2, **8.0/10** on `d2de4ff`. Target: **≥ 9.5** (the latest
submission counts). Phases 1–12 (plan, prompts, verifiers, per-phase log) live in git history: `git show 431eb1f:docs/SPEC.md`,
and `docs/process.md` maps every sub-phase to its commit.

This document is the contract for every phase. A sub-phase is **done** when its verifier (`scripts/verify_phase<id>.py`) passes
on the reviewer's copy, CI is green on the sub-phase commit, and `docs/STATUS.md` shows the real command output.

---

## 0. Ground rules (every phase)

1. **No fake signals.** No hardcoded confidence, token counts, costs, answers or "passing" metrics. Unmeasured → `null`.
2. **No regex/keyword routing.** Routing and tool selection are decided by the LLM via function calling. Regex only in the
   guardrail and PII layers. A deterministic gate over an LLM's structured output (e.g. no ticket when the planner found no
   request for one) is not routing.
3. **No hardcoded answers.** Every user-facing sentence comes from the LLM grounded on tool output, or from a fixed system
   message that is clearly one (refusal, unavailable, abstention, pending ticket).
4. **Tests never hit the network or a real LLM.** Scripted chat models, mocked HTTP, `fakeredis`. Tests that need Postgres and
   Redis carry the `integration` marker, are deselected by default and run in CI against service containers.
5. **Every README/STATUS claim has evidence in the repository** (file, test, committed report or record). The evaluator reads the
   repository without running it and cannot see GitHub Actions: claims about multi-replica behaviour and tracing need a committed
   output (13D, `reports/integration/`).
6. **Records are immutable.** Committed runs, labels and reports are never edited or re-generated with different content; new
   runs get new ids.
7. **Verifiers run on Python 3.11** (CI and image version); no 3.12+ syntax; float sums that end in a rounded value use `math.fsum`.
8. **Language:** code, identifiers, commits and this SPEC in English; `README.md`, `docs/STATUS.md` and phase prompts in pt-BR;
   answers to the merchant in the language of the merchant's message.
9. **Process volume is a cost.** From Phase 13 the repository keeps only the current phase's prompt and verifier,
   `docs/process.md` and a short `docs/STATUS.md` (≤ 150 lines). The author is "o autor", never "candidato"; the reviewer is never
   called independent.
10. **Product model fixed:** `gemini-3.5-flash-lite` (fallback `gemini-3.1-flash-lite`); judge `gemini-3.6-flash`.

**Reviewer files** (written by the reviewer, committed unchanged by Antigravity): `docs/SPEC.md`, `docs/process.md`,
`docs/phase-prompts/*.md`, `scripts/verify_*.py`, `src/prompts/*.md`, `data/eval/*.jsonl`.

---

## Current state (2026-11-18)

**13A done** (`66add08` + fix `3a175bd`, CI green on `test`, `integration` and `docker`): checkpoints and tickets in Postgres
(SQLAlchemy Core; SQLite only for dev and tests), schema setup serialised across replicas by a Postgres advisory lock, Redis
sliding-window rate limit shared by replicas (per-process fallback, flagged), OpenTelemetry spans per request, node, LLM call
and tool (attribute allowlist), Compose with two replicas and an `observability` profile (Jaeger, Prometheus, Grafana). The
reviewer ran `verify_phase13a.py` with real Postgres 16 and Redis 7: 40/40. The verifiers and prompts of phases 1–12 left the
tree; 13A's leave in 13B.

### Before Phase 13 (HEAD `431eb1f`, phase 12F, CI green)

Reviewer rerun of `scripts/verify_phase12f.py` on Python 3.11.18 before retiring the verifier chain: **75/75** (it re-ran the 58
earlier verifiers with their superseded lists). That is the last run of the old chain; see "Retired verifiers" below.

Measured with the product model (raw records in `reports/eval_runs/`, reports in `reports/`):
- v2 set (78 cases × 3): pass 91.9% (11G) → 94.4% (12D) → **95.3%** (12E, `v2-7..9`); official scenarios 96.7% → 80.0% →
  **83.3%**; routing 95.4% → 98.5% → 100%; judge abstention precision 100%, recall 77.8%; p50 5.5 s, p95 11.6 s; US$ 0.288/run.
- Retrieval (48 labeled queries, `rerank-1..3`): hybrid BM25 + dense + LLM reranker; hit@1 0.900 → 1.000; uncovered abstention
  0.000 → 1.000.
- Routing holdouts: holdout 1 routing 24/24; holdout 2 30/36 (screen errors used the decline catalogue in 5/9).
- Human validation (author, blind, 30 cases of `v2-1`): route κ 0.87 vs labels; no answer passed by the checks was rejected.
  An outside annotator gets the same 30 cases (packet sent 2026-11-18, outside the repository) for author × annotator agreement.

Open items (Phase 13 targets, by weight in the rubric):
1. `u03` ("erro 05" on a network screen answered with the decline catalogue's 05) wrong in all six Phase 12 runs.
2. English questions answered in Portuguese (6/7/8 per group; `off08` 6/6); official scenarios 83.3%.
3. Tickets opened without the merchant asking (3/3/4 per group; `off04`, `o04`).
4. State in local SQLite and an in-process rate limit (the feedback names both for 9.0).
5. No write action in the support domain.
6. No distributed tracing, no dashboard; metrics per process.
7. Labels and judge validated only by the author.
8. No explicit planning or verification step in the supervisor ("planner adaptativo"); no operator console.
9. Process volume (discounted in Engineering Judgment); three empty official pages in the corpus (home, Link de Pagamento,
   Pagamentos pelo WhatsApp).

---

## 1. Target architecture (after Phase 13)

```text
POST /chat (X-API-Key → principal; user_id from the credential) ── W3C traceparent in/out, span per node, LLM call and tool
   ▼
rate limit (Redis sliding window shared by all replicas; per-process fallback, flagged) → PII masking → guardrail
(patterns → LLM classifier) → handoff_gate (pending ticket / pending action)
   ▼
planner (13B: structured plan — reply language, sub-tasks, out-of-scope)
   ▼
supervisor (function calling) ⇄ ask_knowledge_agent | ask_support_agent | escalate_to_human | confirm_pending_action (13C)
   ▼
verifier (13B: per sub-task answered / evidence does not apply / unsupported; one replan) → answer_check (URLs, ticket ids,
time promises) → language enforcement (13B) → answer
   │
   └─ checkpoints (PostgresSaver), tickets and audit events (Postgres via SQLAlchemy Core); SQLite only for dev and tests

Knowledge Agent: hybrid KB search (BM25 + dense + reranker, abstains), weather (Open-Meteo), FX (PTAX), web search (news only).
Support Agent: settlement, declined transactions (catalogue applies only to declined sales, 13B), terminal diagnosis,
               request_terminal_replacement (13C: proposal → merchant confirmation → execution, idempotent, audited).
Operator: webhook notification, /operator console (13C), PATCH /tickets/{id} resumes the thread.
Deployment: compose with Postgres, Redis, two app replicas; profile `observability` adds Jaeger, Prometheus and Grafana.
```

---

## 2. Phase 13 — close every open item of feedback v2

Four sub-phases. One round of real-model runs, at the end (13D), plus one small pre-registered smoke at the end of 13B (decided
by the reviewer, delegated by the author: without it a regression of the planner would only show up in 13D). Each sub-phase has
one verifier; `docs/STATUS.md` is rewritten (not appended) at the end of each.

### Retired verifiers (decided 2026-11-18)

The verifiers and prompts of phases 1–12 leave the tree in 13A (decision (c) of the Phase 13 plan, moved from 13D to 13A because
13A rewrites storage, Compose and CI, which dozens of earlier checks pin as text). Their guarantees continue as:
- **the test suite:** no test function present at `431eb1f` may be removed or renamed, and existing test files only gain lines
  (exception: `tests/conftest.py`); the offline suite must pass with at least as many tests;
- **frozen records:** `reports/`, `data/eval/`, `data/corpus/`, `data/index/`, `src/prompts/`, `README.md`,
  `docs/DECISIONS.md` and `docs/history.md` are byte-identical to `431eb1f` until a sub-phase explicitly changes them;
- **cross-cutting invariants** re-checked by every Phase 13 verifier: no raw card/CPF in any persisted state, no conversation
  text in logs or span attributes, `user_id` only from the credential, offline eval 6/6, ruff clean, no network in tests;
- **CI** (lint, tests, integration against Postgres/Redis, compose build with two replicas).
The README still cites the retired verifiers until 13D rewrites the claims table to point at tests and reports.

### 13A — Distributed state, shared rate limit, tracing, dashboard (items 4, 6)

Checked by `scripts/verify_phase13a.py`. No change to graph behaviour, prompts, README or records.
- **Dependencies (one lock regeneration for the whole phase):** `langgraph-checkpoint-postgres`, `psycopg[binary]`,
  `psycopg-pool`, `sqlalchemy`, `redis`, `opentelemetry-api/-sdk/-exporter-otlp-proto-http`, `langdetect` (used in 13B);
  dev: `fakeredis`. Lock regenerated by the author in Codespaces; `langgraph==1.2.20` and `langgraph-checkpoint==4.3.1` unchanged.
- **Settings:** `DATABASE_URL` (empty → SQLite at `TICKETS_DB_PATH`/`CHECKPOINT_DB_PATH`), `DB_POOL_SIZE=5`, `REDIS_URL`
  (empty → in-process limiter), `RATE_LIMIT_REDIS_PREFIX=getnet:rl:`, `TRACING_EXPORTER=none|console|otlp`,
  `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME=getnet-multiagent`, `REPLICA_NAME`. `APP_ENV=production` without a
  `postgresql://` `DATABASE_URL` or without `REDIS_URL` fails at startup.
- **Storage:** `src/core/db.py` (SQLAlchemy Core engine for a path or a Postgres URL, `tickets` table with the current columns,
  `ensure_schema` = create + add missing columns, `ping`); `TicketsRepository` keeps its public API and return shapes on both
  backends; `append_customer_message` locks the row (`FOR UPDATE`) inside one transaction; conditional updates stay conditional.
  `build_checkpointer()` → `PostgresSaver` over a `psycopg_pool.ConnectionPool` (`setup()` at startup) or `SqliteSaver`.
- **Rate limit:** `src/core/rate_limit.py` with the in-process `RateLimiter` (moved from `auth.py`, re-exported) and
  `RedisRateLimiter` (sorted-set sliding window in a MULTI/EXEC pipeline; a rejected hit is removed, so it does not count; wall
  clock; on Redis error it falls back to a per-process limiter for 5 s, counts `getnet_rate_limit_backend_errors_total` and
  reports `redis_degraded`).
- **Tracing:** `src/core/tracing.py` with its own `TracerProvider` (always installed, exporter by setting), attribute allowlist,
  exception status without the message, W3C `traceparent` extraction and injection. Spans: `chat.request` (root, continues an
  incoming `traceparent`), `ticket.update`, `graph.node.<name>`, `llm.call` (caller, model, tokens, fallback), `tool.call`
  (name, status), `notifier.webhook`. Log records carry `otel_trace_id`. `X-Trace-Id` keeps its `trc-` format.
- **Health:** `/health` adds `state_backend`, `rate_limit_backend`, `tracing_exporter`, `replica`; returns 503 when the database
  ping fails. `/` and `/agents` name the real checkpointer.
- **Compose:** `postgres`, `redis`, `app-a` (port 8000), `app-b` (port 8001) sharing one app definition; `POSTGRES_PASSWORD`
  required; profile `observability` with Jaeger, Prometheus (scrapes both replicas) and Grafana (provisioned datasource and one
  dashboard over the existing metrics). Fixed image tags, never `latest`.
- **CI:** new `integration` job (Postgres and Redis service containers, `pytest -m integration`); the `docker` job builds with
  Compose, checks both replicas' health and production defaults, a ticket created on one replica read and updated on the other,
  the rate limit shared across replicas (429 with `Retry-After`), survival of a replica restart, and that the image alone (no
  `DATABASE_URL`) refuses to start.
- **Process volume:** the old verifiers, phase prompts and `docs/status-history.md` leave the tree.

### 13B — Planner, pre-send verification, language, escalation only on request, decline-catalogue applicability (items 1, 2, 3, 8a)

Checked by `scripts/verify_phase13b.py`; prompt `docs/phase-prompts/13B.md`. Decisions taken while writing it (they replace
the provisional text of this section):
- **Holdout 3** (`data/eval/cases_holdout3.jsonl`, 31 cases, reviewer, committed with 13B before any 13B code runs on it):
  English questions across categories and one language switch, off-topic and knowledge-gap requests where no ticket may be
  opened, error codes shown outside a declined sale (05, 51, 57 on settings, update, start-up screens and in the app) with the
  catalogue meaning as forbidden facts, the contrast cases where the catalogue applies, and merchant-requested escalations
  (explicit, formal complaint, accepted offer) in both languages. Not independent (same reviewer, written knowing the
  failures). The 13C confirmation flows get their own pre-registered cases before 13C code.
- **Planner node** before the supervisor, product model, forced structured output `TurnPlan`: `reply_language`,
  `scope` (`support | out_of_scope`), `escalation_request` (`none | asked_for_human | formal_complaint | accepted_offer`),
  up to 4 steps (`goal`, `delegate`). Out of scope → fixed bilingual system message, no tools. The plan is appended to the
  supervisor's system prompt (never to the persisted messages); routing stays function calling.
- **Verifier node** after the supervisor's draft, product model, forced structured output: one verdict per step
  (`answered | evidence_does_not_apply | unsupported_claim | not_answered`). One replan with the critique (the failed draft
  is removed from history); a second failure → fixed abstention with an offer of a human agent. Invalid output or provider
  error → the draft goes on (fail-open, recorded).
- **Escalation gate** instead of the quote idea: a quote can be any substring of the question, so it does not separate
  "asked" from "not asked". The planner's `escalation_request` is an LLM judgement made before the supervisor sees any
  evidence; with a plan and `none`, `escalate_to_human` returns `needs_merchant_request` and opens nothing. Without a plan the
  gate is open (refusing a requested human is worse than one extra ticket). The step-limit escalation and the automatic
  escalation after two consecutive abstentions stay as they are: both are documented system policies, and neither caused the
  unrequested tickets (single-turn `off04`/`o04` tickets were opened by the supervisor).
- **Decline catalogue applicability:** `diagnose_declined_transaction` gets a required `code_context`
  (`declined_sale | terminal_screen | app | unknown`); outside a declined sale it returns `not_applicable`.
- **Language enforcement** after `answer_check`, only on model-written answers: `langdetect` (seeded; not the eval's lexicon
  detector); a mismatch with the plan's language triggers one rewrite, accepted only if every URL, ticket id and number of 2+
  digits survives and the new text is in the target language.
- **Injection, not flags, in tests:** `OrchestrationGraph(..., planner_model, verifier_model, rewrite_model)`; production
  (`chat_model is None`) builds all three with the product model; tests that pass only `chat_model` keep today's behaviour.
- **Smoke** after the 13B commit: holdout 3 once with the product model (author), reported as a smoke, not as a result.

### 13C — Write action with confirmation and audit, operator console, corpus completion (items 5, 8b, 9) — provisional

- `request_terminal_replacement(serial_number, reason)`: proposal stored as `pending_action` in the thread (action id, args,
  expiry); executed only by `confirm_pending_action(action_id)` in a later merchant turn; one open request per terminal
  (idempotency); terminal of another merchant or unknown → `not_found`; no deadline promised.
- `audit_events` table (actor hash, role, action, masked args, outcome, `otel_trace_id`, time) for proposals, confirmations,
  cancellations, executions, ticket updates; `GET /audit` for operators.
- `/operator` console (operator key): ticket queue with filters, masked transcript, reply (PATCH → resume), replacement
  requests and audit.
- Corpus: re-collect the three `no_content` pages if robots.txt allows; re-index; labels unchanged (if a new page covers a case
  labelled "uncovered", the label stays and the README says so).

### 13D — Close: one round of real runs, annotator, integration evidence, README (items 7, 9)

Runs `v2-10..12` (judge), holdouts 1–3 and the 13C cases × 3, `rerank-4..6` if the corpus changed; the annotator's answers and agreement
(author × annotator, annotator × labels, annotator × judge); `reports/integration/` from a Codespaces Compose run (two replicas,
a real conversation continued across replicas, shared 429, PII scan of Postgres, one exported trace); README rewritten shorter,
claims table pointing to tests and reports; `docs/history.md` decision.

### Acceptance (Phase 13)

- AC13.1 State (checkpoints, tickets, audit) and the rate limit are shared by two replicas; shown by CI and by a committed
  Compose run.
- AC13.2 Every request has a trace with spans per node, LLM call and tool, without conversation text or raw identifiers.
- AC13.3 `u03`-like screen errors never receive the decline catalogue's meaning; English questions get English answers;
  no ticket is opened without a merchant request, complaint, blocking problem or accepted offer — each measured on v2 and
  holdout 3, with every regression reported.
- AC13.4 A write action exists with confirmation, idempotency and audit.
- AC13.5 Labels and judge are compared with an annotator outside the project, reported as it came out.
- AC13.6 Every README claim has evidence in the repository; product model unchanged; `docs/DECISIONS.md` unchanged.
