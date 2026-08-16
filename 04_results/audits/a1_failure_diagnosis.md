# A1 failure diagnosis

- Run: `2026-08-16_029_v315_a1_failure_diagnosis`
- Outcome: `INVALID_A1_FAILURE_DIAGNOSIS`
- New fits/V5: 58/58
- Outer-test/calibration reads: `0/0`
- Role: construct-validity positive controls only; not EEG evidence or paper performance.

| Task | A-A3 balanced accuracy | CI95 | null q95 | A-A3 | scorer logp gain CI95 | oracle macro-subject R@1 | scorer |
|---|---:|---:|---:|---|---:|---:|---|
| task1_nr | 1 | [1.0, 1.0] | 0.140881 | PASS | [4.609008696808964, 4.960515656219019] | 1 | FAIL |
| task2_tsr | 1 | [1.0, 1.0] | 0.159379 | PASS | [4.783933681018489, 4.903197441060533] | 1 | FAIL |

The admitted v3.14 `FAIL_A1_ADMISSION` is unchanged. The channel-sham pattern is descriptive only and no mechanism is claimed.
