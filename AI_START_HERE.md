# AI Project Entry Point

This file is the mandatory entry point for every new AI session. Do not use chat history as project state.

## Verified Project Location

- Server: `song@10.244.144.87`
- Project root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

## Source of Truth

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_15_2026-08-16.md` (compact governing overlay)
2. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_14_2026-08-16.md` (frozen A1 pilot contract inherited by v3.15)
3. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_13_2026-08-15.md` (unchanged definitions inherited by v3.14/v3.15)
4. `guide/EEG_Text_Bprime_Execution_Plan_v3_2026-08-11_to_Submission.md`

SPEC v3.15 author-admits the execution-valid `FAIL_A1_ADMISSION`, terminates the original EQ-ANMA admission chain, and freezes one construct-validity diagnosis before a possible full ZuCo2 negative-confirmation panel. v3.14 controls the completed A-A1 through A-A4 pilot; v3.13 controls every unchanged scientific definition, V1-V5 contract, A1 phase role, claim boundary and ZuCo-first order. Never edit a scientific rule merely to make a task or Gate pass.

## Required Recovery Sequence

Read, in order:

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. Relevant guide sections

Then run:

```bash
.venv/bin/python scripts/check_project_state.py
.venv/bin/python scripts/project_status.py
```

Before implementation print:

```text
PROJECT SNAPSHOT

Current stage:
Current route:
Completed prerequisites:
Active blockers:
Ready tasks:
Recommended next task:
Why:
Do not do yet:
```

If state and SPEC disagree, report `STATE_SPEC_CONFLICT` and stop rather than guessing.

## Current Boundary

- Commits `711340d` and `e42b3bf` are admitted: `S0_CANDIDATES=DONE/STRUCTURAL_NO_GO_N50` and `S0_CANDIDATE_COMMON_SUPPORT=DONE/PASS_N10_COMMON_SUPPORT`. Neither task may be reopened.
- The immutable audit covers 18,475 target instances. N=50 is structurally unavailable, but 17,061/18,475 (92.35%) have at least nine legal negatives.
- v3.12 keeps N=10 primary on the per-scope common-support population `legal_count>=9`; this is a scoring-population restriction, never a training-record deletion.
- The common-support artifacts retain all 18,475 target instances, freeze the 17,061 eligible N=10 scoring instances and ledger all 1,414 exclusions. Their large duplicated JSON is an admitted nonblocking efficiency issue; do not compact, delete, regenerate or modify them.
- `S0_LEAKAGE_AUDIT=DONE/PASS_PRE_RUN_V1_V5`. V1-V4 passed on immutable real protocol artifacts; V5 is only `PASS_PRE_RUN_CONTRACT`, with `future_run_admission_required=true` and `real_training_ledgers_audited=0`.
- `d9dfe51442155fbd3854d223916c519a7757fff1` is admitted without rework; its leakage artifacts and state transition are valid.
- `S0_A1_SOURCE_ADMISSION=DONE/PASS_REAL_A1_SOURCE`. All 36 summary MATs and 252 Preprocessed EEG files passed the 500 Hz, exact ordered 105-label, D34 native-unlabelled stable-scale, strict-finite, identity, G0 and deterministic 840D source contracts; the three formal artifacts reproduce byte-identically.
- `6cffbb68477d92463565c65024a164a40e68e840` is admitted without rework. Its 72 source links establish exact `min(20,T) x 105` prefix matches; do not overstate them as whole-array equality and do not reopen the source task for this nonblocking wording note.
- `31164dc3d70b00fb383862f88b6404bd616db696` is execution-valid and admitted without protocol repair. The four formal hashes reproduce, the gzip has 639 unique V5 ledgers, and outer-test/calibration reads are zero.
- `S0_A1_ADMISSION=FAILED/FAIL_A1_ADMISSION`. The frozen NR/TSR pilot completed all 639 fits and V5 ledgers: both tasks fail raw/latent A-A1 and raw/latent A-A3, while A-A2 and A-A4 pass. Significant-negative A-A1 conditions are present. This is a scientific admission failure, not a source/runtime/V5 failure, and it never becomes DONE.
- For A1 bandpower, phase rotation on the exact demeaned-and-Hann windowed rFFT analysis spectrum is a required invariance diagnostic, not a strong sham, `u_min` member or phase-only No-Go. Pre-window phase randomization also changes the analysis-spectrum magnitude and is not a phase-only matched null. The v3.13 identifiable strong family is trial shuffle, within-trial unit-assignment shuffle and channel-block permutation.
- `S0_A1_FAILURE_DIAGNOSIS=BLOCKED/INVALID_A1_FAILURE_DIAGNOSIS`. All 58 fits/58 V5 ledgers completed with zero outer-test/calibration reads. Both A-A3 oracle controls pass; both scorer numerical criteria pass, but the frozen single inner_s0_t0 validation scope provides only 5 scoring subjects per task, not the required 15-subject paired bootstrap.
- `S0_ALIGN_UNIT_COST`, `STAGE1_PROBES`, `S0_DIRECT_U_PLUS`, `S0_EQ_ANMA_CORE`, both Gates, route lock and the original main experiment remain blocked by the failed admission.
- `recommended_next_task=null`. `B_A1_FAILURE_DIAGNOSIS_INVALID_AUTHOR_REVIEW` blocks the diagnosis, `S0_A1_NEGATIVE_CONFIRMATION_FREEZE` and `S1_A1_NEGATIVE_CONFIRMATION`; do not freeze or start the full 6x5 panel.
- Never force feasibility with wrong-scope text, length refill, relaxed cosine/H filters, replacement or silent target deletion. Every excluded target remains ledgered.
- The A1-admission fixed-window path receives no outcome-driven word mapping and cannot be used to rescue the failed admission.
- The preflight may inspect contracts, shapes, hashes, memory and runtime only. It cannot be used to change the frozen ridge/logistic probes, shams, cells, seeds, support or thresholds; a fit over 300 seconds blocks.
- ROAMM remains mandatory but deferred until the frozen ZuCo2 first-dataset package is complete.
- Do not change the backbone, probes, shams, cells, seeds, thresholds or dataset in response to `FAIL_A1_ADMISSION`. The current author-approved exception is only the explicit oracle positive-control input in SPEC v3.15 D42; it must never enter an EEG result or method.
- Do not resolve the invalid diagnosis by treating 5 subjects as 15, scoring outside the registered validation scope, borrowing across inner cells, increasing the exact four scorer fits, or weakening CI/R@1. A new author-approved SPEC/state package is required.

## State Discipline

- `READY` requires every prerequisite `DONE` and no active blocker naming the task.
- `DONE` requires existing evidence files and `completed_by_run`.
- Keep current state in `PROJECT_STATE.yaml`, task evidence in `TASKS.yaml`, concise handoff in `HANDOFF.md`, and history in a new `runs/` record.
- Do not begin Gate B before Gate A PASS.
- Do not begin the main experiment before `ROUTE_LOCK=DONE` and one route is locked.
- The only permitted post-failure direction is a negative diagnostic, not CSPE or an outcome-driven dataset/backbone switch.

## End-of-Session Contract

After changing state:

1. Update `PROJECT_STATE.yaml` and affected `TASKS.yaml` entries.
2. Replace `HANDOFF.md` with the current concise handoff.
3. Add a unique `runs/YYYY-MM-DD_<id>.md` record.
4. Run `scripts/check_project_state.py`, `scripts/project_status.py`, the relevant tests and `git diff --check`.
5. Commit and push only after all task acceptance conditions pass.
