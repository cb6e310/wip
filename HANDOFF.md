# Current Handoff

## Current decision

`S0_LEAKAGE_AUDIT=DONE/PASS_PRE_RUN_V1_V5`. V1–V4 pass on the admitted real ZuCo2 protocol artifacts. V5 passes only as an executable, adversarially tested pre-run ledger contract: `future_run_admission_required=true`, `real_training_ledgers_audited=0`.

This is not evidence that a future or unrun EEG/training job is leakage-free. Every future run must provide exact fit, inner-selection, outer-test-read and calibration record IDs plus frozen input hashes, and must pass the V5 validator independently.

## Admitted evidence

- V1 subject/record isolation: `PASS_REAL_ARTIFACTS` across 60 outer cells and 540 inner cells.
- V2 source-slot/text-fold/material-group isolation: `PASS_REAL_ARTIFACTS`; atomic groups do not cross train/validation/test boundaries.
- V3 legal H boundary: `PASS_REAL_ARTIFACTS`; H_full/H_empty are restricted to the registered probe/history interface, and candidate use is source-sentence identity exclusion only.
- V4 exact physical/canonical/provenance/scope/prefix/position/paired/scoring boundary: `PASS_REAL_ARTIFACTS` across 190 scopes, 18,475 targets and 92,375 repeats. `scoring_only=true`, `training_records_removed=0`.
- V5 future run-ledger validator: `PASS_PRE_RUN_CONTRACT`; nonzero test calibration, illegal fit/selection scope and outer-test tuning reads are rejected.
- Machine audit SHA256: `28f416a4470d8223294e100e2c8dbb514c05d98184a9dd7936c43267d9e8ca2c`; markdown SHA256: `8732d08d6b0145b2da9a71976ec44738ffd241e06dfdc8f6ae838080df44e09d`.
- Focused leakage tests 19/19, affected protocol regressions 50/50, complete suite 157/157.

## Required next action

Run only `S0_A1_ADMISSION`. It must admit the real 105-channel `sentenceData.rawData` source contract, including sampling rate, channel order, units, finite values and field semantics, and execute its outer-train-only real/sham/subject/semantic checks under the admitted leakage contract.

`S0_ALIGN_UNIT_COST` remains BLOCKED until A1 admission is DONE. Do not implement unit cost, direct u+, Stage 1, Gates, route/main experiment, or resume ROAMM in the A1 admission task.
