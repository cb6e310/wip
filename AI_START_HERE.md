# AI Project Entry Point

This file is the mandatory entry point for every new AI session working on this project. Do not use chat history as project state.

## Verified Project Location

- Server: `song@10.244.144.87`
- Project root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

Use `trust_align` consistently in commands, state records and run notes.

## Source of Truth

Scientific definitions, thresholds and experiment rules come only from:

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_9_2026-08-14.md`
2. `guide/EEG_Text_Bprime_Execution_Plan_v3_2026-08-11_to_Submission.md`

SPEC v3.9 controls scientific definitions, claim boundaries and the author-approved ZuCo-first execution order. The execution plan controls the lightweight schedule and evidence-grade use of Gate A/B. Never edit either merely to make a task or Gate pass.

## Required Recovery Sequence

Before doing any work, read in this order:

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. Relevant sections of the two guide files

Then run:

```bash
.venv/bin/python scripts/check_project_state.py
.venv/bin/python scripts/project_status.py
```

Before implementation, print this exact shape with values recovered from files:

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

If repository state disagrees with the guide, report `STATE_SPEC_CONFLICT`. Block on missing facts rather than guessing.

## v3.9 Execution Boundary

- Finish and freeze the full ZuCo 2.0 NR/TSR main experiment before resuming ROAMM.
- `S0_ROAMM_ADMISSION` is deliberately blocked by `B_ROAMM_DEFERRED_UNTIL_ZUCO2_FREEZE`; this is a scheduling deferral, not dataset removal.
- Preserve the incomplete run-015 ROAMM checkpoint and verified partial files with `experiment_ready=false`.
- ROAMM is not a prerequisite for ZuCo inner split, candidates, leakage, Gate A/B, route lock or main experiment.
- ZuCo results must not determine whether ROAMM runs or change its frozen protocol. No cross-dataset claim is allowed until ROAMM finishes.
- ZuCo-only `S0_INNER_SPLIT` is complete. Current recommended task is `S0_CANDIDATES`; do not combine it with training, A1 admission or ROAMM work.

## State Discipline

Allowed task states are `TODO`, `READY`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `FAILED`, `SKIPPED` and `TERMINATED`.

- A task may be `READY` only when every prerequisite is `DONE` and no active blocker names it.
- `DONE` requires existing evidence files and `completed_by_run`; code existence alone is not validation.
- Keep `PROJECT_STATE.yaml` short and current. History belongs in `runs/`.
- Keep `HANDOFF.md` concise and distinguish implemented from validated.
- Gate thresholds and held-out decisions must never change after seeing results.
- Do not begin Gate B before Gate A has a valid passing outcome.
- Do not begin the main experiment before `ROUTE_LOCK` is `DONE` and one route is locked.
- This paper executes EQ-ANMA only; the registered backup is a negative diagnostic, not CSPE or a post-outcome dataset switch.

## End-of-Session Contract

Before ending any session that changed project state:

1. Update `PROJECT_STATE.yaml`.
2. Update affected entries in `TASKS.yaml`.
3. Replace `HANDOFF.md` with a concise current handoff.
4. Append a new, never-reused `runs/YYYY-MM-DD_<id>.md` record.
5. Run `.venv/bin/python scripts/check_project_state.py`.
6. Run `.venv/bin/python scripts/project_status.py` and confirm its recommendation matches the evidence.
