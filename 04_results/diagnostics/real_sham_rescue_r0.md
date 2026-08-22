# Real-vs-sham rescue R0 diagnostic

- Outcome: `PASS_REAL_SHAM_RESCUE_FREEZE`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Parent outcomes: immutable
- New EEG fits: `0`
- Outer-test/calibration reads: `0/0`
- Channel-block permutation: retained as topology sentinel

## Existing-artifact contrasts

| Task | Basis | delta_semantic | delta_legacy | delta_channel | old u_min |
|---|---|---:|---:|---:|---:|
| task1_nr | raw | 0.0053592006 | -0.0410273803 | -0.1338005421 | -0.7883169731 |
| task1_nr | token_local_frozen_initial_latent | 0.0073519506 | 0.0002205160 | -0.0140423532 | -0.3810253694 |
| task2_tsr | raw | 0.0176793216 | -0.0380118863 | -0.1493943020 | -0.7476340655 |
| task2_tsr | token_local_frozen_initial_latent | 0.0029390467 | -0.0077162410 | -0.0290268163 | -0.3809156500 |

The old `u_oof`, `u_min`, and all three single-sham contrasts are retained in the JSON with explicit reproduction checks. These are diagnostic recalculations, not real EEG incremental evidence.

## Claim boundary

R0 releases no alignment, direct u+, EQ-ANMA, Gate A, Gate B, A3, or ROAMM result. The parent admission, recovery, run-032, synthetic-method, and outer-confirmation states remain unchanged.

The only next step is author review followed, if separately authorized, by `R1_REAL_SHAM_INNER_DIAGNOSTIC`. R1 was not executed here.
