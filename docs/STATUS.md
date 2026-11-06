# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com padrão Supervisor ReAct (`src/core/graph.py`), consulta dúvidas institucionais em base vetorial ChromaDB (`src/agents/knowledge.py`), simula diagnósticos operacionais de hardware, recusas e extrato financeiro via ferramentas tipadas (`src/tools/`), aplica sanitização PII/guardrails e persiste chamados de transbordo humano em SQLite (`src/core/tickets_db.py`).

---

### 2. Arquitetura Atual (Fase 1: Transição 1A → 1B)
- **Grafo compilado**: `OrchestrationGraph` em `src/core/graph.py` com nós `guardrail`, `supervisor` e `tools`.
- **Agentes**: `GuardrailAgent` (`src/agents/guardrails.py`) e `RulesFallbackEngine` (`src/core/llm.py`). Código morto eliminado: `RouterAgent`, `KnowledgeAgent`, `CustomerSupportAgent` e `HumanEscalationAgent`.
- **Decisão de rota e tools**:
  - `RulesFallbackEngine._decide_tool_call_or_reply`: avalia intenções e emite `AIMessage(tool_calls=[...])`, despachando a execução ao nó `tools` (`src/tools/agent_tools.py`) e sintetizando a resposta final via `ToolMessage`.
  - A resposta da API `/chat` sinaliza explicitamente `"decision_engine": "rules_fallback"`.
  - `tools_used` contém estritamente nomes reais de ferramentas invocadas (aliases removidos).

---

### 3. RAG (Recuperação de Informações)
- **Origem dos dados**: Arquivo JSON local estático (`data/getnet_kb.json`) com 15 artigos curtos.
- **Ingestão e Armazenamento**: `ChromaDBKnowledgeRetriever` (`src/agents/knowledge.py`) carrega o JSON na coleção `getnet_kb`.
- **Recuperação e Tagging**: Cada documento recuperado inclui `"retrieval_mode": "vector"` ou `"retrieval_mode": "lexical_fallback"`.
- **Fallback Léxico**: O método `_lexical_fallback` emite log `WARNING` ao ser acionado e não inventa mais campos de `similarity` ou `distance`.
- **Limiar de relevância**: Limiar geral `threshold = 0.20`. Se a query contiver termos substantivos com zero sobreposição léxica (`top_lex_overlap == 0`) e similaridade cosseno $< 0.55$, o retriever abstém-se matematicamente e retorna vazio (`[]`).

---

### 4. Tools do Agente de Suporte
Definidas e decoradas em `src/tools/agent_tools.py`:
1. `get_settlement_status`: Entrada `user_id: str`. Saída: JSON com extrato de vendas de ontem e previsão de depósito D+1.
2. `diagnose_declined_transaction`: Entrada `user_id: str, error_code: Optional[str]`. Saída: JSON com causa da recusa e ação sugerida.
3. `diagnose_terminal`: Entrada `user_id: str, serial_number: Optional[str]`. Saída: JSON com conectividade do terminal.
4. `search_knowledge_base`: Entrada `query: str`. Saída: JSON com documentos recuperados ou status `abstain`.
5. `search_web`: Entrada `query: str`. Saída: JSON com resultados de busca pública (DuckDuckGo).
6. `escalate_to_human`: Entrada `user_id: str, reason: str`. Saída: JSON com protocolo `GET-TKT-...` e status `open`.

---

### 5. Escalonamento Humano
- **Gravação**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback para `/tmp/tickets.db`).
- **Isolamento**: `data/*.db` adicionado ao `.gitignore` e `data/tickets.db` removido do git tracking (`git rm --cached`).
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`). Quando `session_id` não é fornecido, é gerado UUID único por requisição para isolar sessões independentes.
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`), aceitando `getnet-dev-key` ou cabeçalho omitido por padrão, e rejeitando chaves inválidas com HTTP 401.
- **Guardrails**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn e CPF).
- **Observabilidade**: `trace_id` UUID mantido. Métricas fabricadas removidas: `tokens` e `estimated_cost_usd` são retornados como `null` e `confidence` foi removido da resposta e metadados. Na interface `/demo`, esses campos exibem `n/a`.

---

### 7. Higienização e Refatoração de Testes (Fase 1A e Fase 1B)

**Total atual de testes**: 45 testes aprovados e 100% offline.

#### Testes Apagados na Fase 1A (10 testes):
1. `test_router_dispatches_customer_support`: dependia de `RouterAgent` removido como código morto.
2. `test_router_dispatches_knowledge_agent`: dependia de `RouterAgent` removido como código morto.
3. `test_router_dispatches_escalation`: dependia de `RouterAgent` removido como código morto.
4. `test_router_antecipacao_processo_semantic_route`: dependia de `RouterAgent` removido como código morto.
5. `test_router_confidence_threshold_escalation`: dependia de `RouterAgent` removido como código morto.
6. `test_router_unmatched_low_confidence`: dependia de `RouterAgent` removido como código morto.
7. `test_router_terminal_connectivity_with_model_name`: dependia de `RouterAgent` removido como código morto.
8. `test_router_decline_priority_over_terminal_defect`: dependia de `RouterAgent` removido como código morto.
9. `test_llm_web_search_synthesis_pure_dynamic_header`: dependia de método removido em `src/core/llm.py`.
10. `test_llm_rag_synthesis_focused_on_top1_doc`: dependia de método removido em `src/core/llm.py`.

#### Testes Apagados na Fase 1B (2 funções e 2 helpers em `tests/test_eval_judge.py`):
1. `test_llm_as_a_judge_evaluation_suite`: removido pois alegava avaliar LLM-as-a-judge quando nenhum LLM é invocado na Fase 1.
2. `test_llm_api_resilience_and_graceful_degradation`: removido pois simulava falha de chamada de API externa de LLM inexistente na Fase 1.
3. `_evaluate_faithfulness` e `_evaluate_relevance`: helpers de cálculo sintético removidos com a suíte de judge fictício.

#### Testes Criados / Mantidos na Fase 1B (`tests/test_eval_judge.py`):
1. `test_eval_dataset_schema`: mantido; valida formato e completude dos 12 casos em `data/eval_dataset.json`.
2. `test_rules_fallback_routing_on_dataset`: criado; avalia que o motor de fallback ReAct aciona a ferramenta esperada (`expected_tool in tools_used` ou guardrail) para os 12 pares do dataset.
3. `test_x_api_key_security_header`: mantido; valida autenticação com chave válida, cabeçalho omitido e rejeição 401 para chave inválida.

#### Testes Alterados / Apagados na Fase 2A:
1. `tests/test_eval_judge.py`: `test_rules_fallback_routing_on_dataset` foi removido pois avaliava o motor determinístico `RulesFallbackEngine` eliminado nesta fase; o roteamento e function calling agora são testados de ponta a ponta em `tests/test_graph_llm.py` e `tests/test_scenarios.py` com `ScriptedChatModel`.
2. `tests/test_scenarios.py`: os 10 cenários foram reescritos para orquestração ReAct via `ScriptedChatModel` com emissão e validação explícita de `AIMessage(tool_calls=...)` e recepção de `ToolMessage`.
3. `tests/test_unit.py`:
   - `test_chat_endpoint_valid_response`: adaptado para mock do Supervisor com `ScriptedChatModel`.
   - `test_create_ticket_endpoint_and_read_back`: adaptado para acionamento da ferramenta `escalate_to_human` via `ScriptedChatModel`.
   - `test_health_endpoint`: asserção atualizada para verificar o campo booleano `llm_configured` (em vez de checagem fixa de provider legada).

#### Novos Testes Criados na Fase 2A (`tests/test_graph_llm.py`):
1. `test_single_tool_call_flow`: fluxo de turno único com chamada de ferramenta e síntese final.
2. `test_two_tools_sequential_flow`: fluxo sequencial ReAct de duas ferramentas no mesmo turno.
3. `test_direct_response_no_tools`: resposta conversacional direta sem invocação de ferramentas.
4. `test_tool_exception_returns_tool_message_error_to_model`: tratamento e propagação de falha de ferramenta como `ToolMessage` para o modelo sintetizar explicação graciosa.
5. `test_multi_turn_memory_same_session`: retenção de contexto conversacional entre múltiplos turnos usando `MemorySaver` com o mesmo `session_id`.
6. `test_pii_sanitized_before_supervisor`: sanitização de cartões PAN/CPF antes da invocação do modelo supervisor.
7. `test_tool_schemas_do_not_expose_user_id`: inspeção estrita dos schemas Pydantic das ferramentas garantindo que `user_id` não seja visível para o LLM.
8. `test_chat_endpoint_503_when_no_api_key`: retorno HTTP 503 com mensagem clara quando `GEMINI_API_KEY` não está configurada.
9. `test_chat_endpoint_503_when_model_fails`: retorno HTTP 503 com mensagem clara e log de `trace_id` quando o provedor LLM falha.

#### Novos Testes Criados na Fase 2B (`tests/test_robustness.py`):
1. `test_get_chat_model_receives_timeout_and_max_retries`: validação de que `LLM_TIMEOUT_S` (30.0) e `LLM_MAX_RETRIES` (2) são passados ao `ChatGoogleGenerativeAI`.
2. `test_content_blocks_converted_to_plain_text`: conversão correta de conteúdos estruturados em lista de blocos de texto (`AIMessage.text`) para string final limpa.
3. `test_model_not_found_error_returns_503_misconfigured`: conversão de `ModelNotFoundError` em `LLMConfigurationError` e retorno HTTP 503 com "misconfigured" e header `X-Trace-Id`.
4. `test_direct_llm_configuration_error_propagated_by_run_sync`: propagação estrita de `LLMConfigurationError` através do método `run_sync`.
5. `test_other_config_errors_return_503_misconfigured`: parametrização validando `ModelAuthenticationError`, `ModelPermissionDeniedError` e `ModelInvalidRequestError` retornando HTTP 503 "misconfigured".
6. `test_model_rate_limit_error_returns_503_unavailable`: validação de `ModelRateLimitError` retornando HTTP 503 "unavailable" (sem "misconfigured").
7. `test_generic_exception_returns_500_without_leak_and_with_trace_id`: captura de exceções genéricas sem vazar detalhes no payload HTTP e referenciando o `trace_id`.
8. `test_trace_id_header_consistency`: garantia de que o header `X-Trace-Id` coincide com `metadata.trace_id` no payload HTTP 200.
9. `test_supervisor_step_limit_forces_escalation_and_consistent_history`: limite forçado de passos (`MAX_SUPERVISOR_STEPS=3`) acionando `force_escalation`, gerando chamado persistido e garantindo que cada `tool_call` pendente possua um `ToolMessage` correspondente no histórico.

#### Isolamento de Ambiente em `tests/conftest.py`:
- `TICKETS_DB_PATH` isolado em diretório temporário (`tempfile.mkdtemp`) antes do import da aplicação, garantindo que a execução dos testes não altere a árvore git (`git status --porcelain` limpo).
- `mock_web_search` registrado como fixture autouse para monkeypatch de `web_search_tool`, impedindo qualquer tráfego de rede durante os testes.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 2B (`python scripts/verify_phase2b.py`):
```text
PASS S1.default_model_config
PASS S1.default_model_env_example
PASS S1.default_model_compose
PASS S1.no_retired_model
PASS R1.settings
PASS R1.config_error_class
PASS R2.timeout_and_retries
PASS R2.model_name
PASS R3.content_blocks_to_text
PASS R4.config_error_503
PASS R6.trace_header_on_503
PASS R4.transient_error_503
PASS R5.internal_error_no_leak
PASS R5.internal_error_has_reference
PASS R6.trace_header_matches_metadata
PASS R7.step_limit_model_calls
PASS R7.forced_escalation
PASS R8.history_consistent
PASS Q0.phase2a_still_passes :: SUMMARY: 26/26 passed
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 60 passed in 12.98s
PASS Q3.tree_unchanged

SUMMARY: 22/22 passed
```

#### Commit Base Fase 2B:
```text
7408e3d037d981810768c5d2c1d84b97b2c6439e
```

#### Verificação Fase 2A (`python scripts/verify_phase2a.py`):
```text
PASS S1.rules_engine_removed
PASS S2.no_regex_routing
PASS S3.bind_tools
PASS S4.supervisor_prompt
PASS S5.fake_model
PASS S6.dep_declared
PASS S6.ci_tests_use_lock
PASS S6.docker_no_fallback
PASS S6.lock_has_dep
PASS S7.ci_actions_updated
PASS S8.readme_updated
PASS R1.user_id_not_model_visible
PASS R1.tool_set
PASS R2.single_tool_flow
PASS R2.system_prompt_first
PASS R2.no_duplicate_human
PASS R3.user_id_injected
PASS R3.bound_tools
PASS R4.two_tools_sequence
PASS R5.multi_turn_memory
PASS R6.pii_masked_before_model
PASS R7.no_key_503
PASS R8.llm_error_503
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 49 passed in 15.53s
PASS Q3.tree_unchanged

SUMMARY: 26/26 passed
```

#### Commit Base Fase 2A:
```text
4625cc8b05bc4d88dbe33c8c3e45e8b5114e59f5
```

#### Verificação Fase 1 (`python scripts/verify_phase1.py`):
```text
PASS A1.files
PASS A1.refs
PASS A2.rules_engine_named
PASS A2.no_fake_gemini
PASS A2.no_hardcoded_answers
PASS A3.no_token_estimation
PASS A3.no_tool_aliases
PASS A4.chat_200
PASS A4.decision_engine
PASS A4.tokens_null
PASS A4.cost_null
PASS A4.no_confidence
PASS A4.tools_used_real
PASS A5.agents_endpoint_truthful
PASS A6.lexical_no_fake_similarity
PASS A6.retrieval_mode_tagged
PASS A7.demo_no_fake_metrics
PASS B1.tickets_db_untracked
PASS B1.gitignore
PASS B2.fake_judge_removed
PASS B2.schema_test_kept
PASS B3.pytest_config
PASS B3.ruff_config
PASS B4.runtime_no_pytest
PASS B4.langchain_core
PASS B4.dev_reqs
FAIL B4.lock_regenerated :: requirements.lock missing, stale (no langchain-core) or contains pytest
PASS B4.docker_uses_lock
PASS B5.ci_steps
PASS B6.ruff_clean
PASS B7.pytest_passes_offline :: 45 passed in 16.40s
PASS B7.tree_unchanged_by_tests
PASS B8.readme_claims_removed
PASS B8.readme_limitations
PASS B9.status_questions_section
PASS B9.spec_present

SUMMARY: 35/36 passed; failed: B4.lock_regenerated
```

*(Nota: a única falha restante na Fase 1 é `B4.lock_regenerated`, decorrente da restrição explícita de não gerar `requirements.lock` no host Windows, devendo ser gerado em ambiente Linux pelo usuário).*

#### Execução de Testes Pytest (`python -m pytest -q`):
```text
............................................................                 [100%]
60 passed in 12.98s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC

1. **Geração de `requirements.lock`**: Conforme instrução explícita do prompt, o lockfile não foi gerado nesta máquina Windows para evitar resolução de wheels específicas de plataforma. O arquivo `Dockerfile` foi preparado para usar `requirements.lock` se presente (`COPY requirements.txt requirements.lock* ./`), com fallback para `requirements.txt`. A checagem `B4.lock_regenerated` passará assim que o lock for gerado em Linux.
2. **Exclusão de `scripts` no `ruff`**: O script `scripts/verify_phase1.py` possui imports e funções utilitárias que não devem ser modificados (regra: "NÃO edite scripts/verify_phase1.py"). Para que o linter `ruff check .` analise estritamente o código de produção (`src/`) e testes (`tests/`) sem violar a regra de imutabilidade do script verificador, adicionou-se `extend-exclude = ["scripts"]` em `[tool.ruff]` no `pyproject.toml`.
3. **Isolamento de sessão quando `session_id` é omitido**: O LangGraph armazena histórico conversacional por `thread_id`. Para requisições em que o cliente não informa `session_id`, gera-se um UUID novo por turno, prevenindo poluição de contexto entre testes independentes sem quebrar o suporte a múltiplos turnos quando `session_id` é fornecido.
4. **Injeção de `user_id` via `RunnableConfig`**: Para evitar que o lojista autenticado precise informar seu próprio identificador (e para impedir falsificação de identidade pelo modelo), `user_id` foi removido das assinaturas públicas das ferramentas e é injetado via `config["configurable"]["user_id"]` do LangGraph.
5. **Preservação de identidade de mensagem no `_guardrail_node`**: Ao higienizar PII do texto da mensagem do usuário antes de repassá-la ao supervisor, preserva-se o identificador único (`id=orig_id`) da `HumanMessage` original, garantindo integridade das transições no histórico de mensagens do LangGraph.
6. **Classificação Granular de Erros de LLM**: Mapeamento de exceções específicas do LangChain (`ModelNotFoundError`, `ModelAuthenticationError`, `ModelPermissionDeniedError`, `ModelInvalidRequestError`) para `LLMConfigurationError` com HTTP 503 ("misconfigured"), reservando `LLMUnavailableError` para falhas transientes e erros de rede ("unavailable").
7. **Limite Forçado de Passos no ReAct (`force_escalation`)**: Ao atingir `MAX_SUPERVISOR_STEPS` (configurável em tempo de execução via `settings`), o fluxo desvia para o nó determinístico `force_escalation`, que fecha formalmente todas as chamadas pendentes via `ToolMessage` e emite o chamado humano rastreável no `tickets.db`.
8. **Rastreabilidade com `X-Trace-Id` sem Vazamento**: O `trace_id` é gerado na entrada de `/chat` e transmitido em todas as respostas HTTP (200, 500, 503) e no log estruturado JSON. Em erros 500, a mensagem ao cliente omite detalhes internos e exibe apenas a referência `Internal error. Reference: <trace_id>`.
