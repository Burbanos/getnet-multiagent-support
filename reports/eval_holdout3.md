# Comparação de execuções: holdout3

| Métrica | 13B-smoke | 13D |
| :--- | :--- | :--- |
| Execuções | h3-smoke-1 | h3-1, h3-2, h3-3 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.5-flash-lite |
| Casos aprovados (checagens determinísticas) | 90,3% (90,3–90,3) | 97,8% (96,8–100,0) |
| Cenários oficiais aprovados | n/d | n/d |
| Roteamento correto | 82,4% (82,4–82,4) | 100,0% (100,0–100,0) |
| Ferramentas corretas | 87,0% (87,0–87,0) | 100,0% (100,0–100,0) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 75,0% (75,0–75,0) | 100,0% (100,0–100,0) |
| Fonte oficial recuperada | n/d | n/d |
| Idioma da resposta | 100,0% (100,0–100,0) | 98,9% (96,8–100,0) |
| Juiz: fundamentação (1 a 5) | n/d | n/d |
| Juiz: responde à pergunta (1 a 5) | n/d | n/d |
| Juiz: precisão da abstenção | n/d | n/d |
| Juiz: cobertura da abstenção | n/d | n/d |
| Latência por caso, mediana | 9,4 s (9,4–9,4) | 9,1 s (8,4–10,1) |
| Latência por caso, p95 | 17,7 s (17,7–17,7) | 19,8 s (18,1–22,6) |
| Tokens por execução | 356.040 (356.040–356.040) | 429.163 (408.710–441.743) |
| Custo estimado por execução (USD, plano pago) | n/d | US$ 0,162 (0,154–0,166) |

## Execuções

- `h3-smoke-1` (13B-smoke): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `h3-1` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `h3-2` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz
- `h3-3` (13D): 2026-11-18, conta Tier 1 (pago); respostas: gemini-3.5-flash-lite; juiz: sem juiz

Tier da conta declarado pelo autor em `reports/run_context.json`; modelos lidos dos registros das execuções.
