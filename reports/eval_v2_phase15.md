# Comparação de execuções: v2_phase15

| Métrica | 14 | full | no_verifier | no_planner |
| :--- | :--- | :--- | :--- | :--- |
| Execuções | v2-13, v2-14, v2-15 | v2-16, v2-17, v2-18 | v2-19, v2-20, v2-21 | v2-22 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 97,4% (96,2–98,7) | 91,9% (89,7–93,6) | 91,5% (88,5–93,6) | 93,6% (93,6–93,6) |
| Cenários oficiais aprovados | 96,7% (90,0–100,0) | 80,0% (80,0–80,0) | 73,3% (70,0–80,0) | 70,0% (70,0–70,0) |
| Roteamento correto | 97,4% (96,9–98,5) | 96,4% (95,4–96,9) | 95,4% (93,8–96,9) | 96,9% (96,9–96,9) |
| Ferramentas corretas | 98,1% (97,1–98,6) | 97,1% (97,1–97,1) | 96,2% (95,7–97,1) | 97,1% (97,1–97,1) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 99,1% (97,4–100,0) | 92,3% (89,7–94,9) | 92,3% (87,2–97,4) | 94,9% (94,9–94,9) |
| Fonte oficial recuperada | 97,3% (96,0–100,0) | 94,7% (92,0–96,0) | 94,7% (92,0–96,0) | 96,0% (96,0–96,0) |
| Idioma da resposta | 100,0% (100,0–100,0) | 99,5% (98,6–100,0) | 100,0% (100,0–100,0) | 98,6% (98,6–98,6) |
| Juiz: fundamentação (1 a 5) | 4,96 (4,94–5,00) | 4,96 (4,89–5,00) | 4,98 (4,94–5,00) | n/d |
| Juiz: responde à pergunta (1 a 5) | 4,76 (4,75–4,76) | 4,80 (4,78–4,83) | 4,77 (4,76–4,79) | n/d |
| Juiz: precisão da abstenção | 100,0% (100,0–100,0) | 92,3% (84,6–100,0) | 92,1% (84,6–100,0) | n/d |
| Juiz: cobertura da abstenção | 88,9% (86,7–93,3) | 73,3% (66,7–80,0) | 73,3% (73,3–73,3) | n/d |
| Latência por caso, mediana | 7,4 s (7,1–7,8) | 7,3 s (7,2–7,5) | 6,5 s (6,3–6,8) | 5,4 s (5,4–5,4) |
| Latência por caso, p95 | 14,7 s (14,2–15,4) | 15,2 s (14,5–15,7) | 13,5 s (12,5–15,0) | 11,0 s (11,0–11,0) |
| Tokens por execução | 1.055.527 (1.046.692–1.071.092) | 1.170.795 (1.157.501–1.189.525) | 995.037 (982.684–1.002.513) | 900.156 (900.156–900.156) |
| Custo estimado por execução (USD, plano pago) | US$ 0,401 (0,399–0,405) | US$ 0,448 (0,442–0,455) | US$ 0,387 (0,383–0,389) | US$ 0,345 (0,345–0,345) |

## Execuções

- `v2-13` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-14` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-15` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-16` (full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-17` (full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-18` (full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-19` (no_verifier): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-20` (no_verifier): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-21` (no_verifier): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-22` (no_planner): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
