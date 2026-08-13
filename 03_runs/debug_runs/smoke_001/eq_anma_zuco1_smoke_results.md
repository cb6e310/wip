# EQ-ANMA ZuCo 1.0 A1 Smoke Result

Status: `NON_PAPER_SMOKE`. This run only checks that the end-to-end data, spectral front-end, frozen text features, InfoNCE head, and metrics execute on real ZuCo 1.0 data. The numbers are not paper results.

## Run

- Seed: `20260811` (written into the output filename)
- Remote script: `~/projects/trust_algin/02_code/scripts/eq_anma_zuco1_smoke.py`
- Remote result: `~/projects/trust_algin/03_runs/debug_runs/smoke_001/eq_anma_zuco1_smoke_seed_20260811.json`
- Local result: `outputs/eq_anma_zuco1_smoke_seed_20260811.json`
- Device and elapsed time: CUDA, 97.91 s

Command used:

```bash
.venv/bin/python 02_code/scripts/eq_anma_zuco1_smoke.py \
  --dataset-root 01_data_protocol/datasets --task task2_nr \
  --seed 20260811 --output-dir 03_runs/debug_runs/smoke_001 \
  --epochs 20 --proj-dim 128 --text-dim 512 --batch-size 64 \
  --lr 1e-3 --temperature 0.07 --train-fraction 0.8 \
  --num-candidates 10
```

## Result

| Item | Value |
|---|---:|
| Subject files | 12 |
| Sentences seen / kept | 3600 / 3487 |
| Valid word EEG units | 51089 |
| Trial split | 2789 train / 698 test |
| Test unique stimuli | 280 |
| EEG unit shape | `(840,)` = 105 channels x 8 bands |
| Maximum valid word units per trial | 57 |
| Recall@1, N=10 | 0.2607 |
| Paired verification AUROC | 0.8083 |

## Data Definition

The smoke run uses ZuCo 1.0 `task2 - NR` MATLAB files under `01_data_protocol/datasets/zuco_1.0`. A trial is one sentence for one subject. Each word's numeric `rawEEG` fixation segment is an EEG unit; when a word contains multiple fixation matrices, they are concatenated in time. Invalid or missing word segments are skipped, so the sentence sequence contains only valid units and retains sentence order.

The A1 spectral feature is deterministic: 500 Hz sampling rate, Hanning window, zero-padded real FFT, and PSD bin-sum integration over the eight spec bands: theta1 4-6 Hz, theta2 6.5-8 Hz, alpha1 8.5-10 Hz, alpha2 10.5-13 Hz, beta1 13.5-18 Hz, beta2 18.5-30 Hz, gamma1 30.5-40 Hz, gamma2 40-49.5 Hz. The resulting contract is `(T, 105*8)` float32 per trial, with a boolean padding mask at batching time.

For preprocessing, the median, 0.5/99.5% clipping limits, and IQR are fitted using training-fold EEG units only, then applied to all folds. The text side is a frozen `HashingVectorizer` with 512 dimensions. The alignment head is two trainable linear projections with masked mean EEG pooling and symmetric InfoNCE.

## Temporary Simplifications To Replace

1. `task2 - NR` only -> run the spec's complete ZuCo 1.0 task/condition matrix and record task-wise coverage.
2. Trial-level random 80/20 split -> replace with the spec-defined cross-subject/stimulus outer split and fold-local preprocessing.
3. FFT band-power smoke front-end -> implement and verify the spec's fixed-window A1 path plus its 1 s / 0.5 s sensitivity.
4. Masked mean plus two linear projections -> replace with the specified small trainable A1 alignment encoder and its tensor contract checks.
5. Frozen hashing text features -> replace with the selected frozen text/backbone representation used by the main experiment.
6. No Stage-1 measurement -> add sham probes, OOF fold predictions, `u`, `u_min`, `G_k`, ANMA-orig, and EQ-ANMA weighting exactly as specified.
7. One seed, 20 epochs, N=10 -> expand to the preregistered seeds, tuning protocol, candidate sizes, and reporting uncertainty.

The standardization self-check still reports a floor-valued minimum IQR (`1e-6`) and an absolute standardized maximum of `59.8474`, indicating near-constant low-power features in this smoke extraction. This is retained for diagnosis and must be investigated before any paper run; it is not a claim about the method.
