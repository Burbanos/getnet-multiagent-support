# Relatório de Calibração e Avaliação de Retrieval (RAG)

- **Gerado em:** 2026-11-07T03:20:43.939816+00:00
- **Dataset:** `data\eval\retrieval_labeled.jsonl` (48 consultas, sha256 `8178a22508da...`)
- **Índice:** `data/index` (92 chunks, modelo `gemini-embedding-2`, dim 768)

## 1. Métricas de Retrieval (Consultas Respondíveis)

| Métrica | Geral (n=30) | Português (n=21) | Inglês (n=9) |
| :--- | :---: | :---: | :---: |
| **hit@1** | 0.900 | 0.952 | 0.778 |
| **hit@3** | 0.967 | 1.000 | 0.889 |
| **hit@5** | 0.967 | 1.000 | 0.889 |
| **mrr@10** | 0.933 | 0.976 | 0.833 |
| **answer_hit@3** | 0.900 | 0.952 | 0.778 |

## 2. Limiar Escolhido e Métricas de Abstenção

- **Limiar Calibrado (`RAG_MIN_SCORE`):** `0.61`
- **Regra de Seleção:** maximize balanced accuracy on answerable vs off_topic; ties pick lower median
- **Balanced Accuracy:** 1.000
- **Taxa de Resposta (Answerable):** 1.000
- **Abstenção Off-Topic:** 1.000
- **Abstenção Uncovered (`uncovered`):** 0.000 (consultas uncovered fora do corpus oficial da Getnet)
- **Precisão de Abstenção:** 1.000
- **Recall de Abstenção:** 1.000

## 3. Curva de Abstenção

| Limiar | Answer Rate | Off-Topic Abstain | Uncovered Abstain | Balanced Accuracy | Precisão | Recall |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.30 | 1.000 | 0.000 | 0.000 | 0.500 | - | 0.000 |
| 0.35 | 1.000 | 0.000 | 0.000 | 0.500 | - | 0.000 |
| 0.40 | 1.000 | 0.000 | 0.000 | 0.500 | - | 0.000 |
| 0.45 | 1.000 | 0.000 | 0.000 | 0.500 | - | 0.000 |
| 0.50 | 1.000 | 0.000 | 0.000 | 0.500 | - | 0.000 |
| 0.55 | 1.000 | 0.750 | 0.000 | 0.875 | 1.000 | 0.750 |
| 0.60 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| 0.61 **(escolhido)** | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 |
| 0.65 | 1.000 | 1.000 | 0.100 | 1.000 | 1.000 | 1.000 |
| 0.70 | 0.967 | 1.000 | 0.200 | 0.983 | 0.889 | 1.000 |
| 0.75 | 0.767 | 1.000 | 0.600 | 0.883 | 0.533 | 1.000 |
| 0.80 | 0.600 | 1.000 | 0.900 | 0.800 | 0.400 | 1.000 |
| 0.85 | 0.100 | 1.000 | 1.000 | 0.550 | 0.229 | 1.000 |
| 0.90 | 0.000 | 1.000 | 1.000 | 0.500 | 0.211 | 1.000 |
| 0.95 | 0.000 | 1.000 | 1.000 | 0.500 | 0.211 | 1.000 |

## 4. Avisos

- `[!WARNING]` `uncovered_not_filtered`

## 5. Avaliação por Consulta

| ID | Idioma | Categoria | Top-1 Score | Top-1 Chunk | Gold Rank | Answer Hit@3 | Decisão |
| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: |
| `a01` | pt | answerable | 0.817 | `a35faa6f803d-004` | 1 | Sim | `answer` |
| `a02` | pt | answerable | 0.831 | `a35faa6f803d-005` | 1 | Sim | `answer` |
| `a03` | pt | answerable | 0.827 | `a35faa6f803d-003` | 1 | Sim | `answer` |
| `a04` | pt | answerable | 0.788 | `590a78a70a4e-001` | 1 | Sim | `answer` |
| `a05` | pt | answerable | 0.831 | `2c9f9e715248-000` | 1 | Sim | `answer` |
| `a06` | pt | answerable | 0.708 | `f42597cedc2c-000` | 1 | Sim | `answer` |
| `a07` | pt | answerable | 0.855 | `a0274ab9b8ba-001` | 1 | Sim | `answer` |
| `a08` | pt | answerable | 0.836 | `75a823f71e23-000` | 1 | Sim | `answer` |
| `a09` | pt | answerable | 0.807 | `75a823f71e23-000` | 1 | Sim | `answer` |
| `a10` | pt | answerable | 0.814 | `314e4bd739df-000` | 1 | Sim | `answer` |
| `a11` | pt | answerable | 0.796 | `018618194cc3-000` | 1 | Sim | `answer` |
| `a12` | pt | answerable | 0.820 | `28851a0d386e-001` | 1 | Sim | `answer` |
| `a13` | pt | answerable | 0.783 | `28851a0d386e-000` | 1 | Sim | `answer` |
| `a14` | pt | answerable | 0.810 | `e6e8bcc6e090-000` | 1 | Sim | `answer` |
| `a15` | pt | answerable | 0.851 | `e6e8bcc6e090-002` | 1 | Sim | `answer` |
| `a16` | pt | answerable | 0.720 | `b3cf4c4a6da6-003` | 1 | Sim | `answer` |
| `a17` | pt | answerable | 0.793 | `a35faa6f803d-004` | 2 | Não | `answer` |
| `a18` | pt | answerable | 0.802 | `f94bd60e1e43-000` | 1 | Sim | `answer` |
| `a19` | pt | answerable | 0.723 | `96da15e4cbd0-000` | 1 | Sim | `answer` |
| `a20` | pt | answerable | 0.833 | `081b9925942a-001` | 1 | Sim | `answer` |
| `a21` | pt | answerable | 0.846 | `5665e9a6303f-000` | 1 | Sim | `answer` |
| `e01` | en | answerable | 0.841 | `a35faa6f803d-000` | 1 | Sim | `answer` |
| `e02` | en | answerable | 0.867 | `2c9f9e715248-000` | 1 | Sim | `answer` |
| `e03` | en | answerable | 0.747 | `08d5affa1f91-002` | 2 | Sim | `answer` |
| `e04` | en | answerable | 0.759 | `4507fe8d48bb-000` | 1 | Sim | `answer` |
| `e05` | en | answerable | 0.651 | `590a78a70a4e-001` | - | Não | `answer` |
| `e06` | en | answerable | 0.741 | `6005d5ea376c-005` | 1 | Sim | `answer` |
| `e07` | en | answerable | 0.806 | `fb3e6c49736e-003` | 1 | Não | `answer` |
| `e08` | en | answerable | 0.740 | `53e32ad391e8-000` | 1 | Sim | `answer` |
| `e09` | en | answerable | 0.809 | `e73ab22a38ed-005` | 1 | Sim | `answer` |
| `u01` | pt | uncovered | 0.849 | `314e4bd739df-000` | - | - | `answer` |
| `u02` | pt | uncovered | 0.778 | `081b9925942a-002` | - | - | `answer` |
| `u03` | pt | uncovered | 0.701 | `28851a0d386e-001` | - | - | `answer` |
| `u04` | pt | uncovered | 0.711 | `28851a0d386e-001` | - | - | `answer` |
| `u05` | pt | uncovered | 0.770 | `28851a0d386e-000` | - | - | `answer` |
| `u06` | pt | uncovered | 0.691 | `28851a0d386e-001` | - | - | `answer` |
| `u07` | pt | uncovered | 0.732 | `590a78a70a4e-002` | - | - | `answer` |
| `u08` | en | uncovered | 0.767 | `4507fe8d48bb-000` | - | - | `answer` |
| `u09` | en | uncovered | 0.636 | `28851a0d386e-001` | - | - | `answer` |
| `u10` | en | uncovered | 0.743 | `75a823f71e23-000` | - | - | `answer` |
| `o01` | pt | off_topic | 0.539 | `28851a0d386e-001` | - | - | `abstain` |
| `o02` | pt | off_topic | 0.516 | `fb3e6c49736e-003` | - | - | `abstain` |
| `o03` | pt | off_topic | 0.553 | `47b12cbe60bc-000` | - | - | `abstain` |
| `o04` | pt | off_topic | 0.512 | `590a78a70a4e-005` | - | - | `abstain` |
| `o05` | pt | off_topic | 0.570 | `28851a0d386e-001` | - | - | `abstain` |
| `o06` | en | off_topic | 0.535 | `f715b5205be9-002` | - | - | `abstain` |
| `o07` | en | off_topic | 0.546 | `53e32ad391e8-002` | - | - | `abstain` |
| `o08` | en | off_topic | 0.547 | `28851a0d386e-001` | - | - | `abstain` |
