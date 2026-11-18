# Evidência de Integração e Observabilidade (compose-1)

- **Data UTC:** `2026-11-18T20:46:31.694302+00:00`
- **Commit:** `14f795b016ac81447d71dc3ff849fb5cec241110` (árvore suja: `não`)
- **Checks:** **9/9** aprovados

## Verificações (`checks`)

| Check | Resultado |
| :--- | :--- |
| `replicas_healthy` | PASS |
| `conversation_across_replicas` | PASS |
| `ticket_across_replicas` | PASS |
| `reply_delivered` | PASS |
| `rate_limit_shared` | PASS |
| `pii_absent_postgres` | PASS |
| `pii_absent_logs` | PASS |
| `trace_exported` | PASS |
| `trace_private` | PASS |

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
- **Chamado entre réplicas:** criação em `app-b` (`GET-TKT-20261118-1C173FD790`), PATCH em `app-a` (HTTP `200`, resume=`resumed`), mensagens após PATCH em `app-b`=`3`, eventos de auditoria=`4`.
- **Varredura de PII:** `pg_dump` (818067 bytes, bytea=630, marcador=28, pii={'card_spaced': 0, 'card_digits': 0, 'cpf_formatted': 0, 'cpf_digits': 0}); logs (`45634` bytes, marcador=0, pii={'card_spaced': 0, 'card_digits': 0, 'cpf_formatted': 0, 'cpf_digits': 0}).
- **Limite compartilhado:** primeiros 6 status=`[200, 200, 200, 200, 200, 200]`, 7º em 8001=HTTP `429` (Retry-After=`43`).
- **Traces no Jaeger:** conversa (`21` spans), PII (`21` spans, `marker_in_attributes=False`).
