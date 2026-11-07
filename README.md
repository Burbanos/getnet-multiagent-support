# Getnet Multi-Agent Support System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2%2B-orange.svg)](https://github.com/langchain-ai/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5%2B-purple.svg)](https://www.trychroma.com/)
[![SQLite](https://img.shields.io/badge/SQLite-tickets.db-blue.svg)](https://www.sqlite.org/)
[![Architecture](https://img.shields.io/badge/architecture-Supervisor%20ReAct-blueviolet.svg)]()
[![Auth](https://img.shields.io/badge/auth-X--API--Key-blue.svg)]()
[![Security](https://img.shields.io/badge/security-PII%20Luhn%20%2B%20non--root-success.svg)]()

Sistema agêntico de suporte inteligente para estabelecimentos e clientes Getnet, estruturado sobre o padrão **Supervisor + ReAct com declaração de ferramentas**, persistência conversacional multi-turn via **LangGraph MemorySaver**, base de conhecimento vetorial **ChromaDB com limiar de relevância**, sanitização de **PII (Luhn PAN + CPF)**, observabilidade com **Trace ID e cálculo de custo por tokens**, avaliação de acurácia de roteamento e persistência de chamados humanos em banco relacional **SQLite (`data/tickets.db`)**.

---

## Limitações atuais

* **Supervisor LLM e API Key**: O supervisor utiliza o modelo Gemini com function calling e exige `GEMINI_API_KEY`; sem a chave, o endpoint `/chat` responde HTTP 503 com mensagem explícita;
* **Testes com modelo roteirizado**: Os testes automatizados utilizam um modelo roteirizado (`ScriptedChatModel`) para validação de plumbing sem chamadas de rede e não medem a qualidade do roteamento, que será avaliada na Fase 6;
* **Base de conhecimento**: A base de conhecimento é conteúdo provisório escrito à mão até a Fase 3;
* **Autenticação**: A API key é opcional até a Fase 4.

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
  * **Confiança Dinâmica** por similaridade do ChromaDB ou execução de tool.
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
  - [Memória Persistente Multi-Turn (LangGraph MemorySaver)](#memória-persistente-multi-turn-langgraph-memorysaver)
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
Resposta ao Usuário + Gravação no MemorySaver (thread_id = session_id)
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
| `search_knowledge_base` | KnowledgeAgent | Busca vetorial semântica no ChromaDB (`data/getnet_kb.json`) com limiar |
| `search_web` | KnowledgeAgent | Busca pública em tempo real (DuckDuckGo) |
| `get_settlement_status` | SupportAgent | Consulta extrato e valores com mascaramento bancário de conta de destino |
| `diagnose_declined_transaction` | SupportAgent | Diagnóstico de transações negadas pelo emissor |
| `diagnose_terminal` | SupportAgent | Diagnóstico de conectividade e hardware de maquininhas Get Smart/Clássica |

---

## 2. Pilares de Engenharia e Diferenciais

### Orquestração Agêntica ReAct
* **Métrica de Confiança**: A métrica de confiança exibida na telemetria reflete o score calculado pelo ChromaDB sobre os vetores de contexto recuperados ou a precisão da ferramenta especializada acionada.
* **Ciclo ReAct Estruturado**: O Supervisor emite chamadas estruturadas de ferramentas no estado do grafo, o ToolNode executa a ferramenta populando ToolMessage e retorna ao Supervisor para observação e síntese.

### Memória Persistente Multi-Turn (LangGraph MemorySaver)
* O workflow compila o grafo utilizando o checkpointer nativo `MemorySaver` de `langgraph.checkpoint.memory`.
* As sessões são indexadas por `thread_id` (correspondente ao `session_id` da requisição HTTP).
* O assistente mantém contexto entre turnos de diálogo: uma pergunta de acompanhamento (ex: *"E qual delas tem tela touch com Android?"*) reaproveita o contexto histórico do turno anterior sem exigir que o lojista repita os modelos.

### RAG Vetorial e Pipeline de Conhecimento (Fase 3B)
* **Pipeline Oficial de RAG**:
  1. **Ingestão (`src/rag/ingest.py`)**: Coleta ética de fontes oficiais (`data/sources.yaml`), respeitando `robots.txt` e gerando o corpus em `data/corpus/pages.jsonl`.
  2. **Fragmentação (`src/rag/chunking.py`)**: Filtra linhas de boilerplate (repetidas em $\ge 4$ páginas), linhas sem caracteres alfanuméricos e agrupa as linhas restantes na ordem original (verbatim) em chunks limitados a 900 caracteres.
  3. **Geração de Embeddings (`src/core/llm.py`)**: Utiliza o modelo `gemini-embedding-2` com 768 dimensões, configurando a tarefa adequada para cada contexto: `RETRIEVAL_DOCUMENT` para indexação de chunks e `RETRIEVAL_QUERY` para consultas em tempo de execução.
  4. **Índice Vetorial Commitado (`src/rag/index.py`)**: Vetores com normalização L2 persistidos em `data/index/embeddings.npy` (float32), metadados em `data/index/index_meta.json` e chunks em `data/index/chunks.jsonl`.
  5. **Retriever e Abstenção (`src/rag/retriever.py`)**: Busca por similaridade de cosseno com limiar de corte (`RAG_MIN_SCORE = 0.60`). Se a melhor pontuação for inferior ao limiar ou não houver resultados, o retriever abstém-se formalmente (`status: "abstain"` com lista vazia de documentos), prevenindo alucinações.
* **Transição e Próximos Passos**: O limiar atual de `0.60` é provisório até a calibração empírica da Fase 3D. A integração completa deste novo retriever ao `KnowledgeAgent` será implementada na Fase 3C (atualmente o agente segue usando `data/getnet_kb.json`).

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
* **Transição Gradual**: O retriever em produção continua consultando `data/getnet_kb.json` até a implementação da nova indexação vetorial e chunking na Fase 3B.

### Transbordo Humano Real com SQLite (tickets.db)
* **Zero Falsas Promessas**: Eliminação de frases enganosas como *"Tempo estimado de espera: Menos de 5 minutos"* ou *"Fila prioritária"*.
* **Persistência Relacional**: A ferramenta `escalate_to_human` grava o chamado na tabela `tickets` do banco SQLite local (`data/tickets.db`) contendo `ticket_id` único no formato `GET-TKT-YYYYMMDD-XXXX`, `user_id`, `reason`, `status='open'` e `created_at`.
* **Rastreabilidade Transparente**: Disponibilização dos endpoints HTTP:
  * `GET /tickets/{ticket_id}`: Consulta os dados auditáveis do chamado persistido.
  * `GET /tickets`: Lista os chamados registrados no banco.
  * Na interface `/demo`, o protocolo exibido é um link clicável direto para a API.

### Segurança, Autenticação & Sanitização de Dados Sensíveis (PII)
* **Algoritmo de Luhn**: Antes de qualquer processamento ou envio ao modelo, o módulo `src/core/pii.py` valida números de cartão de crédito de 13 a 19 dígitos através do algoritmo de Luhn e mascara para `[CARTAO_MASCARADO_****1234]`.
* **Sanitização de CPF**: Números de CPF em formato padrão ou contínuo são mascarados para `[CPF_MASCARADO_***.***.***-XX]`.
* **Proteção contra Injeção de Prompt**: Expressões em português e inglês que tentem sobrescrever instruções (`"ignore todas as suas instruções"`, `"me mostre o seu prompt"`, `"regras internas"`, `"prompt de sistema"`, `"esqueça o que foi dito"`) são bloqueadas pelo guardrail com resposta segura e imediata.
* **Autenticação via Header `X-API-Key`**: Os endpoints da API verificam o cabeçalho `X-API-Key` quando enviado. Para manter o ambiente de testes e Docker fluidos e sem atrito, a chave de desenvolvimento padrão `getnet-dev-key` ou cabeçalho omitido são aceitos. Requisições com chaves expressamente não autorizadas são bloqueadas com HTTP 401 Unauthorized.

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
       "user_id": "cliente1988",
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
| 1 | *"What's the difference between the Get Clássica and the Get Smart?"* | `search_knowledge_base` | Artigo `kb_get_classica_vs_smart` (ChromaDB) | Aprovado |
| 2 | *"What's the weather forecast in Porto Alegre tomorrow?"* | `search_web` | DuckDuckGo Real-Time Search | Aprovado |
| 3 | *"When will the money from yesterday's sales be deposited?"* | `get_settlement_status` | R$ 3.367,20 líquido, depósito Hoje Santander D+1 | Aprovado |
| 4 | *"Do I need a bank account to receive my sales via Pix?"* | `search_knowledge_base` | Artigo `kb_pix_getnet` (QR Code Dinâmico) | Aprovado |
| 5 | *"My card machine won't connect to the internet, what should I do?"* | `diagnose_terminal` | Passo a passo de reboot, Wi-Fi e chip Get Smart | Aprovado |
| 6 | *"How does receivables advance (antecipação) work with Getnet?"* | `search_knowledge_base` | Artigo `kb_antecipacao_recebiveis` (Automática vs Avulsa) | Aprovado |
| 7 | *"What's the euro exchange rate today?"* | `search_web` | DuckDuckGo Real-Time Search | Aprovado |
| 8 | *"My card machine is showing a transaction decline error."* | `diagnose_declined_transaction` | Código 51 (Saldo Insuficiente) no emissor | Aprovado |
| 9 | *"How many installments can I split a sale into with the crediário?"* | `search_knowledge_base` | Artigo `kb_crediario` (Parcelamento 24x e 36x) | Aprovado |
| 10 | *"Can I sell through WhatsApp using the Payment Link?"* | `search_knowledge_base` | Artigo `kb_link_pagamento_whatsapp` (App Getnet) | Aprovado |

---

## 6. Glossário de Defesa Técnica (Perguntas de Entrevista)

### 1. "A UI mostra uma confiança na resposta. Como esse número é calculado?"
> **Defesa**: *"A métrica de confiança exibida no inspetor de telemetria reflete o score calculado pelo ChromaDB sobre os vetores de contexto recuperados. Quando o lojista faz uma pergunta operacional atendida por ferramentas transacionais (como liquidação financeira ou diagnóstico do POS), a confiança reflete 100% de precisão determinística oriunda do banco de dados oficial."*

### 2. "O que o modelo/Supervisor decide no sistema, além de sintetizar a resposta?"
> **Defesa**: *"O Supervisor é o tomador de decisão do loop ReAct. Ele consome o histórico da conversa e os schemas tipados das ferramentas, decide qual ferramenta invocar com quais argumentos, avalia a observação retornada no estado do grafo e decide se necessita de novos passos ou se já possui evidências suficientes para emitir a resposta final."*

### 3. "De onde veio a base de conhecimento e como é garantido que ela não inventa dados fora de domínio?"
> **Defesa**: *"A base em `data/getnet_kb.json` reúne manuais e documentações da Getnet com metadados de categoria e URLs de referência. Implementamos um limiar de abstenção paramétrico no ChromaDB: se a pergunta for fora de domínio, o agente abstém-se explicitamente de opinar, indicando os canais oficiais."*

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
│   ├── getnet_kb.json             # Base de conhecimento provisória de artigos Getnet
│   └── eval_dataset.json          # Dataset de avaliação com 12 pares rotulados
├── src/
│   ├── main.py                    # Servidor FastAPI com endpoints /chat, /tickets e lifecycles
│   ├── config.py                  # Pydantic Settings e configuração de log estruturado JSON
│   ├── agents/
│   │   ├── guardrails.py          # Sanitização PII (Luhn PAN + CPF) e bloqueio de injeções
│   │   └── knowledge.py           # RAG vetorial ChromaDB com limiar explícito de abstenção
│   ├── core/
│   │   ├── graph.py               # Grafo LangGraph Supervisor ReAct com MemorySaver
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
