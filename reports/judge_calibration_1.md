# Calibração do Juiz: judge_calibration_1

Amostra de 30 itens.

## Humanos vs Juízes Candidatos

| Comparação | Concordância | κ de Cohen | AC1 de Gwet | Estabilidade |
| :--- | :--- | :--- | :--- | :--- |
| Humanos (`autor` × `anotador`) | 25/30 | -0,056 | 0,803 | — |
| Candidato 1 (`gemini-3.6-flash`, `0922b4a1`) × `autor` | 27/30 | -0,047 | 0,890 | 0,933 |
| Candidato 1 (`gemini-3.6-flash`, `0922b4a1`) × `anotador` | 26/30 | 0,268 | 0,837 | 0,933 |
| Candidato 2 (`gemini-3.6-flash`, `f423be42`) × `autor` | 28/30 | 0,474 | 0,924 | 1,000 |
| Candidato 2 (`gemini-3.6-flash`, `f423be42`) × `anotador` | 25/30 | 0,194 | 0,790 | 1,000 |
| Candidato 3 (`gemini-3.8-flash`, `f423be42`) × `autor` | 28/30 | 0,474 | 0,924 | 1,000 |
| Candidato 3 (`gemini-3.8-flash`, `f423be42`) × `anotador` | 25/30 | 0,194 | 0,790 | 1,000 |

## Negativos humanos, abstenção e fundamentação

### Candidato 1: `gemini-3.6-flash` (`0922b4a14198`)

- **Execuções:** `jc1-a-1`, `jc1-a-2`, `jc1-a-3`
- **Contra `autor`:** κ(abstenção)=0,911; fundamentação exata=30/30, MAE=0,000; negativos=`h02`=True
- **Contra `anotador`:** κ(abstenção)=0,380; fundamentação exata=28/30, MAE=0,133; negativos=`h03`=True, `h06`=False, `h23`=True, `h30`=True

### Candidato 2: `gemini-3.6-flash` (`f423be42c5f1`)

- **Execuções:** `jc1-b-1`, `jc1-b-2`, `jc1-b-3`
- **Contra `autor`:** κ(abstenção)=1,000; fundamentação exata=29/30, MAE=0,067; negativos=`h02`=False
- **Contra `anotador`:** κ(abstenção)=0,328; fundamentação exata=29/30, MAE=0,067; negativos=`h03`=True, `h06`=True, `h23`=True, `h30`=False

### Candidato 3: `gemini-3.8-flash` (`f423be42c5f1`)

- **Execuções:** `jc1-c-1`, `jc1-c-2`, `jc1-c-3`
- **Contra `autor`:** κ(abstenção)=0,911; fundamentação exata=29/30, MAE=0,067; negativos=`h02`=False
- **Contra `anotador`:** κ(abstenção)=0,380; fundamentação exata=29/30, MAE=0,067; negativos=`h03`=True, `h06`=True, `h23`=True, `h30`=False
