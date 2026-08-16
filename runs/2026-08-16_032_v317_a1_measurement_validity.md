# Run 032 — v3.17 A1 measurement-validity audit

- Date: 2026-08-16
- Task: `S0_A1_FAILURE_DIAGNOSIS`
- Baseline: `ffd2369663eb7a0f069f75726b34a46b7e3808ad`
- SPEC: `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_17_2026-08-16.md` D49-D52
- Outcome: `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`
- Claim boundary: construct-validity measurement audit only. Artificial injection is not physiological EEG, EEG evidence, Gate evidence or paper performance.

## Immutable preflight

- All 17 frozen v3.14/v3.15 artifact, implementation, test and run-record hashes matched.
- Revalidated 639 admission plus 58 diagnosis V5 ledgers: 697/697 unique, zero outer-test reads, zero calibration reads.
- Real admitted A1 observations were loaded from the existing hash-bound cache: NR `[48347,840]`, TSR `[45392,840]`, finite float32, 15 subjects each.
- Frozen MiniLM resolved revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Projection seed: `6749993717453156489`; W contract: little-endian float32 `[840,384]`, C-order SHA256 `dba2ad5e50eb0379a9d5dec29dc3c1af0138d4a36871012d1ee8ffba9e8dba58`. W itself was not saved.
- Canonical frozen item-vector mapping SHA256: `8d871e30c41781fab484f52c8516c8842c52c7d872ed70d2e2b29ca762a0dbe7`.

## D49 — 15-subject amendment

Exactly 8 new ridge fits and 8 unique passing V5 ledgers were created. The immutable s0 subject summaries were combined with the new s1/s2 summaries; each task covered exactly 15 pairwise-disjoint frozen subjects with equal subject weights and B=10000.

| Task | gain estimate | CI95 | positive subjects | macro full-vocabulary R@1 | Result |
|---|---:|---:|---:|---:|---|
| NR | 4.905433 | [4.796239, 5.017762] | 15/15 | 1.0 | PASS |
| TSR | 4.716491 | [4.646393, 4.786212] | 15/15 | 1.0 | PASS |

D49 passed, so D50 was required and was run in full.

## D50 — frozen graded semantic-injection curve

Exactly 192 new ridge fits and 192 unique passing V5 ledgers were created: 2 tasks x 3 frozen `s*_t0` cells x 8 alphas x 4 arms. All alpha-zero train/validation inputs were canonical-byte identical to their uninjected normalized A1 arrays. All four arms were constructed from the same injected input via the inherited deterministic sham constructor.

| Task | family floor | legacy floor | Spearman rho | alpha-10 family | alpha-10 legacy | Result |
|---|---:|---:|---:|---|---|---|
| NR | 0.01 | 0.03 | 0.833333 | true | true | FAIL rho < 0.90 |
| TSR | 0.01 | 0.03 | 0.833333 | true | true | FAIL rho < 0.90 |

The exact subject-first `u_oof` point-estimate curves were:

- NR: `[-0.013363, 0.254415, 1.662237, 3.945989, 4.792468, 4.957246, 4.866750, 4.614712]` for alphas `[0,.01,.03,.1,.3,1,3,10]`.
- TSR: `[-0.032893, 0.212832, 1.552811, 3.856245, 4.767316, 4.940499, 4.852299, 4.617461]` for the same frozen grid.

Both rho values are below the pre-frozen 0.90 minimum. No rerun, grid expansion, alternative projection/embedding, seed/fold/probe/sham change or subject deletion is authorized.

## Counts, reads and runtime

- New fits: 200 ridge = 8 D49 + 192 D50.
- New V5: 200/200 unique passing ledgers.
- Old V5 revalidated: 697/697.
- Outer-test/calibration reads: 0/0.
- Maximum single fit: 0.328877 seconds; summed fit runtime: 22.757819 seconds; total runner elapsed: 193.915 seconds.
- No W, EEG array, observation vector, logit, model parameter or cache was committed.

## Formal artifact hashes

- `artifacts/a1_measurement_validity_contract.yaml`: `4c09d484cc1b09d7b1215fbf70c442ba8aaaaea57cd5ef42a66a5b25f99118b6`
- `04_results/audits/a1_measurement_validity.json`: `89d4dc7ac9b4925f60db4fdc12a059f426bd453764db685827f5ed83b4fef270`
- `04_results/audits/a1_measurement_validity.md`: `f7b84125d56cd0e8816374d0e15ec6228b0fc52d69bc9e812e60e213d2e7ac61`
- `04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz`: `4cc1d14acd8c93e834a96146f63460bc8d6d231a61f8fde6549ec319fd6fc638`

## Verification

- Focused pre-run: 10 passed, 3 skipped because real v3.17 artifacts did not yet exist.
- Focused post-run: 13 passed.
- Related admission + diagnosis + measurement-validity: 46 passed, 4 subtests passed.
- Full pytest: 226 passed, 28 subtests passed.
- Python compile: passed for the three new implementation/test files.
- `scripts/check_project_state.py`: `PROJECT STATE VALID | tasks=35 | done=17`.
- `scripts/project_status.py`: VALID, no READY task, recommended next task none.
- `git diff --check`: passed.

## State transition

- `S0_A1_FAILURE_DIAGNOSIS`: `READY -> BLOCKED`; it is not DONE.
- Added `B_A1_MEASUREMENT_VALIDITY_INVALID` for author review.
- `recommended_next_task=null`; no task is READY.
- Route remains unchanged: `primary=EQ-ANMA`, `backup=NEGATIVE-DIAGNOSTIC`, `locked=null`.
- `S0_A1_ADMISSION` remains `FAILED/FAIL_A1_ADMISSION`.
- Measurement recovery, negative confirmation, alignment, direct `u+`, EQ-ANMA, Gate, A3 and ROAMM were not run.
