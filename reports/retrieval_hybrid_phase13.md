# Relatório de Busca Híbrida (Denso + BM25 + Reranker LLM)

- Conjunto: `data/eval/retrieval_labeled.jsonl` (`8178a22508da`)
- Trechos no índice: 103
- Execuções avaliadas: `rerank-4`, `rerank-5`, `rerank-6`

## Comparação de métricas

| Métrica | Denso (regra atual) | rerank-4 | rerank-5 | rerank-6 | Média |
| --- | --- | --- | --- | --- | --- |
| `answer_rate` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `hit@1` | 0.9000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `hit@3` | 0.9667 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `mrr` | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `answer_hit@3` | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `off_topic_abstain_rate` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `uncovered_abstain_rate` | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## Decisão por consulta

| ID | Categoria | Denso (regra atual) | rerank-4 | rerank-5 | rerank-6 |
| --- | --- | --- | --- | --- | --- |
| `a01` | answerable | responde (4) | responde (3) [ok] | responde (3) [ok] | responde (3) [ok] |
| `a02` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a03` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a04` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a05` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a06` | answerable | responde (1) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a07` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a08` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a09` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a10` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a11` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a12` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a13` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a14` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a15` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a16` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `a17` | answerable | responde (4) | responde (3) [ok] | responde (3) [ok] | responde (3) [ok] |
| `a18` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a19` | answerable | responde (3) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a20` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `a21` | answerable | responde (4) | responde (2) [ok] | responde (4) [ok] | responde (2) [ok] |
| `e01` | answerable | responde (4) | responde (3) [ok] | responde (3) [ok] | responde (3) [ok] |
| `e02` | answerable | responde (4) | responde (1) [ok] | responde (4) [invalid] | responde (4) [invalid] |
| `e03` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `e04` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `e05` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `e06` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `e07` | answerable | responde (4) | responde (2) [ok] | responde (1) [ok] | responde (1) [ok] |
| `e08` | answerable | responde (4) | responde (2) [ok] | responde (2) [ok] | responde (2) [ok] |
| `e09` | answerable | responde (4) | responde (1) [ok] | responde (1) [ok] | responde (1) [ok] |
| `u01` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u02` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u03` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u04` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u05` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u06` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u07` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u08` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u09` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `u10` | uncovered | responde (4) | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] | abstém (no_passage_answers) [ok] |
| `o01` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o02` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o03` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o04` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o05` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o06` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o07` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |
| `o08` | off_topic | abstém | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] | abstém (below_threshold) [gated] |

## Mudanças de posição do trecho com a resposta (`answerable`)

| ID | Posição denso | Posições por execução | Média híbrida |
| --- | --- | --- | --- |
| `a01` | 2 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `a02` | 1 | rerank-4=2, rerank-5=2, rerank-6=2 | 2.00 |
| `a07` | 2 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `a16` | 2 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `a17` | 3 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `e03` | 2 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `e05` | None | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `e06` | 2 | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
| `e07` | None | rerank-4=1, rerank-5=1, rerank-6=1 | 1.00 |
