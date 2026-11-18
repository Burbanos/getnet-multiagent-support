# Comparação de execuções: routing_holdout_phase13

| Métrica | 12E | 13D |
| :--- | :--- | :--- |
| Execuções | rh-4, rh-5, rh-6 | rh-7, rh-8, rh-9 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 87,5% (87,5–87,5) | 95,8% (87,5–100,0) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 100,0% (100,0–100,0) | 95,8% (87,5–100,0) |
| Ferramentas corretas | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 91,7% (87,5–100,0) | 100,0% (100,0–100,0) |
| Fonte oficial recuperada | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Idioma da resposta | 95,8% (87,5–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 4,7 s (4,2–5,2) | 8,8 s (7,5–10,2) |
| Latência por caso, p95 | 10,2 s (10,2–10,3) | 15,5 s (13,3–18,7) |
| Tokens por execução | 61.779 (61.362–62.027) | 97.784 (91.404–107.848) |
| Custo estimado por execução (USD, plano pago) | US$ 0,025 (0,025–0,025) | US$ 0,038 (0,036–0,042) |

## Execuções

- `rh-4` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-5` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-6` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-7` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-8` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-9` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
