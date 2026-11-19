# Comparação de execuções: routing_holdout_phase14

| Métrica | 13D | 14 |
| :--- | :--- | :--- |
| Execuções | rh-7, rh-8, rh-9 | rh-10 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 95,8% (87,5–100,0) | 100,0% (100,0–100,0) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 95,8% (87,5–100,0) | 100,0% (100,0–100,0) |
| Ferramentas corretas | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fonte oficial recuperada | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Idioma da resposta | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 8,8 s (7,5–10,2) | 6,1 s (6,1–6,1) |
| Latência por caso, p95 | 15,5 s (13,3–18,7) | 12,9 s (12,9–12,9) |
| Tokens por execução | 97.784 (91.404–107.848) | 97.571 (97.571–97.571) |
| Custo estimado por execução (USD, plano pago) | US$ 0,038 (0,036–0,042) | US$ 0,037 (0,037–0,037) |

## Execuções

- `rh-7` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-8` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-9` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-10` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
