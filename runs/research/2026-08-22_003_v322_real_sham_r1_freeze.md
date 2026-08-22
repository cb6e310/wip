# Run R003 — v3.22 real-vs-sham R1 inner diagnostic freeze

## Author freeze (pre-execution)

- Task: `R1_REAL_SHAM_INNER_DIAGNOSTIC`
- Branch to create: `research/real-sham-r1-inner`
- Base commit: `ec7ced2708fe68ae8614b6b89b03256d88d1b541`
- Parent R0 outcome: `PASS_REAL_SHAM_RESCUE_FREEZE`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Execution status at freeze: `READY`

## Frozen cells

- Tasks: `task1_nr`, `task2_tsr`
- Inner folds: `inner_s0_t0`, `inner_s1_t0`, `inner_s2_t0`
- Frontends: `F0_A1_BP_CONCAT`, `F1_LOGREL_BP`, `F2_T8_FIXATION`
- Targets: `Y0_RAW_MINILM`, `Y1_H_RESIDUAL_MINILM`
- Arms: `real`, `trial_shuffle`, `within_trial_unit_assignment_shuffle`,
  `channel_block_permutation`
- Alignment: `M0_STRICT_INDUCTIVE` only
- Seed: `20260813`; alpha: `1.0`; temperature: `0.07`

## Fit budget

`6 H-only Y0 + 6 Y1 residualizer + 144 EEG probes = 156` ridge operations.
Expected ledgers: `150` EEG V5 plus `6` text-only residualizer ledgers. Expected
outer-test/calibration reads: `0/0`.

## Outcome field

This record is a freeze template. Codex must append the executed outcome only
after the formal contract, tests, compile, state/status, diff-check and hash
checks pass. Legal outcomes are `PASS_R1_BOTH_TASKS`,
`PASS_R1_LIMITED_ONE_TASK`, `FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`, and
`INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC`.

No result from this run may relabel parent A1/A1-R/run-032/synthetic outcomes or
release an outer or paper-level claim.

## Executed outcome

- Run ID: `2026-08-22_003_v322_real_sham_r1_inner`
- Outcome: `FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC`
- Selected candidate: none
- Selected task scope: none
- Scope violations: none
- Parent/R0 artifacts: byte/hash checks passed and remained immutable

No candidate met both the frozen cross-subject family-detection rule and the
paired recovery rule relative to `F0_A1_BP_CONCAT/Y0_RAW_MINILM`. This is a
valid negative inner diagnostic, not evidence for a real-EEG increment.

## Execution accounting

- H-only Y0 ridge operations: `6`
- Y1 text residualizer ridge operations: `6`
- EEG probe ridge operations: `144`
- Total ridge operations: `156`
- EEG V5 ledgers: `150`
- Text-only residualizer ledgers: `6`
- Outer-test/calibration reads: `0/0`
- F3/M1/outer/alignment/direct u+/EQ-ANMA/A3/ROAMM/Gate executions: `0`

## Formal outputs

- `artifacts/real_sham_r1_contract.yaml`: `50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed`
- `04_results/diagnostics/real_sham_r1_inner.json`: `610e40bf09959fb30f2a08f998b42148e9967168263a64c3ba37969194e964ff`
- `04_results/diagnostics/real_sham_r1_inner.md`: `a858a7475b486bd874ace44435cc2de074c57391f6cdc9ffc102cb7f78c5beed`
- `04_results/diagnostics/real_sham_r1_inner_run_ledger.jsonl.gz`: `28fc32b5103a1ba19b9c2cd2c724da5d7d3aff17f53f5ac72e3993e64db9314a`

## Verification

- Focused R1 pytest: `9 passed`
- Related R0/A1/A1-R/leakage pytest: `61 passed`
- Compileall: passed
- Project-state validator/status: passed/VALID
- `git diff --check`: passed
- PyTorch/CUDA: available (`2.13.0+cu130`, 4 GPUs)

R1 is complete. Stop for author review; R2 outer confirmation was not started
and remains forbidden without a new author freeze.
