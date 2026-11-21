# Comparação de execuções: routing_holdout_phase15

| Métrica | 14 | 15 |
| :--- | :--- | :--- |
| Execuções | rh-10 | rh-11 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 100,0% (100,0–100,0) | 62,5% (62,5–62,5) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 100,0% (100,0–100,0) | 75,0% (75,0–75,0) |
| Ferramentas corretas | 100,0% (100,0–100,0) | 87,5% (87,5–87,5) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 100,0% (100,0–100,0) | 87,5% (87,5–87,5) |
| Fonte oficial recuperada | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Idioma da resposta | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 6,1 s (6,1–6,1) | 7,8 s (7,8–7,8) |
| Latência por caso, p95 | 12,9 s (12,9–12,9) | 14,0 s (14,0–14,0) |
| Tokens por execução | 97.571 (97.571–97.571) | 130.962 (130.962–130.962) |
| Custo estimado por execução (USD, plano pago) | US$ 0,037 (0,037–0,037) | US$ 0,049 (0,049–0,049) |

## Execuções

- `rh-10` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-11` (15): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
