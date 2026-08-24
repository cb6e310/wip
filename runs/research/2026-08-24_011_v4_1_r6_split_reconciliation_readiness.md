# Run R011 — v4.1 R6 split reconciliation readiness review

Status: `DONE`

- Research timestamp: `2026-08-24T23:10:00+08:00`
- Remote repository: `https://github.com/cb6e310/wip.git`
- Target branch: `main`
- Verified remote `main`: `a4a3d3c007639029c8d57d4b1700cdd00587e307`
- Parent R6 implementation commit: `125d72c9aad1dd2d3777d695123f17dc97138268`
- Governing SPEC SHA256: `2d2b584766ab99f4b50dd48dfcb20e0154433081f063cda38fc6833b224850af`
- Split contract: `artifacts/eqalign_r6_split_contract.yaml`
- Completion commit: `SELF`
- Remote `main` after push: `SAME_AS_SELF`

## Remote inspection

The remote `main` implementation commit completed the R6 arm/controller/scope/
ledger synthetic contract surface. The recorded remote validations are PASS for
T-01…T-09 and the standalone self-check; the real R6 runner, training loop and
retrieval loop are still absent.

The author freeze requires `K_S_out=6`, `K_T_out=3` (18 outer cells per task),
with a task-global `3x3` inner split per outer cell. The existing tracked outer
artifact is v3.13 `6x5` (30 cells/task), SHA256
`20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6`; the paired
inner artifact is tied to those 30 cells, SHA256
`0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7`. This is a
real state/spec conflict, not a cosmetic filename mismatch.

## Decision

The current task is `R6_SPLIT_RECONCILIATION`, not `R6_INNER_SELECTION` yet.
Codex must create independent namespaced R6 6x3 outer and per-cell 3x3 inner
artifacts, validate deterministic construction/isolation, and bind their hashes.
The old 6x5 artifacts, `TASKS.yaml`, R0–R4 formal artifacts and existing run
ledgers remain immutable. Only after the split contract passes may the state move
to `R6_INNER_SELECTION`.

## Scope boundary

- Allowed: source-slot join, summary sequence, numeric leaf schema/validity and
  semantic identity ledgers needed to construct folds.
- Forbidden: EEG numeric feature values, text encoder, training, retrieval or
  R@1/Δ metrics, outer-test/calibration rows, gamma selection, DIRECT selection,
  Gate/A3/ROAMM, or a new research branch.
- Required read counters: `r6_real_eeg_value_reads=0`, `outer_test_reads=0`,
  `calibration_reads=0`.

## Branch/cleanup observation

Remote branches are `main` plus the five historical R1–R4/rescue audit refs.
There are no transient remote branches to delete. Future work remains on
`main`; cleanup may remove only transient worktrees/caches/pyc/pytest scratch,
never the historical audit branches or immutable artifacts.

## Next state

`R6_SPLIT_RECONCILIATION` → (if all mechanical assertions pass)
`R6_INNER_SELECTION`. No scientific metric or paper-level claim is produced by
this readiness review.

## Codex completion record

- Outer shape: `6x3`, exactly `18` cells per task.
- Inner shape: fixed `3x3`, exactly `9` cells per outer cell.
- Forward/reverse canonical-byte identity: `PASS`.
- Standalone full rebuild selfcheck: `PASS`.
- Pytest: `PASS (5 passed)`.
- Old 6x5 outer/inner hashes unchanged: `PASS`.
- `TASKS.yaml` and R0-R4 protected history unchanged: `PASS`.
- Read counters (`r6_real_eeg_value_reads/outer_test_reads/calibration_reads`): `0/0/0`.
- Branches deleted: `[]`.
- Transient cleanup: `__pycache__/`, `*.pyc`, `.pytest_cache/`.

Output hashes:

- Outer physical/canonical: `445e640239cff4cbbdb9fd0a81e6cdc8d9e0e1e1a698df4235b6382fb7637794` / `b5664601b34eded841fe87ff04619436115f97c2dcd7e283cb9d6d18630bcc6f`.
- Inner physical/canonical: `1b609a7e4a62c66f8b1a2127a94ec4ee42793521d7accad40178eb5cde54b40d` / `472e0ad970e02d41edfdf2cdbb12147a4264aa980c5ac4241f0bf0032b629034`.
- Support audit physical/canonical: `055be044f222ae38667d5dd3da3828f1901a890f1448d8215c067c960d105d57` / `f6d1a8f5d85f1a091c45b815f4f3edfea16d8685eebd6aa0a556ca930552d374`.
- Construction source manifest: `8ddfa1999748b50aabefe21a04f695961efc333f401df44e2a804fb6578160c5`.
- Final split contract SHA256: `06154b6de9283bc23b3ddecfb4ddd8eebf6430cbd757111723ef93f8676585a3`.

The only next task is `R6_INNER_SELECTION`; it was not started in this commit.
