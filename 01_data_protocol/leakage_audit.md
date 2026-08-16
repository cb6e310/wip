# ZuCo2 pre-run leakage audit

- Overall outcome: `PASS_PRE_RUN_V1_V5`
- V1 subject/record isolation: `PASS_REAL_ARTIFACTS`
- V2 stimulus/source-slot/material isolation: `PASS_REAL_ARTIFACTS`
- V3 legal H boundary: `PASS_REAL_ARTIFACTS`
- V4 candidate/provenance/scoring boundary: `PASS_REAL_ARTIFACTS`
- V5 future run-ledger contract: `PASS_PRE_RUN_CONTRACT`

V1-V4 passed on the admitted real protocol artifacts. No EEG, training output,
held-out metric, Gate, route, main-experiment or ROAMM result was read.

## Future run admission boundary

`future_run_admission_required=true` and `real_training_ledgers_audited=0`.
Every future run must provide fit, inner-selection, outer-test-read and calibration
record IDs plus exact input hashes, and must pass the executable V5 validator.
This pre-run contract is not evidence that an unrun or future training job is leakage-free.

The machine-readable audit and exact input bindings are in
`04_results/audits/zuco2_pre_run_leakage_audit.json`.
