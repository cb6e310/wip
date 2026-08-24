# AI start here — main branch, R4 history preserved, R6 author-approved

Target branch: `main`

R4 source merged by fast-forward:
`research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`

Future-work policy: `MAIN_ONLY_AFTER_R4_MERGE`

Current scientific state:

- Task: `R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC`
- Status: `DONE`
- Outcome: `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Outer/calibration reads: `0/0`

Author decision:

`APPROVED_TO_CREATE_R6_AUTHOR_FREEZE`

This approval releases only the creation of a new R6 author freeze on `main`.
It does not release R4 outer confirmation, calibration, EQ-ANMA execution,
Gate A/B, A3, ROAMM, or any held-out experiment.

Read in order:

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_25_2026-08-24.md`
5. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`
6. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_MAIN_APPROVED_2026-08-24.md`
7. `artifacts/real_sham_r4_freeze.yaml`
8. `artifacts/real_sham_r4_orthogonal_contract.yaml`
9. `04_results/diagnostics/real_sham_r4_orthogonal_inner.{json,md}`
10. `runs/research/2026-08-24_006_v325_real_sham_r4_orthogonal_freeze.md`
11. `runs/research/2026-08-24_007_v4_1_r4align_state_reconciliation.md`

Next task: `R6_AUTHOR_FREEZE_ON_MAIN`

Before any R6 experiment, create and commit a new author freeze on `main`
that explicitly records the base commit, data-consumption scope, estimand,
contracts, budget, and forbidden reads. Do not create another research branch
unless the author explicitly changes the main-only policy.

Historical R0–R4 branches remain read-only audit references.
