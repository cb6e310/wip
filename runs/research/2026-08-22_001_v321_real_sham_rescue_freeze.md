# Run R001 — v3.21 real-vs-sham rescue research freeze

## Scope

This is a branch-local author freeze for `R0_REAL_SHAM_RESCUE_FREEZE`. It
defines an independent diagnostic question and does not modify the parent
project route or any admitted formal outcome.

- Branch: `research/real-sham-rescue`
- Base: `86e4f370bab650ff73831627be102fc9a7ffe6a4`
- Governing overlay: `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_21_2026-08-22.md`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- New EEG fits: `0`
- Outer-test/calibration reads: `0/0`

## Author diagnosis

The parent A1 pilot has uncertain real-vs-trial-shuffle contrasts, strongly
negative channel-block contrasts and a much more negative legacy `u_min`.
Subject identity is decodable while semantic item identity is not. A1-R shows
seen-to-cross transfer collapse. These facts motivate, but do not prove,
geometry, temporal dilution, scale nuisance, sham non-exchangeability and
target-mismatch hypotheses.

## Frozen R0 estimands

```text
delta_semantic = real - mean(trial_shuffle,
                              within_trial_unit_assignment_shuffle)
delta_legacy = real - mean(all_three_parent_shams)
delta_channel = real - channel_block_permutation
```

The semantic contrast is the new diagnostic quantity. The legacy quantities
remain mandatory controls; channel-block cannot be removed because it is
unfavorable.

## Required implementation boundary

R0 may only reuse existing A1 audit/ledger artifacts and pure statistical
helpers. It must not add a feature, train a model, read outer-test values,
change a sham, or modify parent artifacts. If exact reproduction is impossible,
the outcome is `INVALID_REAL_SHAM_RESCUE_R0`.

## Exit

After tests and state checks pass, stop and request author review for R1. R1 is
not part of this run and no positive EEG or EQ-ANMA claim is authorized.
