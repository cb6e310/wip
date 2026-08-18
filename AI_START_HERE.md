# AI Project Entry Point

This file is the mandatory entry point for every new AI session. Do not use chat history as project state.

## Project

- Root: `/home/song/projects/trust_align`
- Python: `/home/song/projects/trust_align/.venv/bin/python`
- Baseline remote commit: `d10446537b3e6cb460abc652100a3978eabc0a3c`

## Source of truth

1. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_20_2026-08-16.md` — synthetic EQ-ANMA method-validity overlay
2. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_19_2026-08-16.md` — inherited real A1 outer negative/transfer confirmation
3. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_18_2026-08-16.md` — immutable A1-R recovery
4. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_17_2026-08-16.md` — immutable measurement-validity audit
5. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_14_2026-08-16.md` — immutable A1 admission
6. `guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_13_2026-08-15.md` — inherited method/fairness definitions

Never change a scientific rule to make a task pass.

## Startup

Read `PROJECT_STATE.yaml`, `HANDOFF.md`, `TASKS.yaml`, then the relevant SPEC. Run:

```bash
.venv/bin/python scripts/check_project_state.py
.venv/bin/python scripts/project_status.py
```

Print the project snapshot. If state/SPEC disagree, report `STATE_SPEC_CONFLICT` and stop.

## Immutable facts

- Real ZuCo2+A1 admission is `FAILED/FAIL_A1_ADMISSION`; real alignment, direct weighting, EQ-ANMA and Gate B are not admitted.
- Run 032 remains `INVALID_A1_MEASUREMENT_VALIDITY_AUDIT`, with bounded interpretation `MEASUREMENT_PATH_DETECTS_INJECTED_SIGNAL_WITH_SATURATION`.
- Commit `d104465` run 034 is admitted as valid `FAIL_A1R_RECOVERY`: 78 fits/V5, 100% row retention, zero outer/calibration reads, no selected frontend.
- SPEC v3.19 freezes a later real 324-fit A1 negative/TSR-T8 transfer panel. It remains READY and unchanged.
- A3 and ROAMM have not failed; they remain unfinished independent real-data routes.

## Current recommended task

Only execute `S1_EQ_ANMA_SYNTHETIC_BENCHMARK` in the current Codex task. `S1_A1_NEGATIVE_CONFIRMATION` is also READY but must not run concurrently in the same working tree/task.

The synthetic benchmark uses no real EEG or real outer-test metric. Exact scope is 192 scenarios, 4,800 measurement ridge fits, 7,104 alignment fits and 11,904 unique passing synthetic V5 ledgers. It must implement the reusable direct-u-plus and EQ-ANMA modules, the structured-Fisher regime, the direct-friendly monotone regime and byte-identical alpha-zero controls exactly as SPEC v3.20 D73–D79.

True generator `a/b/q/I/stable-mask` values are forbidden method inputs. Hyperparameters select on synthetic selection populations only; synthetic final-test subjects/items are read once. No outcome may be called real EEG evidence, Gate B, real retrieval performance or a real alpha threshold.

## Execution discipline

- Safely import the complete v3.19+v3.20 control bundle before implementation.
- Prefer existing W, sham, ridge, V5, ANMA and statistic helpers; keep old behavior/tests compatible.
- Preflight is contract/runtime only and may not read the formal final-test curve.
- Run focused, related and full tests, compile, state/status and `git diff --check`.
- For any legal PASS/MECHANISM_ONLY/FAIL/INVALID outcome, follow SPEC v3.20 exactly, update state/handoff/run record, commit and push.
- After any valid non-INVALID outcome, recommend `S1_A1_NEGATIVE_CONFIRMATION`; never release real Gate/alignment.
