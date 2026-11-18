# Human Validation Agreement (v2-1)

- **Source run:** `v2-1`
- **Sample items:** 30
- **Seed:** `getnet-human-validation-2026-11-12`
- **Pass rate (deterministic checks):** 90.0%
- **Acceptable rate (human):** 96.7%

## Comparisons

| Comparison | Agree/n | Rate | Wilson 95% CI | Kappa |
| :--- | :--- | :--- | :--- | :--- |
| `route_vs_label` | 25/27 | 92.6% | [76.6%, 97.9%] | 0.869 |
| `abstain_vs_label` | 24/26 | 92.3% | [75.9%, 97.9%] | 0.752 |
| `acceptable_vs_checks` | 28/30 | 93.3% | [78.7%, 98.2%] | 0.474 |
| `acceptable_vs_judge` | 28/30 | 93.3% | [78.7%, 98.2%] | -0.034 |
| `abstained_vs_judge` | 29/30 | 96.7% | [83.3%, 99.4%] | 0.911 |

## Groundedness Rating (Human vs Judge)

| Metric | Value |
| :--- | :--- |
| n | 30 |
| Exact match | 30/30 (100.0%) |
| Within 1 point | 30/30 (100.0%) |
| Human mean | 5.000 |
| Judge mean | 5.000 |
| Human lower than judge | 0 |
| Human higher than judge | 0 |

## Disagreements

### `route_vs_label` (2)

- `h13` (`off05`): human=`conhecimento` vs other=`conta`
- `h24` (`x02`): human=`conta` vs other=`ambos`

### `abstain_vs_label` (2)

- `h11` (`k16`): human=`True` vs other=`False`
- `h17` (`u01`): human=`False` vs other=`True`

### `acceptable_vs_checks` (2)

- `h11` (`k16`): human=`True` vs other=`False`
- `h30` (`u08`): human=`True` vs other=`False`

### `acceptable_vs_judge` (2)

- `h02` (`e04`): human=`False` vs other=`True`
- `h07` (`m01`): human=`True` vs other=`False`

### `abstained_vs_judge` (1)

- `h02` (`e04`): human=`True` vs other=`False`
