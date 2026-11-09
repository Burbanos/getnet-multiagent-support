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

