# SPEC — Getnet Multi-Agent Support System (v3)

Owner: Burbanos · Planner/reviewer: Claude (external) · Implementer: Antigravity (Gemini)
Baseline: commit `4ddb820` (2026-11-06). Rubric: "Régua V4" (feedback score 4.2/10).

This document is the contract for every phase. A phase is **done** only when every
acceptance criterion is shown with real command output pasted into `docs/STATUS.md`.
"Should work" is not evidence.

---

## 0. Ground rules (apply to every phase)

1. **No fake signals.** No hardcoded confidence, token counts, costs, answers, or
   "passing" metrics. If a value is not measured, the field is `null` and the README says so.
2. **No regex/keyword routing.** Routing and tool selection are decided by the LLM via
   function calling. Regex is allowed only in the guardrail and PII layers.
3. **No hardcoded answers.** Every user-facing sentence comes from (a) the LLM grounded on
   tool/retrieval output, or (b) a fixed system message that is clearly a system message
   (refusal, "LLM unavailable", abstention).
4. **Tests never hit the network or a real LLM.** Unit/integration tests use a scripted fake
   chat model and mocked web search. Real-model runs live in `scripts/run_eval.py` and
   produce a committed report.
5. **Every README claim maps to code or a committed report.** Phase 8 adds a claims table.
6. **`docs/STATUS.md` is regenerated at the end of each phase** with: phase id, commit hash,
   the exact commands run and their raw output (pytest summary, ruff, eval report path).
7. One phase per PR/commit series; do not start phase N+1 inside phase N.
8. **Language policy:** code, identifiers, docstrings, commit messages and this SPEC in English.
   `README.md` and `docs/STATUS.md` in Brazilian Portuguese (pt-BR). Customer-facing answers
   in the language of the user's message (PT or EN).

---

## 1. Target architecture

```text
POST /chat  (X-API-Key → principal{user_id, role})
   │  user_id comes from the API key, never from the body or the model
   ▼
[guardrail]  regex injection + PII masking  ── blocked ──▶ END (refusal, logged)
   ▼
[supervisor]  LLM with bound tools (function calling)
   │   tools = specialists:
   │     ask_knowledge_agent(question)        → Knowledge Agent (RAG + web)
   │     ask_support_agent(request)           → Customer Support Agent (account tools)
   │     escalate_to_human(reason, priority)  → Escalation (persisted ticket)
   │   loop: supervisor → tool → supervisor (max N steps, then forced escalation)
   ▼
[final answer] grounded; cites sources; or abstains; or escalates
   │
   └─ state checkpointed per (user_id, session_id) in SQLite (SqliteSaver)

Knowledge Agent (LLM + tools): search_knowledge_base(query) → chunks w/ score, url, fetched_at
                               search_web(query)            → snippets w/ url
                               abstains when best score < calibrated threshold
Support Agent   (LLM + tools): get_settlement_status, get_declined_transactions,
                               diagnose_terminal  (user_id injected from auth context)
Escalation: ticket row + transcript snapshot; graph pauses via interrupt();
            operator replies via PATCH /tickets/{id}; next user turn resumes with the reply.
```

Key decisions:
- **LLM provider:** Gemini via `langchain-google-genai` (`ChatGoogleGenerativeAI.bind_tools`)
  behind a small `get_chat_model()` factory. Tests inject `GenericFakeChatModel`-style
  scripted models. No regex fallback engine: without an API key `/chat` returns HTTP 503
  with an explicit message. (Trade-off: evaluators without a key cannot chat; they can run
  the full test suite and read the committed eval report. This is honest; a rules fallback
  would re-create the regex router the feedback penalized.)
- **Tool args:** `user_id` is never a model-visible parameter. Tools read it from the run
  config (`RunnableConfig["configurable"]["user_id"]`).
- **Knowledge corpus:** real pages only, fetched by `scripts/ingest.py` from an allowlist,
  honoring robots.txt, stored as snapshots with `url`, `fetched_at`, `sha256`, raw text.
  Note: `getnet.net` has `/en` and `/pt` (Portugal) locales only; Brazil-specific products
  (Pix, crediário, antecipação, Get Clássica) must come from other official sources
  (e.g. Santander `/getnet` pages, official Getnet product manuals) — only if robots allows.
  `getnet.com.br/robots.txt` blocked our fetcher; respect it. When a scenario is not covered
  by the corpus, the correct behavior is abstention, not an invented article.
- **Embeddings:** multilingual model (PT/EN). Default Chroma English MiniLM is not acceptable.
- **Memory:** LangGraph `SqliteSaver`, thread id = `f"{user_id}:{session_id}"`, so sessions
  are isolated per user and survive restarts.

---

## 2. Reuse vs. rewrite

| Area | Decision | Reason |
|---|---|---|
| FastAPI app shell, Docker, `/health` | Reuse, adjust | Works; needs lockfile + auth |
| `mock_db.py`, `balance_tools.py`, `terminal_tools.py` | Reuse | Business mocks are fine; interface changes (no `user_id` arg exposed) |
| `pii.py`, `guardrails.py` | Reuse | Adequate for regex layer |
| `web_search.py` | Reuse | Honest failure already |
| `tickets_db.py` | Reuse core, extend | Add transcript, status lifecycle, owner filter, operator reply; remove silent `/tmp` fallback |
| `core/llm.py` (regex engine + hardcoded answers) | **Delete** | It is the regex router renamed |
| `core/graph.py` | **Rewrite** | Wire real LLM, specialists, checkpointer, interrupt |
| `agents/router.py`, `support.py`, `escalation.py`, `KnowledgeAgent` | **Delete** | Dead code; call a non-existent `generate_text` |
| `data/getnet_kb.json` (15 hand-written docs, guessed URLs) | **Delete** | Same issue as v1, just larger |
| `tests/test_eval_judge.py` | **Delete/replace** | Scores floored at 0.85: cannot fail |
| `demo.html` | Reuse later (phase 8) | Must stop displaying fake tokens/cost/confidence |
| README | **Rewrite** (phase 8) | Many unsupported claims |

---

## 3. Phases

### Phase 1 — Honest baseline and test hygiene
**Goal:** remove every fake signal and dead code path, isolate tests, fix deps and CI, so later
phases build on a truthful base. No new features.
**Files:** `src/core/llm.py`, `src/core/graph.py`, `src/core/state.py`, `src/main.py`,
`src/agents/*`, `tests/*`, `requirements*.txt`, `requirements.lock`, `.gitignore`,
`data/tickets.db`, `.github/workflows/ci.yml`, `pyproject.toml` (ruff/pytest config),
`Dockerfile`, `README.md` (corrections only), `docs/SPEC.md`, `docs/STATUS.md`.
**Acceptance:**
- AC1.1 `src/agents/router.py`, `support.py`, `escalation.py` and the `KnowledgeAgent` class are
  gone; `grep -rn "generate_text\|RouterAgent\|CustomerSupportAgent\|HumanEscalationAgent" src tests` → empty.
- AC1.2 No hardcoded answer text in the decision engine: `grep -n "touch\|android\|bobina\|3.367,20\|saldo insuficiente no banco" src/core/llm.py` → empty.
- AC1.3 The rules engine is explicitly labeled: response metadata has `"decision_engine": "rules_fallback"`; the unused Gemini client init is removed.
- AC1.4 Tokens/cost are `null` in API responses (no estimation formula in code: `grep -n "// 4\|0.000000075" src` → empty). `confidence` field removed from the response model.
- AC1.5 `tools_used` contains only real tool names (no alias injection).
- AC1.6 `/agents` reflects reality (no "Gemini 2.0 Flash", no "< 0.35").
- AC1.7 `data/tickets.db` untracked and gitignored; tests use `TICKETS_DB_PATH` under `tmp_path`; running the suite twice leaves `git status` clean.
- AC1.8 No test performs network I/O: web search is mocked; any network test is marked `@pytest.mark.network` and excluded by default (`addopts = -m "not network"`).
- AC1.9 `tests/test_eval_judge.py` fake judge removed; no function returns a floor score.
- AC1.10 `requirements.txt` = runtime only (no pytest), declares `langchain-core`; `requirements-dev.txt` adds pytest, ruff; `requirements.lock` regenerated from runtime deps; Dockerfile installs from the lock.
- AC1.11 CI: Python 3.11, installs dev deps, runs `ruff check .` (default rule set) and `pytest`; a second job runs `docker build` and a smoke test (`docker run` + HTTP GET `/health` returns 200). Lockfile generated on Linux (Codespaces), never on Windows.
- AC1.13 `python scripts/verify_phase1.py` prints `SUMMARY: N/N passed`. The script is provided by the reviewer and must not be edited by the implementer.
- AC1.12 README: false claims removed (56 tests badge, 100% routing badge, "LLM-as-a-Judge", CI linting, Gemini tool calling, "abém-se", "documentação oficial"). A short "Current limitations" section states that routing is rule-based until Phase 2.

### Phase 2 — LLM supervisor with function calling
**Goal:** replace the rules engine with a real LLM supervisor that chooses specialists/tools.
**Split:** 2A = model factory, scripted fake, single supervisor with `bind_tools` over the six
tools, `user_id` injection, PII fix, 503 handling (checked by `scripts/verify_phase2a.py`).
2B = LLM robustness (checked by `scripts/verify_phase2b.py`): default model `gemini-3.8-flash`
(`gemini-2.5-flash` is retired for new keys); explicit `LLM_TIMEOUT_S` / `LLM_MAX_RETRIES`;
final text read with `AIMessage.text` (content may be a list of blocks); configuration errors
(model not found, auth, permission, invalid request) → `LLMConfigurationError` → 503 "misconfigured",
transient errors → 503 "unavailable"; 500 never echoes exception text; one `trace_id` per request,
returned in the `X-Trace-Id` header on every `/chat` response; `MAX_SUPERVISOR_STEPS` guard that
answers pending tool calls and forces a persisted escalation (AC2.4).
2C = provider layer and safety fixes (checked by `scripts/verify_phase2c.py`): `LLM_PROVIDER`
(`google_genai` installed; `openai`/`anthropic` lazily imported, missing package →
`LLMConfigurationError`), `LLM_MODEL` default `gemini-3.5-flash` and `LLM_FALLBACK_MODEL` default
`gemini-3.5-flash-lite` (measured on 2026-11-06: `gemini-3.8-flash` returned 504 and `gemini-3.7-flash`
429 on the free tier, while 3.5-flash answered in ~3 s and chose the correct tool). The fallback is
tried only on non-configuration errors; the model that answered is reported as `llm_model`.
Bank account masked in tool output; forced escalation never claims a ticket that was not created.
Phase 2B checks `S1.default_model_*` and `R2.model_name` are superseded by this decision.
2D = Knowledge and Support specialists as sub-agents exposed to the supervisor as tools,
real token usage, tool outputs without invented defaults (AC2.8).
Additional 2A criteria:
- AC2.9 The guardrail replaces the incoming HumanMessage (same message id) instead of appending a masked copy; raw PII never reaches the model and is not stored in the checkpointer (test).
- AC2.10 `langchain-google-genai` declared and locked; the CI test job installs `-r requirements.lock -r requirements-dev.txt` (requirements-dev stays on ranges because the Linux lock pins `uvloop`, which does not install on Windows); Dockerfile fails if the lock is missing; CI actions on `checkout@v5` / `setup-python@v6`.
**Files:** `src/core/llm.py` (factory only), `src/core/graph.py`, `src/agents/{supervisor,knowledge,support}.py`, `src/tools/*`, `src/prompts/*.md`, `tests/fakes.py`, tests.
**Acceptance:**
- AC2.1 `grep -rn "re\.search\|re\.match" src/core src/agents/supervisor.py` → only guardrail/PII modules match.
- AC2.2 Supervisor uses `bind_tools`; specialists exposed as tools; prompts versioned in `src/prompts/`.
- AC2.3 `user_id` absent from every model-visible tool schema (unit test asserts on `tool.args_schema`).
- AC2.4 Graph has a max-steps guard; exceeding it escalates (test).
- AC2.5 Without API key `/chat` → 503 with explicit message (test). LLM exceptions → 503/controlled message, logged with trace_id (test).
- AC2.8 `RulesFallbackEngine` and all `_format_*` response templates are deleted; customer-facing text is generated by the LLM from tool JSON. Tool outputs never fill missing fields with invented defaults (e.g. serial numbers, carriers, deposit times, URLs); missing data is `null` (test).
- AC2.7 Supervisor prompt instructs answering in the user's language; tests check a PT question gets a PT answer and an EN question an EN answer (fake model asserts the instruction is in the system prompt; real-model check goes to the Phase 6 eval).
- AC2.6 Integration tests with scripted fake model cover: single tool, two tools in sequence (e.g. settlement + knowledge), direct answer, tool error handling.

### Phase 3 — Real RAG
**Goal:** corpus from real pages, multilingual embeddings, calibrated threshold, abstention, citations.
**Files:** `scripts/ingest.py`, `data/sources.yaml`, `data/corpus/*.jsonl`, `src/rag/{chunking,store,retriever}.py`, tests.
**Acceptance:**
- AC3.1 `sources.yaml` allowlist; ingest honors robots.txt (unit test with a disallowing robots fixture).
- AC3.2 Each chunk has `doc_url`, `fetched_at`, `sha256`, `chunk_id`, verbatim source text; no hand-written content.
- AC3.3 Index builds offline from committed snapshots (`python -m src.rag.store --rebuild`).
- AC3.4 Threshold chosen by a calibration script over labeled in/out-of-domain queries; value + curve committed in `reports/`.
- AC3.5 Retriever returns `abstain` below threshold; Knowledge Agent answers "not found in official sources" and never cites a chunk it did not receive (test).
- AC3.6 Retrieval metrics (hit@3, MRR) on ≥30 labeled queries committed in `reports/retrieval_*.json`.

### Phase 4 — Identity, auth and persistent memory
**Goal:** user identity from credentials; per-user isolated persistent sessions.
**Acceptance:**
- AC4.1 API keys configured via env (hashed), mapped to `{user_id, role}`; missing/invalid key → 401; no default key accepted when `APP_ENV=production`.
- AC4.2 Body `user_id` ignored or must equal principal (403 otherwise) — test.
- AC4.3 `SqliteSaver` checkpointer; thread id `user_id:session_id`; restart test proves memory survives; user B cannot read user A's session (test).
- AC4.4 `/tickets` filtered by owner; operator role sees all.
- AC4.5 Basic rate limit per key (test).

### Phase 5 — Human escalation with handoff and resume
**Acceptance:**
- AC5.1 Ticket stores reason, priority, transcript snapshot, status (`open|in_progress|answered|closed`).
- AC5.2 Graph uses `interrupt()`; operator `PATCH /tickets/{id}` with reply; next user turn returns the operator reply (test).
- AC5.3 Customer-facing escalation message contains no ETA/queue promise (test asserts on forbidden phrases).
- AC5.4 Auto-escalation triggers: explicit request, max steps, repeated abstention (tests).
- AC5.5 Persistence failure surfaces an error to the user; no silent `/tmp` fallback.

### Phase 6 — Evaluation
**Acceptance:**
- AC6.1 `data/eval/*.jsonl` ≥60 cases: routing, retrieval (gold chunk ids), abstention, multi-turn, safety, escalation, PT and EN.
- AC6.2 `scripts/run_eval.py` runs against the real model, outputs `reports/eval_<date>.json` + `.md` with per-case results, routing accuracy, abstention precision/recall, judge scores, latency, tokens, cost.
- AC6.3 LLM judge with rubric prompt; judge never sees the expected tool; disagreements listed.
- AC6.4 CI runs a deterministic offline subset (fake model) as regression; real-model report committed with model name and date.

### Phase 7 — Observability and cost
**Acceptance:**
- AC7.1 JSON logs per node with `trace_id`, `session_id`, `user_id` (hashed), node, tool, latency.
- AC7.2 Tokens and cost from provider `usage_metadata`; price table in config with source and date.
- AC7.3 `/metrics` (Prometheus format) with request count, latency histogram, tool calls, escalations, abstentions.

### Phase 8 — Production polish and README
**Acceptance:**
- AC8.1 `docker compose up` verified (output pasted), healthcheck green, non-root.
- AC8.2 README (pt-BR) covers build/run/test, architecture, workflow, RAG pipeline, tools, eval, limitations.
- AC8.3 README "Claims → evidence" table: every claim links to file/test/report.
- AC8.4 `demo.html` shows only real fields.
