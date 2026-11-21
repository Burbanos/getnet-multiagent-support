# Calibração do Juiz: judge_calibration_2

Amostra de 40 itens.

## Humanos vs Juízes Candidatos

| Comparação | Concordância | κ de Cohen | AC1 de Gwet | Estabilidade |
| :--- | :--- | :--- | :--- | :--- |
| Candidato 1 (`gemini-3.6-flash`, `0922b4a1`) × `autor` | 34/40 | 0,489 | 0,789 | 1,000 |
| Candidato 2 (`gemini-3.6-flash`, `f423be42`) × `autor` | 35/40 | 0,627 | 0,812 | 1,000 |
| Candidato 3 (`gemini-3.8-flash`, `f423be42`) × `autor` | 36/40 | 0,713 | 0,846 | 1,000 |

## Negativos humanos, abstenção e fundamentação

### Candidato 1: `gemini-3.6-flash` (`0922b4a14198`)

- **Execuções:** `jc2-a-1`, `jc2-a-2`, `jc2-a-3`
- **Contra `autor`:** κ(abstenção)=0,430; fundamentação exata=39/40, MAE=0,100; negativos=`g06`=True, `g08`=False, `g10`=True, `g17`=True, `g18`=True, `g19`=True, `g26`=False, `g32`=False, `g35`=False

### Candidato 2: `gemini-3.6-flash` (`f423be42c5f1`)

- **Execuções:** `jc2-b-1`, `jc2-b-2`, `jc2-b-3`
- **Contra `autor`:** κ(abstenção)=0,607; fundamentação exata=39/40, MAE=0,100; negativos=`g06`=True, `g08`=False, `g10`=True, `g17`=False, `g18`=False, `g19`=False, `g26`=True, `g32`=False, `g35`=False

### Candidato 3: `gemini-3.8-flash` (`f423be42c5f1`)

- **Execuções:** `jc2-c-1`, `jc2-c-2`, `jc2-c-3`
- **Contra `autor`:** κ(abstenção)=0,607; fundamentação exata=39/40, MAE=0,100; negativos=`g06`=True, `g08`=False, `g10`=True, `g17`=False, `g18`=False, `g19`=False, `g26`=False, `g32`=False, `g35`=False
