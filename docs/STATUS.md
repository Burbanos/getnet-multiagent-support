# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com padrão Supervisor ReAct (`src/core/graph.py`), consulta dúvidas institucionais em base vetorial ChromaDB (`src/agents/knowledge.py`), simula diagnósticos operacionais de hardware, recusas e extrato financeiro via ferramentas tipadas (`src/tools/`), aplica sanitização PII/guardrails e persiste chamados de transbordo humano em SQLite (`src/core/tickets_db.py`).

---

### 2. Arquitetura Atual (Fase 1A)
- **Grafo compilado**: `OrchestrationGraph` em `src/core/graph.py` com nós `guardrail`, `supervisor` e `tools`.
- **Agentes**: `GuardrailAgent` (`src/agents/guardrails.py`) e `RulesFallbackEngine` (`src/core/llm.py`). Código morto eliminado: `RouterAgent`, `KnowledgeAgent`, `CustomerSupportAgent` e `HumanEscalationAgent` foram removidos.
- **Decisão de rota e tools**:
  - `RulesFallbackEngine._decide_tool_call_or_reply`: avalia padrões e emite `AIMessage(tool_calls=[...])`, despachando a execução ao nó `tools` (`src/tools/agent_tools.py`) e sintetizando a resposta final via `ToolMessage`.
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
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`). Quando `session_id` não é fornecido, é gerado UUID único por requisição para isolar sessões independentes.
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`), aceitando `getnet-dev-key` por padrão.
- **Guardrails**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn e CPF).
- **Observabilidade**: `trace_id` UUID mantido. Métricas fabricadas removidas: `tokens` e `estimated_cost_usd` são retornados como `null` (não medidos) e `confidence` foi removido da resposta e metadados. Na interface `/demo`, esses campos exibem `n/a`.

---

### 7. Testes Automatizados e Higienização (Fase 1A)

**Total atual**: 46 testes aprovados no pytest.

#### Testes Apagados (10 testes):
1. `test_router_dispatches_customer_support`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
2. `test_router_dispatches_knowledge_agent`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
3. `test_router_dispatches_escalation`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
4. `test_router_antecipacao_processo_semantic_route`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
5. `test_router_confidence_threshold_escalation`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
6. `test_router_unmatched_low_confidence`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
7. `test_router_terminal_connectivity_with_model_name`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
8. `test_router_decline_priority_over_terminal_defect`: dependia de `RouterAgent` (`src/agents/router.py`), removido como código morto.
9. `test_llm_web_search_synthesis_pure_dynamic_header`: dependia de `_synthesize_web_search_response` em `src/core/llm.py`, método removido conforme item 3.
10. `test_llm_rag_synthesis_focused_on_top1_doc`: dependia de `_synthesize_rag_response` em `src/core/llm.py`, método removido conforme item 3.

#### Testes Alterados (5 testes):
1. `tests/test_unit.py::test_agents_introspection_endpoint`: removidos asserts checando presença de `RouterAgent`, `KnowledgeAgent`, `CustomerSupportAgent` e `HumanEscalationAgent` (classes removidas do endpoint `/agents`).
2. `tests/test_unit.py::test_chat_endpoint_valid_response`: atualizados asserts para checar `SupervisorAgent` em `agent` e `agent_type` (removido `KnowledgeAgent`) e verificar o nome real da ferramenta `search_knowledge_base` (sem alias).
3. `tests/test_unit.py::test_langgraph_orchestration_direct_execution`: removido assert checando `AgentRole.KNOWLEDGE` (alias legado removido do enum `AgentRole`) e ajustado assert para ferramenta real `search_knowledge_base`.
4. `tests/test_unit.py::test_supervisor_react_tool_calling`: assert atualizado para validar `"3,367.20"` em vez do literal hardcoded `"(3.367,20)"` removido do formatador conforme item 4.
5. `tests/test_scenarios.py::test_evaluation_scenarios`:
   - `expected_agent` ajustado para `SupervisorAgent` (agentes legados removidos).
   - `expected_tool` ajustado para os nomes reais de ferramentas (`search_knowledge_base`, `search_web`, `get_settlement_status`, `diagnose_terminal`, `diagnose_declined_transaction`).
   - Cenário 3: removido `"3.367,20"` de `expected_keywords` devido à remoção do literal hardcoded no formatador.
6. `tests/test_eval_judge.py::test_llm_as_a_judge_evaluation_suite`: ajustados asserts de `state.tokens` e `state.estimated_cost_usd` para verificar `is None` (remoção de fórmulas estimadas falsas conforme item 6).
7. `tests/test_eval_judge.py::test_llm_api_resilience_and_graceful_degradation`: atualizado monkeypatch de `SupervisorLLMEngine` para `RulesFallbackEngine` (renomeação conforme item 3).

---

### 8. Fase 1A — Saídas Brutas de Verificação

#### Verificação Parte A (`python scripts/verify_phase1.py --part a`):
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

SUMMARY: 17/17 passed
```

#### Testes Automatizados (`python -m pytest -q`):
```text
..............................................                           [100%]
46 passed in 24.91s
```

#### Git Commit Base:
```text
4ddb8209643408db8c7f9460146783ae830f4d03
```

---

### 9. Perguntas / Divergências com o SPEC
1. **Isolamento de sessão quando `session_id` é nulo**: O SPEC define que a memória do LangGraph utiliza `thread_id`. Quando clientes chamam `/chat` sem fornecer `session_id`, associar ao `user_id` causava vazamento de contexto entre cenários de teste independentes executados pelo mesmo usuário padrão (`cliente1988`). Foi adotada a geração de um UUID novo quando `session_id` não é fornecido, preservando o isolamento de testes e mantendo o multi-turn quando `session_id` é explicitamente informado.
2. **Escopo estrito da Fase 1A vs. Requisitos da Parte B**: O SPEC cita requisitos de isolamento de rede (`NO_NETWORK_PLUGIN`), desativação de tracking de `data/tickets.db`, substituição de dependências de runtime (`requirements.txt`) e geração de `requirements.lock` no Codespaces. Conforme orientado pelo prompt, todos esses pontos pertencem à Parte 1B e não foram antecipados na Parte 1A.
