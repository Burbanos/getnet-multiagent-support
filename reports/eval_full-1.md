# Relatório de Avaliação: full-1

- **Gerado em**: `2026-11-08T00:52:05.252599+00:00`
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
| `routing_rate` | 94.64% |
| `tools_rate` | 95.08% |
| `escalation_rate` | 100.00% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | 92.00% |
| `facts_rate` | 91.67% |
| `facts_none_rate` | 100.00% |
| `language_rate` | 98.41% |
| `escalation_precision` | 100.00% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 6335.0 ms |
| `latency_ms_p95` | 20431.4 ms |
| `tokens_total` | 422393 |
| `tokens_mean_per_case` | 6704.650793650793 |
| `estimated_cost_usd` | - |

> *Nota de Custo*: Token pricing arrives in Phase 7; cost calculation is not active yet.

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 5 | 100.00% |
| `knowledge` | 22 | 86.36% |
| `multi_intent` | 2 | 100.00% |
| `multi_turn` | 6 | 100.00% |
| `off_topic` | 5 | 80.00% |
| `pii` | 2 | 100.00% |
| `safety` | 6 | 100.00% |
| `support` | 9 | 66.67% |
| `uncovered` | 8 | 100.00% |
| `web` | 4 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 28 | 85.71% |
| `pt` | 41 | 92.68% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 10
- **Pass Rate**: 90.00%

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `off08` | `support` | `en` | `ok` | `language_ok` |
| `k07` | `knowledge` | `pt` | `ok` | `sources_ok, facts_ok` |
| `k16` | `knowledge` | `en` | `ok` | `sources_ok, facts_ok` |
| `k17` | `knowledge` | `en` | `ok` | `facts_ok` |
| `s04` | `support` | `pt` | `ok` | `routing_ok, tools_ok` |
| `s06` | `support` | `en` | `ok` | `routing_ok, tools_ok` |
| `o02` | `off_topic` | `pt` | `ok` | `routing_ok, tools_ok` |
