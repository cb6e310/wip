# Current Handoff

## Completed R0 diagnosis

`R0_REAL_SHAM_RESCUE_FREEZE` completed with
`PASS_REAL_SHAM_RESCUE_FREEZE` on branch `research/real-sham-rescue`.

- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`.
- Existing A1 admission values reproduced across 2 tasks x 2 bases.
- New EEG fits: `0`.
- Outer-test/calibration reads: `0/0`.
- All 639 parent A1 admission V5 ledgers retained unique zero-read scope.
- Channel-block permutation remains visible as a topology sentinel.

The new semantic-sham estimates are NR raw `0.0053592`, NR latent
`0.0073520`, TSR raw `0.0176793`, and TSR latent `0.0029390`. These are pure
recalculations of existing artifacts, not real EEG incremental evidence.

## Parent state

The current repository does not yet contain a valid paper-level outer negative
confirmation. It contains a valid A1 admission failure, a valid A1-R recovery
failure, an immutable run-032 construct-validity audit, and a valid synthetic
EQ-ANMA method-boundary failure. The next author-approved question is whether
the negative contrast is partly caused by the measurement estimand rather than
by absence of all real EEG information.

## Why this branch exists

The admitted A1 pilot shows:

- raw `real - trial_shuffle`: NR `-0.0072`, TSR `+0.0293`, both CI lower bounds `<=0`;
- latent `real - trial_shuffle`: NR `+0.0040`, TSR `+0.0058`, both uncertain;
- raw `real - channel_block_permutation`: NR `-0.1338`, TSR `-0.1494`, both strongly negative;
- legacy raw `u_min`: NR `-0.7883`, TSR `-0.7476`;
- subject identity probe passes while semantic item probe fails;
- A1-R T8 detects signal for seen subjects in TSR but not for held-out subjects.

The most informative hypothesis is a combination of cross-subject geometry,
sentence-level temporal dilution, absolute-power nuisance and a potentially
non-exchangeable topology-destroying sham. This is a hypothesis, not an
outcome.

## Sole next action

Stop for author review. The only possible next task is the separately
authorized `R1_REAL_SHAM_INNER_DIAGNOSTIC`; it remains blocked until that
review.

Do not implement R1 feature repair or any alignment model in this task.

## Claim boundary

Any R0 result is `RESEARCH_DIAGNOSTIC_ONLY`. It cannot release Gate A/B,
alignment, direct `u+`, EQ-ANMA, A3 or ROAMM and cannot relabel old outcomes.
