# Run 2026-08-14_022 — v3.12 common-support review and leakage freeze

## Scope

Reviewed remote commit `e42b3bf5233c0226dbaf225fc1eeab0c46acc331`, admitted its completed N=10 common-support task, corrected the Stage-0 dependency state machine and froze the next Codex task as pre-run V1-V5 leakage audit. This author revision did not edit implementation/artifacts, run EEG, train a model or inspect held-out performance.

## Review verdict

`S0_CANDIDATE_COMMON_SUPPORT=DONE/PASS_N10_COMMON_SUPPORT` is admitted. The implementation is JSON-only, validates the immutable base triplet, preserves all target/exclusion identities, derives the first-nine prefix and paired 1:1/1:9 views deterministically, and reports `training_records_removed=0`.

Exact evidence:

- outer NR 306/349, TSR 359/390, total 665/739; minimum 60/70;
- inner NR 7,553/8,376, TSR 8,843/9,360, total 16,396/17,736; minimum 77/93;
- overall 17,061/18,475; 1,414 exclusions; transition length/cosine/H = 1,402/0/12;
- derived SHA256: `b3eda1c09542344e108ce162a0f414beb54a426644db18126ee1e87e36ddf097`, `71b6b53e5686e125d067240fd6414b833ef74b46159b130d5c6097152d722771`, `6dfba054d8242501808e267f91efdf080f6cbd479b617819edb4baf47554c0fc`.

The three derived JSON files total about 59.9 MB and duplicate ledger information. This is admitted as a nonblocking engineering-efficiency note: correctness and reproducibility pass, so no further Codex quota will be spent compacting or regenerating them.

## Verification

- Server run record: common-support 8/8, candidate 15/15, full suite 138/138.
- Independent review: common-support 8/8 and candidate 15/15 pass; physical hashes, exact counts, deterministic rederivation, project-state validation and diff check pass.
- Independent full-suite attempt was not used as a blocker because this review environment lacks the repository's ML dependencies and a system `/tmp`; the real focused artifact tests and the server full suite provide the relevant evidence.

## Scientific/state decisions

1. V1-V4 will audit the current real subject/record, stimulus/material, H and candidate/common-support artifacts.
2. V5 will implement an executable run-ledger validator. Since no real EEG/training run exists, the only valid current V5 result is `PASS_PRE_RUN_CONTRACT`, with every future run requiring revalidation.
3. Removed the self-circular `B_A1_REAL_SOURCE_ADMISSION`. `S0_A1_ADMISSION` now explicitly depends on common-support and leakage; its real MAT/source checks remain task-local hard acceptance requirements.
4. `S0_ALIGN_UNIT_COST` now depends on completed A1 admission and cannot start early.

## Next task

Only `S0_LEAKAGE_AUDIT` is READY/recommended. On PASS it becomes DONE with `PASS_PRE_RUN_V1_V5`, and `S0_A1_ADMISSION` becomes READY/recommended. No A1, unit cost, direct u+, Stage 1, Gate, route/main experiment or ROAMM work is included in the leakage task.
