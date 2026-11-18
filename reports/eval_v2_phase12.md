# Comparação de execuções: v2_phase12

| Métrica | 11G | 12D | 12E |
| :--- | :--- | :--- | :--- |
| Execuções | v2-1, v2-2, v2-3 | v2-4, v2-5, v2-6 | v2-7, v2-8, v2-9 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 91,9% (91,0–92,3) | 94,4% (93,6–96,2) | 95,3% (93,6–96,2) |
| Cenários oficiais aprovados | 96,7% (90,0–100,0) | 80,0% (70,0–90,0) | 83,3% (80,0–90,0) |
| Roteamento correto | 95,4% (95,4–95,4) | 98,5% (98,5–98,5) | 100,0% (100,0–100,0) |
| Ferramentas corretas | 95,7% (95,7–95,7) | 98,1% (97,1–98,6) | 99,0% (98,6–100,0) |
| Escalonamento correto | 98,6% (98,6–98,6) | 98,6% (97,1–100,0) | 98,1% (97,1–100,0) |
| Fatos esperados presentes | 94,9% (92,3–97,4) | 96,6% (94,9–97,4) | 99,1% (97,4–100,0) |
| Fonte oficial recuperada | 96,0% (96,0–96,0) | 96,0% (96,0–96,0) | 100,0% (100,0–100,0) |
| Idioma da resposta | 97,2% (97,2–97,2) | 96,8% (95,8–97,2) | 96,3% (94,4–97,2) |
| Juiz: fundamentação (1 a 5) | 4,99 (4,97–5,00) | 4,99 (4,97–5,00) | 4,98 (4,94–5,00) |
| Juiz: responde à pergunta (1 a 5) | 4,71 (4,69–4,74) | 4,70 (4,67–4,75) | 4,74 (4,68–4,83) |
| Juiz: precisão da abstenção | 80,0% (80,0–80,0) | 97,4% (92,3–100,0) | 100,0% (100,0–100,0) |
| Juiz: cobertura da abstenção | 80,0% (80,0–80,0) | 80,0% (73,3–86,7) | 77,8% (73,3–80,0) |
| Latência por caso, mediana | 5,1 s (4,9–5,1) | 6,1 s (6,0–6,3) | 5,5 s (5,4–5,7) |
| Latência por caso, p95 | 9,3 s (9,0–9,5) | 13,8 s (12,0–16,8) | 11,6 s (10,9–12,1) |
| Tokens por execução | 652.585 (646.665–662.717) | 717.626 (709.497–733.851) | 738.505 (723.549–749.771) |
| Custo estimado por execução (USD, plano pago) | US$ 0,253 (0,251–0,256) | US$ 0,281 (0,279–0,284) | US$ 0,288 (0,283–0,292) |

## Execuções

- `v2-1` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-2` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-3` (11G): 2026-11-09, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-4` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-5` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-6` (12D): 2026-11-13, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-7` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-8` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash
- `v2-9` (12E): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.6-flash

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
