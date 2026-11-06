# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 2C: Camada de Provedor, Modelo Reserva e Correções de Segurança

#### Verificação Fase 2C (`python scripts/verify_phase2c.py`):
```text
PASS S1.gemini_model_renamed
PASS S2.env_example
PASS S3.readme_provider_docs
PASS R1.settings_defaults
PASS R1.gemini_model_removed
PASS R2.factory_primary
PASS R2.factory_fallback
PASS R2.factory_model_override
PASS R2.timeouts_kept
PASS R2.fallback_disabled_when_empty
PASS R3.provider_not-a-provider
PASS R3.provider_anthropic
PASS R4.fallback_on_transient
PASS R4.model_used_reported
PASS R5.no_fallback_on_config_error
PASS R6.both_fail_unavailable
PASS R7.injected_model_without_fallback
PASS R7.api_reports_model
PASS R8.bank_account_masked
PASS R9.no_false_ticket_garbage
PASS R9.no_false_ticket_raise
PASS Q0.phase2a_still_passes
PASS Q0.phase2b_only_superseded_fail
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 69 passed in 16.14s
PASS Q3.tree_unchanged

SUMMARY: 26/26 passed
```

#### Commit Base da Fase 2C:
```text
0ab2c52641ac149e5c75456e36e012ef9f207ab3
```

#### Testes Alterados e Criados na Fase 2C:
1. `tests/test_robustness.py::test_get_chat_model_receives_timeout_and_max_retries`: asserção atualizada para o novo modelo padrão `"gemini-3.5-flash"` (conforme decisão de estabilidade autorizada).
2. `tests/test_providers.py` (novo, 9 testes):
   - `test_provider_defaults`: validação dos defaults `LLM_PROVIDER="google_genai"`, `LLM_MODEL="gemini-3.5-flash"`, `LLM_FALLBACK_MODEL="gemini-3.5-flash-lite"`.
   - `test_get_chat_model_respects_model_override`: override de `model_name` em tempo de execução.
   - `test_get_fallback_model_returns_none_when_empty`: desativação limpa do fallback quando a variável está vazia.
   - `test_unknown_provider_raises_configuration_error`: rejeição imediata de provedores desconhecidos (`LLMConfigurationError`).
   - `test_missing_optional_provider_packages_raise_configuration_error`: instruções explícitas de instalação para pacotes opcionais ausentes (`langchain-openai`, `langchain-anthropic`).
   - `test_missing_api_key_raises_not_configured_error`: sinalização adequada de ausência de credenciais (`LLMNotConfiguredError`).
   - `test_transient_error_uses_fallback_model`: acionamento do fallback em erro 429 com propagação do modelo no estado.
   - `test_configuration_error_does_not_use_fallback`: bloqueio estrito de fallback em erros não transitórios (`ModelNotFoundError`).
   - `test_bank_account_masking`: validação do mascaramento financeiro em agências e contas correntes.

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com padrão Supervisor ReAct (`src/core/graph.py`), consulta dúvidas institucionais em base vetorial ChromaDB (`src/agents/knowledge.py`), simula diagnósticos operacionais de hardware, recusas e extrato financeiro via ferramentas tipadas (`src/tools/`), aplica sanitização PII/guardrails e persiste chamados de transbordo humano em SQLite (`src/core/tickets_db.py`). Suporta provedor configurável (`LLM_PROVIDER`), modelo principal (`LLM_MODEL`) e modelo reserva (`LLM_FALLBACK_MODEL`).

---

### 2. Arquitetura Atual (Fase 2C)
- **Grafo compilado**: `OrchestrationGraph` em `src/core/graph.py` com nós `guardrail`, `supervisor`, `tools` e `force_escalation`.
- **Supervisor ReAct**: Invocação via function calling (`ChatGoogleGenerativeAI` ou provedores opcionais) com fallback automático em falhas transitórias (429/timeout). Em erros de configuração (`ModelNotFoundError`, auth), falha rapidamente sem acionar o reserva.
- **Tools**: Executadas no nó `tools` (`src/tools/agent_tools.py`) e observadas via `ToolMessage`.
- **Rastreabilidade**: `llm_model` registrado no estado (`SupervisorState`, `AgentState`) e exposto em `metadata.llm_model` da API `/chat`.

---

### 3. RAG (Recuperação de Informações)
- **Origem dos dados**: Arquivo JSON local estático (`data/getnet_kb.json`) com 15 artigos curtos.
- **Ingestão e Armazenamento**: `ChromaDBKnowledgeRetriever` (`src/agents/knowledge.py`) carrega o JSON na coleção `getnet_kb`.
- **Recuperação e Tagging**: Cada documento recuperado inclui `"retrieval_mode": "vector"` ou `"retrieval_mode": "lexical_fallback"`.
- **Fallback Léxico**: O método `_lexical_fallback` emite log `WARNING` ao ser acionado e não inventa campos de `similarity` ou `distance`.
- **Limiar de relevância**: Limiar geral `threshold = 0.20`. Se a query contiver termos substantivos com zero sobreposição léxica (`top_lex_overlap == 0`) e similaridade cosseno $< 0.55$, o retriever abstém-se matematicamente e retorna vazio (`[]`).

---

### 4. Tools do Agente de Suporte
Definidas e decoradas em `src/tools/agent_tools.py`:
1. `get_settlement_status`: Consulta extrato e valores a receber. Aplica `mask_bank_account` na conta de destino (`Ag: **** CC: ***65-4`), prevenindo vazamento de dados bancários ao modelo.
2. `diagnose_declined_transaction`: Entrada `error_code: Optional[str]`. Saída: JSON com causa da recusa e ação sugerida.
3. `diagnose_terminal`: Entrada `serial_number: Optional[str]`. Saída: JSON com conectividade do terminal.
4. `search_knowledge_base`: Entrada `query: str`. Saída: JSON com documentos recuperados ou status `abstain`.
5. `search_web`: Entrada `query: str`. Saída: JSON com resultados de busca pública (DuckDuckGo mockado nos testes).
6. `escalate_to_human`: Entrada `reason: str`. Saída: JSON com protocolo `GET-TKT-...` persistido no SQLite.

---

### 5. Escalonamento Humano e Resiliência
- **Gravação**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback para `/tmp/tickets.db`).
- **Resiliência em `force_escalation`**: Caso o supervisor exceda `MAX_SUPERVISOR_STEPS` e a abertura do chamado falhe (banco offline, erro de I/O ou payload inválido), o sistema não emite protocolos falsos nem mente ao lojista. O identificador fictício `GET-TKT-PENDING` foi totalmente erradicado, e uma mensagem defensiva e graciosa é retornada.
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`). Quando `session_id` não é fornecido, gera-se UUID único por requisição.
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`).
- **Guardrails e PII**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn para cartões, formatação de CPF e mascaramento de agências/contas bancárias via `mask_bank_account`).
- **Observabilidade**: `trace_id` UUID mantido em todos os logs estruturados e propagado via header `X-Trace-Id`. `llm_model` aponta com precisão o modelo que sintetizou a resposta (principal ou reserva).

---

### 7. Higienização e Refatoração de Testes (Fases 1A, 1B, 2A, 2B e 2C)

**Total atual de testes**: 69 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 2C**: 9 novos testes em `tests/test_providers.py` e atualização de asserção em `tests/test_robustness.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos que dependiam do código morto de roteamento por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 2C (`python scripts/verify_phase2c.py`):
```text
PASS S1.gemini_model_renamed
PASS S2.env_example
PASS S3.readme_provider_docs
PASS R1.settings_defaults
PASS R1.gemini_model_removed
PASS R2.factory_primary
PASS R2.factory_fallback
PASS R2.factory_model_override
PASS R2.timeouts_kept
PASS R2.fallback_disabled_when_empty
PASS R3.provider_not-a-provider
PASS R3.provider_anthropic
PASS R4.fallback_on_transient
PASS R4.model_used_reported
PASS R5.no_fallback_on_config_error
PASS R6.both_fail_unavailable
PASS R7.injected_model_without_fallback
PASS R7.api_reports_model
PASS R8.bank_account_masked
PASS R9.no_false_ticket_garbage
PASS R9.no_false_ticket_raise
PASS Q0.phase2a_still_passes
PASS Q0.phase2b_only_superseded_fail
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 69 passed in 16.14s
PASS Q3.tree_unchanged

SUMMARY: 26/26 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
69 passed in 16.14s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas em aberto e apontamentos para a Fase 2D (Subagentes)

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock deve ser gerado pelo usuário em ambiente Linux/container para resolução nativa de dependências de compilação sem pacotes Windows-specific (ex.: `uvloop`).
2. **Decomposição em Subagentes Especializados (Fase 2D)**: A arquitetura atual centraliza o function calling no `SupervisorAgent`. Na Fase 2D, conforme o `docs/SPEC.md`, o supervisor passará a orquestrar subagentes dedicados (`KnowledgeSubagent`, `SupportSubagent` etc.) em subgrafos isolados, preservando o modelo agnóstico, o fallback e o mascaramento PII consolidados na Fase 2C.
