# STATUS DO REPOSITÓRIO

**Subfase:** 13D-2 — README final, importação do anotador de fora e concordância (encerramento da Fase 13)
**Base:** `a6a1175` (rodada 13D) | **Python:** 3.13.3

## Estado final da Fase 13

- **Arquitetura distribuída e observabilidade:** checkpoints, chamados e auditoria em Postgres; rate limit compartilhado em Redis; tracing OpenTelemetry (jaeger) e painel Prometheus/Grafana; evidência em Compose (`compose-1`, `8994c1e`) com 9/9 checks aprovados.
- **Rodada com modelo produto (`a6a1175`):** v2 95.7% (93.6–97.4%), idioma 100%, escalonamento 100%, cobertura de abstenção pelo juiz 91.1% e precisão 86.3%, cenários oficiais 86.7%, fatos esperados 92.3%, latência mediana 8.4 s e US$ 0.392/execução; holdout 1 95.8%, holdout 2 80.6%, holdout 3 97.8% (roteamento 100%), ações 95.8% e busca híbrida `rerank-4..6` com `hit@1` 1.000 e abstenção em não cobertas 1.000.
- **Anotador externo (`--omit-name`):** 30 respostas e 1 comentário importados em `reports/human_validation_annotator/` sem nome publicado (`name: null`, `name_withheld_by_author: true`). Concordância autor × anotador: rota 26/30, deveria abster 25/30, aceitável 25/30, absteve 24/30, fundamentação exata 28/30; anotador × checks determinísticos: 25/30 (`acceptable_rate_human 0.8667`, `pass_rate_checks 0.9000`).

## O que mudou (13D-2)

- **Aposentadoria da 13D-1:** removidos via `git rm` `docs/phase-prompts/13D-1.md`, `docs/phase-prompts/13D-1-fix.md` e `scripts/verify_phase13d1.py`.
- **Opção `--omit-name` ([annotator.py](src/eval/annotator.py), [__main__.py](src/eval/__main__.py)):** `import_annotator_xlsx(..., omit_name=...)` e CLI `human-import --omit-name` permitem omitir o nome em `declaration.json` (`"name": null` e `"name_withheld_by_author": true`) mesmo quando autorizado pelo anotador, mantendo `name_authorized`.
- **Artefatos do anotador ([reports/human_validation_annotator/](reports/human_validation_annotator/)):** gerados pelos comandos `human-import --omit-name`, `human-agreement` e `human-raters` (`answers.csv`, `comments.csv`, `declaration.json`, `human_validation.json`, `human_validation.md`, `raters.json`, `raters.md`).
- **README final ([README.md](README.md)):** atualizado a partir de `docs/phase-prompts/13D-2-README.md` (removido em seguida).
- **Testes ([test_annotator_omit_name.py](tests/test_annotator_omit_name.py)):** 2 testes cobrindo `--omit-name` (via CLI, nome omitido em todos os arquivos gerados) e execução padrão (`name_withheld_by_author: false`).

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `506 passed, 13 deselected in 77.36s`
- `python scripts/verify_phase13d2.py`: `SUMMARY: 36/36 passed` (`PASS A0`–`A5`, `PASS S1.status`, `PASS T1`–`T11`, `PASS G1`–`G2`, `PASS D1`–`D6`, `PASS R1`–`R4`, `PASS Q1`–`Q6`, `INFO Q7.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md` ou `docs/phase-prompts/13D-2.md`.
