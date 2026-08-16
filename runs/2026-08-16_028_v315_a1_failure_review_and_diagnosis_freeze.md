# Run 2026-08-16_028_v315_a1_failure_review_and_diagnosis_freeze

## Scope

Author-level review of pushed commit `31164dc3d70b00fb383862f88b6404bd616db696`, its frozen v3.14 A1-admission artifacts, implementation, V5 ledgers, tests and state transition. No EEG model, positive control, outer-test metric, alignment, Gate, route lock, A3 or ROAMM execution was performed in this review.

## Independent verification

- `origin/main` resolves to `31164dc`; the commit changes only the expected A1 implementation, formal outputs and project-memory files.
- The four formal SHA256 values reproduce exactly: contract `c9c5a94...d9f4b`, audit JSON `b3d2b47...e151e`, audit Markdown `e187f23...29a8e`, V5 ledger `fe22b69...963fd`.
- The gzip ledger decodes to 639 rows and 639 unique fit IDs: 9 preflight, 486 A-A1, 36 A-A2 and 108 A-A3. Every row has empty outer-test-read and calibration lists.
- New Python files pass bytecode compilation; `git diff --check` and `scripts/check_project_state.py` pass. The server run records focused 21/21, related 96/96 and full 201/201 tests, 0 skipped/failed.
- The review container lacks `torch`, so its local focused unittest import stops at the missing dependency. This is recorded as a local environment limitation, not converted into a repository failure or an invented test pass.
- Code audit found no blocking defect in split scope, outer-train extraction, sham axes/derangements, common four-arm rows, fold-local normalization/support/clusters, frozen latent, ridge/logistic probes, subject-first statistics, completion logic or real V5 generation. A duplicated identical dictionary key in the V5 builder is a harmless style detail and is not reopened under the user's audited-tolerance instruction.

## Frozen result

`FAIL_A1_ADMISSION` is valid as a scientific admission outcome. Both NR/TSR fail raw and latent A-A1 and A-A3; A-A2 and A-A4 pass. Every task/basis has significantly negative `u_min`; NR raw also has significantly negative `u_oof`. Channel-block permutation is the strongest observed sham in all four task/basis summaries. This pilot is not Stage 1, Gate A, held-out evidence or a paper conclusion.

## Author decision

- Mark `S0_A1_ADMISSION=FAILED/FAIL_A1_ADMISSION`; never mark it DONE or release the original EQ-ANMA training chain.
- Do not tune thresholds, substitute shams/backbones/cells/seeds/dataset, or use the result to revive fixed-window/A3/ROAMM work.
- Run one bounded construct-validity task next: `S0_A1_FAILURE_DIAGNOSIS`. It adds an A-A3 item-embedding oracle positive control and an A-A1 ridge scorer oracle positive control, revalidates the admitted hashes/V5 ledgers, and performs no new judged EEG comparison.
- If all positive controls pass, direction changes to a separately frozen ZuCo2 full 6×5 negative-confirmation panel. The immediate next step is the no-outcome pre-run specification freeze, not the outer run itself. It does not continue EQ-ANMA/direct-weighting experiments because incremental EEG evidence was not admitted.

## State transition prepared by SPEC v3.15

- governing spec: v3.15;
- `S0_A1_ADMISSION=FAILED/FAIL_A1_ADMISSION`;
- `S0_A1_FAILURE_DIAGNOSIS=READY` and sole recommended task;
- original alignment/Stage-1/Gate/route/main chain remains blocked; diagnosis PASS may release only `S0_A1_NEGATIVE_CONFIRMATION_FREEZE`, not the outer run;
- ROAMM remains deferred;
- no paper-level claim is authorized.
