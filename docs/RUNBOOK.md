# Runbook de Alertas — Getnet Multi-Agent Support

Procedimentos operacionais para os onze alertas definidos em `deploy/alerts.yml`.

## GetnetHighErrorRate

- **O que significa:** Mais de 5% das requisições em `/chat` ou `/api/v1/chat` retornaram código HTTP 5xx nos últimos 5 minutos (com volume mínimo de 20 requisições).
- **Primeiras verificações:**
  1. Consultar logs estruturados das réplicas (`docker compose logs --tail=200 app-a app-b`) buscando `status_code=500`/`503` e `exception`.
  2. Verificar `GET /health` em todas as réplicas para checar PostgreSQL (`state_backend`) e `llm_configured`.
  3. Inspecionar traces com erro no Jaeger pelo `trace_id`.
- **Mitigação:** Se o provedor de LLM estiver instável, confirmar que `LLM_FALLBACK_MODEL` está definido e alcançável. Em falha de conexão com PostgreSQL, verificar saúde do banco e pool (`DB_POOL_SIZE`).
- **Escalonamento:** Se o índice de 5xx permanecer acima de 5% por mais de 10 minutos após confirmar saúde do banco e provedores, acionar engenharia de plataforma / plantão de SRE.

## GetnetHighChatLatencyP95

- **O que significa:** O percentil 95 do tempo de resposta dos endpoints de chat superou 10 segundos na janela de 5 minutos.
- **Primeiras verificações:**
  1. Comparar `getnet_llm_calls_total` e spans `llm.call` no Jaeger para identificar se a demora está no supervisor, no planejador, nos especialistas, no verificador ou no reranker.
  2. Verificar latência de consultas externas (`search_web`, APIs de clima/câmbio) e tempos de I/O do PostgreSQL/Redis.
- **Mitigação:** Avaliar redução temporária de `LLM_TIMEOUT_S`, verificação de sobrecarga no modelo primário ou degradação controlada de ferramentas externas lentas.
- **Escalonamento:** Escalar para o responsável de infraestrutura/LLM caso o p95 ultrapasse `LLM_TIMEOUT_S` ou cause timeouts em sequência.

## GetnetLLMErrorsOrFallbacks

- **O que significa:** Ocorreram mais de 3 falhas ou ativações de failover (`status="error"` ou `"fallback"`) nas chamadas a modelos de LLM em 5 minutos.
- **Primeiras verificações:**
  1. Checar `getnet_llm_calls_total` por `caller` (`Supervisor`, `Planner`, `Verifier`, `InjectionClassifier`, `LanguageRewriter`).
  2. Inspecionar logs JSON de `multiagent.llm` para distinguir erro de cota/rede (`LLMUnavailableError`) de erro de configuração (`LLMConfigurationError`).
- **Mitigação:** Em erro de configuração ou chave expirada, corrigir `GEMINI_API_KEY` ou nome de modelo e reiniciar as réplicas. Em erro transitório/cota, validar funcionamento do `LLM_FALLBACK_MODEL`.
- **Escalonamento:** Se ambas as famílias de modelo falharem ou houver erro persistente de cota, escalar para o responsável pela conta do provedor de IA.

## GetnetGuardrailClassifierDegraded

- **O que significa:** O classificador LLM de injeção de prompt registrou erros (`getnet_guardrail_classifier_total{status="error"}`), deixando o sistema exposto em modo fail-open (`GUARDRAIL_CLASSIFIER_FAIL_MODE=open`).
- **Primeiras verificações:**
  1. Consultar logs do logger `multiagent.orchestrator` filtrando decisões `classifier_error_open`.
  2. Verificar disponibilidade do modelo configurado em `GUARDRAIL_CLASSIFIER_MODEL` (ou `LLM_MODEL`) e timeout `GUARDRAIL_CLASSIFIER_TIMEOUT_S`.
- **Mitigação:** Caso haja incidente de segurança ativo durante indisponibilidade prolongada do classificador, alternar `GUARDRAIL_CLASSIFIER_FAIL_MODE=closed` ou ajustar o modelo/timeout do classificador.
- **Escalonamento:** Se o classificador não se recuperar em 15 minutos, escalar para o time de segurança e responsáveis pelo provedor de LLM.

## GetnetRateLimitBackendErrors

- **O que significa:** O limitador de taxa distribuído (`RedisRateLimiter`) encontrou erros ao acessar o Redis e entrou em fallback local por memória em uma ou mais réplicas.
- **Primeiras verificações:**
  1. Verificar saúde e conectividade do container/instância Redis (`redis-cli ping` / logs do Redis).
  2. Conferir `GET /health` buscando `rate_limit_backend: "redis_degraded"`.
- **Mitigação:** Restabelecer conectividade de rede, memória ou processo do Redis; enquanto degradado, monitorar carga por réplica pois o limite não é compartilhado entre instâncias.
- **Escalonamento:** Acionar equipe de infraestrutura se o Redis não responder após reinício ou apresentar saturação de memória/CPU.

## GetnetOperatorNotificationFailures

- **O que significa:** Pelo menos uma tentativa de notificação por webhook (`OPERATOR_WEBHOOK_URL`) para equipe humana falhou nos últimos 5 minutos.
- **Primeiras verificações:**
  1. Checar logs de `multiagent.notifier` e registros recentes na tabela `tickets` (`notification_status='failed'`).
  2. Testar acessibilidade e código HTTP do endpoint configurado em `OPERATOR_WEBHOOK_URL`.
- **Mitigação:** Verificar disponibilidade do receptor de webhook ou credenciais do serviço de destino; orientar operadores a monitorarem diretamente a fila em `/operator`.
- **Escalonamento:** Se o serviço receptor de chamados estiver indisponível, abrir incidente junto ao time responsável pelo sistema de atendimento/webhook.

## GetnetMerchantNotificationFailures

- **O que significa:** Falhou a publicação no broker de eventos (`getnet_merchant_notifications_total{status="failed"}`) ao registrar resposta de operador em `PATCH /tickets/{id}`.
- **Primeiras verificações:**
  1. Verificar conectividade do Redis (canal `getnet:events:*`) e logs de `multiagent.events`.
  2. Checar o gauge `getnet_sse_connections` e erros no endpoint `GET /sessions/{session_id}/events`.
- **Mitigação:** Restabelecer o Redis pub/sub; os lojistas conectados ao `/demo` continuarão recebendo atualizações via fallback de consulta em `/sessions/{id}/messages`.
- **Escalonamento:** Se o Redis estiver saudável mas a publicação continuar falhando, escalar para o time de backend responsável pela camada de eventos.

## GetnetOldestOpenTicketAge

- **O que significa:** Existe ao menos um chamado com status `open` ou `in_progress` aguardando há mais de 3.600 segundos (1 hora) na base.
- **Primeiras verificações:**
  1. Listar chamados em aberto via `GET /tickets?status=open` e `GET /tickets?status=in_progress` ordenando pelos mais antigos.
  2. Confirmar se operadores estão conectados e conseguindo autenticar em `/operator`.
- **Mitigação:** Priorizar o atendimento dos chamados mais antigos no console do operador (`/operator`) e validar se não houve falha prévia de notificação aos atendentes.
- **Escalonamento:** Escalar para a coordenação da fila de atendimento humano caso o SLA operacional esteja estourado por falta de capacidade.

## GetnetHighAbstentionRate

- **O que significa:** Mais de 30% das respostas bem-sucedidas dos últimos 15 minutos terminaram em abstenção (com pelo menos 10 requisições).
- **Primeiras verificações:**
  1. Verificar logs do `Retriever`, `Verifier` e do índice em `data/index/` (checar integridade dos arquivos e score mínimo `RAG_MIN_SCORE`).
  2. Avaliar se houve mudança súbita no padrão de perguntas dos lojistas ou indisponibilidade da API de embeddings (`EMBEDDING_MODEL`).
- **Mitigação:** Se a causa for falha de embeddings ou reranker, verificar `GEMINI_API_KEY` e conectividade; se for lacuna documental recorrente, registrar tópicos para futura ampliação do corpus.
- **Escalonamento:** Escalar para o responsável pelo pipeline de RAG e base de conhecimento quando a taxa não decorrer de perguntas fora de escopo legítimas.

## GetnetEstimatedCostPerHour

- **O que significa:** O custo acumulado estimado de chamadas de LLM ultrapassou US$ 2,00 na janela móvel de 1 hora.
- **Primeiras verificações:**
  1. Identificar qual agente concentra consumo em `getnet_llm_tokens_total`, `getnet_llm_calls_total` e spans de tracing.
  2. Verificar se há rajadas atípicas de tráfego, retries excessivos do supervisor/verificador ou possíveis abusos em `/chat`.
- **Mitigação:** Ajustar `RATE_LIMIT_PER_MINUTE`, revisar limites de iterações (`MAX_SUPERVISOR_STEPS`) ou investigar clientes específicos pelo `key_id` nos logs de autenticação.
- **Escalonamento:** Se houver tráfego abusivo persistente ou risco de exaustão de orçamento, escalar para SRE/segurança e responsável financeiro do projeto.

## GetnetReplicaDown

- **O que significa:** O Prometheus não conseguiu coletar `/metrics` de uma das réplicas configuradas (`up{job="getnet-multiagent"} == 0`) por mais de 1 minuto.
- **Primeiras verificações:**
  1. Checar estado dos containers (`docker compose ps`) e saúde local (`GET /health` nas portas 8000 e 8001).
  2. Inspecionar logs da réplica afetada para verificar OOM, falha de startup (`validate_state_config`/`validate_auth_config`) ou crash do processo.
- **Mitigação:** Reiniciar a réplica (`docker compose restart app-a` ou `app-b`) e confirmar retorno de `up == 1` após passar o healthcheck.
- **Escalonamento:** Se a réplica falhar repetidamente ao subir ou reiniciar em loop, acionar o plantão de infraestrutura/SRE com os logs capturados.
