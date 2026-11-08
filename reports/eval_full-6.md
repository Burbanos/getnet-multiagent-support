# Relatório de Avaliação: full-6

- **Gerado em**: `2026-11-08T20:30:28.811089+00:00`
- **Cases SHA256**: `2d7d8e746a2322c2e61306f837b8176eabba838810b5a4f160584c433754ad07`
- **Status de Conclusão (`complete`)**: `True`
- **Modelos Avaliados (`answer_models`)**: `gemini-3.8-flash`
- **Total de Casos**: 69
- **Avaliados com Sucesso**: 69
- **Erros de Execução**: 0

## Métricas Determinísticas Principais

| Métrica | Valor |
| :--- | :--- |
| `pass_rate` | 88.41% |
| `routing_rate` | 92.86% |
| `tools_rate` | 95.08% |
| `escalation_rate` | 100.00% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 92.00% |
| `facts_rate` | 88.89% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 100.00% |
| `escalation_precision` | 100.00% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 15770.1 ms |
| `latency_ms_p95` | 33247.4 ms |
| `tokens_total` | 549248 |
| `tokens_mean_per_case` | 8718.222222222223 |
| `estimated_cost_usd` | 0.622446 |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Avaliação do Juiz LLM

- **Casos Julgados**: 63 (Erros: 0)
- **Modelos do Juiz**: `gemini-3.6-flash`
- **Erros de Abstenção (`abstention_errors`)**: `k09, k16, k17, off01, off10, s06, u03, u05`
- **Discordâncias entre Juiz e Fatos (`disagreements`)**: `k16, m04, off01`

| Métrica do Juiz | Valor |
| :--- | :--- |
| `grounded_mean` | 4.94 / 5.0 |
| `answers_mean` | 4.48 / 5.0 |
| `abstention_precision` | 64.71% |
| `abstention_recall` | 84.62% |

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 100.00% |
| `knowledge` | 22 | 81.82% |
| `multi_intent` | 2 | 100.00% |
| `multi_turn` | 6 | 83.33% |
| `off_topic` | 5 | 80.00% |
| `pii` | 2 | 100.00% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 77.78% |
| `uncovered` | 8 | 100.00% |
| `web` | 4 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 28 | 82.14% |
| `pt` | 41 | 92.68% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 10
- **Pass Rate**: 90.00%

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `off01` | `knowledge` | `en` | `ok` | `facts_ok` |
| `k09` | `knowledge` | `pt` | `ok` | `facts_ok` |
| `k16` | `knowledge` | `en` | `ok` | `sources_ok, facts_ok` |
| `k17` | `knowledge` | `en` | `ok` | `facts_ok` |
| `s04` | `support` | `pt` | `ok` | `routing_ok` |
| `s06` | `support` | `en` | `ok` | `routing_ok, tools_ok` |
| `o02` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
| `m04` | `multi_turn` | `en` | `ok` | `routing_ok, tools_ok, sources_ok` |
