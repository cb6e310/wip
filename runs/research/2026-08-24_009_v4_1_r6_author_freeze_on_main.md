# Run R009 — v4.1 R6 author freeze on main

Status: `DONE`

- Execution timestamp: `2026-08-24T21:13:20+08:00`
- Target branch: `main`
- Committed base: `0a140bafabf9ec489547dda002f7613cafdfa4db`
- Freeze commit SHA: `SELF` (the commit containing this record; resolved by
  post-commit `git rev-parse HEAD`)
- Remote `main` after push: `SAME_AS_SELF` (verified by `git ls-remote`)
- Historical R4 source: `e80862e943b9fbff7f5788dc109eefbf2c27a476`
- Author approval: `APPROVED`
- Approval scope: `R6_AUTHOR_FREEZE_ONLY`
- R6 experiment release: `BLOCKED_UNTIL_IMPLEMENTATION`

## Applied files

- `AI_START_HERE.md`
- `PROJECT_STATE.yaml`
- `HANDOFF.md`
- `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6_EQALIGN_MSP_R6FREEZE_MAIN_2026-08-24.md`
- `artifacts/eqalign_r6_author_freeze.yaml`
- `runs/research/2026-08-24_009_v4_1_r6_author_freeze_on_main.md`
- `TASKS.yaml`: unchanged

## Bound hashes

- Governing SPEC SHA256:
  `0d520ce03959e5b733f44cfa00ae5f6bd4c4eddbb43f92ed2ca29f28df439e55`
- Final author-freeze artifact SHA256:
  `a48b26976344108b4cbdc0fb9264d28cab5a9eb893f2602ffca6254a720338b4`
- R0-R4 formal SHA values: unchanged.

## Cleanup and branch preservation

- Removed transient logs:
  - `.codex_eq_anma_preflight.log`
  - `.codex_eq_anma_formal_worker_0.log`
  - `.codex_eq_anma_formal_worker_1.log`
  - `.codex_stage1_a1r_v318_run.log`
  - `.codex_eq_anma_full_tests.log`
  - `.codex_eq_anma_formal_worker_2.log`
  - `.codex_eq_anma_aggregate.log`
  - `.codex_eq_anma_formal_worker_3.log`
- Removed compile-only caches:
  - `02_code/src/methods/__pycache__/`
  - `02_code/src/data/__pycache__/`
  - `02_code/scripts/__pycache__/`
- Preserved uncertain/history-bearing logs under `01_data_protocol/` and
  `runs/research/`.
- Temporary Codex worktrees removed: none; none existed.
- Protected local and remote main/R0-R4/rescue branches: preserved.
- `branches_deleted=[]`.

## Validation

- `python scripts/check_project_state.py`: `PASS`.
- `python scripts/project_status.py`: `VALID`.
- `git diff --check`: `PASS`.
- Required four-file `python -m compileall -q`: `PASS`.
- Pytest: not run in this step; package environment status remains
  `BLOCKED_ENV_NO_PYTEST`. No dependency was installed.
- `TASKS.yaml`: unchanged.
- R0-R4 formal SHA recheck: `PASS`.
- Real R6 runner: absent.
- Real EEG reads: `0`.
- Outer-test reads: `0`.
- Calibration reads: `0`.

Next task: `R6_IMPLEMENT_ARMS_AND_TESTS` on `main`.

No real R6 training or held-out scoring is released until implementation and
tests complete.
