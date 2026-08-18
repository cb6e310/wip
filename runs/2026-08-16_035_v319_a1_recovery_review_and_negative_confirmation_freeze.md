# Run 035 — run-034 author review and SPEC v3.19 negative-confirmation freeze

## Audited baseline

- Remote commit: `d10446537b3e6cb460abc652100a3978eabc0a3c` (`v3.18-A1-measurement-recovery`).
- Worktree was clean and equal to `origin/main` before this author-only update.
- Run 034 completed the exact 78-fit/78-V5 budget, revalidated 897/897 old V5 ledgers, retained 100% common rows and read zero outer/calibration values.
- The four formal SHA256 values reproduce exactly; the JSON subject summaries, bootstrap CIs, transfer losses, recovery deltas and `FAIL_A1R_RECOVERY` outcome were independently recomputed.
- Implementation review found no material split, frontend, train-only-normalization, sham, fit-accounting, V5, aggregation or selection defect. Minor presentation/implementation choices that do not alter the estimand were accepted without reopening the run.

## Scientific decision

`FAIL_A1R_RECOVERY` is admitted as a valid bounded failure. No A1-R frontend passed cross family detection plus recovery-delta acceptance; no candidate is selected for positive outer recovery, and no third frontend, threshold change or rerun is allowed.

The one informative secondary pattern is TSR `A1R_T8_FIXATION`: inner seen family detection passed, cross failed, and paired transfer loss had a strictly positive CI. This does not rescue cross-subject EEG evidence, but creates a testable transfer-collapse hypothesis.

To avoid reusing inner-development score observations, the confirmatory T8 panel is restricted to the six outer subject folds at outer text fold `t0`. Run 034 used only `outer_s0_t0.train_record_ids`; outer-t0 seen/cross score records are outside that development population. This is stricter and cheaper than running the inner-selected T8 diagnostic over all 30 outer cells.

## Frozen execution

- Primary: immutable raw `A1_BP_CONCAT`, NR + TSR, all 6×5 outer cells.
- Secondary: TSR `A1R_T8_FIXATION`, only six `outer_s*_t0` cells, with explicit zero-overlap reconstruction against run 034.
- Per cell: fit-only normalizer/support/vocabulary/ridge; one model scores seen and cross without refit.
- Exact budget: 60 H-only + 240 A1-arm + 24 T8-arm = 324 ridge fits and 324 unique passing V5 ledgers.
- Final statistics: paired subject-first 18-subject summaries, B=10000, frozen family/legacy/negative/transfer criteria and A-S1 Holm safety.
- Claims: no equivalence or proof of zero; T8 transfer collapse is not positive cross-subject recovery.

No outer EEG/label/metric, alignment, direct `u+`, EQ-ANMA, Gate, A3 or ROAMM value was read or produced in this freeze task.

## State transition

- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE`: `READY → DONE/PASS_A1_NEGATIVE_CONFIRMATION_FREEZE`.
- `S1_A1_NEGATIVE_CONFIRMATION`: `BLOCKED → READY`; sole recommended task.
- `S0_ZUCO2_NEGATIVE_PACKAGE_FREEZE`: added BLOCKED pending a valid outer outcome.
- ROAMM remains deferred until the complete ZuCo2 first-dataset package is frozen.

## Evidence

- `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_19_2026-08-16.md`
- `artifacts/a1_negative_confirmation_freeze.yaml`
- this run record
