# STATUS DO REPOSITÓRIO

**Subfase:** 13B — Planner, verificação antes do envio, idioma, escalonamento só a pedido e aplicabilidade do catálogo de recusas
**Base:** `3a175bd` (Fase 13A-fix) | **Python:** 3.13.3

## O que mudou

- **Processo aposentado (13A removida):** removidos via `git rm` `docs/phase-prompts/13A.md`, `docs/phase-prompts/13A-fix.md` e `scripts/verify_phase13a.py`; adicionados `docs/phase-prompts/13B.md`, `scripts/verify_phase13b.py`, `data/eval/cases_holdout3.jsonl` e os prompts em `src/prompts/`.
- **Planner ([src/agents/planner.py](src/agents/planner.py)):** `PlanStep`, `TurnPlan`, `PlannerResult` e `Planner` com chamada estruturada (`TurnPlan`), span `llm.call` (`llm.caller = "Planner"`), escape XML e corte de `previous_reply` em 2000 caracteres.
- **Verificador pré-envio ([src/agents/verifier.py](src/agents/verifier.py)):** `StepVerdict`, `Verification`, `VerifierResult` e `Verifier` avaliando cada passo contra a evidência do turno (`llm.caller = "Verifier"`).
- **Idioma ([src/agents/language.py](src/agents/language.py)):** `detect_reply_language` (via `langdetect` com seed `0` e limiar `0.80`), `preserved_tokens` (URLs, `GET-TKT-...`, números com 2+ dígitos) e `LanguageRewriter` (`llm.caller = "LanguageRewriter"`).
- **Orquestração, estado, métricas e API ([src/core/graph.py](src/core/graph.py), [src/core/state.py](src/core/state.py), [src/core/metrics.py](src/core/metrics.py), [src/config.py](src/config.py), [.env.example](.env.example), [src/eval/runner.py](src/eval/runner.py), [src/main.py](src/main.py)):** novos nós `planner`, `out_of_scope`, `verifier` (até 1 replanejamento com `RemoveMessage` ou abstenção fixa) e `language_check` (1 reescrita validada por `preserved_tokens`); portão de escalonamento em `_tools_node`; métricas `getnet_planner_total`, `getnet_verifier_total`, `getnet_language_enforcement_total` e `getnet_escalation_gate_total`; campos `plan`, `verification`, `language` e `escalation_gate` em `observe_turn`, `AgentState` e `/chat`.
- **Ferramenta de recusa ([src/tools/agent_tools.py](src/tools/agent_tools.py)):** parâmetro obrigatório `code_context` em `diagnose_declined_transaction` (retornando `not_applicable` para `terminal_screen` e `app`) e docstring atualizada em `escalate_to_human`.
- **Testes:** novos [tests/test_planner.py](tests/test_planner.py) (9), [tests/test_verifier_node.py](tests/test_verifier_node.py) (8), [tests/test_language_enforcement.py](tests/test_language_enforcement.py) (8), [tests/test_escalation_gate.py](tests/test_escalation_gate.py) (6) e [tests/test_decline_context.py](tests/test_decline_context.py) (5); ajustes permitidos nos 4 pontos em testes existentes.

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `448 passed, 10 deselected in 43.75s`
- `python scripts/verify_phase13b.py`: `SUMMARY: 32/32 passed` (`PASS A0`–`A7`, `PASS S1.status`, `PASS P1`–`P4`, `PASS G1`–`G10`, `PASS R1`–`R3`, `PASS Q1`–`Q6`, `INFO C2.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/13B.md`.
