# Relatório de Ablação: ablation_phase15

- **Baseline:** `full`
- **SHA-256 do conjunto:** `e32b61a20c57fd3fb6c919b848339b56c6c57a7f7cf9b74959cb617f3b28bb10`

## Métricas por configuração

| Métrica | full | no_verifier | no_planner |
| :--- | :--- | :--- | :--- |
| Execuções | v2-16, v2-17, v2-18 | v2-19, v2-20, v2-21 | v2-22 |
| Aprovados por execução | 73, 70, 72 | 69, 72, 73 | 73 |
| Casos aprovados (checagens determinísticas) | 91,9% (89,7–93,6) | 91,5% (88,5–93,6) | 93,6% (93,6–93,6) |
| Cenários oficiais aprovados | 80,0% (80,0–80,0) | 73,3% (70,0–80,0) | 70,0% (70,0–70,0) |
| Roteamento correto | 96,4% (95,4–96,9) | 95,4% (93,8–96,9) | 96,9% (96,9–96,9) |
| Ferramentas corretas | 97,1% (97,1–97,1) | 96,2% (95,7–97,1) | 97,1% (97,1–97,1) |
| Escalonamento correto | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) | 100,0% (100,0–100,0) |
| Fatos esperados presentes | 92,3% (89,7–94,9) | 92,3% (87,2–97,4) | 94,9% (94,9–94,9) |
| Fonte oficial recuperada | 94,7% (92,0–96,0) | 94,7% (92,0–96,0) | 96,0% (96,0–96,0) |
| Idioma da resposta | 99,5% (98,6–100,0) | 100,0% (100,0–100,0) | 98,6% (98,6–98,6) |
| Juiz: fundamentação (1 a 5) | 4,96 (4,89–5,00) | 4,98 (4,94–5,00) | n/d |
| Juiz: responde à pergunta (1 a 5) | 4,80 (4,78–4,83) | 4,77 (4,76–4,79) | n/d |
| Juiz: precisão da abstenção | 92,3% (84,6–100,0) | 92,1% (84,6–100,0) | n/d |
| Juiz: cobertura da abstenção | 73,3% (66,7–80,0) | 73,3% (73,3–73,3) | n/d |
| Latência por caso, mediana | 7,3 s (7,2–7,5) | 6,5 s (6,3–6,8) | 5,4 s (5,4–5,4) |
| Latência por caso, p95 | 15,2 s (14,5–15,7) | 13,5 s (12,5–15,0) | 11,0 s (11,0–11,0) |
| Tokens por execução | 1.170.795 (1.157.501–1.189.525) | 995.037 (982.684–1.002.513) | 900.156 (900.156–900.156) |
| Custo estimado por execução (USD, plano pago) | US$ 0,448 (0,442–0,455) | US$ 0,387 (0,383–0,389) | US$ 0,345 (0,345–0,345) |

## Custo médio por agente (US$ / execução)

| Agente | full | no_verifier | no_planner |
| :--- | :--- | :--- | :--- |
| `GuardrailClassifier` | US$ 0,0247 | US$ 0,0245 | US$ 0,0244 |
| `KnowledgeAgent` | US$ 0,1617 | US$ 0,1657 | US$ 0,1618 |
| `LanguageRewriter` | US$ 0,0002 | US$ 0,0002 | US$ 0,0012 |
| `Planner` | US$ 0,0468 | US$ 0,0467 | US$ 0,0000 |
| `SupervisorAgent` | US$ 0,1394 | US$ 0,1306 | US$ 0,1345 |
| `SupportAgent` | US$ 0,0200 | US$ 0,0189 | US$ 0,0231 |
| `Verifier` | US$ 0,0554 | US$ 0,0000 | US$ 0,0000 |

## Portões de segurança e escopo (soma nas execuções)

| Portão | full | no_verifier | no_planner |
| :--- | :--- | :--- | :--- |
| Chamados sem pedido (`escalate: false`) | 0 | 0 | 0 |
| Idioma incorreto (`language_ok == false`) | 1 | 0 | 1 |
| Ferramentas fora de escopo (`off_topic`) | 0 | 0 | 1 |

## Comparação pareada contra `full`

| Configuração | Perdidos (`lost`) | Ganhos (`gained`) |
| :--- | :--- | :--- |
| `no_verifier` | `s06`, `x01` | nenhum |
| `no_planner` | `k14`, `o02`, `off03`, `off08` | `k13`, `m04`, `off05`, `s03` |

## Estimativa da camada de idioma

- Turnos reescritos no baseline: **1**
- Custo médio do `LanguageRewriter` por execução: **US$ 0,0002**
- Participação no custo total médio: **0,04%**

## Decisões pela regra de ablação

Regra da seção 3.4 do `docs/SPEC.md` (declarada antes da rodada): para o verificador, seja ΔQ = média de casos aprovados por execução em `full` menos em `no_verifier` (78 casos), e G = soma dos contadores dos três portões (`unrequested_tickets` + `wrong_language` + `out_of_scope_tools`) nas três execuções. O verificador permanece ligado por padrão se e somente se ΔQ ≥ 1,0 ou G(`no_verifier`) > G(`full`); caso contrário, `VERIFIER_ENABLED` passa a `false` por padrão na 15C (código, testes e flag permanecem no repositório). A checagem de idioma permanece ligada se e somente se os registros da configuração de referência mostrarem pelo menos 1 turno reescrito ou se a participação dela no custo total médio for inferior a 1%. O planner permanece sempre ligado por dependência funcional (portão de escalonamento e confirmação de ação de escrita); sua execução sem planner é reportada para medição de custo, latência e qualidade.

| Camada | Configuração comparada | Entradas | Manter padrão? |
| :--- | :--- | :--- | :--- |
| Verificador | `no_verifier` | ΔQ=0.333, G_base=1, G_abl=0 | não |
| Checagem de idioma | `full` | rewritten_turns=1, cost_share=0.04% | sim |
| Planner | `no_planner` | reason=feature_dependency | sim |
