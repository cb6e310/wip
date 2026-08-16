# Run 2026-08-15_025: v3.13 ZuCo2 A1 source admission

## Scope

Completed only `S0_A1_SOURCE_ADMISSION` under SPEC v3.13 D32–D34 and Appendix Q.3. No real-source normalizer fit, A-A1–A-A4, probe/sham/model training, unit cost, direct u+, Stage 1, Gate, route, main experiment or ROAMM work was run. No held-out or paper metric was produced.

## Source evidence and outcome

- Outcome: `PASS_REAL_A1_SOURCE`.
- Audited all 36 NR/TSR summary MATs; physical inventory SHA256 `7fc731c4ccd273e12c425ef86cdbd5b02c2546e931ed27aadc7e4b538a30bf86`.
- Audited metadata from all 252 co-released Preprocessed EEG files. Every `EEG.srate` and `automagic.SamplingFrequency` is 500 Hz; official acquisition evidence independently states 500 Hz.
- All 252 files have the same unique ordered 105-label tuple. Tuple SHA256: `23b8d1ee22d87560fe1a6384141b2713c450ca34ef9eeff8241e7bd3bd885ef5`.
- For every summary file, one sentence and one word source matched a unique same-task/same-subject/same-session `Preprocessed/EEG.data` slice exactly across all 105 columns. This binds summary order and unchanged scale to the labelled release source.
- The release does not label a physical amplitude unit. Status is `release_native_amplitude_unit_unlabelled`; no V/µV inference or conversion was made. Future PSD remains native-unit² and normalization may be fit only on outer training.
- A1 finite policy is `reject_any_nonfinite_no_imputation`; no accepted source matrix contained NaN/Inf.

## Coverage and exclusions

- NR: 18/18 retained subjects; 5,915 valid sentence sources, 5,838 at least 500 samples, 122,213 valid word fixation sources.
- TSR: 18/18 retained subjects; 6,588 valid sentence sources, 6,441 at least 500 samples, 109,703 valid word fixation sources.
- Exclusion ledger: 214,496 rows, all explicit release placeholders or missing/dangling references. Reason counts: 1,741 `OBJECT_PLACEHOLDER_1X1`, 212,228 `OBJECT_PLACEHOLDER_OR_DANGLING_REFERENCE`, 527 `WORD_GROUP_OR_RAWeeg_MISSING`.
- G0 passed independently for both tasks: 18 retained subjects each, above the frozen minimum 12.

## Deterministic feature and phase evidence

- Seed `20260813`; stable SHA256 selection chose two sentence and two word sources for every retained task×subject, 144 records total.
- Selection-manifest SHA256 `9c6865cbb2f0eeff2fdd3c72df06b477548d686722e6a86dc3d5ec4dcd71eb75`; concatenated feature-bytes SHA256 `2d2f1b8b185d634323b46d7bdee8a98b08988e705c13d04cafa9af6f86415565`.
- All outputs are finite `float32 [T,840]`; repeat calls are byte-identical.
- Analysis-spectrum phase rotation used demean → Hann → rFFT, preserved magnitude and DC/Nyquist reality, and integrated magnitude² directly with no inverse transform or second Hann. Maximum absolute and relative feature errors were both `0`, within `rtol=1e-5`, `atol=1e-7`.
- Two independent full real builds produced byte-identical formal outputs.

## Formal artifacts

- `artifacts/a1_real_source_contract.yaml`: SHA256 `bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c`.
- `01_data_protocol/a1_source_exclusions.jsonl.gz`: SHA256 `250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c`.
- `04_results/audits/zuco2_a1_source_admission.json`: SHA256 `07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f`.
- A1 config SHA256 after strict-finite binding: `c143e3d85bdc8796f352b046f71e43e68465450f075e143fbac853ffef523edf`.

## Verification

- Focused source mutations and real-artifact checks: 21 passed, 0 skipped, 0 failed (18 mutation/contract tests plus 3 formal-artifact tests).
- A1 frontend contract: 9 passed, 0 skipped, 0 failed.
- Loader/source-join/joint-split/leakage regressions: 38 passed, 0 skipped, 0 failed.
- Total focused: 68 passed, 0 skipped, 0 failed.
- Complete unittest suite: 180 passed, 0 skipped, 0 failed.
- Synthetic A1 self-check: 8/8 assertions passed; output `[2,384]`.

## State transition

- `S0_A1_SOURCE_ADMISSION`: `READY → DONE/PASS_REAL_A1_SOURCE`.
- `S0_A1_ADMISSION`: `BLOCKED → READY`, sole recommended next task.
- `S0_ALIGN_UNIT_COST` remains BLOCKED.
- ROAMM remains deferred until the ZuCo2 main experiment is frozen.
