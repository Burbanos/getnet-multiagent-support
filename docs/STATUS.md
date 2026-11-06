# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com padrão Supervisor ReAct (`src/core/graph.py`), consulta dúvidas institucionais em base vetorial ChromaDB (`src/agents/knowledge.py`), simula diagnósticos operacionais de hardware, recusas e extrato financeiro via ferramentas tipadas (`src/tools/`), aplica sanitização PII/guardrails e persiste chamados de transbordo humano em SQLite (`src/core/tickets_db.py`).

---

### 2. Arquitetura Atual
- **Grafo compilado**: `OrchestrationGraph` em `src/core/graph.py` com nós `guardrail`, `supervisor` e `tools`.
- **Agentes**: `GuardrailAgent` (`src/agents/guardrails.py`), `SupervisorLLMEngine` (`src/core/llm.py`) e classes legadas mantidas para retrocompatibilidade de testes (`RouterAgent`, `KnowledgeAgent`, `CustomerSupportAgent`, `HumanEscalationAgent`).
- **Decisão de rota e tools**:
  - Com `LLM_PROVIDER=gemini` e chave configurada: o `google.genai` executa Tool Calling nativo com declarações de função (`src/core/llm.py`).
  - No modo padrão offline (`LLM_PROVIDER=mock`): o `SupervisorLLMEngine._decide_tool_call_or_reply` avalia padrões semânticos e emite `AIMessage(tool_calls=[...])`, despachando a execução ao nó `tools` (`src/tools/agent_tools.py`) e sintetizando a resposta final via `ToolMessage`.

---

### 3. RAG (Recuperação de Informações)
- **Origem dos dados**: Arquivo JSON local estático escrito à mão (`data/getnet_kb.json`) com 15 artigos curtos. Não há crawler ou raspagem de páginas reais do site getnet.com.br.
- **Ingestão e Armazenamento**: `ChromaDBKnowledgeRetriever` (`src/agents/knowledge.py`) carrega o JSON na coleção `getnet_kb` com embeddings padrão do ChromaDB em memória (ou persistente se `CHROMA_PERSIST_DIR` for setado).
- **Recuperação**: Score híbrido ponderado: 60% similaridade cosseno ChromaDB + 25% overlap léxico substantivo + 15% overlap de título.
- **Limiar de relevância**: Limiar geral `threshold = 0.20`. Se a query contiver termos substantivos com zero sobreposição léxica (`top_lex_overlap == 0`) e similaridade cosseno $< 0.55$, o retriever abstém-se matematicamente e retorna vazio (`[]`).

---

### 4. Tools do Agente de Suporte
Definidas e decoradas em `src/tools/agent_tools.py`:
1. `get_settlement_status`: Entrada `user_id: str`. Saída: JSON com extrato de vendas de ontem e previsão de depósito D+1. Fonte: dados mock em memória (`src/tools/balance_tools.py`).
2. `diagnose_declined_transaction`: Entrada `user_id: str, error_code: Optional[str]`. Saída: JSON com causa da recusa (código 51, etc.) e ação sugerida. Fonte: dicionário fixo (`src/tools/balance_tools.py`).
3. `diagnose_terminal`: Entrada `user_id: str, serial_number: Optional[str]`. Saída: JSON com diagnóstico de conectividade e passos de reinicialização. Fonte: mock em código (`src/tools/terminal_tools.py`).
4. `search_knowledge_base`: Entrada `query: str`. Saída: JSON com documentos recuperados ou status `abstain`. Fonte: ChromaDB (`data/getnet_kb.json`).
5. `search_web`: Entrada `query: str`. Saída: JSON com resultados de busca pública. Fonte: DuckDuckGo Search (`duckduckgo_search` / `ddgs`).
6. `escalate_to_human`: Entrada `user_id: str, reason: str`. Saída: JSON com protocolo `GET-TKT-...` e status `open`. Fonte: SQLite (`data/tickets.db`).

---

### 5. Escalonamento Humano
- **O que acontece**: A ferramenta `escalate_to_human` invoca `TicketsRepository.create_ticket` (`src/core/tickets_db.py`), persistindo o protocolo no formato `GET-TKT-YYYYMMDD-XXXX`.
- **Onde é gravado**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback dinâmico para `/tmp/tickets.db` se o volume for read-only).
- **Quem recebe**: Ninguém de forma ativa/push. Não há webhook, mensageria (Kafka/RabbitMQ) ou integração com CRM/Slack. Os chamados ficam armazenados no SQLite e são consultados passivamente via endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`) em `src/core/graph.py`, indexado por `thread_id` (`session_id`). Mantém histórico multi-turn em memória RAM durante a execução do processo. Não há persistência externa de sessão (Redis/Postgres); se o processo reiniciar, o histórico de mensagens em RAM é limpo.
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`). Aceita `getnet-dev-key` por padrão e rejeita chaves não autorizadas com HTTP 401. Não há OAuth2, JWT ou controle por perfil (RBAC).
- **Guardrails**: `GuardrailAgent` (`src/agents/guardrails.py`) avalia injeções de prompt em PT-BR e EN via regex. Módulo `src/core/pii.py` mascara cartões válidos pelo algoritmo de Luhn e números de CPF. Não há modelos de moderação LLM dedicados.
- **Observabilidade**: Geração de `trace_id` UUID (`trc-<hex12>`), latência em ms, estimativa de tokens (`prompt`, `completion`, `total`) e cálculo de custo em USD do Gemini Flash em cada resposta (`src/main.py`) e na UI (`src/static/demo.html`). Não há exportador OpenTelemetry conectado a backends APM externos.

---

### 7. Testes Automatizados
- **Quantidade e cobertura**: 56 testes automatizados cobrindo os 10 cenários oficiais (`tests/test_scenarios.py`), endpoints, ferramentas, RAG, guardrails, memória multi-turn e fallback do SQLite (`tests/test_unit.py`), e rotina de avaliação LLM-as-a-judge e resiliência a timeout (`tests/test_eval_judge.py`).
- **Última execução real**:
  - Comando: `pytest tests/ -v`
  - Saída resumida: `56 passed in 32.64s` (Python 3.13.3).

---

### 8. Docker
- **Status de execução**: não verificado diretamente (o binário `docker` não está presente no PATH do ambiente Windows host de desenvolvimento).
- **Arquivos presentes**:
  - `Dockerfile`: Multi-stage build com `python:3.11-slim`, criação do usuário não-root `appuser` e permissão explícita `chmod -R 777 /app/data`.
  - `docker-compose.yml`: Serviço configurado na porta 8000 com volumes nomeados `tickets_data:/app/data` e `chroma_data:/app/chroma_db`.

---

### 9. Afirmações do README que o Código NÃO Sustenta
1. **CI completo com linting**: O README afirma que o CI executa linting e testes a cada push; o arquivo `.github/workflows/ci.yml` existente apenas executa `pip install -r requirements.txt` e `pytest tests/ -v`, sem executar linters (`flake8`, `ruff`, `black`).
2. **Uso de LLM generativo como padrão**: O README apresenta o fluxo focado no Gemini 2.0 Flash; na prática, a configuração default de execução (`src/config.py`) roda com `LLM_PROVIDER=mock` determinístico offline.
3. **Documentação oficial completa da Getnet**: O README cita diversos tópicos contratuais e regulatórios avançados; o corpus real consiste em apenas 15 resumos curtos escritos manualmente em `data/getnet_kb.json`.

---

### 10. Problemas Conhecidos e Dívidas Técnicas
- **Sessões voláteis**: O checkpointer `MemorySaver` guarda o histórico de mensagens em memória do processo, perdendo o estado conversacional em restarts.
- **Simulação estática de suporte**: Dados de liquidação financeira, terminais e recusas são estáticos em memória, sem integração com APIs bancárias reais.
- **Notificação de transbordo passiva**: Tickets residem no SQLite sem fila assíncrona para encaminhamento aos atendentes humanos.
- **Roteamento offline por padrões**: No modo mock, a seleção de ferramentas do supervisor depende de casamento de padrões em `src/core/llm.py` em vez de inferência probabilística.

---

### 11. Decisões de Design e Motivações
1. **LangGraph com MemorySaver**: Estrutura o ciclo ReAct em nós (`guardrail`, `supervisor`, `tools`), garantindo suporte conversacional multi-turn via `thread_id`.
2. **Modo Híbrido (Offline Mock + Gemini Flash)**: Permite que avaliadores e testes executem 100% dos cenários sem necessidade de chave de API ou conexão de rede, preservando suporte ao modelo real quando configurado.
3. **SQLite Local com Fallback**: Garante persistência relacional real dos chamados de escalonamento em `tickets.db`, com desvio automático para `/tmp` em ambientes containerizados com restrições de permissão.
4. **Abstenção Vetorial Matemática**: Elimina listas fixas de termos obrigatórios no RAG, utilizando o limiar de similaridade e a densidade de termos substantivos para rejeitar consultas fora de domínio.
5. **Autenticação Leve com Dev Key Padrão**: Habilita segurança de API com o header `X-API-Key` sem criar fricção na execução automatizada de testes e containers.
