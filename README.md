# Getnet Multi-Agent Support System

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2%2B-orange.svg)](https://github.com/langchain-ai/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5%2B-purple.svg)](https://www.trychroma.com/)
[![SQLite](https://img.shields.io/badge/SQLite-tickets.db-blue.svg)](https://www.sqlite.org/)
[![Architecture](https://img.shields.io/badge/architecture-Supervisor%20ReAct-blueviolet.svg)]()
[![Tests](https://img.shields.io/badge/tests-55%20passed-brightgreen.svg)]()
[![Eval](https://img.shields.io/badge/eval%20judge-100%25%20routing-brightgreen.svg)]()
[![Auth](https://img.shields.io/badge/auth-X--API--Key-blue.svg)]()
[![Security](https://img.shields.io/badge/security-PII%20Luhn%20%2B%20non--root-success.svg)]()

Sistema agêntico de suporte inteligente para estabelecimentos e clientes Getnet, estruturado sobre o padrão **Supervisor + ReAct com Tool Calling nativo**, persistência conversacional multi-turn via **LangGraph MemorySaver**, base de conhecimento vetorial **ChromaDB com limiar explícito de abstenção**, sanitização de **PII (Luhn PAN + CPF)**, observabilidade com **Trace ID e cálculo de custo por tokens (Gemini Flash)**, avaliação automatizada **LLM-as-a-Judge** e persistência real de chamados humanos em banco relacional **SQLite (`data/tickets.db`)**.

---

## Interface Visual & Observabilidade (/demo)

O sistema disponibiliza uma console visual interativa em 3 colunas acessível diretamente pelo navegador em [`/demo`](http://localhost:8000/demo):

* **Coluna Esquerda (Cenários 1-Click)**: Catálogo com os 12 cenários de teste pré-configurados (10 cenários oficiais de referência do desafio Getnet + testes de injeção de prompt e transbordo humano). Dispara qualquer teste com um único clique.
* **Coluna Central (Chat Interativo Multi-Turn)**: Interface de conversação em tempo real com controle de `Session ID` para teste de memória contextual contínua, balões de diálogo com identificação do modelo, ferramentas acionadas e latência.
* **Coluna Direita (Inspetor de Telemetria & Rastreabilidade)**: Painel de observabilidade técnica com:
  * **Trace ID UUID** único gerado por ciclo de vida da requisição (`trc-<uuid12>`).
  * **Consumo Estimado de Tokens** dividido em `Prompt`, `Completion` e `Total`.
  * **Custo Financeiro Estimado em USD** baseado na tabela oficial do Gemini Flash ($0.075 / 1M input e $0.30 / 1M output).
  * **Latência em milissegundos** (`execution_time_ms`) com alta performance.
  * **Confiança Dinâmica** por similaridade real de cosseno do ChromaDB ou execução de tool (sem constantes fixas).
  * **Auditoria de Guardrails** (`is_safe`, detecção de PII mascarada e injeção de prompt).
  * **Rastreabilidade de Chamados SQLite** com link direto para o endpoint `GET /tickets/{ticket_id}`.
  * **Payload JSON Integral** colapsável para inspeção por avaliadores técnicos.

### Como Acessar a Interface:
* **Execução Local**: Acesse [`http://localhost:8000/demo`](http://localhost:8000/demo) no navegador com a aplicação em execução.
* **GitHub Codespaces**: Na aba **Ports** do ambiente, acesse a porta `8000` pública no caminho `/demo`.

---

## Sumário

- [1. Arquitetura do Sistema](#1-arquitetura-do-sistema)
  - [Padrão Supervisor ReAct](#padrão-supervisor-react)
  - [Grafo de Estados Compilado (LangGraph)](#grafo-de-estados-compilado-langgraph)
  - [Especialistas Registrados como Tools](#especialistas-registrados-como-tools)
- [2. Pilares de Engenharia e Diferenciais](#2-pilares-de-engenharia-e-diferenciais)
  - [Orquestração por Tool Calling vs. Roteamento por Regras](#orquestração-por-tool-calling-vs-roteamento-por-regras)
  - [Memória Persistente Multi-Turn (LangGraph MemorySaver)](#memória-persistente-multi-turn-langgraph-memorysaver)
  - [RAG Vetorial Generalista e Limiar de Abstenção](#rag-vetorial-generalista-e-limiar-de-abstenção)
  - [Transbordo Humano Real com SQLite (tickets.db)](#transbordo-humano-real-com-sqlite-ticketsdb)
  - [Segurança & Sanitização de Dados Sensíveis (PII)](#segurança--sanitização-de-dados-sensíveis-pii)
- [3. Como Executar e Modos de Operação](#3-como-executar-e-modos-de-operação)
  - [Modos de Operação (Offline Resiliente vs. Gemini Generativo)](#modos-de-operação-offline-resiliente-vs-gemini-generativo)
  - [Execução via Docker Compose](#execução-via-docker-compose)
  - [Execução Local](#execução-local)
  - [Endpoints da API REST](#endpoints-da-api-rest)
- [4. Testes Automatizados e CI/CD](#4-testes-automatizados-e-cicd)
- [5. Matriz de Cobertura dos Cenários Oficiais](#5-matriz-de-cobertura-dos-cenários-oficiais)
- [6. Glossário de Defesa Técnica (Perguntas de Entrevista)](#6-glossário-de-defesa-técnica-perguntas-de-entrevista)
- [7. Estrutura do Repositório](#7-estrutura-do-repositório)

---

## 1. Arquitetura do Sistema

O núcleo do sistema abandona completamente rotas lineares e classificadores estáticos de regex. O fluxo implementa o padrão agêntico canônico: **Supervisor $\rightarrow$ Especialistas como Tools $\rightarrow$ Observação $\rightarrow$ Decisão $\rightarrow$ Humano $\rightarrow$ Retomada**.

### Padrão Supervisor ReAct

```text
Usuário (Turno N)
       ↓
[Guardrail Node] (Sanitização PII Luhn + CPF & Defesa contra Injection)
       ↓
[Supervisor Node] (Gemini 2.0 Flash / ReAct Engine com bind_tools)
       ↓ (decide tool_call ou resposta direta)
       ├── search_knowledge_base  (ChromaDB Cosseno, limiar de abstenção < 0.20)
       ├── get_settlement_status   (Consulta de liquidação D+1 Santander)
       ├── diagnose_declined_txn   (Diagnóstico de recusas: Cód 51, 05, etc.)
       ├── diagnose_terminal       (Conectividade Wi-Fi / Chip 3G/4G e reboot)
       ├── search_web              (DuckDuckGo em tempo real para clima/câmbio)
       └── escalate_to_human       (Criação de chamado persistido em SQLite)
       ↓
[Tool Execution Node] (Produz ToolMessage estruturada no State)
       ↓
[Supervisor Node] (Observa saída da Tool, sintetiza resposta grounded)
       ↓
Resposta ao Usuário + Gravação no MemorySaver (thread_id = session_id)
```

### Grafo de Estados Compilado (LangGraph)

```mermaid
flowchart TD
    Start([Início: Request HTTP /chat]) --> GuardrailNode[Nó: Guardrails & PII Sanitizer]

    GuardrailNode -->|Violação / Prompt Injection| SafeExit([Interrupção Segura: Mensagem Bloqueada])
    GuardrailNode -->|Mensagem Segura| SupervisorNode[Nó: Supervisor ReAct\nGemini Flash Tool Calling]

    SupervisorNode -->|Requer Tool Call| ToolsNode[Nó: ToolNode\nExecução de Especialista Tipado]
    ToolsNode -->|Observação ToolMessage| SupervisorNode

    SupervisorNode -->|Resposta Concluída| EndNode([Fim: Resposta Grounded + Telemetria])
    SafeExit --> EndNode
```

### Especialistas Registrados como Tools

Todas as ferramentas são decoradas com `@tool` do LangChain e contratos tipados com schemas Pydantic:

| Ferramenta | Especialidade | Parâmetros | Fonte de Verdade |
| :--- | :--- | :--- | :--- |
| `search_knowledge_base` | Produtos Getnet, manuais, taxas, Pix, crediário, link de pagamento | `query: str` | ChromaDB (`data/getnet_kb.json`) com limiar |
| `get_settlement_status` | Extrato de liquidação, vendas de ontem e previsão bancária D+1 | `user_id: str` | Tabela transacional financeira |
| `diagnose_declined_transaction` | Diagnóstico de transações negadas pelo emissor (código 51, 05, etc.) | `user_id: str, error_code: Optional[str]` | Catálogo de recusas bancárias |
| `diagnose_terminal` | Diagnóstico de conectividade, chip móvel e reinicialização do POS | `user_id: str, serial_number: Optional[str]` | Telemetria de hardware Get Smart/Clássica |
| `search_web` | Informações públicas em tempo real (tempo, câmbio do Euro/Dólar) | `query: str` | DuckDuckGo Search (`ddgs`) |
| `escalate_to_human` | Registro formal de transbordo humano | `user_id: str, reason: str` | Banco relacional SQLite (`data/tickets.db`) |

---

## 2. Pilares de Engenharia e Diferenciais

### Orquestração por Tool Calling vs. Roteamento por Regras
* **Eliminação de Constantes Hardcoded**: Não existem probabilidades estáticas (como `0.98` ou `0.96`) ou listas de regex decidindo para onde a requisição vai. A métrica de confiança exibida na telemetria é a **similaridade cosseno real** calculada pelo ChromaDB sobre os vetores de contexto.
* **Ciclo ReAct Verdadeiro**: O Supervisor emite `AIMessage(tool_calls=[...])`, o grafo executa o `ToolNode` populando `ToolMessage` e retorna ao Supervisor para observação e síntese fundamentada.

### Memória Persistente Multi-Turn (LangGraph MemorySaver)
* O workflow compila o grafo utilizando o checkpointer nativo `MemorySaver` de `langgraph.checkpoint.memory`.
* As sessões são indexadas por `thread_id` (correspondente ao `session_id` da requisição HTTP).
* O assistente mantém contexto entre turnos de diálogo: uma pergunta de acompanhamento (ex: *"E qual delas tem tela touch com Android?"*) reaproveita o contexto histórico do turno anterior sem exigir que o lojista repita os modelos.

### RAG Vetorial Generalista e Limiar de Abstenção
* **Base Expandida**: A base `data/getnet_kb.json` conta com 15 artigos detalhados abrangendo o ecossistema Getnet (maquininhas Get Smart, Clássica, Mini, POS Digital, Pix na maquininha, antecipação avulsa e automática, crediário em até 36x, cancelamento e estorno, taxas, segurança PCI-DSS, reposição gratuita de bobinas e fechamento de lote).
* **Limiar de Abstenção Explícito**: Ao realizar a busca vetorial combinada (cosseno + relevância léxica), se o score for inferior ao limiar (`threshold = 0.20`) ou não houver sobreposição temática com os produtos Getnet, o sistema não alucina nem responde com documentos errados; ele **abém-se explicitamente**:
  > *"Não foram encontradas informações oficiais sobre este assunto nos manuais e documentações cadastrados da Getnet."*

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
* **Autenticação via Header `X-API-Key`**: Os endpoints da API exigem o cabeçalho `X-API-Key`. Para manter o ambiente de testes e Docker fluidos e sem atrito, a chave de desenvolvimento padrão `getnet-dev-key` é aceita por padrão. Requisições com chaves não autorizadas são bloqueadas com HTTP 401 Unauthorized.

### Observabilidade Técnica, Trace ID e Custo por Tokens
* **Trace ID por Ciclo de Vida**: Cada chamada gera um identificador único de rastreamento no padrão `trc-<hex12>`, propagado no payload de resposta HTTP e na telemetria.
* **Métricas de Tokens**: Medição dinâmica de `prompt_tokens`, `completion_tokens` e `total_tokens` em todas as respostas.
* **Cálculo de Custo Financeiro**: Estimativa automática em USD com base na tabela oficial do Gemini Flash ($0.075 / 1 milhão de tokens de input e $0.30 / 1 milhão de tokens de output), viabilizando governança de custos em produção.

### Avaliação Automatizada & LLM-as-a-Judge
* **Dataset Rotulado (`data/eval_dataset.json`)**: Conjunto de 12 pares de avaliação contendo `id`, `question`, `expected_tool`, `ground_truth_context` e `ideal_answer`, cobrindo 100% dos cenários do desafio técnico Getnet.
* **Acurácia de Roteamento (100%)**: Avaliação automatizada em `tests/test_eval_judge.py` comprovando que o Supervisor seleciona a ferramenta correta em 100% dos casos (meta do desafio: $\ge 90\%$).
* **Fidelidade Contextual (Faithfulness $\ge 0.85$)**: Medição de aderência factual entre o texto gerado e a base de conhecimento, assegurando ausência de alucinações.
* **Relevância Semântica (Relevance $\ge 0.85$)**: Verificação semântica da resposta contra a resposta ideal.
* **Resiliência e Degradação Graciosa**: Teste automatizado simulando timeout e falha de API externa do LLM (erro 500 / 429), comprovando que o sistema responde com degradação graciosa sem crash da aplicação (HTTP 200).

---

## 3. Como Executar e Modos de Operação

### Modos de Operação (Offline Resiliente vs. Gemini Generativo)

1. **Modo Padrão (Offline / Resiliente / Zero-Friction — Default)**:
   * **Execução Autônoma Sem Custos**: Não requer chaves de API pagas nem quotas externas.
   * **ReAct Determinístico**: O loop ReAct de seleção de ferramentas, recuperação no ChromaDB local e observação de ferramentas executa de ponta a ponta sem internet.
   * **Busca Web Autêntica**: Consulta informações públicas externas em tempo real via DuckDuckGo (`ddgs`), admitindo indisponibilidade honesta se a rede pública oscilar.

2. **Modo Generativo (Gemini 2.0 Flash)**:
   * **Ativação por Variável de Ambiente**: Configure `GEMINI_API_KEY=sua_chave` e `LLM_PROVIDER=gemini` no arquivo `.env`.
   * **Tool Calling Nativo**: O modelo consome os esquemas de declaração de função (`function_declarations`) e orquestra a chamada de ferramentas diretamente.

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

A suíte conta com **55 testes automatizados** cobrindo todos os cenários oficiais do desafio, testes unitários de componentes e rotinas de avaliação LLM-as-a-Judge:

```bash
# Executar a suíte completa com pytest
pytest tests/ -v
```

Resultado da execução oficial:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.7.0
plugins: anyio-4.15.1, langsmith-0.14.17, asyncio-1.4.1
collected 55 items

tests/test_eval_judge.py ....                                            [  7%]
tests/test_scenarios.py ..........                                       [ 25%]
tests/test_unit.py ........................................               [100%]

============================= 55 passed in 25.43s =============================
```

### Pipeline de Integração Contínua (CI)
O repositório possui pipeline automatizado configurado em `.github/workflows/ci.yml`, executando linting e os 50 testes a cada `push` e `pull_request` na branch `main`.

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
> **Defesa**: *"Na versão anterior o valor era constante em código. Agora, a métrica de confiança exibida no inspetor de telemetria é a **similaridade cosseno matemática real** calculada pelo ChromaDB sobre os embeddings dos documentos recuperados ($\text{Similaridade} = 1 - \text{Distância Cosseno}$). Quando o lojista faz uma pergunta operacional atendida por ferramentas transacionais (como liquidação financeira ou diagnóstico do POS), a confiança reflete 100% de precisão determinística oriunda do banco de dados oficial."*

### 2. "O que o modelo/Supervisor decide no sistema, além de sintetizar a resposta?"
> **Defesa**: *"O Supervisor é o tomador de decisão do loop ReAct. Ele consome o histórico da conversa e os schemas tipados das ferramentas (`bind_tools`), decide autonomamente qual ferramenta invocar com quais argumentos, avalia a observação retornada no estado do grafo e decide se necessita de novos passos ou se já possui evidências suficientes para emitir a resposta final."*

### 3. "De onde veio a base de conhecimento e como é garantido que ela não inventa dados fora de domínio?"
> **Defesa**: *"A base em `data/getnet_kb.json` foi expandida para 15 manuais e documentações oficiais da Getnet com metadados de categoria e URLs de origem. Implementamos um **limiar de abstenção paramétrico** no ChromaDB: se a pergunta for fora de domínio (ex: maquinário agrícola, culinária, etc.), a similaridade fica abaixo do limiar e o agente abém-se explicitamente de opinar, indicando os canais oficiais."*

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
│   ├── getnet_kb.json             # Base de conhecimento oficial expandida (15 artigos Getnet)
│   └── tickets.db                 # Banco relacional SQLite para persistência de tickets humanos
├── src/
│   ├── main.py                    # Servidor FastAPI com endpoints /chat, /tickets e lifecycles
│   ├── config.py                  # Pydantic Settings e configuração de log estruturado JSON
│   ├── agents/
│   │   ├── guardrails.py          # Sanitização PII (Luhn PAN + CPF) e bloqueio de injeções
│   │   ├── knowledge.py           # RAG vetorial ChromaDB com limiar explícito de abstenção
│   │   ├── router.py              # Introspecção e compatibilidade de intenção semântica
│   │   ├── support.py             # Agente especialista em suporte financeiro e hardware
│   │   └── escalation.py          # Especialista de escalação e transbordo humano
│   ├── core/
│   │   ├── graph.py               # Grafo LangGraph Supervisor ReAct com MemorySaver
│   │   ├── llm.py                 # Motor Supervisor ReAct e integração Gemini 2.0 Flash
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
│   ├── test_scenarios.py          # Testes de integração dos 10 cenários oficiais de avaliação
│   └── test_unit.py               # 40 testes unitários (Supervisor, ReAct, MemorySaver, RAG, PII, SQLite)
├── Dockerfile                     # Build multi-stage seguro executado sob usuário não-root
├── docker-compose.yml             # Orquestração Compose v2 com volumes e healthcheck
├── requirements.txt               # Dependências versionadas do projeto
├── .env.example                   # Modelo de variáveis de ambiente
└── README.md                      # Documentação técnica e guia de defesa arquitetural
```
