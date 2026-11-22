# STATUS DO REPOSITÓRIO
**Subfase:** 15E | **Base:** `3426c78` | **Python:** 3.13.3
**O que mudou:** `README.md` copiado byte a byte de `docs/phase-prompts/15E_README.md` (rascunho removido); aposentados `docs/phase-prompts/15D.md` e `scripts/verify_phase15d.py`.
## Verificações (`python scripts/verify_phase15e.py`)
```text
PASS A0.py311_syntax
PASS A1.reviewer_files
PASS A2.retired_process_files
PASS A3.scope
PASS A4.readme_hygiene :: 122 repository paths exist
PASS S1.status
INFO python 3.13.3
INFO AL4.promtool :: promtool not found: run by the reviewer and by CI
INFO Q7.integration_suite :: TEST_DATABASE_URL/TEST_REDIS_URL not set: run by the reviewer and by the CI job
INFO P15B.A1.reviewer_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A2.retired_process_files :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A3.scope :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A4.frozen :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.A5.existing_tests_only_grow :: superseded by the 15C A0–A6 and S1 checks (the 15B copy fails)
INFO P15B.S1.status :: superseded by the 15C A0–A6 and S1 checks (the 15B copy passes)
INFO P15C.P15B :: 15B failures inside the 15C re-run: ['D4.corpus_committed', 'H2.second_sample_committed'] (allowed: ['D4.corpus_committed', 'H2.second_sample_committed'])
INFO P15C.A1.reviewer_files :: superseded by 15D (fails)
INFO P15C.A2.retired_process_files :: superseded by 15D (fails)
INFO P15C.A3.scope :: superseded by 15D (fails)
INFO P15C.A4.index_and_corpus_unchanged :: superseded by 15D (fails)
INFO P15C.A5.existing_tests_unchanged :: superseded by 15D (fails)
INFO P15C.S1.status :: superseded by 15D (fails)
INFO P15D.A1.reviewer_files :: superseded by 15E (fails)
INFO P15D.A2.retired_process_files :: superseded by 15E (fails)
INFO P15D.A3.scope :: superseded by 15E (fails)
INFO P15D.A4.data_and_reports_unchanged :: superseded by 15E (fails)
INFO P15D.S1.status :: superseded by 15E (passes)
PASS P15D.previous_verifiers :: 21/25 pass
PASS M1.matrix_matches_records :: 24 numeric rows recomputed
PASS M2.no_class_e_drop
INFO M1 :: drops: ['B3', 'V2.2', 'V2.4', 'V3.18']; drops only with the exceptions: ['E3', 'E9', 'V2.13']
PASS M3.drops_have_causes
PASS M4.exceptions_documented
PASS C1.round2_criterion :: R1 1 failure(s) [('off03', 'v2-24')]; R6 k13 3/3, m04 3/3
PASS C2.abstention_without_new_pages :: 26/30; ['u01', 'u02', 'u04', 'u06', 'u07']
PASS R1.probes_left_tree_clean

SUMMARY: 14/14 passed
```
## Perguntas / divergências
Nenhuma.
