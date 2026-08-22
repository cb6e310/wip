# Run R002 - v3.21 real-vs-sham rescue R0

## Outcome

- Task: `R0_REAL_SHAM_RESCUE_FREEZE`
- Outcome: `PASS_REAL_SHAM_RESCUE_FREEZE`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Branch: `research/real-sham-rescue`
- Base: `86e4f370bab650ff73831627be102fc9a7ffe6a4`
- New EEG fits: `0`
- Outer-test/calibration reads: `0/0`
- Parent outcomes: immutable

R0 only read admitted aggregate A1 artifacts and the 639-row parent admission
V5 ledger. It did not load EEG, labels, feature caches, model weights, outer
metrics, or calibration data.

## Reproduction and diagnostics

Old `u_oof`, `u_min`, and all three single-sham contrasts reproduced for both
tasks and both inherited bases. The channel-block contrast was retained as a
topology sentinel.

| Task | Basis | delta_semantic | delta_legacy | delta_channel | old u_min |
|---|---|---:|---:|---:|---:|
| task1_nr | raw | 0.0053592006 | -0.0410273803 | -0.1338005421 | -0.7883169731 |
| task1_nr | token_local_frozen_initial_latent | 0.0073519506 | 0.0002205160 | -0.0140423532 | -0.3810253694 |
| task2_tsr | raw | 0.0176793216 | -0.0380118863 | -0.1493943020 | -0.7476340655 |
| task2_tsr | token_local_frozen_initial_latent | 0.0029390467 | -0.0077162410 | -0.0290268163 | -0.3809156500 |

These values do not establish real EEG incremental evidence and do not modify
the parent admission, recovery, run-032, synthetic-method, or outer-confirmation
outcomes.

## Verification

- Focused: `6 passed` in `02_code/tests/test_real_sham_rescue.py`.
- Related: `55 passed` in the frozen A1 admission, A1 recovery, and leakage suites.
- Compile: the R0 module and runner compiled successfully.
- State validator: `VALID`.
- Project status: branch-local snapshot `VALID`.
- `git diff --check`: passed.
- Parent formal artifacts: byte hashes unchanged.

Formal SHA256:

- contract: `89f9bc468f5bea0bafe127baa1e0a96ceb5ff1c9327aba89e3445d86ed683055`
- JSON: `70eb78aaa7de232d908d62e610c916a45035c8586f23909879a162c0712a3c5c`
- Markdown: `0126550bef4e4220327ed93aa811ade6c7d2170e483dd975d39fa80066037955`
- gzip ledger: `1739ebc0e8b4a9b39887041a3907208a13be98fd4a619acd340e5fc955345ec1`

## Claim boundary

R0 releases no alignment, direct u+, EQ-ANMA, Gate A, Gate B, A3, or ROAMM
result. The only next step is author review and, only after separate
authorization, `R1_REAL_SHAM_INNER_DIAGNOSTIC`. R1 was not executed.
