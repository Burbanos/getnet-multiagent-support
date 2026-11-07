# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 3B: Fragmentação, Índice de Embeddings e Retriever (Biblioteca)

#### Verificação Fase 3B (`python scripts/verify_phase3b.py`):
```text
PASS L1.settings
PASS L2.get_embedder
PASS L2.get_embedder_requires_key
PASS L3.boilerplate_removed
PASS L3.dash_lines_removed
PASS L3.non_ok_ignored
PASS L3.max_chars
PASS L3.verbatim_lines
PASS L3.deterministic_ids
PASS L3.fields
PASS L4.build_index
PASS L4.load_rejects_mismatch
PASS L4.search_sorted
PASS L5.retriever_success
PASS L5.retriever_abstain
PASS L5.top_k
PASS I1.index_files
PASS I2.meta
PASS I3.embeddings_shape
PASS I4.chunk_fields
PASS I5.chunk_provenance
PASS I5.chunk_verbatim
PASS I5.chunk_size
PASS I6.no_boilerplate
PASS I6.page_coverage
PASS I7.embeddings_are_semantic :: intra=0.806 inter=0.685
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 111 passed in 15.85s
PASS Q3.tree_unchanged

SUMMARY: 35/35 passed
```

#### Commit Base da Fase 3B:
```text
fb0923f148e96a79c8b34ff55540966c445a88ea
```

#### Testes Alterados e Criados na Fase 3B:
1. `tests/test_rag_index.py` (novo, 11 testes unitários determinísticos e 100% offline com `FakeKeywordEmbedder`):
   - `test_boilerplate_removal_and_dash_lines`: remoção de linhas de rodapé/boilerplate presentes em $\ge 4$ páginas e de linhas compostas apenas por traços/pontuação (ex.: "—").
   - `test_non_ok_records_ignored`: registros com status diferente de "ok" ignorados na fragmentação.
   - `test_chunk_size_capped_at_max_chars`: chunks respeitando o limite máximo de caracteres (900 chars).
   - `test_chunk_lines_are_verbatim`: preservação estrita e verbatim das linhas originais da página fonte nos chunks.
   - `test_chunk_id_deterministic_and_unique`: identificadores de chunk reproduzíveis e determinísticos (`{doc_sha256[:12]}-{idx:03d}`).
   - `test_chunk_fields_completeness`: presença de todos os campos (`chunk_id`, `doc_url`, `title`, `market`, `fetched_at`, `doc_sha256`, `text`).
   - `test_build_index_artifacts_and_normalization`: geração de `embeddings.npy` em float32 normalizado (norma L2 = 1.0), `chunks.jsonl` e `index_meta.json`.
   - `test_vector_index_load_valid_and_mismatches`: carregamento do índice com validação de modelo e dimensões esperadas (levantando `ValueError` em caso de incompatibilidade).
   - `test_vector_index_search_cosine_ordering`: ordenação decrescente por similaridade de cosseno nas buscas do índice.
   - `test_retriever_success_abstain_and_top_k`: retorno formatado com documentos relevantes em caso de score $\ge min\_score$, abstenção explícita (`status: "abstain"`) quando abaixo do limiar e respeito a `top_k`.
   - `test_get_embedder_configuration`: `get_embedder` levanta `LLMNotConfiguredError` se `GEMINI_API_KEY` não estiver definida, e constrói `GoogleGenerativeAIEmbeddings` com modelo, dimensão e task type corretos quando configurada.

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

### 7. Higienização e Refatoração de Testes (Fases 1A a 3B)

**Total atual de testes**: 111 testes aprovados e 100% offline (`verify_nonet`).

- **Fase 3B**: 11 novos testes em `tests/test_rag_index.py` cobrindo fragmentação com remoção de boilerplate, filtro de linhas de pontuação, normalização L2 e persistência do índice vetorial (`embeddings.npy`, `chunks.jsonl`, `index_meta.json`), busca por cosseno e abstenção formal do retriever.
- **Fase 3A**: 12 novos testes em `tests/test_ingest.py` cobrindo conformidade ética de robots.txt, RFC 9309 (404 permitido, 5xx restrito), rate limiting por host, isolamento de domínios na allowlist, extração e limpeza de tags HTML e persistência do corpus.
- **Fase 2E**: 9 novos testes em `tests/test_tokens_and_tools.py`.
- **Fase 2D**: 10 novos testes em `tests/test_specialists.py` e adaptação do fluxo hierárquico nos testes de integração.
- **Fase 2C**: 9 testes de integração de provedores em `tests/test_providers.py`.
- **Fase 2B**: 9 testes de robustez e tratamento de exceções em `tests/test_robustness.py`.
- **Fase 2A**: 9 testes de integração e function calling em `tests/test_graph_llm.py`.
- **Fase 1B**: 2 testes em `tests/test_eval_judge.py` e isolamento estrito de tickets/rede no `conftest.py`.
- **Fase 1A**: Remoção de testes obsoletos baseados no router por regex.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Fase 3B (`python scripts/verify_phase3b.py`):
```text
PASS L1.settings
PASS L2.get_embedder
PASS L2.get_embedder_requires_key
PASS L3.boilerplate_removed
PASS L3.dash_lines_removed
PASS L3.non_ok_ignored
PASS L3.max_chars
PASS L3.verbatim_lines
PASS L3.deterministic_ids
PASS L3.fields
PASS L4.build_index
PASS L4.load_rejects_mismatch
PASS L4.search_sorted
PASS L5.retriever_success
PASS L5.retriever_abstain
PASS L5.top_k
PASS I1.index_files
PASS I2.meta
PASS I3.embeddings_shape
PASS I4.chunk_fields
PASS I5.chunk_provenance
PASS I5.chunk_verbatim
PASS I5.chunk_size
PASS I6.no_boilerplate
PASS I6.page_coverage
PASS I7.embeddings_are_semantic :: intra=0.806 inter=0.685
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 111 passed in 15.85s
PASS Q3.tree_unchanged

SUMMARY: 35/35 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
111 passed in 15.85s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 3C

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final permanece delegado para ser gerado em ambiente Linux/container pelo usuário para compatibilidade com bibliotecas dependentes de SO (`uvloop`).
2. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
3. **Índice Commitado de Embeddings**: O índice oficial gerado com `gemini-embedding-2` contém 94 chunks a partir das 30 páginas oficiais, com discriminação semântica confirmada (`intra=0.806` vs `inter=0.685`). Os arquivos `data/index/{chunks.jsonl, embeddings.npy, index_meta.json}` encontram-se commitados e versionados.
4. **Próxima Fase (Fase 3C: Integração do Retriever aos Agentes)**: Conectar o novo `Retriever` da biblioteca ao `KnowledgeAgent` (`src/agents/knowledge.py` e `src/tools/agent_tools.py`), aposentando a base estática legada `data/getnet_kb.json` e o ChromaDB provisório.
