# Real-vs-sham R2 geometry inner diagnostic

- Run: `2026-08-23_004_v323_real_sham_r2_geometry_inner`
- Outcome: `FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Passing task scope: `[]`
- Ridge operations / V5 ledgers: `102/102`
- M1 transform ledger rows: `300`
- Outer-test/calibration reads: `0/0`

| Task | Cell | Role | seen semantic | seen family | cross semantic | cross family | recovery | pass |
|---|---|---|---:|---|---:|---|---:|---|
| task1_nr | M0_STRICT_INDUCTIVE/B0_RAW_A1 | immutable_baseline | 0.0454847 | True | 0.0389076 | False | n/a | False |
| task1_nr | M0_STRICT_INDUCTIVE/B1_TOKEN_LOCAL_LATENT | primary_inductive_candidate | 0.0137519 | False | 0.0144845 | False | -0.0244231 | False |
| task1_nr | M1_UNLABELED_TRANSDUCTIVE_EA/B0_RAW_A1 | secondary_transductive_diagnostic | 0.0283147 | False | -0.0104054 | False | -0.049313 | False |
| task1_nr | M1_UNLABELED_TRANSDUCTIVE_EA/B1_TOKEN_LOCAL_LATENT | secondary_transductive_diagnostic | 0.00991143 | False | -0.0112146 | False | -0.0501222 | False |
| task2_tsr | M0_STRICT_INDUCTIVE/B0_RAW_A1 | immutable_baseline | 0.00155238 | False | 0.0182842 | False | n/a | False |
| task2_tsr | M0_STRICT_INDUCTIVE/B1_TOKEN_LOCAL_LATENT | primary_inductive_candidate | 0.0100478 | False | 0.0159164 | False | -0.00236786 | False |
| task2_tsr | M1_UNLABELED_TRANSDUCTIVE_EA/B0_RAW_A1 | secondary_transductive_diagnostic | -0.0148246 | False | -0.0199167 | False | -0.0382009 | False |
| task2_tsr | M1_UNLABELED_TRANSDUCTIVE_EA/B1_TOKEN_LOCAL_LATENT | secondary_transductive_diagnostic | 0.00965939 | False | 0.000759967 | False | -0.0175243 | False |

M0/B1 is the only inductive candidate. Every M1 result is an unlabeled transductive secondary diagnostic and cannot release inductive or paper-level evidence.

Channel-block remains a topology sentinel; both semantic single-sham contrasts and legacy u_oof/u_min are retained.

Parent/R0/R1 outcomes and formal artifacts are immutable. No F3, Y1, outer confirmation, calibration, direct u+, EQ-ANMA, A3, ROAMM, or Gate was run.

Stop for author review. No outer confirmation was started.
