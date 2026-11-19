# STATUS DO REPOSITÓRIO

**Subfase:** 14A — Verificador com a evidência completa do turno e filtro de boilerplate só em blocos
**Base:** `1a6df5c` (13D-2) | **Python:** 3.13.3

## O que mudou (14A)

- **Aposentadoria da 13D-2:** removidos via `git rm` `docs/phase-prompts/13D-2.md` e `scripts/verify_phase13d2.py`.
- **Saídas brutas dos especialistas ([specialists.py](src/agents/specialists.py)):** `SpecialistAgent.run` passa a retornar `"tool_outputs"` (lista `{"tool", "content"}` em ordem de chamada, já após a triagem da busca web ou registro de erro/ferramenta indisponível).
- **Evidência completa e conversa no verificador ([state.py](src/core/state.py), [graph.py](src/core/graph.py), [verifier.py](src/agents/verifier.py)):** adicionado `SupervisorState.turn_evidence` (zerado a cada turno e acumulado em `_tools_node` inclusive no replanejamento); limites aumentados (`MAX_EVIDENCE_ITEM_CHARS=6000`, `MAX_EVIDENCE_TOTAL_CHARS=24000`); novas funções `build_verifier_evidence` e `build_verifier_conversation` (até 8 mensagens anteriores, 1500 chars/entrada e 6000 total, ignorando `ToolMessage`s e chamadas de ferramenta); `format_verifier_input` e `Verifier.verify` incluem `<conversation>`, mantendo compatibilidade com 4 argumentos; `verification` registra `evidence_chars` e `evidence_truncated`.
- **Boilerplate só em blocos ([chunking.py](src/rag/chunking.py), [index.py](src/rag/index.py)):** `build_chunks(..., boilerplate_min_run=2)` remove linhas frequentes apenas quando formam sequência contígua ≥ `boilerplate_min_run` após os filtros de linha vazia/sem alfanuméricos, restaurando **54 linhas isoladas** (`C3.fix_only_restores_isolated_lines :: 54 lines restored`) nos trechos do corpus atual; `build_index(..., chunking=...)` grava os parâmetros em `index_meta.json`.
- **Índice atual:** o índice em `data/index/` continua sendo o da 13C até o autor reconstruí-lo após este commit com `python -m src.rag.index`.
- **Testes:** novos [test_verifier_evidence.py](tests/test_verifier_evidence.py) (7) e [test_chunking_blocks.py](tests/test_chunking_blocks.py) (3).

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `516 passed, 13 deselected in 81.72s`
- `python scripts/verify_phase14a.py`: `SUMMARY: 32/32 passed` (`PASS A0`–`A6`, `PASS S1.status`, `PASS V1`–`V8`, `PASS C1`–`C4` com `54 lines restored`, `PASS G1`–`G2`, `PASS R1`–`R4`, `PASS Q1`–`Q6` e `INFO Q7.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/14A.md`.
