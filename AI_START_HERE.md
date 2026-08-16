# AI Project Entry Point

This file is the mandatory entry point for every new AI session. Do not use chat history as project state.

## Verified Project Location

- Server: `song@10.244.144.87`
- Project root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

## Source of Truth

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_12_2026-08-14.md`
2. `guide/EEG_Text_Bprime_Execution_Plan_v3_2026-08-11_to_Submission.md`

SPEC v3.12 controls scientific definitions, the admitted N=10 candidate-common-support scoring population, V1-V5 pre-run leakage contract, claim boundaries and the ZuCo-first execution order. Never edit a scientific rule merely to make a task or Gate pass.

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
- `S0_A1_ADMISSION=READY` is the sole recommended task. Real sentenceData.rawData sampling rate, channel order, units, finite values, field semantics and outer-train-only admission evidence remain hard work inside that task.
- `S0_ALIGN_UNIT_COST` stays blocked until `S0_A1_ADMISSION=DONE`.
- `S0_DIRECT_U_PLUS` remains blocked by Stage-0 execution order; common-support completion is not permission to implement it in the leakage task.
- Never force feasibility with wrong-scope text, length refill, relaxed cosine/H filters, replacement or silent target deletion. Every excluded target remains ledgered.
- ROAMM remains mandatory but deferred until the frozen ZuCo2 main experiment is complete.

## State Discipline

- `READY` requires every prerequisite `DONE` and no active blocker naming the task.
- `DONE` requires existing evidence files and `completed_by_run`.
- Keep current state in `PROJECT_STATE.yaml`, task evidence in `TASKS.yaml`, concise handoff in `HANDOFF.md`, and history in a new `runs/` record.
- Do not begin Gate B before Gate A PASS.
- Do not begin the main experiment before `ROUTE_LOCK=DONE` and one route is locked.
- The registered backup is a negative diagnostic, not CSPE or an outcome-driven dataset switch.

## End-of-Session Contract

After changing state:

1. Update `PROJECT_STATE.yaml` and affected `TASKS.yaml` entries.
2. Replace `HANDOFF.md` with the current concise handoff.
3. Add a unique `runs/YYYY-MM-DD_<id>.md` record.
4. Run `scripts/check_project_state.py`, `scripts/project_status.py`, the relevant tests and `git diff --check`.
5. Commit and push only after all task acceptance conditions pass.
