# Current Handoff

## Current stage

Stage 0 remains `IN_PROGRESS` under SPEC v3.7. No Stage-1 probe, Gate A/B, route lock, EEG training, held-out evaluation, or paper-level experiment was authorized or run.

## Completed in `2026-08-14_012_v37_text_encoder`

- The frozen text-encoder engineering contract is `PASS`: `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` resolved exactly and was loaded on CPU through `transformers.AutoTokenizer`/`AutoModel`.
- The one public encode path uses last-hidden-state attention-mask mean pooling, L2 normalization, explicit float32 384D output, eval/no-grad and zero trainable parameters. Cache keys bind exact UTF-8 text SHA256, model ID, revision, tokenizer hash, config hash, pooling and normalization.
- Real CPU admission passed 19/19 assertions: short `[1,384]`, padding batch `[2,384]`, long `[1,384]`, finite norms approximately 1, byte-identical repeated encoding, and truncation 1730 to 512 tokens. Model/tokenizer/config provenance hashes are frozen in `artifacts/text_encoder_freeze.yaml`; weights remain outside the repository.
- A1 default `d_align` is now 384. The new synthetic A1 contract rerun passed 6/6 with output `[2,384]`; PSD, bands, windows, normalization, other network hyperparameters and parameter ceiling were unchanged.
- Focused tests passed 15/15 for the text encoder and 7/7 for A1; the full suite passed 84/84.

## Current critical path

1. `S0_INNER_SPLIT` — READY and recommended; it has not been implemented.
2. `S0_CANDIDATES` — BLOCKED until the inner split exists and per-target N=50 feasibility is verified.
3. A1 real-source admission and the full leakage audit.
4. Stage 1 / Gate A only after all protocol artifacts pass.

`S0_DIRECT_U_PLUS` remains independently READY but was not implemented in this run.

## Residual blockers

- No inner split artifact inside each outer cell.
- Candidate N=50 remains unverified per target after all legal filters; no shared candidate or paired-verification artifacts exist.
- A1 real `sentenceData.rawData` admission has not passed: sampling rate, channel order, units, finite values and field semantics remain unverified end to end.
- A3 canonical channel mapping and real extraction remain T6-only blockers.
- TMNRED experiment protocol remains unresolved for the supplementary panel only.

## Claim boundary

The text-encoder engineering contract and A1 384D synthetic contract pass. A1 real-data admission does not pass. There are no EEG or paper-level results and no Gate conclusion.

## Do not do yet

Do not treat outer split PASS as nested OOF readiness. Do not construct candidates or force N=50 before the inner split and feasibility ledger. Do not run Stage 1, Gate A/B, route lock, T6 real extraction, EEG training, or main experiments.
