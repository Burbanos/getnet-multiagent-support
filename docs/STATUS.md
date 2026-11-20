# STATUS DO REPOSITÓRIO

**Subfase:** 15C — Reconferência de chave, IDs por URL, boilerplate por seção e exclusões do índice
**Base:** `dd9e8d3` (fim da 15B) | **Python:** 3.13.3

## O que mudou (15C)

- **Aposentadoria e arquivos do revisor:** removidos `docs/phase-prompts/15B.md` e `scripts/verify_phase15b.py` (`git rm`); preservados sem edição `docs/SPEC.md`, `docs/phase-prompts/15C.md`, `scripts/verify_phase15c.py`, `data/eval/retrieval_labeled2.jsonl`, `src/prompts/judge_acceptable.md` e `data/`.
- **Credencial conferida após emissão:** `credential_problem(principal)` (`src/core/auth.py`) chamada no Bearer (`authenticate`) antes do rate limit; `RefreshTokenRepository.rotate(..., key_check=...)` (`src/core/refresh_tokens.py`) revoga a família e audita `auth.refresh_revoked`; `/auth/refresh` (`src/main.py`) passa `credential_problem`.
- **Índice do corpus:** `chunk_id` via SHA-256 da URL e `boilerplate_section_exempt=True` em `src/rag/chunking.py`; `INDEX_EXCLUDED_URLS` (2 PDFs corporativos) e `excluded_urls` em `src/rag/index.py` (`data/index/` inalterado).
- **Testes novos:** `tests/test_auth_key_recheck.py` (6 testes) e `tests/test_chunking_index_15c.py` (6 testes).

## Verificações (`python scripts/verify_phase15c.py`)

```text
PASS A0.py311_syntax
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS A4.index_and_corpus_unchanged
PASS A5.existing_tests_unchanged
PASS S1.status
PASS A6.no_case_ids_in_code
PASS Q6.new_tests_written :: {'tests/test_auth_key_recheck.py': 6, 'tests/test_chunking_index_15c.py': 6}
{"timestamp": "2026-11-20T17:20:14.363661+00:00", "level": "INFO", "logger": "multiagent.refresh_tokens", "message": "Refresh token repository initialized"}
PASS K10.bearer_rechecks_api_key
PASS K11.refresh_rechecks_api_key_and_revokes_family
PASS K13.credential_problem
{"timestamp": "2026-11-20T17:20:14.588522+00:00", "level": "INFO", "logger": "multiagent.refresh_tokens", "message": "Refresh token repository initialized"}
PASS K12.rotate_key_check_contract
PASS X1.chunk_id_per_url
PASS X2.section_aware_boilerplate
Built index with 361 chunks from 125 ok pages (dim=768).
PASS X3.index_exclusions_and_config :: 361 chunks from 103 pages
PASS X4.gold_snippets_in_index_chunks
PASS X5.original_pages_chunks_unchanged
PASS R4.probes_left_tree_clean
INFO python 3.13.3
INFO AL4.promtool :: promtool not found: run by the reviewer and by CI
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
INFO P15B.A1.reviewer_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A2.retired_process_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A3.scope :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A4.frozen :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A5.existing_tests_only_grow :: superseded by the 15C A0–A6 and S1 checks (the 15B copy passes)
INFO P15B.S1.status :: superseded by the 15C A0–A6 and S1 checks (the 15B copy passes)
PASS P15B.previous_verifier :: 43/47 pass, superseded failures allowed: ['A1.reviewer_files', 'A2.retired_process_files', 'A3.scope', 'A4.frozen']
PASS Q2c.test_count :: 596 passed

SUMMARY: 21/21 passed
```

## Perguntas / divergências

Nenhuma divergência em aberto com `docs/SPEC.md` (§3.6) ou `docs/phase-prompts/15C.md`. `AL4.promtool` e `Q7.integration_suite` seguem para execução no CI / ambiente do revisor; `data/index/` será reconstruído pelo autor antes da rodada.
