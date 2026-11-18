# Comparação de execuções: routing_holdout

| Métrica | 12D | 12E |
| :--- | :--- | :--- |
| Execuções | rh-1, rh-2, rh-3 | rh-4, rh-5, rh-6 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 95,8% (87,5–100,0) | 87,5% (87,5–87,5) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Ferramentas corretas | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 100,0% (100,0–100,0) | 91,7% (87,5–100,0) |
| Fonte oficial recuperada | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Idioma da resposta | 95,8% (87,5–100,0) | 95,8% (87,5–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 4,9 s (4,7–5,2) | 4,7 s (4,2–5,2) |
| Latência por caso, p95 | 11,0 s (10,8–11,3) | 10,2 s (10,2–10,3) |
| Tokens por execução | 60.547 (60.207–60.913) | 61.779 (61.362–62.027) |
| Custo estimado por execução (USD, plano pago) | US$ 0,025 (0,024–0,025) | US$ 0,025 (0,025–0,025) |

## Execuções

- `rh-1` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-2` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-3` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-4` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-5` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh-6` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
