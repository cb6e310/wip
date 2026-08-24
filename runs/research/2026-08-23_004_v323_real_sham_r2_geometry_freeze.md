# Run R004 — v3.23 R2 geometry inner diagnostic freeze

## Author freeze

- Task: `R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC`
- Branch: `research/real-sham-r2-geometry-inner`
- Base: `012590ff1bc9c421644168a555511715bb30ec4a`
- R1 outcome: `FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Status before execution: `READY`

## Frozen cells

- `M0_STRICT_INDUCTIVE/B0_RAW_A1`
- `M0_STRICT_INDUCTIVE/B1_TOKEN_LOCAL_LATENT`
- `M1_UNLABELED_TRANSDUCTIVE_EA/B0_RAW_A1`
- `M1_UNLABELED_TRANSDUCTIVE_EA/B1_TOKEN_LOCAL_LATENT`
- Target: `Y0_RAW_MINILM`
- Tasks: `task1_nr`, `task2_tsr`
- Folds: `inner_s0_t0`, `inner_s1_t0`, `inner_s2_t0`
- Arms: real, trial shuffle, within-trial-unit shuffle, channel block

## Budget and boundary

`6 H-only + 96 geometry probes = 102 ridge operations`, 102 V5 ledgers, and
outer/calibration reads `0/0`. M1 is unlabeled transductive only; it cannot
release an inductive or paper-level claim.

This is a freeze template. Codex appends the executed outcome only after formal
contract, tests, compile, state/status, diff-check and parent/R0/R1 hash checks.

## Executed outcome

- Run ID: `2026-08-23_004_v323_real_sham_r2_geometry_inner`
- Outcome: `FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC`
- Passing task scope: none
- Scope violations: none
- Parent/R0/R1 hashes: passed and immutable

Neither the sole inductive candidate M0/B1 nor either secondary transductive M1
cell passed the frozen cross family plus paired recovery criteria. M0/B0
reproduced the R1 baseline subject values exactly (maximum absolute difference
`0.0`). This is a valid negative inner diagnostic, not paper-level evidence.

## Execution accounting

- H-only Y0 ridge operations: `6`
- Geometry probe ridge operations: `96`
- Total ridge operations / unique V5 ledgers: `102/102`
- D102 transform ledger rows / unique scopes / unique hashes: `300/300/300`
- B1 frozen helper calls: `72`; encoder training operations: `0`
- Outer-test/calibration reads: `0/0`
- F3/Y1/outer/direct u+/EQ-ANMA/A3/ROAMM/Gate executions: `0`

All D102 transforms used real-arm EEG values only, float64 full covariance,
labels=false, shared_across_arms=true, transductive=true, and fallback=false.
Minimum covariance trace was `20.22948118791483`; minimum lambda/eigenvalue
floor was `5.268088791264029e-08`.

## Formal outputs

- `artifacts/real_sham_r2_geometry_contract.yaml`: `cb28e85029ec01dff3961e101a42d00672155ac7258641a077bf4bd6cf6eee78`
- `04_results/diagnostics/real_sham_r2_geometry_inner.json`: `6aca8e2be1e062092a3ca7a4133cacd179e0fd73926240bd48739aedaa51426b`
- `04_results/diagnostics/real_sham_r2_geometry_inner.md`: `931091510f32059e6b199028eab6e8023960d74a093b8a09546925b709a60d55`
- `04_results/diagnostics/real_sham_r2_geometry_inner_run_ledger.jsonl.gz`: `8e9ee515cfef330eba7d6f2d6caaa91ec4d4b140678c191e21f11597253fecd3`
- `04_results/diagnostics/real_sham_r2_geometry_inner_transform_ledger.jsonl.gz`: `21d257d3002a4e3aff8198317bd2e25293eab3b2d8ec585b85acad42b951021b`

## Verification

- Focused R2 pytest: `9 passed`
- Related R1/R0/A1/A1-R/leakage pytest: `70 passed`
- Compileall: passed
- Project state/status: passed/VALID
- `git diff --check`: passed
- PyTorch/CUDA: available

R2 is complete. Stop for author review; outer confirmation was not started.
