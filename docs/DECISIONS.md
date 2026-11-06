# Resumo de Contexto do Projeto

### 1. Objetivo do Projeto e Restrições Informadas

* **Objetivo:** Refatorar integralmente o projeto `getnet-multiagent-support` para mitigar a nota inicial baixa (4,2/10) atribuída pelo avaliador técnico e alcançar a faixa de excelência agêntica (meta 9,5+ / 95).
* **Restrições informadas:**
* O vídeo demonstrativo não é necessário (dispensado conforme alinhamento prévio).
* Execução, validação e testes conteinerizados em ambiente GitHub Codespaces e Docker Compose.
* Preservação de resiliência e fallback determinístico (o sistema deve funcionar mesmo offline ou sem chaves externas).
* Demais restrições de negócio ou orçamento: não consta.



---

### 2. Decisões de Arquitetura e Motivações

* **Supervisor ReAct Nativo (LangGraph + Tool Calling via Pydantic):** Substituição completa do roteamento por regex da versão anterior por raciocínio agêntico real via `bind_tools`, nós de observação e síntese.
* **Memória Conversacional Persistente (`MemorySaver`):** Uso do checkpointer nativo do LangGraph indexado por `session_id`/`thread_id` para reter entidades e histórico em diálogos multi-turn reais.
* **RAG Generalista com Limiar de Abstenção:** Expansão da base para 15 manuais no ChromaDB e implementação de limiar de corte para abstenção formal quando a consulta estiver fora do domínio.
* **Human Oversight Real em SQLite (`tickets.db`):** Fim das mensagens fictícias de fila; criação de banco relacional local com persistência de chamados e endpoints `GET /tickets` e `GET /tickets/{id}`.
* **Evaluation Formal e LLM-as-a-Judge:** Implementação de `data/eval_dataset.json` (12 casos rotulados) e testes semânticos (`test_eval_judge.py`) para validar acurácia de roteamento, fidelidade e relevância.
* **Observabilidade e Custo:** Inclusão de `trace_id` único por requisição, contagem de tokens e estimativa de custo em USD baseada na tabela do Gemini Flash.
* **Segurança e Produção:** Mascaramento de PII (algoritmo de Luhn para cartões e máscara de CPF), autenticação via header `X-API-Key` (com chave dev padrão), isolamento de dependências (`requirements.lock`, `requirements-dev.txt`) e container não-root.

---

### 3. Prompts Enviados ao Antigravity (em ordem)

#### Prompt 1 (Implementação dos gaps de Avaliação, Observabilidade, Segurança e Lockfile) — Funcionou bem:

```markdown
Para fechar 100% dos gaps remanescentes do 'feedback burbanos v4.md' e assegurar a nota 9,5+:

1. Evaluation & Quality Engineering (peso 14%):
   - Crie 'data/eval_dataset.json' com 12 pares de teste rotulados contendo: 'id', 'question', 'expected_tool', 'ground_truth_context' e 'ideal_answer'.
   - Crie 'tests/test_eval_judge.py' que itera sobre esse dataset e implementa a rotina de LLM-as-a-judge (avaliando acurácia de roteamento, faithfulness e relevância semântica contra o ground truth, com suporte a fallback offline determinístico).
   - Adicione 1 teste automatizado de resiliência simulando timeout ou erro 500/429 da API externa do LLM, comprovando degradação graciosa sem crash da aplicação.

2. Observability & Cost (peso 6%):
   - Adicione à resposta da API (`/chat`), aos logs e ao painel de telemetria da interface `/demo`:
     * 'trace_id': UUID único gerado por requisição.
     * 'tokens': contagem estimada de 'prompt_tokens', 'completion_tokens' e 'total_tokens'.
     * 'estimated_cost_usd': cálculo estimado de custo em dólares baseado na tabela do Gemini Flash.

3. Security & Production Engineering (pesos 13% e 5%):
   - Adicione suporte a header 'X-API-Key' nos endpoints FastAPI (deve ser opcional ou aceitar uma chave padrão 'getnet-dev-key' para manter os testes automatizados e o Docker Compose 100% funcionais sem atrito).
   - Isole dependências de teste e gere o arquivo 'requirements.lock' com versões fixadas.

Garanta que todos os testes passem (50+ testes aprovados no pytest) e suba as alterações para a branch main.

```

#### Prompt 2 (Correção de permissões de escrita do SQLite no Docker e abstenção léxica do RAG):

* *Resumo:* Pedia a correção do erro `attempt to write a readonly database` via volumes Docker e abstenção para consultas fora de domínio; funcionou para os dois problemas, mas gerou o efeito colateral de introduzir uma lista estática de palavras (`GETNET_DOMAIN_KEYWORDS`) que bloqueou perguntas válidas de multi-turn.

---

### 4. O Que Deu Errado ou Precisou Ser Refeito

* **Permissão no SQLite no Docker:** O bind mount `./data:/app/data:ro` e a execução sob usuário não-root `appuser` causaram o erro `attempt to write a readonly database`. Refeito com volume nomeado (`getnet_tickets_data`), ajuste de permissões e mecanismo de fallback para `/tmp/tickets.db`.
* **Falso Positivo de Busca no RAG (Falta de Abstenção):** A consulta sobre bolo de chocolate pontuou no manual de Pix por sobreposição léxica de stopwords ("como", "fazer"). Refeito com expansão de stopwords e trava de domínio.
* **Falso Positivo de Abstenção no Multi-turn:** A trava adicionada para conter o bolo de chocolate passou a exigir palavras-chave de uma lista estática; no teste frontend do Turno 2 ("E qual delas tem tela touch com sistema Android?"), o sistema se absteve indevidamente porque "touch" e "android" não estavam na lista.

---

### 5. Pendências e Dúvidas em Aberto

* **Remoção de Regras Estáticas no RAG/Multi-turn:** O sistema ainda possui a trava `GETNET_DOMAIN_KEYWORDS` e precisa ser flexibilizado para que o Supervisor utilize a memória conversacional do histórico antes de acionar a busca, deixando a abstenção por conta puramente da distância vetorial do ChromaDB.
* **Dúvida sobre Modelos e Assinatura Claude:** Foi esclarecido que a assinatura do Claude Pro/Team não fornece cota para uso via API no Antigravity/ferramentas externas, exigindo créditos pré-pagos no Anthropic Console.
* **Avaliação de Ferramenta (Claude Code):** Ficou em aberto a decisão de utilizar ou não o Claude Code CLI no projeto, considerando os custos de API e a maturidade atual do repositório.
* **Envio da Versão Final:** O texto de submissão para o avaliador está redigido, aguardando o ajuste fino do Turno 2 antes do envio definitivo.
