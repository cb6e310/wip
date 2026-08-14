# A3 LaBraM-Base Preparation, Contamination, and Provenance Audit

Run: `2026-08-14_010_v36_stage0_recovery`

## Verdict

`SPEC_FROZEN / ARCHITECTURE_SUPPORTED / CHECKPOINT_HASH_VERIFIED / SOURCE_CHANNEL_ORDER_VERIFIED / PREPROCESSING_SYNTHETIC_SMOKE_PASS / CO-N7_CLEARED_BY_V3.6 / LOCAL_RESEARCH_INFERENCE_ASSUMED_WITH_DISCLOSURE / SEMANTIC_CHANNEL_MAP_BLOCKED / RAW_UNIT_AND_FILTER_PARAMETERS_UNFROZEN / REAL_EXTRACTION_NOT_VALIDATED`

A3 is still blocked for T6/K7 admission, but no longer by contamination or
checkpoint-use rights. Under v3.6, LaBraM Appendix D's complete 2534.78-hour
pretraining inventory contains neither ZuCo nor natural-reading EEG, so CO-N7
is cleared. Local research inference/frozen extraction is the project's
recorded working assumption; the checkpoint source/hash must be disclosed and
the checkpoint must not be redistributed. No third backbone is substituted.

## Frozen engineering contract

- The engineering candidate accepts continuous raw EEG at 500 Hz, applies
  0.1-75 Hz bandpass and 50 Hz notch, resamples to 200 Hz, and divides by 100
  according to the official finetuning engine convention. The filter order
  and notch Q are intentionally required inputs because the guide does not
  freeze them; the candidate smoke uses order 4 and Q 30 and is not real-data
  admission.
- LaBraM-Base is constructed with `patch_size=200`, `embed_dim=200`,
  `depth=12`, `num_heads=10`, `init_values=0.1`, `qkv_bias=false`, absolute
  position embeddings, and `use_mean_pooling=true`.
- The release pooled output is obtained inside the official model as
  `fc_norm(mean(non-CLS patch tokens))`; the wrapper does not re-pool those
  tokens. A sentence window uses 5 s and 2.5 s stride, then means the window
  embeddings as specified by the guide. All extraction is no-gradient and
  frozen.
- The current wrapper accepts either an approved 128-channel permutation or a
  128x128 spatial mixing matrix, but the project has not approved either map.

## Evidence matrix

| Item | Observation | Verdict |
|---|---|---|
| Architecture | Official vendor code and checkpoint load with the Base constructor; pooled output is 200D. | SUPPORTED |
| Checkpoint | `02_code/vendor/checkpoints/labram-base.pth`, 96,612,769 bytes, SHA256 `7c50583826afac76c4ab18f43d958df40496c8229accc09ed6a227c9bb57c37c`; pinned file commit `d52cb6d1801bb038e10ea1b6b3292c0bd569a9d5`, source commit `c431221e6cfd23dbfa9950e0180682fb322b0548`. | HASH VERIFIED |
| Checkpoint load | The official pretraining checkpoint has expected extra `norm.*`, `mask_token`, and `lm_head.*` keys and lacks finetuning `fc_norm.*`; these are explicitly allow-listed and recorded. | COMPATIBILITY VERIFIED |
| Raw inventory | All 252 continuous files expose `EEG.data` as 128xT, `nbchan=128`, `srate=500`, and stable labels `E1..E128`. | SOURCE ORDER VERIFIED |
| Raw geometry | Continuous MAT `chanlocs` geometry fields are empty. | EXTERNAL MONTAGE REQUIRED |
| Summary distinction | The separate preprocessed/word-level files have 105 channels and are not the A3 continuous input. | VERIFIED; DO NOT MIX |
| Preprocessing | A synthetic 500-to-200 smoke passes shape and finite-value assertions using an explicitly labeled candidate filter order/Q; the guide has not frozen those values and no real EEG extraction has been run. | SYNTHETIC ONLY |
| Pretraining corpus | LaBraM Appendix D's complete 2534.78-hour list covers the public datasets and five self-collected paradigms; it contains neither ZuCo nor natural-reading EEG. | CO-N7 CLEARED BY v3.6 |
| Rights / redistribution | v3.6 authorizes local research inference/frozen extraction as a working assumption. Source/version/hash are disclosed and the original checkpoint is not redistributed with artifacts. | DISCLOSURE ITEM; NOT A T6/K7 HARD BLOCKER |
| Semantic channel map | LaBraM requires canonical name-derived positions. No approved EGI128-to-canonical map, interpolation matrix, coverage, or map hash exists. | BLOCKED |
| Raw units / filter parameters | The official frequency/resampling/scale convention is recorded, but ZuCo raw units, filter order, and notch Q are not scientifically frozen. Order 4/Q 30 exist only in the synthetic engineering fixture. | BLOCKED FOR REAL ADMISSION |

## Preparation self-check

The engineering-only audit is recorded in a seed/fold/config-hash JSON under
`03_runs/debug_runs/`. It audits 252 files and checks finite no-gradient
output, unchanged model weights, the 5 s/2.5 s window contract, and 200D
pooling. Its synthetic channel positions are an identity shape fixture and
must not be treated as a real semantic mapping.

The v3.6 rerun used seed `20260813`, fold `A3-contract-1`, method
`A3-LaBraM-Base-preparation`, and config hash
`1546c94a5e8dc297e5633afe6d5493f8e146526af1d4efd4175759c894151000`.
It scanned 252 MAT files, produced synthetic preprocessing shape `[128,1600]`
and pooled shape `[2,200]`, passed 12/12 engineering assertions in 161.671 s,
and wrote artifact SHA256
`c92f6f1b2cd02d3e5e88518fc8f368abcc31050da837e1747c1058f1f454b299`.

## Required resolution before DONE

1. Approve an authoritative HydroCel-128 geometry and exact-name or spatial
   interpolation policy; publish ordered names, matrix/indices, coverage, and
   hash.
2. Verify the ZuCo continuous-MAT signal unit and freeze filter order and notch
   Q; the synthetic order-4/Q-30 fixture is not author-level admission.
3. Run the real 500 Hz MAT preprocessing and mapped extraction, with an
   end-to-end no-gradient 200D self-check, before any T6/K7 use.

## Candidate feasibility if LaBraM fails

These entries are audit-only and do not alter the v3.6 A1/A3 specification.

| Candidate | Interface evidence | Contamination / rights | Feasibility conclusion |
|---|---|---|---|
| CBraMod | Native `[B,C,S,200]`, 200D; checkpoint SHA256 `0792cb808c14e6b7a2bb2ce1dff379bc47bc54c49a779825bdfeb33bf8157178`. | TUEG-only claim but formal CO-N7 status UNKNOWN; code MIT versus HF Apache-2.0 claim requires rights review. | Closest contingency interface; no substitution authorized. |
| REVE-Base | Requires 200 Hz EEG plus `[B,C,3]` positions; native 512D; checkpoint SHA256 metadata `8ecc650619598748286c2457f81f5c6bd12e8bb59db44f7b02af1955c44de8fe`. | CO-N7 UNKNOWN; gated `license=other`, Responsible Use and no-redistribution terms; direct download requires authorization. | Not drop-in; needs position bank and fixed 512-to-200 projection; operational/legal blocker. |

## First-party sources

- LaBraM repository: https://github.com/935963004/LaBraM
- LaBraM paper: https://arxiv.org/html/2405.18765
- LaBraM finetuning engine: https://raw.githubusercontent.com/935963004/LaBraM/c431221e6cfd23dbfa9950e0180682fb322b0548/engine_for_finetuning.py
- LaBraM model code: https://raw.githubusercontent.com/935963004/LaBraM/c431221e6cfd23dbfa9950e0180682fb322b0548/modeling_finetune.py
- CBraMod repository/paper: https://github.com/wjq-learning/CBraMod and https://arxiv.org/html/2412.07236
- CBraMod checkpoint card: https://huggingface.co/weighting666/CBraMod
- REVE repository/paper/card: https://github.com/elouayas/reve_eeg, https://arxiv.org/html/2510.21585, and https://huggingface.co/brain-bzh/reve-base
