# AI Project Entry Point

This package is a branch-local author freeze for an independent real-vs-sham
diagnostic. It is not a replacement for the current project state and must not
be merged into `main` without a later author decision.

## Branch target

- Branch: `research/real-sham-rescue`
- Base: `origin/main@86e4f370bab650ff73831627be102fc9a7ffe6a4`
- Project root on server: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

## Read order

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_21_2026-08-22.md`
5. `artifacts/real_sham_rescue_freeze.yaml`
6. `CODEX_INSTRUCTION.md`

If the branch state conflicts with the governing SPEC, stop with
`STATE_SPEC_CONFLICT`.

## Immutable boundaries

- Preserve `FAIL_A1_ADMISSION`, `FAIL_A1R_RECOVERY`, run-032 `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`, and v3.20 synthetic `FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE`.
- Do not run `S1_A1_NEGATIVE_CONFIRMATION` in the same task.
- Do not run A3, ROAMM, alignment training, direct `u+`, EQ-ANMA, Gate A or Gate B.
- R0 is an existing-artifact reanalysis only: zero new EEG fits and zero outer-test/calibration reads.
- Do not add candidates, change thresholds, delete subjects, relax support, or remove the channel-block sentinel after seeing results.

## Branch task

`R0_REAL_SHAM_RESCUE_FREEZE` creates the v3.21 contract and reproduces the
semantic-sham, legacy-sham and channel-topology contrasts from admitted A1
artifacts. It must stop after contract/tests/report verification.
