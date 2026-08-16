# Current Handoff

## Current decision

Run `2026-08-16_032_v317_a1_measurement_validity` completed the only SPEC v3.17 execution budget. Its declarative outcome is `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`, so `S0_A1_FAILURE_DIAGNOSIS` remains not-DONE and is blocked for author review. `recommended_next_task=null`; there is no READY task.

The run preserved the admitted v3.14 admission evidence, the v3.15 diagnosis evidence and their implementation/tests byte-identical. All 639 admission plus 58 diagnosis V5 ledgers were revalidated with zero outer-test/calibration reads.

## Frozen run-032 evidence

- D49 added exactly 8 ridge fits/8 unique passing V5 ledgers. NR and TSR each covered the exact 15 disjoint frozen subjects with equal subject weighting and B=10000.
- NR D49 oracle-minus-H logp gain was 4.905433, CI95 `[4.796239,5.017762]`, macro-subject full-vocabulary R@1 `1.0`.
- TSR D49 oracle-minus-H logp gain was 4.716491, CI95 `[4.646393,4.786212]`, macro-subject full-vocabulary R@1 `1.0`.
- Because D49 passed, D50 completed the full frozen 192 ridge fits/192 unique passing V5 ledgers. The complete run has exactly 200 new fits/V5.
- Both tasks had `alpha_family_floor=0.01`, `alpha_legacy_floor=0.03`, and alpha-10 family/legacy detection true.
- Both task curves had eight-point Spearman rho `0.833333`, below the frozen `0.90` minimum. This is the only completion failure and it cannot be repaired by rerun, a larger alpha, a different W/embedding, another seed/fold, a different probe/sham or subject deletion.
- New-run outer-test/calibration reads are `0/0`. Formal outputs contain only aggregate/subject summaries, support, scope, hashes, fits/runtime, floors, rho and outcome.

The admitted v3.14 `FAIL_A1_ADMISSION` remains unchanged. The artificial semantic injection is a construct-validity ruler only; it is not physiological EEG, EEG evidence, Gate evidence or paper performance.

## Sole next action

Stop for author review. A new user-provided governing SPEC is required before any further execution. Do not infer or implement a recovery design from run 032.

## Boundaries

- Do not rerun run 032 or modify its alpha grid, seed, fold, projection, embedding, probe, sham, threshold or subject population.
- Do not modify admitted v3.14/v3.15 artifacts, implementation or tests.
- Do not execute measurement recovery, negative confirmation, outer 6x5, alignment, direct `u+`, EQ-ANMA, Gate, A3 or ROAMM.
- Route remains unchanged: `primary=EQ-ANMA`, `backup=NEGATIVE-DIAGNOSTIC`, `locked=null`. This does not make the failed EQ-ANMA chain admissible.

## Evidence

- SPEC: `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_17_2026-08-16.md`
- Run: `runs/2026-08-16_032_v317_a1_measurement_validity.md`
- Contract: `artifacts/a1_measurement_validity_contract.yaml`
- Audit: `04_results/audits/a1_measurement_validity.json`
- Markdown: `04_results/audits/a1_measurement_validity.md`
- V5 ledger: `04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz`
