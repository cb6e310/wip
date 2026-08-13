# trust_align

Research code and frozen specifications for the EEG-Text cross-subject alignment study EQ-ANMA.

## Repository scope

This public repository contains source code, project specifications, audit records, and reproducibility metadata. It does not contain the ZuCo datasets, the local Python environment, generated debug outputs, or pretrained checkpoint binaries. Dataset access and model-weight provenance must be handled according to the relevant original terms.

The current project state is recorded in [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml), with task-level detail in [`TASKS.yaml`](TASKS.yaml) and the latest handoff in [`HANDOFF.md`](HANDOFF.md).

## Status

The project is still in stage 0. A3/LaBraM preparation has an engineering smoke pass but remains blocked for formal use by unresolved contamination attestation, weight/corpus rights, and the frozen EGI-128 to model-channel mapping. CBraMod and REVE-Base are feasibility candidates only; they are not silent substitutions for the frozen A3 specification.

## Local setup

Use the environment and data paths described in `02_code/environment/ENVIRONMENT.md`. Run the project-state checks before experiments:

```bash
python scripts/check_project_state.py
python scripts/project_status.py
```
