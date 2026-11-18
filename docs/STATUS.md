# STATUS DO REPOSITÓRIO

**Subfase:** 13D-1 (`13D-1-fix`) — Correções do script de evidência do Compose
**Base:** `ce0ceec` (13D-1) | **Python:** 3.13.3

## O que mudou (13D-1-fix)

- **Varredura de `bytea` no `pg_dump` ([compose_evidence.py](scripts/compose_evidence.py)):** criada `scan_dump(dump_text, marker)` que decodifica os valores hexadecimais `\\x...` gravados em texto pelo `PostgresSaver`/`pg_dump` em UTF-8 (`errors="replace"`), soma às ocorrências do texto restante e retorna `pii`, `marker` e `bytea_values`. Substituído o uso de `scan_pii` sobre o dump bruto pelo `scan_dump`.
- **Uma chave de API por cenário e `.env` sem `GEMINI_API_KEY` ([compose_evidence.py](scripts/compose_evidence.py)):** criada `make_api_keys()` gerando cinco chaves aleatórias distintas (`conversation`, `ticket`, `pii`, `rate_limit`, `operator`) e sua especificação SHA-256 `API_KEYS` (cada cenário usa no máximo 5 requisições antes do teste explícito de rate limit), além de `render_env(pg_password, api_keys_spec)` sem escrever `GEMINI_API_KEY` no `.env` temporário.
- **Entrega do operador avaliada no `PATCH` ([compose_evidence.py](scripts/compose_evidence.py)):** criada `ticket_checks(patch_status, patch_body, messages_after_patch, audit_actions)` validando `status == "answered"`, `resume.status == "resumed"`, `ticket_reply_delivered` na auditoria e pelo menos 2 mensagens `assistant` em `GET /sessions/<sessão>/messages` em `app-b` após o `PATCH` em `app-a` (seguido do Turno 2 em `app-b` sem comparação de substring do texto do operador).
- **Testes ([test_compose_evidence.py](tests/test_compose_evidence.py)):** acrescentados 3 testes cobrindo `scan_dump` (dump sintético com `\\x...`, com e sem PII), `make_api_keys` + `render_env`, e `ticket_checks` (totalizando 6 testes no arquivo).

## Verificações

- `python -m ruff check .`: `All checks passed!`
- `python -m pytest -q -p no:cacheprovider`: `504 passed, 13 deselected in 80.03s`
- `python scripts/verify_phase13d1.py`: `SUMMARY: 30/30 passed` (`PASS A0`–`A5`, `PASS S1.status`, `PASS T1`–`T11`, `PASS G1`–`G2`, `PASS R1`–`R4`, `PASS Q1`–`Q6`, `INFO Q7.integration_suite`)

## Perguntas / divergências

Nenhuma divergência identificada com `docs/SPEC.md`, `docs/phase-prompts/13D-1.md` ou `docs/phase-prompts/13D-1-fix.md`.
