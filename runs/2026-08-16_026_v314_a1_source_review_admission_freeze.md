# Run 2026-08-16_026: review A1 source admission and freeze A1 diagnostic pilot

## Scope

Independently reviewed remote commit `6cffbb68477d92463565c65024a164a40e68e840`, admitted its `S0_A1_SOURCE_ADMISSION` result without rework, and froze the executable v3.14 contract for the next and only task `S0_A1_ADMISSION`. No EEG model/probe was trained, no A-A1–A-A4 outcome was read, and no unit cost, Stage 1, Gate, route, main experiment, A3 or ROAMM work was run.

## Source-admission review

- Remote HEAD and parent were confirmed as `6cffbb6` / `d9dfe51`; worktree was clean before this review overlay.
- Project validator passed at 31 tasks / 17 done; `S0_A1_ADMISSION` was the sole READY/recommended task.
- Formal SHA256 values independently reproduced: source contract `bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c`; deterministic exclusion ledger `250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c`; source audit `07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f`.
- The audit contains all 36 summary inventory rows, 252 preprocessing metadata inputs, one 105-label tuple, 72 exact source links and 214,496 unique explicit exclusions. The gzip ledger decompresses cleanly and has no duplicate rows.
- Strict finite rejection replaces the previous 95%-finite plus imputation path. The analysis-spectrum phase routine preserves magnitude and does not inverse-transform or apply a second Hann.
- The 72 source links compare the first `min(20,T)` sample rows over all 105 columns. This supports order/scale binding together with the complete release metadata evidence, but “exact slice” must not be expanded to an entire-array equality claim. Admitted as a nonblocking wording correction.
- The freeze file references a debug self-check path ignored by the repository. Existing implementation/config hashes, server test record and run evidence make this a nonblocking provenance note.
- Independent local import of torch-dependent tests was unavailable because torch is not installed in the review environment. Source syntax, state, artifact structures, hashes and the server-recorded focused 68/68, full 180/180 and self-check 8/8 were sufficient for admission; no code defect was inferred from the environment gap.

## Author-level v3.14 decisions

1. A1 admission is a two-panel diagnostic pilot, one pre-outcome canonical outer cell per task (`outer_s0_t0`), all nine admitted inner cells, and three seeds. NR/TSR remain separate.
2. The admission verdict uses released word-aligned content-word observations. Raw is the fold-normalized current-word 840D feature; latent is the same word passed as a length-one sequence through the seed-bound frozen initial A1 encoder. This removes the unresolved permutation-invariant raw pooling ambiguity and gives the three shams an observable action at the same semantic unit.
3. A-A1 uses a fixed ridge-to-frozen-item-embedding probe with no hyperparameter tuning. The three strong shams are trial shuffle, within-trial Sattolo unit assignment and 105-channel-block Sattolo permutation. Phase remains diagnostic only.
4. A-A2 uses material-group CV for 15-way subject identity. A-A3 uses fold-local K=8 MiniLM item clusters. A-A4 is a paired subject-level latent-minus-raw audit with a higher-priority raw-pass/latent-fail CO-N1 rule.
5. The fixed-window source/extraction path stays admitted but is not assigned arbitrarily to word targets in Stage 0. Its required outcome sensitivity remains later Stage-1/T4 and main/T6 work.
6. A single real preflight checks contract/runtime only. It cannot change the frozen design; >300 seconds per fit, OOM, V5 failure or <50% four-arm common support blocks.
7. Only `PASS_A1_ADMISSION_BOTH_TASKS` or the prespecified nonnegative-one-task `PASS_LIMITED_A1_ADMISSION_ONE_TASK` releases unit-cost measurement. No A1 pilot outcome is a Gate decision.

## State

`S0_A1_SOURCE_ADMISSION` remains DONE. `S0_A1_ADMISSION` remains the sole READY/recommended task under SPEC v3.14. `S0_ALIGN_UNIT_COST`, Stage 1, Gates, route/main experiment and ROAMM remain blocked/deferred.
