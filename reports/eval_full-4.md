# Relatório de Avaliação: full-4

- **Gerado em**: `2026-11-08T20:30:20.740226+00:00`
- **Cases SHA256**: `2d7d8e746a2322c2e61306f837b8176eabba838810b5a4f160584c433754ad07`
- **Status de Conclusão (`complete`)**: `True`
- **Modelos Avaliados (`answer_models`)**: `gemini-3.5-flash-lite`
- **Total de Casos**: 69
- **Avaliados com Sucesso**: 69
- **Erros de Execução**: 0

## Métricas Determinísticas Principais

| Métrica | Valor |
| :--- | :--- |
| `pass_rate` | 89.86% |
| `routing_rate` | 92.86% |
| `tools_rate` | 93.44% |
| `escalation_rate` | 98.36% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 96.00% |
| `facts_rate` | 97.22% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 96.83% |
| `escalation_precision` | 83.33% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 4343.6 ms |
| `latency_ms_p95` | 9694.9 ms |
| `tokens_total` | 422859 |
| `tokens_mean_per_case` | 6712.047619047619 |
| `estimated_cost_usd` | 0.169846 |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Avaliação do Juiz LLM

- **Casos Julgados**: 63 (Erros: 0)
- **Modelos do Juiz**: `gemini-3.6-flash`
- **Erros de Abstenção (`abstention_errors`)**: `k16, o02, o04, s04, s06, u01`
- **Discordâncias entre Juiz e Fatos (`disagreements`)**: `k16`

| Métrica do Juiz | Valor |
| :--- | :--- |
| `grounded_mean` | 5.00 / 5.0 |
| `answers_mean` | 4.67 / 5.0 |
| `abstention_precision` | 76.92% |
| `abstention_recall` | 76.92% |

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 100.00% |
| `knowledge` | 22 | 95.45% |
| `multi_intent` | 2 | 100.00% |
| `multi_turn` | 6 | 83.33% |
| `off_topic` | 5 | 60.00% |
| `pii` | 2 | 100.00% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 77.78% |
| `uncovered` | 8 | 87.50% |
| `web` | 4 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 28 | 85.71% |
| `pt` | 41 | 92.68% |

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
| `o01` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `o02` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `m06` | `multi_turn` | `en` | `ok` | `language_ok` |
