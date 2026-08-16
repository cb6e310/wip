# Run 2026-08-16_031_v317_external_advice_review_and_measurement_validity_freeze

## Scope

Author review of the existing A1 admission/diagnosis evidence and the attached external recovery proposal. This run freezes a bounded next audit only. It executes no fit, reads no outer-test/calibration outcome, and does not run a recovery frontend, negative-confirmation panel, alignment, Gate, A3 or ROAMM task.

## Evidence-backed decision

- The v3.14 `FAIL_A1_ADMISSION` remains immutable and valid for the exact frozen A1 contract, but it is not a dataset-wide statement that EEG has no value.
- The v3.15 diagnosis is execution-valid and numerically passes all controls; its historical INVALID is solely the authored 5-versus-15-subject contradiction.
- The pointwise maximum in `u_min` creates a large max-selection penalty, while the winning channel sham can be both a matched null and an accidental regularizer. Neither fact alone identifies a biological or implementation mechanism.
- Strong A-A2 with failed A-A1/A-A3 is the previously frozen identity-dominant backcheck signature. A full negative outer panel is therefore premature until the downstream A1 measurement path has a frozen detectability curve.
- The external proposal's graded signal injection is adopted in a stricter, leakage-safe form. Its NaN-imputation and 128-to-105-map concerns are rejected for admitted A1 because strict finiteness and exact ordered 105-channel source identity already passed. Sham-above-chance and significant-negative observations are not treated as automatic invalidity.

## Frozen next task

`S0_A1_FAILURE_DIAGNOSIS` remains the sole READY task and now completes one conditional 200-fit measurement-validity run:

1. eight ridge fits complete the unchanged oracle scorer positive control across all 15 subjects;
2. only after that passes, 192 ridge fits run the frozen eight-alpha semantic-injection curve across NR/TSR, three disjoint t0 subject folds and four A1 arms;
3. family-mean detectability and legacy pointwise-max detectability are reported separately;
4. injected data are construct-validity evidence only and can never enter an EEG result or Gate.

On PASS, the next author task is only `S0_A1_MEASUREMENT_RECOVERY_FREEZE`; it will later freeze a seen-subject versus subject-heldout audit and at most two mechanism-motivated A1-R candidates. Negative confirmation remains blocked. On INVALID, execution stops for author review without expanding alpha, seed, fold, probe or sham budgets.

## Prepared state

- governing SPEC v3.17;
- baseline remains `origin/main=ffd2369663eb7a0f069f75726b34a46b7e3808ad`;
- `S0_A1_FAILURE_DIAGNOSIS=READY` and is the sole recommended task;
- no paper claim, route lock or old outcome is changed before execution;
- all earlier admitted and historical artifacts remain immutable.
