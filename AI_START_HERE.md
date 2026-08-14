# AI Project Entry Point

This file is the mandatory entry point for every new AI session. Do not use chat history as project state.

## Verified Project Location

- Server: `song@10.244.144.87`
- Project root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`

## Source of Truth

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_10_2026-08-14.md`
2. `guide/EEG_Text_Bprime_Execution_Plan_v3_2026-08-11_to_Submission.md`

SPEC v3.10 controls scientific definitions, candidate construction, claim boundaries and the ZuCo-first execution order. Never edit a scientific rule merely to make a task or Gate pass.

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

- `S0_INNER_SPLIT=DONE` is admitted after review of commit `d4b0830`.
- `S0_CANDIDATES=DONE` with `completion_outcome=STRUCTURAL_NO_GO_N50`; the three canonical artifacts are admitted protocol evidence.
- The complete audit retained 18,475 outer-test/inner-validation target instances; 18,184 have fewer than 49 legal negatives, so frozen N=50 cannot proceed.
- `B_ZUCO2_N50_STRUCTURAL_NO_GO` blocks leakage and downstream method implementation pending `AUTHOR_REVIEW_N50_PROTOCOL`.
- `recommended_next_task=null`: no automated engineering or experiment task is authorized until a future author-approved SPEC revision resolves the protocol.
- Never force feasibility with wrong-scope text, length refill, relaxed cosine/H filters, replacement, target deletion or an unapproved N change.
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
