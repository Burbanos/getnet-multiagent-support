# STATUS DO REPOSITÓRIO

**Data de geração**: 09/11/2026 | **Branch**: `main`

## Resumo

- O sistema foi construído em fases. Cada fase tem um prompt em `docs/phase-prompts/`, um verificador em `scripts/verify_phase*.py` (roda sem chave de API e reroda os verificadores anteriores) e um commit próprio; o CI roda ruff, pytest, o build da imagem e um smoke test em `/health` a cada push.
- Fases 1 a 8: supervisor com function calling, RAG sobre páginas oficiais, autenticação, memória, transbordo humano, avaliação com juiz, observabilidade e Docker.
- Fase 9: correções da auditoria simulada (cartão e CPF fora do disco, chamada de ferramenta órfã, mock sem conta inventada, imagem em produção, logs sem texto da conversa).
- Fase 10: clima e câmbio por API, guardrail híbrido (padrões e classificador por LLM), conjunto de avaliação v2 e execuções com modelo real.
- Fase 11: resposta inválida do classificador passa a bloquear; holdout do guardrail commitado antes da única execução (`author-1`); o runner registra a camada do guardrail por turno; tier e modelos nos relatórios; documentação reorganizada.
- Resultados vigentes: README e `reports/`. Resultados antigos: `docs/history.md`.
- Registro completo de cada fase (saída bruta dos verificadores, testes, perguntas ao SPEC): `docs/status-history.md`.

---

### Fase 12A: Amostra para Validação Humana e Holdout de Roteamento

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 12A:
```text
INFO python 3.13.3
PASS A0.py311_syntax
PASS A1.provider_branches_removed
PASS A2.readme_one_sentence
PASS A3.routing_holdout
PASS E2.scope
PASS A12.decisions_untouched
PASS A11.status
PASS A10.unsupported_providers
PASS A4.module_api
PASS A5.sample_recomputed :: eligible 72, allocation {'escalation': 2, 'knowledge': 9, 'multi_intent': 1, 'multi_turn': 3, 'off_topic': 2, 'pii': 1, 'public_data': 5, 'support': 4, 'uncovered': 3, 'web': 0}
PASS A5.functions_match_reference
PASS A6.generated_by_cli
PASS A7.form_blind_and_complete :: 125940 chars
PASS A8.answers_template
PASS A8.no_answers_yet
PASS A9.agreement_matches_reference
PASS A9.cli_agreement
PASS A13.tests_written :: 10 tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q0.verify_phase11g
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 348 passed in 29.19s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 76/76 passed
```

#### Commit base:
`d2de4ffa84a1c9c0917ef1ba8dffa961a6132c75`

#### Não feito:
Nada pendente nesta subfase (preenchimento do `answers.csv` e execução de `human-agreement` ficam a cargo do autor após o commit).

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
Ramos `openai` e `anthropic` removidos de `src/core/llm.py`, `tests/test_providers.py` e `README.md`; módulo `src/eval/human_validation.py`, subcomandos `human-sample` e `human-agreement` em `src/eval/__main__.py`, amostra cega gerada em `reports/human_validation/` (`sample.json`, `form.md`, `answers_template.csv`) e suíte `tests/test_human_validation.py` adicionada.

### Fase 11G: README Reorganizado

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11G:
```text
Python 3.13.3
INFO python 3.13.3
PASS G0.py311_syntax
PASS G1.readme_from_prompt :: 286 lines
PASS G2.structure
PASS G3.claims_evidence :: 22 rows, 82 paths
PASS G6.tier_and_models
PASS G7.authorship
PASS G9.history_unchanged
PASS G10.status
PASS E2.scope
PASS G8.2c.S3
PASS G8.3c.S5
PASS G8.3c.S5.48x
PASS G8.5a.S3
PASS G8.5b.S1
PASS G8.5c.S1
PASS G8.6a.S1
PASS G8.6b.S2
PASS G8.6c.S1
PASS G8.6c.S1.run
PASS G8.6c.S2
PASS G8.6d.S3
PASS G8.6e.S1-S2
PASS G8.6f.C4
PASS G8.6f.C5
PASS G8.6f.C6
PASS G8.6f.C8
PASS G8.7a.L0
PASS G8.7b.P0
PASS G8.7c.M0
PASS G8.7d.W0
PASS G8.8a.A0.ci
PASS G8.8a.A0.compose
PASS G8.8b.R2
PASS G8.8b.R4
PASS G8.8d.E3
PASS G8.8e.R2
PASS G8.8e.R3
PASS G8.8f.F1
PASS G8.8f.F2
PASS G8.8f.F4
PASS G8.8f.F5
PASS G8.9b.B5
PASS G8.9b.B6
PASS G8.9b.R1
PASS G8.9c.C8
PASS G8.9d.D9
PASS G8.9e.G8
PASS G8.9e.G9
PASS G8.9f.H10
PASS G8.9g.J2
PASS G8.9g.J3
PASS G8.9g.J3.full1
PASS G8.9g.J4
PASS G8.9g.J6
PASS G8.9g.J8
PASS G8.10i.I2
PASS G8.10i.I3
PASS G8.11a.A1
PASS G8.11a.A2
PASS G8.11a.A1.failopen
PASS G8.old_wording_gone
PASS G4.numbers_match_reports
PASS G5.demo_matches_records :: 6 transcripts
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q0.verify_phase11f
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 338 passed in 25.85s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 120/120 passed
ba480dfcb4579d98b591c6eebadbcc9c1e846d2c
```

#### Commit base:
`ba480dfcb4579d98b591c6eebadbcc9c1e846d2c`

#### Não feito:
Nada pendente.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
README.md reorganizado conforme o texto ditado em docs/phase-prompts/11G.md; resultados vigentes mantidos, histórico preservado em docs/history.md.

### Fase 11F: Registro por Fase e Resultados Antigos Movidos

#### Versão do Python:
```text
Python 3.13.3
```

#### Verificação Fase 11F:
```text
INFO python 3.13.3
PASS F0.py311_syntax
PASS F1.status_history :: 4109 lines
PASS F2.history
PASS F3.status_summary
PASS F4.old_status_checks_on_history
PASS F5.no_candidato
PASS E2.scope
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q0.verify_phase4a
PASS Q0.verify_phase4b
PASS Q0.verify_phase5a
PASS Q0.verify_phase5b
PASS Q0.verify_phase5c
PASS Q0.verify_phase6a
PASS Q0.verify_phase6b
PASS Q0.verify_phase6c
PASS Q0.verify_phase6d
PASS Q0.verify_phase6e
PASS Q0.verify_phase6f
PASS Q0.verify_phase7a
PASS Q0.verify_phase7b
PASS Q0.verify_phase7c
PASS Q0.verify_phase7d
PASS Q0.verify_phase8a
PASS Q0.verify_phase8b
PASS Q0.verify_phase8c
PASS Q0.verify_phase8d
PASS Q0.verify_phase8e
PASS Q0.verify_phase8f
PASS Q0.verify_phase9a
PASS Q0.verify_phase9b
PASS Q0.verify_phase9c
PASS Q0.verify_phase9d
PASS Q0.verify_phase9e
PASS Q0.verify_phase9f
PASS Q0.verify_phase9g
PASS Q0.verify_phase10a
PASS Q0.verify_phase10b
PASS Q0.verify_phase10c
PASS Q0.verify_phase10d
PASS Q0.verify_phase10e
PASS Q0.verify_phase10f
PASS Q0.verify_phase10g
PASS Q0.verify_phase10h
PASS Q0.verify_phase10i
PASS Q0.verify_phase11a
PASS Q0.verify_phase11b
PASS Q0.verify_phase11c
PASS Q0.verify_phase11d
PASS Q0.verify_phase11e
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 338 passed in 24.73s
PASS Q5.offline_eval
PASS Q3.tree_unchanged
PASS Q4.tests_do_not_touch_data_dbs

SUMMARY: 63/63 passed
```

#### Commit base:
`c6a3aeb899556b77fa994614da7adf9f78d148ef`

#### Não feito:
Nada pendente.

#### Perguntas / divergências com o SPEC:
Nenhuma.

#### Alterações:
O registro detalhado por fase foi movido de `docs/STATUS.md` para `docs/status-history.md`; os resultados históricos foram movidos do `README.md` para `docs/history.md`; o topo de `docs/STATUS.md` foi substituído pelo resumo gerado pelo script.

