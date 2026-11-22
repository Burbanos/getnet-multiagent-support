# Comparação de execuções: v2_phase15r2

| Métrica | 14 | r1 | r2 |
| :--- | :--- | :--- | :--- |
| Execuções | v2-13, v2-14, v2-15 | v2-19, v2-20, v2-21 | v2-23, v2-24, v2-25 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 97,4% (96,2–98,7) | 91,5% (88,5–93,6) | 94,4% (93,6–96,2) |
| Cenários oficiais aprovados | 96,7% (90,0–100,0) | 73,3% (70,0–80,0) | 86,7% (80,0–90,0) |
| Roteamento correto | 97,4% (96,9–98,5) | 95,4% (93,8–96,9) | 98,5% (96,9–100,0) |
| Ferramentas corretas | 98,1% (97,1–98,6) | 96,2% (95,7–97,1) | 99,0% (97,1–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 99,1% (97,4–100,0) | 92,3% (87,2–97,4) | 95,7% (94,9–97,4) |
| Fonte oficial recuperada | 97,3% (96,0–100,0) | 94,7% (92,0–96,0) | 96,0% (96,0–96,0) |
| Idioma da resposta | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) | 99,5% (98,6–100,0) |
| Juiz: fundamentação (1 a 5) | 4,96 (4,94–5,00) | 4,98 (4,94–5,00) | 5,00 (4,99–5,00) |
| Juiz: responde à pergunta (1 a 5) | 4,76 (4,75–4,76) | 4,77 (4,76–4,79) | 4,81 (4,76–4,83) |
| Juiz: precisão da abstenção | 100,0% (100,0–100,0) | 92,1% (84,6–100,0) | 96,7% (90,0–100,0) |
| Juiz: cobertura da abstenção | 88,9% (86,7–93,3) | 73,3% (73,3–73,3) | 62,2% (60,0–66,7) |
| Latência por caso, mediana | 7,4 s (7,1–7,8) | 6,5 s (6,3–6,8) | 6,1 s (5,9–6,3) |
| Latência por caso, p95 | 14,7 s (14,2–15,4) | 13,5 s (12,5–15,0) | 12,2 s (12,0–12,5) |
| Tokens por execução | 1.055.527 (1.046.692–1.071.092) | 995.037 (982.684–1.002.513) | 1.000.773 (981.526–1.021.629) |
| Custo estimado por execução (USD, plano pago) | US$ 0,401 (0,399–0,405) | US$ 0,387 (0,383–0,389) | US$ 0,392 (0,386–0,398) |

## Execuções

- `v2-13` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-14` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-15` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-19` (r1): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-20` (r1): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-21` (r1): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-23` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-24` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-25` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
