# AI start here — main branch, R6 split reconciliation complete

Target branch: `main`

Current remote base:
`main@a4a3d3c007639029c8d57d4b1700cdd00587e307`

R6 arm/contract implementation parent:
`main@125d72c9aad1dd2d3777d695123f17dc97138268`

Historical R4 source already fast-forwarded:
`research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`

Future-work policy: `MAIN_ONLY_AFTER_R4_MERGE`

## Current scientific state

- Historical task: `R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC`
- Historical status/outcome: `DONE` / `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Historical outer/calibration reads: `0/0`
- Current R6 implementation status: `DONE_SYNTHETIC_CONTRACT_SURFACE`
- Real R6 runner/align/training/retrieval modules: absent
- R6 frozen split requirement: outer `6x3` (18 cells/task), inner task-global `3x3`
- Existing old split artifact: `6x5` (30 cells/task), immutable historical input

## Author decision and current action

Author approval: `APPROVED_TO_CREATE_R6_AUTHOR_FREEZE`

Completed task: `R6_AUTHOR_FREEZE_ON_MAIN`

Freeze status: `R6_AUTHOR_FREEZE_COMMITTED`

Completed task: `R6_IMPLEMENT_ARMS_AND_TESTS`

Implementation package status: `DONE`

The `R6_SPLIT_RECONCILIATION` task is complete. Independent namespaced R6 6x3
outer and fixed 3x3 inner artifacts passed deterministic rebuild, isolation,
hash and support-audit checks without changing the old 6x5 files. The only
next task is `R6_INNER_SELECTION`; calibration, outer work, Gate A/B, A3,
ROAMM, V-A/V-B and held-out experiments remain blocked.

## Read in order

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6SPLIT_RECONCILE_READY_MAIN_2026-08-24.md`
5. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_MAIN_APPROVED_2026-08-24.md`
6. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`
7. `artifacts/eqalign_r6_author_freeze.yaml`
8. `artifacts/eqalign_r6_implementation_contract.yaml`
9. `artifacts/real_sham_r4_freeze.yaml`
10. `artifacts/real_sham_r4_orthogonal_contract.yaml`
11. `04_results/diagnostics/real_sham_r4_orthogonal_inner.{json,md}`
12. `runs/research/2026-08-24_008_v4_1_main_activation_and_author_approval.md`
13. `runs/research/2026-08-24_009_v4_1_r6_author_freeze_on_main.md`
14. `runs/research/2026-08-24_010_v4_1_r6_implementation_readiness.md`
15. `runs/research/2026-08-24_011_v4_1_r6_split_reconciliation_readiness.md`

## Acceptance and next task

The freeze, implementation, and split reconciliation are committed on `main`.
The old
`01_data_protocol/splits/zuco_2_0_{outer,inner}_folds.json` files are v3.13 6x5
artifacts remain byte-identical. R6 now has namespaced 6x3/3x3 artifacts with
bound hashes. The next independent task is `R6_INNER_SELECTION`. No EEG
value reads, text encoder, training, retrieval metric, outer/calibration read,
Gate, A3, or ROAMM is allowed in this task.

Historical R0–R4 branches remain read-only audit references. `TASKS.yaml` is
unchanged by this protocol-only freeze.
