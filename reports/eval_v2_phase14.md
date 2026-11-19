# Comparação de execuções: v2_phase14

| Métrica | 11G | 12E | 13D | 14 |
| :--- | :--- | :--- | :--- | :--- |
| Execuções | v2-1, v2-2, v2-3 | v2-7, v2-8, v2-9 | v2-10, v2-11, v2-12 | v2-13, v2-14, v2-15 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 91,9% (91,0–92,3) | 95,3% (93,6–96,2) | 95,7% (93,6–97,4) | 97,4% (96,2–98,7) |
| Cenários oficiais aprovados | 96,7% (90,0–100,0) | 83,3% (80,0–90,0) | 86,7% (80,0–90,0) | 96,7% (90,0–100,0) |
| Roteamento correto | 95,4% (95,4–95,4) | 100,0% (100,0–100,0) | 99,5% (98,5–100,0) | 97,4% (96,9–98,5) |
| Ferramentas corretas | 95,7% (95,7–95,7) | 99,0% (98,6–100,0) | 99,5% (98,6–100,0) | 98,1% (97,1–98,6) |
| Escalonamento correto | 98,6% (98,6–98,6) | 98,1% (97,1–100,0) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 94,9% (92,3–97,4) | 99,1% (97,4–100,0) | 92,3% (89,7–94,9) | 99,1% (97,4–100,0) |
| Fonte oficial recuperada | 96,0% (96,0–96,0) | 100,0% (100,0–100,0) | 97,3% (92,0–100,0) | 97,3% (96,0–100,0) |
| Idioma da resposta | 97,2% (97,2–97,2) | 96,3% (94,4–97,2) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | 4,99 (4,97–5,00) | 4,98 (4,94–5,00) | 4,98 (4,93–5,00) | 4,96 (4,94–5,00) |
| Juiz: responde à pergunta (1 a 5) | 4,71 (4,69–4,74) | 4,74 (4,68–4,83) | 4,70 (4,65–4,76) | 4,76 (4,75–4,76) |
| Juiz: precisão da abstenção | 80,0% (80,0–80,0) | 100,0% (100,0–100,0) | 86,3% (77,8–100,0) | 100,0% (100,0–100,0) |
| Juiz: cobertura da abstenção | 80,0% (80,0–80,0) | 77,8% (73,3–80,0) | 91,1% (86,7–93,3) | 88,9% (86,7–93,3) |
| Latência por caso, mediana | 5,1 s (4,9–5,1) | 5,5 s (5,4–5,7) | 8,4 s (8,3–8,5) | 7,4 s (7,1–7,8) |
| Latência por caso, p95 | 9,3 s (9,0–9,5) | 11,6 s (10,9–12,1) | 18,3 s (16,1–20,3) | 14,7 s (14,2–15,4) |
| Tokens por execução | 652.585 (646.665–662.717) | 738.505 (723.549–749.771) | 1.020.426 (996.511–1.048.568) | 1.055.527 (1.046.692–1.071.092) |
| Custo estimado por execução (USD, plano pago) | US$ 0,253 (0,251–0,256) | US$ 0,288 (0,283–0,292) | US$ 0,392 (0,382–0,403) | US$ 0,401 (0,399–0,405) |

## Execuções

- `v2-1` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-2` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-3` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-7` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-8` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-9` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-10` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-11` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-12` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-13` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-14` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-15` (14): 2026-11-19, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
