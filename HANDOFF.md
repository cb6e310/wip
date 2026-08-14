# Current Handoff

## Current decision

`S0_CANDIDATE_COMMON_SUPPORT=DONE/PASS_N10_COMMON_SUPPORT`. The immutable v3.10 candidate triplet remains admitted as `S0_CANDIDATES=DONE/STRUCTURAL_NO_GO_N50`; it was neither modified nor reopened.

The v3.11 N=10 candidate-common-support scoring population is now materialized. Eligibility is exactly per-scope `legal_count>=9`; all 18,475 target instances remain ledgered, all training records remain intact, and every excluded scoring target has reason `LEGAL_NEGATIVES_LT_9` with its admitted sequential counts.

## Admitted evidence

- Base physical hashes were rechecked: candidate lists `51130ffc216a1f0bf50a9eeec42136555ab98ee110f3aaa265de54c3a004115a`; paired pairs `bc37630ea3c6c870d4388ac0c16582f742e6751d533e3656a284304d09e3ec5c`; feasibility audit `8f478fddc78ccb46df2c1a75945a3f90ec89f7c58ca456172a4874bef75f7960`.
- Common support is 17,061/18,475 (92.35%): outer NR 306/349, outer TSR 359/390; inner NR 7,553/8,376, inner TSR 8,843/9,360.
- Minimum exact per-scope coverage is 60/70=85.71% outer and 77/93=82.80% inner. The 1,414 exclusions transition below nine at length=1,402, cosine=0, H=12.
- Every eligible repeat uses the first nine admitted maximal-order negatives and its admitted target position. Paired AUROC uses the first negative; paired AUPRC uses the same nine negatives at prevalence 0.1.
- Two same-order builds, one reverse-order build, and the formal artifacts are canonical-byte identical. `training_records_removed=0`; no tokenizer, encoder, EEG, training/model result or ROAMM path was read.
- New artifact SHA256: candidate common-support lists `b3eda1c09542344e108ce162a0f414beb54a426644db18126ee1e87e36ddf097`; N=10 paired pairs `71b6b53e5686e125d067240fd6414b833ef74b46159b130d5c6097152d722771`; audit `6dfba054d8242501808e267f91efdf080f6cbd479b617819edb4baf47554c0fc`.

## Required next action

Run only `S0_LEAKAGE_AUDIT`, the ZuCo2 V1-V5 protocol/leakage audit. Treat both the v3.10 base ledgers and v3.11 N=10 common-support artifacts as immutable admitted inputs.

Do not implement direct u+, A1 real admission, Stage 1, Gates, route/main experiment, or resume ROAMM in that task. ROAMM remains mandatory but deferred at its preserved incomplete checkpoint until the complete ZuCo2 first-dataset experiment is frozen.
