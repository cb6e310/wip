# trust_align

Research code and frozen specifications for the EEG-Text cross-subject alignment study EQ-ANMA.

## Repository scope

This public repository contains source code, project specifications, audit records, and reproducibility metadata. It does not contain the ZuCo datasets, the local Python environment, generated debug outputs, or pretrained checkpoint binaries. Dataset access and model-weight provenance must be handled according to the relevant original terms.

The current project state is recorded in [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml), with task-level detail in [`TASKS.yaml`](TASKS.yaml) and the latest handoff in [`HANDOFF.md`](HANDOFF.md).

## Status

The project is still in Stage 0 under specification v3.6. The ZuCo2 source-slot join, semantic-item support ledger, deterministic 6x5 joint split, H contract, ANMA-orig reference implementation, and Gate-A subject-population contract pass their current acceptance checks. A1 remains blocked for real-data admission by the verified 128-to-105 map and author-frozen numeric band edges, so Stage 1 and both gates have not started.

A3/LaBraM preparation has an engineering smoke pass. v3.6 clears CO-N7 and treats local frozen inference as a provenance/no-redistribution disclosure rather than a hard rights blocker. A3 is still excluded from T6 until the EGI-128-to-canonical map, raw signal unit, filter order/notch Q, and real mapped MAT extraction pass. CBraMod and REVE-Base remain feasibility candidates only; they are not substitutions for the frozen A3 specification.

## Local setup

Use the environment and data paths described in `02_code/environment/ENVIRONMENT.md`. Run the project-state checks before experiments:

```bash
python scripts/check_project_state.py
python scripts/project_status.py
```
