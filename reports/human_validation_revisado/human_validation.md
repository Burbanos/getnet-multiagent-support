# Human Validation Agreement (v2-1)

- **Source run:** `v2-1`
- **Sample items:** 30
- **Seed:** `getnet-human-validation-2026-11-12`
- **Pass rate (deterministic checks):** 90.0%
- **Acceptable rate (human):** 93.3%

## Comparisons

| Comparison | Agree/n | Rate | Wilson 95% CI | Kappa |
| :--- | :--- | :--- | :--- | :--- |
| `route_vs_label` | 26/27 | 96.3% | [81.7%, 99.3%] | 0.935 |
| `abstain_vs_label` | 24/26 | 92.3% | [75.9%, 97.9%] | 0.752 |
| `acceptable_vs_checks` | 29/30 | 96.7% | [83.3%, 99.4%] | 0.783 |
| `acceptable_vs_judge` | 27/30 | 90.0% | [74.4%, 96.5%] | -0.047 |
| `abstained_vs_judge` | 29/30 | 96.7% | [83.3%, 99.4%] | 0.911 |

## Groundedness Rating (Human vs Judge)

| Metric | Value |
| :--- | :--- |
| n | 30 |
| Exact match | 29/30 (96.7%) |
| Within 1 point | 29/30 (96.7%) |
| Human mean | 4.933 |
| Judge mean | 5.000 |
| Human lower than judge | 1 |
| Human higher than judge | 0 |

## Disagreements

### `route_vs_label` (1)

- `h13` (`off05`): human=`conhecimento` vs other=`conta`

### `abstain_vs_label` (2)

- `h11` (`k16`): human=`True` vs other=`False`
- `h17` (`u01`): human=`False` vs other=`True`

### `acceptable_vs_checks` (1)

- `h11` (`k16`): human=`True` vs other=`False`

### `acceptable_vs_judge` (3)

- `h02` (`e04`): human=`False` vs other=`True`
- `h07` (`m01`): human=`True` vs other=`False`
- `h30` (`u08`): human=`False` vs other=`True`

### `abstained_vs_judge` (1)

- `h02` (`e04`): human=`True` vs other=`False`
