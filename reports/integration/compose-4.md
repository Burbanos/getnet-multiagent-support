# Evidência de Integração e Observabilidade (compose-4)

- **Data UTC:** `2026-11-21T18:18:21.221673+00:00`
- **Commit:** `5ad0b92c5dfbbb6ee864a1e0283ea648fcc91a00` (árvore suja: `não`)
- **Checks:** **17/17** aprovados

## Verificações (`checks`)

| Check | Resultado |
| :--- | :--- |
| `replicas_healthy` | PASS |
| `token_cross_replica` | PASS |
| `api_key_rejected_in_production` | PASS |
| `refresh_rotation_cross_replica` | PASS |
| `refresh_reuse_revokes_family` | PASS |
| `tampered_token_rejected` | PASS |
| `conversation_across_replicas` | PASS |
| `ticket_across_replicas` | PASS |
| `reply_delivered` | PASS |
| `sse_cross_replica` | PASS |
| `rate_limit_shared` | PASS |
| `pii_absent_postgres` | PASS |
| `pii_absent_logs` | PASS |
| `no_raw_refresh_tokens_in_dump` | PASS |
| `trace_exported` | PASS |
| `trace_private` | PASS |
| `alert_rules_loaded` | PASS |

## Serviços (`docker compose ps`)

| Serviço | Imagem | Estado |
| :--- | :--- | :--- |
| `app-a` | `getnet-multiagent-app:local` | `running` |
| `app-b` | `getnet-multiagent-app:local` | `running` |
| `grafana` | `grafana/grafana:11.3.1` | `running` |
| `jaeger` | `jaegertracing/jaeger:2.6.0` | `running` |
| `postgres` | `postgres:16-alpine` | `running` |
| `prometheus` | `prom/prometheus:v2.55.1` | `running` |
| `redis` | `redis:7-alpine` | `running` |

## Saúde das réplicas

| Réplica | Porta | HTTP | Ambiente | Estado | Rate Limit | Tracing |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `app-a` | 8000 | 200 | `production` | `postgres` | `redis` | `otlp` |
| `app-b` | 8001 | 200 | `production` | `postgres` | `redis` | `otlp` |

## Resumo dos cenários

- **Troca entre réplicas:** Turno 1 (`app-a`: status action=`pending_confirmation`), Turno 2 (`app-b`: status action=`executed`), mensagens na sessão=`4`, `/replacements` em `app-a`/`app-b`=`True`/`True`, eventos de auditoria=`1`.
- **Chamado entre réplicas:** criação em `app-b` (`GET-TKT-20261121-BFD60F7976`), PATCH em `app-a` (HTTP `200`, resume=`resumed`), mensagens após PATCH em `app-b`=`3`, eventos de auditoria=`4`.
- **Varredura de PII:** `pg_dump` (831057 bytes, bytea=651, marcador=6, pii={'card_spaced': 0, 'card_digits': 0, 'cpf_formatted': 0, 'cpf_digits': 0}); logs (`47655` bytes, marcador=0, pii={'card_spaced': 0, 'card_digits': 0, 'cpf_formatted': 0, 'cpf_digits': 0}).
- **Limite compartilhado:** primeiros 6 status=`[200, 200, 200, 200, 200, 200]`, 7º em 8001=HTTP `429` (Retry-After=`51`).
- **Traces no Jaeger:** conversa (`21` spans), PII (`14` spans, `marker_in_attributes=False`).
