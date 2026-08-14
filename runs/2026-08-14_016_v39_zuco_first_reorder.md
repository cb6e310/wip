# v3.9 ZuCo-First Execution Reorder

- Run ID: `2026-08-14_016_v39_zuco_first_reorder`
- Baseline reviewed: `502a92f5de1a984e999ea8692b59ad9fd9e6d8bd`
- Evidence scope: `AUTHOR_APPROVED_PROTOCOL_ORDERING_ONLY`
- Paper-level EEG outcomes read or produced: `none`
- Threshold, null, metric or fairness changes: `none`

## Decision

The author elected to finish and freeze the complete ZuCo 2.0 NR/TSR experiment before continuing the second dataset. SPEC v3.9 records this as an execution-order change, not removal of ROAMM and not an outcome-contingent dataset switch.

The new path is:

`ZuCo inner → candidates → A1 admission/leakage → Stage 1/Gate A → direct/EQ/Gate B → route lock → ZuCo main experiment freeze → ROAMM admission and frozen replication`.

## State changes

- Added SPEC v3.9 with D19/D20, the ZuCo-first freeze boundary and Appendix M.
- Removed `S0_ROAMM_ADMISSION` from the `S0_INNER_SPLIT` prerequisites.
- Scoped `S0_INNER_SPLIT`, `S0_CANDIDATES` and `S0_LEAKAGE_AUDIT` to ZuCo2 for the current phase.
- Set `S0_INNER_SPLIT=READY` and `recommended_next_task=S0_INNER_SPLIT`.
- Replaced the old ROAMM-admission blocker with `B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE`, which blocks only `S0_ROAMM_ADMISSION`.
- Preserved the run-015 `IN_PROGRESS_DOWNLOAD` / `experiment_ready=false` boundary and recorded seven required corrections before future resumption.

## Current claim boundary

No EEG metric, held-out result, Gate decision, route or paper conclusion was inspected or generated. ZuCo-first completion will not by itself authorize a cross-dataset claim; ROAMM remains mandatory after the frozen ZuCo milestone.

## Next task

Only `S0_INNER_SPLIT`: generate deterministic task-local inner folds for all 60 ZuCo2 outer cells (30 NR and 30 TSR), perform the fold-local J17 support trigger audit, validate outer-test isolation and hashes, then release `S0_CANDIDATES` if and only if all protocol assertions pass. SPEC v3.9 Appendix M.4 is the exact Codex contract.
