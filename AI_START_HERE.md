# AI Project Entry Point

This file is the mandatory entry point for every new AI session working on this project.
Do not use chat history as project state.

## Verified Project Location

- Server: `song@10.244.144.87`
- Project root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

The project directory is `trust_align` on the server. Use this path consistently in
commands, state records, and run notes.

## Source Of Truth

Scientific definitions, thresholds, and experimental rules come only from:

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_8_2026-08-14.md`
2. `guide/EEG_Text_Bprime_Execution_Plan_v3_2026-08-11_to_Submission.md`

The unified spec controls scientific definitions and claim boundaries. The execution
plan controls the current lightweight schedule and evidence-grade use of Gate A/B.
Never edit either file merely to make project state or a gate pass.

## Required Recovery Sequence

Before doing any work, read in this order:

1. `PROJECT_STATE.yaml`
2. `HANDOFF.md`
3. `TASKS.yaml`
4. The sections of the guide files relevant to the requested task

Then run:

```bash
.venv/bin/python scripts/check_project_state.py
.venv/bin/python scripts/project_status.py
```

Before implementation, print this exact shape with values recovered from the files:

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

If repository state disagrees with the guide, report `STATE_SPEC_CONFLICT`. Block on
missing facts instead of guessing.

## State Discipline

Allowed task states are `TODO`, `READY`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `FAILED`,
`SKIPPED`, and `TERMINATED`.

- A task may be `READY` only when every prerequisite is `DONE` and no active blocker
  names it.
- `DONE` requires existing evidence files and `completed_by_run`; code existence alone
  is not evidence of validation.
- Keep `PROJECT_STATE.yaml` short and current. History belongs in `runs/`.
- Keep `HANDOFF.md` short and explicitly distinguish implemented from validated.
- Gate thresholds and held-out decisions must never be changed after seeing results.
- Do not begin Gate B before Gate A has a valid passing outcome.
- Do not begin the main experiment before `ROUTE_LOCK` is `DONE` and one route is locked.
- This paper executes EQ-ANMA only; the registered backup is a negative diagnostic, not CSPE or a post-outcome dataset switch.

## End-Of-Session Contract

Before ending any session that changed project state:

1. Update `PROJECT_STATE.yaml`.
2. Update affected entries in `TASKS.yaml`.
3. Replace `HANDOFF.md` with a concise current handoff.
4. Append a new, never-reused `runs/YYYY-MM-DD_<id>.md` record.
5. Run `.venv/bin/python scripts/check_project_state.py`.
6. Run `.venv/bin/python scripts/project_status.py` and confirm its recommendation is
   consistent with the evidence.
