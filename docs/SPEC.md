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

## Current state and next steps (handoff, 2026-11-07)

**Read this first in a new planning conversation.** Repository HEAD at handoff: `f467d56` (phase 3D) plus
this SPEC/prompt update for 4A. CI (lint, tests, docker build + /health smoke) runs on every push.

**Done (each verified independently by the reviewer with its `scripts/verify_*.py`):**
- Phase 1: honest baseline, test hygiene, CI, Linux lockfile.
- 2A LLM supervisor with function calling · 2B timeouts, error classes, step limit, `X-Trace-Id` · 2C
  provider-agnostic factory, fallback model (`gemini-3.5-flash` → `gemini-3.5-flash-lite`), account masking ·
  2D KnowledgeAgent and SupportAgent sub-agents · 2E real token usage, tools without invented values.
- 3A ingestion of 33 official URLs (30 `ok`: 10 getnet.net/en, 20 site.getnet.com.br; santander.com.br
  dropped, 403 on robots.txt) · 3B chunking, committed `gemini-embedding-2` index, retriever · 3C retriever
  wired into `search_knowledge_base`, legacy KB and ChromaDB removed (index: 92 chunks, 28 pages) · 3D
  retrieval evaluation, `RAG_MIN_SCORE=0.61` (`reports/retrieval_calibration.*`).

**3D results (48 reviewer-labeled queries, reviewer recomputed every number):** answerable hit@1 0.900, hit@3
0.967 (PT 1.000, EN 0.889), MRR@10 0.933, answer_hit@3 0.900. At 0.61: all 30 answerable pass, all 8 off-topic
abstain, **0 of 10 uncovered abstain** (top-1 0.636–0.849). Margin to the best off-topic query is only 0.04
and the 8 negatives are easy (recipes, football); a payments question about another company would pass.
"Passing the threshold" is not "having the answer": the Get Mini battery query passes at 0.651 while the chunk
with "12 hours" ranks 16th. Generic chunks outrank specific ones (home news list over the countries chunk; the
estorno how-to chunk is top-1 for 5 uncovered queries).

**Real-model smoke test after 3C (5 questions, all facts checked against the corpus):** crediário "até 48x"
with the issuer caveat (literal on the official page; the old hand-written KB said 36x); Pix bank account →
honest "official sources do not detail it" (no such text in the corpus); Get Clássica vs Get Smart → rents
R$ 79,90 vs R$ 129,90 (literal); WhatsApp + payment link → yes, from the global online-payments page; cake
recipe → polite refusal without search. Observed problems: EN questions answered in PT; collection dates not
cited; global source not flagged (supervisor prompt fixed in this handoff commit, not yet re-measured);
flattened tables can misattribute numbers ("isenção acima de R$ 10 mil" came from a price-band selector);
latency 24–42 s per question.

**Working agreements (also in the project instructions):** the reviewer writes only `scripts/verify_*.py`,
`docs/SPEC.md`, `docs/phase-prompts/*.md` and `src/prompts/*.md` (from Phase 6 also the labeled sets
`data/eval/*.jsonl`, decided 2026-11-07, pending the matching change in the project instructions; until then
labeled data travels verbatim inside the phase prompt), between phases, after checking that the
local folder equals GitHub HEAD; the user types `Execute docs/phase-prompts/<phase>.md` in Antigravity, which
commits the reviewer files unchanged; the reviewer monitors GitHub and verifies independently. Each verifier
reruns earlier ones with `VERIFY_NESTED=1` (skips their suites) and lists superseded checks in `PRIOR`
(2A: R2.single_tool_flow, R3.user_id_injected, R3.bound_tools, R4.two_tools_sequence; 2B:
S1.default_model_config, S1.default_model_env_example, R2.model_name; 2D: R6.knowledge_flow; 3B: L1.settings,
which pinned the provisional `RAG_MIN_SCORE=0.60`; 4A: the checks that call `/chat` without a key, re-checked
with a key as C1–C4 in `verify_phase4a.py`). Anything that
needs the API key (index builds, smoke tests, real-model evals) is run by the user in a terminal with
`Read-Host -MaskInput`; Antigravity must stop and ask. Antigravity's sandbox hangs pytest/TestClient when run
in the background on Windows: run tests and verifiers in the foreground. Local Python is 3.13, CI and Docker
use 3.11; the lock is regenerated in Codespaces with the `python:3.11-slim` image.

**Current phase: 4A (identity from credentials, per-user isolation, tickets by owner, rate limit)**, prompt
`docs/phase-prompts/4A.md`, verifier `scripts/verify_phase4a.py` (details in Phase 4). Found while planning: the
checkpointer thread id was the bare `session_id` and `user_id` came from the request body, so anyone knowing
a session id could read that conversation. 4B (SQLite checkpointer, restart test) follows; it adds the
`langgraph-checkpoint-sqlite` dependency, so the user regenerates the lock in Codespaces.

**Backlog:**
- Phase 6 (from 3D): real-model abstention on the 10 `uncovered` queries through the Knowledge Agent as a
  headline metric; harder negatives (other acquirers, banks, generic payments); "answered with the answer"
  vs "passed the threshold"; language rule (EN question → EN answer) and collection-date citation; replace
  `data/eval_dataset.json` (ground truth from the old KB).
- RAG quality: chunk generality (title prefix per chunk or smaller chunks, measured with the 3D set);
  cadastro pop-up text ("Como deseja continuar?", in <4 pages) survives the boilerplate filter; WhatsApp
  payment link has only the global page as source.
- Phase 5 escalation handoff/resume; Phase 7 observability (per-node logs, latency per agent, hashed user id
  in logs, circuit breaker so the failing primary model is skipped for a while, cost).
- Phase 8: README claims table (3D wording "separação ideal" / "100% rejeitadas" holds only for the 8
  off-topic queries; "100% respondidas" means passing the threshold), `/agents` lists stale tools and
  "MemorySaver", `demo.html` review.

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
2D = specialist sub-agents (checked by `scripts/verify_phase2d.py`): the supervisor binds only
`ask_knowledge_agent(question)`, `ask_support_agent(request)` and `escalate_to_human(reason)`.
`KnowledgeAgent` (tools: `search_knowledge_base`, `search_web`) and `SupportAgent` (tools:
`get_settlement_status`, `diagnose_declined_transaction`, `diagnose_terminal`) are `SpecialistAgent`
instances, each with its own prompt (`src/prompts/*.md`, owned by the reviewer), its own tool set
(calls to tools outside it return an error), an isolated context (system prompt + the supervisor's
self-contained task only), the same primary/fallback models and failover as the supervisor, and a
`MAX_SPECIALIST_STEPS` limit (default 4) that returns status `step_limit`. A specialist returns to the
supervisor a JSON with `agent`, `status`, `answer`, `tools_used`, `sources`. `tools_used` keeps
listing leaf tools; `agents_used` lists agents in order. Supervisor prompt forbids vague time
promises ("em breve", "shortly"). Phase 2A checks that assumed the supervisor calls leaf tools
directly are superseded (listed in the verifier).
2E = real token usage and tools without invented values (checked by `scripts/verify_phase2e.py`):
`tokens` (`input_tokens`, `output_tokens`, `total_tokens`) summed from the provider's `usage_metadata`
of every model call in the turn (supervisor and specialists), plus `tokens_by_agent`; both `null` when
the provider reports nothing; counted per turn, not per session; `estimated_cost_usd` stays `null`
until Phase 7. `diagnose_declined_transaction` never invents a decline code (no decline and no code →
`queried_code`/`code_details` null) and never presents an unknown code as catalogued (`code_known`
false, `code_details` null). `diagnose_terminal` derives diagnosis and steps from the terminal's own
telemetry (model, operator, signal, Wi-Fi, SIM status) with no hardcoded model or carrier. The benign
"fixed sampling defaults" warning from lite models is filtered in `src/core/llm.py`.
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
**Goal:** corpus from real official pages, multilingual retrieval, calibrated threshold, abstention, citations.
**Source policy (decided 2026-11-06, revised in 3A.1):** `www.getnet.net/en` (market `global`) and
`site.getnet.com.br`, the official Getnet Brasil site that `www.getnet.com.br` redirects to (market `BR`;
its `/robots.txt` returns 404, which RFC 9309 treats as no restrictions). `www.santander.com.br` was dropped:
its CDN (Akamai) answers 403 "Access Denied" to the project user agent even on `/robots.txt`, and the
project never disguises its user agent. `www.getnet.net/pt` is excluded: it is the Portugal market (TPA,
euro tariffs) and would mislead Brazilian merchants. The ingested text is committed under `data/corpus/`
with source URL, fetch date and sha256 per page, plus an attribution notice (content belongs to its owners
and is not covered by the repository licence), so evaluators can check answers against literal page text
without network. Topics with no official coverage must be answered with abstention, never invented.
**Split:**
- 3A (checked by `scripts/verify_phase3a.py`): `data/sources.yaml` allowlist; `src/rag/ingest.py` with
  `USER_AGENT` (identifies the project and repo URL), `ALLOWED_DOMAINS` (`www.getnet.net`,
  `site.getnet.com.br`, `www.getnet.com.br`), `Ingestor(client, user_agent,
  min_delay_s).fetch(url, market)` and `.run(sources_path, out_dir)`; robots.txt per host (404/410 → allowed,
  5xx or network error → disallowed, cached per host); per-host rate limit; main-text extraction without
  nav/header/footer/scripts; statuses `ok | robots_disallowed | http_error | fetch_error | no_content |
  off_allowlist`; `data/corpus/pages.jsonl` (one record per source) and `manifest.json` (user agent, counts);
  at least 15 `ok` pages, 8 of them `BR`. Ingestion tooling deps (beautifulsoup4, pyyaml) live in
  `requirements-dev.txt`, not in the runtime lock.
- 3B (checked by `scripts/verify_phase3b.py`): library only, agents unchanged. `src/rag/chunking.py`
  `build_chunks(records, max_chars=900, boilerplate_min_pages=4)`: only `ok` pages; drops lines repeated in
  ≥4 pages (site footer/CTA) and lines without alphanumerics; chunks of verbatim source lines ≤900 chars with
  deterministic `chunk_id` and provenance (`doc_url`, `title`, `market`, `fetched_at`, `doc_sha256`).
  `src/rag/index.py`: `build_index(chunks, embedder, out_dir, embedding_model, dim, corpus_sha256)` writes
  `data/index/{chunks.jsonl, embeddings.npy (float32, L2-normalised), index_meta.json}`; `VectorIndex.load(dir,
  expected_model, expected_dim)` (mismatch → ValueError) and `.search(vector, k)` by cosine; CLI
  `python -m src.rag.index` builds the committed index (run by the user, who holds the API key).
  `src/rag/retriever.py`: `Retriever(index, embedder, min_score, top_k).search(query)` → `success` with
  documents scoring ≥ `min_score` (max `top_k`) or `abstain` with no documents. `get_embedder(task_type)` in
  `src/core/llm.py`. Embedding model `gemini-embedding-2` at 768 dims, task types RETRIEVAL_DOCUMENT/QUERY.
  Chosen on 2026-11-06 over `gemini-embedding-001` with 5 real pages and 4 queries: relevant top scores
  0.738–0.807 vs 0.461 for an out-of-domain query (margin 0.277 vs 0.215), and better PT/EN cross-lingual
  matching. `RAG_MIN_SCORE=0.60` and `RAG_TOP_K=4` are provisional until 3D.
- 3C (checked by `scripts/verify_phase3c.py`): `search_knowledge_base` calls
  `src.rag.retriever.get_knowledge_retriever()` (cached; loads the committed index with the expected model and
  dimension and a RETRIEVAL_QUERY embedder; `reset_knowledge_retriever()` for tests) and returns `success`
  (documents with url, title, fetched_at, market, chunk_id, score, text), `abstain`, or `unavailable` when the
  retriever cannot be built or the embedding call fails. Its description states no product facts (the old one
  claimed "36x"; the official page says up to 48x). `build_chunks(..., min_chars=0)`; the index CLI uses
  `RAG_MIN_CHUNK_CHARS=120`: pages with less retained text produce no chunk and a short tail chunk is merged
  into the previous one (title-only passages such as "Antecipação de Vendas" scored high and carried no
  answer). Removed: `data/getnet_kb.json`, `src/agents/knowledge.py` (ChromaDB retriever, stopwords, lexical
  fallback), `KB_DATA_PATH`, `CHROMA_PERSIST_DIR`, the chroma volume and the `chromadb` dependency (lock
  regenerated by the user after the phase). Knowledge Agent prompt (reviewer-owned) requires the passage to
  actually contain the answer, cites URL and collection date, and prefers BR over global passages. Phase 2D
  check `R6.knowledge_flow` is superseded (re-checked with a fake retriever as `K6`).
- 3D (checked by `scripts/verify_phase3d.py`): retrieval evaluation and threshold calibration.
  *Labeled set* `data/eval/retrieval_labeled.jsonl`, written by the reviewer from literal corpus text (the
  implementer copies it verbatim; the verifier holds an identical copy): 48 queries, fields `id`, `lang`
  (`pt|en`), `category`, `query`, `gold_urls`, `gold_snippets`. Categories: `answerable` (30: 21 PT, 9 EN, some
  EN questions about PT pages to test cross-lingual retrieval), `uncovered` (10: Getnet or competitor topics
  with no answer in the corpus, e.g. Pix key registration, support phone number, Stone fees) and `off_topic`
  (8). `answerable` needs non-empty `gold_urls` and `gold_snippets`; the others have both empty.
  Canonical hash: sha256 of the records serialized with `json.dumps(r, ensure_ascii=False, sort_keys=True)`
  joined by `"\n"` (immune to CRLF checkouts).
  *Module* `src/rag/calibration.py` (no regex; `normalize_text` = split/join whitespace + lower): `load_labeled`
  (ValueError on unknown category or language, duplicate id, answerable without gold), `dataset_sha256`,
  `threshold_grid` (0.30..0.95 step 0.01), `evaluate`, `abstention_curve`, `choose_threshold`, `run_embed`,
  `run_report`; CLI `python -m src.rag.calibration embed|report`. `embed` (run by the user, who holds the key)
  embeds each query with `get_embedder("RETRIEVAL_QUERY").embed_query`, the production path, and writes
  `data/eval/retrieval_query_embeddings.npy` (float32, raw) + `.json` (model, dim, task type, query ids,
  dataset hash, date). `report` is offline and refuses (ValueError) embeddings whose ids, dataset hash, model
  or dimension do not match.
  *Metrics.* Score = cosine between the L2-normalised query and the stored chunk vectors (float64 product,
  stable ordering). `gold_rank` = 1-based rank of the first chunk whose `doc_url` is in `gold_urls` within the
  top 10. Over `answerable`, overall and per language: hit@1, hit@3, hit@5, MRR@10 and answer_hit@3 (a top-3
  chunk from a gold URL that contains a gold snippet after normalisation: the passage carries the answer, not
  only the page). *Abstention* (answer iff top-1 score ≥ t, the Retriever's rule), per t: answer_rate
  (answerable), off_topic_abstain_rate, uncovered_abstain_rate, balanced_accuracy = mean of answer_rate and
  off_topic_abstain_rate, abstain precision/recall over answerable+off_topic. *Rule:* maximise balanced
  accuracy; ties → lower median of the tied thresholds. Calibration uses answerable vs off_topic only:
  `uncovered` queries are near-domain by construction and a global similarity threshold cannot reject them
  without dropping real answers; their abstention rate is reported, and rejecting them is the Knowledge
  Agent prompt's job ("the passage must contain the answer") and a Phase 6 metric. *Warnings* (reported, not
  enforced): `weak_separation` (balanced accuracy < 0.9), `uncovered_not_filtered` (uncovered abstention
  < 0.5), `low_answer_hit` (answer_hit@3 < 0.7), `threshold_at_grid_edge`.
  *Outputs:* `reports/retrieval_calibration.json` (+ `.md` generated by the same code), `RAG_MIN_SCORE` in
  `src/config.py` and `.env.example` set to the chosen value, README updated. The verifier recomputes every
  number from the committed embeddings and index with its own implementation and rejects implausible
  (non-model) query vectors.
  Known coverage gap: no official BR page with server-rendered text about payment links via WhatsApp
  (`/link-de-pagamento/`, `/pagamentos-pelo-whatsapp/` and alternatives are JavaScript-only or menu-only),
  so that scenario must abstain or use the global online-payments page.
**Acceptance (whole phase):**
- AC3.1 `sources.yaml` allowlist; ingest honors robots.txt (tests with simulated robots).
- AC3.2 Each chunk has `doc_url`, `fetched_at`, `sha256`, `chunk_id`, verbatim source text; no hand-written content.
- AC3.3 Index builds from committed snapshots.
- AC3.4 Threshold chosen by a calibration script over labeled in/out-of-domain queries; value + curve committed in `reports/`.
- AC3.5 Retriever returns `abstain` below threshold; Knowledge Agent answers "not found in official sources" and never cites a chunk it did not receive (test).
- AC3.6 Retrieval metrics (hit@3, MRR) on ≥30 labeled queries committed in `reports/retrieval_*.json`.

### Phase 4 — Identity, auth and persistent memory
**Goal:** user identity from credentials; per-user isolated persistent sessions.
**Split:**
- 4A (checked by `scripts/verify_phase4a.py`): `src/core/auth.py` with `Principal(user_id, role, key_id)`
  (frozen dataclass; `key_id` = first 12 hex chars of the key hash, the only key-derived value that may be
  logged), `hash_api_key` (sha256 hex of the UTF-8 key), `parse_api_keys(spec)` for `API_KEYS` =
  `sha256hex:user_id:role` entries separated by `;` (lowercase 64-hex hash, non-empty user id, role
  `customer|operator`, no duplicates, else ValueError), `get_principal_table()` (read at request time:
  `API_KEYS` when set; otherwise, only when `APP_ENV` is not `production`, the documented development keys
  `getnet-dev-key` → `cliente1988`/customer and `getnet-dev-operator` → `operador_dev`/operator; in
  production with no `API_KEYS` no key is accepted), `authenticate` (FastAPI dependency on `X-API-Key`,
  constant-time comparison, 401 without echoing the key), `RateLimiter(limit_per_minute, clock)` (sliding
  60 s window per `key_id`, `hit()` returns seconds to wait or None, 0 disables), `get_rate_limiter()` /
  `reset_rate_limiter()`; 429 with `Retry-After`. `/health` stays public and reports `auth_mode`
  (`configured | development_defaults | none`). `/chat`: user from the principal; body `user_id` optional and
  403 if it differs; `session_id` 1–64 chars, generated when absent; checkpointer thread id
  `f"{user_id}:{session_id}"`; `run_sync` rejects an empty user id; no `cliente1988` fallback in `main.py` or
  `graph.py`. `/tickets`: customers see only their own (403 when asking for another `user_id`), operators see
  all and may filter by `user_id`; `/tickets/{id}` of another owner → 404 for customers. CLI
  `python -m src.core.auth hash` reads the key with `getpass` and prints its hash. Settings `API_KEYS=""`,
  `RATE_LIMIT_PER_MINUTE=30`; dead `CONFIDENCE_THRESHOLD_ESCALATION` removed. `demo.html` sends `X-API-Key`
  and no `user_id`. Checkpointer still `MemorySaver` (in-process).
- 4B: `SqliteSaver` (`langgraph-checkpoint-sqlite`, lock regenerated by the user), `CHECKPOINT_DB_PATH`,
  restart test (new orchestrator instance over the same file keeps the conversation), isolation re-checked
  over SQLite, Docker volume for the checkpoint file.
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
