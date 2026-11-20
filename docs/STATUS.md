# STATUS DO REPOSITÓRIO

**Subfase:** 15C2 — Ajuste do teste de chunking da 15C para reconstrução do índice | **Base:** `a1cfac9` | **Python:** 3.13.3

- **O que mudou:** `tests/test_chunking_index_15c.py::test_original_33_pages_match_committed_chunks_as_url_text_pairs` passou a filtrar `committed_pairs` pelas 33 URLs originais (mantendo `== 103` e `rebuilt_pairs == committed_pairs`); removidos `docs/phase-prompts/15C.md` e `scripts/verify_phase15c.py` (`git rm`), mantendo inalterados arquivos do revisor, `src/` e `data/`.

## Verificações (`python scripts/verify_phase15c2.py`)

```text
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS T1.only_the_named_test_changed
PASS S1.status
PASS T2.test_file_passes_with_committed_index :: 6 passed in 0.56s
PASS T3.test_file_passes_after_index_rebuild :: rebuilt index with 361 chunks; 15C version fails, 15C2 version passes
PASS R1.probes_left_tree_clean
INFO python 3.13.3
INFO AL4.promtool :: promtool not found: run by the reviewer and by CI
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
INFO P15B.A1.reviewer_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A2.retired_process_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A3.scope :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A4.frozen :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A5.existing_tests_only_grow :: superseded by the 15C A0–A6 and S1 checks (the 15B copy passes)
INFO P15B.S1.status :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15C.A1.reviewer_files :: superseded by the 15C2 check of the same name (the 15C copy fails)
INFO P15C.A2.retired_process_files :: superseded by the 15C2 check of the same name (the 15C copy fails)
INFO P15C.A3.scope :: superseded by the 15C2 check of the same name (the 15C copy fails)
INFO P15C.S1.status :: superseded by the 15C2 check of the same name (the 15C copy passes)
PASS P15C.previous_verifier :: 18/21 pass
PASS Q2.test_count :: 596 passed

SUMMARY: 10/10 passed
```

## Perguntas / divergências

Nenhuma divergência com `docs/SPEC.md` (§3.6 "15C2") ou `docs/phase-prompts/15C2.md`; `AL4.promtool` e `Q7.integration_suite` seguem para CI / revisor e `data/index/` será reconstruído pelo autor antes da rodada.
