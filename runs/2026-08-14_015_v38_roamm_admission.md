# v3.8 ROAMM Admission — Download Checkpoint

- Run ID: `2026-08-14_015_v38_roamm_admission`
- Seed: `20260813`
- Fold: `S0-ROAMM`
- Method: `ROAMM-structural-admission`
- Status at this checkpoint: `IN_PROGRESS_DOWNLOAD`
- Baseline: `3457b6a3592bd75cf1b0312d6818047c66d3f537`
- Claim boundary: source/structure/support engineering only; no alignment training, EEG-to-text metric, retrieval result, held-out evaluation, Gate result or paper conclusion was produced

## Text-evidence prerequisite

The two v3.8 text-encoder self-check JSON files were found with their frozen SHA256 values, force-added individually without changing the directory ignore, committed separately as `3457b6a3592bd75cf1b0312d6818047c66d3f537`, and pushed before ROAMM work began.

## Exact sources

- OpenNeuro dataset/version: `ds007629` / `1.3.0`.
- Snapshot commit: `15c38fd03740ff60008e0e309bf7b53883e2c36d`.
- DOI/license: `10.18112/openneuro.ds007629.v1.3.0` / `CC0`.
- Official GraphQL snapshot manifest SHA256: `20f02d614b9d18d774920037153141fb2a90eee6ce3dbec76bdce0ab9a30e4b3`.
- Normalized exact-tree manifest hash: `bca0df219672db1c6340d677a1be931e7f0d1b248d0ab46cc4b0ed0686752d55`.
- Author-code repository/commit: `https://github.com/GlassBrainLab/roamm_ml` / `77702115a8ff31f659363619b1baf2d9dae1a533`.
- Author-code tree: `8f1f7ca25ac68845e45bbe1dac60d92c5481ef18`.
- `notebooks/create_roamm.ipynb` SHA256: `4cb4f00b7c4140d41aac49896f45630294edbc1d7152f0a517b634210596455b`.

## Completed without the bulk download

- Exact tree inventory: 44 participants, 220 raw BDF, 220 synced PKL, 220 raw-eye and 220 log entries.
- Four participants lack a flowsheet (`10073`, `10138`, `10145`, `10188`); this is recorded as an auxiliary anomaly and does not silently exclude them.
- Five coordinate files pass the frozen contract: 10 pages/story, 10,839 rows, globally unique non-empty word keys, 487 unique sentences, 42 cross-page exclusions, and 445 single-page sentences distributed `86/88/93/91/87`.
- Structural negative upper bounds are `85/87/92/90/86`; full N=50 feasibility remains delegated to `S0_CANDIDATES`.
- Implemented deterministic inventory, coordinate, exact-join, trial, item, support, `is_mw` isolation, outer-train selector, PKL schema/statistics and representative-BDF audit code.
- Offline focused tests pass `16/16`.
- Metadata-only audit completed with `63/220` synced PKLs present and size-matched at the captured checkpoint; the downloader continues separately with per-file size/SHA256 verification.

## Commands and checkpoint results

1. `.venv/bin/python -m unittest discover -s 02_code/tests -p 'test_roamm_admission.py' -v` — `16 passed, 0 skipped, 0 failed`.
2. `.venv/bin/python 02_code/scripts/audit_roamm_admission.py ... --mode metadata` — metadata/coordinate assertions PASS; overall `IN_PROGRESS_DOWNLOAD`.
3. Complete unittest suite — `104 passed, 0 skipped, 0 failed`.
4. `.venv/bin/python scripts/check_project_state.py` — `PROJECT STATE VALID | tasks=29 | done=12`.
5. `.venv/bin/python scripts/project_status.py` — PASS; recommended next task remains `S0_ROAMM_ADMISSION`.
6. `git diff --check` — PASS after LF normalization of `HANDOFF.md`.

## State boundary

`S0_ROAMM_ADMISSION` remains incomplete, `B_ROAMM_NOT_ADMITTED` remains active, and `S0_INNER_SPLIT` remains TODO. The generated data card, artifact and feasibility JSON are explicitly marked `IN_PROGRESS_DOWNLOAD` / `experiment_ready=false`; they are not admission evidence until the strict full audit reads and validates all 220 PKLs plus the representative BDF.
