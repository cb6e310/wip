# Run 033 — v3.18 run-032 author review and A1-R freeze

## Scope

Author-level review of pushed commit `6dadf3290e38213b33074eeeb61642966db0e876` and pre-run freeze of a bounded A1-R recovery audit. No EEG fit, outer-test value, recovery result, alignment, Gate, A3 or ROAMM task was executed in this review.

## Audit result

- The implementation and formal evidence match the v3.17 budget: 8 D49 plus 192 D50 ridge fits, 200 unique V5 ledgers, 697 old ledgers revalidated and zero outer/calibration reads.
- Both 15-subject oracle controls pass strongly.
- Both injection panels detect the family at alpha 0.01 and legacy at alpha 0.03; alpha 10 passes both.
- Both curves rise strictly through alpha 1 and then saturate/decline slightly. The full-grid rho 0.833333 is below the frozen 0.90 threshold, so `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT` remains immutable.
- The rho failure does not show that the downstream path cannot detect signal. It shows the v3.17 monotonicity condition also measured behavior after probe saturation. This post-run interpretation is logged as a deviation and is not used to relabel run 032.

## Author decision

Release one independent inner-only recovery audit. It pairs matched 10-subject training fits with seen-subject held-text and held-subject+held-text scoring, and tests exactly two mechanism-prior candidates:

1. train-only scale-equivariant log bandpower on the old concatenated-fixation PSD;
2. signed eight-bin fixation-relative time features that preserve temporal morphology.

The old A1 is rerun only as a paired baseline on the same common observations. The run is exactly 78 ridge fits, uses no outer test or test calibration, and pre-freezes candidate admission/selection before any recovery outcome.

## Prepared state

- governing SPEC v3.18;
- `S0_A1_MEASUREMENT_RECOVERY_FREEZE=DONE/PASS_A1R_RECOVERY_FREEZE`;
- `S1_A1_MEASUREMENT_RECOVERY=READY` and sole recommended task;
- route direction `MEASUREMENT-RECOVERY`, unlocked;
- run-032 INVALID, v3.14 FAIL and every old formal artifact remain unchanged;
- outer confirmation, negative confirmation and the original EQ-ANMA chain remain blocked.
