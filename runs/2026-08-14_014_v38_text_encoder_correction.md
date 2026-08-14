# v3.8 Frozen Text Encoder Contract Correction

- Run ID: `2026-08-14_014_v38_text_encoder_correction`
- Seed: `20260813`
- Fold: `S0-TEXT`
- Method: `frozen-MiniLM-L6-v2`
- Scope: reopened `S0_TEXT_ENCODER` only
- Baseline: `bbf8d114a16580451d85a47328ec8b37ec54971a`
- Claim boundary: engineering admission only; no ROAMM admission, EEG data, training, held-out metric, Gate result or paper-level result was read or produced

## v3.8 package import

- ZIP SHA256: `43864e357b5b6233196955c6cf9362d34ad9b6d2585f979022194dafa95e3612`.
- The ZIP contained exactly six expected regular files: v3.8 SPEC, four root state documents and run `013`; no absolute path, `..` or symlink was present.
- Imported SPEC SHA256: `81a5ed46c7748c3e1865a8aef46aa7acd5165a589399bbac87d53c46e24f48ef`.
- Imported state validated as `tasks=29 | done=11`, `S0_TEXT_ENCODER=READY`, recommended `S0_TEXT_ENCODER`.

## Correction

- Added `max_seq_length=256` to the frozen scientific config and its hash.
- `_resolve_model_max_length` now hard-fails if tokenizer or transformer physical capacity is below 256 and otherwise returns exactly 256.
- Renamed the dataclass hash to `scientific_config_hash` and separated it from released-file manifests.
- Cache keys now require and bind `tokenizer_manifest_hash`, `encoder_config_manifest_hash` and `scientific_config_hash` independently.
- The exact release has tokenizer/model physical capacities 512/512. Its sentence-transformers config freezes 256.

## Provenance

- Model/revision: `sentence-transformers/all-MiniLM-L6-v2` / `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; resolved revision identical.
- Tokenizer manifest hash: `78a3daa92dcec076e80baaa628a6553bcbd0b431a214eb02d72c8b5672e69e09`.
- Encoder-config manifest hash: `8049791e90383b0f56624a32a14852552e292bcb38ab18da1de533ad79629845`.
- Scientific config hash: `0f2fb795c15c7ad7ee185f44509ec86eb912aaca6abf88b78fa1560179e412af`.
- Loaded `model.safetensors` SHA256: `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
- Encoder-config manifest includes root `config.json`, `sentence_bert_config.json`, `modules.json`, `1_Pooling/config.json` and released `config_sentence_transformers.json`. `2_Normalize/config.json` is absent from the release and is explicitly recorded absent.

## Evidence

- Text CPU evidence: `03_runs/debug_runs/text_encoder_selfcheck_run2026-08-14_014_v38_text_encoder_correction_seed20260813_foldS0-TEXT_methodfrozen-MiniLM-L6-v2_cfg0f2fb795c15c.json`.
- Text evidence SHA256: `1563ca5460af0df44fdbef7d9b86c5b1243b40f227594cc8d3c2b2ab86e82ef0`.
- CPU assertions: `26/26 PASS`; long token counts `962→256`, `truncated=true`; shapes `[1,384]`, `[2,384]`, `[1,384]`; dtype float32; finite L2 norms approximately 1; repeated bytes identical; trainable parameters 0.
- A1 evidence: `03_runs/debug_runs/a1_contract_selfcheck_run2026-08-14_014_v38_text_encoder_correction_seed20260813_foldS0-TEXT_methodA1_cfga9ff618892a2.json`.
- A1 evidence SHA256: `f3240622d55d7721c6f1f7ccbea5f0a935df25fb7c1d8211b7307111db449769`.
- A1 code changed: `false`; A1 assertions `6/6 PASS`; output `[2,384]`.

## Validation

- Frozen encoder focused tests: `19 passed, 0 skipped, 0 failed`.
- A1 focused tests: `7 passed, 0 skipped, 0 failed`.
- Frozen encoder real CPU self-check: `26 passed, 0 skipped, 0 failed`.
- A1 synthetic self-check: `6 passed, 0 skipped, 0 failed`.
- Complete unittest suite before state update: `88 passed, 0 skipped, 0 failed`.
- Final complete suite: `88 passed, 0 skipped, 0 failed`.
- Final project validator: `PROJECT STATE VALID | tasks=29 | done=12`.
- Final status report: `S0_TEXT_ENCODER=DONE`; recommended next task `S0_ROAMM_ADMISSION`.
- Final `git diff --check`: PASS with no output.

## State transition

- `S0_TEXT_ENCODER`: `READY → DONE`.
- Removed `B_TEXT_ENCODER_CONTRACT_MISMATCH`.
- Recommended next task: `S0_ROAMM_ADMISSION`.
- No other task status changed by this correction.
