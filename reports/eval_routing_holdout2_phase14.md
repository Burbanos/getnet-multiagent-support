# Comparação de execuções: routing_holdout2_phase14

| Métrica | 13D | 14 |
| :--- | :--- | :--- |
| Execuções | rh2-4, rh2-5, rh2-6 | rh2-7 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 80,6% (75,0–83,3) | 75,0% (75,0–75,0) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 96,3% (88,9–100,0) | 100,0% (100,0–100,0) |
| Ferramentas corretas | 83,3% (83,3–83,3) | 75,0% (75,0–75,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fonte oficial recuperada | n/d | n/d |
| Idioma da resposta | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 9,8 s (9,2–11,0) | 8,0 s (8,0–8,0) |
| Latência por caso, p95 | 21,0 s (19,4–23,7) | 19,2 s (19,2–19,2) |
| Tokens por execução | 177.684 (175.932–178.985) | 187.755 (187.755–187.755) |
| Custo estimado por execução (USD, plano pago) | US$ 0,069 (0,068–0,070) | US$ 0,072 (0,072–0,072) |

## Execuções

- `rh2-4` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-5` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-6` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-7` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
