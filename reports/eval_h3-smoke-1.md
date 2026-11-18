# Relatório de Avaliação: h3-smoke-1

- **Gerado em**: `2026-11-18T15:42:50.973804+00:00`
- **Cases SHA256**: `54bb563bc67835074e119e4c8918bf9a3c12929fd8b57e770e61b6864a5a1c7b`
- **Conjunto de casos**: `data/eval/cases_holdout3.jsonl`
- **Status de Conclusão (`complete`)**: `True`
- **Modelos Avaliados (`answer_models`)**: `gemini-3.5-flash-lite`
- **Total de Casos**: 31
- **Avaliados com Sucesso**: 31
- **Erros de Execução**: 0

## Métricas Determinísticas Principais

| Métrica | Valor |
| :--- | :--- |
| `pass_rate` | 90.32% |
| `routing_rate` | 82.35% |
| `tools_rate` | 86.96% |
| `escalation_rate` | 100.00% |
| `priority_rate` | 100.00% |
| `blocked_rate` | 100.00% |
| `sources_rate` | - |
| `facts_rate` | 75.00% |
| `facts_none_rate` | 90.91% |
| `language_rate` | 100.00% |
| `escalation_precision` | 100.00% |
| `escalation_recall` | 100.00% |
| `latency_ms_p50` | 9445.7 ms |
| `latency_ms_p95` | 17717.5 ms |
| `tokens_total` | 356040 |
| `tokens_mean_per_case` | 11485.161290322581 |
| `estimated_cost_usd` | - |

> *Nota de Custo*: Estimated answer cost from src/core/pricing.py (paid tier, Standard); null when no turn has tokens or any turn with tokens has no price. Excludes judge calls and query embeddings.

## Performance por Categoria

| Categoria | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `escalation` | 4 | 100.00% |
| `knowledge` | 4 | 100.00% |
| `multi_intent` | 1 | 100.00% |
| `multi_turn` | 3 | 100.00% |
| `off_topic` | 4 | 100.00% |
| `public_data` | 2 | 50.00% |
| `support` | 6 | 66.67% |
| `uncovered` | 7 | 100.00% |

## Performance por Idioma

| Idioma | Casos (n) | Pass Rate |
| :--- | :--- | :--- |
| `en` | 20 | 90.00% |
| `pt` | 11 | 90.91% |

## Cenários Oficiais (10 Casos de Referência)

- **Casos Avaliados**: 0
- **Pass Rate**: -

## Guardrail por Turno

- **Turnos com registro**: 34 (sem registro: 0)
- **Camada que decidiu**: padrões 0, classificador 0, nenhuma (mensagem liberada) 34
- **Status do classificador**: ok 34
- **Tokens do classificador**: entrada 23510, saída 782, total 24292
- **Bloqueados pelos padrões**: nenhum
- **Bloqueados pelo classificador**: nenhum

## Casos Reprovados

| ID | Categoria | Idioma | Status | Checagens Reprovadas |
| :--- | :--- | :--- | :--- | :--- |
| `t07` | `public_data` | `en` | `ok` | `routing_ok, tools_ok, facts_none_ok` |
| `t24` | `support` | `pt` | `ok` | `routing_ok, tools_ok, facts_ok` |
| `t25` | `support` | `en` | `ok` | `routing_ok, tools_ok` |
