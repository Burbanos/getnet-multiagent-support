# Guardrail: resumo de 3 execuções

- hybrid-1: modelos gemini-3.5-flash-lite; completa sim; metas não atingidas
- hybrid-2: modelos gemini-3.5-flash-lite; completa sim; metas atingidas
- hybrid-3: modelos gemini-3.5-flash-lite; completa sim; metas não atingidas

| Métrica | Média | Mínimo | Máximo |
|---|---|---|---|
| hybrid_block_rate | 1.0000 | 1.0000 | 1.0000 |
| hybrid_false_positive_rate | 0.1042 | 0.0625 | 0.1250 |
| hybrid_holdout_block_rate | 1.0000 | 1.0000 | 1.0000 |
| hybrid_holdout_false_positive_rate | 0.1667 | 0.1000 | 0.2000 |
| classifier_block_rate | 1.0000 | 1.0000 | 1.0000 |
| classifier_false_positive_rate | 0.1042 | 0.0625 | 0.1250 |
| latency_p50_ms | 797.8 | 779.3 | 817.9 |
| latency_p95_ms | 977.9 | 956.8 | 992.5 |
| cost_usd_mean_per_message | 0.00026884 | 0.00026875 | 0.00026889 |

Metas atingidas em todas as execuções: não
