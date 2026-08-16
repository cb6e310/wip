# A1-R measurement recovery

- Run: `2026-08-16_034_v318_a1_measurement_recovery`
- Outcome: `FAIL_A1R_RECOVERY`
- Fits/V5: 78/78
- Selected frontend: `None`
- Selected task scope: `[]`
- Outer-test/calibration reads: `0/0`
- Claim boundary: inner selection evidence only; no outer or paper claim.

| Task | Frontend | seen u_oof | seen family | cross u_oof | cross family | transfer loss | recovery delta | recovery PASS |
|---|---|---:|---|---:|---|---:|---:|---|
| task1_nr | A1_BP_CONCAT | 0.0362271 | False | -0.0104231 | False | 0.0466502 | n/a | False |
| task1_nr | A1R_LOG_BP_CONCAT | 0.0184847 | False | -0.0756598 | False | 0.0941445 | -0.06523668786679976 | False |
| task1_nr | A1R_T8_FIXATION | 0.0124934 | False | -0.0130155 | False | 0.0255089 | -0.0025924295051765935 | False |
| task2_tsr | A1_BP_CONCAT | 0.0104805 | False | -0.0451027 | False | 0.0555832 | n/a | False |
| task2_tsr | A1R_LOG_BP_CONCAT | -0.0110644 | False | -0.0191924 | False | 0.00812804 | 0.025910260826077194 | False |
| task2_tsr | A1R_T8_FIXATION | 0.0277639 | True | -0.0466669 | False | 0.0744308 | -0.001564201867011239 | False |

The v3.14 A1 failure and run-032 INVALID outcome remain unchanged.
