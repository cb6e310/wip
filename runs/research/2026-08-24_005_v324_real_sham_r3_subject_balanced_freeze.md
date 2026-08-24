# Run R005 — v3.24 R3 subject-balanced inner diagnostic freeze

## Author freeze

- Task: `R3_REAL_SHAM_SUBJECT_BALANCED_INNER_DIAGNOSTIC`
- Branch: `research/real-sham-r3-subject-balanced`
- Base: `a6fdf258ae89e4032e5e7afba61bba021fca186d`
- R2 outcome: `FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Status before execution: `READY`

## Frozen methods

- `P0_OBSERVATION_WEIGHTED`: inherited raw A1 row-level pooled ridge
- `P1_SUBJECT_ITEM_BALANCED`: fit-only arithmetic mean per available
  `(subject_id,item_id)` group, equal group weight
- Basis: `B0_RAW_A1`; target: `Y0_RAW_MINILM`; alignment: M0
- Tasks: `task1_nr`, `task2_tsr`
- Folds: `inner_s0_t0`, `inner_s1_t0`, `inner_s2_t0`
- Arms: real, trial shuffle, within-trial-unit shuffle, channel block

## Budget and boundary

`12 H-only + 48 EEG probes = 60 ridge operations`, 60 V5 ledgers, and
outer/calibration reads `0/0`. This freeze tests only source-fit weighting and
does not authorize any outer or paper-level claim.

Codex must append the executed outcome only after formal contract, tests,
compile, state/status, diff-check and parent/R0/R1/R2 hash checks.

## Executed outcome

- Run ID: `2026-08-24_005_v324_real_sham_r3_subject_balanced_inner`
- Outcome: `FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC`
- Passing task scope: none
- Scope violations: none
- Parent/R0/R1/R2 hashes: passed and immutable

P0 reproduced the R2 M0/B0 baseline with maximum subject-value absolute
difference `0.0`. P1 did not pass the frozen cross semantic family or paired
recovery rule for either task. This is a valid negative inner diagnostic, not
paper-level real-EEG increment evidence.

## Execution accounting

- P0/P1 H-only ridge operations: `6/6`
- P0/P1 EEG probe ridge operations: `24/24`
- Total ridge operations / unique V5 ledgers: `60/60`
- Fit-only subject-item group scopes: `6`
- Task1 groups by fold: `1054`, `1263`, `1011`
- Task2 groups by fold: `1346`, `1162`, `1202`
- Outer-test/calibration reads: `0/0`
- F3/Y1/M1/outer/direct u+/EQ-ANMA/A3/ROAMM/Gate executions: `0`

All P1 groups were constructed from supported fit rows only. Seen/cross rows
did not create groups, alter weights, select vocabulary or set thresholds.
Subject ID was used only as a fit grouping key and never entered probe input.
P0/P1 scoring row identities were exactly equal and remained individual rows.

## Formal outputs

- `artifacts/real_sham_r3_subject_balanced_contract.yaml`: `04f67c0cc4762ee93eb13fbcb26e57c20a65e3ec57cdfbd0b2f5fe107f9b1f92`
- `04_results/diagnostics/real_sham_r3_subject_balanced_inner.json`: `ccf89fb575c9bcd35a866ccf53c1d0f8fcc56bd9a17cffea3c1bb85261258812`
- `04_results/diagnostics/real_sham_r3_subject_balanced_inner.md`: `1822c9efa69496f089858c1f266d75b8e87b0e42faa2c709ec7a8976d8c06cc9`
- `04_results/diagnostics/real_sham_r3_subject_balanced_inner_run_ledger.jsonl.gz`: `417070b98346de0a3e9015922cc06afd32988d298f6b28b7110c766ffefa292d`

## Verification

- Focused R3 pytest: `8 passed`
- Focused plus related pytest: `87 passed`
- Compileall: passed
- Project state/status: passed/VALID
- `git diff --check`: passed
- PyTorch/CUDA: available

R3 is complete. Stop for author review; outer confirmation was not started.
