# Real-vs-sham R4 orthogonal inner diagnostic

- Run: `2026-08-24_006_v325_real_sham_r4_orthogonal_inner`
- Outcome: `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Passing task scope: `[]`
- Ridge operations: `234`
- Final-scoring V5 / nuisance ledgers: `54/180`
- Outer-test/calibration reads: `0/0`

| Task | Method | Role | seen semantic | seen family | cross semantic | cross family | recovery | pass |
|---|---|---|---:|---|---:|---|---:|---|
| task1_nr | P0_JOINT_RIDGE_REPLICATION | baseline_replication | 0.0454847 | True | 0.0389076 | False | n/a | False |
| task1_nr | C1_SUBJECT_BLOCK_ORTHOGONAL | sole_candidate | 0.0423467 | False | 0.0388348 | False | -7.28185e-05 | False |
| task2_tsr | P0_JOINT_RIDGE_REPLICATION | baseline_replication | 0.00155238 | False | 0.0182842 | False | n/a | False |
| task2_tsr | C1_SUBJECT_BLOCK_ORTHOGONAL | sole_candidate | -0.00280146 | False | 0.0152228 | False | -0.00306141 | False |

C1 is the only candidate. P0 exactly replicates the inherited joint ridge baseline.

C1 uses five deterministic two-subject source-fit blocks. Every OOF residual excludes its held-out subjects; mY is shared across arms and mX uses symmetric row scope and capacity. Residual probes contain only 840D EEG residuals.

Seen/cross scoring uses only source-fit full nuisance models and the frozen query formula. No seen/cross fit, calibration, normalizer update, support selection, or target-subject statistic was used.

Parent/R0/R1/R2/R3 outcomes and formal artifacts are immutable. No outer confirmation, direct u+, EQ-ANMA, A3, ROAMM, or Gate was run.

Stop for author review. No downstream task was started.
