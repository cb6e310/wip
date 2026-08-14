# Current Handoff

## Current stage

Stage 0 remains `IN_PROGRESS` under SPEC v3.8. No ROAMM admission, inner split, candidate construction, Stage-1 probe, Gate A/B, route lock, EEG training, held-out evaluation or paper-level experiment ran in the text-correction task.

## Active `2026-08-14_015_v38_roamm_admission` checkpoint

- The two ignored v3.8 text self-check evidence files were hash-verified, archived in the separate pushed commit `3457b6a3592bd75cf1b0312d6818047c66d3f537`, and left scientifically unchanged.
- ROAMM exact v1.3.0 source/tree metadata and all five coordinate files pass the frozen structural counts: 44×5 raw/synced inventory, 10,839 coordinate rows, 487 sentences, 42 cross-page exclusions and 445 single-page sentences (`86/88/93/91/87`).
- Strict full-audit code and 16 offline focused tests are implemented. The background transfer of all 220 synced PKLs is still running; no sample-based support result is accepted as complete.
- Checkpoint artifacts are marked `IN_PROGRESS_DOWNLOAD`, `experiment_ready=false`. `S0_ROAMM_ADMISSION` is not DONE, `B_ROAMM_NOT_ADMITTED` remains active, and `S0_INNER_SPLIT` remains TODO.
- Resume by waiting for the verified 220/220 PKL transfer, downloading and hashing the one frozen representative BDF, then run the audit script in `--mode full`. Do not start inner split, candidates, direct `u+`, A1 real admission, training or Gates.

## Completed in `2026-08-14_014_v38_text_encoder_correction`

- `S0_TEXT_ENCODER` is corrected and readmitted. The exact model/revision, attention-mask mean pooling, L2, float32 384D, eval/no-grad, zero-trainable and shared encode interface from `bbf8d11` are retained.
- The sentence-transformers contract is now explicitly `max_seq_length=256`, sourced from exact-revision `sentence_bert_config.json`; tokenizer and transformer physical capacities are separately verified as 512 and 512 and may not raise the scientific limit.
- Cache keys bind exact UTF-8 text SHA256, model ID, revision, tokenizer manifest hash `78a3daa9...e09`, encoder-config manifest hash `8049791e...845`, scientific config hash `0f2fb795...2af`, pooling and normalization.
- The encoder-config manifest covers `config.json`, `sentence_bert_config.json`, `modules.json`, `1_Pooling/config.json` and the released `config_sentence_transformers.json`; `2_Normalize/config.json` is absent from this release and recorded as absent. Module order and mean-only pooling were verified.
- Real CPU self-check passed 26/26: long input 962→256, `truncated=true`, shapes remain `[1,384]`/`[2,384]`, finite L2 norms are approximately 1, repeated bytes are identical, and trainable parameters are 0.
- A1 code and hyperparameters were not changed. A1 focused tests passed 7/7 and the new regression self-check passed 6/6 with output `[2,384]`.
- Text focused tests passed 19/19 and the complete suite passed 88/88 before the final state update.

## Current critical path

1. `S0_ROAMM_ADMISSION` — recommended next task; not implemented in this run.
2. `S0_INNER_SPLIT` — waits for ROAMM structural admission.
3. `S0_CANDIDATES`, A1 real-source admission and full leakage audit.
4. Stage 1 / Gate A only after all protocol artifacts pass.

## Residual blockers

- ROAMM ds007629 v1.3.0 has not been admitted in the repository.
- No dataset-local inner split artifacts exist.
- Target-level N=50 feasibility and shared candidate/paired-verification artifacts do not exist.
- A1 real `sentenceData.rawData` source admission has not passed.
- A3 canonical channel mapping and real extraction remain unresolved.

## Claim boundary

The corrected text-encoder engineering contract and unchanged A1 384D synthetic regression pass. There are no ROAMM/EEG/held-out/paper-level results and no Gate conclusion.

## Do not do yet

Do not combine ROAMM admission with this completed correction record. Do not start inner split, candidates, direct `u+`, A1 real admission, Stage 1, Gate A/B, route lock or training.
