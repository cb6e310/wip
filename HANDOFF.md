# Current Handoff

## Current stage

Stage 0: data protocol is structurally complete; experiment protocol remains blocked.

## Reconciled in run `2026-08-13_009_state_reconciliation`

- Restored the active ZuCo2 reference-exclusion and material-identity-join blockers recorded by the completed data-card audit.
- Replaced the stale TMNRED data-card blocker with a residual experiment-protocol blocker; both structural data-card tasks remain `DONE` and `experiment_ready=false`.
- Preserved the A3 engineering-preparation evidence and corrected its Handoff checkpoint hash from the authoritative file digest.
- No scientific specification, threshold, fold, seed, candidate set, null, model parameter, data exclusion, or task completion status was changed.

## Validated evidence retained

- ZuCo2: 36/36 summary files and 504/504 raw inventory records PASS; 18 complete subjects; NR 349 and TSR 390 sentence slots; structural data card complete, experiment protocol unresolved.
- TMNRED: 30 subjects, eight sessions each, 240 event files, 11,991 rows, 50 stimuli; structural self-check 10/10 PASS; incomplete cell, license and split policies unresolved.
- A3: wrapper, preprocessing and channel-map contracts, candidate feasibility ledger, and six focused tests are present.
- Vendored LaBraM-Base checkpoint identity is verified: 96,612,769 bytes and SHA256 `7c50583826afac76c4ab18f43d958df40496c8229accc09ed6a227c9bb57c37c`; code/source and checkpoint upload commits are recorded.
- Official release pooling/load semantics are implemented: `use_mean_pooling=true`, `init_values=0.1`, `qkv_bias=false`, expected pretraining/finetuning key differences allow-listed, no gradients, and no re-pooling outside the model.
- The continuous ZuCo2 raw inventory is verified across all 252 files: 128 channels at 500 Hz, stable `E1..E128` order. The separate 105-channel summary files are explicitly excluded from A3 input.
- The engineering candidate smoke passes the 500-to-200 preprocessing shape, 5 s / 2.5 s windows, pooled 200D output, finite values, unchanged weights, and required runtime module checks. Filter order/Q remain explicitly unfrozen.
- CBraMod and REVE-Base are recorded as contingency feasibility candidates only. The guide-frozen A3 route and no-third-backbone rule are unchanged.

## Evidence files

- `04_results/audits/a3_contamination_check.md`
- `artifacts/a3_backbone_feasibility.yaml`
- `artifacts/a3_channel_contract.yaml`
- `03_runs/debug_runs/a3_labram_preparation_seed20260813_foldA3-contract-1_methodA3-LaBraM-Base-preparation_cfg1546c94a5e8d.json`
- `02_code/src/backbones/a3_labram.py`
- `02_code/scripts/a3_preparation_audit.py`
- `02_code/tests/test_a3_contract.py`

## Still blocked

- ZuCo2 source-verified 128-to-105 map, A1 PSD/window/unit convention, reference exclusions, material identity join, semantic item, joint split, candidate lists, and leakage audit.
- TMNRED incomplete-cell/session policy, CC0 versus CC BY 4.0 discrepancy, joint split, candidate policy, and leakage audit.
- CO-N7 contamination exclusion needs a corpus manifest or author attestation covering the opaque self-collected EEG portion.
- Checkpoint and pretraining-corpus rights remain unknown; MIT code licensing is not sufficient evidence.
- Raw MAT channel geometry is absent. An author-approved EGI128-to-LaBraM canonical name map or spatial mixing matrix, coverage, and hash are required.
- Real EEG MAT preprocessing and mapped extraction have not been validated. The synthetic identity positions in the smoke are not semantic evidence.
- A3 remains excluded from T6/K7 until those conditions are resolved. CBraMod/REVE-Base cannot be substituted without a guide-level author decision.

## Recommended next task

`S0_H_DEFINITION`, followed by explicit author decisions for the semantic item,
reference exclusion, material identity join, channel map, A1 PSD recipe, and
joint split.

## Do not do yet

Do not treat either structural data card as experiment-ready. Do not run T6/K7,
Stage 1, Gate A/B, route lock, or paper-level experiments. Do not use the A3
synthetic identity map as a real mapping, and do not add a third backbone.
