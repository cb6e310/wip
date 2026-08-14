# Run 2026-08-14_017_v39_zuco2_inner_split

## Scope

Implemented only SPEC v3.9 Appendix M.4 `S0_INNER_SPLIT` for ZuCo 2.0 NR/TSR. No candidate construction, ROAMM admission, A1 admission, probe, training, retrieval, held-out paper metric, Gate, or paper conclusion was run.

## Recovery and state-package import

- Base and `origin/main`: `502a92f5de1a984e999ea8692b59ad9fd9e6d8bd`.
- Initial worktree was clean; no unknown user modifications were present.
- Imported the six-file v3.9 package after verifying SHA256 `dbab350239e0ffa0397e42c8b7a7281b57d1fc25d211dfa68f396050ff5c8d18` and rejecting unsafe/archive-extra conditions.
- Initial state validation: `PROJECT STATE VALID | tasks=29 | done=12`; recommended task `S0_INNER_SPLIT`.
- The project ROAMM downloader PID 2414156 and four direct curl children were identified by full command, cwd, and ds007629 path, then stopped with SIGTERM only. Stop state: 172/220 complete PKLs and four `.part` files retained; no manifest, log, partial, or completed file was deleted.

## Inputs and hashes

- Seed: `20260813`.
- Outer artifact SHA256: `20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6`.
- Outer panel input hashes: NR `1a6a46c27e36a9613e2c0e34708af5d4d2892521429dfbda28c5276b9497d476`; TSR `b1bb58dd7c3bae3dbb9d6361ee046b948e4113c3c09fcfd066bf5d1a478f8a32`.
- Semantic config hash: `a20eda60450e31e6e4aa790672a3efa2900fd8a517640a409fef4320c333360c`.
- Semantic source manifest hash: `c3ce71ddb56b5aed0066d35ce635c88f89144ea063031ed9d387be5325aba43f`.
- Dataset source manifest hash: `31e38d255f80c3c14c2f00b74cde649afb986999f7285a7a8fc8ceee2972f74f`.
- Official reader SHA256: `90e3bab7d082891b4b53fcb154286d8a73eea0f3fa89a312176025f035cfa71c`.
- Positive observation ledger: 143,055 tuples; canonical SHA256 `a10f1ef00fdc67054e70c884c371feb38e687216183d59ea864cb932a254b580`; EEG values were not embedded.

## J17 result and artifacts

- NR: task-global 3x3. Minimum outer-train subject count 15; subject trigger false. Minimum provisional inner-train item-support median 9.0; item trigger true.
- TSR: task-global 3x3. Minimum outer-train subject count 15; subject trigger false. Minimum provisional inner-train item-support median 8.0; item trigger true.
- 60 outer cells and 540 final inner cells passed exact outer-train coverage, Cartesian partition, atomic-group, and outer-test record/subject/stimulus isolation assertions.
- Exact record IDs are stored once per outer cell; partition record sets use lossless zero-based indices into that frozen table and are resolved back to exact IDs by validation. This keeps the canonical artifact below GitHub's single-file limit without changing any assignment.
- `01_data_protocol/splits/zuco_2_0_inner_folds.json`: 38,203,238 bytes; SHA256 `0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7`.
- `04_results/audits/zuco2_inner_split_support.json`: 160,892 bytes; SHA256 `536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564`.
- Two independent real-source builds produced byte-identical split and audit files. One earlier non-counted attempt completed validation but failed to write an incorrectly shell-expanded `/inner.json`; it made no repository write and was not used as evidence.

## Tests

- Inner focused: 10 passed, 0 skipped, 0 failed.
- Joint-split focused: 8 passed, 0 skipped, 0 failed.
- Semantic-item focused: 5 passed, 0 skipped, 0 failed.
- Complete unittest suite: 114 passed, 0 skipped, 0 failed.

## State transition

- `S0_INNER_SPLIT`: READY to DONE.
- Removed `B_INNER_SPLIT_NOT_IMPLEMENTED`.
- `S0_CANDIDATES`: BLOCKED to READY.
- `recommended_next_task`: `S0_CANDIDATES`.
- Preserved `B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE`.
