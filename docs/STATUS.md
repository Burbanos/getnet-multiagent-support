# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 2E: Tokens Reais e Tools sem Valores Inventados

#### Verificação Fase 2E (`python scripts/verify_phase2e.py`):
```text
PASS S1.no_generic_decline_text
PASS S2.terminal_no_hardcoded_specifics
PASS S3.fixed_sampling_warning_filtered
PASS R1.tokens_total
PASS R1.tokens_by_agent
PASS R1.cost_still_null
PASS R2.tokens_per_turn
PASS R3.tokens_null_when_unmeasured
PASS R4.api_tokens
PASS R5.no_decline_no_invented_code
PASS R6.unknown_code_not_invented
PASS R6.known_code_kept
PASS R7.terminal_reflects_data_healthy
PASS R8.terminal_reflects_data_weak
PASS R8.terminal_no_other_operator
PASS Q0.verify_phase2a_regressions
PASS Q0.verify_phase2b_regressions
PASS Q0.verify_phase2c_regressions
PASS Q0.verify_phase2d_regressions
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 88 passed in 12.95s
PASS Q3.tree_unchanged

SUMMARY: 22/22 passed
```

#### Commit Base da Fase 2E:
```text
7076a57b352ffa18ba87488aecb8e59d5af4bd66
```

#### Testes Alterados e Criados na Fase 2E:
1. `tests/test_tokens_and_tools.py` (novo, 9 testes):
   - `test_token_accumulation_supervisor_and_support`: soma de tokens por agente (`SupervisorAgent`, `SupportAgent`) e total num turno com múltiplos agentes.
   - `test_tokens_per_turn_counts_only_current_turn`: contagem estrita por turno (tokens zerados a cada novo turno na mesma sessão).
   - `test_tokens_null_when_unmeasured`: `tokens` e `tokens_by_agent` retornam `None` quando nenhuma resposta traz `usage_metadata` (sem estimativas inventadas).
   - `test_chat_endpoint_reports_tokens_in_metadata`: exposição fiel de `tokens` e `tokens_by_agent` no schema de metadados da API `/chat`.
   - `test_declined_transaction_no_declines_and_no_code`: lojista sem recusas recentes e sem código informado retorna campos nulos (`queried_code=None`, `code_known=None`, `code_details=None`), sem forçar "51".
   - `test_declined_transaction_unknown_code`: código fora do catálogo retorna `code_known=False` e `code_details=None` (remoção de "Erro Genérico").
   - `test_declined_transaction_known_code`: código catalogado retorna `code_known=True` e detalhes completos.
   - `test_diagnose_terminal_healthy`: terminal saudável não gera passos de erro nem cita modelos/operadoras ausentes nos dados.
   - `test_diagnose_terminal_weak_signal_recommends_wifi`: terminal com sinal fraco e sem Wi-Fi recomenda conexão Wi-Fi e cita a operadora real do chip.
2. `tests/test_unit.py::test_diagnose_terminal_connectivity`: mantido e aprovado sem alteração de asserção (o terminal de `cliente1988` possui sinal fraco e Wi-Fi desconectado, gerando 4 passos dinâmicos).

---

### 1. Visão Geral
Sistema de atendimento ao cliente em FastAPI (`src/main.py`) para lojistas Getnet. Processa mensagens por um grafo LangGraph com arquitetura hierárquica multiagente (`src/core/graph.py`): um `SupervisorAgent` orquestra subagentes especialistas (`KnowledgeAgent` e `SupportAgent`), além de escalonamento humano direto (`escalate_to_human`). Conta com consulta à base vetorial ChromaDB (`src/agents/knowledge.py`), simulações operacionais de hardware e extrato bancário com PII mascarado e telemetria real sem valores inventados (`src/tools/`), persistência em SQLite (`src/core/tickets_db.py`) e suporte a provedores de LLM configuráveis com medição real de consumo de tokens.

---

### 2. Arquitetura Atual (Fase 2E)
- **Hierarquia Multiagente**:
  - **SupervisorAgent**: Ponto de entrada do raciocínio conversacional ReAct. Liga-se a ferramentas de alto nível (`ask_knowledge_agent`, `ask_support_agent`, `escalate_to_human`). Mantém o histórico completo da sessão (`MemorySaver`) e sintetiza a resposta final ao lojista.
  - **KnowledgeAgent**: Especialista em informações conceituais, manuais e políticas. Possui as ferramentas `search_knowledge_base` e `search_web`.
  - **SupportAgent**: Especialista em diagnóstico operacional e dados transacionais. Possui as ferramentas `get_settlement_status`, `diagnose_declined_transaction` e `diagnose_terminal`.
- **Isolamento de Contexto**: Cada especialista opera em contexto limpo e isolado (`[SystemMessage(prompt), HumanMessage(task)]`), sem carregar mensagens antigas do chat do lojista. O `user_id` é injetado pelo orquestrador no momento da chamada da ferramenta.
- **Medição de Tokens Reais**: Cada chamada de modelo que retorna `usage_metadata` é contabilizada na chave interna `"usage"` do especialista e somada no orquestrador. O consumo é registrado por agente em `tokens_by_agent` e no agregado `tokens`. Se não houver medição do provedor, ambos os campos permanecem `None` (sem estimativas empíricas).
- **Rastreabilidade**: Metadados da API `/chat` incluem `llm_model`, `agents_used`, `tokens` e `tokens_by_agent`.

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
2. `diagnose_declined_transaction` (SupportAgent): Diagnostica motivos de recusa com base estrita no catálogo (`decline_code_catalog`). Sem código ou recusa, retorna campos nulos (`queried_code=None`, `code_known=None`, `code_details=None`). Código fora do catálogo retorna `code_known=False` e `code_details=None` sem descrições inventadas.
3. `diagnose_terminal` (SupportAgent): Diagnóstico e passos derivados exclusivamente da telemetria da máquina (`model`, `sim_operator`, `sim_status`, `signal_level`, `wifi_connected`). Sem problema detectado, informa ausência de anomalias sem inventar instabilidade de sinal.
4. `search_knowledge_base` (KnowledgeAgent): Consulta semântica na base Getnet.
5. `search_web` (KnowledgeAgent): Consulta pública auxiliar (mockada nos testes).

---

### 5. Escalonamento Humano e Resiliência
- **Gravação**: Tabela `tickets` no banco SQLite local (`data/tickets.db`, com fallback para `/tmp/tickets.db`).
- **Resiliência em `force_escalation`**: Caso o supervisor exceda `MAX_SUPERVISOR_STEPS` e a abertura do chamado falhe (banco offline, erro de I/O ou payload inválido), o sistema não emite protocolos falsos nem mente ao lojista.
- **Acompanhamento**: Endpoints HTTP `GET /tickets/{ticket_id}` e `GET /tickets` (`src/main.py`).

---

### 6. Memória, Autenticação, Guardrails e Observabilidade
- **Memória e Sessão**: `MemorySaver` nativo do LangGraph (`langgraph.checkpoint.memory`), indexado por `thread_id` (`session_id`).
- **Autenticação**: Header opcional `X-API-Key` validado em `verify_api_key` (`src/main.py`).
- **Guardrails e PII**: `GuardrailAgent` (`src/agents/guardrails.py`) e `src/core/pii.py` (Luhn para cartões, formatação de CPF e mascaramento de agências/contas bancárias via `mask_bank_account`).
- **Observabilidade**: `trace_id` UUID mantido em logs estruturados e propagado via header `X-Trace-Id`. `llm_model`, `agents_used`, `tokens` e `tokens_by_agent` fornecem auditoria detalhada de execução por turno.
- **Filtro de Warnings**: Silenciamento pontual via `warnings.filterwarnings` apenas para o `UserWarning` benigno de amostragem fixa dos modelos lite (`uses fixed sampling defaults`).

---

### 7. Higienização e Refatoração de Testes (Fases 1A a 2E)

**Total atual de testes**: 88 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 2E**: 9 novos testes em `tests/test_tokens_and_tools.py`.
- **Fase 2D**: 10 novos testes em `tests/test_specialists.py` e adaptação do fluxo hierárquico nos testes de integração.
- **Fase 2C**: 9 testes de integração de provedores em `tests/test_providers.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos baseados no router por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 2E (`python scripts/verify_phase2e.py`):
```text
PASS S1.no_generic_decline_text
PASS S2.terminal_no_hardcoded_specifics
PASS S3.fixed_sampling_warning_filtered
PASS R1.tokens_total
PASS R1.tokens_by_agent
PASS R1.cost_still_null
PASS R2.tokens_per_turn
PASS R3.tokens_null_when_unmeasured
PASS R4.api_tokens
PASS R5.no_decline_no_invented_code
PASS R6.unknown_code_not_invented
PASS R6.known_code_kept
PASS R7.terminal_reflects_data_healthy
PASS R8.terminal_reflects_data_weak
PASS R8.terminal_no_other_operator
PASS Q0.verify_phase2a_regressions
PASS Q0.verify_phase2b_regressions
PASS Q0.verify_phase2c_regressions
PASS Q0.verify_phase2d_regressions
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 88 passed in 12.95s
PASS Q3.tree_unchanged

SUMMARY: 22/22 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
88 passed in 12.95s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 3

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final permanece delegado para ser gerado em ambiente Linux/container pelo usuário para compatibilidade com bibliotecas dependentes de SO (`uvloop`).
2. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
3. **Próxima Fase (Fase 3: RAG e Ingestão de Documentos)**: Expansão e calibração da base de conhecimento da Getnet, enriquecimento de metadados dos artigos e rigor na recuperação semântica e lexical.
