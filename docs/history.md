# Histórico de resultados

Trechos retirados do README em 2026-11-09, quando ele foi reorganizado para mostrar só os resultados vigentes. O texto de cada trecho está como estava no README do commit `c6a3aeb`; os números continuam valendo para as execuções a que se referem (registros em `reports/eval_runs/`). Os resultados vigentes estão no README.

---

## Resultados da comparação de modelos (v1)

### Resultados da avaliação: comparação de modelos (3 execuções por modelo, 2026-11-08)

Seis execuções completas dos 69 casos de `data/eval/cases.jsonl`: três com o modelo padrão `gemini-3.5-flash-lite` e três com `gemini-3.8-flash`. Todas usaram o código da Fase 8D e o mesmo juiz, `gemini-3.6-flash`, diferente dos dois modelos avaliados. Nenhuma execução teve erro, e o modelo reserva não foi acionado. Cada célula mostra a média das três execuções e, entre parênteses, o mínimo e o máximo. Os dados brutos estão em `reports/eval_runs/` (`full-2` a `full-7`, cada uma com o `.judge.jsonl`), o relatório de cada execução em `reports/eval_full-N.md`, e esta tabela é gerada por `python -m src.eval compare` em `reports/eval_models.md`.

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
| Fonte oficial recuperada | 96,0% (96,0–96,0) | 92,0% (92,0–92,0) |
| Idioma da resposta | 94,7% (93,7–96,8) | 100,0% (100,0–100,0) |
| Juiz: fundamentação (1 a 5) | 4,98 (4,95–5,00) | 4,94 (4,94–4,94) |
| Juiz: responde à pergunta (1 a 5) | 4,67 (4,65–4,68) | 4,61 (4,48–4,70) |
| Juiz: precisão da abstenção | 74,9% (69,2–78,6) | 69,6% (64,7–72,7) |
| Juiz: cobertura da abstenção | 76,9% (69,2–84,6) | 74,4% (61,5–84,6) |
| Latência por caso, mediana | 4,3 s (4,2–4,3) | 15,4 s (15,0–15,8) |
| Latência por caso, p95 | 8,8 s (8,1–9,7) | 31,6 s (29,8–33,2) |
| Tokens por execução | 421.140 (413.563–426.999) | 566.646 (549.248–581.298) |
| Custo estimado por execução (USD, plano pago) | US$ 0,167 (0,163–0,170) | US$ 0,640 (0,622–0,654) |

> A linha "Fonte oficial recuperada" confere se a URL oficial esperada está entre as fontes recuperadas no turno; não confere se a resposta cita essa fonte no texto.

- **O modelo padrão continua `gemini-3.5-flash-lite`.** O `gemini-3.8-flash` aprovou cerca de 3 pontos a mais de casos, uma diferença do tamanho da variação entre execuções do mesmo modelo, e respondeu sempre no idioma da pergunta. Em troca, levou cerca de 3,5 vezes mais tempo e custou quase 4 vezes mais por execução.
- **Variação entre execuções:** com o mesmo modelo e os mesmos casos, a taxa de aprovação do flash-lite variou de 84,1% a 89,9%. Uma execução isolada não basta para comparar modelos nem para medir o efeito de uma mudança.
- **Falharam em todas as execuções dos dois modelos:** `k16` (a bateria da Get Mini está num trecho mal ranqueado), `o02` (pedido fora do tema atendido em vez de recusado), `s04` e `s06` (pergunta sobre código de recusa roteada para a base de conhecimento em vez de `diagnose_declined_transaction`). São defeitos do sistema, não do modelo, e não foram corrigidos ajustando prompts contra estes casos.
- **Só no `gemini-3.8-flash`, nas três execuções:** em `off01` (cenário oficial: diferença entre Get Clássica e Get Smart), ele buscou na base e respondeu que não encontrou a informação, que está lá. Em `u03` e `u05`, que deveriam ser abstenções, ele respondeu: tratou o "erro 05" da tela de rede como código de recusa e informou taxas da Stone a partir de uma busca web. Também falharam nas três execuções `k09` e `m04` (`m04` respondeu a pergunta de continuação com o contexto do turno anterior, sem nova busca, e a checagem de roteamento exige a busca).
- **Só no flash-lite:** respostas em português para perguntas em inglês (idioma 94,7%) e `u01` respondido sem fonte nas três execuções.
- **Busca web fora do ar na `full-2`:** em `off02` e `off07`, `search_web` não devolveu resultados durante a execução, e as respostas disseram que o serviço estava indisponível. A busca voltou a funcionar no mesmo dia. Os dois casos contam como falha nessa execução e não foram removidos.
- **Custo:** estimativa do plano pago a partir dos tokens de cada turno e da tabela de `src/core/pricing.py`. Não inclui o juiz nem os embeddings das consultas. O preço do `gemini-3.8-flash` (US$ 0,75 por milhão de tokens de entrada e US$ 3,75 de saída) vale até 2026-12-31; a partir de 2027-01-01, passa a US$ 1,50 e US$ 7,50.
- **Os rótulos foram escritos pelo Claude, que também planejou o sistema, e o juiz é um modelo:** a fundamentação perto de 5 discrimina pouco, e é a abstenção que separa os modelos.

---

## Resultados da execução full-1 (v1)

### Resultados da avaliação (execução `full-1`, 2026-11-07)

Execução única dos 69 casos de `data/eval/cases.jsonl` com o modelo `gemini-3.5-flash-lite` (respostas) e o juiz `gemini-3.1-flash-lite`. Dados brutos em `reports/eval_runs/full-1.jsonl` e `reports/eval_runs/full-1.judge.jsonl`; relatório completo em `reports/eval_full-1.md`.

| Métrica | Valor |
| :--- | :--- |
| Casos aprovados em todas as checagens determinísticas | 62/69 (89,9%) |
| Cenários oficiais do desafio | 9/10 |
| Roteamento correto / ferramentas corretas | 94,6% / 95,1% |
| Fatos esperados presentes / fonte oficial recuperada | 91,7% / 92,0% |
| Resposta no idioma da pergunta | 98,4% |
| Abstenção (juiz): precisão / cobertura | 76,9% / 76,9% |
| Fundamentação (juiz, 1 a 5) / responde à pergunta (juiz, 1 a 5) | 4,95 / 4,68 |
| Latência por caso: mediana / p95 | 6,3 s / 20,4 s |
| Tokens | 422.393 no total (~6,7 mil por caso); custo estimado US$ 0,170 (plano pago) |

Limites e falhas conhecidas:
- É uma execução única, sem estimativa de variância; os rótulos foram escritos pelo Claude.
- A categoria `uncovered` aparece com 100% nas checagens determinísticas apenas porque nenhuma delas se aplica a abstenção; a medida real é a do juiz: 7 de 8 se abstiveram, e `u01` afirmou algo que não está no corpus (que não é preciso cadastrar chave Pix).
- Fora do tema: `o04` escreveu o poema pedido e `o02` respondeu com busca web; só o juiz detectou o `o04`.
- A nota de fundamentação está perto do teto e discrimina pouco: o juiz é um modelo pequeno e aceitou a inferência do `u01`.
- Os resultados de `search_web` não ficam no registro da execução, então o juiz não confere respostas vindas da web.
- Falhas determinísticas: `s04` e `s06` (código de recusa roteado para a base de conhecimento), `o02`, `k07`, `k16` (bateria da Get Mini, problema de ranking), `k17` e `off08` (idioma).

---

## Matriz dos cenários oficiais medida na full-1

## 6. Matriz de Cobertura dos Cenários Oficiais

Resultado medido na execução `full-1` (2026-11-07, `gemini-3.5-flash-lite`), pelas checagens determinísticas de `src/eval/checks.py`; detalhes por caso em `reports/eval_full-1.md`.

| ID | Pergunta de Avaliação | Ferramenta acionada (`full-1`) | Fonte / evidência | Status (`full-1`) |
| :-: | :--- | :--- | :--- | :-: |
| 1 | *"What's the difference between the Get Clássica and the Get Smart?"* | `search_knowledge_base` | `site.getnet.com.br/todas-as-maquininhas/` | Aprovado |
| 2 | *"What's the weather forecast in Porto Alegre tomorrow?"* | `search_web` | Busca DuckDuckGo (resultados não registrados) | Aprovado |
| 3 | *"When will the money from yesterday's sales be deposited?"* | `get_settlement_status` | Dados simulados da conta (`cliente1988`) | Aprovado |
| 4 | *"Do I need a bank account to receive my sales via Pix?"* | `search_knowledge_base` | `site.getnet.com.br/get-ajuda-pix/` | Aprovado |
| 5 | *"My card machine won't connect to the internet, what should I do?"* | `diagnose_terminal` | Dados simulados do terminal | Aprovado |
| 6 | *"How does receivables advance (antecipação) work with Getnet?"* | `search_knowledge_base` | `site.getnet.com.br/get-ajuda-antecipacao-de-venda/` | Aprovado |
| 7 | *"What's the euro exchange rate today?"* | `search_web` | Busca DuckDuckGo (resultados não registrados) | Aprovado |
| 8 | *"My card machine is showing a transaction decline error."* | `diagnose_declined_transaction` | Dados simulados da transação | Reprovado (respondeu em português) |
| 9 | *"How many installments can I split a sale into with the crediário?"* | `search_knowledge_base` | `site.getnet.com.br/crediario/` (até 48x) | Aprovado |
| 10 | *"Can I sell through WhatsApp using the Payment Link?"* | `search_knowledge_base` | `getnet.net/en/our-solutions/online-payments` (página global; as páginas brasileiras de Link de Pagamento e WhatsApp vieram sem conteúdo na coleta, `data/corpus/manifest.json`) | Aprovado |

---

## Troca da base escrita à mão pelo corpus oficial

* **Por que trocamos a base**:
  A base antiga era um arquivo JSON escrito à mão (`getnet_kb.json`) que continha informações desatualizadas ou imprecisas. Um exemplo verificável: a base antiga afirmava que o parcelamento no crediário era em até 36x, enquanto a documentação oficial na página https://site.getnet.com.br/crediario/ estabelece parcelamento em até 48x (com a ressalva de que as condições variam conforme o emissor do cartão). Com a ingestão automatizada e o novo índice vetorial, o assistente passa a responder estritamente embasado nos documentos oficiais coletados.

---

## Perguntas e respostas que estavam no README

## 7. Glossário de Defesa Técnica (Perguntas de Entrevista)

### 1. "A UI mostra uma confiança na resposta. Como esse número é calculado?"
> **Resposta**: *"Não mostra. Removemos a métrica de confiança: não existe um cálculo que a sustente, e um número fixo ou inventado seria enganoso. O que o sistema expõe é verificável: as fontes com URL e data de coleta, a nota de similaridade de cada trecho recuperado (`retrieved_docs[].score`), o limiar `RAG_MIN_SCORE` e as métricas da avaliação em `reports/eval_full-1.md`."*

### 2. "O que o modelo/Supervisor decide no sistema, além de sintetizar a resposta?"
> **Defesa**: *"O Supervisor é o tomador de decisão do loop ReAct. Ele consome o histórico da conversa e os schemas tipados das ferramentas, decide qual ferramenta invocar com quais argumentos, avalia a observação retornada no estado do grafo e decide se necessita de novos passos ou se já possui evidências suficientes para emitir a resposta final."*

### 3. "De onde veio a base de conhecimento e como é garantido que ela não inventa dados fora de domínio?"
> **Resposta**: *"O corpus em `data/corpus/` reúne páginas oficiais da Getnet coletadas respeitando o robots.txt, fragmentadas e indexadas em `data/index/`. Se a melhor similaridade não atinge `RAG_MIN_SCORE`, o retriever devolve `abstain` e o Knowledge Agent diz que a informação não está nas fontes oficiais. Isso não é uma garantia: na avaliação `full-1`, 7 de 8 perguntas sem cobertura geraram abstenção, uma (`u01`) recebeu uma afirmação que não está no corpus, e um pedido fora do tema (`o04`, um poema) foi atendido."*

### 4. "O que acontece quando o usuário pede atendimento humano? Onde o caso é gravado e quem o recebe?"
> **Resposta**: *"Não prometemos fila nem prazo. A ferramenta `escalate_to_human` grava o chamado em SQLite (`TICKETS_DB_PATH`, padrão `data/tickets.db`) com protocolo `GET-TKT-YYYYMMDD-<10 hexadecimais>`, status `open`, prioridade, sessão e transcrição mascarada. Um operador responde via `PATCH /tickets/{ticket_id}` e a resposta é entregue no chat no turno seguinte do cliente; o cliente consulta o chamado via `GET /tickets/{ticket_id}`."*

### 5. "Como você garante que o sistema mantém o contexto em conversas longas?"
> **Resposta**: *"O grafo usa o checkpointer `SqliteSaver` do LangGraph (`CHECKPOINT_DB_PATH`), com `thread_id` igual a `user_id:session_id`: a memória sobrevive a reinícios e fica isolada por usuário mesmo com `session_id` repetido. Não há limpeza automática de conversas antigas nem memória compartilhada entre réplicas."*
