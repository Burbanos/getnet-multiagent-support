# STATUS DO REPOSITÓRIO

**Data de geração**: 07/11/2026 | **Branch**: `main`

---

### Fase 4A: Identidade pela Credencial, Isolamento por Usuário, Tickets por Dono e Rate Limit

#### Verificação Fase 4A (`python scripts/verify_phase4a.py`):
```text
PASS S1.no_default_user
PASS S2.no_plaintext_key_in_main
PASS S3.dead_confidence_setting_removed
PASS S4.config_documented
PASS S4.env_example_has_no_key
PASS S5.readme
PASS S6.demo_sends_key
PASS R0.api
PASS R0.settings
PASS A1.hash
PASS A1.parse_valid
PASS A2.parse_rejects
PASS A3.missing_or_invalid_401
PASS A3.dev_key_in_development
PASS A3.dev_operator_key
PASS A3.health_public_and_auth_mode
PASS A4.production_rejects_dev_keys
PASS A4.configured_keys
PASS A4.configured_keys_replace_dev_defaults
PASS A5.body_user_id
PASS I1.session_isolated_per_user
PASS I2.thread_id_format
PASS I3.session_id_generated_and_bounded
PASS I4.run_sync_requires_user
PASS T1.list_by_owner
PASS T2.get_by_owner
PASS T3.tickets_need_key
PASS L1.rate_limit_per_key
PASS L2.zero_disables
PASS C1.no_llm_key_503
PASS C2.config_error_503
PASS C2.transient_error_503
PASS C2.timeout_503
PASS C3.internal_error_500
PASS C4.metadata_fields
PASS Q0.auth_tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q0.verify_phase3d
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 132 passed in 14.93s
PASS Q3.tree_unchanged

SUMMARY: 48/48 passed
```

#### Commit Base da Fase 4A (`git rev-parse HEAD`):
```text
f467d568528fe9551a1e4c824d1ad30463c3fc11
```

#### Testes Criados na Fase 4A:
`tests/test_auth.py` (8 novos testes unitários):
- `test_parse_api_keys_valid_and_invalid`: testa parsing de chave válida e rejeição de entradas com hash inválido (tamanho != 64, não-hex), usuário vazio, role inválido e hashes duplicados.
- `test_auth_missing_or_invalid_key_401`: testa rejeição com HTTP 401 e detalhe genérico para cabeçalho ausente ou chave desconhecida (sem vazar a chave no log ou resposta).
- `test_auth_dev_defaults_and_production_rejection`: valida aceitação das chaves padrão de desenvolvimento quando APP_ENV=development e recusa total em APP_ENV=production sem API_KEYS.
- `test_auth_configured_keys_override_dev_defaults`: valida que configuração de API_KEYS aceita as chaves mapeadas e desabilita as chaves de desenvolvimento.
- `test_chat_body_user_id_mismatch_403`: valida erro HTTP 403 se user_id no corpo da requisição for divergente da identidade autenticada na chave.
- `test_session_isolation_and_thread_id`: valida isolamento completo de histórico entre dois usuários com mesmo session_id e formato composite `user_id:session_id` no checkpointer.
- `test_ticket_authorization_by_role_and_owner`: valida que customer só lista e acessa seus próprios tickets (recebendo 404 para tickets de terceiros) e operador pode listar todos ou filtrar por user_id.
- `test_rate_limiter_sliding_window_and_zero_disable`: valida bloqueio com HTTP 429 e cabeçalho Retry-After ao exceder limite e liberação após 60s via relógio simulado, bem como desativação com RATE_LIMIT_PER_MINUTE=0.

#### Testes Ajustados na Fase 4A:
- `tests/conftest.py`: adicionada fixture autouse `reset_auth_settings` para garantir `APP_ENV = "development"`, `API_KEYS = ""` e `reset_rate_limiter()` isolando a suíte de testes de variáveis locais e limites de taxa.
- `tests/test_eval_judge.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` e removido `user_id` manual no payload do teste de segurança, atualizando asserção para 401 quando o cabeçalho é omitido (conforme nova regra de autenticação estrita).
- `tests/test_graph_llm.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em requisições `/chat` e `/tickets` e atualizados testes de erro 500/503.
- `tests/test_robustness.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas aos endpoints de chat.
- `tests/test_specialists.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas HTTP à API.
- `tests/test_tokens_and_tools.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas `/chat`.
- `tests/test_unit.py`: adicionado cabeçalho `X-API-Key: getnet-dev-key` em chamadas `/chat` e `/tickets`; removido `cliente1988` hardcoded em testes de `/chat` para que a identidade derive do principal autenticado.

---

### Fase 3D: Avaliação do Retrieval e Calibração do RAG_MIN_SCORE

#### Verificação Fase 3D (`python scripts/verify_phase3d.py`):
```text
PASS S1.dataset_identical :: 48 queries, sha256 8178a22508da
PASS S2.dataset_composition
PASS R0.api
PASS R0.no_regex
PASS R1.sha_canonical
PASS R1.normalize
PASS R1.grid
PASS R2.load_labeled_validates
PASS R2.load_labeled_real
PASS R3.evaluate_matches_reference
PASS R4.curve_matches_reference
PASS R4.choose_matches_reference
PASS R4.choose_median_of_plateau
PASS R5.run_embed
PASS R6.run_report_writes
PASS R6.run_report_refuses_mismatch
PASS E1.query_embeddings
PASS E2.embeddings_plausible :: mean top1 answerable=0.795, off_topic=0.540
PASS P1.report_exists
PASS P1.provenance
PASS P2.retrieval_metrics_recomputed :: hit@1=0.900 hit@3=0.967 hit@5=0.967 mrr@10=0.933 answer_hit@3=0.900
PASS P2.per_query_recomputed
PASS P2.curve_recomputed
PASS P2.chosen_threshold :: chosen=0.61 balanced_accuracy=1.000 answer_rate=1.000 off_topic_abstain=1.000 uncovered_abstain=0.000
PASS P2.warnings :: warnings=['uncovered_not_filtered']
PASS P2.markdown_report
PASS P3.setting_updated
PASS P3.compose_consistent
PASS P4.readme
PASS Q0.calibration_tests
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q0.verify_phase3a
PASS Q0.verify_phase3b
PASS Q0.verify_phase3c
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 124 passed in 12.81s
PASS Q3.tree_unchanged

SUMMARY: 41/41 passed
```

#### Commit Base da Fase 3D:
```text
6cddc0ec2935827a1c1fe60fbd01df5356b0a836
```

#### Consultas `answerable` com `gold_rank` None ou `answer_hit@3` falso:
- `a17` (PT): `gold_rank = 2`, `answer_hit@3 = False` (top-1 score 0.793, chunk `a35faa6f803d-004`).
- `e05` (EN): `gold_rank = None`, `answer_hit@3 = False` (top-1 score 0.651, chunk `590a78a70a4e-001`).
- `e07` (EN): `gold_rank = 1`, `answer_hit@3 = False` (top-1 score 0.806, chunk `fb3e6c49736e-003`).

#### Consultas `uncovered` respondidas no limiar escolhido (`RAG_MIN_SCORE = 0.61`):
Todas as 10 consultas `uncovered` obtiveram score superior ao limiar calibrado (0.61) e decisão `answer`:
- `u01` (PT): score 0.849, chunk `314e4bd739df-000`, decisão `answer`
- `u02` (PT): score 0.778, chunk `081b9925942a-002`, decisão `answer`
- `u03` (PT): score 0.701, chunk `28851a0d386e-001`, decisão `answer`
- `u04` (PT): score 0.711, chunk `28851a0d386e-001`, decisão `answer`
- `u05` (PT): score 0.770, chunk `28851a0d386e-000`, decisão `answer`
- `u06` (PT): score 0.691, chunk `28851a0d386e-001`, decisão `answer`
- `u07` (PT): score 0.732, chunk `590a78a70a4e-002`, decisão `answer`
- `u08` (EN): score 0.767, chunk `4507fe8d48bb-000`, decisão `answer`
- `u09` (EN): score 0.636, chunk `28851a0d386e-001`, decisão `answer`
- `u10` (EN): score 0.743, chunk `75a823f71e23-000`, decisão `answer`

#### Testes Criados na Fase 3D:
`tests/test_retrieval_calibration.py` (7 novos testes unitários):
- `test_load_labeled_validations`: valida rejeição de categoria desconhecida, idioma inválido, id duplicado, campos vazios de URLs e trechos em answerable, e leitura de registros válidos.
- `test_evaluate_hit_and_mrr_ranks`: valida cálculo analítico de hit@1, hit@3, hit@5 e MRR@10 sobre matriz ortogonal e ranks conhecidos.
- `test_evaluate_answer_hit3_multiline`: valida normalização sem regex em correspondência de trechos com múltiplas quebras de linha e caixas altas/baixas.
- `test_abstention_curve_and_choose_threshold_tie`: valida métricas da curva de abstenção e desempate de platô de acurácia balanceada pela mediana inferior.
- `test_run_embed_with_fake_embedder`: valida que consultas são vetorizadas via `embed_query` (RETRIEVAL_QUERY) e nunca `embed_documents`, gravando shape (n, dim) e metadados JSON.
- `test_run_report_refuses_mismatches`: valida que `run_report` recusa divergências de `query_ids`, `dataset_sha256` ou `embedding_model`.
- `test_run_report_outputs`: valida geração dos relatórios JSON e Markdown em diretório temporário com conferência de chaves e métricas.

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

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 4B

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final permanece delegado para ser gerado em ambiente Linux/container pelo usuário para compatibilidade com bibliotecas dependentes de SO (`uvloop`).
2. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
3. **Calibração do Limiar `RAG_MIN_SCORE = 0.61`**: A avaliação do retrieval no conjunto rotulado de 48 consultas demonstrou separação perfeita (balanced accuracy = 1.000) entre consultas respondíveis e consultas fora de domínio (*off-topic*).
4. **Comportamento das Consultas *Uncovered***: Como previsto na especificação, as consultas *uncovered* pertencem ao domínio semântico Getnet/concorrentes e obtêm similaridade cosseno superior a 0.61 (aviso `uncovered_not_filtered`). A sua abstenção caberá ao prompt do Knowledge Agent ("não encontrado nas fontes oficiais") na Fase 6.
5. **Próxima Fase (Fase 4B: Checkpointer Persistente em SQLite)**: Substituição do `MemorySaver` in-memory pelo `SqliteSaver` persistente em disco (`data/checkpoints.db`), suporte a concorrência, migração de schema e retenção do isolamento estrito `thread_id = f"{user_id}:{session_id}"`.
6. **Proteção contra Enumeração de Tickets**: Acesso a tickets de outro cliente retorna HTTP 404 (o mesmo código para ticket inexistente), prevenindo enumeração de identificadores de tickets por clientes mal-intencionados.
