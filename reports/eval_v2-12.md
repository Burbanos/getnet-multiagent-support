# Relatório de Avaliação: v2-12

- **Gerado em**: `2026-11-18T22:28:49.055775+00:00`
- **Cases SHA256**: `e32b61a20c57fd3fb6c919b848339b56c6c57a7f7cf9b74959cb617f3b28bb10`
- **Conjunto de casos**: `data/eval/cases_v2.jsonl`
- **Status de Conclusão (`complete`)**: `True`
- **Modelos Avaliados (`answer_models`)**: `gemini-3.5-flash-lite`
- **Total de Casos**: 78
- **Avaliados com Sucesso**: 78
- **Erros de Execução**: 0

## Métricas Determinísticas Principais

| Métrica | Valor |
| :--- | :--- |
| `pass_rate` | 93.59% |
| `routing_rate` | 98.46% |
| `tools_rate` | 98.57% |
| `escalation_rate` | 100.00% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 92.00% |
| `facts_rate` | 89.74% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 100.00% |
| `escalation_precision` | 100.00% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 8282.4 ms |
| `latency_ms_p95` | 16056.5 ms |
| `tokens_total` | 1016198 |
| `tokens_mean_per_case` | 14113.861111111111 |
| `estimated_cost_usd` | 0.390662 |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Avaliação do Juiz LLM

- **Casos Julgados**: 72 (Erros: 0)
- **Modelos do Juiz**: `gemini-3.6-flash`
- **Erros de Abstenção (`abstention_errors`)**: `d04, k03, m04, off01, u01`
- **Discordâncias entre Juiz e Fatos (`disagreements`)**: `k03, m04, off01`

| Métrica do Juiz | Valor |
| :--- | :--- |
| `grounded_mean` | 4.93 / 5.0 |
| `answers_mean` | 4.68 / 5.0 |
| `abstention_precision` | 77.78% |
| `abstention_recall` | 93.33% |

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 100.00% |
| `knowledge` | 22 | 86.36% |
| `multi_intent` | 3 | 100.00% |
| `multi_turn` | 6 | 83.33% |
| `off_topic` | 5 | 100.00% |
| `pii` | 2 | 100.00% |
| `public_data` | 11 | 90.91% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 100.00% |
| `uncovered` | 8 | 100.00% |
| `web` | 1 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 30 | 86.67% |
| `pt` | 48 | 97.92% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 10
- **Pass Rate**: 80.00%

## Guardrail por Turno

- **Turnos com registro**: 84 (sem registro: 0)
- **Camada que decidiu**: padrões 6, classificador 0, nenhuma (mensagem liberada) 78
- **Status do classificador**: not_run 6, ok 78
- **Tokens do classificador**: entrada 53860, saída 1794, total 55654
- **Bloqueados pelos padrões**: g01, g02, g03, g04, g05, g06
- **Bloqueados pelo classificador**: nenhum

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `off01` | `knowledge` | `en` | `ok` | `facts_ok` |
| `off10` | `knowledge` | `en` | `ok` | `sources_ok` |
| `k03` | `knowledge` | `pt` | `ok` | `facts_ok` |
| `d04` | `public_data` | `en` | `ok` | `facts_ok` |
| `m04` | `multi_turn` | `en` | `ok` | `routing_ok, tools_ok, sources_ok, facts_ok` |
