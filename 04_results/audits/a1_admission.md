# A1 admission audit

- Run: `2026-08-16_027_v314_a1_admission`
- Outcome: `FAIL_A1_ADMISSION`
- Preflight: `PASS`; 9 fits; max 0.135 s/fit
- Full pilot fits: 630; V5 ledgers: 639
- Outer-test EEG/features/labels/metrics read: `false`

## A-A1 through A-A4

| Task | Basis | A-A1 u_oof (95% CI) | A-A1 u_min (95% CI) | A-A1 | A-A2 | A-A3 |
|---|---|---:|---:|---|---|---|
| task1_nr | raw | -0.0410274 [-0.08094766421050514, -0.0026373244212528355] | -0.788317 [-0.9122656058155941, -0.6590526024508749] | FAIL | PASS | FAIL |
| task1_nr | token_local_frozen_initial_latent | 0.000220516 [-0.011020755520116164, 0.01177249767753654] | -0.381025 [-0.41724490782858625, -0.3430286788559128] | FAIL | PASS | FAIL |

task1_nr A-A4: `PASS`.
| task2_tsr | raw | -0.0380119 [-0.08902500950914431, 0.009330593928556818] | -0.747634 [-0.9002616035832207, -0.6020518781798497] | FAIL | PASS | FAIL |
| task2_tsr | token_local_frozen_initial_latent | -0.00771624 [-0.021427150300124834, 0.005200372319231889] | -0.380916 [-0.42156124670491835, -0.3404669790061012] | FAIL | PASS | FAIL |

task2_tsr A-A4: `PASS`.

This is a Stage-0 diagnostic pilot, not Stage 1, Gate A, route evidence, a held-out result, or a paper conclusion.
