# Processo de desenvolvimento (fases 1 a 12)

O código foi escrito pelo Google Antigravity, uma subfase por vez, a partir de um prompt de fase; o Claude (Anthropic), em
sessões separadas, escreveu o plano (`docs/SPEC.md`), os prompts de fase, um verificador de aceite por subfase, os conjuntos
rotulados e os prompts dos agentes, e conferiu cada subfase na própria cópia do repositório. Não é uma revisão independente:
o mesmo autor conduz as duas ferramentas.

Na Fase 13 os prompts, os verificadores e o registro por fase das fases 1 a 12 saíram da árvore para reduzir o volume de
processo. Continuam no histórico do git: o prompt e o verificador de cada subfase estão no commit dela, por exemplo
`git show 541f467:docs/phase-prompts/12C.md` e `git show 541f467:scripts/verify_phase12c.py`; o plano completo das fases
1 a 12 em `git show 431eb1f:docs/SPEC.md`; o registro de cada subfase em `git show 431eb1f:docs/status-history.md`.
A última execução da cadeia completa de verificadores (o da 12F, que reexecuta os anteriores) passou 75 de 75 em Python
3.11.18, no commit `431eb1f`.

| Subfase | Commit | Data | Descrição (mensagem do commit) |
|---|---|---|---|
| 1A | `947fd2b` | 2026-11-06 | remove fake signals and dead code |
| 1B | `1a4ad22` | 2026-11-06 | test hygiene, deps, CI, README corrections |
| 2A | `7408e3d` | 2026-11-06 | LLM supervisor with function calling |
| 2B | `946bfe9` | 2026-11-06 | LLM robustness (timeouts, error classes, step limit, trace id) |
| 2C | `05ad015` | 2026-11-06 | provider-agnostic model factory, fallback model, account masking |
| 2D | `7076a57` | 2026-11-06 | knowledge and support specialist sub-agents |
| 2E | `e08c1f7` | 2026-11-06 | real token usage and tools without invented values |
| 3A | `fb0923f` | 2026-11-06 | ingestion of official sources with robots.txt compliance |
| 3B | `d89d2cb` | 2026-11-06 | chunking, committed embedding index and retriever |
| 3C | `e6d1482` | 2026-11-06 | real RAG wired into the Knowledge Agent, legacy KB removed |
| 3D | `f467d56` | 2026-11-07 | retrieval evaluation and calibrated RAG_MIN_SCORE |
| 4A | `0e3ef87` | 2026-11-07 | identity from API key, per-user session isolation, tickets by owner, rate limit |
| 4B | `e84765f` | 2026-11-07 | SQLite checkpointer, restart survival, fail-fast auth and storage config |
| 5A | `31a18ec` | 2026-11-07 | ticket lifecycle, transcript snapshot, operator reply API, no silent persistence fallback |
| 5B | `fa8ccf0` | 2026-11-07 | handoff gate delivers the operator reply, ticket id entropy, conditional updates |
| 5C | `3c09da8` | 2026-11-07 | auto-escalation on repeated abstention, follow-ups reach the operator, single delivery |
| 6A | `4778cce` | 2026-11-07 | evaluation harness, deterministic checks, offline regression subset |
| 6B | `3074ecf` | 2026-11-07 | real-model eval runner, LLM judge and judge metrics |
| 6C | `636c9ba` | 2026-11-07 | judge reads list replies and stops on errors, free-tier model defaults, full-1 run |
| 6D | `ab87a46` | 2026-11-07 | judge reads full passages from the index, README quota and judge limits |
| 6E | `6aa2cbd` | 2026-11-07 | judge run 2, final evaluation report and README results |
| 6F | `6295a63` | 2026-11-07 | README and demo stop claiming confidence, cost and stale results |
| 7A | `6c8ad5a` | 2026-11-07 | structured logs with trace_id, session and hashed user; node and tool events |
| 7B | `83d6453` | 2026-11-08 | cost from the official price table, /chat logs inside the request context |
| 7C | `bb31178` | 2026-11-08 | /metrics in Prometheus text format |
| 7D | `fd93649` | 2026-11-08 | web results recorded for the judge, internal errors flagged, bilingual fixed messages |
| 8A | `5e57b8e` | 2026-11-08 | /agents generated from the code, demo shows real fields, README leftovers |
| 8B | `a4c57df` | 2026-11-08 | docker state volume, claims table, final README |
| 8C | `a70b60b` | 2026-11-08 | image defaults the databases to /app/state |
| 8D | `34fc9e1` | 2026-11-08 | read-only image files, last README claims |
| 8E | `c2d52e3` | 2026-11-08 | six committed runs, evaluation cost, model comparison |
| 8F | `c5e2698` | 2026-11-08 | README points to the multi-run results |
| 9A | `6c809bc` | 2026-11-08 | verifiers reproducible on Python 3.11, true authorship |
| 9B | `a561d4c` | 2026-11-08 | mask card and CPF before the message enters the graph |
| 9C | `308d382` | 2026-11-08 | close dangling tool calls after a failed turn |
| 9D | `613991b` | 2026-11-08 | the account mock never invents a merchant |
| 9E | `48af0a0` | 2026-11-08 | image and compose default to production |
| 9F | `ffb210b` | 2026-11-08 | no conversation text in the logs |
| 9G | `6456bf5` | 2026-11-08 | README residues from the V4 audit |
| 10A | `1eb3626` | 2026-11-09 | guardrail patterns re-evaluated on a pre-registered set |
| 10B | `fac9e87` | 2026-11-09 | LLM injection classifier behind the pattern guardrail |
| 10C | `b06dec3` | 2026-11-09 | guardrail real-model runner, report and summary |
| 10D | `74f9ee1` | 2026-11-09 | real Open-Meteo and PTAX responses captured as test fixtures |
| 10E | `2daa711` | 2026-11-09 | Open-Meteo and PTAX client with explicit statuses |
| 10F | `939b67b` | 2026-11-09 | weather and exchange-rate tools for the Knowledge Agent |
| 10G | `d2744b1` | 2026-11-09 | evaluation set v2 with the weather and exchange-rate tools |
| 10H | `9b8d082` | 2026-11-09 | real-model runs of the hybrid guardrail and the v2 evaluation set |
| 10I | `e8eb27e` | 2026-11-09 | README with the real-model results of the hybrid guardrail and the v2 set |
| 11A | `a2db8ac` | 2026-11-09 | an invalid guardrail classifier output blocks the message in both modes |
| 11B | `a3bb4df` | 2026-11-09 | guardrail holdout committed before its only run |
| 11C | `aac5773` | 2026-11-09 | author-1 run of the guardrail holdout, record and report |
| 11D | `1f7e93d` | 2026-11-09 | eval runner records the deciding guardrail layer and classifier tokens per turn |
| 11E | `c6a3aeb` | 2026-11-09 | account tier and models in the comparison and guardrail summary reports |
| 11F | `ba480df` | 2026-11-09 | per-phase log moved to docs/status-history.md and old results to docs/history.md |
| 11G | `d2de4ff` | 2026-11-09 | README reorganized (current results, demo from real records, authorship and repository map) |
| 12A | `70d4b1e` | 2026-11-12 | human validation sample, routing holdout and provider branches removed |
| 12B | `d1d9251` | 2026-11-12 | hybrid retrieval (BM25 + embeddings) with an LLM reranker |
| 12C | `541f467` | 2026-11-12 | operator webhook, supervisor resume on operator reply and history trim |
| 12D | `79aa33f` | 2026-11-12 | routing via tool descriptions, answer check, account fail-closed and web results guard |
| 12E | `a32b702` | 2026-11-17 | tool description boundaries for terminal functions and screen errors |
| 12F | `431eb1f` | 2026-11-18 | close phase 12 (author records, reports, README and STATUS) |
