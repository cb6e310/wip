# Current Handoff

## Current stage

Stage 0 remains `IN_PROGRESS`. The governing specification is v3.6. No Stage-1 probe, Gate A/B, route lock, T6 real extraction, or main experiment has been authorized or run.

## Completed in `2026-08-14_010_v36_stage0_recovery`

- Synchronized `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_6_2026-08-11.md` (SHA256 `ae93e506e62e2d35349258ca0a9c4d7065f507c8aa56b0adfcb8beacaaafefbd`) and reconciled project memory to v3.6.
- Kept exactly two backbones in scope: A1 and A3. The stale A4 task is `SKIPPED` because neither the user nor v3.6 requests a third backbone.
- Preserved A1 as `ENGINEERING_CONTRACT_PASS_SCIENTIFIC_ADMISSION_BLOCKED`: the raw-unit Hann periodogram, `nFFT=max(512,nextpow2(T))`, half-open integration, no-dB rule, and outer-train-only robust normalization are frozen; the numeric band edges remain an engineering configuration, not an author-level freeze.
- Verified ZuCo2 source-slot identity without using text hash as identity. NR maps 349 summary slots into 370 material rows and TSR maps 390 into 411; the unique mapping hashes are `97f3a0bd...f12` and `7a3bc1cb...060`.
- Generated the real ZuCo2 6x5 joint split for two task-local panels: 12,503 eligible records, 799 exclusions, seed `20260813`, config hash `3899709d...437`, artifact SHA256 `20aedfd5...fa6`.
- Froze the task-local released lexical content-word semantic item and completed the full exclusion ledger. NR support is 624/2,553 = 24.441833%; TSR is 666/2,536 = 26.261830%; both pass the frozen 20% No-Go redline. TMNRED remains blocked by missing released word-level lexical content.
- Completed H_full/H_empty and explicit leakage assertions for target/gold/current/future payloads, candidates, target statistics, and eye-tracking fields.
- Completed our ANMA-orig reference implementation and synthetic validation, including partial-Spearman covariate diagnostics, parameter-rank stability, and v3.6 RankFit plateau logic. Seed `20260813`, fold `S0-T0`, config hash `09130227...adb`; 12/12 self-check assertions pass.
- Completed E-5 subject-first aggregation and seeded subject-cluster bootstrap contract testing. This is a synthetic statistical-unit check only, not Gate-A evidence.
- Reconciled A3 to v3.6: CO-N7 is cleared by the complete 2534.78-hour Appendix-D inventory, and local frozen inference is a disclosure/no-redistribution assumption rather than a hard blocker. Checkpoint/load/pooling/no-gradient and the 252-file E1..E128 source order remain engineering-verified. The v3.6 rerun passed 12/12 assertions in 161.671 s; config hash `1546c94a...000`, artifact SHA256 `c92f6f1b...299`.

## Validation

- Full remote unittest suite: 69/69 PASS.
- A3 v3.6 preparation rerun: 12/12 engineering assertions PASS_WITH_BLOCKERS.
- Final project-memory validator: `PROJECT STATE VALID | tasks=25 | done=11`.
- Final status report lists four active blockers and exactly one ready task, `S0_DIRECT_U_PLUS`.

## Still blocked

- A1 real admission: no verified continuous 128-to-105 channel map and no author-frozen numeric edges for the eight named bands. Do not use the first 105 channels as an implicit map.
- Candidates and full leakage audit: no shared candidate lists or paired-verification pairs exist; TMNRED lexical/event, license, incomplete-cell, session, and split policies remain unresolved.
- TMNRED semantic item: the released snapshot lacks word-level lexical content. Do not retokenize sentence text, translate it, or infer lexical items.
- A3 real admission: no approved EGI128-to-canonical map/interpolation matrix and hash; ZuCo raw signal units plus filter order/notch Q are not frozen; no real mapped MAT-to-200D extraction has passed.
- A1 admission blocks Stage 1. Therefore Gate A/B, EQ-ANMA real weights, route lock, T6, and main experiments remain prohibited.

## Recommended next task

`S0_DIRECT_U_PLUS` is the next independently ready engineering task. Resolving A1 channel/band admission and the shared candidate/leakage protocol remains the prerequisite for Stage 1.

## Do not do yet

Do not treat global support rates as fold-local training statistics; downstream support must be fitted outer-train-only. Do not treat the A1/A3 synthetic checks as real-data admission. Do not run Stage 1, Gate A/B, T6 real extraction, route lock, or paper experiments. Do not substitute a third backbone.
