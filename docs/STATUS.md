# STATUS DO REPOSITÓRIO

**Subfase:** 14B — README com a rodada da Fase 14
**Base:** `d95d55f` (rodada da Fase 14) | **Python:** 3.13.3

## O que mudou (14B)

- **Aposentadoria da 14A:** removidos via `git rm` `docs/phase-prompts/14A.md` e `scripts/verify_phase14a.py`.
- **Atualização de `README.md`:** copiado byte a byte a partir de `docs/phase-prompts/14B-README.md` (temporário removido em seguida), registrando os resultados da rodada da Fase 14 (`v2-13` a `v2-15`, holdouts `rh-10`, `rh2-7`, `h3-4`, `act-4` e recuperação `rerank-7`) e o desvio de modelo do juiz documentado em `docs/SPEC.md`.
- **Escopo preservado:** nenhum arquivo de código, teste, registro, rótulo ou prompt foi modificado.
- **Arquivos do revisor preservados:** `docs/SPEC.md`, `docs/phase-prompts/14B.md` e `scripts/verify_phase14b.py` permanecem intactos.

## Verificações (`python scripts/verify_phase14b.py`)

```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.reviewer_files_and_readme
PASS A2.retired_process_files
PASS A3.scope
PASS S1.status
PASS E1.readme_paths_exist :: 113 paths
PASS N1.v2_column_14_matches_report
PASS N2.success_criterion_stated
PASS N3.v2_failures_as_stated
PASS N4.verifier_counts_as_stated
PASS N5.holdouts_and_retrieval_as_stated
PASS N6.judge_model_as_stated
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 516 passed, 13 deselected in 84.30s (0:01:24)
PASS Q5.offline_eval
PASS Q3.tree_unchanged

SUMMARY: 16/16 passed
```

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/14B.md`.
