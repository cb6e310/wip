# R4 author handoff — orthogonal conditional increment freeze

R3 completed at commit fbc54c7b90ffc1bbc07b55ffc3123d0421779104
with FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC. Its contract and output
hashes were independently reproduced. It completed 60/60 ridge/V5 operations,
read outer/calibration data 0/0 times, had no scope violations, and left all
earlier outcomes immutable.

The P1 subject-item mean reduced each fit cell from 6,053–8,624 observations to
1,011–1,346 groups. Task1 cross semantic contrast changed from +0.0389076 to
-0.127937; task2 changed from +0.0182842 to -0.0404971. Simple equal-group
training therefore did not repair transfer and materially reduced effective
training information.

R4 tests a different mechanism. The inherited joint ridge estimates H and EEG
effects together in a high-dimensional model, although the scientific target is
the EEG contribution conditional on H. R1's Y1 is not an orthogonal estimator:
it builds one canonical item residual vocabulary, keeps H inside the EEG probe,
and never residualizes EEG against H.

R4 uses source-subject-block cross-fitting to compute out-of-fold residuals
Y0 - mY(H) and X_arm - mX_arm(H), fits each arm's residual EEG probe on those
residuals, and scores unseen rows as
mY_full(H) + beta_arm(X_arm - mX_arm_full(H)). Real and every sham receive
the same algorithm, capacity, folds, rows, alpha, normalizer, and scoring rule.

This remains RESEARCH_DIAGNOSTIC_ONLY. Even a pass only releases author
review for a separately frozen outer step. R4 itself must not read outer-test or
calibration data and must not run direct u+, EQ-ANMA, A3, ROAMM, or a Gate.

R4 completed as `FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC`. C1 did not pass either
task: task1 cross semantic delta was +0.0388348 (CI95 -0.0465514 to
+0.122657, 9/15 positive) with paired recovery -0.0000728 (CI95 -0.0133054
to +0.0126437, 7/15 positive); task2 cross semantic delta was +0.0152228
(CI95 -0.0478296 to +0.0801269, 9/15 positive) with paired recovery
-0.00306141 (CI95 -0.0125178 to +0.00810636, 3/15 positive).

The run completed exactly 234 unique ridge operations with 54 final-scoring
V5 ledgers and 180 nuisance ledgers. Held-out nuisance overlap, fallback,
seen/cross nuisance reads, and outer/calibration reads were all zero. P0
reproduced R3/P0 with maximum subject-level absolute error 0.0. Parent/R0-R3
hashes remained unchanged and scope violations were empty. Stop at author
review; no downstream task is released automatically.

## R4 state reconciliation

`R4_STATE_RECONCILIATION` aligned the active protocol reference and project
entry point to the R4 HEAD
`954cecd5d8885bb274dd4cde97db6255bd9cf54d` using the v4.1-R4ALIGN protocol.
All R0-R4 formal artifacts, outcomes, hashes, and read counters remain
unchanged. The next step remains `AUTHOR_REVIEW_ONLY`. An R6 author freeze may
be created from this R4 HEAD only after explicit author approval; this
reconciliation does not release R6 or any downstream research task.

## Main activation and author approval (completed fast-forward)

The author approved and Codex fast-forwarded the verified R4 branch
`research/real-sham-r4-orthogonal-inner@e80862e943b9fbff7f5788dc109eefbf2c27a476`
into `main`. The merge is safe only after confirming that `main` is an ancestor
of the R4 commit; no merge commit, rebase, reset, or force update is allowed.

After the fast-forward, `main` is the only future working branch. The R0–R4
branches remain read-only historical audit references. The approval releases
only `R6_AUTHOR_FREEZE_ON_MAIN`; it does not release R4 outer confirmation,
calibration, EQ-ANMA, Gate A/B, A3, ROAMM, or any held-out experiment.

The next task is to create a new R6 author freeze on `main`. No R6 experiment
may start before that freeze records its base commit, estimand, data-consumption
scope, contracts, budget, and forbidden reads.

## R6 author freeze committed on main

The freeze was based on `main@0a140bafabf9ec489547dda002f7613cafdfa4db` and is now
committed at `main@125d72c9aad1dd2d3777d695123f17dc97138268`.
The author approved creation of the R6 freeze, and this package records that
protocol-only freeze as `R6_AUTHOR_FREEZE_COMMITTED`. The R4 outcome and every
R0–R4 formal hash remain immutable; `TASKS.yaml` remains unchanged.

Repository inspection found only synthetic R6 surfaces at this point:
`02_code/src/methods/eq_anma.py`, `02_code/src/methods/direct_u_plus.py`, the
synthetic benchmark and tests are present, while a real R6 runner and the
`src/align`, `src/training`, and `src/retrieval` packages are absent. The
freeze therefore has no real EEG reads, no outer/calibration reads, and no
metrics. `compileall` is the available code check; pytest is blocked by the
runtime missing the `pytest` module and must not be treated as a code failure.

The SPEC and freeze artifact SHA are bound on `main`; experiment execution
remains blocked until implementation. The only next task is
`R6_IMPLEMENT_ARMS_AND_TESTS` on `main`; do not create a research branch and
do not run held-out work before implementation and tests pass.

## R6 implementation readiness review

Remote inspection after the freeze commit confirms that `main` is clean at
`125d72c9aad1dd2d3777d695123f17dc97138268`, while the historical R4 branch
remains at `e80862e943b9fbff7f5788dc109eefbf2c27a476`. The freeze artifact,
SPEC hash, R0–R4 formal hashes, `TASKS.yaml`, and all read counters are intact.

The current code has the legacy/synthetic EQ-ANMA and DIRECT weighting surfaces,
but no R6 arm adapter, bounded `clip(1+gamma*h)` controller, fit-only scope
guard, compute-matching ledger, or R6 contract self-check. The next task is
therefore deliberately limited to those protocol surfaces and T-01…T-09
synthetic/adversarial tests. It must not add a real runner, real data loader,
training loop, retrieval loop, outer/calibration output, or held-out metric.

Codex completed `R6_IMPLEMENT_ARMS_AND_TESTS` as protocol-only Python surfaces.
The standalone synthetic selfcheck and pytest suite both pass all T-01…T-09
contracts, including adversarial fit-ID, shuffle-axis, and feature-injection
checks. No real data loader, runner, training, retrieval, outer/calibration
output, or held-out metric was added or used. The only next task is
`R6_INNER_SELECTION`; real EEG, outer, calibration, Gate, A3, ROAMM, and
paper-level operations remain blocked.
