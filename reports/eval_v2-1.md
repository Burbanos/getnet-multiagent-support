# Relatório de Avaliação: v2-1

- **Gerado em**: `2026-11-09T12:03:37.624492+00:00`
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
| `pass_rate` | 92.31% |
| `routing_rate` | 95.38% |
| `tools_rate` | 95.71% |
| `escalation_rate` | 98.57% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 96.00% |
| `facts_rate` | 97.44% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 97.22% |
| `escalation_precision` | 83.33% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 4927.8 ms |
| `latency_ms_p95` | 9385.6 ms |
| `tokens_total` | 662717 |
| `tokens_mean_per_case` | 9204.402777777777 |
| `estimated_cost_usd` | 0.25627 |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Avaliação do Juiz LLM

- **Casos Julgados**: 72 (Erros: 0)
- **Modelos do Juiz**: `gemini-3.6-flash`
- **Erros de Abstenção (`abstention_errors`)**: `k16, o02, o04, s04, s06, u01`
- **Discordâncias entre Juiz e Fatos (`disagreements`)**: `k16`

| Métrica do Juiz | Valor |
| :--- | :--- |
| `grounded_mean` | 5.00 / 5.0 |
| `answers_mean` | 4.74 / 5.0 |
| `abstention_precision` | 80.00% |
| `abstention_recall` | 80.00% |

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 80.00% |
| `knowledge` | 22 | 95.45% |
| `multi_intent` | 3 | 100.00% |
| `multi_turn` | 6 | 100.00% |
| `off_topic` | 5 | 80.00% |
| `pii` | 2 | 100.00% |
| `public_data` | 11 | 100.00% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 77.78% |
| `uncovered` | 8 | 87.50% |
| `web` | 1 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 30 | 86.67% |
| `pt` | 48 | 95.83% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 10
- **Pass Rate**: 100.00%

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `k16` | `knowledge` | `en` | `ok` | `sources_ok, facts_ok` |
| `s04` | `support` | `pt` | `ok` | `routing_ok, tools_ok` |
| `s06` | `support` | `en` | `ok` | `routing_ok, tools_ok, escalation_ok` |
| `u08` | `uncovered` | `en` | `ok` | `language_ok` |
| `o02` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `e04` | `escalation` | `en` | `ok` | `language_ok` |
