# A1 measurement-validity audit

- Run: `2026-08-16_032_v317_a1_measurement_validity`
- Outcome: `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`
- New fits/V5: 200/200
- Outer-test/calibration reads: `0/0`
- Claim boundary: construct-validity only; injected data are not physiological EEG or paper performance.

## D49 — frozen 15-subject scorer amendment

| Task | gain | CI95 | macro R@1 | subjects | PASS |
|---|---:|---:|---:|---:|---|
| task1_nr | 4.90543 | [4.796239319383288, 5.017761584659506] | 1 | 15 | PASS |
| task2_tsr | 4.71649 | [4.646392641564454, 4.786212454966998] | 1 | 15 | PASS |

## D50 — frozen graded semantic-injection curve

| Task | family floor | legacy floor | rho | alpha=10 family | alpha=10 legacy | PASS |
|---|---:|---:|---:|---|---|---|
| task1_nr | 0.01 | 0.03 | 0.833333 | True | True | False |
| task2_tsr | 0.01 | 0.03 | 0.833333 | True | True | False |

The admitted `FAIL_A1_ADMISSION` remains unchanged. This audit does not establish that real EEG has or lacks semantic increment.
