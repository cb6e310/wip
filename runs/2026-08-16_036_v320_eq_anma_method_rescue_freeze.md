# Run 036 — SPEC v3.20 EQ-ANMA synthetic method-rescue freeze

## Author decision

The valid ZuCo2+A1 `FAIL_A1_ADMISSION` and `FAIL_A1R_RECOVERY` close only the real A1 word-bandpower instantiation. They do not logically invalidate the EQ-ANMA mapping itself, the independent A3 admission chain or the later ROAMM replication.

The paper is therefore split into two non-interchangeable evidence chains:

- real measurement qualification, including the already frozen v3.19 A1 outer negative/transfer confirmation;
- synthetic method validity, testing whether EQ-ANMA recovers a known 2PL/Fisher allocation and can beat the strongest monotone direct `u+` control under the structure it claims to exploit.

No real outer-test value was read. No real Gate, alignment or EQ-ANMA result was produced.

## Anti-self-fulfilling design

The synthetic benchmark contains both:

- `STRUCTURED_FISHER`, where non-monotone 2PL information and cross-subject gating are genuinely useful;
- `MONOTONE_DIRECT`, where utility is monotone in positive contribution and direct weighting is the correct inductive bias.

Alpha zero is byte-identical across regimes. A valid method claim requires no false gain at alpha zero and no two-consecutive-alpha EQ superiority in the direct-friendly regime. Thus the benchmark can reject EQ-ANMA and is not an unconditional constructed win.

## Frozen scope

- 12 replicate seeds, two regimes, eight inherited alpha points: 192 scenarios.
- 30 synthetic subjects and 120 synthetic items per replicate, with disjoint train/selection/final-test subject and item populations.
- Existing v3.17 `W[840,384]`, EEG-shaped 105×8 features, inherited three shams, fit-only ridge contribution scoring and synthetic V5.
- Exact 4,800 measurement ridge fits plus 7,104 alignment fits: 11,904 total fits and 11,904 unique passing synthetic V5 ledgers.
- Uniform, strongest direct, gated direct, EQ V0/V1/V2 under the frozen L1/L2/L3 fairness rules.
- Primary method result is paired replicate `R@1@N=10`; parameter, oracle-weight and gate recovery are mandatory mechanism diagnostics.

## State decision

- `S0_EQ_ANMA_SYNTHETIC_BENCHMARK_FREEZE=DONE/PASS_EQ_ANMA_SYNTHETIC_BENCHMARK_FREEZE`.
- `S1_EQ_ANMA_SYNTHETIC_BENCHMARK=READY` and becomes recommended next.
- `S1_A1_NEGATIVE_CONFIRMATION` remains READY but must not run in the same Codex task; after the synthetic task it becomes recommended again.
- The ZuCo2 package freeze now requires valid synthetic-method and real-negative tasks plus an independent A3 admission resolution; A3 may not be silently dropped or described as an A1 replacement.

## Claim discipline

A full PASS can support only a bounded statement that EQ-ANMA is synthetically validated under the pre-specified 2PL/Fisher regime and has an observed synthetic alpha threshold. It cannot support real EEG superiority, Gate B, a real alpha threshold or claims about unfinished A3/ROAMM panels.

## Evidence

- `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_20_2026-08-16.md`
- `artifacts/eq_anma_synthetic_benchmark_freeze.yaml`
- this run record
