# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 3C: Ligação do RAG Real ao Knowledge Agent e Remoção da Base Antiga

#### Verificação Fase 3C (`python scripts/verify_phase3c.py`):
```text
PASS S1.old_kb_removed
PASS S2.legacy_removed
PASS S3.requirements
PASS S4.knowledge_prompt
PASS S5.readme
PASS R1.min_chunk_setting
PASS R2.default_keeps_3b_behaviour
PASS R2.tiny_page_dropped
PASS R2.tail_merged
PASS R3.committed_index_regenerated
PASS R4.tool_description_has_no_facts
PASS R4.tool_uses_retriever
PASS R4.tool_abstains
PASS K6.knowledge_flow_real_index
PASS R5.tool_unavailable_without_key
PASS R6.real_retriever_requires_key
PASS R6.real_retriever_wiring
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 117 passed in 11.64s
PASS Q3.tree_unchanged

SUMMARY: 27/27 passed
```

#### Commit Base da Fase 3C:
```text
d89d2cbb90d04787552083501d82f66de0005ed6
```

#### Testes Alterados, Reescritos e Criados na Fase 3C:
1. `tests/test_knowledge_rag.py` (novo, 7 testes):
   - `test_search_knowledge_base_success`: ferramenta retorna status "success" com documentos oficiais e todos os campos (`url`, `title`, `fetched_at`, `market`, `chunk_id`, `score`, `text`).
   - `test_search_knowledge_base_abstain`: ferramenta retorna status "abstain" com lista vazia de documentos quando o score está abaixo de `min_score`.
   - `test_search_knowledge_base_unavailable_on_retriever_exception`: conversão de qualquer exceção interna (ex.: `LLMNotConfiguredError`) em status `"unavailable"` sem quebrar o grafo.
   - `test_supervisor_knowledge_flow_extracts_source_url`: fluxo integrado Supervisor -> KnowledgeAgent -> search_knowledge_base preenchendo `state.sources` com a URL oficial da página.
   - `test_build_chunks_with_min_chars`: validação do parâmetro `min_chars=120`, descartando páginas curtas (<120 chars) e mesclando caudas curtas ao trecho anterior da mesma página.
   - `test_get_knowledge_retriever_without_key_raises_error`: `get_knowledge_retriever()` levanta `LLMNotConfiguredError` se `GEMINI_API_KEY` não estiver definida.
   - `test_get_knowledge_retriever_loads_committed_index`: com chave configurada, instancia singleton com as configurações ativas (`RAG_MIN_SCORE`, `RAG_TOP_K`, `task_type="RETRIEVAL_QUERY"`).
2. `tests/test_unit.py` (reescritos):
   - `test_retriever_loads_documents`: reescrito para verificar o carregamento de trechos pelo `get_knowledge_retriever()` da biblioteca.
   - `test_retriever_matches_pix_bank_account`, `test_retriever_matches_antecipacao`, `test_retriever_matches_crediario`, `test_retriever_matches_wifi`: reescritos para consultar o retriever novo e validar a presença das URLs oficiais em `documents`.
   - `test_retriever_matches_classica_smart` e `test_retriever_matches_payment_link`: substituídos pela validação de modelos e link pelo retriever novo.
   - `test_rag_abstention_out_of_domain`: reescrito para testar abstenção vetorial com o novo contrato de retorno (`status: "abstain"`, `documents: []`).
3. `tests/conftest.py` (atualizado):
   - Removida a importação legada `from src.agents.knowledge import get_retriever` e a fixture `retriever`.
   - Criada a fixture autouse `mock_knowledge_retriever` que indexa trechos oficiais de teste em diretório temporário com `KeywordFakeEmbedder` e intercepta `src.rag.retriever.get_knowledge_retriever`.

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

### 7. Higienização e Refatoração de Testes (Fases 1A a 3C)

**Total atual de testes**: 117 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 3C**: 7 novos testes em `tests/test_knowledge_rag.py` cobrindo o fluxo integrado do Knowledge Agent com o novo retriever, extração de URL e metadados, abstenção e indisponibilidade sem interrupção do grafo, além da refatoração completa dos testes unitários legados de `test_unit.py` e remoção da base legada ChromaDB.
- **Fase 3B**: 11 novos testes em `tests/test_rag_index.py`.
- **Fase 3A**: 12 novos testes em `tests/test_ingest.py`.
- **Fase 2E**: 9 novos testes em `tests/test_tokens_and_tools.py`.
- **Fase 2D**: 10 novos testes em `tests/test_specialists.py` e adaptação do fluxo hierárquico nos testes de integração.
- **Fase 2C**: 9 testes de integração de provedores em `tests/test_providers.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos baseados no router por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 3C (`python scripts/verify_phase3c.py`):
```text
PASS S1.old_kb_removed
PASS S2.legacy_removed
PASS S3.requirements
PASS S4.knowledge_prompt
PASS S5.readme
PASS R1.min_chunk_setting
PASS R2.default_keeps_3b_behaviour
PASS R2.tiny_page_dropped
PASS R2.tail_merged
PASS R3.committed_index_regenerated
PASS R4.tool_description_has_no_facts
PASS R4.tool_uses_retriever
PASS R4.tool_abstains
PASS K6.knowledge_flow_real_index
PASS R5.tool_unavailable_without_key
PASS R6.real_retriever_requires_key
PASS R6.real_retriever_wiring
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 117 passed in 11.64s
PASS Q3.tree_unchanged

SUMMARY: 27/27 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
117 passed in 11.64s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 3D

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final permanece delegado para ser gerado em ambiente Linux/container pelo usuário para compatibilidade com bibliotecas dependentes de SO (`uvloop`).
2. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
3. **Índice Commitado Regenerado**: O índice foi reconstruído com `RAG_MIN_CHUNK_CHARS = 120`, consolidando 92 chunks a partir das 30 páginas oficiais, sem nenhum trecho menor que 120 caracteres (`chunks.jsonl`, `embeddings.npy`, `index_meta.json`).
4. **Descontinuação Completa do ChromaDB**: Todo o código legado em `src/agents/knowledge.py`, `data/getnet_kb.json`, dependência `chromadb` em `requirements.txt`, volume e variáveis no `docker-compose.yml` foram integralmente expurgados do repositório.
5. **Próxima Fase (Fase 3D: Avaliação e Calibração Paramétrica do RAG)**: Criação de dataset rotulado com $\ge 30$ queries (in- e out-of-domain, PT e EN), calibração empírica do limiar `RAG_MIN_SCORE` e geração de relatórios de métricas (hit@k, MRR, precision/recall de abstenção) em `reports/`.
