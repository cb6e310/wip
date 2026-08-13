# Run 2026-08-13_009: State Reconciliation

## Scope

Reconcile project-memory records after the completed data-card and A3 engineering-preparation runs. This run changes governance records only; it does not change scientific specifications, thresholds, folds, seeds, candidates, nulls, models, data, or experiment results.

## Changes

- Replaced stale `B_TMNRED_DATA_CARD_AUDIT`, which incorrectly blocked a completed task, with `B_TMNRED_EXPERIMENT_PROTOCOL` targeting unresolved downstream protocol work.
- Promoted the already documented ZuCo2 reference-exclusion and stimulus-identity-join issues to active top-level blockers.
- Set `last_completed_task` to the latest completed task listed by `TASKS.yaml` and kept `S0_H_DEFINITION` as the recommended next task.
- Merged completed ZuCo2/TMNRED structural data-preparation evidence with the A3 engineering-preparation status in `HANDOFF.md`.
- Corrected the LaBraM checkpoint SHA256 typo in the A3 run note and Handoff to the digest calculated from the vendored checkpoint.

## Evidence boundary

- ZuCo2 and TMNRED data cards are structurally complete but remain `experiment_ready=false`.
- A3 architecture/checkpoint/raw-order/runtime synthetic checks pass, but CO-N7 contamination exclusion, rights, approved semantic channel mapping, and real extraction remain blocked.
- A1 frontend remains an engineering-contract completion, not real-data admission.

## Verification

- Project state: `PROJECT STATE VALID | tasks=25 | done=6`.
- Project snapshot: Stage 0 `IN_PROGRESS`, route unlocked, both structural data-card tasks remain `DONE`, and the reconciled blockers are active.
- Focused tests: A3 contract 6/6 PASS, ZuCo2 loader 7/7 PASS, TMNRED data preparation 5/5 PASS.
- Checkpoint digest: 96,612,769 bytes, SHA256 `7c50583826afac76c4ab18f43d958df40496c8229accc09ed6a227c9bb57c37c`; Handoff, A3 run note, audit and feasibility artifact agree.
- Recommended next task remains `S0_H_DEFINITION`; Gate A/B, T6/K7, route lock and paper-level experiments remain prohibited.
