# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 2D: Subagentes Especialistas (Knowledge e Support)

#### Verificação Fase 2D (`python scripts/verify_phase2d.py`):
```text
PASS S1.supervisor_prompt
PASS S1.knowledge_prompt
PASS S1.support_prompt
PASS S2.specialists_module
PASS S3.readme_agents
PASS R1.supervisor_tools
PASS R1.no_user_id_in_supervisor_schema
PASS R1.settings_specialist_steps
PASS R2.agent_names
PASS R2.knowledge_tools
PASS R2.support_tools
PASS R3.support_flow
PASS R3.agents_used
PASS R4.specialist_isolated_context
PASS R4.user_id_injected_in_specialist
PASS R5.specialist_payload
PASS R6.knowledge_flow
PASS R7.two_specialists
PASS R8.specialist_tool_isolation
PASS R9.escalation_from_supervisor
PASS R10.specialist_step_limit
PASS R11.specialist_llm_error_503
PASS R12.api_agents_used
PASS Q0.verify_phase2a_regressions
PASS Q0.verify_phase2b_regressions
PASS Q0.verify_phase2c_regressions
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 79 passed in 13.98s
PASS Q3.tree_unchanged

SUMMARY: 29/29 passed
```

#### Commit Base da Fase 2D:
```text
2b1a9d89aee5eabac6ac134ae04baf93c2d4c699
```

#### Testes Alterados e Criados na Fase 2D:
1. `tests/test_graph_llm.py` (3 testes reescritos):
   - `test_single_tool_execution`: atualizado para verificar a delegação do supervisor para `ask_support_agent`, execução interna de `get_settlement_status` e retorno sintetizado ao lojista.
   - `test_two_tools_sequence`: atualizado para validar a delegação sequencial do supervisor para múltiplos especialistas (`ask_support_agent` seguido de `ask_knowledge_agent`).
   - `test_tool_exception_returns_tool_message_error_to_model`: atualizado para testar falha em ferramenta do especialista retornando payload com erro e status de degradação graciosa.
2. `tests/test_scenarios.py` (10 cenários de benchmark reescritos):
   - Atualizados para o novo fluxo hierárquico `SupervisorAgent -> ask_knowledge_agent / ask_support_agent -> SpecialistAgent -> leaf tool -> SpecialistAgent -> SupervisorAgent`.
3. `tests/test_unit.py` (1 teste reescrito):
   - `test_chat_endpoint_valid_response`: adaptado para simular resposta via `ask_knowledge_agent` e validar a presença de `agents_used=["SupervisorAgent", "KnowledgeAgent"]` nos metadados da resposta da API.
4. `tests/test_specialists.py` (novo, 10 testes):
   - `test_specialist_initialization_prompts_and_tools`: valida prompts e ferramentas isoladas de cada especialista.
   - `test_specialist_isolated_context`: valida isolamento estrito de mensagens (apenas SystemMessage e HumanMessage da tarefa).
   - `test_specialist_user_id_injection`: garante injeção de `user_id` em ferramentas autorizadas (`get_settlement_status`).
   - `test_specialist_tool_isolation`: rejeição imediata com ToolMessage de erro ao tentar executar ferramentas de outros especialistas.
   - `test_specialist_step_limit_enforced`: encerramento controlado e status `"step_limit"` ao atingir `MAX_SPECIALIST_STEPS=4`.
   - `test_specialist_payload_contract`: valida o schema estrito do dicionário de retorno dos especialistas.
   - `test_specialist_llm_unavailable_propagated`: propagação de `LLMUnavailableError` em falhas transitórias de LLM.
   - `test_specialist_empty_tool_calls_direct_answer`: suporte a resposta direta sem acionamento de ferramentas.
   - `test_specialist_multiple_tools_in_single_turn`: execução ordenada de múltiplas chamadas na mesma rodada.
   - `test_specialist_sources_and_docs_propagation`: extração e retorno íntegro de documentos e fontes do RAG.

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com arquitetura hierárquica multiagente (`src/core/graph.py`): um `SupervisorAgent` orquestra subagentes especialistas (`KnowledgeAgent` e `SupportAgent`), além de escalonamento humano direto (`escalate_to_human`). Conta com consulta à base vetorial ChromaDB (`src/agents/knowledge.py`), simulações operacionais seguras de hardware e extrato bancário com PII mascarado (`src/tools/`), persistência em SQLite (`src/core/tickets_db.py`) e suporte a provedores de LLM configuráveis com fallback resiliente.

---

### 2. Arquitetura Atual (Fase 2D)
- **Hierarquia Multiagente**:
  - **SupervisorAgent**: Ponto de entrada do raciocínio conversacional ReAct. Liga-se exclusivamente a ferramentas de alto nível (`ask_knowledge_agent`, `ask_support_agent`, `escalate_to_human`). Mantém o histórico completo da sessão (`MemorySaver`) e sintetiza a resposta final ao lojista.
  - **KnowledgeAgent**: Especialista em informações institucionais, manuais e políticas. Possui as ferramentas `search_knowledge_base` e `search_web`.
  - **SupportAgent**: Especialista em diagnóstico operacional e dados transacionais. Possui as ferramentas `get_settlement_status`, `diagnose_declined_transaction` e `diagnose_terminal`.
- **Isolamento de Contexto**: Cada especialista opera em contexto limpo e isolado (`[SystemMessage(prompt), HumanMessage(task)]`), sem carregar mensagens antigas do chat do lojista. O `user_id` é injetado pelo orquestrador no momento da chamada da ferramenta.
- **Contrato de Comunicação**: O especialista retorna um payload padronizado ao supervisor contendo `agent`, `status`, `answer`, `tools_used`, `sources` e `retrieved_docs`.
- **Limites de Execução**: Limite de 6 passos no supervisor (`MAX_SUPERVISOR_STEPS=6`) e 4 passos nos especialistas (`MAX_SPECIALIST_STEPS=4`). Ao atingir o teto de passos, o especialista devolve `status="step_limit"` e o supervisor sintetiza ou escala graciosamente.
- **Rastreabilidade**: Metadados da API `/chat` incluem `llm_model` e `agents_used: list[str]` (registrando os agentes que efetivamente participaram da resposta).

---

### 3. RAG (Recuperação de Informações)
- **Origem dos dados**: Arquivo JSON local estático (`data/getnet_kb.json`) com 15 artigos curtos.
- **Ingestão e Armazenamento**: `ChromaDBKnowledgeRetriever` (`src/agents/knowledge.py`) carrega o JSON na coleção `getnet_kb`.
- **Recuperação e Tagging**: Cada documento recuperado inclui `"retrieval_mode": "vector"` ou `"retrieval_mode": "lexical_fallback"`.
- **Fallback Léxico**: O método `_lexical_fallback` emite log `WARNING` ao ser acionado e não inventa campos de `similarity` ou `distance`.
- **Limiar de relevância**: Limiar geral `threshold = 0.20`. Se a query contiver termos substantivos com zero sobreposição léxica (`top_lex_overlap == 0`) e similaridade cosseno $< 0.55$, o retriever abstém-se matematicamente e retorna vazio (`[]`).

---

### 4. Tools do Sistema

#### Tools do Supervisor (`src/tools/supervisor_tools.py`):
1. `ask_knowledge_agent`: Encaminha dúvidas conceituais, taxas e procedimentos ao `KnowledgeAgent`.
2. `ask_support_agent`: Encaminha pedidos de extrato, erros de maquininha e transações ao `SupportAgent`.
3. `escalate_to_human`: Registra protocolo de transbordo no banco de tickets quando solicitado pelo lojista.

#### Tools Folha / Especialistas (`src/tools/agent_tools.py`):
1. `get_settlement_status` (SupportAgent): Consulta extrato financeiro. Mascara contas bancárias (`mask_bank_account`).
2. `diagnose_declined_transaction` (SupportAgent): Diagnostica motivos de recusa de transações.
3. `diagnose_terminal` (SupportAgent): Verifica status de conectividade de terminais POS.
4. `search_knowledge_base` (KnowledgeAgent): Consulta semântica na base Getnet.
5. `search_web` (KnowledgeAgent): Consulta pública auxiliar (mockada nos testes).

---

### 5. Escalonamento Humano e Resiliência
- **Gravação**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback para `/tmp/tickets.db`).
- **Resiliência em `force_escalation`**: Caso o supervisor exceda `MAX_SUPERVISOR_STEPS` e a abertura do chamado falhe (banco offline, erro de I/O ou payload inválido), o sistema não emite protocolos falsos nem mente ao lojista. O identificador fictício `GET-TKT-PENDING` permanece erradicado.
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`).
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`).
- **Guardrails e PII**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn para cartões, formatação de CPF e mascaramento de agências/contas bancárias via `mask_bank_account`).
- **Observabilidade**: `trace_id` UUID mantido em todos os logs estruturados e propagado via header `X-Trace-Id`. `llm_model` e `agents_used` reportam com fidelidade a cadeia de execução.

---

### 7. Higienização e Refatoração de Testes (Fases 1A a 2D)

**Total atual de testes**: 79 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 2D**: 10 novos testes em `tests/test_specialists.py`; reescrita de testes de grafo (`tests/test_graph_llm.py`), cenários (`tests/test_scenarios.py`) e endpoint (`tests/test_unit.py`) para validar o fluxo especialista.
- **Fase 2C**: 9 testes de integração de provedores em `tests/test_providers.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos baseados no router por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 2D (`python scripts/verify_phase2d.py`):
```text
PASS S1.supervisor_prompt
PASS S1.knowledge_prompt
PASS S1.support_prompt
PASS S2.specialists_module
PASS S3.readme_agents
PASS R1.supervisor_tools
PASS R1.no_user_id_in_supervisor_schema
PASS R1.settings_specialist_steps
PASS R2.agent_names
PASS R2.knowledge_tools
PASS R2.support_tools
PASS R3.support_flow
PASS R3.agents_used
PASS R4.specialist_isolated_context
PASS R4.user_id_injected_in_specialist
PASS R5.specialist_payload
PASS R6.knowledge_flow
PASS R7.two_specialists
PASS R8.specialist_tool_isolation
PASS R9.escalation_from_supervisor
PASS R10.specialist_step_limit
PASS R11.specialist_llm_error_503
PASS R12.api_agents_used
PASS Q0.verify_phase2a_regressions
PASS Q0.verify_phase2b_regressions
PASS Q0.verify_phase2c_regressions
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 79 passed in 13.98s
PASS Q3.tree_unchanged

SUMMARY: 29/29 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
79 passed in 13.98s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas em aberto e apontamentos para a Fase 2E (Avaliação e Calibração Final)

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final deve ser gerado pelo usuário em ambiente Linux/container.
2. **Avaliação Automatizada (Fase 2E)**: Implementação e calibração dos cenários de teste automatizados de fidelidade, relevância e conformidade agêntica de acordo com os critérios do `docs/SPEC.md`, garantindo nota máxima sem chamadas externas não autorizadas.
