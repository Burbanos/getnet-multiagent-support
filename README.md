# Getnet Multi-Agent Support System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2%2B-orange.svg)](https://github.com/langchain-ai/langgraph)
[![SQLite](https://img.shields.io/badge/SQLite-tickets.db-blue.svg)](https://www.sqlite.org/)
[![Architecture](https://img.shields.io/badge/architecture-Supervisor%20ReAct-blueviolet.svg)]()
[![Auth](https://img.shields.io/badge/auth-X--API--Key-blue.svg)]()
[![Security](https://img.shields.io/badge/security-PII%20Luhn%20%2B%20non--root-success.svg)]()

Sistema agêntico de suporte inteligente para estabelecimentos e clientes Getnet, estruturado sobre o padrão **Supervisor + ReAct com declaração de ferramentas**, persistência conversacional multi-turn em banco SQLite via **LangGraph SqliteSaver**, base de conhecimento vetorial **índice de embeddings com limiar de relevância**, sanitização de **PII (Luhn PAN + CPF)**, observabilidade com **Trace ID e contagem de tokens**, e persistência e ciclo de vida de chamados humanos em banco relacional **SQLite (`data/tickets.db`)**.

---

## Limitações atuais

* **Supervisor LLM e API Key**: O supervisor utiliza o modelo Gemini com function calling e exige `GEMINI_API_KEY`; sem a chave, o endpoint `/chat` responde HTTP 503 com mensagem explícita;
* **Testes com modelo roteirizado**: Os testes automatizados utilizam um modelo roteirizado (`ScriptedChatModel`) para validação de plumbing sem chamadas de rede e não medem a qualidade do roteamento, que será avaliada na Fase 6;
* **Base de conhecimento**: Base oficial ingerida e vetorizada (`gemini-embedding-2`), com avaliação de retrieval e limiar calibrado na Fase 3D;
* **Persistência e Isolamento de Memória**: O histórico de sessões é persistido em SQLite via `SqliteSaver` no arquivo `CHECKPOINT_DB_PATH` (padrão `data/checkpoints.db`, preservado no volume Docker), sobrevivendo a reinícios e isolado por `user_id:session_id`. Limitações honestas: não há expiração/limpeza automática de conversas antigas; cada réplica utiliza seu próprio arquivo SQLite (sem memória compartilhada entre instâncias sem banco compartilhado); o rate limit é controlado em memória por processo; o app não sobe com `API_KEYS` inválido ou banco inacessível (e responde 503 se a configuração ficar inválida em execução).

---

## Interface Visual & Observabilidade (/demo)

O sistema disponibiliza uma console visual interativa em 3 colunas acessível diretamente pelo navegador em [`/demo`](http://localhost:8000/demo):

* **Coluna Esquerda (Cenários 1-Click)**: Catálogo com os 12 cenários de teste pré-configurados (10 cenários oficiais de referência do desafio Getnet + testes de injeção de prompt e transbordo humano). Dispara qualquer teste com um único clique.
* **Coluna Central (Chat Interativo Multi-Turn)**: Interface de conversação em tempo real com controle de `Session ID` para teste de memória contextual contínua, balões de diálogo com identificação do modelo, ferramentas acionadas e latência.
* **Coluna Direita (Inspetor de Telemetria & Rastreabilidade)**: Painel de observabilidade técnica com:
  * **Trace ID UUID** único gerado por ciclo de vida da requisição (`trc-<uuid12>`).
  * **Consumo Estimado de Tokens** dividido em `Prompt`, `Completion` e `Total`.
  * **Custo Financeiro Estimado em USD** baseado na tabela oficial de tokens.
  * **Latência em milissegundos** (`execution_time_ms`) com alta performance.
  * **Confiança Dinâmica** por similaridade de embeddings ou execução de tool.
  * **Auditoria de Guardrails** (`is_safe`, detecção de PII mascarada e injeção de prompt).
  * **Rastreabilidade de Chamados SQLite** com link direto para o endpoint `GET /tickets/{ticket_id}`.
  * **Payload JSON Integral** colapsável para inspeção por avaliadores técnicos.

### Como Acessar a Interface:
* **Execução Local**: Acesse [`http://localhost:8000/demo`](http://localhost:8000/demo) no navegador com a aplicação em execução.
* **GitHub Codespaces**: Na aba **Ports** do ambiente, acesse a porta `8000` pública no caminho `/demo`.

---

## Sumário

- [Limitações atuais](#limitações-atuais)
- [1. Arquitetura do Sistema](#1-arquitetura-do-sistema)
  - [Padrão Supervisor ReAct](#padrão-supervisor-react)
  - [Grafo de Estados Compilado (LangGraph)](#grafo-de-estados-compilado-langgraph)
  - [Especialistas Registrados como Tools](#especialistas-registrados-como-tools)
- [2. Pilares de Engenharia e Diferenciais](#2-pilares-de-engenharia-e-diferenciais)
  - [Orquestração Agêntica ReAct](#orquestração-agêntica-react)
  - [Memória Persistente Multi-Turn (LangGraph SqliteSaver)](#memória-persistente-multi-turn-langgraph-sqlitesaver)
  - [RAG Vetorial e Limiar de Abstenção](#rag-vetorial-e-limiar-de-abstenção)
  - [Transbordo Humano Real com SQLite (tickets.db)](#transbordo-humano-real-com-sqlite-ticketsdb)
  - [Segurança & Sanitização de Dados Sensíveis (PII)](#segurança--sanitização-de-dados-sensíveis-pii)
- [3. Como Executar e Modos de Operação](#3-como-executar-e-modos-de-operação)
  - [Modos de Operação](#modos-de-operação)
  - [Execução via Docker Compose](#execução-via-docker-compose)
  - [Execução Local](#execução-local)
  - [Endpoints da API REST](#endpoints-da-api-rest)
- [4. Testes Automatizados e CI/CD](#4-testes-automatizados-e-cicd)
- [5. Matriz de Cobertura dos Cenários Oficiais](#5-matriz-de-cobertura-dos-cenários-oficiais)
- [6. Glossário de Defesa Técnica (Perguntas de Entrevista)](#6-glossário-de-defesa-técnica-perguntas-de-entrevista)
- [7. Estrutura do Repositório](#7-estrutura-do-repositório)

---

## 1. Arquitetura do Sistema

O fluxo implementa a arquitetura de orquestração com subagentes especialistas: **Supervisor $\rightarrow$ Especialistas (KnowledgeAgent / SupportAgent) ou Transbordo Humano $\rightarrow$ Observação $\rightarrow$ Decisão $\rightarrow$ Resposta Grounded**.

### Padrão Supervisor ReAct com Subagentes Especialistas

O `SupervisorAgent` não invoca ferramentas operacionais de baixo nível diretamente. Ele analisa o diálogo e delega para subagentes especialistas isolados (`KnowledgeAgent` e `SupportAgent`) ou efetua o transbordo humano direto (`escalate_to_human`):

```text
Usuário (Turno N)
       ↓
[Guardrail Node] (Sanitização PII Luhn + CPF & Defesa contra Injection)
       ↓
[Supervisor Node] (Supervisor ReAct com ferramentas de delegação)
       ├── ask_knowledge_agent  → [KnowledgeAgent] (search_knowledge_base, search_web)
       ├── ask_support_agent    → [SupportAgent]   (get_settlement_status, diagnose_declined_transaction, diagnose_terminal)
       └── escalate_to_human    → Registro formal de transbordo no SQLite (tickets.db)
       ↓
[Tool Execution Node] (Executa especialista em contexto isolado ou chamado humano)
       ↓
[Supervisor Node] (Observa saída ToolMessage estruturada e sintetiza resposta grounded)
       ↓
Resposta ao Usuário + Gravação no SqliteSaver (thread_id = user_id:session_id)
```

### Grafo de Estados Compilado (LangGraph)

```mermaid
flowchart TD
    Start([Início: Request HTTP /chat]) --> GuardrailNode[Nó: Guardrails & PII Sanitizer]

    GuardrailNode -->|Violação / Prompt Injection| SafeExit([Interrupção Segura: Mensagem Bloqueada])
    GuardrailNode -->|Mensagem Segura| SupervisorNode[Nó: Supervisor ReAct\nTool Calling ReAct Engine]

    SupervisorNode -->|ask_knowledge_agent| KnowledgeSpecialist[KnowledgeAgent Sub-Agent\nContexto Isolado: search_knowledge_base, search_web]
    SupervisorNode -->|ask_support_agent| SupportSpecialist[SupportAgent Sub-Agent\nContexto Isolado: settlement, declined, terminal]
    SupervisorNode -->|escalate_to_human| HumanEscalation[Transbordo Humano Direto\nSQLite tickets.db]

    KnowledgeSpecialist -->|ToolMessage: agent, status, answer, sources| SupervisorNode
    SupportSpecialist -->|ToolMessage: agent, status, answer, tools_used| SupervisorNode
    HumanEscalation -->|ToolMessage: ticket_id, protocol| SupervisorNode

    SupervisorNode -->|Resposta Concluída| EndNode([Fim: Resposta Grounded + Telemetria])
    SafeExit --> EndNode
```

### Isolamento de Contexto e Limite de Passos dos Especialistas

* **Isolamento de Contexto**: Cada especialista (`KnowledgeAgent`, `SupportAgent`) é instanciado como `SpecialistAgent` e executa em um loop isolado com `[SystemMessage(prompt), HumanMessage(task)]`, sem acesso ao histórico completo da conversa do usuário, prevenindo vazamentos de contexto e alucinações cruzadas.
* **Injeção de Identidade Segura**: O `user_id` autenticado é injetado programaticamente via `RunnableConfig` (`config={"configurable": {"user_id": user_id}}`) e nunca exposto aos parâmetros visíveis ao LLM.
* **Limite de Passos dos Especialistas**: Cada especialista executa no máximo `MAX_SPECIALIST_STEPS` (padrão: 4) chamadas ao modelo. Se o limite for atingido, o especialista devolve status `"step_limit"` e o Supervisor trata o retorno graciosamente. O supervisor por sua vez possui o limite global `MAX_SUPERVISOR_STEPS` (padrão: 6).
* **Ferramentas do Supervisor e dos Especialistas**:
  * `ask_knowledge_agent`: delega dúvidas conceituais, produtos Getnet e dados públicos em tempo real ao `KnowledgeAgent`.
  * `ask_support_agent`: delega consultas sobre a conta do lojista (extrato D+1, transações negadas, conectividade de terminal) ao `SupportAgent`.
  * `escalate_to_human`: transbordo direto para especialista humano em casos de reclamações formais ou solicitação explícita.

### Especialistas Registrados como Tools do Supervisor e dos Especialistas

Todas as ferramentas são decoradas com `@tool` do LangChain e contratos tipados com schemas Pydantic:

| Ferramenta | Pertence a | Descrição |
| :--- | :--- | :--- |
| `ask_knowledge_agent` | Supervisor | Delega perguntas sobre produtos Getnet ou dados públicos em tempo real ao KnowledgeAgent |
| `ask_support_agent` | Supervisor | Delega solicitações de conta de lojista ao Customer Support Agent |
| `escalate_to_human` | Supervisor | Cria chamado humano persistido em `tickets.db` |
| `search_knowledge_base` | KnowledgeAgent | Busca vetorial semântica no índice oficial (gemini-embedding-2) com limiar |
| `search_web` | KnowledgeAgent | Busca pública em tempo real (DuckDuckGo) |
| `get_settlement_status` | SupportAgent | Consulta extrato e valores com mascaramento bancário de conta de destino |
| `diagnose_declined_transaction` | SupportAgent | Diagnóstico de transações negadas pelo emissor |
| `diagnose_terminal` | SupportAgent | Diagnóstico de conectividade e hardware de maquininhas Get Smart/Clássica |

---

## 2. Pilares de Engenharia e Diferenciais

### Orquestração Agêntica ReAct
* **Métrica de Confiança**: A métrica de confiança exibida na telemetria reflete o score calculado sobre os vetores de contexto recuperados ou a precisão da ferramenta especializada acionada.
* **Ciclo ReAct Estruturado**: O Supervisor emite chamadas estruturadas de ferramentas no estado do grafo, o ToolNode executa a ferramenta populando ToolMessage e retorna ao Supervisor para observação e síntese.

### Memória Persistente Multi-Turn (LangGraph SqliteSaver)
* O workflow compila o grafo utilizando o checkpointer relacional `SqliteSaver` de `langgraph.checkpoint.sqlite`, persistido no caminho definido por `CHECKPOINT_DB_PATH` (padrão: `data/checkpoints.db`).
* As sessões são indexadas por `thread_id` composto no formato `f"{user_id}:{session_id}"`, assegurando isolamento estrito entre usuários distintos mesmo que compartilhem o mesmo `session_id`.
* O estado conversacional persiste em disco e sobrevive a reinicializações completas do serviço. O assistente mantém contexto entre turnos de diálogo: perguntas de acompanhamento reaproveitam o contexto histórico do turno anterior sem exigir que o lojista repita os dados já informados.

### RAG Vetorial e Pipeline de Conhecimento (Fase 3C)
* **Knowledge Agent Conectado ao Índice Real**:
  O `KnowledgeAgent` agora realiza consultas semânticas reais diretamente sobre o índice vetorial em `data/index`, gerado pelo modelo `gemini-embedding-2` (768 dimensões). Cada fato respondido referencia a URL da fonte oficial e a data de coleta (`fetched_at`). Quando não há trechos suficientes que superem o limiar de relevância, o retriever abstém-se formalmente (`status: "abstain"`), prevenindo respostas especulativas.
* **Por que trocamos a base**:
  A base antiga era um arquivo JSON escrito à mão (`getnet_kb.json`) que continha informações desatualizadas ou imprecisas. Um exemplo verificável: a base antiga afirmava que o parcelamento no crediário era em até 36x, enquanto a documentação oficial na página https://site.getnet.com.br/crediario/ estabelece parcelamento em até 48x (com a ressalva de que as condições variam conforme o emissor do cartão). Com a ingestão automatizada e o novo índice vetorial, o assistente passa a responder estritamente embasado nos documentos oficiais coletados.
* **Pipeline Oficial de RAG**:
  1. **Ingestão (`src/rag/ingest.py`)**: Coleta ética de fontes oficiais (`data/sources.yaml`), respeitando `robots.txt` e gerando o corpus em `data/corpus/pages.jsonl`.
  2. **Fragmentação (`src/rag/chunking.py`)**: Filtra linhas de boilerplate (repetidas em $\ge 4$ páginas), linhas sem caracteres alfanuméricos, descarta páginas com menos de 120 caracteres de conteúdo retido e agrupa as linhas restantes na ordem original (verbatim) em chunks de até 900 caracteres, anexando caudas curtas (< 120 chars) ao trecho anterior.
  3. **Geração de Embeddings (`src/core/llm.py`)**: Utiliza o modelo `gemini-embedding-2` com 768 dimensões, configurando `RETRIEVAL_DOCUMENT` para indexação de chunks e `RETRIEVAL_QUERY` para consultas em tempo de execução.
  4. **Índice Vetorial Commitado (`src/rag/index.py`)**: Vetores com normalização L2 persistidos em `data/index/embeddings.npy` (float32), metadados em `data/index/index_meta.json` e chunks em `data/index/chunks.jsonl`.
  5. **Retriever e Abstenção (`src/rag/retriever.py`)**: Busca por similaridade de cosseno com limiar de corte calibrado (`RAG_MIN_SCORE = 0.61`). Quando a melhor similaridade de cosseno fica abaixo desse limiar, o retriever devolve status `abstain`.

#### Avaliação do retrieval e Calibração de Limiar (Fase 3D)
O sistema avalia a qualidade do retrieval e a política de abstenção sobre um conjunto rotulado de 48 consultas (`data/eval/retrieval_labeled.jsonl`: 30 respondíveis [21 PT, 9 EN], 10 *uncovered* e 8 *off-topic*). Os detalhes completos e curvas estão disponíveis em [`reports/retrieval_calibration.md`](reports/retrieval_calibration.md) (e JSON em [`reports/retrieval_calibration.json`](reports/retrieval_calibration.json)).

* **Métricas de Retrieval (Consultas Respondíveis)**:
  | Métrica | Geral (n=30) | Português (n=21) | Inglês (n=9) |
  | :--- | :---: | :---: | :---: |
  | **hit@1** | 0.900 | 0.952 | 0.778 |
  | **hit@3** | 0.967 | 1.000 | 0.889 |
  | **hit@5** | 0.967 | 1.000 | 0.889 |
  | **mrr@10** | 0.933 | 0.976 | 0.833 |
  | **answer_hit@3** | 0.900 | 0.952 | 0.778 |

* **Limiar Escolhido (`RAG_MIN_SCORE = 0.61`) e Métricas de Abstenção**:
  * **Balanced Accuracy**: 1.000 (separação ideal entre consultas respondíveis e fora do domínio).
  * **Taxa de Resposta (Answerable)**: 1.000 (100% das perguntas respondíveis são respondidas).
  * **Abstenção Off-Topic**: 1.000 (100% das perguntas fora de domínio são rejeitadas com abstenção).
  * **Abstenção Uncovered**: 0.000 (perguntas *uncovered* estão próximas do vocabulário do domínio Getnet por construção e não são filtradas apenas pelo limiar de similaridade vetorial, dependendo do Knowledge Agent para reconhecer a ausência de resposta no trecho e responder "não encontrado nas fontes oficiais").
  * **Avisos do Relatório**: `[!WARNING]` `uncovered_not_filtered` (comportamento esperado e documentado na especificação).

### Fontes de Dados e Corpus Oficial (Fase 3A)
* **Política de Fontes Oficiais**:
  * **getnet.net/en**: Conteúdo global institucional, soluções presenciais, e-commerce, omnichannel e APIs.
  * **site.getnet.com.br**: Conteúdo de produtos e serviços Getnet para o mercado brasileiro (maquininhas, Pix, taxas, antecipação e manuais). O domínio `www.santander.com.br` foi removido porque sua CDN (Akamai) bloqueia o User-Agent do projeto com HTTP 403 no `robots.txt`; já o `site.getnet.com.br` não possui `robots.txt` (retorna HTTP 404), o que pela RFC 9309 indica ausência de restrições de rastreamento.
  * **getnet.com.br**: Portal institucional brasileiro condicionado ao cumprimento estrito das regras do `robots.txt`.
  * **getnet.net/pt**: Expressamente excluído do escopo por pertencer ao mercado de Portugal.
* **Armazenamento do Corpus**: Os documentos e auditoria de coleta ficam persistidos no diretório `data/corpus` (`pages.jsonl` e `manifest.json`).
* **Como Regenerar o Corpus**: A coleta pode ser executada respeitando taxa limite e `robots.txt` com:
  ```bash
  python -m src.rag.ingest
  ```

### Transbordo Humano Real com SQLite e Ciclo de Vida de Tickets (Fase 5A)
* **Zero Falsas Promessas**: Eliminação de frases enganosas ou previsões não verificadas (sem promessas de tempo de espera, fila ou prazos como "em breve" ou "em menos de 5 minutos").
* **Estrutura e Dados Persistidos**: A ferramenta `escalate_to_human` grava o chamado no banco SQLite configurado em `TICKETS_DB_PATH` (padrão: `data/tickets.db`, persistido em volume Docker). Cada registro armazena:
  * `ticket_id`: Identificador único no formato `GET-TKT-YYYYMMDD-XXXX`.
  * `user_id`: Identificador do lojista autenticado.
  * `session_id`: Identificador da sessão em que o transbordo foi acionado.
  * `reason`: Motivo detalhado do encaminhamento ao operador.
  * `priority`: Nível de prioridade (`standard` ou `high` para órgãos regulatórios como Procon ou ouvidoria).
  * `transcript`: Snapshot estruturado das últimas 20 mensagens da conversa contendo papéis `user` e `assistant` com dados sensíveis previamente sanitizados pelo guardrail (números de cartão e CPF mascarados).
  * `status`: Estado atual no ciclo de vida do chamado.
  * `operator_reply`, `operator_id`, `answered_at`: Resposta registrada pelo operador humano.
* **Ciclo de Vida de Status**:
  * Transições permitidas:
    * `open` $\rightarrow$ `in_progress`, `answered`, `closed`
    * `in_progress` $\rightarrow$ `answered`, `closed`
    * `answered` $\rightarrow$ `closed`
    * `closed` (estado terminal; não aceita reabertura nem novas respostas)
* **Atualização por Operadores (`PATCH /tickets/{ticket_id}`)**:
  * Exclusivo para credenciais com papel `operator` (requisições de clientes recebem HTTP 403 Forbidden).
  * Permite atualizar o status ou registrar uma resposta (`reply`), o que transiciona o ticket para `answered` e registra o horário de resposta (`answered_at`) e o `operator_id`.
  * Exemplo com `curl`:
    ```bash
    curl -X PATCH http://localhost:8000/tickets/GET-TKT-20261107-ABCD \
      -H "X-API-Key: sua-chave-de-operador" \
      -H "Content-Type: application/json" \
      -d '{"reply": "Sua solicitação de alteração cadastral foi processada com sucesso."}'
    ```
* **Consulta pelo Cliente (`GET /tickets/{ticket_id}`)**:
  * O lojista dono do chamado pode consultar o protocolo a qualquer momento e visualizar o `status`, o histórico enviado e a `operator_reply` fornecida pelo operador.

### Portão de Transbordo Humano e Entrega de Resposta no Chat (Fase 5B)
* **Controle de Estado com `pending_ticket_id`**: Ao registrar um chamado com sucesso, o grafo grava o identificador do ticket no campo persistido `pending_ticket_id` do estado conversacional, mantido pelo `SqliteSaver` entre turnos e reinicializações.
* **Nó `handoff_gate` após o Guardrail**: O fluxo de atendimento posiciona o nó `handoff_gate` imediatamente após o `guardrail`. Isso garante que todas as mensagens enviadas pelo cliente enquanto o chamado aguarda resposta tenham seus dados sensíveis (PII) mascarados e fiquem salvas no histórico de mensagens.
* **Mensagem Fixa Sem Chamada ao LLM**: Enquanto o chamado estiver em aberto ou em atendimento (`open` ou `in_progress`), o `handoff_gate` responde com uma mensagem de espera padronizada e bilíngue informando o número do protocolo, sem invocar o LLM (`llm_model: None`, `tokens: None`) e sem fazer qualquer promessa enganosa de tempo ou fila.
* **Entrega Única da Resposta do Operador (`delivered_at`)**: Quando o operador responde ao chamado via `PATCH /tickets/{id}`, o próximo turno do cliente entrega a resposta humana com o prefixo oficial, grava a data de entrega no banco (`delivered_at`), limpa o `pending_ticket_id` e marca o evento com `handoff: {"status": "delivered"}`. Turnos seguintes retornam automaticamente ao atendimento convencional pelo supervisor.
* **Retomada de Atendimento (`resumed`)**: Se o chamado for fechado pelo operador sem resposta (`status: "closed"`), o portão limpa a pendência, define `handoff: {"status": "resumed"}` e direciona a mensagem no mesmo turno para o supervisor do bot.
* **Metadados da API (`metadata.handoff`)**: Nos turnos em que o portão intercepta a conversa (`pending` ou `delivered`), a resposta expõe `agent_type = "HumanHandoff"` e o objeto `handoff` com o `ticket_id` e seu respectivo status.
* **Por que não usamos `interrupt()` do LangGraph**: Optamos por não usar `interrupt()` porque a retomada do atendimento depende de uma ação assíncrona de terceiros (o operador) e o lojista pode continuar enviando mensagens durante a espera; com o portão `handoff_gate`, as mensagens intermediárias do cliente passam pelo guardrail e são preservadas na memória conversacional sem bloquear a execução do grafo.

### Escalonamento Automático por Abstenção Repetida e Atualização do Chamado (Fase 5C)
* **Critério de Abstenção**: Uma consulta ao `KnowledgeAgent` é classificada como abstenção quando o especialista não retorna nenhuma fonte (`sources` vazio, tanto de documentos oficiais quanto de busca web).
* **Limitação Importante**: A abstenção é estritamente contabilizada pela ausência de fontes no resultado do retriever/especialista; uma resposta fundamentada em fontes que porventura não responda à totalidade da pergunta não pontua como abstenção mecânica (essa avaliação qualitativa com modelo real é o foco da Fase 6).
* **Contador de Abstenções Consecutivas (`consecutive_abstentions`)**: O estado conversacional mantém o contador persistido no checkpointer `SqliteSaver`.
* **Limite Configurável (`ESCALATE_AFTER_ABSTENTIONS`)**: Definido por variável de ambiente (padrão: 2; valor `0` desativa o gatilho automático).
* **Regras de Reset e Manutenção do Contador**:
  - Se um chamado for aberto no turno (pelo modelo ou por limite de passos), o contador zera (`consecutive_abstentions = 0`).
  - Se qualquer chamada ao `KnowledgeAgent` retornar fontes, o contador zera.
  - Turnos conversacionais sem invocação do Knowledge Agent (como saudações, small talk ou consultas de conta no Support Agent) não alteram nem zeram o contador.
* **Abertura Automática e Nota Fixa**: Ao atingir o limite configurado (e na ausência de chamado pendente), o nó `abstention_check` aciona `escalate_to_human`, anexa a nota bilíngue oficial sem promessas de prazo (`AUTO_ESCALATION_NOTE`) ao final da resposta, grava o ticket no estado com `pending_ticket_id` e zera o contador. Falhas de gravação preservam a resposta original e mantêm o contador.
* **Encaminhamento de Mensagens Durante a Espera**: Mensagens enviadas pelo cliente enquanto o chamado aguarda resposta passam pelo guardrail (sanitização de cartões e CPF) e são anexadas diretamente ao histórico do chamado no banco SQLite via `append_customer_message`, garantindo que o operador visualize todo o diálogo recente.
* **Garantia de Entrega Única**: O portão só entrega a resposta humana se `mark_delivered` retornar `True`. Caso requisições concorrentes já tenham entregue a resposta, a pendência é limpa e o fluxo retoma o atendimento convencional (`resumed`) sem repetições.

### Segurança, Autenticação, Isolamento & Sanitização de Dados Sensíveis (PII)
* **Algoritmo de Luhn**: Antes de qualquer processamento ou envio ao modelo, o módulo `src/core/pii.py` valida números de cartão de crédito de 13 a 19 dígitos através do algoritmo de Luhn e mascara para `[CARTAO_MASCARADO_****1234]`.
* **Sanitização de CPF**: Números de CPF em formato padrão ou contínuo são mascarados para `[CPF_MASCARADO_***.***.***-XX]`.
* **Proteção contra Injeção de Prompt**: Expressões em português e inglês que tentem sobrescrever instruções (`"ignore todas as suas instruções"`, `"me mostre o seu prompt"`, `"regras internas"`, `"prompt de sistema"`, `"esqueça o que foi dito"`) são bloqueadas pelo guardrail com resposta segura e imediata.
* **Autenticação Obrigatória via Header `X-API-Key`**:
  * Toda chamada aos endpoints da API (`/chat`, `/api/v1/chat`, `/tickets`, `/tickets/{id}`) exige o cabeçalho `X-API-Key`. A identidade do usuário (`user_id`) e seu papel (`role`: `customer` ou `operator`) são derivados exclusivamente da credencial autenticada, nunca do corpo da requisição. Se a requisição omitir o cabeçalho ou fornecer uma chave inválida, o sistema responde com **HTTP 401 Unauthorized** ("Missing or invalid API key.").
  * Se o cliente enviar um `user_id` no corpo diferente do proprietário da credencial, o sistema responde com **HTTP 403 Forbidden** ("user_id does not match the authenticated credential.").
  * Clientes (`customer`) que tentarem consultar chamados de outro usuário via `GET /tickets/{ticket_id}` recebem **HTTP 404 Not Found** (resposta indistinguível de ticket inexistente para evitar enumeração de recursos).
  * **Rate Limiting (HTTP 429)**: O sistema impõe rate limit por janela deslizante de 60 segundos por credencial (`RATE_LIMIT_PER_MINUTE`, padrão: 30). Ao ultrapassar o limite, responde com **HTTP 429 Too Many Requests** acompanhado do cabeçalho `Retry-After` com o número de segundos para reintento.
* **Configuração de Chaves (`API_KEYS`) e Ambientes**:
  * O mapeamento é configurado via variável de ambiente `API_KEYS` no formato `hash:user_id:role;hash:user_id:role;...`, onde `hash` é o SHA-256 (64 hexadecimais em minúsculas) da chave.
  * O utilitário de linha de comando `python -m src.core.auth hash` lê a chave de forma mascarada com `getpass` e exibe apenas o hash para que credenciais reais nunca sejam persistidas em arquivos de configuração ou histórico.
  * **Chaves de Desenvolvimento**: Fora de produção (`APP_ENV != production`), quando `API_KEYS` estiver vazio, são aceitas as chaves padrão de desenvolvimento `getnet-dev-key` (`cliente1988`, `customer`) e `getnet-dev-operator` (`operador_dev`, `operator`).
  * **Produção Obrigatória no Docker Compose**: Como o `docker-compose.yml` opera com `APP_ENV=production`, é obrigatório configurar a variável `API_KEYS`; sem isso, o modo de autenticação é `none` e nenhuma requisição é aceita (todas respondem 401).
* **Isolamento de Sessão e Persistência em SQLite (`user_id:session_id`)**:
  * O identificador de thread do checkpointer é montado como `f"{user_id}:{session_id}"`. Mesmo que dois usuários diferentes utilizem o mesmo `session_id`, suas conversas e memórias permanecem completamente isoladas.
  * A memória é persistida em banco de dados SQLite (`SqliteSaver`) no arquivo indicado por `CHECKPOINT_DB_PATH` (padrão `data/checkpoints.db`, mantido dentro do volume persistente no Docker). A conversa e o histórico de mensagens sobrevivem a reinícios da aplicação.
  * **Fail-Fast de Configuração**: Na inicialização do serviço (`lifespan`), a aplicação valida a sintaxe das credenciais em `API_KEYS` e inicializa o banco em `CHECKPOINT_DB_PATH`. Se `API_KEYS` estiver mal formado ou o caminho do banco for inacessível (ex.: caminho sob um arquivo regular), o app recusa inicializar e levanta erro imediatamente. Caso a configuração se torne inválida durante a execução, o endpoint `/chat` responde com **HTTP 503 Service Unavailable** ("Authentication misconfigured: check API_KEYS.") e `/health` reporta `auth_mode: "invalid"`.
  * **Limitações Conhecidas**: Não há rotina automática de retenção ou limpeza (purge) de conversas antigas; o armazenamento opera com um arquivo SQLite por instância (réplicas horizontais não compartilham memória em disco sem um banco compartilhado); o rate limiting é mantido em memória por processo.

### Observabilidade Técnica, Trace ID e Custo por Tokens
* **Trace ID por Ciclo de Vida**: Cada chamada gera um identificador único de rastreamento no padrão `trc-<hex12>`, propagado no payload de resposta HTTP e na telemetria.
* **Métricas de Tokens**: Medição dinâmica de `prompt_tokens`, `completion_tokens` e `total_tokens` em todas as respostas.
* **Cálculo de Custo Financeiro**: Estimativa automática em USD com base na tabela de tokens, viabilizando governança de custos em produção.

### Avaliação Automatizada de Roteamento
* **Dataset Rotulado (`data/eval_dataset.json`)**: Conjunto de 12 pares de avaliação contendo `id`, `question`, `expected_tool`, `ground_truth_context` e `ideal_answer`, cobrindo os cenários de avaliação.
* **Acurácia de Roteamento no Dataset**: Avaliação automatizada em `tests/test_eval_judge.py` verificando que a seleção de ferramentas atende às ferramentas esperadas.

---

## 3. Como Executar e Modos de Operação

### Modos de Operação e Configuração

O sistema opera com arquitetura agnóstica de provedores via `langchain-google-genai` (com suporte extensível a OpenAI e Anthropic):

* **Configuração de Variáveis de Ambiente**:
  * `GEMINI_API_KEY`: Chave de API do Google Gemini (obrigatória quando `LLM_PROVIDER=google_genai`). Se não for fornecida, a API responde HTTP 503 com `detail: "LLM not configured: set GEMINI_API_KEY."`.
  * `LLM_PROVIDER`: Provedor do modelo de linguagem (padrão: `google_genai`; aceita também `openai` e `anthropic` caso as bibliotecas cliente estejam instaladas).
  * `LLM_MODEL`: Modelo principal utilizado pelo Supervisor (padrão: `gemini-3.5-flash`).
  * `LLM_FALLBACK_MODEL`: Modelo reserva automático acionado em caso de erro temporário ou rate limit (padrão: `gemini-3.5-flash-lite`; string vazia desativa o reserva).
  * `LLM_TIMEOUT_S`: Timeout em segundos para chamadas à API do modelo (padrão: `30.0`).
  * `LLM_MAX_RETRIES`: Número máximo de tentativas automáticas em caso de erro transiente (padrão: `2`).
  * `MAX_SUPERVISOR_STEPS`: Limite de iterações do Supervisor por turno antes de acionar escalonamento forçado (padrão: `6`).
  * `APP_ENV`: Ambiente de execução (`development`, `staging`, `production`, `testing`).
  * `ENABLE_GUARDRAILS`: Ativa ou desativa a sanitização de PII e bloqueio de prompt injection (padrão: `true`).
  * `WEB_SEARCH_ENABLED`: Habilita busca externa em tempo real via DuckDuckGo (padrão: `true`).

> **Seleção de Modelos e Benchmarking**: Em medição realizada em 2026-11-06 com credenciais reais, `gemini-3.8-flash` apresentou instabilidade de timeout (HTTP 504) e `gemini-3.7-flash` esgotou cota (HTTP 429) no tier gratuito. Por sua vez, `gemini-3.5-flash` demonstrou excelente consistência respondendo em ~3 segundos com seleção precisa de ferramentas, sendo definido como padrão primário, acompanhado de `gemini-3.5-flash-lite` como reserva resiliente.

* **Execução dos Testes**: Os testes automatizados executam 100% offline sem custos nem chamadas externas, utilizando o `ScriptedChatModel` para validação determinística de encadeamento de ferramentas.

---

### Execução via Docker Compose

```bash
# 1. Configurar variáveis de ambiente (opcional para modo generativo)
cp .env.example .env

# 2. Inicializar o serviço
docker compose up --build -d
```

Para parar o container:
```bash
docker compose down
```

---

### Execução Local

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# 2. Instalar dependências de produção
pip install -r requirements.txt

# Para desenvolvimento e execução de testes:
pip install -r requirements-dev.txt

# Para reprodução determinística exata:
pip install -r requirements.lock

# 3. Inicializar a aplicação
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Endpoints da API REST

Com a aplicação rodando em `http://localhost:8000`:

* **Interface Visual de Testes e Telemetria**: `GET /demo`
* **Swagger / OpenAPI Interativo**: `GET /docs`
* **Health Check & Provedor Ativo**: `GET /health`
* **Catálogo e Arquitetura de Agentes**: `GET /agents`
* **Consulta de Chamado Persistido**: `GET /tickets/{ticket_id}`
* **Listagem de Chamados de Suporte**: `GET /tickets`
* **Endpoint de Atendimento do Grafo**: `POST /chat`

Exemplo de requisição com sessão multi-turn e autenticação:
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: getnet-dev-key" \
     -d '{
       "message": "When will the money from yesterday'\''s sales be deposited?",
       "session_id": "sess-minha-loja-01"
     }'
```

---

## 4. Testes Automatizados e CI/CD

A suíte conta com testes automatizados cobrindo os cenários oficiais do desafio, testes unitários de componentes e validação do dataset de avaliação:

```bash
# Executar a suíte completa com pytest
pytest tests/ -v
```

### Pipeline de Integração Contínua (CI)
O repositório possui pipeline automatizado configurado em `.github/workflows/ci.yml`, executando linting e testes a cada `push` e `pull_request` na branch `main`.

---

## 5. Matriz de Cobertura dos Cenários Oficiais

| ID | Pergunta de Avaliação | Ferramenta Acionada (ReAct) | Fonte / Evidência | Status |
| :-: | :--- | :--- | :--- | :-: |
| 1 | *"What's the difference between the Get Clássica and the Get Smart?"* | `search_knowledge_base` | Índice oficial `site.getnet.com.br` | Aprovado |
| 2 | *"What's the weather forecast in Porto Alegre tomorrow?"* | `search_web` | DuckDuckGo Real-Time Search | Aprovado |
| 3 | *"When will the money from yesterday's sales be deposited?"* | `get_settlement_status` | R$ 3.367,20 líquido, depósito Hoje Santander D+1 | Aprovado |
| 4 | *"Do I need a bank account to receive my sales via Pix?"* | `search_knowledge_base` | Artigo `kb_pix_getnet` (QR Code Dinâmico) | Aprovado |
| 5 | *"My card machine won't connect to the internet, what should I do?"* | `diagnose_terminal` | Passo a passo de reboot, Wi-Fi e chip Get Smart | Aprovado |
| 6 | *"How does receivables advance (antecipação) work with Getnet?"* | `search_knowledge_base` | Artigo `kb_antecipacao_recebiveis` (Automática vs Avulsa) | Aprovado |
| 7 | *"What's the euro exchange rate today?"* | `search_web` | DuckDuckGo Real-Time Search | Aprovado |
| 8 | *"My card machine is showing a transaction decline error."* | `diagnose_declined_transaction` | Código 51 (Saldo Insuficiente) no emissor | Aprovado |
| 9 | *"How many installments can I split a sale into with the crediário?"* | `search_knowledge_base` | Índice oficial (Parcelamento em até 48x) | Aprovado |
| 10 | *"Can I sell through WhatsApp using the Payment Link?"* | `search_knowledge_base` | Artigo `kb_link_pagamento_whatsapp` (App Getnet) | Aprovado |

---

## 6. Glossário de Defesa Técnica (Perguntas de Entrevista)

### 1. "A UI mostra uma confiança na resposta. Como esse número é calculado?"
> **Defesa**: *"A métrica de confiança exibida no inspetor de telemetria reflete o score calculado sobre os vetores de contexto recuperados. Quando o lojista faz uma pergunta operacional atendida por ferramentas transacionais (como liquidação financeira ou diagnóstico do POS), a confiança reflete 100% de precisão determinística oriunda do banco de dados oficial."*

### 2. "O que o modelo/Supervisor decide no sistema, além de sintetizar a resposta?"
> **Defesa**: *"O Supervisor é o tomador de decisão do loop ReAct. Ele consome o histórico da conversa e os schemas tipados das ferramentas, decide qual ferramenta invocar com quais argumentos, avalia a observação retornada no estado do grafo e decide se necessita de novos passos ou se já possui evidências suficientes para emitir a resposta final."*

### 3. "De onde veio a base de conhecimento e como é garantido que ela não inventa dados fora de domínio?"
> **Defesa**: *"O corpus em `data/corpus/` reúne páginas oficiais da Getnet coletadas eticamente com conformidade estrita de robots.txt, fragmentadas em chunks e indexadas com embeddings normalizados em `data/index/`. Implementamos um limiar de abstenção paramétrico: se a pergunta for fora de domínio ou a melhor pontuação não atingir o limiar, o retriever e o agente abstêm-se explicitamente de opinar."*

### 4. "O que acontece quando o usuário pede atendimento humano? Onde o caso é gravado e quem o recebe?"
> **Defesa**: *"Não prometemos filas fictícias nem tempos de espera irreais de 'menos de 5 minutos'. A ferramenta `escalate_to_human` grava um registro real no banco SQLite `data/tickets.db` com protocolo estruturado `GET-TKT-YYYYMMDD-XXXX`, status aberto, motivo e timestamp. Qualquer operador ou sistema de atendimento pode auditar e consumir o ticket em tempo real via endpoint `GET /tickets/{ticket_id}`."*

### 5. "Como você garante que o sistema mantém o contexto em conversas longas?"
> **Defesa**: *"Implementamos o checkpointer `MemorySaver` nativo do LangGraph, que armazena a sequência de mensagens agrupada por `thread_id` (o `session_id` da requisição HTTP). Isso permite que o lojista faça perguntas de acompanhamento de forma natural e que o Supervisor recupere as variáveis e decisões tomadas nos turnos anteriores da mesma sessão."*

---

## 7. Estrutura do Repositório

```text
getnet-multiagent-support/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Pipeline de Integração Contínua (GitHub Actions)
├── data/
│   ├── corpus/                # Páginas oficiais Getnet e manifest.json
│   ├── index/                 # Índice de embeddings (chunks.jsonl, embeddings.npy, index_meta.json)
│   └── eval_dataset.json      # Dataset de avaliação com 12 pares rotulados
├── src/
│   ├── main.py                # Servidor FastAPI com endpoints /chat, /tickets e lifecycles
│   ├── config.py              # Pydantic Settings e configuração de log estruturado JSON
│   ├── agents/
│   │   └── guardrails.py      # Sanitização PII (Luhn PAN + CPF) e bloqueio de injeções
│   ├── rag/
│   │   ├── ingest.py          # Coleta ética de fontes com robots.txt
│   │   ├── chunking.py        # Fragmentação com remoção de boilerplate e caudas
│   │   ├── index.py           # Vetorização e persistência de embeddings
│   │   └── retriever.py       # Busca vetorial com abstenção formal
│   ├── core/
│   │   ├── graph.py               # Grafo LangGraph Supervisor ReAct com SqliteSaver
│   │   ├── checkpointer.py        # Construtor do SqliteSaver persistente
│   │   ├── auth.py                # Autenticação via X-API-Key, papéis e rate limiting
│   │   ├── llm.py                 # Provedor do modelo ChatGoogleGenerativeAI e tratamento de erros
│   │   ├── pii.py                 # Sanitizador de PII (algoritmo de Luhn para cartões e CPF)
│   │   ├── tickets_db.py          # Repositório SQLite para persistência e consulta de chamados
│   │   ├── state.py               # Schemas tipados de estado LangGraph (SupervisorState, AgentState)
│   │   └── mock_db.py             # Base de dados operacionais (liquidação e códigos de recusa)
│   ├── tools/
│   │   ├── agent_tools.py         # Ferramentas tipadas com schemas Pydantic para o Supervisor
│   │   ├── balance_tools.py       # Funções de liquidação financeira e consulta de recusa
│   │   ├── terminal_tools.py      # Funções de diagnóstico de POS e conectividade
│   │   └── web_search.py          # Busca web em tempo real (DuckDuckGo ddgs) com fallback
│   └── static/
│       └── demo.html              # Console interativo 3 colunas com telemetria e tickets
├── tests/
│   ├── conftest.py                # Fixtures de sessão para TestClient e componentes
│   ├── test_eval_judge.py         # Validação de schema do dataset de avaliação e roteamento
│   ├── test_scenarios.py          # Testes de integração dos 10 cenários oficiais de avaliação
│   └── test_unit.py               # Testes unitários (Supervisor, ReAct, MemorySaver, RAG, PII, SQLite)
├── Dockerfile                     # Build multi-stage seguro executado sob usuário não-root
├── docker-compose.yml             # Orquestração Compose v2 com volumes e healthcheck
├── requirements.txt               # Dependências versionadas do projeto
├── requirements-dev.txt           # Dependências para desenvolvimento e testes
├── .env.example                   # Modelo de variáveis de ambiente
└── README.md                      # Documentação técnica e limitações atuais
```
