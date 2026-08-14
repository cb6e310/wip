# v3.8 Text-Encoder Review and ROAMM Freeze

- Run ID: `2026-08-14_013_v38_review_and_roamm_freeze`
- Reviewed repository commit: `bbf8d114a16580451d85a47328ec8b37ec54971a`
- Scope: read-only implementation review, public source-structure audit and SPEC/state reconciliation
- Claim boundary: no EEG values, alignment training, held-out metric, Gate decision or paper result read or produced

## Submitted implementation review

The remote commit exists and correctly implements the frozen MiniLM model/revision, attention-mask mean pooling, L2 normalization, float32 384D output, eval/no-grad/zero-trainable behavior, unified encode interface and A1 `d_align=384` integration. Recorded source/artifact hashes match committed files; `git diff --check` and the project-state validator pass.

Admission is reopened for two protocol defects:

1. The code resolves and self-checks a 512-token limit. The exact revision's `sentence_bert_config.json` and official model card specify default truncation at 256 word pieces.
2. The cache key binds a scientific dataclass hash but not the actual encoder config-file manifest hash.

The submitted server record reports 15/15 text tests, 7/7 A1 tests and 84/84 full tests. The independent review runtime lacks torch and h5py, so its dependency import failures are recorded as environment limitations rather than implementation test failures.

## ROAMM public structure audit

Pinned source: OpenNeuro `ds007629` v1.3.0, tag commit `15c38fd03740ff60008e0e309bf7b53883e2c36d`, DOI `10.18112/openneuro.ds007629.v1.3.0`, CC0.

Git-tree and released coordinate-table checks found:

- 44 subjects with five raw BDF runs each;
- 44 subjects with five synchronized pkl runs each;
- five article coordinate tables with released `word_key`, `sentence_id`, `sentence` and page fields;
- 487 unique sentences total;
- 42 sentence IDs span page boundaries and are globally excluded by the v3.8 main rule;
- 445 single-page sentences remain: history of film 86, Pluto 88, Prisoner's Dilemma 93, Serena Williams 91, Voynich Manuscript 87.

Therefore N=50 is structurally possible within every held-out article before near-duplicate, H-overlap, real fixation and support filtering. It is not yet admitted.

## State transition

- Governing SPEC: v3.7 → v3.8.
- `S0_TEXT_ENCODER`: DONE → READY, reopened for 256/config-manifest correction.
- `S0_ROAMM_ADMISSION`: added as mandatory second-dataset task, waiting on corrected text encoder.
- `S0_INNER_SPLIT`: READY → TODO, waiting on ROAMM admission so split tooling is generalized once.
- TMNRED protocol: BLOCKED → SKIPPED; CSPE removed from this paper's route.
- Recommended next task: `S0_TEXT_ENCODER` only.
