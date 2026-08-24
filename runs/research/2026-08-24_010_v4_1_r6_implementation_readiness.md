# Run R010 — v4.1 R6 implementation readiness review

Status: `DONE`

- Research timestamp: `2026-08-24T21:35:00+08:00`
- Remote repository: `https://github.com/cb6e310/wip.git`
- Target branch: `main`
- Verified remote `main`: `125d72c9aad1dd2d3777d695123f17dc97138268`
- Parent freeze commit: `0a140bafabf9ec489547dda002f7613cafdfa4db`
- Verified historical R4 branch: `e80862e943b9fbff7f5788dc109eefbf2c27a476`
- Implementation commit: `SELF`
- Remote `main` after push: `SAME_AS_SELF`
- Prepared governing SPEC SHA256: `e6bc63c134bc7136516521beed7519e34982278e06cd576e17f9e204f6cc5fbe`
- Final implementation contract SHA256: `e8b4942bfb1a9fa25db6196d36a0f74d592f1759b11e7e216a4641e3c7518544`

## State transition

The previous Codex task `R6_AUTHOR_FREEZE_ON_MAIN` is committed and pushed.
The freeze artifact and SPEC SHA are bound; the author-approved release remains
blocked for all real experiment work until implementation and tests complete.
The current task is `R6_IMPLEMENT_ARMS_AND_TESTS` on `main`.

## Repository research

Present implementation surfaces:

- `02_code/src/methods/eq_anma.py` — legacy V0/V1/V2 measurement/Fisher module;
- `02_code/src/methods/direct_u_plus.py` — legacy v3.13 direct-u+ weighting;
- synthetic benchmark/data generators and their tests;
- existing ZuCo loaders and historical R0–R4 diagnostic modules.

Missing R6 surfaces:

- bounded `clip(1+gamma*h, 0.2, 3.0)` controller;
- exact 8-variant R6 DIRECT adapter;
- `DIRECT_MATCHED` and `EQ_SHUFFLE` arm adapters;
- fit-only scope guard and outer-read counter;
- compute-matching ledger/schema/hash contract;
- R6 contract self-check and T-01…T-09 adversarial tests;
- real R6 runner, real training loop, retrieval loop, and outer pipeline.

The implementation task must add only the protocol-level surfaces listed in
the governing SPEC §G.1. It must not consume real EEG, instantiate a real
runner, alter historical code/artifacts, or emit metrics.

## Validation of the post-freeze remote state

- `python scripts/check_project_state.py`: `PASS`.
- `python scripts/project_status.py`: `VALID`.
- `git diff --check`: `PASS`.
- Four-file `python -m compileall -q`: `PASS`.
- Pytest: not available in the runtime (`BLOCKED_ENV_NO_PYTEST`); no dependency installed.
- Real EEG reads: `0`.
- Outer-test reads: `0`.
- Calibration reads: `0`.
- `TASKS.yaml`: unchanged.
- R0–R4 formal SHA recheck: `PASS`.

## Implementation completion

Codex added only the six protocol modules, T-01…T-09 synthetic/adversarial
tests, and standalone selfcheck authorized by SPEC §G. No real loader, runner,
training or retrieval pipeline, outer/calibration output, or held-out metric
was added or executed.

- `r6_contract_selfcheck.py`: `PASS (9/9)`.
- `pytest test_eqalign_r6_contracts.py`: `PASS (9 passed)`.
- `compileall`: `PASS`.
- `check_project_state.py`: `PASS`.
- `project_status.py`: `VALID`.
- `git diff --check`: `PASS`.
- Real EEG / outer-test / calibration reads: `0 / 0 / 0`.
- `TASKS.yaml`: unchanged (`919c86e80a5f6cd8fab0d44bede6f090f52e96cb8c87d6f9fb781137dfa2adb0`).
- R0–R4 formal SHA recheck: `PASS`.
- Branches deleted: `[]`.
- Transient cleanup: `__pycache__/`, `*.pyc`, `.pytest_cache/`,
  `/tmp/r6_selfcheck_r010.txt`.

The only next task is `R6_INNER_SELECTION`. Real EEG, outer/calibration, Gate,
A3, ROAMM, and paper-level work remain blocked.
