# Current Handoff

## Completed decision

Run `2026-08-16_034_v318_a1_measurement_recovery` completed the exact SPEC v3.18 inner-only audit with declarative outcome `FAIL_A1R_RECOVERY`.

- exact budget: 6 H-only plus 72 frontend-arm ridge fits, 78 total fits and 78 unique passing V5 ledgers;
- data boundary: zero outer-test EEG/label/metric reads and zero calibration reads;
- common observations: NR 48,347/48,347 and TSR 45,392/45,392, retention 1.0, all frozen 15 scoring subjects retained;
- selected frontend: none; selected task scope: empty;
- immutable history: v3.14 remains `FAIL_A1_ADMISSION` and run 032 remains `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`.

Neither frozen candidate passed the required combination of cross `family_detected`, recovery-delta CI lower above zero and at least 10/15 positive paired subject deltas in either task. This is a valid bounded FAIL, not an invalid run and not permission for another frontend search.

## Sole next action

Only `S0_A1_NEGATIVE_CONFIRMATION_FREEZE` is READY. A new governing SPEC must freeze, before any outer value is read:

- the exact 6×5 outer-cell run budget and V5 scopes;
- subject-first aggregation, multiplicity and decision rules;
- expected-negative and unexpected-positive handling;
- formal outputs and claim language.

The freeze task must not run the negative panel. `S1_A1_NEGATIVE_CONFIRMATION` remains BLOCKED until that freeze is DONE.

## Boundaries

- Do not rerun run 034, change either candidate, add a frontend, or alter the fold, seed, probe, sham, row-retention or recovery threshold.
- Do not execute A1-R outer confirmation; no frontend was selected.
- Do not read outer-test outcomes, run negative confirmation, alignment, direct `u+`, EQ-ANMA, Gate, A3 or ROAMM.
- Preserve all admitted/run-032 files byte-for-byte.

## Evidence

- Governing SPEC: `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_18_2026-08-16.md`
- Recovery contract: `artifacts/a1_measurement_recovery_contract.yaml`
- Recovery audit: `04_results/audits/a1_measurement_recovery.json`
- Human-readable audit: `04_results/audits/a1_measurement_recovery.md`
- V5 ledger: `04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz`
- Run record: `runs/2026-08-16_034_v318_a1_measurement_recovery.md`
