# Run R012 — v4.1 R6 inner-selection readiness review

Status: `BLOCKED_R6_EXECUTION_CONTRACT_INCOMPLETE`

- Research timestamp: `2026-08-25T00:05:00+08:00`
- Remote repository: `https://github.com/cb6e310/wip.git`
- Verified remote `main`: `309b70163707c145b9e92a38b41a3ff92cf0f510`
- Governing SPEC: `guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_R6INNER_READY_MAIN_2026-08-25.md`
- Governing SPEC SHA256: `00f2a8fc7c77ba578903249f545e6ace5a622b79ed887fd18a3db07bdc98c8da`
- Contract: `artifacts/eqalign_r6_inner_selection_contract.yaml`
- Preflight commit: `SELF`
- Remote `main` after push: `SAME_AS_SELF`

## Remote facts

The remote branch inventory is `main` plus the five historical R1–R4/rescue
audit refs. No transient remote branch was found. The split reconciliation
commit is on `main`; it created independent R6 `6x3` outer and task-global
`3x3` inner surfaces, preserving the old `6x5` artifacts byte-for-byte. The
remote split selfcheck and five split tests are recorded as PASS.

## Current scientific state

- R6 author freeze: DONE, protocol-only.
- R6 arm/controller/scope/ledger contract: DONE, synthetic tests only.
- R6 split reconciliation: DONE; no EEG values, text encoder, training,
  retrieval, outer-test or calibration rows were read.
- R6 real runner/training/retrieval: ABSENT.
- R6 inner metric: NOT GENERATED.
- Active/future branch: `main`.
- Historical validator provenance remains the R4 branch in `PROJECT_STATE.yaml`;
  this is not the active work branch.

## Newly identified blocker

The author freeze states that alignment optimizer, batch, steps/early-stop,
temperature and related L1 values must be shared, but the repository does not
contain their concrete frozen values. The real OOF probe → 2PL → model-implied
Fisher → `h` contract is likewise not bound to a real runner, including its
probe folds/capacity and ledger schema. The synthetic smoke and synthetic
benchmark defaults are explicitly non-paper and cannot be promoted.

Therefore the next Codex action is a contract preflight. If either contract is
missing, stop with `BLOCKED_R6_EXECUTION_CONTRACT_INCOMPLETE`, record zero EEG
value/text-encoder/training/metric reads, and do not create an empty result. If
both contracts are already author-frozen in the checked-out repository, run only
the inner-selection scope in the accompanying SPEC/contract.

## Scope boundary

Allowed after the gate: new R6 outer-train, inner-train and current
inner-validation reads; frozen MiniLM/A1 inputs; the 4 EQ gamma points, 8 DIRECT
variants, 3 shuffle realizations, and `DIRECT_MATCHED`; pooled inner selection.

Forbidden: old 6x5 split files; held_out_only for fit/selection; outer-test or
calibration reads; synthetic substitutions; new gamma/seed/metric; Gate/A3/ROAMM;
paper-level PASS/FAIL classification; deletion or relabelling of R0–R4 history.

## Codex preflight outcome

The execution gate is blocked. Repository search found only architectural
bounds and shared-recipe requirements, not concrete values bound to a real R6
runner. Synthetic smoke/benchmark defaults and the old A1 loader were excluded
as required.

Present and hash-bound:

- R6 outer/inner/support artifacts and exact 18/9 cell shapes;
- exact MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, weight/config/tokenizer manifests;
- ZuCo dataset root `01_data_protocol/datasets/zuco_2.0` and dataset source manifest.

Missing execution-contract fields:

- exact alignment encoder architecture and parameter count;
- optimizer and parameter groups;
- learning rate and scheduler;
- batch size and deterministic batch-order rule;
- total steps or epochs;
- validation cadence and early-stopping rule;
- InfoNCE temperature;
- real OOF probe architecture/capacity and nested fit-only folds;
- real-runner bindings for normalizer fit scope and `u_oof`/`u_min` definitions;
- amortized 2PL fitting rule/capacity;
- complete RNG stream partition;
- real ledger record-ID schema.

Final contract artifact:

- `artifacts/eqalign_r6_inner_selection_contract.yaml`;
- SHA256 `a03824883e8e11d910cad1d94915c51df4fe072fef5786bd930d496d6f9fbcde`.

Counters and effects:

- `real_eeg_value_reads=0`;
- `text_encoder_reads=0`;
- `training_started=false`;
- `inner_metrics_generated=false`;
- `outer_test_reads=0`;
- `calibration_reads=0`;
- metric outputs created: `[]`;
- cleanup targets removed: `.codex_stage0_a1_admission_v314/`,
  `.codex_stage0_tests/`, `.codex_stage0_scripts/`, `.codex_stage0_src/`,
  `.codex_stage0_artifacts/`, `.codex_stage1_a1r_v318/`,
  `02_code/src/methods/__pycache__/`, and
  `02_code/src/data/__pycache__/`;
- branches deleted: `[]`.
