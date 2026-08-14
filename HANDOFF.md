# Current Handoff

## Direction and stage

Stage 0 remains `IN_PROGRESS` under SPEC v3.9. ZuCo 2.0 NR/TSR must be completed and frozen before ROAMM resumes as the mandatory external replication panel. This ordering does not change any scientific threshold or remove ROAMM.

## Current verified state

- Repository base before this task: `502a92f5de1a984e999ea8692b59ad9fd9e6d8bd`.
- `S0_TEXT_ENCODER=DONE`, `S0_JOINT_SPLIT=DONE`, and `S0_SEMANTIC_ITEM=DONE` remain unchanged.
- `S0_INNER_SPLIT=DONE` by run `2026-08-14_017_v39_zuco2_inner_split`.
- The real ZuCo2 builder verified the frozen outer artifact SHA256 `20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6`, both panel input hashes, the source-slot identity, the official semantic predicate, and 143,055 positive item observations.
- All 60 outer cells exist. J17 independently selected task-global 3x3 for both panels: NR minimum provisional item-support median 9.0, TSR 8.0; both had minimum outer-train subject count 15, so the subject trigger did not fire.
- Two independent real builds were byte-identical. The split artifact SHA256 is `0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7`; the support audit SHA256 is `536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564`.
- Focused tests passed 10 inner, 8 joint-split, and 5 semantic-item tests. The complete suite passed 114 tests with no skip or failure.

## ROAMM checkpoint remains paused and not admitted

The project-specific downloader was positively identified and stopped with SIGTERM only. At stop, 172/220 PKLs were complete and four `.part` files remained. No partial file, manifest, log, or verified download was deleted. `B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE` still blocks only `S0_ROAMM_ADMISSION`; `experiment_ready=false` remains the claim boundary.

## Next task

`S0_CANDIDATES` is now `READY` and is the only recommended next task. Build only the frozen ZuCo2 unseen-stimulus candidate feasibility and paired-verification artifacts. Do not use outer-train text, cross-article borrowing, relaxed filters, replacement, or silent target deletion to force N=50.

## Do not do yet

Do not resume ROAMM, run A1 real admission, Stage 1, EEG training, retrieval evaluation, Gate A/B, route lock, or paper-level held-out analysis as part of the candidate task. The admitted inner artifacts are protocol infrastructure, not OOF or paper evidence. Cross-dataset replication and paper completion remain blocked until the deferred ROAMM panel is finished.
