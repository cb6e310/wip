# Current Handoff

## Current stage

Stage 0: data protocol is structurally complete; experiment protocol remains blocked.

## Completed in run `2026-08-13_008_a3_preparation`

- Added the A3 preparation wrapper, explicit preprocessing contract, channel-map contract, candidate feasibility ledger, and six focused tests.
- Vendored LaBraM-Base checkpoint identity is verified: 96,612,769 bytes and SHA256 `7c50583826afac76c4ab18f43d958df40496c8229acc09ed6a227c9bb57c37c`; code/source and checkpoint upload commits are recorded.
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

Do not run T6/K7, Gate A/B, route lock, or paper-level experiments. Do not use
the A3 synthetic identity map as a real mapping, and do not add a third
backbone.
