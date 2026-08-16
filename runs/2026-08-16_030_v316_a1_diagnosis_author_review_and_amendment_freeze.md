# Run 2026-08-16_030_v316_a1_diagnosis_author_review_and_amendment_freeze

## Scope

Author review of pushed commit `ffd2369663eb7a0f069f75726b34a46b7e3808ad` and pre-run freeze of the minimum amendment. No new fit, outer-test value, negative-confirmation result, alignment, Gate, A3 or ROAMM task was executed in this review.

## Review result

- The old v3.14 evidence and code remain byte-identical; 639/639 old V5 ledgers revalidate.
- The v3.15 diagnosis produced exactly 58 new fits and 58 passing V5 ledgers with zero outer-test/calibration reads.
- Both A-A3 oracle controls pass perfectly. Both scorer controls pass every numerical condition: positive logp-gain CI and macro-subject R@1=1.0.
- The sole INVALID reason is contractual: `inner_s0_t0` is one of three subject folds and therefore has 5 validation subjects, while D42.3 also requires a 15-subject bootstrap.
- Focused 12/12, related 112/112 and full 213/213 server tests pass. Local code compilation, canonical JSON, deterministic gzip structure, project state and diff checks pass. No blocking implementation defect was found.

## Author decision

Do not relax 15 subjects to 5. Keep the completed `s0_t0` scorer fits immutable and add only H-only/oracle fits for `s1_t0` and `s2_t0` in both tasks: 8 new ridge fits total. The three subject sets are pairwise disjoint and their union is exactly the frozen 15 subjects per task. Combine subject-level summaries with equal subject weights and the unchanged bootstrap/R@1 thresholds.

This resolves an impossible conjunction in the authored v3.15 contract; it does not change an EEG result or positive-control threshold. The run-029 INVALID record remains immutable history.

## Prepared state

- governing SPEC v3.16;
- `S0_A1_FAILURE_DIAGNOSIS=READY` solely for the 8-fit amendment;
- `recommended_next_task=S0_A1_FAILURE_DIAGNOSIS`;
- negative-confirmation freeze/run, original EQ-ANMA chain and ROAMM remain blocked;
- no route migration or paper claim occurs before amendment PASS.
