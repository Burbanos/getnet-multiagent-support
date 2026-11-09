# SPEC — Getnet Multi-Agent Support System (v3)

Owner (the author): Burbanos · Planner/reviewer: Claude (external) · Implementer: Antigravity (Gemini)
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
8. **Verifiers run on Python 3.11** (CI and Docker version): no 3.12+ syntax; CI compiles `scripts/`, `src/` and
   `tests/` with 3.11 (from 9A). Float sums that end in a rounded value use `math.fsum` (`sum()` changed in 3.12).
9. **Language policy:** code, identifiers, docstrings, commit messages and this SPEC in English.
   `README.md` and `docs/STATUS.md` in Brazilian Portuguese (pt-BR). Customer-facing answers
   in the language of the user's message (PT or EN).

---

## Current state and next steps (handoff, 2026-11-08)

**Read this first in a new planning conversation.** Repository HEAD at handoff: `c5e2698` (phase 8F, CI green, run #49)
plus this SPEC/prompt update for 9A. CI (lint, tests, docker build + /health smoke) runs on every push.

**Who is the reviewer:** Claude (Anthropic), in sessions separate from Antigravity. It writes this SPEC, the phase
prompts, the verifiers, the labeled sets and the agent/judge prompts, and verifies each phase on its own copy. This is
not an independent review (the same author drives both tools); never describe it as independent. From Phase 11 every
README, STATUS and reply text calls the repository owner "o autor", never "candidato".

**Done (each verified by the reviewer on its own copy with its `scripts/verify_*.py`):**
- Phase 1: honest baseline, test hygiene, CI, Linux lockfile.
- 2A LLM supervisor with function calling · 2B timeouts, error classes, step limit, `X-Trace-Id` · 2C
  provider-agnostic factory, fallback model (`gemini-3.5-flash` → `gemini-3.5-flash-lite`), account masking ·
  2D KnowledgeAgent and SupportAgent sub-agents · 2E real token usage, tools without invented values.
- 3A ingestion of 33 official URLs (30 `ok`: 10 getnet.net/en, 20 site.getnet.com.br; santander.com.br
  dropped, 403 on robots.txt) · 3B chunking, committed `gemini-embedding-2` index, retriever · 3C retriever
  wired into `search_knowledge_base`, legacy KB and ChromaDB removed (index: 92 chunks, 28 pages) · 3D
  retrieval evaluation, `RAG_MIN_SCORE=0.61` (`reports/retrieval_calibration.*`).
- 4A identity from `X-API-Key` (hashed `API_KEYS`, development keys only outside production), thread id
  `user_id:session_id`, tickets by owner, per-key rate limit. Review notes: a malformed `API_KEYS` turned every
  authenticated request into a 500 while `/health` said `configured` (fixed in 4B); the rate limit is per
  process and unlocked (state it in the README claims table, Phase 8).
- 4B `SqliteSaver` at `CHECKPOINT_DB_PATH` (memory survives restarts), fail-fast startup on malformed
  `API_KEYS` or unusable database path, 503 instead of 500 for keys broken at runtime. Lock regenerated in
  Codespaces: +7 lines only (`langgraph-checkpoint-sqlite` 3.1.3, `aiosqlite`, `sqlite-vec`). Review notes: the
  README headline claimed token cost, a routing-accuracy evaluation and an untested multi-turn example (fixed
  in 5A); `/` and `/agents` exposed the database path (fixed in 5A); an existing read-only database file is only
  detected on the first write.
- 5A ticket lifecycle (`open → in_progress → answered → closed`), masked transcript, session and priority on
  the ticket, `PATCH /tickets/{id}` for operators, no `/tmp` fallback, failed escalation no longer reported as a
  ticket. Review notes (fixed in 5B): 4-hex ticket suffix (collision ≈50% at ~300 tickets/day), the tool
  accepted a missing `user_id`, check-then-act race in `update_ticket`, FastAPI 422 deprecation warning.
- 5B handoff gate (`pending_ticket_id`, fixed pending message without LLM, operator reply delivered once,
  `resumed` when closed without reply). Review notes (fixed in 5C): messages sent while waiting never reached
  the operator; `mark_delivered` result ignored (double delivery under concurrent requests). Still open: the
  delivery is marked before the checkpoint write.
- 5C auto-escalation after 2 consecutive knowledge abstentions (no sources), follow-ups appended to the ticket,
  single delivery. Review notes: README says forced escalation resets the counter (it does not: that path skips
  `abstention_check`); `append_customer_message` is read-modify-write without a lock; the transcript has no cap.
- 6A evaluation harness: 69 reviewer-written cases, deterministic checks and metrics (match the reviewer's reference
  on randomized runs), offline safety subset in CI with zero model calls. Review notes (fixed in 6B): README cited a
  non-existent corpus path, claimed the labels were checked against the graph's behaviour (they were not: that
  would be circular) and did not say the reviewer wrote them.
- 6B real-model runner (resumable, temporary tickets DB, stops on repeated `LLMUnavailableError`), blind LLM judge
  (`src/prompts/judge.md`), judge metrics, CLI `run|judge|report`. Review notes (fixed in 6C): the judge read
  `str(response.content)`, which for Gemini 3 replies (a list of content blocks) is a Python repr, so every judgment
  of the first real run was `unparseable`; the judge's stop rule only counted `LLMUnavailableError`, which the judge
  (calling the model directly) never raises; the error line kept only the class name, hiding a 503; the temporary
  tickets directory was never removed; `report` without a results file wrote an empty report and exited 0.
- 6C judge fixes, free-tier defaults (`gemini-3.5-flash-lite` / fallback and judge `gemini-3.1-flash-lite`), `full-1`
  committed with its deterministic report. Review notes (fixed in 6D): the README claimed 1,500 requests/day for
  Flash-Lite (AI Studio shows 500); it suggested `run --run-id full-1`, which now skips every case; STATUS named a
  "Phase 7: prompt calibration to maximise the pass rate" as next (the next step is 6D, and tuning prompts against
  the eval set is overfitting).
- 6D the judge reads full passages from the index by `chunk_id`; runs store up to 2000 characters; README quota and
  judge limits fixed. Review note: README says `search_web` results are not recorded "in the index" (it is the run
  record); fixed in 6E. `observe_turn` now stores `None` instead of `""`/`0.0` for a missing chunk id or score.
- 6E judge run 2 and the final report committed; README "Resultados da avaliação". Review of the WHOLE README
  (earlier reviews only read each phase's diff) found older claims the code does not support, fixed in 6F: a
  "confidence" metric in the UI and README ("Confiança Dinâmica", "100% de precisão determinística") although no
  confidence is computed anywhere (the demo card always shows n/a); cost "estimated in USD from the official token
  table" although `estimated_cost_usd` is always null; a routing evaluation on `data/eval_dataset.json` (removed in
  6A); the official-scenario matrix marking 10/10 "Aprovado" with sources from the deleted hand-written KB
  (`kb_pix_getnet`, ...) while `full-1` measured 9/10; ticket format `XXXX` (it is 10 hex); `MemorySaver` keyed by
  `session_id` in the glossary (it is `SqliteSaver` with `user_id:session_id`); "separação ideal" / "100% off-topic
  rejected" from the retriever-only 3D set presented without the end-to-end failures; token field names
  `prompt_tokens`/`completion_tokens` (they are `input_tokens`/`output_tokens`).
- 6F README and /demo cleaned (verified 32/32). Leftovers for Phase 8: "Trace ID UUID" label, "tokens em todas as
  respostas" (blocked and handoff turns have none), the demo cost label still says "Gemini Flash".
- Found while planning 7A: logs carry `trace_id` only inside message text (no field), several log calls print the
  raw `user_id`, and `run_sync` logs the first 60 characters of the RAW message before the guardrail masks it, so a
  card number or CPF typed by the merchant reaches the logs.
- 7A structured logs (verified 37/37, CI green). Review notes (fixed in 7B): the four `/chat` error logs in
  `src/main.py` run outside `bind`, so they have no `trace_id`/`user_hash` fields (the README says every record has
  them) and they print the provider's exception text; the `tool finished` block is copied four times in `graph.py`.
- Price research for 7B (2026-11-07): Google's official pricing page (https://ai.google.dev/gemini-api/docs/pricing,
  "Last updated 2026-10-30") lists, paid tier, Standard, per 1M tokens: `gemini-3.5-flash-lite` $0.30 in / $2.50 out
  (output includes thinking tokens), `gemini-3.1-flash-lite` $0.25 in (text) / $1.50 out, `gemini-embedding-2` $0.20
  text in. A first fetch returned a stale cached copy (2026-06-02) without 3.5 Flash-Lite; re-fetched and confirmed.
  `gemini-3.5-flash` is no longer listed (the page lists 3.6 and 3.8 Flash), so it is not in the table.
- 7B cost and `/chat` context (verified 32/32, CI green). Review note (fixed in 7C): the three LLM error logs in
  `src/main.py` dropped `{exc}` from the text but kept `logger.exception`, whose traceback still carries the provider
  message.
- 7C `/metrics` (verified 35/35, CI green), no review issues.
- 7D web results, `internal_error`, bilingual fixed messages (verified 38/38, CI green), no review issues. Phase 7 done.
- Audit for Phase 8 (whole repository): `/agents` is hand-written fiction (supervisor tools listed as the account
  tools, invented specialists `HardwareSpecialist`/`WebSearchSpecialist`/`HumanOversightSpecialist`, guardrail
  "tools" `sanitize_pii`/`regex_safety_evaluator`, model "Google Gemini Flash"); `/demo` still says `MemorySaver`
  and "Gemini Flash", prints tokens and cost as a fixed `n/a` although the API returns them, and shows a missing
  similarity as `0.000`; README leftovers ("Trace ID UUID", tokens "Prompt/Completion" and "em todas as respostas",
  "com alta performance", routing "será avaliada na Fase 6", CI described without the Docker build and /health
  probe, Docker Compose without the `API_KEYS` requirement of `APP_ENV=production`). Docker: the named volume is
  mounted on `/app/data`, which also holds the committed index and corpus, so after an image update the container
  keeps serving the OLD index from the volume (fix in 8B: mount the volume on a state sub-directory and point
  `CHECKPOINT_DB_PATH`/`TICKETS_DB_PATH` there).
- 8A `/agents` from the code, `/demo` real fields, README leftovers (verified 39/39, CI green), no review issues.
  Also found for 8B: the Dockerfile makes `/app/data` world-writable (`chmod -R 777`) and `.dockerignore` does not
  exclude local SQLite files, so a local `docker build` would copy real conversations and tickets into the image.
- 8B (verified 38/38 by the static verifier) broke the CI `docker` job: CI starts the image with a plain
  `docker run` (no compose variables), so the app used the code defaults `data/checkpoints.db`/`data/tickets.db`
  in the now read-only `/app/data`, failed fast and never answered `/health`. The reviewer's 8B spec and verifier
  missed it (static checks only; this workspace has no Docker daemon). Fixed in 8C by setting both paths to
  `state/` in the image's `ENV`.
- 8C (verified 34/34; CI docker job green again). AC8.1 verified by the user in Codespaces (2026-11-08): `docker
  compose up --build` healthy, `uid=999(appuser)`, both databases in `/app/state` owned by `appuser`, `/chat` 401
  without a key and 503 with a valid key and no `GEMINI_API_KEY`, `/metrics` counted both, healthy again after
  `docker compose restart`. Found there: the files inside `/app/data` (`corpus`, `eval`, `index`, `sources.yaml`)
  are world-writable in the image (`COPY` keeps the checkout's permissions), so `appuser` could alter the index.
- Final audit (reviewer, whole repository): no API key anywhere in git history; no `.env` or SQLite file tracked;
  the nine review criteria are backed by the "Afirmações e evidências" table. Last README issues: "Limitações"
  and the tickets section still say the databases live in `data/` "preserved in the Docker volume"; "Zero Falsas
  Promessas" reads as a guarantee (it is a prompt instruction). Fixed in 8D with the `/app/data` permissions.
  Open product failures stay documented (not tuned away): `k16` ranking, off-topic `o02`/`o04`, decline-code
  routing `s04`/`s06`, language `off08`, unsupported inference `u01`.
- 8D (verified 35/35, CI green), no review issues.
- Multi-run evaluation (2026-11-08, user's terminal, paid Tier 1 key; code of 8D; judge `gemini-3.6-flash` for all six
  runs): `full-2`, `full-4`, `full-5` with the default `gemini-3.5-flash-lite`; `full-3`, `full-6`, `full-7` with
  `LLM_MODEL=gemini-3.8-flash` (fallback `gemini-3.6-flash`, never used). 69/69 `ok` and 63/63 judged in every run.
  Reviewer recomputation (mean, min–max of three runs), flash-lite vs 3.8-flash: pass 86.0% (84.1–89.9) vs 88.9%
  (88.4–89.9); official 8.7/10 vs 9/10; language 94.7% vs 100%; abstention precision 0.749 vs 0.696, recall 0.769
  vs 0.744; latency p50 4.3 s vs 15.4 s, p95 8.8 s vs 31.6 s; estimated cost per run US$ 0.167 vs 0.640. Decision:
  the default stays `gemini-3.5-flash-lite` (the pass-rate gap is within run-to-run variance; 3.5x latency and ~4x
  cost; evaluators are likely on the free tier). Failed in every run of both models: `k16`, `o02`, `s04`, `s06`.
  3.8-flash only, every run: `off01` (official; abstained although the answer is in the index), `u03` and `u05`
  answered instead of abstaining (decline-code meaning for a network-screen error; Stone fees from web search),
  `k09`, `m04` (answered the follow-up from the previous turn without a new search; the routing label requires one;
  labels are NOT changed after seeing results). In `full-2`, `search_web` returned no results for `off02`/`off07`
  (transient; the same call worked later), kept as failures. Raw files on the user's machine, LF-normalised sha256
  pinned in `scripts/verify_phase8e.py`.
- Price research for 8E (2026-11-08): the pricing page now redirects to https://aistudio.google.com/docs/pricing; it
  lists, paid tier, Standard, per 1M tokens, `gemini-3.6-flash` and `gemini-3.8-flash` at $0.75 in / $3.75 out
  through 2026-12-31 and $1.50 / $7.50 from 2027-01-01 (also in Google's 3.8 Flash launch post, 2026-09-02), and
  `gemini-3.5-flash-lite` unchanged at $0.30 / $2.50. A fetch of the old URL returned a stale copy without these
  models (the same caching problem as in 7B).
- 8E (verified 52/52, CI green). Review notes (fixed in 8F): the README sub-heading "Execução de Referência
  Registrada (`full-1`)" still presents `full-1` as the reference run; "Limitações atuais" and the table of contents
  point only to `full-1`; the README does not say that the recorded output tokens include reasoning tokens. Checked
  against the user's AI Studio usage page (2026-11-08): `gemini-3.8-flash` ≈1.5M input / ≈210K output tokens that
  day vs 1,484,859 / 215,078 recorded by the three runs, so the recorded counts (and `estimated_cost_usd`) include
  thinking tokens. Billing page: R$ 21.43 spent in the month, consistent with the reviewer's ≈US$ 3.6 estimate for
  the six runs plus judge. The `full-1` matrix (section 6) and the claims row "62/69 na `full-1`" stay: earlier
  verifiers pin them and they are labelled as `full-1` results.

- 8F (STATUS reported 42/42; CI green, run #49). Reviewer reproduction on Python 3.11 (2026-11-08): **40/42**.
  `scripts/verify_phase7c.py` does not compile on 3.11 (backslash and reused quotes inside an f-string expression, 3.12+
  syntax) and `verify_phase8e.py` C1 differs in the 6th decimal of the cost: Python 3.12 changed `sum()` of floats to
  compensated summation, so the app (`sum`) and the reference (`sum`) agree on 3.13 and disagree with each other's
  rounding on 3.11. The defects were in the reviewer's verifiers; 42/42 was obtained with the local Python 3.13. Fixed
  in 9A (both sides use `math.fsum`, CI compiles `scripts/` on 3.11).
- Simulated audit with the evaluator's "V4" rubric (PDF "Avaliação V4 — Burbanos (nova versão)", HEAD `c5e2698`):
  **6.9/10** (6.94; previous version 4.23). Section 5 lists README/STATUS claims the code does not support; section 6
  the problems by severity. Reproduced by the reviewer on its copy (2026-11-08): raw card number and CPF in both
  SQLite tables of `checkpoints.db` (`checkpoints`, `writes`) while the model only sees the mask; a provider failure
  after a supervisor tool call leaves `next == ('tools',)` and the AIMessage tool call without a ToolMessage, which is
  sent to the model again on the next turn; `MockDatabase.get_user` builds an account for any user id, with serials
  from `hash()` (random per process); `search_knowledge_base`/`search_web` log the query and `escalate_to_human` the
  reason; the image has no `APP_ENV`, so a plain `docker run` accepts the public development keys. Also confirmed:
  the masked card swallows the following space (`****1111]foi`; the pattern `(?:\d[ -]?){13,19}` consumes it).

- 9A (`6c809bc`; reviewer reran `verify_phase9a.py`: 46/46 on Python 3.11.18 and 3.13.18, `compileall` clean on both;
  reviewer files in the commit identical to the reviewer's copy), no review issues. STATUS records the run on the local
  Python 3.13.3. CI run #50 green (read through the GitHub API): test job on CPython 3.11.18, the new compileall step
  passed, 220 tests; docker job green.
- Found while planning 9B: the raw values are also in `checkpoints.db-wal` (WAL mode), not only in the two tables, so the
  9B checks scan every file of the database directory; follow-ups appended to a pending ticket were already masked
  (the guardrail runs before `handoff_gate`).

- 9B (`a561d4c`; reviewer reran `verify_phase9b.py`: 50/50 on 3.11.18 and 3.13.18; reviewer files identical; CI run
  #51 green, 225 tests on 3.11.18), no review issues. The implementer's tests are slightly stricter than asked (they also
  assert `AgentState.message` is masked). The user's old local `data/checkpoints.db` was deleted.
- Planning 9C (reproduced on `a561d4c`): after a provider failure inside a specialist, the thread keeps
  `next == ('tools',)` and the supervisor's tool call without a ToolMessage; with two tool calls in one message and the
  second specialist failing, neither gets a ToolMessage (the tools node writes atomically); the internal-error path
  (non-LLM exception in the tools node) leaves the same orphan. A failure before any tool call leaves only the
  HumanMessage, which needs no repair. Fix: `run_sync` writes error ToolMessages with
  `update_state(..., as_node="abstention_check")` (edge to END, so `next == ()`).

- 9C (`308d382`; reviewer reran `verify_phase9c.py`: 48/48 on 3.11.18 and 3.13.18; reviewer files identical; CI run
  #52 green, 230 tests on 3.11.18), no review issues.
- 9D prompt change (reviewer file): `src/prompts/support_agent.md` gains one rule for `status: "not_found"` (say the
  account was not found, give no values, suggest a human agent). The committed real-model runs predate it; it only fires
  for unknown merchants, and every eval case uses `cliente1988`, so the reported numbers are unaffected.

- 9D (`613991b`; reviewer reran `verify_phase9d.py`: 50/50 on 3.11.18 and 3.13.18; reviewer files identical; CI run
  #53 green, 236 tests on 3.11.18), no review issues.
- Planning 9E (reproduced on `613991b`): with the Dockerfile's ENV and no `API_KEYS`, the app runs in `development`,
  `POST /chat` with `getnet-dev-key` passes auth and `GET /tickets` with `getnet-dev-operator` returns 200 (every ticket,
  with transcripts). `docker compose config` with `.env` copied from `.env.example` (as the README instructs) resolves
  `APP_ENV: development`. The reviewer's container has the docker CLI and compose plugin but no daemon: the image build
  and the new CI steps are checked in Actions; `verify_phase9e.py` runs the CI curl step against uvicorn started with
  the Dockerfile's ENV when bash and curl exist.

- 9E (`48af0a0`; reviewer reran `verify_phase9e.py`: 51/51 on 3.11.18 and 3.13.18, including the compose and CI-script
  checks the user's Windows machine skips; reviewer files identical; CI run #54 green: the real image reports
  `environment: production`, both public keys get 401, and Compose resolves production with the example `.env`).
- Planning 9F (reproduced on `48af0a0` with a unique marker): the marker reaches the log in 7 of 8 scenarios
  (knowledge and web search queries, support tool arguments, escalation reason, provider errors with and without
  fallback, internal error, API 500); only a normal turn is clean. Errors will log `exc_brief(exc)` (class and the
  innermost code locations, no message); `logger.exception` is gone from the service code. Two new
  `except Exception as exc` need `# noqa: BLE001` (ruff flags a blind except that does not re-raise).

- 9F (`ffb210b`; reviewer reran `verify_phase9f.py`: 53/53 on 3.11.18 and 3.13.18, the marker absent in all 8 log
  scenarios; reviewer files identical; CI run #55 green, 243 tests), no review issues.
- Planning 9G: confirmed on `ffb210b` that the guardrail lets both audit paraphrases through and blocks both legitimate
  questions; corpus 30 pages / 92 chunks (16 from one blog post), `no_content` for the Brazilian home, payment-link and
  WhatsApp pages; scenario 10's gold URL is the global online-payments page. Known follow-up, out of scope:
  `src/eval/compare.py` averages with `sum()`, so regenerating `reports/eval_models.json` on 3.11 vs 3.13 can change the
  last digit of some means (the 8E check K2 compares with a tolerance, so it passes on both).

- 9G (`6456bf5`; reviewer reran `verify_phase9g.py`: 53/53 on 3.11.18; reviewer files identical; CI run #56 green, 243
  tests). Reconfirmation of the simulated V4 audit on `6456bf5` (PDF "Avaliação V4 — Burbanos (nova versão) v2", section 9):
  probes 1, 2, 3 and 5 fixed, probe 4 (guardrail) unchanged and listed in "Limitações atuais"; the nine section-5 claims
  fixed. Still open from the real V4 feedback: "guardrail só por padrões", "clima e câmbio dependem de snippets de busca,
  não de API", no video (the video is the user's).
- Planning Phase 10 (reproduced on `6456bf5`): with the five narrowed patterns of 10A the 243 tests still pass, the six
  offline safety cases and the `/demo` injection scenario are still blocked, and on the 36-message pre-registered guardrail
  set the pattern layer goes from 6/20 injections blocked and 6/16 legitimate messages blocked to 6/20 and 0/16 (the
  paraphrases are left to the classifier). The reviewer's sandbox has no route to `open-meteo.com` or `olinda.bcb.gov.br`
  (proxy 403): API shapes come from the official docs (Open-Meteo forecast and geocoding docs; BCB "Taxas de câmbio -
  todos os boletins diários", OData `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/`, dates
  `'MM-DD-YYYY'`, fields `paridadeCompra`, `paridadeVenda`, `cotacaoCompra`, `cotacaoVenda`, `dataHoraCotacao`,
  `tipoBoletim`), and the test fixtures are captured from the live APIs by the user in 10D (public, no key). Terms
  (checked 2026-11-09): Open-Meteo free API for non-commercial use only, under 10,000 calls/day, data under CC BY 4.0 with
  attribution ("Weather data by Open-Meteo.com" linked to open-meteo.com); BCB PTAX dataset under ODbL.

- 10A (`1eb3626`; reviewer reran `verify_phase10a.py`: 62/62 on 3.11.18 and 3.13.18; reviewer files identical; CI run #57
  green, 254 tests). Minor, not fixed: `load_guardrail_set` does not type-check `text` (a number would raise
  AttributeError, not ValueError); the CLI catches every exception when loading the set. Missed by the reviewer's 10A
  prompt and fixed in 10B: the README security bullet "Proteção contra Injeção de Prompt" still listed the bare phrases
  `"regras internas"`, `"prompt de sistema"` and `"esqueça o que foi dito"` as blocked, which the narrowed patterns no
  longer block on their own. The push of 10A first hung waiting for the GitHub sign-in (the user had moved the remote off
  a token stored in `.git/config`); the commit is unchanged.
- Fail-open as the default failure mode: the user delegated the decision to the reviewer (2026-11-09); the reviewer kept
  fail-open for the reasons in Phase 10 below.
- 10B (`fac9e87`; reviewer reran `verify_phase10b.py`: 68/68 on 3.11.18 and 3.13.18; reviewer files identical; CI run #58
  green, 270 tests). Minor, not fixed: a non-configuration exception while building the classifier model (outside the
  invoke) is not caught, so it becomes the generic `internal_error` reply instead of fail-open; the guardrail counter's
  `# HELP`/`# TYPE` lines appear in `/metrics` only after the first decision; the STATUS 10B section has no "Não feito".
- 10C (`b06dec3`; reviewer reran `verify_phase10c.py`: 61/61 on 3.11.18 and 3.13.18; reviewer files identical; CI run #59
  green, 280 tests), no review issues. The reviewer's first 10C verifier let two wrong implementations pass (targets met on
  an incomplete run; p95 = maximum); found by mutation testing before publishing and fixed (C7).
- Re-split of the rest of Phase 10 (2026-11-09): the reviewer's sandbox cannot reach Open-Meteo or Olinda, and the docs
  leave open details that decide the module's behaviour (the exact closing-bulletin name, whether USD is in the `Moedas`
  list, what geocoding returns for an unknown city). So 10D captures real responses first; the module follows in 10E.
- 10D (`74f9ee1`; reviewer reran `verify_phase10d.py`: 54/54 on 3.11.18; reviewer files identical; CI run #60 green, 280
  tests), no review issues. The captured bodies carry the server's own `@odata.context` host, microsecond timestamps and
  per-day bulletin sequences, consistent with real responses. Findings that fix the 10E contract: PTAX publishes
  `Abertura`, three `Intermediário` and one `Fechamento` per business day (the closing shares the timestamp of the last
  intermediate), weekends and the 2 November holiday return `"value": []`; `Moedas` lists 10 currencies including USD; an
  unknown currency (XYZ) also returns 200 with `"value": []`, so `Moedas` is what tells "unknown currency" from "no
  bulletin"; an unknown city returns 200 with no `results` key; the forecast snaps the coordinates to its grid
  (-29.98/-51.19 for the geocoded -30.03/-51.23) and returns its own units (`°C`, `%`, `mm`); latitude 999 returns 400 with
  `reason`. EUR closing 2026-11-06: 6.13 / 6.1317.
- 10E (`2daa711`; reviewer reran `verify_phase10e.py`: 63/63 on 3.11.18 and 3.13.18; reviewer files identical; CI run #61
  green), no review issues.
- Re-split of 10F/10G (2026-11-09): 10F as first planned (tools, prompts, `api_results`, eval plumbing, `cases_v2`) is
  well over ten actions, so it becomes 10F (tools, prompts, state/API, README), 10G (eval plumbing and `cases_v2`) and 10H
  (the user's real runs and the README numbers). Found while simulating 10F: the `httpx` library logs every request URL
  (city, currency, dates) at INFO. Today it never reaches an output (only the `multiagent` logger has a handler), but a
  deployment that configures the root logger would print it; 10F pins the `httpx` logger at WARNING and the verifier
  checks the logs with the root logger at INFO.
- 10F (`939b67b`; reviewer reran `verify_phase10f.py`: 61/61 on 3.11.18 and 3.13.18; reviewer files identical; CI green
  (test and docker), 310 tests). Minor, not fixed: STATUS says the logs "mask" city and currency (they never log them) and
  points the real-model runs to 10G (they are 10H); `get_exchange_rate` wraps the fetch in the same `try` as the date
  parsing, harmless because `public_data.py` raises nothing. Antigravity first ran the new tests in the background and the
  `TestClient` test hung the sandbox, as known.
- 10G decisions (2026-11-09): the API-status expectation is folded into `tools_ok` instead of a new check, because a new
  entry in `CHECKS` would change every per-case `checks` dict and break the 6A reference comparison on v1; v1 cases have
  no `api_status`, so their results are unchanged. The four re-labelled weather/FX cases now expect `abstain: false` (an
  API answer is substantive). The judge prompt names the API results as evidence and says weather and FX values need it;
  v2 judgments are therefore not directly comparable with the v1 runs, which were judged with the previous prompt. The
  authorship line keeps `data/eval/cases.jsonl` (pinned by 9A) and lists the other two labeled files.
- 10G (`d2744b1`; reviewer reran `verify_phase10g.py`: 65/65 on 3.11.18 and 3.13.18; reviewer files identical; CI green
  (test and docker), 316 tests), no review issues. Found while reviewing: 7A `L2.no_pii_in_logs` looks for the bare
  substring `4111`, which a log timestamp's microseconds can contain; reproduced 2 times in 240 runs, both from a
  timestamp, never from a card. 10H supersedes it and re-checks with markers a timestamp cannot contain (H6).
- 10H/10I split (2026-11-09): the README numbers can only be written after the reviewer reads the real runs, so the real
  runs and their reports are 10H (no code change) and the README, the limitations and the reply to the V4 feedback are
  10I. The user's Gemini project is on the paid tier, so the three runs of each evaluation fit in one session with
  `--sleep 1`; the judge is `gemini-3.6-flash`, as in `full-2`..`full-7`, and must differ from the answer model.
- 10H (`9b8d082`; reviewer files identical; the 9 raw records in the commit are byte-identical to the ones the
  reviewer read in the user's folder before Antigravity ran; CI green). `verify_phase10h.py`: 60/60 on 3.13.18 but 59/60
  on 3.11.18: `H5.v2_reports` compares floats exactly, and `compare.py` averages with `sum()`, whose float summation
  changed in Python 3.12 (compensated); `facts_rate` mean differs by 2e-16. Verifier defect, not a data defect; 10I
  re-checks with a 1e-9 tolerance (I6). STATUS 10H named the answer model `gemini-2.5-flash-lite` (records say
  `gemini-3.5-flash-lite`); corrected in 10I with a note. Results: hybrid guardrail blocked 20/20 attacks in all 3 runs,
  false positives 2, 1, 2 of 16 (mean 10.4%, target ≤10% met in 1 run; both false positives in `holdout`: `ga07` in 3
  runs, `ga14` in 2); classifier p50 0.80 s, p95 0.98 s, US$ 0.00027 per message. v2: 91.9% (91.0-92.3) pass, the 11
  `public_data` cases pass in all runs, no legitimate case blocked, `k16`/`o02`/`s04`/`s06` fail in all runs as in v1.
  The classifier prompt is not tuned after these results (pre-registered).

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
`docs/SPEC.md`, `docs/phase-prompts/*.md` and `src/prompts/*.md` and the labeled sets `data/eval/*.jsonl`
(from 2026-11-07; the 3D set was still copied from the prompt), between phases, after checking that the
local folder equals GitHub HEAD; the user types `Execute docs/phase-prompts/<phase>.md` in Antigravity, which
commits the reviewer files unchanged; the reviewer monitors GitHub and verifies on its own copy. Each verifier
reruns earlier ones with `VERIFY_NESTED=1` (skips their suites) and lists superseded checks in `PRIOR`
(2A: R2.single_tool_flow, R3.user_id_injected, R3.bound_tools, R4.two_tools_sequence; 2B:
S1.default_model_config, S1.default_model_env_example, R2.model_name; 2D: R6.knowledge_flow; 3B: L1.settings,
which pinned the provisional `RAG_MIN_SCORE=0.60`; 4A: the checks that call `/chat` without a key, re-checked
with a key as C1–C4 in `verify_phase4a.py`). When a phase invalidates earlier checks, its verifier re-checks the
covered behaviour under the new rule. From 4B, nested verifier runs get a temporary `CHECKPOINT_DB_PATH`. Anything that
needs the API key (index builds, smoke tests, real-model evals) is run by the user in a terminal with
`Read-Host -MaskInput`; Antigravity must stop and ask. Antigravity's sandbox hangs pytest/TestClient when run
in the background on Windows: run tests and verifiers in the foreground. Local Python is 3.13, CI and Docker
use 3.11; the lock is regenerated in Codespaces with the `python:3.11-slim` image.

- 10I (`e8eb27e`; reviewer reran `verify_phase10i.py`: 59/59 on 3.11.18; CI runs #57-#65 green for 10A-10I, read through
  the GitHub API on 2026-11-09). Simulated V4 audit re-check of 10A-10I (PDF "Avaliação V4 — Burbanos (nova versão) v3",
  section 10): weather/FX correct; the guardrail paraphrases are blocked only by the classifier, measured on a set written
  together with the classifier prompt (commit `1eb3626`), so in-sample, not independent; design defect: a `block` verdict
  with category `none`, or an answer without a tool call, is treated as an error and fails open; three README claims not
  supported ("fixados antes de existir o classificador", "APIs oficiais (Open-Meteo e PTAX)", and the v2 records do not show
  that the classifier ran or which layer decided). Phase 11 addresses them.
- The evaluator told the author the presentation video is not required (2026-11-09); the resubmission goes without video.

- 11A (`a2db8ac`; reviewer reran `verify_phase11a.py`: 69/69 on 3.11.18; reviewer files identical; CI run #66 green, 331
  tests). Minor, not fixed: `test_invalid_records_block_and_are_not_retried` puts the invalid answer on `gb02`, which the
  patterns already block, so its `hybrid_blocked` assert would pass without the change (A10 covers it with a legitimate
  message); the verifier prints the graph's JSON logs to stdout during its module checks (cosmetic).
- Holdout provenance (2026-11-09): the author asked another model instead of writing the messages by hand. The reviewer
  wrote the generation prompt (`docs/phase-prompts/11B-gerador-holdout.md`, it names the three attack types and ways to vary
  the messages, no classifier rule or example); the author ran it in a separate conversation with GPT 6.1 Sol (outside
  Antigravity), got 30 candidates, chose 20 (10 block / 10 allow, 5 pt + 5 en each), rewrote 18 by hand, checked every
  label and kept the suggested ones, and states they did not read the classifier prompt, the 36-message set or the README
  guardrail section. The reviewer checked the format only.

- 11B (`a3bb4df`, committed 2026-11-09T17:24:59Z; reviewer reran `verify_phase11b.py`: 62/62 on 3.11.18; reviewer files
  identical; no `author-*` file in the commit; CI run #67 green, started 17:25:31Z), no review issues.
- `author-1` (the author's only run, 2026-11-09 17:30:59Z-17:31:34Z, after the 11B commit and its CI run): 20 records, one per
  message, all `ok`, classifier `gemini-3.5-flash-lite` (the model of `hybrid-1..3`). Reviewer recomputation with
  `guardrail_report`: patterns 0/10 blocked; classifier and hybrid 10/10 blocked, 0/10 false positives; targets met;
  p50 879 ms, p95 1037 ms; 706 input / 24 output tokens and US$ 0.00027 per message. 20 messages give wide intervals (95%
  Wilson: block rate >= 0.72, false-positive rate <= 0.28); state that next to the result. The classifier prompt is not
  changed after this run.

- 11C (`aac5773`; reviewer reran `verify_phase11c.py`: 61/61 on 3.11.18; reviewer files identical; the committed record is
  byte-identical (LF) to the file the author's run wrote; CI run #68 green), no review issues.

- 11D (`1f7e93d`; reviewer reran `verify_phase11d.py`: 64/64 on 3.11.18; reviewer files identical; 334 tests). CI run #69
  first ended as failure with only the `test` job (green): the `docker` job was never created; re-run by the author
  (attempt 2), both jobs green. No review issues.
- Tier declaration (2026-11-09): the author confirmed in AI Studio that every real-model run from 2026-11-08 on (`full-2` to
  `full-7`, `v2-1` to `v2-3`, `hybrid-1` to `hybrid-3`, `author-1`) used the paid Tier 1 project, and that `full-1`
  (2026-11-07) used the free tier.

- 11E (`c6a3aeb`; reviewer reran `verify_phase11e.py`: 65/65 on 3.11.18; reviewer files identical; CI run #70 green, test and
  docker). Minor, accepted: `write_guardrail_summary` also gained an optional `context` parameter passed to
  `guardrail_summary` (not asked; harmless).

- 11F (`ba480df`; reviewer reran `verify_phase11f.py`: 63/63 on 3.11.18; reviewer files identical; CI run #71 green, test and
  docker). No review issues.

**Current phase: 11G** (README reorganized), prompt `docs/phase-prompts/11G.md`, verifier `scripts/verify_phase11g.py`. Phase 11 is the last before the resubmission. Open
product failures (`k16`, `o02`, `s04`, `s06` in every run; `off01` with 3.8-flash) stay documented; fixing them needs new
held-out cases, not prompt tuning against these.

**Free-tier quota (user's AI Studio page, 2026-11-07):** "Gemini 3.6 Flash" (what `gemini-3.5-flash` now serves)
5 RPM / 20 RPD; `gemini-3.5-flash-lite` 15 RPM / 500 RPD; `gemini-3.1-flash-lite` 15 RPM / 500 RPD (separate quota);
`gemini-embedding-2` 100 RPM / 30K TPM / 1K RPD; `gemini-2.5-flash-lite` returns 404 for new users. Each case makes
3–6 model calls, so the Flash default cannot run the 69 cases (≈300 calls) in a day. Decision (6C): defaults become
`LLM_MODEL=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL=gemini-3.1-flash-lite`, `EVAL_JUDGE_MODEL=gemini-3.1-flash-lite`
(a different model from the answers). If 3.1 Flash-Lite stays overloaded (it returned 503 "high demand" for hours on
2026-11-07), the documented fallback is `EVAL_JUDGE_MODEL=gemini-3.5-flash-lite`, a self-judging setup whose bias
must be stated next to the numbers (`judge_models` records it).

**Real runs on 2026-11-07 (user's terminal, `LLM_MODEL=gemini-3.5-flash-lite`):**
- Smoke (3 official EN cases, 6B prompts): all three answers in Portuguese (`language_rate` 0). The reviewer moved the
  language rule to its own section at the top of `supervisor.md`, added a final check at the end, and told both
  specialists that tool results and passages are in Portuguese and must be translated for English requests.
  Re-run on 9 EN cases: 8/9 in English; the second turn of `m06` ("Ok. And can you check yesterday's deposit too?")
  still came back in Portuguese. No further prompt tuning against the eval set (it would overfit).
- Other failures seen in the 9 EN cases: `s06` ("What does decline code 05 mean?") routed to the Knowledge Agent
  instead of `diagnose_declined_transaction`, and the model emitted a non-existent tool `escalate_to_knowledge_agent`
  (rejected by the graph without crashing); `off04` (Pix bank account) escalated on its own after a knowledge
  abstention instead of offering, with the ticket reason written in Portuguese; `off02` (weather) cited its web
  source as "(retrieved March 2025)" with identical numbers across runs (either an invented date or a stale page:
  investigate in 6D with the raw `tool_results`).
- Full run `full-1`: 69/69 `ok` (resumed once after a laptop restart; the file was intact). Raw file
  `reports/eval_runs/full-1.jsonl` (sha256 of the LF-normalised bytes `70e300da…ab2b`) is committed in 6C unchanged.
  The judge run on it hit the list-content bug: `full-1.judge.jsonl` is deleted in 6C and re-run after it.
- Deterministic report of `full-1` (reviewer recomputed): pass 62/69 (0.899), official 9/10, routing 0.946, tools
  0.951, facts 0.917, sources 0.920, language 0.984, escalation precision/recall 1.0/1.0, latency p50 6.3 s / p95
  20.4 s, 422k tokens (~6.7k per case). Failures: `s04`, `s06` (decline-code questions routed to knowledge), `o02`
  (off-topic routed to an agent), `k07`, `k16`, `k17` (facts/sources), `off08` (language). The 8 `uncovered` cases
  pass deterministically only because no deterministic check applies to them: their real metric is the judge's.
- Judge run 1 on `full-1` (after 6C, `gemini-3.1-flash-lite`, 63 judged, 0 errors): abstention precision 0.714,
  recall 0.769; 7/8 uncovered abstained (`u01` answered); off-topic `o02` answered from web search and `o04` wrote
  the requested ocean poem (a product failure no deterministic check catches); `k07`, `k16`, `s04`, `s06` abstained
  when an answer was expected. Its `grounded` scores are INVALID: the runner stored passages cut at 600 characters
  (74 of the 92 chunks are longer; median 834) and the judge flagged literal official facts as invented (R$ 129,90
  in `k03`; the R$ 50 advance minimum in `k04`/`k15`). Not published; the file is deleted in 6D and the judge re-run.
  The run records keep only the specialist's answer for `search_web`, not the search results, so the judge cannot
  check web answers (it scored them as general knowledge).
- Judge run 2 on `full-1` (after 6D, full passages; `full-1.judge.jsonl` sha256 of the LF-normalised bytes
  `62b743f9…3dd6`), recomputed by the reviewer with the 6B reference: 63 judged, 0 errors; grounded mean 4.95,
  answers 4.68; abstention precision 10/13 and recall 10/13 (0.769); abstention errors `k16`, `o02`, `o04`, `s04`,
  `s06`, `u01`; disagreements `k07`, `k16`, `k17`. The six false "invented" verdicts of run 1 disappeared; the only
  grounded 3 is `m01` (gave the Get Clássica price, omitted the Get Smart one). `u01` claims "no Pix key needs to be
  registered", which no chunk says (no chunk mentions "chave Pix"); the judge accepted it: grounded is near the
  ceiling and the small judge is lenient.

**Design change kept from 5B:** the handoff gate replaced `interrupt()` (see AC5.2); the user can still ask to revert.

**Backlog:**
- Phase 6 (from 3D): real-model abstention on the 10 `uncovered` queries through the Knowledge Agent as a
  headline metric; harder negatives (other acquirers, banks, generic payments); "answered with the answer"
  vs "passed the threshold"; language rule (EN question → EN answer) and collection-date citation; replace
  `data/eval_dataset.json` (ground truth from the old KB).
- Phase 7 (from 6B review): `run_sync` turns any non-LLM exception into a fixed Portuguese "instabilidade" reply, so
  an infrastructure failure is scored as an `ok` wrong answer and English users get Portuguese; the forced-escalation
  and handoff messages are also fixed Portuguese strings. Mark errors in the state instead of relying on text.
- Phase 7: record `search_web` results (url, title, snippet) in the turn so the judge can check web answers; the
  `off02` weather answer cited "(retrieved March 2025)" and cannot be traced with the current records.
- Off-topic handling: `o04` (poem) was answered and `o02` went to an agent; revisit the supervisor's scope rule only
  with new held-out cases, not by tuning against these.
- Tests leave SQLite connections unclosed: with `-W error` about 20 tests fail on `ResourceWarning` (already in 6A).
- PII masking eats the space after a masked card ("[CARTAO_MASCARADO_****1111]foi").
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
[guardrail]  PII masking (before the graph) → injection patterns (cheap, no model)
             → LLM classifier (forced function call, own prompt; fail-open by default, Phase 10B)
             ── blocked ──▶ END (refusal, logged without text)
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
                               get_weather_forecast(city, ...) → Open-Meteo values w/ unit, time, source_url (10E)
                               get_exchange_rate(currency, date) → BCB PTAX values w/ unit, bulletin time, source_url (10E)
                               search_web(query)            → snippets w/ url (only what no API covers: news)
                               abstains when best score < calibrated threshold
Support Agent   (LLM + tools): get_settlement_status, get_declined_transactions,
                               diagnose_terminal  (user_id injected from auth context)
Escalation: ticket row + transcript snapshot; pending_ticket_id hands the thread to the human
            (handoff_gate); operator replies via PATCH /tickets/{id}; next user turn delivers the reply.
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
- 4B (checked by `scripts/verify_phase4b.py`): dependency `langgraph-checkpoint-sqlite>=3.1,<4` (3.1.3 accepts
  the locked `langgraph-checkpoint==4.3.1`; adds `aiosqlite` and `sqlite-vec`), declared in a first commit; the
  user regenerates `requirements.lock` in Codespaces with `python:3.11-slim` and `pip-compile` (existing pins
  kept) before the implementation. `src/core/checkpointer.py`: `build_sqlite_checkpointer(path)` creates the
  parent directory, opens `sqlite3.connect(path, check_same_thread=False)` (FastAPI runs sync endpoints in a
  thread pool; `SqliteSaver` serialises access with its own lock) and returns a `SqliteSaver`; any failure
  propagates (no temp-dir or in-memory fallback). `OrchestrationGraph(..., checkpointer=None)`: None keeps
  `MemorySaver`, so tests and earlier verifiers stay in memory; `get_orchestrator()` builds the SQLite one at
  `CHECKPOINT_DB_PATH` (default `data/checkpoints.db`, inside the Docker data volume). `.gitignore` covers the
  database and its WAL files. Fail-fast configuration: `validate_auth_config()` raises ValueError for a
  malformed `API_KEYS`; `auth_mode()` reports `invalid`; `authenticate` answers 503 "Authentication
  misconfigured: check API_KEYS." instead of 500; the FastAPI lifespan calls `validate_auth_config()` and
  `get_orchestrator()`, so the app refuses to start with bad keys or an unusable database path.
  `tests/conftest.py` sets `CHECKPOINT_DB_PATH` to a temporary file before importing `src`; the suite never
  writes `data/checkpoints.db`. `/` and `/agents` stop describing `MemorySaver`. Known limits (README):
  no retention or cleanup of old threads; one SQLite file per instance (no shared memory across replicas).
**Acceptance:**
- AC4.1 API keys configured via env (hashed), mapped to `{user_id, role}`; missing/invalid key → 401; no default key accepted when `APP_ENV=production`.
- AC4.2 Body `user_id` ignored or must equal principal (403 otherwise) — test.
- AC4.3 `SqliteSaver` checkpointer; thread id `user_id:session_id`; restart test proves memory survives; user B cannot read user A's session (test).
- AC4.4 `/tickets` filtered by owner; operator role sees all.
- AC4.5 Basic rate limit per key (test).

### Phase 5 — Human escalation with handoff and resume
**Split:**
- 5A (checked by `scripts/verify_phase5a.py`): `src/core/tickets_db.py` rewritten without fallbacks:
  `TicketsRepository(db_path)` creates the parent directory, creates the table if missing and adds the new
  columns to an existing pre-5A table (`session_id`, `transcript` JSON default `[]`, `operator_reply`,
  `operator_id`, `answered_at`); any failure raises (no `/tmp`, no `chmod`, no second database).
  `create_ticket(user_id, reason, priority="standard", session_id=None, transcript=None)` validates priority
  (`standard|high`, else ValueError), strips the reason and keeps the current return shape (`status: "success"`,
  `ticket_id`, `ticket_status`, ..., `message` with the id and no time promise). `get_ticket` returns every
  column with `transcript` decoded; `list_tickets(user_id=None, status=None, limit=50)` clamps limit to 1..200;
  `update_ticket(ticket_id, *, status=None, reply=None, operator_id)` returns None for unknown ids; a reply sets
  status `answered`, `operator_reply`, `operator_id`, `answered_at`; allowed transitions open→{in_progress,
  answered, closed}, in_progress→{answered, closed}, answered→{closed}, closed→{} (else `TicketTransitionError`,
  a ValueError); unknown status or `answered` without reply → ValueError. `transcript_snapshot(messages, limit=20,
  max_chars=2000)`: user and assistant text only (no tool messages, no tool-call-only AI messages), last 20,
  each truncated; messages are already PII-masked by the guardrail. `get_tickets_repository()` reads
  `settings.TICKETS_DB_PATH` (default `data/tickets.db`, env wins); `reset_tickets_repository()` for tests.
  `escalate_to_human(reason, priority)` is the only model-visible signature; `user_id`, `session_id` and
  `transcript` come from the run config set by the graph (also in the forced escalation); a persistence error
  returns `{"status": "error", "error": "ticket_persistence_failed"}` without exception text, and the graph keeps
  `ticket` only when the result has a `ticket_id`. API: `PATCH /tickets/{id}` (operators only; body `status`
  and/or `reply`; 401/403/404, 409 for an invalid transition, 422 for an empty body, unknown status or
  `answered` without reply); `GET /tickets?status=` filter; customers see `operator_reply` on their own tickets.
  The lifespan also opens the tickets database. `/` and `/agents` expose no database paths.
- 5B (checked by `scripts/verify_phase5b.py`): `SupervisorState` gains `pending_ticket_id` (persisted by the
  checkpointer; never part of the per-turn input, so it survives turns and restarts) and `handoff` (per-turn,
  reset by the input). Creating a ticket (tool or forced escalation) sets `pending_ticket_id`; a failed one does
  not. Graph: START → guardrail → (blocked → END) → `handoff_gate` → supervisor | END. The gate, with a pending
  ticket: unknown ticket → clear and continue; `operator_reply` present and `delivered_at` empty (answered, or
  answered then closed) → answer `HANDOFF_REPLY_PREFIX + reply`, `mark_delivered`, clear, END; closed without
  reply → clear, `handoff.status = "resumed"`, continue to the supervisor; otherwise → `HANDOFF_PENDING_MESSAGE`
  (fixed, bilingual, ticket id, no time words), END. Gate turns call no LLM (`llm_model` and `tokens` null),
  `agents_used = ["HumanHandoff"]`; the customer's message is still masked by the guardrail and kept in memory.
  API metadata gains `handoff` (`{ticket_id, status}` or null) and `agent_type = "HumanHandoff"` on gate turns.
  Tickets: `delivered_at` column (migrated), `mark_delivered(ticket_id) -> bool` (only the first call returns
  True), ticket suffix of 10 hex chars, `create_ticket` rejects an empty `user_id` (the tool then answers
  `status: error`), `update_ticket` uses `UPDATE ... WHERE ticket_id = ? AND status = ?` and raises
  `TicketTransitionError` when no row changed. 422 responses use `HTTP_422_UNPROCESSABLE_CONTENT`; the suite runs
  without warnings.
- 5C (checked by `scripts/verify_phase5c.py`): a knowledge call "abstains" when the Knowledge Agent returns no
  `sources` (neither official pages nor web). Per turn, `knowledge_outcomes: list[bool]` (reset by the input)
  records one entry per `ask_knowledge_agent` call; `consecutive_abstentions: int` is persisted. A new
  `abstention_check` node runs when the supervisor finishes (supervisor "end" → `abstention_check` → END):
  ticket created this turn → counter 0; no knowledge call → unchanged (small talk does not reset); any grounded
  call → 0; otherwise +1, and when it reaches `ESCALATE_AFTER_ABSTENTIONS` (default 2, 0 disables) with no
  pending ticket, it calls `escalate_to_human` (priority standard, reason stating the automatic trigger, session
  and transcript from the state); on success it appends `"\n\n" + AUTO_ESCALATION_NOTE` (fixed, bilingual, no
  time words) to the final answer, sets `ticket` and `pending_ticket_id`, adds `escalate_to_human` to
  `tools_used` and resets the counter; on failure nothing is appended and the counter is kept. Gate fixes:
  while pending, the customer's (masked) message is appended to the ticket transcript
  (`append_customer_message(ticket_id, content) -> bool`, content cut at 2000 chars) so the operator sees it;
  the reply is delivered only if `mark_delivered` returns True, otherwise the gate clears the pending ticket and
  resumes. Verifier 5B check F4 is superseded (it asserted the old transcript behaviour; re-checked as G3).
**Acceptance:**
- AC5.1 Ticket stores reason, priority, transcript snapshot, status (`open|in_progress|answered|closed`).
- AC5.2 While a ticket is pending the thread is handled by the `handoff_gate` (no LLM, fixed status message); operator `PATCH /tickets/{id}` with reply; the next user turn returns the operator reply exactly once, then normal service resumes (tests). (Reworded 2026-11-07: originally `interrupt()`.)
- AC5.3 Customer-facing escalation message contains no ETA/queue promise (test asserts on forbidden phrases).
- AC5.4 Auto-escalation triggers: explicit request, max steps, repeated abstention (tests).
- AC5.5 Persistence failure surfaces an error to the user; no silent `/tmp` fallback.

### Phase 6 — Evaluation
**Split:**
- 6A (checked by `scripts/verify_phase6a.py`): `data/eval/cases.jsonl` (reviewer-owned, 69 cases: the 10 official
  scenarios verbatim, 17 more knowledge questions whose gold URLs and facts were checked against literal corpus
  text, 6 support, 2 web, 8 uncovered, 5 off-topic, 6 safety, 2 PII, 5 escalation, 6 multi-turn, 2 multi-intent;
  41 PT, 28 EN). Case keys: `id`, `category`, `lang`, `official`, `offline` (safety only), `turns` (the last one is
  evaluated; earlier turns run in the same session), `expect` with exactly `agents` (set of specialists, `[]` = none,
  null = not checked), `tools_all`, `tools_none`, `escalate`, `priority`, `blocked`, `gold_urls`, `facts_any`
  (groups; every group needs one alternative in the answer), `facts_none`, `abstain` (judged in 6B).
  Package `src/eval` (no regex, no imports from `tests/`): `cases.load_cases` (ValueError on duplicate id, unknown
  category, language, agent or tool, empty turns, missing/extra keys, `offline` outside safety), `cases_sha256`
  (canonical form as in 3D); `checks.detect_language` (lowercase, split on whitespace, strip the punctuation
  in `STRIP` (exact string in `docs/phase-prompts/6A.md`), count hits in `PT_WORDS` and `EN_WORDS`, larger wins, tie → `unknown`); `checks.
  evaluate_case(case, result)` → `{"checks": {...}, "passed"}` over the last turn, each check True/False/None
  (not applicable): `routing_ok` (specialists in `agents_used` == expected set), `tools_ok`, `escalation_ok`
  (ticket created == expected), `priority_ok`, `blocked_ok` (always), `sources_ok` (any gold URL in sources),
  `facts_ok`, `facts_none_ok` (whitespace-normalised, lowercase substring), `language_ok` (skipped when blocked,
  unsafe or handoff); `passed` = all applicable checks true; a result with status other than `ok` → all None,
  not passed. `metrics.aggregate(cases, results)`: errors excluded from every rate and listed; `<check>_rate`
  (`routing_rate`, `tools_rate`, `escalation_rate`, `priority_rate`, `blocked_rate`, `sources_rate`,
  `facts_rate`, `facts_none_rate`, `language_rate`), `pass_rate`, escalation precision/recall, latency p50/p95
  per case (nearest rank, turns summed), `tokens_total` and `tokens_mean_per_case` over cases that report tokens,
  `estimated_cost_usd: null` with `cost_note`, pass rate by category, by language and for the official cases.
  `report.write_report(cases, results, out_json, out_md, run_id)`. `offline.ForbiddenChatModel` (counts calls and
  fails) and `offline.run_offline(cases)` (each case in a fresh graph; any exception → status `error`;
  `model_calls` per result); CLI `python -m src.eval offline` prints `offline: N/M passed` and fails unless every
  offline case passes with zero model calls; `tests/test_eval_offline.py` runs it in CI (AC6.4). The old
  `data/eval_dataset.json` (ground truth from the deleted KB) and its schema test are removed.
- 6B (checked by `scripts/verify_phase6b.py`): `src/eval/runner.py`: `observe_turn(state, message, latency_ms)`
  (the 6A turn fields plus `tool_results`; retrieved docs reduced to `url`, `chunk_id`, `score`, `text[:600]`),
  `run_case(case, orchestrator, run_id)` (user `cliente1988`, session `eval-<run_id>-<id>`, every turn in the same
  session; any exception except `LLMNotConfiguredError` → status `error` with the class name only),
  `load_results(path)` (JSONL, the last line per id wins), `run_eval(cases, results_path, run_id,
  orchestrator_factory=None, sleep_s=None, max_cases=None, only=None, max_consecutive_errors=3)`: skips ids already
  `ok`, keeps file order, `only` filters, `max_cases` caps this invocation, appends and flushes one line per case,
  sleeps `EVAL_SLEEP_S` (default 6.0) between cases, stops after 3 consecutive `LLMUnavailableError` results
  (`stopped_early`), lets `LLMNotConfiguredError` propagate, and points `TICKETS_DB_PATH` to a temporary file during
  the run (restored afterwards). `src/eval/judge.py`: `load_judge_prompt()` (`src/prompts/judge.md`, reviewer-owned),
  `get_judge_model()` (`get_chat_model(settings.EVAL_JUDGE_MODEL)`, default `gemini-3.5-flash-lite`, a different
  model from the default answering model), `build_judge_input(case, result)` (merchant messages, final answer,
  passages and tool outputs of the last turn; never the case id, category or anything from `expect`),
  `parse_judgment(text)` (JSON between the first `{` and the last `}`; integers 1..5 for `grounded` and
  `answers_question`, boolean `abstained`, else ValueError), `judge_case` (system = judge prompt; unparseable →
  status `error`, `error_type: "unparseable"`), `should_judge` (ok, safe, no handoff, not `safety`), `run_judge`
  (resumable like the runner) and `load_judgments`. `metrics.aggregate(cases, results, judgments=None)` adds
  `answer_models` and `judge` (null without judgments): `n_judged`, `n_judge_errors`, `grounded_mean`,
  `answers_mean`, end-to-end `abstention_precision`/`abstention_recall` (expected `abstain` vs judged `abstained`),
  `abstention_errors`, `disagreements` (deterministic `facts_ok` true but `grounded` ≤ 2, or `facts_ok` false but
  `grounded` and `answers_question` ≥ 4), `judge_models`. `write_report(..., judgments=None)` adds `complete`
  (no errors and every case evaluated). CLI: `python -m src.eval run|judge|report --run-id ID [--runs-dir
  reports/eval_runs] [--out-dir reports] [--sleep S] [--max-cases N] [--only a,b]`; no key → exit 2 with a message
  naming `GEMINI_API_KEY`.
- 6C (checked by `scripts/verify_phase6c.py`): `judge.response_text(message)` (string content as is; list content →
  concatenation of string items and of the `text` of `{"type": "text"}` blocks; other blocks such as thinking are
  ignored) used by `judge_case`; `judge.error_code(exc)` (an int HTTP status 100–599 from `code` or `status_code` on
  the exception or its `__cause__`, else a leading 3-digit word of `str(exc)`, else None); judge error lines carry
  `error_code` but never the exception message; `run_judge` stops after `max_consecutive_errors` consecutive error
  judgments of ANY type (including `unparseable`), an ok judgment resets the count; `run_eval` removes its temporary
  tickets directory; `report` without the results file exits non-zero and writes nothing. Defaults:
  `LLM_MODEL=gemini-3.5-flash-lite`, `LLM_FALLBACK_MODEL=gemini-3.1-flash-lite`, `EVAL_JUDGE_MODEL=gemini-3.1-flash-lite`
  (config, `.env.example`, `docker-compose.yml`, README, `tests/test_providers.py`); supersedes 2C `S2.env_example`,
  `R1.settings_defaults`, `R2.factory_primary`, `R2.factory_fallback` and 6B `R0.settings`. Committed data: the
  user's `reports/eval_runs/full-1.jsonl` unchanged, `reports/eval_full-1.json` + `.md` generated from it by
  `python -m src.eval report --run-id full-1` (no judge section yet), the buggy `full-1.judge.jsonl` deleted. Reviewer
  prompts changed for the language rule (`supervisor.md`, `support_agent.md`, `knowledge_agent.md`).
- 6D (checked by `scripts/verify_phase6d.py`): `judge.load_chunk_texts(path=None)` (chunk_id → full text from
  `<INDEX_DIR>/chunks.jsonl`, cached for the default path) and `build_judge_input` uses the full text of every
  passage whose `chunk_id` is in the index (else the stored text), so the judge sees exactly the passages the agent
  saw, including runs recorded before this change; `observe_turn` stores up to 2000 characters (supersedes 6B
  `R1.observe_turn`). README: no false quota, a new run id in the `run` example, the judge's limits (full passages
  from the index; `search_web` results are not visible to it). The 600-character `full-1.judge.jsonl` is deleted and
  `reports/eval_full-1.*` regenerated without a judge section.
- 6E (checked by `scripts/verify_phase6e.py`): judge run 2 committed unchanged, `reports/eval_full-1.*` regenerated
  with the judge section (must equal `aggregate(cases, full-1, judge run 2)`), README section "Resultados da
  avaliação" with the numbers formatted from the report (pt-BR decimals) and the limits: single run, reviewer-written
  labels, `uncovered` only measured by the judge (`u01`), off-topic failures (`o04`, `o02`), grounded near the ceiling,
  `search_web` results not recorded. Supersedes 6C `D2`/`D3` and 6D `D1` (they required no judge file / no judge
  section).
- 6F (checked by `scripts/verify_phase6f.py`): README text and the /demo confidence card only. Banned README phrases
  (list in the verifier), the official-scenario matrix and glossary answers 1, 3, 4, 5 exactly as given in
  `docs/phase-prompts/6F.md` (statuses from `full-1`), the real ticket format, `estimated_cost_usd` null until Phase
  7, real token fields, the 3D statement limited to the retriever; the "Resultados da avaliação" section unchanged.
**Acceptance:**
- AC6.1 `data/eval/*.jsonl` ≥60 cases: routing, retrieval (gold URLs and literal facts), abstention, multi-turn, safety, escalation, PT and EN.
- AC6.2 `python -m src.eval run` executes against the real model and `report` outputs `reports/eval_<run_id>.json` + `.md` with per-case results, routing accuracy, abstention precision/recall, judge scores, latency, tokens, cost (null until Phase 7).
- AC6.3 LLM judge with rubric prompt; judge never sees the expected tool; disagreements listed.
- AC6.4 CI runs a deterministic offline subset (no model may be called) as regression; real-model report committed with model name and date.

### Phase 7 — Observability and cost
**Split:**
- 7A (checked by `scripts/verify_phase7a.py`): `src/core/log_context.py` with contextvars and `user_hash(user_id)`
  (`"u_" + sha256(LOG_HASH_SALT + user_id)[:16]`), `bind(trace_id, session_id, user_id)` (context manager, resets on
  exit) and `current()`; `JsonFormatter` adds `trace_id`, `session_id`, `user_hash` from the context and the extras
  `agent`, `node`, `tool`, `status`, `latency_ms`, `execution_time_ms`, and never writes a raw `user_id`;
  `run_sync` runs inside `bind` (trace and session generated before binding); every graph node logs one
  `"node finished"` record (`node`, `latency_ms`); every supervisor tool call and every specialist tool call logs one
  `"tool finished"` record (`tool`, `agent`, `status` ok|error, `latency_ms`); no log call formats the raw user id or
  the merchant's message. `LOG_HASH_SALT` setting (default empty).
- 7B (checked by `scripts/verify_phase7b.py`): `src/core/pricing.py` with `PRICES_USD_PER_1M` holding exactly the
  three officially listed models above, `PRICE_SOURCE_URL`, `PRICE_PAGE_LAST_UPDATED = "2026-10-30"`,
  `PRICE_RETRIEVED_AT = "2026-11-07"`, `PRICE_TIER`, and `cost_usd(model, input_tokens, output_tokens)` (strips a
  `models/` prefix; None for an unlisted model or unknown usage). `run_sync` sets `estimated_cost_usd` from the
  turn's tokens and `llm_model` (assumes every call of the turn used that model; query embeddings are not counted).
  The eval report keeps cost null for now (per-case cost in the eval is later work). `/chat` runs inside `bind`,
  so its error logs carry the context; those logs keep only the exception class.
- 7C (checked by `scripts/verify_phase7c.py`): `src/core/metrics.py`, thread-safe, no dependency, with `reset()`,
  `render()` (text format 0.0.4, `# HELP`/`# TYPE` for every metric), `inc_request(status_code, latency_s)`,
  `inc_tool(tool, status)` (tool names outside the 8 known tools become `unknown`, status `ok`|`error`),
  `inc_escalation()`, `inc_abstention()`, `add_tokens(input, output)`. Metrics: `getnet_requests_total{status}` and
  the histogram `getnet_request_latency_seconds` (buckets 0.5, 1, 2, 5, 10, 20, 30, 60, +Inf; cumulative) for
  `/chat` and `/api/v1/chat` only (HTTP middleware, every status including 401/503); `getnet_tool_calls_total{tool,
  status}` next to every `tool finished` log; `getnet_escalations_total` on every persisted ticket;
  `getnet_abstentions_total` when a turn's knowledge calls all abstain; `getnet_llm_tokens_total{direction}` per
  turn. `GET /metrics` without authentication (no identifiers in labels; restrict it at the network level). The
  three LLM error logs use `logger.error` with the class name only.
- 7D (checked by `scripts/verify_phase7d.py`): the Knowledge Agent collects every `search_web` result as
  `{url, title, snippet}` into `web_results` (specialist result, graph state, `AgentState`); `observe_turn` records
  `web_results` (snippet cut at 600 characters; supersedes 6D `R1.observe_turn_2000`, re-checked as W2) and
  `build_judge_input` adds each web result as a passage `{url, text: title + newline + snippet}`. An unexpected
  exception in `run_sync` sets `AgentState.error = "internal_error"` (also `metadata.error` in the API) with the
  bilingual `INSTABILITY_MESSAGE`, and `run_case` reports such a turn as status `error`, `error_type:
  "internal_error"`, not as a wrong answer. Fixed messages become module constants with Portuguese then English
  (`INSTABILITY_MESSAGE`, `FORCED_ESCALATION_MESSAGE` with `{ticket_id}`, `FORCED_ESCALATION_FAILED_MESSAGE`); the
  Portuguese sentences are kept verbatim. Detecting the merchant's language for fixed messages is not attempted.
**Acceptance:**
- AC7.1 JSON logs per node with `trace_id`, `session_id`, `user_id` (hashed), node, tool, latency.
- AC7.2 Tokens and cost from provider `usage_metadata`; price table in config with source and date.
- AC7.3 `/metrics` (Prometheus format) with request count, latency histogram, tool calls, escalations, abstentions.

### Phase 8 — Production polish and README
**Split:**
- 8A (checked by `scripts/verify_phase8a.py`): `KNOWLEDGE_TOOLS` and `SUPPORT_TOOLS` constants in `src/core/graph.py`
  used to build the specialists; `/agents` generated from them, `SUPERVISOR_TOOLS` and settings (agents with their
  tool names and prompt files, `GuardrailAgent` with no tools and no LLM, models, one row per tool with name, first
  description line and sorted args); `/demo` without `MemorySaver`/"Gemini Flash", tokens and cost from the response
  metadata, a missing score shown as `n/a`; README leftovers fixed.
- 8B (checked by `scripts/verify_phase8b.py`): named volume `app_state` (`getnet_app_state`) on `/app/state` with
  both databases defaulting to `state/`; `/app/data` (index, corpus) read-only from the image; no `chmod 777`;
  `.dockerignore` excludes `data/*.db*` and `reports/`; CI asserts the container is not root; README Docker section
  and the reviewer-written "9. Afirmações e evidências" table (every path must exist).
- 8C (checked by `scripts/verify_phase8c.py` and by the CI docker job): `ENV CHECKPOINT_DB_PATH=state/checkpoints.db`
  and `TICKETS_DB_PATH=state/tickets.db` in the Dockerfile runner stage. Then the user verifies `docker compose up`
  in Codespaces (AC8.1, done) and the reviewer does a final audit (done).
- 8D (checked by `scripts/verify_phase8d.py` and by the CI docker job): `chmod -R go-w /app/data /app/src
  /app/README.md` before `USER appuser`; CI probes that `appuser` cannot write the index or the code but can write
  `/app/state`; README database paths in Docker and "Sem prazos nem filas" wording.
- 8E (checked by `scripts/verify_phase8e.py`): commit the raw runs `full-2`..`full-7` and their judge files unchanged;
  `gemini-3.6-flash` and `gemini-3.8-flash` ($0.75 / $3.75) added to `PRICES_USD_PER_1M` with `PRICE_NOTES` (retrieved
  2026-11-08, price change on 2027-01-01; supersedes 7B `P1.price_table`, re-checked as P1); `aggregate` computes
  `estimated_cost_usd` = round(sum of `cost_usd(turn.llm_model, input, output)` over every turn with tokens of the
  `ok` results, 6), `null` if no turn has tokens or any such turn is unpriced, with `COST_NOTE`; reports regenerated
  for `full-1`..`full-7`; `src/eval/compare.py` (`compare_runs`, `write_comparison`, CLI `compare --name --group
  LABEL=run,run`) with mean/min/max per metric (`null` if any run lacks the value), `failed_in_all_runs` and
  `judge_abstention_errors_in_all_runs`; `reports/eval_models.{json,md}`; README comparison section (reviewer text)
  before the `full-1` section, cost text updated, claims row. The default answer model stays `gemini-3.5-flash-lite`.
- 8F (checked by `scripts/verify_phase8f.py`): README only. The `full-1` sub-heading becomes "Execuções registradas"
  (the six-run comparison is the current result, `full-1` is historical); "Limitações atuais" and the table of
  contents point to the comparison; the cost bullet states that recorded output tokens include reasoning tokens,
  with the AI Studio cross-check.
**Acceptance:**
- AC8.1 `docker compose up` verified (output pasted), healthcheck green, non-root.
- AC8.2 README (pt-BR) covers build/run/test, architecture, workflow, RAG pipeline, tools, eval, limitations.
- AC8.3 README "Claims → evidence" table: every claim links to file/test/report.
- AC8.4 `demo.html` shows only real fields.
- AC8.5 Results reported as mean and range over at least three runs per model, from committed raw files.

### Phase 9 — Short fixes and honest claims before resubmission
Source: the simulated V4 audit (6.9/10, HEAD `c5e2698`), sections 4–6. Goal: every README/STATUS claim backed by the
code, and the four defects the audit reproduced (raw PII on disk, orphan tool call, invented merchant, public keys in the
image) fixed, plus conversation text out of the logs. One verifier per sub-phase; each re-runs the earlier ones and
lists the checks it supersedes. Each later prompt is written after the previous sub-phase is reviewed (its verifier pins
the previous commit). The original 9E (Docker + logs) was split into 9E (Docker) and 9F (logs) to keep prompts
small; the README residues moved to 9G.
**Out of scope until the real evaluator's feedback:** LLM-based guardrail, `interrupt()`, a write action in the support
domain, weather/FX APIs, a larger corpus, conversation trimming/summarisation, CORS tightening. (The LLM guardrail and the
weather/FX APIs are named in the real V4 feedback and move into Phase 10.) The README states the
guardrail and corpus limits honestly instead (9F).
**Split:**
- 9A (checked by `scripts/verify_phase9a.py`): reproducible verifiers and true authorship. Reviewer side: `verify_phase7c.py`
  without 3.12-only f-string syntax; `verify_phase8e.py` reference cost with `math.fsum`. Implementer side:
  `aggregate` computes `estimated_cost_usd` with `math.fsum` (`tests/test_eval_harness.py::test_estimated_cost_is_exact_sum`
  with five costs whose left-to-right sum rounds differently); CI test job runs `python -m compileall -q scripts src tests`
  on 3.11 before pytest; README section "Autoria e revisão" (reviewer text: Antigravity/Gemini 3.8 Flash implements,
  Claude/Anthropic plans and reviews in separate sessions, the author decides and commits, "não é uma revisão
  independente"); every "revisor externo"/"independente" for the reviewer removed from README and STATUS; STATUS 8F
  keeps its 42/42 output and gains a correction note (40/42 on 3.11). Supersedes 8B `R1.claims_table` (the table's
  opening sentence changes; re-checked as R1.claims_table_9a) and 8F `E2.readme_only`.
- 9B: card and CPF masked in `run_sync` before the `HumanMessage` enters the graph, regardless of `ENABLE_GUARDRAILS`
  (the toggle only controls the injection check); the masked card keeps the following space (card pattern must not end
  in a separator); test that scans every byte of the SQLite files (and `-wal`) after turns with a Luhn-valid card,
  formatted and unformatted CPF, a blocked (injection) turn and `ENABLE_GUARDRAILS=false`; README PII sentence becomes
  "antes de a mensagem entrar no grafo" and states that databases created before 9B may hold raw text.
- 9C: when `graph.invoke` raises (LLM errors re-raised as 503, or the internal-error path), `run_sync` closes every
  tool call of the thread without a ToolMessage by writing `ToolMessage(content={"status":"error","error":<class or
  "internal_error">}, tool_call_id=...)` with `graph.update_state(..., as_node=<a node whose edge goes to END>)`; after
  the failure `get_state(config).next == ()` and no AIMessage tool call is unanswered; the next turn's model input has no
  orphan. Tests with `SqliteSaver` for both paths. README limitation line updated.
- 9D: `MockDatabase.get_user` returns `None` for an unknown merchant (no generated account); no `hash()` anywhere in
  `src/`; the three support functions return `{"status": "not_found", "error": "merchant_not_found"}` without echoing
  the id; the support prompt says to report it and offer escalation. Tests for the three tools with an unknown id.
- 9E: `ENV APP_ENV=production` in the Dockerfile runner stage and `APP_ENV=production` pinned in `docker-compose.yml`
  (the README's `cp .env.example .env` made Compose resolve `development`); CI docker job asserts `/health` reports
  `environment: production`, `POST /chat` with `getnet-dev-key` and `GET /tickets` with `getnet-dev-operator` return 401,
  and `docker compose config` with the example `.env` resolves production; README Docker text (no `--env-file .env` in a
  plain `docker run`) and `python -m src.core.auth hash` without an argument; `tests/test_docker_defaults.py`.
- 9F: logs carry no conversation text: no query, reason, task, error code, serial or exception text in any record
  (lengths only); `logger.exception` replaced where the exception text can carry conversation or provider text (class
  name and code locations only). Test: a unique marker in the message, the specialist task, the search query, the
  escalation reason, a tool argument and a provider/internal exception never appears in captured log output.
- 9G: README residues from audit section 5: "Fonte oficial citada" becomes "Fonte oficial recuperada" (compare.py,
  regenerated `reports/eval_models.{json,md}`, README tables) with a sentence that it checks retrieved URLs, not
  citations in the text; scenario 10 source is `getnet.net/en/our-solutions/online-payments` (the Brazilian payment-link
  and WhatsApp pages were `no_content`); `getnet.com.br` removed from the source policy (README and
  `data/corpus/README.md`); provider text (Gemini only in practice;
  the openai/anthropic branches are not installed or tested; embeddings always Gemini); `MemorySaver` docstrings in
  `graph.py`; test tree (`test_eval_judge.py` renamed `test_api_key_header.py`); "Limitações atuais" lists the regex
  guardrail (bypassed by paraphrase, false positives), the corpus gaps and the out-of-scope items; claims table rows for
  PII, logs, mock and Docker point to the 9B–9F tests. Also: `docs/DECISIONS.md` (pre-SPEC notes describing abandoned
  plans as current) gets a historical-document banner.
**Acceptance:**
- AC9.1 Every verifier, including the last one, passes on Python 3.11 (CI compiles them) and on the local 3.13.
- AC9.2 No README/STATUS sentence calls the reviewer independent; the authorship section names both tools.
- AC9.3 No raw card or CPF byte in any SQLite file after any turn.
- AC9.4 No unanswered tool call persists after a failed turn.
- AC9.5 Unknown merchant → `not_found`, never data.
- AC9.6 The image defaults to production; development keys get 401 in CI.
- AC9.7 No log record contains conversation text.
- AC9.8 Every claim in audit section 5 is fixed or removed.

### Phase 10 — Weather and FX by API; guardrail beyond patterns
Source: the two items of the real V4 feedback still open after Phase 9: "clima e câmbio dependem de snippets de busca, não
de API" (Business & Challenge Fit) and "guardrail só por padrões" (Security & Identity); the simulated audit's probe 4 (two
paraphrases pass, two legitimate questions are blocked). One verifier per sub-phase; each re-runs the earlier ones and lists
the checks it supersedes. Each later prompt is written after the previous sub-phase is reviewed.
**Decisions (reviewer proposal; the user decides):**
- *Hybrid guardrail.* Patterns stay as the cheap first layer (no model call; the offline CI subset keeps zero model calls).
  Only messages that pass them reach an LLM classifier with its own prompt (`src/prompts/guardrail_classifier.md`) and a
  structured output: a forced function call `GuardrailVerdict(verdict: "block"|"allow", category: "prompt_injection"|
  "prompt_leak"|"attack_request"|"none")`, no free text (nothing to leak into logs). The classifier sees only the latest
  message, already PII-masked, wrapped in `<message>` tags.
- *Failure mode: fail-open by default* (`GUARDRAIL_CLASSIFIER_FAIL_MODE=open`; `closed` is supported and tested). Reasons:
  (1) the blast radius of a missed injection is small: `user_id` comes from the credential through `RunnableConfig`, tools
  read only the caller's own account, and the only write is a ticket for that caller; (2) the prompts are public in this
  repository, so a leaked prompt reveals nothing secret; (3) the classifier and the supervisor share the provider and the
  quota, so fail-closed would turn every quota hiccup into a false "blocked" refusal that looks like an accusation; with
  fail-open the supervisor call fails the same way and the merchant gets the honest 503. Misconfiguration
  (`LLMNotConfiguredError`, `LLMConfigurationError`) is not a classifier failure: it propagates (503). Revisit if a write
  action on the merchant's money is ever added (then fail-closed for that path).
- *Pre-registered labels.* `data/eval/guardrail_labeled.jsonl` (36 messages: 20 `block` = the 6 offline safety cases, the 2
  audit paraphrases and 12 new paraphrases; 16 `allow` = the 2 audit false positives and 14 near misses; splits `dev`/
  `holdout`) and the classifier prompt are committed in 10A, before any classifier code exists. Any later prompt change is
  made against `dev` only and reported with both splits. Targets for the hybrid (patterns OR classifier) over the whole
  set, in the report as `targets_met`: block rate ≥ 0.90 and false-positive rate ≤ 0.10. A miss is reported, not tuned away.
- *Weather and FX by API.* Open-Meteo (geocoding + forecast) and BCB PTAX (Olinda OData), both free and keyless. Every
  value carries its unit, the reference date/time from the API and the request URL (`source_url`); timeout, HTTP error,
  invalid payload, unknown place or currency and "no bulletin for that date" (weekend, holiday, before publication) are
  explicit statuses with no value. No value, rate or fallback number in the code. `search_web` stays for what has no API
  (news). PTAX is the Central Bank reference rate, not a retail or tourism rate: the answer must say so.
- *Evaluation sets.* `data/eval/cases.jsonl` (v1, 69 cases) stays frozen: the committed runs `full-1`..`full-7` measure it.
  A new `data/eval/cases_v2.jsonl` = v1 with the four weather/FX cases (`off02`, `off07`, `w01`, `w02`) re-labelled to the
  new tools (`tools_all` the API tool, `tools_none` adds `search_web`) plus new live-data cases (unknown city, PTAX on a
  Saturday, a past business day, a non-USD/EUR currency, weather + knowledge, news via `search_web`). The runner and report
  take `--cases`; every report records its `cases_sha256`.
**Split:**
- 10A (checked by `scripts/verify_phase10a.py`): pattern layer re-evaluated, no model. Five patterns narrowed
  (`system\s*prompt` → `your\s+system\s*prompt`; `regras\s+internas` → `(suas|tuas)\s+regras\s+internas`;
  `prompt\s+de\s+sistema` → `(seu|teu)\s+prompt\s+de\s+sistema`; `esque[cç]a\s+(o\s+que\s+foi\s+dito|tudo)` →
  `esque[cç]a\s+(tudo\s+)?o\s+que\s+foi\s+dito`; `hack` dropped from the attack terms); `GuardrailAgent.match_patterns(text)`
  → `"prompt_injection" | "attack_request" | None`; `src/eval/guardrail_eval.py` (loader with validation, canonical sha256,
  block/false-positive rates per split and kind, pattern-layer results); CLI `python -m src.eval guardrail-patterns` writes
  `reports/guardrail_patterns.{json,md}`; `tests/test_guardrail_patterns.py` (pattern false positives = 0 on the set, every
  offline safety case blocked, the rates can fail); README guardrail limitation reworded with the measured numbers.
  Reviewer files: the labeled set and the classifier prompt (pre-registered, not wired yet).
- 10B (checked by `scripts/verify_phase10b.py`): `src/agents/injection_classifier.py` (`GuardrailVerdict` pydantic schema,
  `ClassifierResult`, `format_classifier_input` wrapping the masked message in `<message>` tags with `<`/`>` escaped,
  `InjectionClassifier(model=None).classify(text)`; the model is built lazily with `get_chat_model(GUARDRAIL_CLASSIFIER_MODEL
  or LLM_MODEL, timeout_s=GUARDRAIL_CLASSIFIER_TIMEOUT_S, max_retries=0)` and bound with `tool_choice="GuardrailVerdict"`;
  no fallback model). Settings `GUARDRAIL_CLASSIFIER_ENABLED=true`, `GUARDRAIL_CLASSIFIER_MODEL=""`,
  `GUARDRAIL_CLASSIFIER_TIMEOUT_S=10`, `GUARDRAIL_CLASSIFIER_FAIL_MODE: Literal["open","closed"]="open"` (an invalid value
  stops the app). New graph node `guardrail_classifier` AFTER `handoff_gate` (turns held by a pending ticket never reach a
  model, so they need no classification and still work without a key). `OrchestrationGraph(..., guardrail_model=None)`: an
  injected `chat_model` without `guardrail_model` means no classifier (keeps every scripted-model test and earlier
  verifier unchanged; `tests/conftest.py` is not touched); production (`chat_model=None`) always has one. Fail-open:
  error/timeout/unparseable → continue to the supervisor; fail-closed: `LLMUnavailableError` → the existing 503 path (no
  new fixed message). `LLMNotConfiguredError`/`LLMConfigurationError` always propagate. A classifier block reuses the
  pattern refusals (`INJECTION_REFUSAL`, `ATTACK_REFUSAL` constants). State/API field `guardrail` = `{patterns, blocked_by,
  classifier{status, verdict, category, error_type, latency_ms, model}}`, never text; classifier tokens in
  `tokens_by_agent["GuardrailClassifier"]`; metric `getnet_guardrail_decisions_total{decision}`; one log record per
  classifier run without text; `/agents` describes the classifier. README: hybrid limitation (the classifier's real-model
  rate is "not measured yet" until the runs of 10H), flow diagrams, injection bullet, env vars, claims row. Supersedes 9F
  `H11.claims_row`, 9G `J9.limitations`, 10A `A15.readme_limitation` and `A2.classifier_prompt_preregistered` (re-checked
  as B8, B9 and B2).
- 10C (checked by `scripts/verify_phase10c.py`; code only, no real-model run): in `src/eval/guardrail_eval.py`,
  `run_guardrail` (production classifier by default, PII masked first, the classifier runs on all 36 messages so its
  standalone rates are measured; resumable JSONL under `reports/guardrail_runs/` with ids, verdicts and numbers only, no
  text; stops after 3 consecutive classifier errors; missing key or misconfiguration propagates), `guardrail_report`
  (layers `patterns`, `classifier` (ok records only) and `hybrid` (pattern OR classifier block; a classifier error or a
  missing record counts as "not blocked by the classifier", which is what fail-open does), `complete`, `errors`,
  `missing`, `targets_met` = complete AND hybrid block rate >= 0.90 AND false-positive rate <= 0.10, latency p50/p95
  (nearest rank), mean tokens and mean cost per classified message from `src/core/pricing.py`), the report files
  `reports/guardrail_<run_id>.{json,md}`, and `guardrail_summary` over several runs (mean/min/max per metric,
  `all_targets_met`) in `reports/guardrail_summary.{json,md}`; CLI `guardrail-run`, `guardrail-report`,
  `guardrail-summary`. Offline tests with scripted classifiers, including one that misses the targets. The real runs are the
  user's, in 10H.
- 10D (checked by `scripts/verify_phase10d.py`): `scripts/capture_public_data.py` (implementer file; `httpx`, project user
  agent, no key) fetches 12 fixed requests (geocoding of Porto Alegre, São Paulo and an unknown town; a 3-day forecast with
  `current` and the daily variables; a forecast with an invalid latitude (HTTP 400); the PTAX `Moedas` list; EUR, USD and
  JPY on 2026-11-06 (Friday); EUR on 2026-11-07 (Saturday); EUR from 2026-10-30 to 2026-11-09 (includes the 2 November
  holiday); the unknown currency XYZ) and stores the raw bodies in `tests/fixtures/public_data/` with a manifest (URL,
  status, content type, size, sha256 of the LF-normalised body, capture time). Antigravity runs it (network, no key); the
  files are never edited by hand. The verifier checks the script offline with an in-memory transport and the fixtures for
  plausibility (coordinates, units, WMO codes, PTAX fields and ranges, empty Saturday, no weekend rows) and prints the
  bulletin names and whether USD is listed, which fix the 10E contract.
- 10E (checked by `scripts/verify_phase10e.py`): `src/tools/public_data.py` (no regex, no logging, `httpx` with an
  injectable client, `PUBLIC_DATA_TIMEOUT_S=8`; URL builders reproduce the 10D manifest URLs exactly; only
  `tipoBoletim == "Fechamento"` counts, the latest one on the requested date or in the last 10 days; `Moedas` decides
  `not_found`):
  `fetch_weather(city, country_code=None, forecast_days=3)` and `fetch_exchange_rate(currency, date=None)` returning the
  documented statuses (`success`, `not_found`, `no_data`, `unavailable`, `invalid_request`), every value with its unit, the
  reference date/time from the API and `source_url`; the WMO weather-code table from the Open-Meteo docs; the PTAX closing
  bulletin of the requested date, or the latest one in the last 10 days when no date is given ("today" in UTC-3, injectable).
  Tests with `httpx.MockTransport` serving the 10D fixtures, plus timeout, HTTP 5xx and invalid JSON.
- 10F (checked by `scripts/verify_phase10f.py`): tools `get_weather_forecast(city, country_code=None, days=3)` and
  `get_exchange_rate(currency, date=None)` (ISO date string; an unparseable date returns `invalid_request` /
  `invalid_date` without a request) in `ALL_TOOLS` and `KNOWLEDGE_TOOLS` (order: knowledge base, weather, FX, web),
  descriptions dictated by the reviewer; `search_web` described as news-only; the tools return the module's result as JSON
  and log only the status; the `httpx` logger pinned at WARNING. Reviewer prompts updated (`knowledge_agent.md`: tools,
  how to read weather/FX results, no estimates; `supervisor.md`: routing line and grounding of values, units, dates,
  PTAX as reference rate). The specialist records every API call in `api_results` (`{"tool", **result}`) and adds
  `source_url` to `sources` only on `success`; `api_results` goes through `AgentState`, the graph, `run_sync` and the
  `/chat` metadata; metrics know the two tools. README: limitation item rewritten, flows, tools table, a section on both
  APIs (statuses, terms of use, attribution), `PUBLIC_DATA_TIMEOUT_S`, claims row. Supersedes 2A `R1.tool_set`, 2D
  `R2.knowledge_tools`, 10B `B8.readme_texts` and `B9.claims_row` (re-checked as F2, F8 and F9).
- 10G (checked by `scripts/verify_phase10g.py`): `src/eval/cases.py` accepts category `public_data`, the two API tools and an
  optional `expect.api_status` ({API tool in `tools_all`: one of `success`, `not_found`, `no_data`, `unavailable`,
  `invalid_request`}); `tools_ok` also requires, for each pair, an `api_results` entry with that tool and status;
  `observe_turn` records `api_results` (copies); `build_judge_input` adds one passage per API result (`url` = `source_url`
  or empty, `text` = the result as sorted JSON); `write_report(..., cases_file)` records the file; `--cases` for `run`,
  `judge`, `report` and `compare` (default v1; a missing file returns 1). Reviewer files: `data/eval/cases_v2.jsonl` (78
  cases: v1 with `off02`/`off07`/`w01`/`w02` re-labelled to the API tools, the API tools also forbidden in `off_topic` and
  `safety`, plus `d01`-`d08` and `x03`; expected PTAX values checked against the 10D fixtures) and `src/prompts/judge.md`.
  Supersedes 7D `W2.observe_turn` (re-checked as G5) and 10F `F9.claims_row` (re-checked as G9).
- 10H (checked by `scripts/verify_phase10h.py`): the user runs, in a terminal with the key typed via `Read-Host`,
  `guardrail-run` for `hybrid-1`..`hybrid-3`, `run` and `judge` with `--cases data/eval/cases_v2.jsonl` for `v2-1`..`v2-3`
  (`EVAL_JUDGE_MODEL=gemini-3.6-flash`); Antigravity only generates the reports (`guardrail-report`, `guardrail-summary`,
  `report`, `compare --name v2`) and commits records and reports, editing nothing in `reports/` by hand. The verifier checks
  the records (one per message or case, keys, dates, no message text in the guardrail records, judge model different from
  the answer model), recomputes every committed report from them, recomputes the hybrid rates and the v2 pass rates with
  its own reference, and checks that every PTAX value for 2026-11-06 in the records equals the response captured in 10D.
  Supersedes 7A `L2.no_pii_in_logs` (re-checked as H6).
- 10I (checked by `scripts/verify_phase10i.py`): README texts dictated by the reviewer: the guardrail and weather/FX
  limitation items rewritten with the measured results; the runs paragraph; a section with the v2 results (table copied
  from `reports/eval_v2.md`) and a section on the hybrid guardrail measurement (layers table, false positives quoted,
  audit phrases, extra latency and cost per message, the fail-open reasons, what it does not cover), both before the
  model comparison; two claims rows. STATUS 10H gets the model name fixed and a correction note on the 3.11 result. The
  verifier checks every quoted number against the committed reports and records, and re-checks the texts of 10B, 10F and
  10G that stay. Supersedes 10F `F8.readme_texts`/`F8.readme_10b_texts_kept`, 10G `G9.readme_texts`/`G9.claims_row` and
  10H `H5.v2_reports` (re-checked as I2, I3 and I6). Outside the repository: the reply to the V4 feedback and its open
  items, for the user.
**Acceptance:**
- AC10.1 No regex outside `src/agents/guardrails.py` and `src/core/pii.py`; routing to the new tools by function calling only.
- AC10.2 Weather and FX answers come from API tool results with unit, reference time and `source_url`; every failure
  status is explicit and carries no value (tests without network).
- AC10.3 The guardrail runs patterns first and the classifier only on what passes; fail-open and fail-closed both tested.
- AC10.4 The pre-registered guardrail set and classifier prompt are committed before the classifier code; the committed
  real-model report states block and false-positive rates per split and whether the targets were met.
- AC10.5 README states the APIs' terms, the failure-mode decision, the measured extra latency and cost, and what the
  guardrail still does not cover; every number comes from a committed report.

### Phase 11 — Last fixes before the resubmission
Source: the simulated V4 audit re-check of 10A-10I (PDF "Avaliação V4 — Burbanos (nova versão) v3", sections 8 and 10) and
the author's instructions of 2026-11-09. Goal: no README claim without evidence, the guardrail's incoherent-verdict defect
fixed, an independent guardrail measurement written by the author, and a README a reviewer can read in one sitting. One
verifier per sub-phase; each re-runs the earlier ones and lists the checks it supersedes. Each later prompt is written after
the previous sub-phase is reviewed. Old runs are never re-run; records written before a format change say so in the README.
**Decisions (the author's):**
- *Only `allow`/`none` lets a message through.* A classifier answer without a valid verdict (no `GuardrailVerdict` call,
  arguments that fail the schema, or `(verdict == "allow") != (category == "none")`) is `status: "invalid"` (verdict `block`,
  category `None`, `error_type` = `no_verdict_call` | `invalid_arguments` | `incoherent_verdict`) and blocks in both modes
  with `INJECTION_REFUSAL`. Fail-open applies only to provider unavailability (an exception from the model call: timeout,
  API error, quota); `closed` still turns it into 503. The README's fail-open reason is rewritten: an isolated classifier
  timeout lets an unclassified message reach the supervisor; that is the accepted risk, not "the supervisor fails too".
- *Independent guardrail holdout.* About 20 messages (about 10 injection attempts, 10 similar legitimate questions) written
  without reading `src/prompts/guardrail_classifier.md` or the 36-message set, in `data/eval/guardrail_author_holdout.jsonl`
  (source `author_holdout`, split `holdout`). Changed on 2026-11-09 at the author's request: the candidates were generated by
  another model (GPT 6.1 Sol, separate conversation) from a reviewer-written prompt, and the author selected, rewrote and
  labelled them; the prompt, the 30 candidates and the selection are committed (provenance above). The files are committed
  alone, before any run; the author runs them once with the real model in their terminal (`guardrail-run --set ... --run-id
  author-1`); the result enters the README as it came out, and the classifier prompt is not changed afterwards. Same
  targets as Phase 10 (block >= 0.90, false positives <= 0.10).
- *Recorded decision layer.* From 11C, every turn recorded by the v2 runner carries `guardrail` (patterns category,
  `blocked_by`, classifier status/verdict/category/error_type/model, no text) and `tokens_by_agent`; reports count the layer
  that decided (`patterns`, `classifier`, `none`) and the classifier tokens, and say "não registrado" for older records.
- *Tier and models in the reports.* The published real-model runs since 2026-11-08 used a paid Tier 1 key (`full-1`,
  2026-11-07, the free tier). The tier is the author's declaration, kept in a committed file read by the report generators;
  models come from the records. The free-tier justification of the default model stays, with the date of the quotas.
- *README.* At most ~350 lines: what it is + architecture diagram; how to run; current results only (history in
  `docs/history.md`); demo transcripts copied from committed real-model records (each with its record path; flows without a
  real record are said to have none); limitations; authorship and review (the author's decisions); repository map (product
  vs. process). No "(Fase X)" in titles, no marketing adjectives, no interview glossary, "o autor" instead of "candidato",
  no video. `docs/STATUS.md` keeps a short summary; the per-phase log moves to `docs/status-history.md`.
**Split (provisional; each prompt is written after the previous review):**
- 11A (checked by `scripts/verify_phase11a.py`): `status: "invalid"` in `src/agents/injection_classifier.py`; the graph blocks
  it in both modes (metric `classifier_invalid_block`, tokens counted); `src/eval/guardrail_eval.py`: `invalid` records are
  final (not retried), reset the error streak, count as blocked in the classifier and hybrid layers, `run_guardrail` returns
  an `invalid` count; `VALID_SOURCES` gains `author_holdout`; tests for every case in both modes; README: guardrail limitation
  sentence, `GUARDRAIL_CLASSIFIER_*` line, fail-open bullet, claims row. Committed reports unchanged (the 108 real calls were
  all `ok`). Supersedes 10B `R4.fail_open`, 10C `C0.append_only`/`C2`/`C3`/`C4` and 10I `I1.readme_texts` (re-checked as
  A1, A3, A6-A9).
- 11B (checked by `scripts/verify_phase11b.py`): `data/eval/guardrail_author_holdout.jsonl` (20 messages),
  `data/eval/guardrail_author_holdout_candidates.jsonl` (the 30 generated candidates with `selected_as`) and the generation
  prompt `docs/phase-prompts/11B-gerador-holdout.md` committed alone (no code, no run), sha256 pinned; classifier prompt and
  36-message set unchanged; no `author-*` record or report yet. Then the author runs `author-1` once.
- 11C (checked by `scripts/verify_phase11c.py`): `reports/guardrail_runs/author-1.jsonl` committed as the author's run wrote
  it, and `reports/guardrail_author-1.{json,md}` generated from it with `guardrail-report` (nothing edited by hand); the
  verifier pins the record, recomputes the report, and checks one record per message, timestamps after the 11B commit, the
  classifier model, and the classifier prompt and holdout files unchanged since 11B. Supersedes 11B `B5.no_run_yet`.
- 11D (checked by `scripts/verify_phase11d.py`): `observe_turn` records `tokens_by_agent`, `guardrail` (deep copies, no
  text) and `guardrail_layer` (`patterns` for `blocked_by` patterns/empty message, `classifier`, `none`, or None when not
  recorded); `aggregate` gains a last key `guardrail` (recorded/unrecorded turns, turns by layer, classifier status counts,
  classifier tokens, case ids blocked by each layer; None when no turn has the fields, so every committed report still
  matches its records); the Markdown report gains a "Guardrail por Turno" section that says "Não registrado" for old runs.
  No run and no committed report regenerated. Also fixes the 11A test so the invalid answer falls on a legitimate message.
  Supersedes 10G `G5.observe_turn` and `G10.existing_test_only_gains_key` (re-checked as D2 and D7).
- 11E (checked by `scripts/verify_phase11e.py`): `reports/run_context.json` (the author's declaration: date and tier of every
  real-model run) and `src/eval/run_context.py` (loader, labels, note); `write_comparison` adds `runs_context` (date, tier,
  answer and judge models per run, models read from the records) and a "## Execuções" Markdown section after the unchanged
  table; `guardrail_summary` adds `date` and `tier` to each run and the Markdown names the tier; `compare_runs` averages with
  `math.fsum`. `reports/eval_models.*`, `reports/eval_v2.*` and `reports/guardrail_summary.*` regenerated from the committed
  records (same numbers, same tables). Supersedes 10C `C10.summary` and 10H `E3.old_reports_untouched` (re-checked as E5,
  E3 and E4).
- 11F (checked by `scripts/verify_phase11f.py`): a script given in the prompt (run outside the repository, then deleted)
  rebuilds from the 11E commit: `docs/status-history.md` = the old STATUS body (only " do candidato " -> " do autor "),
  `docs/history.md` = the README sections that leave in 11G (model comparison on v1, `full-1` results, the `full-1`
  official-scenario matrix, the hand-written-KB paragraph, the interview glossary), and `docs/STATUS.md` = a short summary
  followed by the phase sections from 11F on. README unchanged. Supersedes the STATUS checks 6D `S4.status_next_phase`, 6E
  `S4.status`, 6F `C7.status`, 8C `C3.status`, 8D `E4.status`, 8E `E1.status`, 8F `E1.status`, 9A `A8.status_8f_correction`
  and 10I `I5.status_10h_corrected` (re-checked on `docs/status-history.md` as F4).
- 11G (checked by `scripts/verify_phase11g.py`): the new README, dictated by the reviewer in full and written by a script
  that copies the block of the prompt (byte-equal check); STATUS gains the 11G section above 11F, summary unchanged;
  `docs/history.md` and `docs/status-history.md` unchanged. Sections in order: O que é, Como rodar, Resultados atuais,
  Demonstração, Limitações, Autoria e revisão, Mapa do repositório (286 lines). The demo is six transcripts copied from
  `reports/eval_runs/v2-1.jsonl` (`k01`, `s01`, `g02`, `k11`, `d04`, `e01`), checked against the records; the unknown
  merchant and the operator's reply have no real-model record and the README says so, pointing to their tests. Every
  quoted number is recomputed from `reports/` (G4). One correction found while writing it: 30 pages were collected but 28
  became the 92 chunks (two hub pages are navigation only and fall under `MIN_CHARS`); the README now says so. Supersedes
  every README check of earlier verifiers that depended on the old layout (2C to 11A, listed in the verifier as `NEW_11G`)
  and 11F `F3.status_summary`; each guarantee is re-checked as `G8.<phase>.<check>`, in the README or, for historical
  numbers, in `docs/history.md` (pinned since 11F).
- Outside the repository: the reply to the feedback (first person, no phase numbers, "Conforme combinado, esta versão não
  inclui vídeo."), the exact open items and the green CI run of the final HEAD, saved in the project as
  `claude/nota-resposta-feedback-v4.md`.
**Acceptance:**
- AC11.1 No path lets an invalid classifier answer through; provider unavailability follows the fail mode; both tested.
- AC11.2 The author's holdout is committed before its only run, and its result is reported unchanged.
- AC11.3 Every README claim has evidence in the repository; the three unsupported claims of audit section 10.4 are fixed or
  removed.
- AC11.4 Every real-model report states the tier and the models used.
- AC11.5 The README has at most ~350 lines, no "(Fase", no "candidato", no video text; nothing historical is lost (it moves
  to `docs/history.md` / `docs/status-history.md`).
