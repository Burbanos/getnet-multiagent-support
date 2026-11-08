# Relatório de Avaliação: full-5

- **Gerado em**: `2026-11-08T20:30:24.413246+00:00`
- **Cases SHA256**: `2d7d8e746a2322c2e61306f837b8176eabba838810b5a4f160584c433754ad07`
- **Status de Conclusão (`complete`)**: `True`
- **Modelos Avaliados (`answer_models`)**: `gemini-3.5-flash-lite`
- **Total de Casos**: 69
- **Avaliados com Sucesso**: 69
- **Erros de Execução**: 0

## Métricas Determinísticas Principais

| Métrica | Valor |
| :--- | :--- |
| `pass_rate` | 84.06% |
| `routing_rate` | 92.86% |
| `tools_rate` | 91.80% |
| `escalation_rate` | 96.72% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 96.00% |
| `facts_rate` | 94.44% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 93.65% |
| `escalation_precision` | 71.43% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 4225.9 ms |
| `latency_ms_p95` | 8562.6 ms |
| `tokens_total` | 413563 |
| `tokens_mean_per_case` | 6564.492063492064 |
| `estimated_cost_usd` | 0.162859 |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Avaliação do Juiz LLM

- **Casos Julgados**: 63 (Erros: 0)
- **Modelos do Juiz**: `gemini-3.6-flash`
- **Erros de Abstenção (`abstention_errors`)**: `k16, o02, s04, s06, u01`
- **Discordâncias entre Juiz e Fatos (`disagreements`)**: `k16, x01`

| Métrica do Juiz | Valor |
| :--- | :--- |
| `grounded_mean` | 5.00 / 5.0 |
| `answers_mean` | 4.65 / 5.0 |
| `abstention_precision` | 78.57% |
| `abstention_recall` | 84.62% |

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 100.00% |
| `knowledge` | 22 | 90.91% |
| `multi_intent` | 2 | 50.00% |
| `multi_turn` | 6 | 83.33% |
| `off_topic` | 5 | 40.00% |
| `pii` | 2 | 100.00% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 66.67% |
| `uncovered` | 8 | 87.50% |
| `web` | 4 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 28 | 75.00% |
| `pt` | 41 | 90.24% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 10
- **Pass Rate**: 80.00%

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `off04` | `knowledge` | `en` | `ok` | `escalation_ok` |
| `off08` | `support` | `en` | `ok` | `language_ok` |
| `k16` | `knowledge` | `en` | `ok` | `sources_ok, facts_ok` |
| `s04` | `support` | `pt` | `ok` | `routing_ok, tools_ok` |
| `s06` | `support` | `en` | `ok` | `routing_ok, tools_ok` |
| `u06` | `uncovered` | `en` | `ok` | `language_ok` |
| `o01` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `o02` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `o04` | `off_topic` | `en` | `ok` | `tools_ok, escalation_ok, language_ok` |
| `m06` | `multi_turn` | `en` | `ok` | `language_ok` |
| `x01` | `multi_intent` | `pt` | `ok` | `facts_ok` |
