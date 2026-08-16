# Run 2026-08-15_023 — v3.12 pre-run leakage audit

## Scope

Completed only `S0_LEAKAGE_AUDIT` under SPEC v3.12 Appendix P.3. The task read immutable protocol JSON/YAML only. It did not read EEG, run training, perform A1 admission or unit-cost work, implement direct u+, run Stage 1/Gates/route/main experiment, or access ROAMM.

## Immutable input admission

All 12 Appendix P.3 physical SHA256 values matched before audit. Existing pure validators and canonical helpers rechecked outer/inner integrity, candidate/common-support integrity, cross-artifact bindings and scientific provenance. The audit script rehashed all inputs after writing its two outputs; every hash remained unchanged.

## V1–V5 results

- V1 subject/record isolation: `PASS_REAL_ARTIFACTS`; 60 outer cells and 540 inner cells checked.
- V2 source-slot/text-fold/material-group isolation: `PASS_REAL_ARTIFACTS`; record identities and atomic groups checked rather than aggregate counts alone.
- V3 legal H boundary: `PASS_REAL_ARTIFACTS`; H_full/H_empty and all forbidden current/future/target-stat/candidate/ET classes checked.
- V4 candidate/provenance/scoring boundary: `PASS_REAL_ARTIFACTS`; 190 scopes, 18,475 target instances and 92,375 repeats checked, including first-nine prefixes, target positions, paired 1:1/1:9, eligibility/exclusion ledgers, `scoring_only=true` and `training_records_removed=0`.
- V5 executable run-ledger admission: `PASS_PRE_RUN_CONTRACT`; `future_run_admission_required=true`, `real_training_ledgers_audited=0`, test-time calibration count 0.
- Overall: `PASS_PRE_RUN_V1_V5`.

No claim is made that future or unrun training is leakage-free. Each future run requires a separate admitted ledger.

## Outputs

- `04_results/audits/zuco2_pre_run_leakage_audit.json`: `28f416a4470d8223294e100e2c8dbb514c05d98184a9dd7936c43267d9e8ca2c` (6,026 bytes)
- `01_data_protocol/leakage_audit.md`: `8732d08d6b0145b2da9a71976ec44738ffd241e06dfdc8f6ae838080df44e09d` (992 bytes)
- Validator source: `1ccdfef0abfda7e5e8522791c83e96759325d1ffcfdb1b7d03bf4201ebe97fa0`
- CLI source: `82f8155599cea0c07f605eeea99028d121fe38bb625b155605a9efa8c83d04d4`
- Focused test source: `2e96981968b77a4e0817211c21f35c1fbb368bb296baf9d9d2d566d07131bc93`

## Verification

- Focused leakage tests: 19 passed, 0 skipped, 0 failed.
- Affected candidate/common-support/joint/inner/H/source-join regressions: 50 passed, 0 skipped, 0 failed.
- Full unittest suite: 157 passed, 0 skipped, 0 failed.
- Post-migration full suite repeated: 157 passed, 0 skipped, 0 failed.
- Final state validation: `PROJECT STATE VALID | tasks=30 | done=16`; sole READY/recommended task `S0_A1_ADMISSION`.
- `git diff --check`: PASS; all 12 immutable inputs have zero Git diff and retain their frozen SHA256 values.

## State migration

- `S0_LEAKAGE_AUDIT`: READY → DONE / `PASS_PRE_RUN_V1_V5`.
- `S0_A1_ADMISSION`: BLOCKED → READY and recommended.
- `S0_ALIGN_UNIT_COST`: remains BLOCKED until A1 admission is DONE.
- ROAMM remains deferred.
