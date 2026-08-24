# Real-vs-sham R3 subject-balanced inner diagnostic

- Run: `2026-08-24_005_v324_real_sham_r3_subject_balanced_inner`
- Outcome: `FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC`
- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`
- Passing task scope: `[]`
- Ridge operations / V5 ledgers: `60/60`
- H-only / EEG probe fits: `12/48`
- Outer-test/calibration reads: `0/0`

| Task | Method | Role | seen semantic | seen family | cross semantic | cross family | recovery | pass |
|---|---|---|---:|---|---:|---|---:|---|
| task1_nr | P0_OBSERVATION_WEIGHTED | baseline_replication | 0.0454847 | True | 0.0389076 | False | n/a | False |
| task1_nr | P1_SUBJECT_ITEM_BALANCED | sole_candidate | 0.0477367 | False | -0.127937 | False | -0.166845 | False |
| task2_tsr | P0_OBSERVATION_WEIGHTED | baseline_replication | 0.00155238 | False | 0.0182842 | False | n/a | False |
| task2_tsr | P1_SUBJECT_ITEM_BALANCED | sole_candidate | 0.0562844 | False | -0.0404971 | False | -0.0587813 | False |

P1 is the only candidate. P0 is an immutable observation-weighted baseline replication.

P1 groups were created only from supported fit rows. Subject identity was used only as a grouping key and was never a probe input. Seen/cross rows remained unchanged individual observations.

Both semantic single-sham contrasts, legacy three-sham contrast, channel-block sentinel, u_oof/u_min, seen/cross, support, retention, and group-size summaries are retained.

Parent/R0/R1/R2 outcomes and formal artifacts are immutable. No F3, Y1, M1, outer confirmation, calibration, direct u+, EQ-ANMA, A3, ROAMM, or Gate was run.

Stop for author review. No outer confirmation was started.
