# Human Validation Agreement (v2-1)

- **Source run:** `v2-1`
- **Sample items:** 30
- **Seed:** `getnet-human-validation-2026-11-12`
- **Pass rate (deterministic checks):** 90.0%
- **Acceptable rate (human):** 86.7%

## Comparisons

| Comparison | Agree/n | Rate | Wilson 95% CI | Kappa |
| :--- | :--- | :--- | :--- | :--- |
| `route_vs_label` | 24/27 | 88.9% | [71.9%, 96.1%] | 0.799 |
| `abstain_vs_label` | 24/26 | 92.3% | [75.9%, 97.9%] | 0.708 |
| `acceptable_vs_checks` | 25/30 | 83.3% | [66.4%, 92.7%] | 0.194 |
| `acceptable_vs_judge` | 25/30 | 83.3% | [66.4%, 92.7%] | -0.056 |
| `abstained_vs_judge` | 25/30 | 83.3% | [66.4%, 92.7%] | 0.380 |

## Groundedness Rating (Human vs Judge)

| Metric | Value |
| :--- | :--- |
| n | 30 |
| Exact match | 28/30 (93.3%) |
| Within 1 point | 28/30 (93.3%) |
| Human mean | 4.867 |
| Judge mean | 5.000 |
| Human lower than judge | 2 |
| Human higher than judge | 0 |

## Disagreements

### `route_vs_label` (3)

- `h06` (`m03`): human=`conhecimento` vs other=`conta`
- `h12` (`s01`): human=`conhecimento` vs other=`conta`
- `h24` (`x02`): human=`conta` vs other=`ambos`

### `abstain_vs_label` (2)

- `h03` (`u03`): human=`False` vs other=`True`
- `h17` (`u01`): human=`False` vs other=`True`

### `acceptable_vs_checks` (5)

- `h02` (`e04`): human=`True` vs other=`False`
- `h03` (`u03`): human=`False` vs other=`True`
- `h06` (`m03`): human=`False` vs other=`True`
- `h11` (`k16`): human=`True` vs other=`False`
- `h23` (`m05`): human=`False` vs other=`True`

### `acceptable_vs_judge` (5)

- `h03` (`u03`): human=`False` vs other=`True`
- `h06` (`m03`): human=`False` vs other=`True`
- `h07` (`m01`): human=`True` vs other=`False`
- `h23` (`m05`): human=`False` vs other=`True`
- `h30` (`u08`): human=`False` vs other=`True`

### `abstained_vs_judge` (5)

- `h01` (`e02`): human=`False` vs other=`True`
- `h08` (`o03`): human=`False` vs other=`True`
- `h22` (`o01`): human=`False` vs other=`True`
- `h27` (`off04`): human=`False` vs other=`True`
- `h30` (`u08`): human=`False` vs other=`True`
