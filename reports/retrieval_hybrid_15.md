# Relatório de Busca Híbrida (Denso + BM25 + Reranker LLM)

- Conjunto: `data/eval/retrieval_labeled.jsonl` (`8178a22508da`)
- Trechos no índice: 361
- Execuções avaliadas: `rerank-8`

## Comparação de métricas

| Métrica | Denso (regra atual) | rerank-8 | Média |
| --- | --- | --- | --- |
| `answer_rate` | 1.0000 | 1.0000 | 1.0000 |
| `hit@1` | 0.8333 | 0.9333 | 0.9333 |
| `hit@3` | 0.9000 | 0.9667 | 0.9667 |
| `mrr` | 0.8694 | 0.9444 | 0.9444 |
| `answer_hit@3` | 0.8667 | 0.9667 | 0.9667 |
| `off_topic_abstain_rate` | 1.0000 | 1.0000 | 1.0000 |
| `uncovered_abstain_rate` | 0.0000 | 0.6000 | 0.6000 |

## Decisão por consulta

| ID | Categoria | Denso (regra atual) | rerank-8 |
| --- | --- | --- | --- |
| `a01` | answerable | responde (4) | responde (3) [ok] |
| `a02` | answerable | responde (4) | responde (2) [ok] |
| `a03` | answerable | responde (4) | responde (2) [ok] |
| `a04` | answerable | responde (4) | responde (3) [ok] |
| `a05` | answerable | responde (4) | responde (3) [ok] |
| `a06` | answerable | responde (2) | responde (1) [ok] |
| `a07` | answerable | responde (4) | responde (1) [ok] |
| `a08` | answerable | responde (4) | responde (1) [ok] |
| `a09` | answerable | responde (4) | responde (1) [ok] |
| `a10` | answerable | responde (4) | responde (1) [ok] |
| `a11` | answerable | responde (4) | responde (1) [ok] |
| `a12` | answerable | responde (4) | responde (2) [ok] |
| `a13` | answerable | responde (4) | responde (1) [ok] |
| `a14` | answerable | responde (4) | responde (2) [ok] |
| `a15` | answerable | responde (4) | responde (4) [ok] |
| `a16` | answerable | responde (4) | responde (2) [ok] |
| `a17` | answerable | responde (4) | responde (1) [ok] |
| `a18` | answerable | responde (4) | responde (1) [ok] |
| `a19` | answerable | responde (4) | responde (1) [ok] |
| `a20` | answerable | responde (4) | responde (1) [ok] |
| `a21` | answerable | responde (4) | responde (2) [ok] |
| `e01` | answerable | responde (4) | responde (3) [ok] |
| `e02` | answerable | responde (4) | responde (2) [ok] |
| `e03` | answerable | responde (4) | responde (4) [ok] |
| `e04` | answerable | responde (4) | responde (3) [ok] |
| `e05` | answerable | responde (4) | responde (1) [ok] |
| `e06` | answerable | responde (4) | responde (2) [ok] |
| `e07` | answerable | responde (4) | responde (3) [ok] |
| `e08` | answerable | responde (4) | responde (2) [ok] |
| `e09` | answerable | responde (4) | responde (1) [ok] |
| `u01` | uncovered | responde (4) | responde (1) [ok] |
| `u02` | uncovered | responde (4) | responde (4) [ok] |
| `u03` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `u04` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `u05` | uncovered | responde (4) | responde (3) [ok] |
| `u06` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `u07` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `u08` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `u09` | uncovered | responde (4) | responde (1) [ok] |
| `u10` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `o01` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o02` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o03` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o04` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o05` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o06` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o07` | off_topic | abstém | abstém (below_threshold) [gated] |
| `o08` | off_topic | abstém | abstém (below_threshold) [gated] |

## Mudanças de posição do trecho com a resposta (`answerable`)

| ID | Posição denso | Posições por execução | Média híbrida |
| --- | --- | --- | --- |
| `a01` | 2 | rerank-8=1 | 1.00 |
| `a02` | 1 | rerank-8=2 | 2.00 |
| `a07` | 2 | rerank-8=1 | 1.00 |
| `a16` | 4 | rerank-8=None | None |
| `a17` | None | rerank-8=1 | 1.00 |
| `e03` | None | rerank-8=3 | 3.00 |
| `e04` | 3 | rerank-8=1 | 1.00 |
| `e05` | None | rerank-8=1 | 1.00 |
| `e06` | 2 | rerank-8=1 | 1.00 |
| `e07` | 3 | rerank-8=1 | 1.00 |
