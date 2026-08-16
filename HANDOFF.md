# Current Handoff

## Current decision

`S0_A1_SOURCE_ADMISSION=DONE/PASS_REAL_A1_SOURCE` under run `2026-08-15_025_v313_a1_source_admission`. All 36 ZuCo2 summary MATs and all 252 co-released Preprocessed EEG files passed the frozen source-field, 500 Hz, exact ordered 105-channel, stable native-unlabelled scale, strict finite, source-slot identity and G0 contracts. The source contract, exclusion ledger and audit were rebuilt independently and are byte-identical.

The A1 frontend now rejects any NaN/Inf without imputation. Bands, Hann-periodogram, nFFT, windows, stride, 840D order, normalization formula, encoder and `d_align=384` are unchanged. The 144-record real smoke was deterministic finite float32 `[T,840]`; analysis-spectrum phase rotation had zero observed feature error within the frozen tolerance.

## Required next action

Run only `S0_A1_ADMISSION`, now the sole READY/recommended task. Execute the frozen A-A1 through A-A4 outer-training admission checks under SPEC v3.13 D32, using only the three identifiable strong A1 shams and treating analysis-spectrum phase rotation solely as the admitted invariance diagnostic.

Do not start unit-cost measurement, direct u+, Stage 1, Gates, route/main experiment or ROAMM in the same task. Source PASS is not A1 signal/model admission and is not a Gate or paper result.

## Evidence boundary

- Formal artifact SHA256: contract `bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c`; exclusion ledger `250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c`; audit `07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f`.
- Ordered 105-label tuple SHA256: `23b8d1ee22d87560fe1a6384141b2713c450ca34ef9eeff8241e7bd3bd885ef5`; summary physical inventory SHA256: `7fc731c4ccd273e12c425ef86cdbd5b02c2546e931ed27aadc7e4b538a30bf86`.
- NR retained 18/18 subjects with 5,915 valid sentence sources and 122,213 valid word fixations; TSR retained 18/18 with 6,588 and 109,703. The 214,496 exclusions are explicit release placeholders/missing references; no accepted matrix contained NaN/Inf.
- Focused tests: 68/68; complete unittest suite: 180/180; 0 skipped, 0 failed.
- No normalizer was fit on real source data; no A-A1–A-A4 probe, sham/model training, held-out metric, Gate, route, main experiment or ROAMM work was run.
