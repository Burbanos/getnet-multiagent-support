# Comparação de execuções: routing_holdout2_phase13

| Métrica | 12E | 13D |
| :--- | :--- | :--- |
| Execuções | rh2-1, rh2-2, rh2-3 | rh2-4, rh2-5, rh2-6 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 83,3% (75,0–91,7) | 80,6% (75,0–83,3) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 100,0% (100,0–100,0) | 96,3% (88,9–100,0) |
| Ferramentas corretas | 86,1% (83,3–91,7) | 83,3% (83,3–83,3) |
| Escalonamento correto | 96,3% (88,9–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fonte oficial recuperada | n/d | n/d |
| Idioma da resposta | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 4,8 s (4,6–5,0) | 9,8 s (9,2–11,0) |
| Latência por caso, p95 | 13,6 s (13,1–14,5) | 21,0 s (19,4–23,7) |
| Tokens por execução | 102.326 (98.737–104.706) | 177.684 (175.932–178.985) |
| Custo estimado por execução (USD, plano pago) | US$ 0,043 (0,041–0,044) | US$ 0,069 (0,068–0,070) |

## Execuções

- `rh2-1` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-2` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-3` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-4` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-5` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `rh2-6` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
