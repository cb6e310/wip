# Run 2026-08-16_029_v315_a1_failure_diagnosis

## Scope

Executed only SPEC v3.15 D42 on ZuCo2 outer-train data. No full 6x5 negative confirmation, alignment, direct `u+`, EQ-ANMA, Stage 1, Gate, A3, ROAMM or second-dataset task was run.

## Frozen evidence revalidation

- All four admitted A1 artifact SHA256 values reproduced.
- The old gzip contained exactly 639 rows and 639 unique fit IDs; 639/639 real V5 ledgers revalidated with zero outer-test and calibration reads.
- The three admitted v3.14 implementation/test files remained byte-identical.

## New real positive controls

- Fits: 58 total = 54 fixed multinomial logistic + 4 fixed ridge.
- V5: 58/58 PASS; unique fit IDs: 58.
- Fit-time sum: 7.164272 seconds; maximum single fit: 0.453632 seconds.
- End-to-end runtime: 164.897 seconds.
- Outer-test/calibration reads: 0/0.

| Task | A-A3 BA | subject CI95 | within-subject null q95 | A-A3 | scorer logp gain | CI95 | scorer subjects | oracle macro-subject R@1 | scorer contract |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| NR | 1.0 | [1.0,1.0] | 0.140881204 | PASS | 4.78095450 | [4.60900870,4.96051566] | 5 | 1.0 | INVALID |
| TSR | 1.0 | [1.0,1.0] | 0.159379472 | PASS | 4.84339106 | [4.78393368,4.90319744] | 5 | 1.0 | INVALID |

Every numerical positive-control threshold passes. The overall outcome is nevertheless `INVALID_A1_FAILURE_DIAGNOSIS` because D42.3 freezes a 15-subject paired bootstrap while the sole registered `inner_s0_t0` validation-only scoring scope contains only 5 subjects per task. Satisfying 15 subjects would require an unapproved scope or fit-budget change.

## Formal artifact SHA256

- `artifacts/a1_failure_diagnosis_contract.yaml`: `1796f58bd7786a682f65f944e29b975b87289fab2e944730bfe9b25ad99d9b1b`
- `04_results/audits/a1_failure_diagnosis.json`: `56b3e6e42d8611072ecc62f10de60badf57bfc752954ba63ebe2941af6a9a38e`
- `04_results/audits/a1_failure_diagnosis.md`: `a3e1b735a5cfca01a320cdae5d8c92b7cc8c1f54d4af8e6be8b6b1e11e6797f6`
- `04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz`: `80cb11bc7ab12b59c00eb38c6cd03318f1ac2f347505e6940d8aeab5b434e6c4`

## State

The diagnosis remains not-DONE and is BLOCKED for author review. Route remains unchanged and unlocked, `recommended_next_task=null`, and both negative-confirmation tasks remain BLOCKED.

## Verification

- Focused failure-diagnosis tests: 12 passed, 0 skipped, 0 failed in 0.690 seconds.
- Related A1 admission/source/frontend, text, H, inner/joint split and leakage regressions: 112 passed, 0 skipped, 0 failed in 32.460 seconds.
- Complete unittest suite: 213 passed, 0 skipped, 0 failed in 62.332 seconds.
- Project state validator: PASS (`34 tasks / 17 done`); project status: stage BLOCKED, zero READY tasks, `recommended_next_task=null`.
- `git diff --check`: PASS.
