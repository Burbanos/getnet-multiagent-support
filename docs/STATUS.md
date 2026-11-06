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

#### Isolamento de Ambiente em `tests/conftest.py`:
- `TICKETS_DB_PATH` isolado em diretório temporário (`tempfile.mkdtemp`) antes do import da aplicação, garantindo que a execução dos testes não altere a árvore git (`git status --porcelain` limpo).
- `mock_web_search` registrado como fixture autouse para monkeypatch de `web_search_tool`, impedindo qualquer tráfego de rede durante os testes.

---

### 8. Verificação e Saídas Oficiais

#### Verificação Completa (`python scripts/verify_phase1.py`):
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

*(Nota: a única falha restante é `B4.lock_regenerated`, decorrente da restrição explícita de não gerar `requirements.lock` no host Windows, devendo ser gerado em ambiente Linux pelo usuário).*

#### Execução de Testes Pytest (`python -m pytest -q`):
```text
.............................................                            [100%]
45 passed in 15.82s
```

#### Linting (`python -m ruff check .`):
```text
All checks passed!
```

#### Commit Base:
```text
c071ed2e0a7a7bf0eab85e4cd11bfc5eb818890b
```

---

### 9. Perguntas / divergências com o SPEC

1. **Geração de `requirements.lock`**: Conforme instrução explícita do prompt, o lockfile não foi gerado nesta máquina Windows para evitar resolução de wheels específicas de plataforma. O arquivo `Dockerfile` foi preparado para usar `requirements.lock` se presente (`COPY requirements.txt requirements.lock* ./`), com fallback para `requirements.txt`. A checagem `B4.lock_regenerated` passará assim que o lock for gerado em Linux.
2. **Exclusão de `scripts` no `ruff`**: O script `scripts/verify_phase1.py` possui imports e funções utilitárias que não devem ser modificados (regra: "NÃO edite scripts/verify_phase1.py"). Para que o linter `ruff check .` analise estritamente o código de produção (`src/`) e testes (`tests/`) sem violar a regra de imutabilidade do script verificador, adicionou-se `extend-exclude = ["scripts"]` em `[tool.ruff]` no `pyproject.toml`.
3. **Isolamento de sessão quando `session_id` é omitido**: O LangGraph armazena histórico conversacional por `thread_id`. Para requisições em que o cliente não informa `session_id`, gera-se um UUID novo por turno, prevenindo poluição de contexto entre testes independentes sem quebrar o suporte a múltiplos turnos quando `session_id` é fornecido.
