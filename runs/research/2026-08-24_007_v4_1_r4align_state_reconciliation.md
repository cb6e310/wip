# Run R007 — v4.1-R4ALIGN state reconciliation

- Time: `2026-08-24T10:53:47+00:00`
- Task: `R4_STATE_RECONCILIATION`
- Branch: `research/real-sham-r4-orthogonal-inner`
- HEAD: `954cecd5d8885bb274dd4cde97db6255bd9cf54d`
- Completion outcome: `ALIGNED_R4_BRANCH_LOCAL`

## Entry-point reconciliation

- Before: `AI_START_HERE.md` pointed to the stale v3.23/R2 branch-local overlay.
- After: `AI_START_HERE.md` points to the v3.25/R4 branch-local overlay and the
  active v4.1-R4ALIGN protocol.
- Active protocol:
  `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`
- `PROJECT_STATE.yaml` preserves the existing parent/branch spec, base commit,
  R0-R4 outcomes, execution counts, formal hashes, and current scientific task.
- `TASKS.yaml` is unchanged.
- Changed files:
  - `AI_START_HERE.md`
  - `PROJECT_STATE.yaml`
  - `HANDOFF.md`
  - `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R4ALIGNED_2026-08-24.md`
  - `runs/research/2026-08-24_007_v4_1_r4align_state_reconciliation.md`

## Preserved lineage

- Protected local branches: `main`, `research/real-sham-rescue`,
  `research/real-sham-r1-inner`, `research/real-sham-r2-geometry-inner`,
  `research/real-sham-r3-subject-balanced`,
  `research/real-sham-r4-orthogonal-inner`.
- All corresponding `origin/*` remote-tracking branches are preserved.
- R0-R4 guides, freezes, contracts, diagnostics, ledgers, and run records are
  unchanged.
- `branches_deleted=[]`.

## Cleanup inventory

- Pre-cleanup Git status: clean.
- Worktrees: `/home/song/projects/trust_align  954cecd [research/real-sham-r4-orthogonal-inner]`.
- Removed transient paths:
  - `01_data_protocol/datasets/zuco_2.0/scripts/python_reader/__pycache__/`
  - `02_code/src/methods/__pycache__/`
  - `02_code/src/backbones/__pycache__/`
  - `02_code/src/data/__pycache__/`
  - `02_code/src/protocol/__pycache__/`
  - `02_code/src/text/__pycache__/`
  - `02_code/scripts/__pycache__/`
  - `02_code/tests/__pycache__/`
  - `02_code/vendor/LaBraM/__pycache__/`
  - `scripts/__pycache__/`
  - `.pytest_cache/`
- `.venv/` dependency caches were preserved as environment content.
- Post-cleanup transient scan outside `.venv/`: empty.
- Post-cleanup Git status contains only the five expected reconciliation files.

## Validation

- `python scripts/check_project_state.py`: PASS.
- `python scripts/project_status.py`: VALID.
- `git diff --check`: PASS.
- Branch and HEAD recheck: PASS.
- R4 formal SHA recheck: unchanged.
- Outer-test reads: `0`.
- Calibration reads: `0`.

Next task: `AUTHOR_REVIEW_ONLY`. This documentation reconciliation does not
release R6 or any downstream research task.
