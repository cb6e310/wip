# AI start here — main branch, R6 author freeze committed

Target branch: `main`

Current remote baseline:
`origin/main@0a140bafabf9ec489547dda002f7613cafdfa4db`

Historical R4 source already fast-forwarded:
`research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`

Future-work policy: `MAIN_ONLY_AFTER_R4_MERGE`

## Current scientific state

- Historical task: `R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC`
- Historical status/outcome: `DONE` / `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Historical outer/calibration reads: `0/0`
- Current R6 implementation readiness: `SYNTHETIC_SURFACE_ONLY`
- Real R6 runner/align/training/retrieval modules: absent

## Author decision and current action

Author approval: `APPROVED_TO_CREATE_R6_AUTHOR_FREEZE`

Completed task: `R6_AUTHOR_FREEZE_ON_MAIN`

Freeze status: `R6_AUTHOR_FREEZE_COMMITTED`

This package freezes the R6 protocol only. It does not release R4 outer
confirmation, calibration, EQ-ANMA training, Gate A/B, A3, ROAMM, V-A/V-B,
or any held-out experiment. Do not run a real R6 experiment while applying it.

## Read in order

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R6FREEZE_MAIN_2026-08-24.md`
5. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_MAIN_APPROVED_2026-08-24.md`
6. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`
7. `artifacts/eqalign_r6_author_freeze.yaml`
8. `artifacts/real_sham_r4_freeze.yaml`
9. `artifacts/real_sham_r4_orthogonal_contract.yaml`
10. `04_results/diagnostics/real_sham_r4_orthogonal_inner.{json,md}`
11. `runs/research/2026-08-24_008_v4_1_main_activation_and_author_approval.md`
12. `runs/research/2026-08-24_009_v4_1_r6_author_freeze_on_main.md`

## Acceptance and next task

The freeze is committed on `main` with its SPEC/artifact SHA bound. The only
next implementation task is `R6_IMPLEMENT_ARMS_AND_TESTS`, still on `main`;
no research branch should be created.

Historical R0–R4 branches remain read-only audit references. `TASKS.yaml` is
unchanged by this protocol-only freeze.
