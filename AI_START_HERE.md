# AI start here — main branch, R6 inner-selection contract blocked

Target branch: `main`

Current verified remote base:
`main@309b70163707c145b9e92a38b41a3ff92cf0f510`

Current SPEC:
`guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6INNER_READY_MAIN_2026-08-25.md`

Future-work policy: `MAIN_ONLY_AFTER_R4_MERGE`

## Plain-language state

The old R1–R4 diagnostic line is historical and unchanged. The R6 author freeze,
synthetic arm/controller contracts, and the independent R6 split reconciliation
are complete. R6 now has 18 outer cells per task (`6×3`) and 9 task-global inner
cells per outer cell (`3×3`). No R6 training or metric has been produced.

The `R6_INNER_SELECTION` preflight is complete and blocked because the repository
does not contain a real R6 runner or hash-bound execution recipe. Before any
EEG/text read or training, a future author-approved task must supply
an author-frozen real alignment recipe and a real fit-only
`u_oof → 2PL → Fisher → h` OOF contract. Their concrete optimizer, batch,
steps/early-stop, probe folds/capacity and ledger schema are currently absent.
Synthetic smoke defaults are not valid substitutes. Current status is
`BLOCKED_R6_EXECUTION_CONTRACT_INCOMPLETE`; no metric was written.

## Read in order

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml` (historical validator task list; do not rewrite in this task)
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6INNER_READY_MAIN_2026-08-25.md`
5. `artifacts/eqalign_r6_inner_selection_contract.yaml`
6. `artifacts/eqalign_r6_split_contract.yaml`
7. `artifacts/eqalign_r6_author_freeze.yaml`
8. `artifacts/eqalign_r6_implementation_contract.yaml`

## Immutable split facts

- R6 outer: `01_data_protocol/splits/eqalign_r6_zuco_2_0_outer_folds.json`
  physical SHA256 `445e640239cff4cbbdb9fd0a81e6cdc8d9e0e1e1a698df4235b6382fb7637794`.
- R6 inner: `01_data_protocol/splits/eqalign_r6_zuco_2_0_inner_folds.json`
  physical SHA256 `1b609a7e4a62c66f8b1a2127a94ec4ee42793521d7accad40178eb5cde54b40d`.
- Old v3.13 6×5 outer/inner files remain byte-identical historical inputs and R6
  must never read them.

## Branch and cleanup policy

All future work is on `main`. The five R1–R4/rescue refs are read-only audit
history and must not be deleted. There are no transient remote branches in the
verified remote state. Only stale local worktrees created by the current Codex
session, `__pycache__`, `*.pyc`, `.pytest_cache`, and clearly labelled scratch
outputs may be removed; never delete tracked historical artifacts or run ledgers.

## If the execution gate passes

Run only inner selection: outer-train/inner-train fit, current inner-validation
selection, 3 main seeds, 4 EQ gamma values, 8 DIRECT variants, 3 shuffle
realizations and `DIRECT_MATCHED`. Keep `outer_test_reads=0` and
`calibration_reads=0`; do not classify a paper outcome. The locked pooled gamma,
DIRECT variant, recipe and inner deltas are the only scientific outputs.
