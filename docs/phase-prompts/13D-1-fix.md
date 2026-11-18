# Fase 13D-1-fix — Correções do script de evidência do Compose

**Modelo: Orchestrator (Argon).** Base: `ce0ceec` (13D-1). A revisão achou três defeitos em `scripts/compose_evidence.py`
que fariam a execução do autor no Codespaces falhar ou medir errado. Só esse script, os testes dele e o `docs/STATUS.md`
mudam; o resto das regras de `docs/phase-prompts/13D-1.md` continua valendo (arquivos do revisor intocados, testes
existentes só ganham linhas, nada de rede ou LLM real nos testes).

## Passo 0 — Conferir a pasta

`git status --short` deve mostrar só arquivos do revisor: `docs/SPEC.md` e `scripts/verify_phase13d1.py` modificados e o
novo `docs/phase-prompts/13D-1-fix.md`. Qualquer outra coisa: pare e avise. `docs/phase-prompts/13D-1.md` continua no
repositório.

## Passo 1 — Os três defeitos

1. **O `pg_dump` esconde os checkpoints.** O `PostgresSaver` grava as mensagens em colunas `bytea`, e o `pg_dump` em texto
   as escreve como `\\x` seguido de hexadecimal. O revisor reproduziu: com uma mensagem gravada, o marcador aparece 0 vezes
   no texto do dump e 6 vezes depois de decodificar os `bytea`. Hoje `pii_absent_postgres` falharia (marcador não achado), e
   a varredura de cartão e CPF não enxerga os checkpoints. Crie a função pura `scan_dump(dump_text, marker) -> dict` com
   `pii` (as quatro contagens de `scan_pii`, somando o texto do dump sem os valores `bytea` e os valores `bytea`
   decodificados como UTF-8 com `errors="replace"`), `marker` (mesma soma) e `bytea_values` (quantos valores `\\x...`
   havia). Use-a no passo do PII no lugar do `scan_pii` do dump.
2. **O limite de 6 por minuto vale por chave em todos os endpoints.** O `authenticate` conta toda requisição autenticada,
   e hoje a mesma chave do cliente faz 5 conversas e 3 consultas em menos de um minuto: a 7ª recebe 429. Crie a função pura
   `make_api_keys() -> tuple[dict[str, str], str]`, que devolve cinco chaves aleatórias, uma por cenário (`conversation`,
   `ticket`, `pii`, `rate_limit`, `operator`), e a especificação de `API_KEYS` com os hashes (as três primeiras para
   `cliente1988:customer`, `rate_limit` para `cliente_rl:customer`, `operator` para `operador_evidencia:operator`). Cada
   cenário usa a sua chave; nenhum cenário faz mais de 5 requisições com a mesma chave.
3. **A entrega da resposta do operador acontece no `PATCH`.** O `PATCH /tickets/<id>` chama `resume_after_operator`, que
   entrega a resposta na conversa na hora e devolve `resume.status == "resumed"`; a mensagem seguinte do cliente é um turno
   normal e não repete a resposta do operador. Crie a função pura `ticket_checks(patch_status, patch_body,
   messages_after_patch, audit_actions) -> dict` com `ticket_across_replicas` (PATCH 200 e status `answered`) e
   `reply_delivered` (além disso, `resume.status == "resumed"`, `ticket_reply_delivered` na auditoria e pelo menos duas
   mensagens do assistente em `GET /sessions/<sessão>/messages`, consultado em `app-b` depois do PATCH). Remova a
   comparação do texto do operador com a resposta do turno seguinte; esse turno continua sendo feito e registrado, como
   prova de que `app-b` segue a conversa retomada em `app-a`.

Além disso, `GEMINI_API_KEY` **não** é gravada no `.env` temporário: o `docker-compose.yml` já a recebe do ambiente do shell
(`${GEMINI_API_KEY:-}`). Crie a função pura `render_env(pg_password, api_keys_spec) -> str`, que monta o `.env` temporário
(`POSTGRES_PASSWORD`, `API_KEYS`, `RATE_LIMIT_PER_MINUTE=6`, `TRACING_EXPORTER=otlp`), e use-a no `run`.

## Passo 2 — Testes, verificação, STATUS e commit

1. `tests/test_compose_evidence.py` ganha pelo menos 3 testes (um por função nova; `scan_dump` com um dump sintético no
   formato real do `pg_dump`, com e sem PII). Só acrescente linhas.
2. `ruff check .`, `pytest` e `python scripts/verify_phase13d1.py` em primeiro plano. Qualquer FAIL: corrija o código
   (nunca o verificador) ou pare e registre.
3. Reescreva `docs/STATUS.md` (pt-BR, no máximo 150 linhas, mencionando "13D-1"): o que a correção mudou, saída real dos três
   comandos e "Perguntas / divergências".
4. Commit único com `git add -A`, mensagem `phase-13d1-fix: compose evidence scans bytea, one key per scenario, delivery
   judged at the PATCH`, e push. Avise o autor com o hash. Não rode o script do Compose nem avaliações reais.
