# Run 034 — SPEC v3.18 A1 measurement recovery

## Scope

- Task: `S1_A1_MEASUREMENT_RECOVERY`
- Baseline: `6dadf3290e38213b33074eeeb61642966db0e876`
- Governing contract: SPEC v3.18 D54–D60
- Dataset/tasks: ZuCo 2.0 `task1_nr`, `task2_tsr`
- Outer base: `outer_s0_t0`; folds: `inner_s0_t0`, `inner_s1_t0`, `inner_s2_t0`
- Seed: `20260813`
- Device: ridge solver inherited CPU float64 Cholesky; scoring `cuda:1`; text encoder CPU
- Claim boundary: inner selection evidence only; no outer or paper-level EEG claim

No outer-test EEG, label or metric and no calibration value was read. No outer confirmation, negative confirmation, alignment, direct `u+`, EQ-ANMA, Gate, A3 or ROAMM task was run.

## Immutable and data checks

- Admitted plus diagnosis plus run-032 V5 revalidation: `897/897 PASS`.
- Run 032 remained `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`; its formal artifacts, implementation, tests, run note and SPEC hashes reproduced.
- NR old A1/T8 common observations: `48,347/48,347`, retention `1.0`.
- TSR old A1/T8 common observations: `45,392/45,392`, retention `1.0`.
- T8 real deterministic smoke: 16 observations per task; `TEMPORAL_T_LT_8=0`, `TEMPORAL_INVALID=0`.
- All fit/seen/cross partitions retained the frozen 15 scoring subjects and had common-row retention `>=0.90`; observed minimum was `1.0`.

## Exact fit and V5 budget

- H-only fits: `6`.
- Frontend-arm fits: `72`.
- Total ridge fits: `78`.
- Real V5 ledgers: `78`; unique fit IDs: `78`.
- Each fit scored seen and cross without refitting.
- Maximum single-fit time: `1.3139111511409283 s`.
- Outer-test reads: `0`; calibration reads: `0`.

## Subject-first results

| Task | Frontend | seen u_oof (family) | cross u_oof (family) | transfer loss |
|---|---|---:|---:|---:|
| NR | A1_BP_CONCAT | 0.0362271000 (false) | -0.0104230760 (false) | 0.0466501761 |
| NR | A1R_LOG_BP_CONCAT | 0.0184847133 (false) | -0.0756597639 (false) | 0.0941444772 |
| NR | A1R_T8_FIXATION | 0.0124933505 (false) | -0.0130155055 (false) | 0.0255088561 |
| TSR | A1_BP_CONCAT | 0.0104805244 (false) | -0.0451026760 (false) | 0.0555832004 |
| TSR | A1R_LOG_BP_CONCAT | -0.0110643719 (false) | -0.0191924151 (false) | 0.0081280432 |
| TSR | A1R_T8_FIXATION | 0.0277638875 (true) | -0.0466668778 (false) | 0.0744307654 |

Candidate recovery deltas are candidate cross `u_oof` minus paired `A1_BP_CONCAT` cross `u_oof` on the same 15 subjects:

| Task | Candidate | Delta | 95% CI | Positive subjects | Recovery PASS |
|---|---|---:|---:|---:|---|
| NR | A1R_LOG_BP_CONCAT | -0.0652366879 | [-0.1361187545, -0.0000177189] | 4/15 | false |
| NR | A1R_T8_FIXATION | -0.0025924295 | [-0.0689150486, 0.0711292176] | 8/15 | false |
| TSR | A1R_LOG_BP_CONCAT | 0.0259102608 | [-0.0502885476, 0.1055439602] | 9/15 | false |
| TSR | A1R_T8_FIXATION | -0.0015642019 | [-0.0785102047, 0.0861861988] | 6/15 | false |

## Declarative outcome and state transition

Outcome: `FAIL_A1R_RECOVERY`.

- Selected frontend: `none`.
- Selected task scope: empty.
- `S1_A1_MEASUREMENT_RECOVERY`: `READY → DONE/FAIL_A1R_RECOVERY`.
- `S0_A1_NEGATIVE_CONFIRMATION_FREEZE`: `BLOCKED → READY` and becomes the sole recommended task.
- `S0_A1R_OUTER_CONFIRMATION_FREEZE` remains BLOCKED.
- Route direction: `primary=NEGATIVE-DIAGNOSTIC`, `backup=null`, `locked=null`.

No candidate met the frozen cross family-detection and paired recovery-delta criteria. The valid FAIL releases only a future pre-run negative-confirmation freeze; it does not authorize the negative panel itself.

## Formal artifacts

- `artifacts/a1_measurement_recovery_contract.yaml`: `fb711a799de5e9346f244f4c0942f19ecf8a26f35a0df26a6f9391e05e7cd01e`
- `04_results/audits/a1_measurement_recovery.json`: `cf68c0ca170152a79f163ed001706df80ea649ea854da85b09fef1f638e8b51a`
- `04_results/audits/a1_measurement_recovery.md`: `fc039ae77043619e562eb942898287321882189736bdd8219fc3c6a71cc87004`
- `04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz`: `90326ad6ed2bb981df0c0d8559102dd73c56a16ce7de6923973bad42529debc7`

Formal validation found no forbidden raw EEG, 840D array, observation embedding/logit, model weight or cache key. All four artifacts are aggregate/hash/subject-summary evidence only.

## Verification

- Pre-run recovery focused: `14 passed, 1 skipped` (real artifact test skipped before build).
- Post-run recovery focused: `15 passed`.
- Related A1/source/sham/V5/leakage tests: `95 passed, 28 subtests passed`.
- Full suite: `241 passed, 28 subtests passed`.
- Compile checks: PASS.
- Project state: `PROJECT STATE VALID | tasks=37 | done=19`.
- Project status: sole READY/recommended task is `S0_A1_NEGATIVE_CONFIRMATION_FREEZE`.
- `git diff --check`: PASS.
