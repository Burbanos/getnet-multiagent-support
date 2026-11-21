# Relatório de Busca Híbrida (Denso + BM25 + Reranker LLM)

- Conjunto: `data/eval/retrieval_labeled2.jsonl` (`7cbb17ef977f`)
- Trechos no índice: 361
- Execuções avaliadas: `rerank2-1`

## Comparação de métricas

| Métrica | Denso (regra atual) | rerank2-1 | Média |
| --- | --- | --- | --- |
| `answer_rate` | 1.0000 | 1.0000 | 1.0000 |
| `hit@1` | 0.8500 | 1.0000 | 1.0000 |
| `hit@3` | 0.9000 | 1.0000 | 1.0000 |
| `mrr` | 0.8750 | 1.0000 | 1.0000 |
| `answer_hit@3` | 0.7500 | 1.0000 | 1.0000 |
| `off_topic_abstain_rate` | 1.0000 | 1.0000 | 1.0000 |
| `uncovered_abstain_rate` | 0.0000 | 1.0000 | 1.0000 |

## Decisão por consulta

| ID | Categoria | Denso (regra atual) | rerank2-1 |
| --- | --- | --- | --- |
| `r2a01` | answerable | responde (4) | responde (4) [ok] |
| `r2a02` | answerable | responde (4) | responde (1) [ok] |
| `r2a03` | answerable | responde (4) | responde (1) [ok] |
| `r2a04` | answerable | responde (4) | responde (1) [ok] |
| `r2a05` | answerable | responde (4) | responde (1) [ok] |
| `r2a06` | answerable | responde (4) | responde (1) [ok] |
| `r2a07` | answerable | responde (4) | responde (1) [ok] |
| `r2a08` | answerable | responde (4) | responde (1) [ok] |
| `r2a09` | answerable | responde (4) | responde (2) [ok] |
| `r2a10` | answerable | responde (4) | responde (3) [ok] |
| `r2a11` | answerable | responde (4) | responde (3) [ok] |
| `r2a12` | answerable | responde (4) | responde (1) [ok] |
| `r2a13` | answerable | responde (4) | responde (4) [ok] |
| `r2a14` | answerable | responde (4) | responde (2) [ok] |
| `r2a15` | answerable | responde (4) | responde (2) [ok] |
| `r2a16` | answerable | responde (4) | responde (2) [ok] |
| `r2a17` | answerable | responde (4) | responde (1) [ok] |
| `r2a18` | answerable | responde (4) | responde (1) [ok] |
| `r2a19` | answerable | responde (4) | responde (3) [ok] |
| `r2a20` | answerable | responde (4) | responde (1) [ok] |
| `r2u01` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `r2u02` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `r2u03` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `r2u04` | uncovered | responde (4) | abstém (no_passage_answers) [ok] |
| `r2o01` | off_topic | abstém | abstém (below_threshold) [gated] |
| `r2o02` | off_topic | abstém | abstém (below_threshold) [gated] |

## Mudanças de posição do trecho com a resposta (`answerable`)

| ID | Posição denso | Posições por execução | Média híbrida |
| --- | --- | --- | --- |
| `r2a01` | 2 | rerank2-1=1 | 1.00 |
| `r2a02` | None | rerank2-1=1 | 1.00 |
| `r2a03` | 4 | rerank2-1=1 | 1.00 |
| `r2a04` | None | rerank2-1=1 | 1.00 |
| `r2a05` | 2 | rerank2-1=1 | 1.00 |
| `r2a08` | 2 | rerank2-1=1 | 1.00 |
| `r2a18` | None | rerank2-1=1 | 1.00 |
| `r2a19` | None | rerank2-1=2 | 2.00 |
