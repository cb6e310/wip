# Run R008 — v4.1 main activation and author approval

Status: `DONE`

- Execution timestamp: `2026-08-24T20:22:11+08:00`
- Merge-base ancestor check: `PASS`
- Merge mode: `FAST_FORWARD`
- Source branch: `research/real-sham-r4-orthogonal-inner`
- Source commit: `e80862e943b9fbff7f5788dc109eefbf2c27a476`
- Target branch: `main`
- Main commit before merge: `86e4f370bab650ff73831627be102fc9a7ffe6a4`
- Main HEAD after fast-forward: `e80862e943b9fbff7f5788dc109eefbf2c27a476`
- Main activation documentation commit: `SELF` (the commit containing this record)
- Final local/remote main: the activation documentation commit; verified equal
  after the non-force push.

## Author approval

- Approval status: `APPROVED`
- Approval scope: `R6_AUTHOR_FREEZE_ONLY`
- R4 outer confirmation: `NOT_APPROVED`
- R6 experiment execution: `BLOCKED_UNTIL_NEW_FREEZE`
- R6 release: `AUTHOR_APPROVED_PENDING_NEW_FREEZE`
- Future-work branch: `main`

## Applied management files

- `AI_START_HERE.md`
- `PROJECT_STATE.yaml`
- `HANDOFF.md`
- `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_MAIN_APPROVED_2026-08-24.md`
- `runs/research/2026-08-24_008_v4_1_main_activation_and_author_approval.md`
- `TASKS.yaml`: unchanged

## Preservation and cleanup

- Local R4 branch handling: preserved unchanged as a historical audit line.
- Remote R0, R1, R2, R3, R4, and rescue branches: preserved unchanged.
- `branches_deleted=[]`.
- Transient removals: none.
- R0-R4 formal artifacts and their recorded SHA values: unchanged.
- R4 formal SHA recheck: `PASS`.
- Outer-test reads: `0`.
- Calibration reads: `0`.

## Validation

- `python scripts/check_project_state.py`: `PASS`.
- `python scripts/project_status.py`: `VALID`.
- `git diff --check`: `PASS`.
- Expected pre-commit working-tree changes only: `PASS`.
- `git branch --show-current`: `main`.
- Pre-documentation-commit `git rev-parse HEAD`:
  `e80862e943b9fbff7f5788dc109eefbf2c27a476`.
- Pre-push remote `main`:
  `86e4f370bab650ff73831627be102fc9a7ffe6a4`.

Next task: `R6_AUTHOR_FREEZE_ON_MAIN`.

No R6 experiment is released by this migration. A new R6 author freeze must be
created and committed on `main` before any R6 execution.
