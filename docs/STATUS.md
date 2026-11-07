# STATUS DO REPOSITÓRIO

**Data de geração**: 06/11/2026 | **Branch**: `main`

---

### Fase 3A: Coleta das Fontes Oficiais e Conformidade com robots.txt (Fase 3A e 3A.1)

#### Nota sobre Ajuste de Fonte Oficial (Fase 3A.1):
- Na execução inicial da Fase 3A, o domínio `www.santander.com.br` retornou HTTP 403 Forbidden (bloqueio por CDN Akamai para o `USER_AGENT` público do projeto) mesmo na consulta ao `/robots.txt`. Em estrita conformidade com as regras de coleta ética (sem falsificação de User-Agent nem contorno de bloqueios), o domínio foi descontinuado da lista de fontes.
- Conforme alinhamento na Fase 3A.1, o domínio brasileiro foi substituído por `site.getnet.com.br` (site oficial direto da Getnet Brasil). Sua rota `/robots.txt` retorna HTTP 404, o que pela RFC 9309 significa ausência de restrições de rastreamento.
- A lista oficial `data/sources.yaml` foi atualizada para 33 fontes oficiais (10 globais em `getnet.net/en` e 23 nacionais em `site.getnet.com.br`).
- A coleta real via rede (`python -m src.rag.ingest`) resultou em:
  - `ok`: 30 páginas coletadas e higienizadas com sucesso (10 globais, 20 nacionais).
  - `no_content`: 3 páginas com conteúdo renderizado estritamente no navegador via JavaScript (`site.getnet.com.br/`, `site.getnet.com.br/link-de-pagamento/`, `site.getnet.com.br/pagamentos-pelo-whatsapp/`), registradas fielmente sem texto.
  - `robots_disallowed`: 0
  - `http_error`: 0
  - `off_allowlist`: 0

#### Verificação Fase 3A (`python scripts/verify_phase3a.py`):
```text
PASS C1.sources_yaml
PASS C1.no_portugal_market
PASS C1.no_blocked_santander
PASS C2.one_record_per_source
PASS C2.statuses_valid
PASS C3.ok_records_integrity
PASS C3.non_ok_without_text
PASS C4.corpus_size
PASS C5.manifest
PASS C6.attribution
PASS C6.readme_sources
PASS M1.user_agent
PASS M1.allowed_domains
PASS M2.robots_disallow
PASS M3.robots_404_allows
PASS M3.ua_header
PASS M4.extraction
PASS M4.record_fields
PASS M5.robots_5xx_disallows
PASS M6.http_error
PASS M6.no_content
PASS M7.redirect_off_allowlist
PASS M7.unknown_host_no_request
PASS M8.robots_cached
PASS M8.rate_limit
PASS M9.run_writes_outputs
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 100 passed in 14.97s
PASS Q3.tree_unchanged

SUMMARY: 34/34 passed
```

#### Commit Base da Fase 3A:
```text
e08c1f7644bc687146f627666f470f7f2700ef4d
```

#### Testes Alterados e Criados na Fase 3A:
1. `tests/test_ingest.py` (novo, 12 testes unitários 100% offline via `httpx.MockTransport`):
   - `test_extraction_clean_content_and_title`: validação da higienização HTML (remoção de tags de script, style, nav, header, footer, etc.) e extração de título.
   - `test_robots_txt_disallow_skips_page_request`: bloqueio preventivo de requisição quando o `robots.txt` desautoriza a rota.
   - `test_robots_txt_404_allows_page_request`: respeito à RFC 9309 onde HTTP 404 em `robots.txt` autoriza o rastreamento.
   - `test_robots_txt_500_disallows_page_request`: respeito à RFC 9309 onde HTTP 5xx em `robots.txt` trata temporariamente como desautorizado.
   - `test_user_agent_header_sent_on_all_requests`: envio estrito do `USER_AGENT` oficial em todas as requisições (`robots.txt` e páginas).
   - `test_http_error_handling`: captura e classificação de erros de servidor HTTP (500) gerando registro sem texto.
   - `test_no_content_for_short_pages`: páginas com menos de 300 caracteres úteis classificadas como `no_content`.
   - `test_redirect_off_allowlist`: redirecionamentos que saem dos domínios da allowlist são bloqueados e classificados como `off_allowlist`.
   - `test_unknown_host_off_allowlist_without_network_request`: URLs com host desconhecido nem chegam a disparar chamadas de rede.
   - `test_robots_txt_cached_single_request_per_host`: cache em memória do arquivo `robots.txt` por host na mesma sessão de ingestão.
   - `test_rate_limiting_enforced_per_host`: aplicação de intervalo mínimo (`min_delay_s`) entre requisições ao mesmo domínio.
   - `test_ingestor_run_generates_pages_jsonl_and_manifest`: ciclo completo de ponta a ponta gerando `data/corpus/pages.jsonl` e `manifest.json`.

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

### 7. Higienização e Refatoração de Testes (Fases 1A a 3A)

**Total atual de testes**: 100 testes aprovados e 100% offline (`verify_nonet`).

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

#### Verificação Fase 3A (`python scripts/verify_phase3a.py`):
```text
PASS C1.sources_yaml
PASS C1.no_portugal_market
PASS C1.no_blocked_santander
PASS C2.one_record_per_source
PASS C2.statuses_valid
PASS C3.ok_records_integrity
PASS C3.non_ok_without_text
PASS C4.corpus_size
PASS C5.manifest
PASS C6.attribution
PASS C6.readme_sources
PASS M1.user_agent
PASS M1.allowed_domains
PASS M2.robots_disallow
PASS M3.robots_404_allows
PASS M3.ua_header
PASS M4.extraction
PASS M4.record_fields
PASS M5.robots_5xx_disallows
PASS M6.http_error
PASS M6.no_content
PASS M7.redirect_off_allowlist
PASS M7.unknown_host_no_request
PASS M8.robots_cached
PASS M8.rate_limit
PASS M9.run_writes_outputs
PASS Q0.verify_phase2a
PASS Q0.verify_phase2b
PASS Q0.verify_phase2c
PASS Q0.verify_phase2d
PASS Q0.verify_phase2e
PASS Q1.ruff_clean
PASS Q2.pytest_offline_no_key :: 100 passed in 14.97s
PASS Q3.tree_unchanged

SUMMARY: 34/34 passed
```

#### Execução da Suíte Pytest (`python -m pytest -q`):
```text
100 passed in 14.97s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

---

### 9. Perguntas / divergências com o SPEC e apontamentos para a Fase 3B

1. **Geração de `requirements.lock` no Linux**: O arquivo de lock final permanece delegado para ser gerado em ambiente Linux/container pelo usuário para compatibilidade com bibliotecas dependentes de SO (`uvloop`).
2. **Custo Estimado (`estimated_cost_usd`)**: Mantido explicitamente como `None` conforme instrução do SPEC/prompt, ficando a precificação por milhão de tokens para a Fase 7.
3. **Corpus de Conhecimento e Páginas JavaScript**: Das 33 fontes oficiais (10 globais, 23 BR), 30 páginas foram indexadas com conteúdo superior a 300 caracteres úteis (`ok`), e 3 páginas institucionais com renderização puramente client-side via JavaScript (`https://site.getnet.com.br/`, `https://site.getnet.com.br/link-de-pagamento/`, `https://site.getnet.com.br/pagamentos-pelo-whatsapp/`) foram catalogadas sem texto como `no_content`.
4. **Próxima Fase (Fase 3B: Chunking, Enriquecimento e Indexação Vetorial)**: Implementar chunking hierárquico sobre `data/corpus/pages.jsonl`, preservação rigorosa de metadados (`url`, `title`, `market`) e substituição do retriever em memória para a nova coleção ChromaDB baseada nos documentos oficiais ingeridos.
