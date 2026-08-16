# Current Handoff

## Current decision

`S0_A1_ADMISSION` completed its frozen SPEC v3.14 pilot but is not DONE. The outcome is `FAIL_A1_ADMISSION`: NR and TSR both fail A-A1 on raw and `token_local_frozen_initial_latent`, both fail A-A3 on both bases, while A-A2 and A-A4 pass. NR raw A-A1 has significantly negative `u_oof`; every task/basis has significantly negative `u_min`. There is no `CO_N1_LATENT_LOSS` and no `INVALID_BASIS_ORDER`.

The preflight passed: 9 fits, maximum 0.135 seconds, validation four-arm common support 1068 observations / 54.4343%, finite raw `[7094,840]` and latent `[7094,384]`, and 9/9 V5 ledgers. The complete pilot used 93,739 released word-aligned observations and produced 639 fits/639 passing real V5 ledgers (495 ridge, 144 logistic); maximum single fit was 8.217 seconds. No outer-test EEG/features/labels/metrics or calibration were read.

## State boundary

- `S0_A1_ADMISSION=BLOCKED/FAIL_A1_ADMISSION`; it must not be marked DONE.
- `S0_ALIGN_UNIT_COST` remains BLOCKED; Stage 1, Gates, route and main experiment remain blocked.
- `last_completed_task=S0_A1_SOURCE_ADMISSION`.
- `recommended_next_task=null`.
- `B_A1_ADMISSION_FAILED_AUTHOR_REVIEW` requires an author-approved specification/state update. Do not change backbone, cells, seeds, shams, probes, thresholds or dataset to force a pass.
- ROAMM remains mandatory but deferred; do not resume it.

## Evidence

- Contract: `artifacts/a1_admission_contract.yaml` (`c9c5a94b8227b6e43ecfc6d61b9b10b33f9340f7c845ca7dbaa0e0a3e65d9f4b`)
- Audit JSON: `04_results/audits/a1_admission.json` (`b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e`)
- Audit Markdown: `04_results/audits/a1_admission.md` (`e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e`)
- V5 ledger: `04_results/audits/a1_admission_run_ledger.jsonl.gz` (`fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd`)
- Run: `runs/2026-08-16_027_v314_a1_admission.md`
