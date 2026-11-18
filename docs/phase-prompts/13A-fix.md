# Fase 13A-fix — Correções da revisão da 13A (CI vermelho)

**Modelo: Orchestrator (Argon).** Correção pequena sobre o commit `66add08`. Valem todas as regras do
`docs/phase-prompts/13A.md`, com as exceções escritas aqui.

O revisor rodou a 13A contra Postgres 16 e Redis 7 reais. O CI de `66add08` falhou em `integration` e `docker`. Causas,
confirmadas pelo revisor:

1. **Pool do checkpointer:** `ConnectionPool(max_size=pool_size, ...)` sem `min_size`. O padrão do psycopg_pool é
   `min_size=4`, então qualquer `pool_size` menor que 4 levanta `ValueError: max_size must be greater or equal than
   min_size`. Três testes de integração falham por isso (eles usam `pool_size=2`). O prompt da 13A ditou a chamada sem
   `min_size`; o erro também é do revisor.
2. **Job `docker`, item 4:** o `python -c` dentro do container imprime dois logs JSON no stdout antes do id; o `TID`
   fica com três linhas, a URL do `curl` fica malformada e o `curl` sai com código 3. Os itens 4 a 7 do job nunca rodaram.
3. **Corrida na partida das réplicas:** `app-a` e `app-b` sobem juntas e as duas criam o schema (`create_all`) e rodam o
   `PostgresSaver.setup()` ao mesmo tempo. Com 4 inicializações simultâneas num banco novo, 6 de 6 tentativas deram
   `DuplicateTable`/`UniqueViolation`. No Compose uma réplica cai na partida e o `restart: unless-stopped` esconde isso.
4. **Compose:** a lista de variáveis do app está repetida três vezes (âncora + `app-a` + `app-b`), porque o merge `<<` do
   YAML não junta listas. O prompt pedia UMA definição compartilhada.
5. **Jaeger:** `jaegertracing/all-in-one:1.62.0` é da linha 1.x, descontinuada; use a imagem v2.

## O que fazer

**A. `src/core/checkpointer.py`** — no `ConnectionPool` de `build_postgres_checkpointer`, passe `min_size=1` (e mantenha
`max_size=pool_size`).

**B. Setup do schema serializado entre réplicas** — em `src/core/db.py`, acrescente:
- `SCHEMA_LOCK_KEY` (uma constante inteira fixa) e um context manager `schema_lock(target: str)`: para URL Postgres, abre
  uma conexão **dedicada** `psycopg.connect(<url sem o +psycopg>, autocommit=True)` (nunca uma conexão do pool), adquire o
  lock com `SELECT pg_try_advisory_lock(%s)` **em laço** (espera 0,1 s entre tentativas; depois de 60 s levanta
  `TimeoutError`) e libera com `pg_advisory_unlock` no `finally`; para SQLite não faz nada.
- **Não use `pg_advisory_lock` (bloqueante).** O `setup()` do `PostgresSaver` roda `CREATE INDEX CONCURRENTLY`, que espera
  terminar toda sessão com snapshot aberto; uma sessão parada dentro de `pg_advisory_lock` segura um snapshot e o resultado
  é um deadlock que o Postgres não detecta (o revisor reproduziu). Com `pg_try_advisory_lock` em laço, nenhuma instrução
  fica aberta durante a espera.
- `ensure_schema` executa todo o trabalho dentro de `schema_lock(...)` quando a engine é Postgres, e
  `build_postgres_checkpointer` executa `saver.setup()` dentro de `schema_lock(url)`.

**C. Teste de integração** — acrescente em `tests/integration/test_postgres_redis_integration.py` a função
`test_concurrent_startup_setup_is_serialized`: num banco Postgres **novo, criado dentro do próprio teste** com
`CREATE DATABASE` e apagado no fim com `DROP DATABASE` (o banco da fixture de sessão já tem as tabelas e não exercita a
corrida), 4 threads começam juntas (`threading.Barrier(4)`) e
cada uma chama `ensure_schema(make_engine(url))` e depois `build_postgres_checkpointer(url, pool_size=1)`; nenhuma pode
levantar exceção, a tabela `tickets` e as tabelas do checkpointer existem no fim, e os pools são fechados.

**D. CI, job `docker`, item 4** — capture o id com a última linha do stdout e valide o formato antes de usar:
`TID=$(docker compose exec -T app-a python -c "..." | tail -n 1 | tr -d '\r')` seguido de
`echo "$TID" | grep -Eq '^GET-TKT-[0-9]{8}-[0-9A-F]{10}$'`. Nada mais no job muda.

**E. `docker-compose.yml`** — UMA definição das variáveis do app: um mapa com âncora (por exemplo `x-app-env: &app-env`,
com `APP_ENV: production` literal e as mesmas variáveis e padrões de hoje, sem `REPLICA_NAME`), usado por `app-a` e `app-b`
como `environment: {<<: *app-env, REPLICA_NAME: app-a}` (e `app-b`). O texto do arquivo não pode repetir nenhuma variável
do app. Troque `jaegertracing/all-in-one:1.62.0` por `jaegertracing/jaeger:2.<versão estável atual>` (OTLP HTTP na 4318 e UI
na 16686) e registre a versão no STATUS. Nada mais muda no Compose.

**F. Exceção à regra 2 (só esta):** em `tests/test_docker_defaults.py`, a linha `assert "- APP_ENV=production" in
compose_content` deixa de valer, porque o ambiente passa a ser um mapa. Troque-a por uma checagem mais forte, que carrega o
arquivo com `yaml.safe_load` e afirma `APP_ENV == "production"` no `environment` de todo serviço cujo nome começa com
`app-` (e que existem pelo menos dois). A linha do `${APP_ENV` e o resto do arquivo ficam como estão.

## Verificar, STATUS e commit

1. `ruff check .`, `pytest` e `python scripts/verify_phase13a.py` em primeiro plano (o verificador foi atualizado pelo
   revisor para cobrir estas correções; não o edite).
2. Reescreva `docs/STATUS.md` (no máximo 150 linhas): mantenha o conteúdo da 13A e acrescente uma seção "13A-fix" com as
   cinco correções, a versão do Jaeger e a saída real dos três comandos.
3. Commit único com `git add -A`, mensagem `phase-13a-fix: pool size, serialized schema setup, compose env, CI ticket id`,
   e push. Avise o autor com o hash; o revisor confere o CI.
