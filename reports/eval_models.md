# Comparação de execuções: models

| Métrica | flash-lite | 3.8-flash |
| :--- | :--- | :--- |
| Execuções | full-2, full-4, full-5 | full-3, full-6, full-7 |
| Modelo das respostas | gemini-3.5-flash-lite | gemini-3.8-flash |
| Casos aprovados (checagens determinísticas) | 86,0% (84,1–89,9) | 88,9% (88,4–89,9) |
| Cenários oficiais aprovados | 86,7% (80,0–100,0) | 90,0% (90,0–90,0) |
| Roteamento correto | 93,5% (92,9–94,6) | 91,7% (91,1–92,9) |
| Ferramentas corretas | 93,4% (91,8–95,1) | 95,6% (95,1–96,7) |
| Escalonamento correto | 98,4% (96,7–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 93,5% (88,9–97,2) | 90,7% (88,9–94,4) |
| Fonte oficial citada | 96,0% (96,0–96,0) | 92,0% (92,0–92,0) |
| Idioma da resposta | 94,7% (93,7–96,8) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | 4,98 (4,95–5,00) | 4,94 (4,94–4,94) |
| Juiz: responde à pergunta (1 a 5) | 4,67 (4,65–4,68) | 4,61 (4,48–4,70) |
| Juiz: precisão da abstenção | 74,9% (69,2–78,6) | 69,6% (64,7–72,7) |
| Juiz: cobertura da abstenção | 76,9% (69,2–84,6) | 74,4% (61,5–84,6) |
| Latência por caso, mediana | 4,3 s (4,2–4,3) | 15,4 s (15,0–15,8) |
| Latência por caso, p95 | 8,8 s (8,1–9,7) | 31,6 s (29,8–33,2) |
| Tokens por execução | 421.140 (413.563–426.999) | 566.646 (549.248–581.298) |
| Custo estimado por execução (USD, plano pago) | US$ 0,167 (0,163–0,170) | US$ 0,640 (0,622–0,654) |
