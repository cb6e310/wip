# Run 024 — v3.13 leakage review and A1 source-admission freeze

## Scope

Author-level review of pushed commit `d9dfe51442155fbd3854d223916c519a7757fff1`, followed by a pre-outcome specification correction and the smallest quota-efficient next-task freeze. This run did not read an EEG value, fit a normalizer/probe/model, inspect a held-out metric, or execute Gate/route/main-experiment/ROAMM work.

## Leakage audit review

Verdict: `ADMITTED_NO_REWORK`.

- Repository state before author documents was clean; HEAD was exactly `d9dfe51442155fbd3854d223916c519a7757fff1` (`Freeze_v312_pre_run_leakage_audit`).
- V1 `PASS_REAL_ARTIFACTS`: 60 outer cells and 540 inner cells.
- V2 and V3 `PASS_REAL_ARTIFACTS` with exact source/material and H-boundary checks.
- V4 `PASS_REAL_ARTIFACTS`: 190 scopes, 18,475 targets, 92,375 repeats, 17,061 eligible and 1,414 explicit exclusions; `training_records_removed=0`.
- V5 `PASS_PRE_RUN_CONTRACT`: `future_run_admission_required=true`, `real_training_ledgers_audited=0`.
- Formal JSON SHA256 `28f416a4470d8223294e100e2c8dbb514c05d98184a9dd7936c43267d9e8ca2c`; markdown SHA256 `8732d08d6b0145b2da9a71976ec44738ffd241e06dfdc8f6ae838080df44e09d`.
- Independent focused leakage suite: 19/19 PASS. Rebuilt real audit JSON/markdown were byte-identical to the committed formal artifacts and immutable inputs remained unchanged.
- Independent affected protocol run: 46 PASS with only the `h5py`-dependent source-join module unavailable locally; the pushed server record reports 50/50. Independent full discovery: 99 PASS, one skip and six dependency-only import errors from absent `torch`/`h5py`; the pushed server record reports complete 157/157 twice. These local environment gaps do not invalidate the focused real-artifact admission.
- Project state validator passed at 30 tasks / 16 done before this author revision; commit diff check was clean.

## Pre-outcome scientific correction

The A1 frontend computes per-epoch Hann-periodogram bandpower and reads only the magnitude of the demeaned, Hann-windowed rFFT. Rotating phase on that actual analysis spectrum is an identity for the 840D input. Randomizing phase on the raw epoch before the frontend is not equivalent: the subsequent Hann multiplication changes the new analysis-spectrum magnitude, so the perturbation is no longer phase-only in the representation A1 uses. The old phase-only comparison is therefore implementation-position-dependent and non-identifying for A1.

SPEC v3.13 D32 therefore moves analysis-spectrum phase rotation to a required feature-invariance implementation diagnostic and freezes three identifiable A1 shams: matched trial shuffle, within-trial EEG-unit/window assignment shuffle, and per-trial channel-block permutation. The diagnostic rotates phase only after the exact demean+Hann+rFFT step and recomputes features directly from the unchanged magnitudes; it does not inverse-transform and apply Hann again. This was decided without EEG outcomes or training results.

## State and next task

Added `S0_A1_SOURCE_ADMISSION` as the sole READY/recommended task and made `S0_A1_ADMISSION` depend on it. This gate performs only read-only source/metadata inspection, compact exclusion/coverage evidence and deterministic A1 feature smoke. It stops before normalization, probes, shams or training.

On PASS only:

1. `S0_A1_SOURCE_ADMISSION` READY → DONE with `completion_outcome=PASS_REAL_A1_SOURCE`.
2. `S0_A1_ADMISSION` BLOCKED → READY and becomes the sole recommended task.
3. `S0_ALIGN_UNIT_COST` stays BLOCKED until full A1 admission is DONE.

On a source-order, sampling, scale/provenance, finite-value, identity or G0 failure, keep the source task not-DONE, record the precise blocker and stop. Do not weaken the source contract or proceed to probes.
