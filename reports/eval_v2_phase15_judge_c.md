# Comparação de execuções: v2_phase15_judge_c

| Métrica | r1_full | r2 |
| :--- | :--- | :--- |
| Execuções | v2-16, v2-17, v2-18 | v2-23, v2-24, v2-25 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 91,9% (89,7–93,6) | 94,4% (93,6–96,2) |
| Cenários oficiais aprovados | 80,0% (80,0–80,0) | 86,7% (80,0–90,0) |
| Roteamento correto | 96,4% (95,4–96,9) | 98,5% (96,9–100,0) |
| Ferramentas corretas | 97,1% (97,1–97,1) | 99,0% (97,1–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 92,3% (89,7–94,9) | 95,7% (94,9–97,4) |
| Fonte oficial recuperada | 94,7% (92,0–96,0) | 96,0% (96,0–96,0) |
| Idioma da resposta | 99,5% (98,6–100,0) | 99,5% (98,6–100,0) |
| Juiz: fundamentação (1 a 5) | 5,00 (5,00–5,00) | 4,96 (4,93–5,00) |
| Juiz: responde à pergunta (1 a 5) | 4,85 (4,82–4,88) | 4,82 (4,78–4,86) |
| Juiz: precisão da abstenção | 92,1% (84,6–100,0) | 96,7% (90,0–100,0) |
| Juiz: cobertura da abstenção | 68,9% (60,0–73,3) | 60,0% (53,3–66,7) |
| Juiz: aceitável sem correção | 98,1% (97,2–98,6) | 97,7% (95,8–100,0) |
| Latência por caso, mediana | 7,3 s (7,2–7,5) | 6,1 s (5,9–6,3) |
| Latência por caso, p95 | 15,2 s (14,5–15,7) | 12,2 s (12,0–12,5) |
| Tokens por execução | 1.170.795 (1.157.501–1.189.525) | 1.000.773 (981.526–1.021.629) |
| Custo estimado por execução (USD, plano pago) | US$ 0,448 (0,442–0,455) | US$ 0,392 (0,386–0,398) |

## Execuções

- `v2-16` (r1_full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash
- `v2-17` (r1_full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash
- `v2-18` (r1_full): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash
- `v2-23` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash
- `v2-24` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash
- `v2-25` (r2): 2026-11-21, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: gemini-3.8-flash

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
