# Real-vs-sham R1 inner diagnostic

- Run: `2026-08-22_003_v322_real_sham_r1_inner`
- Outcome: `FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Selected candidate: `None`
- Selected task scope: `[]`
- Ridge operations: `156`
- EEG V5/text-only ledgers: `150/6`
- Outer-test/calibration reads: `0/0`

| Task | Candidate | seen semantic | seen family | cross semantic | cross family | recovery delta | recovery pass |
|---|---|---:|---|---:|---|---:|---|
| task1_nr | F0_A1_BP_CONCAT/Y0_RAW_MINILM | 0.0454847 | True | 0.0389076 | False | n/a | False |
| task1_nr | F0_A1_BP_CONCAT/Y1_H_RESIDUAL_MINILM | 0.0533204 | False | 0.00150748 | False | -0.0374001 | False |
| task1_nr | F1_LOGREL_BP/Y0_RAW_MINILM | 0.0214429 | False | -0.0692105 | False | -0.108118 | False |
| task1_nr | F1_LOGREL_BP/Y1_H_RESIDUAL_MINILM | -0.000681573 | False | -0.198292 | False | -0.237199 | False |
| task1_nr | F2_T8_FIXATION/Y0_RAW_MINILM | -0.000210484 | False | -0.0106049 | False | -0.0495125 | False |
| task1_nr | F2_T8_FIXATION/Y1_H_RESIDUAL_MINILM | 0.0229033 | False | -0.0216692 | False | -0.0605768 | False |
| task2_tsr | F0_A1_BP_CONCAT/Y0_RAW_MINILM | 0.00155238 | False | 0.0182842 | False | n/a | False |
| task2_tsr | F0_A1_BP_CONCAT/Y1_H_RESIDUAL_MINILM | -0.00833388 | False | -0.0587268 | False | -0.0770111 | False |
| task2_tsr | F1_LOGREL_BP/Y0_RAW_MINILM | -0.0143338 | False | 0.0185587 | False | 0.000274483 | False |
| task2_tsr | F1_LOGREL_BP/Y1_H_RESIDUAL_MINILM | -0.00927182 | False | 0.0150418 | False | -0.00324244 | False |
| task2_tsr | F2_T8_FIXATION/Y0_RAW_MINILM | 0.0232735 | False | -0.020927 | False | -0.0392112 | False |
| task2_tsr | F2_T8_FIXATION/Y1_H_RESIDUAL_MINILM | 0.0496585 | False | -0.0585043 | False | -0.0767885 | False |

Channel-block permutation remains reported only as a topology sentinel; legacy u_oof/u_min are retained sensitivities.

This is inner-only `RESEARCH_DIAGNOSTIC_ONLY` evidence. Parent/R0 outcomes are immutable. No outer confirmation, calibration, alignment, direct u+, EQ-ANMA, A3, ROAMM, or Gate is released.

The only possible next step is author review of `R2_REAL_SHAM_OUTER_CONFIRMATION_FREEZE_IF_R1_PASS`; R2 was not run.
