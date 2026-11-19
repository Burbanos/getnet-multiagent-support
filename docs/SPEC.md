# SPEC — Getnet Multi-Agent Support System (v4)

Owner (the author): Burbanos · Planner/reviewer: Claude (external, Anthropic) · Implementer: Antigravity (Gemini)
Rubric: the evaluator's "Régua V4". Latest real feedback: v2, **8.0/10** on `d2de4ff`. Target: **≥ 9.5** (the latest
submission counts). Phases 1–12 (plan, prompts, verifiers, per-phase log) live in git history: `git show 431eb1f:docs/SPEC.md`;
the full Phase 13 plan: `git show 1a6df5c:docs/SPEC.md`. `docs/process.md` maps the sub-phases of phases 1–12 to their commits.

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

## Current state (2026-11-19)

**Phase 14: 14A done** (`10548ed`, verifier 32/32, CI green), index rebuilt (`45a6047`), round committed (`d95d55f`; the five
comparison reports regenerate byte-identical from the records). **The pre-registered success criterion was not met**:

| v2, mean of three runs | 11G | 13D | 14 (`v2-13..15`) | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| Official scenarios | 96.7% | 86.7% | 96.7% | ≥ 96.7: met |
| Expected facts | 94.9% | 92.3% | 99.1% | ≥ 94.9: met |
| Routing / tools | 95.4 / 95.7% | 99.5 / 99.5% | 97.4 / 98.1% | ≥ 99.5: not met (both) |
| Escalation | 98.6% | 100.0% | 100.0% | 100: met |
| Median / p95 latency, cost per run | 5.1 s / 9.3 s, US$ 0.253 | 8.4 s / 18.3 s, US$ 0.392 | 7.4 s / 14.7 s, US$ 0.401 | reported |

Fixed: `off01` 3/3 (0/3 in 13D), `d04`/`d05` 3/3, verifier abstentions 5 → 2 (both `u03`, the expected abstention). Routing
drop: `m04` 2/3 (follow-up answered from the conversation, no KB call: the direct trade-off of 14A), `s03`/`off05`/`s01` 1/3
each. `u02` (central phone) is now answered 3/3 because the block rule restored the line; its label (uncovered) is stale and
was not changed. Holdouts, one run each: rh 100%, rh2 75% (`n05`, `n06`, `n07`), h3 96.8% (`t20`), actions 87.5% (`a05`);
`rerank-7` hit@1 1.000, uncovered abstention 0.900 (`u02`).

**Deviation in the round (reviewer's error):** the commands given to the author did not set `EVAL_JUDGE_MODEL`, so `v2-13..15`
were judged by the code default `gemini-3.1-flash-lite`, not `gemini-3.6-flash`. No criterion depends on the judge. Decision
(delegated by the author): the judge is not re-run (records are immutable, and re-judging would pick a result); the README
marks the judge rows of column 14 as another model.

Next: **14B** (README with the round, then resubmission). No further round or fix sub-phase in Phase 14.

---

## 1. Target architecture (after Phase 14)

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
verifier (13B: per sub-task answered / evidence does not apply / unsupported; one replan; 14A: sees the turn's raw tool
outputs and the earlier conversation) → answer_check (URLs, ticket ids, time promises) → language enforcement (13B) → answer
   │
   └─ checkpoints (PostgresSaver), tickets and audit events (Postgres via SQLAlchemy Core); SQLite only for dev and tests

Knowledge Agent: hybrid KB search (BM25 + dense + reranker, abstains; 14A: boilerplate removed only in repeated blocks),
                 weather (Open-Meteo), FX (PTAX), web search (news only).
Support Agent: settlement, declined transactions (catalogue applies only to declined sales, 13B), terminal diagnosis,
               request_terminal_replacement (13C: proposal → merchant confirmation → execution, idempotent, audited).
Operator: webhook notification, /operator console (13C), PATCH /tickets/{id} resumes the thread.
Deployment: compose with Postgres, Redis, two app replicas; profile `observability` adds Jaeger, Prometheus and Grafana.
```

---

## 2. Phase 13 (closed)

Four sub-phases and one round: 13A (Postgres/Redis state, tracing, dashboard), 13B (planner, verifier, language, escalation
gate, decline context; holdout 3), 13C (smoke fixes, confirmed terminal replacement, operator console, corpus pages),
13D-1 (+ fix) and 13D-2 (round, annotator, README). Guarantees of the retired verifiers continue as the test suite (no test
removed or renamed; test files only grow), frozen records, the cross-cutting invariants re-checked by every verifier (no raw
card/CPF in any persisted state, no conversation text in logs or spans, `user_id` only from the credential, offline eval 6/6,
ruff clean, no network in tests) and CI. Acceptance AC13.1–AC13.6 met; the regressions are the subject of Phase 14.
Implementer models: Gemini 3.8 Flash up to 11G; Gemini 4 Hydrogen 12A–12D; Orchestrator (Argon) 12E, 12F, 13A, 13A-fix, 13B,
13C, 13D-1 and 13D-1-fix; Orchestrator (Neon) from 13D-2.

---

## 3. Phase 14 — fix the Phase 13 regressions before resubmission

Two sub-phases and one round of real runs, no fix sub-phase planned in advance. 14A changes code; the author rebuilds the
index and runs the round; 14B writes the results into the README. Implementer: Antigravity, Orchestrator (Neon). Nothing is
tuned against a case: no change to labels, to the agents' prompts other than the verifier's input description, or to code
that names a case or its strings.

### Diagnosis (reviewer, from the 13D records and the committed corpus)

1. **The verifier judges with less evidence than the supervisor had.** `_verifier_node` passes only the current turn's
   supervisor-level `ToolMessage`s, that is, each specialist's summary; the raw tool outputs stay inside
   `SpecialistAgent.run`, and the earlier conversation is not passed at all. Records: `d04` (`v2-10`, `v2-12`) was rejected
   for "a general disclaimer about bank exchange rates" and then for "a collection date not present", while the raw PTAX result
   carries both (`rate_note`: "a reference rate, not a retail or tourism rate"; `retrieved_at`), and the knowledge agent's
   summary kept only "(taxa de referência)"; `d05` (`v2-10`) the same for the date; `m04` turn 2 (`v2-12`) was rejected with
   "empty evidence" although "Android 12 or higher" was in the assistant's turn-1 answer; in `compose-1`, "Alguma novidade?"
   after a delivered operator reply got the fixed abstention.
2. **`off01`: a chunking defect, not retrieval or the agent prompt.** `build_chunks` drops, as boilerplate, every line whose
   normalized form appears in at least `boilerplate_min_pages=4` ok pages. At 12F the line "Get Smart" was in 3 pages
   (`in-person-payments`, `todas-as-maquininhas`, `get-tap`); the 13C re-collection of the home page made it 4, so it left every
   chunk, including the price tables. `data/corpus/pages.jsonl` has "Get Clássica / R$ 79,90/mês / Get Smart / R$ 129,90/mês";
   the committed chunk `590a78a70a4e-001` (and the home and Get Tap chunks) has "Get Clássica / R$ 79,90/mês / R$ 129,90/mês",
   with no label for the second price. Reproducible offline: `build_chunks(ok_pages, max_chars=900, boilerplate_min_pages=4,
   min_chars=RAG_MIN_CHUNK_CHARS)` returns the committed `chunks.jsonl` exactly. At 12E the chunk still had the label (index of
   `431eb1f`) and the agent gave both prices in 3/3 runs; in 13D, without the label and with the home page chunk also retrieved
   (Black Friday purchase prices, "12x R$ 7,90 … Get Clássica"), it gave neither price in 3/3 and said the comparison was not
   in the sources. The same rule removes other isolated content lines: 16 distinct lines in the current
   corpus ("débito", "link de pagamento", "get tap", "para compras com:" …). The home page chunk stays as it is (second factor,
   not changed: it is real content of an official page).
3. **Latency and cost** rose with the planner, the verifier and the language check. Not targeted in Phase 14 beyond not adding
   calls; the round measures them again.

### 14A — Verifier evidence and block boilerplate (`scripts/verify_phase14a.py`, prompt `docs/phase-prompts/14A.md`)

Verifier (general fix of 1):
- `SpecialistAgent.run` returns `tool_outputs`: one `{"tool", "content"}` per tool call, in call order, with `content` exactly
  as appended to the specialist's `ToolMessage` (after the web-results screening: a blocked result is the blocked payload;
  an unavailable tool is its error payload).
- `SupervisorState.turn_evidence` (list), reset to `[]` in `_build_turn_state`; the tools node appends
  `{"agent", "tool", "content"[:MAX_EVIDENCE_ITEM_CHARS]}` for every output of `ask_knowledge_agent` and `ask_support_agent`;
  it accumulates across the replan of the same turn.
- `build_verifier_evidence(messages, merchant_idx, turn_evidence) -> (str, bool)` (module level in `src/core/graph.py`): the
  current turn's supervisor `ToolMessage`s (as today), then the `turn_evidence` items, each block headed `[<name>]` or
  `[<agent>/<tool>]`; each item cut to `MAX_EVIDENCE_ITEM_CHARS = 6000`; the whole string at most
  `MAX_EVIDENCE_TOTAL_CHARS = 24000` (the item that crosses the limit is cut, later items dropped); the bool says whether
  anything was cut or dropped.
- `build_verifier_conversation(messages, merchant_idx) -> str`: messages before the latest merchant message, oldest first, one
  entry per message, `merchant: …`, `operator: …` (HumanMessage with `origin == "operator"`) or `assistant: …` (AIMessage
  without tool calls); never `ToolMessage`s or AIMessages with tool calls (earlier evidence is not reused: test
  `test_verifier_uses_only_current_turn_tool_evidence` stays); at most the 8 most recent entries, each text cut to 1500
  characters, the joined block at most 6000 characters (older entries dropped first).
- `format_verifier_input(message, steps, evidence, draft, conversation="")` and `Verifier.verify(..., conversation="")`: blocks
  `<message>`, `<conversation>` (always present, may be empty), `<plan_steps>`, `<evidence>`, `<draft>`, same escaping.
- `verification` gains `evidence_chars` (int) and `evidence_truncated` (bool) whenever the verifier model was called.
- Prompt `src/prompts/verifier.md` (reviewer): describes the new input; a fact is supported by any field of a raw tool result
  or by what the merchant, the operator or an earlier assistant answer said; general knowledge never is.
- Unchanged: when the verifier runs or is skipped, the single replan, the fixed abstention, fail-open on invalid output or
  provider error, `answer_check`, planner, language enforcement, supervisor and specialist prompts.

Chunking (general fix of 2):
- `build_chunks(..., boilerplate_min_run: int = 2)`: a line is removed as boilerplate only when its normalized form appears in
  at least `boilerplate_min_pages` ok pages **and**, in that page, it is part of a run of at least `boilerplate_min_run`
  consecutive such lines, counted over the lines that survive the empty and non-alphanumeric filters. Template chrome (menus,
  footers, call-to-action blocks) comes in runs; an isolated repeated line is content. `boilerplate_min_run=1` is the old rule.
- `src/rag/index.py`: `build_index(..., chunking=None)` writes `chunking` into `index_meta.json` when given; `main()` passes
  `{"max_chars": 900, "boilerplate_min_pages": 4, "boilerplate_min_run": 2, "min_chars": RAG_MIN_CHUNK_CHARS}`.
- No change to `data/` in 14A: the author rebuilds the index after the commit (needs the API key).

Tests (new files; existing test files only grow): `tests/test_verifier_evidence.py` (≥ 7) and `tests/test_chunking_blocks.py`
(≥ 3), scripted models only. Process: `docs/phase-prompts/13D-2.md` and `scripts/verify_phase13d2.py` leave the tree.

### Between 14A and 14B — index rebuild and the round (author; pre-registered here, before any run)

1. `python -m src.rag.index` → commit `index: rebuild with block boilerplate filter` (only `data/index/`).
2. With the code of that commit, Tier 1 paid account, product model `gemini-3.5-flash-lite`, judge `gemini-3.6-flash`, same
   settings as 13D; no code, prompt or label change until the round is committed:
   - `v2-13`, `v2-14`, `v2-15` (`data/eval/cases_v2.jsonl`), each `run` then `judge`;
   - `rh-10` (`cases_routing_holdout.jsonl`), `rh2-7` (`cases_routing_holdout2.jsonl`), `h3-4` (`cases_holdout3.jsonl`),
     `act-4` (`cases_actions.jsonl`), one `run` each, no judge;
   - `rerank-7` (`python -m src.rag.hybrid_eval run --run-id rerank-7`), one run: the index changes, and the README's retrieval
     table describes the current index (reviewer's addition, confirmed by delegation of the author before the round);
   - `python -m src.eval context` for every new run id;
   - comparison reports (new names; 13D reports are not regenerated): `compare --name v2_phase14` with groups
     `11G=v2-1,v2-2,v2-3`, `12E=v2-7,v2-8,v2-9`, `13D=v2-10,v2-11,v2-12`, `14=v2-13,v2-14,v2-15`;
     `routing_holdout_phase14` (`13D=rh-7,rh-8,rh-9`, `14=rh-10`); `routing_holdout2_phase14` (`13D=rh2-4,rh2-5,rh2-6`,
     `14=rh2-7`); `holdout3_phase14` (`13D=h3-1,h3-2,h3-3`, `14=h3-4`); `actions_phase14` (`13D=act-1,act-2,act-3`,
     `14=act-4`); `python -m src.rag.hybrid_eval report --runs rerank-7 --name retrieval_hybrid_phase14`;
   - one commit `eval: phase 14 round (...)` with the records and the reports. Failures are published as they come out.

**Success criterion (declared before the round).** From `reports/eval_v2_phase14.md`, group `14` (mean of `v2-13..15`, as
printed with one decimal) against the values printed in `reports/eval_v2_phase13.md`:
- official scenarios ≥ **96.7%** (11G);
- expected facts present ≥ **94.9%** (11G);
- routing ≥ **99.5%**, tools ≥ **99.5%**, escalation ≥ **100.0%** (13D: no drop).
Met only if all five hold. The README states, criterion by criterion, whether it held; if not, it says so plainly. Language,
judge metrics, latency, cost, holdouts, action cases and retrieval are reported, not criteria. The four cases that motivated
14A (`d04`, `d05`, `m04`, `off01`) belong to v2; no holdout case influenced 14A.

### 14B — README with the round (`scripts/verify_phase14b.py`, prompt `docs/phase-prompts/14B.md`)

The README text is dictated by the reviewer (`docs/phase-prompts/14B-README.md`, a temporary reviewer file copied byte for
byte and deleted; the verifier pins the README's SHA-256). Changes, decided by the author and, where he delegated, by the
reviewer (2026-11-19): the "Resultados" opening paragraph (round 14, code `10548ed`, index `45a6047`, the judge deviation);
the v2 table with column "14" (latency and cost rows included), the success criterion and its outcome, and the bullets under
the table; column "14" in the holdouts table and its bullets; the retrieval table with `rerank-7`; "Limitações conhecidas"
revised; "Autoria e revisão" with Orchestrator (Neon) for 14A and 14B; the evidence rows of the verifier, chunking, decline
context and results claims. Nothing else in the README changes. 14B also retires the 14A prompt and verifier, and rewrites
`docs/STATUS.md`. No code, record, label or prompt changes.

### Acceptance (Phase 14)

- AC14.1 The verifier receives the turn's raw tool outputs and the earlier conversation; a fact present only there is not
  rejected, and a fact supported by neither still is (scripted tests and `verify_phase14a.py`).
- AC14.2 Isolated repeated lines stay in the chunks and repeated blocks do not; the old rule reproduces the 13C index exactly;
  the rebuilt index records its chunking parameters.
- AC14.3 One round, pre-registered above, published as it came out, with the success criterion stated before it and its outcome
  in the README.
- AC14.4 Every README claim has evidence in the repository; product model, labels and agent prompts (other than the verifier's)
  unchanged.
