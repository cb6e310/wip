# Run 018: v3.10 inner review and candidate freeze

- Date: 2026-08-14
- Review baseline: `d4b08308f6f51e4f7ba4256719641461d38bdc68`
- Scope: review and specification/state reconciliation only
- Paper-level outcome access: none
- EEG value access: none
- Training/evaluation: none

## Decision

`S0_INNER_SPLIT=DONE` is admitted and is not reopened. The implementation satisfies the scientific requirements that determine assignment, outer-test isolation, task-global J17 downgrade and reproducibility. Minor engineering notes are retained as nonblocking because they do not alter any identity, fold, trigger or downstream scientific conclusion.

The only recommended next task is ZuCo2-only `S0_CANDIDATES`. ROAMM remains mandatory but deferred until the ZuCo2 method table, thresholds, route and main results are frozen.

## Independently checked evidence

- `scripts/check_project_state.py`: valid; 29 tasks, 13 DONE.
- `scripts/project_status.py`: recommends `S0_CANDIDATES`.
- Focused inner tests: 10/10 passed locally.
- Server run record: complete suite 114/114 passed.
- Outer split SHA256: `20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6`.
- Inner split SHA256: `0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7`.
- Inner support audit SHA256: `536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564`.
- Canonical integrity passed independently for both new artifacts; `validate_inner_artifact` returned no errors.
- 60 task-local outer cells and 540 final inner cells.
- NR: task-global 3x3; minimum provisional item-support median 9.0; 143 provisional partitions triggered; minimum 15 valid outer-train subjects; subject trigger false.
- TSR: task-global 3x3; minimum provisional item-support median 8.0; all 480 provisional partitions triggered; minimum 15 valid outer-train subjects; subject trigger false.
- Subject, stimulus and record isolation from outer test passed; group atomicity, stable hashes, reverse-input determinism and compact lossless record indexing passed.

The local review runtime lacks torch/h5py, so unrelated dependency-bound modules were not rerun locally. This does not block admission: the changed focused suite passed locally, the recorded full server suite passed, and the relevant artifacts and validators were independently checked.

## Accepted nonblocking notes

1. The support audit does not expose a separate public validator.
2. Some root assertions summarize cell-level checks and include expected totals.
3. Record identities use a validated compact index rather than embedding every expanded ID in every cell.

These notes do not affect assignment, leakage isolation, J17 decisions, canonical integrity or reproducibility.

## v3.10 candidate freeze

- Candidate identity is verified source-slot, not text hash.
- Build both outer-test and inner-validation scopes; never borrow train or wrong-scope text.
- Sequential hard filters are target exclusion, inclusive 0.75-to-1.25 exact token-length match, MiniLM cosine greater than 0.9 exclusion, and exact H-full source-identity exclusion.
- No nearest-neighbor length refill, relaxed filter, replacement or silent target deletion.
- Seed 20260813; five SHA256-ranked without-replacement permutations per target; N=10/50/100/200 use 9/49/99/199 negative prefixes from the same ordering.
- Paired verification is derived from the same frozen lists: first negative for 1:1 AUROC and the same 49 negatives for 1:49 AUPRC.
- N=50 passes only if every outer-test and inner-validation target has at least 49 legal negatives.
- If N=50 fails, the candidate audit may still be DONE with `STRUCTURAL_NO_GO_N50`, but leakage remains blocked and no rule changes occur in the same task.

## State transition made by this review

- SPEC: v3.9 -> v3.10.
- `S0_INNER_SPLIT`: remains DONE; review admission metadata added.
- `S0_CANDIDATES`: remains READY and is the unique recommendation; acceptance expanded to the v3.10 frozen contract.
- `B_ZUCO2_CANDIDATE_FEASIBILITY`: retained until the real outer/inner target audit resolves it.
- `B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE`: retained.

No EEG result, retrieval score, Gate decision, route decision or paper conclusion was produced.
