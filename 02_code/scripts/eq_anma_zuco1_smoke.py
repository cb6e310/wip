#!/usr/bin/env python3
"""Reproducible ZuCo 1.0 A1 spectral-feature alignment smoke test.

The data definition is deliberately explicit:
  * task2 - NR (normal reading), one MAT file per subject;
  * one trial is one sentence for one subject;
  * each valid word rawEEG segment is one EEG unit;
  * each unit is converted to 105 channels x 8 band-power features;
  * the alignment head uses masked mean pooling and two linear projections.

This is a NON_PAPER smoke run. It uses a trial-level random split, one seed,
N=10 retrieval, and no Stage-1 sham/OOF/ANMA weighting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import scipy.io as sio
import torch
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics import roc_auc_score
from torch import Tensor, nn
from torch.nn.utils.rnn import pad_sequence


FS = 500.0
N_CHANNELS = 105
BANDS = (
    ("theta1", 4.0, 6.0),
    ("theta2", 6.5, 8.0),
    ("alpha1", 8.5, 10.0),
    ("alpha2", 10.5, 13.0),
    ("beta1", 13.5, 18.0),
    ("beta2", 18.5, 30.0),
    ("gamma1", 30.5, 40.0),
    ("gamma2", 40.0, 49.5),
)
TASK_DIR = {"task2_nr": "task2 - NR"}
TASK_SUFFIX = {"task2_nr": "NR"}


@dataclass
class Trial:
    subject_id: str
    stimulus_id: str
    trial_id: str
    sentence: str
    eeg_units: np.ndarray
    valid_word_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--task", choices=tuple(TASK_DIR), default="task2_nr")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("smoke_runs"))
    parser.add_argument("--proj-dim", type=int, default=128)
    parser.add_argument("--text-dim", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--num-candidates", type=int, default=10)
    parser.add_argument("--max-trials", type=int, default=0)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.dataset_root.exists():
        raise RuntimeError(f"BLOCKER: dataset root does not exist: {args.dataset_root}")
    if not 0.0 < args.train_fraction < 1.0:
        raise RuntimeError("BLOCKER: --train-fraction must be strictly between 0 and 1")
    if args.seed < 0:
        raise RuntimeError("BLOCKER: --seed must be non-negative")
    if args.proj_dim < 1 or args.text_dim < 1:
        raise RuntimeError("BLOCKER: projection/text dimensions must be positive")
    if args.epochs < 1 or args.batch_size < 2:
        raise RuntimeError("BLOCKER: epochs must be positive and batch size at least 2")
    if args.lr <= 0.0 or args.temperature <= 0.0:
        raise RuntimeError("BLOCKER: learning rate and temperature must be positive")
    if args.num_candidates < 2:
        raise RuntimeError("BLOCKER: --num-candidates must be at least 2")
    if args.max_trials < 0:
        raise RuntimeError("BLOCKER: --max-trials must be non-negative")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False


def find_subject_files(dataset_root: Path, task: str) -> list[Path]:
    directory = dataset_root / "zuco_1.0" / TASK_DIR[task] / "Matlab files"
    suffix = TASK_SUFFIX[task]
    files = sorted(directory.glob(f"results*_{suffix}.mat"))
    if not files:
        raise RuntimeError(f"BLOCKER: no MATLAB subject files found under {directory}")
    return files


def as_sentence_array(value: object) -> np.ndarray:
    array = np.asarray(value, dtype=object).reshape(-1)
    if array.size == 0:
        return array
    return array


def orient_epoch(value: object) -> np.ndarray | None:
    array = np.asarray(value)
    if array.dtype == object:
        elements = [np.asarray(item) for item in array.reshape(-1)]
        matrices = []
        vectors = []
        for element in elements:
            if element.ndim == 2:
                matrices.append(element)
            elif element.ndim == 1 and element.size:
                vectors.append(element)
        if matrices:
            parts = [orient_epoch(item) for item in matrices]
            parts = [item for item in parts if item is not None]
            if parts:
                return np.concatenate(parts, axis=1)
        if len(vectors) == N_CHANNELS:
            return np.stack(vectors, axis=0)
        return None
    if array.ndim != 2 or array.size == 0:
        return None
    if array.shape[0] == N_CHANNELS:
        return array
    if array.shape[1] == N_CHANNELS:
        return array.T
    return None


def spectral_unit(epoch: np.ndarray) -> np.ndarray | None:
    if epoch.shape[0] != N_CHANNELS or epoch.shape[1] < 8:
        return None
    x = np.asarray(epoch, dtype=np.float64)
    finite_fraction = float(np.isfinite(x).mean())
    if finite_fraction < 0.95:
        return None
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    x -= x.mean(axis=1, keepdims=True)
    window = np.hanning(x.shape[1])
    if not np.any(window):
        return None
    n_fft = max(512, 1 << int(math.ceil(math.log2(x.shape[1]))))
    spectrum = np.fft.rfft(x * window[None, :], n=n_fft, axis=1)
    frequencies = np.fft.rfftfreq(n_fft, d=1.0 / FS)
    psd = (np.abs(spectrum) ** 2) / (FS * float(np.sum(window**2)))
    frequency_step = float(frequencies[1] - frequencies[0])
    features = []
    for _name, low, high in BANDS:
        mask = (frequencies >= low) & (frequencies < high)
        if not np.any(mask):
            features.append(np.zeros(N_CHANNELS, dtype=np.float32))
        else:
            # Bin-sum integration remains nonzero when a short epoch has one bin in a band.
            features.append((np.sum(psd[:, mask], axis=1) * frequency_step).astype(np.float32))
    return np.stack(features, axis=1).reshape(-1)


def load_trials(dataset_root: Path, task: str, max_trials: int) -> tuple[list[Trial], dict[str, int]]:
    trials: list[Trial] = []
    counters = {"subjects": 0, "sentences_seen": 0, "sentences_kept": 0, "words_seen": 0, "words_kept": 0}
    for subject_file in find_subject_files(dataset_root, task):
        subject_id = subject_file.stem.split("_")[0].replace("results", "")
        data = sio.loadmat(subject_file, squeeze_me=True, struct_as_record=False).get("sentenceData")
        if data is None:
            raise RuntimeError(f"BLOCKER: sentenceData missing in {subject_file}")
        counters["subjects"] += 1
        for sentence_index, sentence_data in enumerate(as_sentence_array(data)):
            counters["sentences_seen"] += 1
            sentence = str(getattr(sentence_data, "content", "")).strip()
            words = as_sentence_array(getattr(sentence_data, "word", []))
            units = []
            for word in words:
                counters["words_seen"] += 1
                epoch = orient_epoch(getattr(word, "rawEEG", np.array([])))
                if epoch is None:
                    continue
                unit = spectral_unit(epoch)
                if unit is None or not np.isfinite(unit).all():
                    continue
                units.append(unit)
                counters["words_kept"] += 1
            if not sentence or not units:
                continue
            counters["sentences_kept"] += 1
            trials.append(
                Trial(
                    subject_id=subject_id,
                    stimulus_id=f"{task}:sentence_{sentence_index:04d}",
                    trial_id=f"{subject_id}:{task}:{sentence_index:04d}",
                    sentence=sentence,
                    eeg_units=np.stack(units).astype(np.float32),
                    valid_word_count=len(units),
                )
            )
            if max_trials and len(trials) >= max_trials:
                return trials, counters
    if len(trials) < 2:
        raise RuntimeError("BLOCKER: fewer than two valid sentence trials were extracted")
    return trials, counters


def fit_robust_standardizer(trials: list[Trial], train_idx: np.ndarray) -> tuple[list[Trial], dict[str, float]]:
    train_units = np.concatenate([trials[int(index)].eeg_units for index in train_idx], axis=0)
    median = np.median(train_units, axis=0)
    q_low, q_high = np.quantile(train_units, [0.005, 0.995], axis=0)
    clipped = np.clip(train_units, q_low, q_high)
    iqr = np.quantile(clipped, 0.75, axis=0) - np.quantile(clipped, 0.25, axis=0)
    iqr = np.maximum(iqr, 1e-6)
    transformed = []
    for trial in trials:
        values = np.clip(trial.eeg_units, q_low, q_high)
        normalized = ((values - median) / iqr).astype(np.float32)
        transformed.append(
            Trial(
                subject_id=trial.subject_id,
                stimulus_id=trial.stimulus_id,
                trial_id=trial.trial_id,
                sentence=trial.sentence,
                eeg_units=normalized,
                valid_word_count=trial.valid_word_count,
            )
        )
    stats = {
        "train_feature_median_abs_max": float(np.max(np.abs(median))),
        "train_iqr_min": float(np.min(iqr)),
        "train_iqr_max": float(np.max(iqr)),
        "all_standardized_abs_max": float(max(np.max(np.abs(t.eeg_units)) for t in transformed)),
    }
    return transformed, stats


def make_text_features(sentences: list[str], text_dim: int) -> np.ndarray:
    vectorizer = HashingVectorizer(
        n_features=text_dim,
        alternate_sign=False,
        norm="l2",
        lowercase=True,
        token_pattern=r"(?u)\b\w+\b",
    )
    return vectorizer.transform(sentences).toarray().astype(np.float32)


class AlignmentHead(nn.Module):
    def __init__(self, input_dim: int, text_dim: int, proj_dim: int, temperature: float) -> None:
        super().__init__()
        self.eeg_projection = nn.Linear(input_dim, proj_dim)
        self.text_projection = nn.Linear(text_dim, proj_dim)
        self.temperature = temperature

    def encode_eeg(self, padded: Tensor, mask: Tensor) -> Tensor:
        projected = self.eeg_projection(padded)
        weights = mask.unsqueeze(-1).to(projected.dtype)
        return nn.functional.normalize((projected * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0), dim=-1)

    def encode_text(self, text: Tensor) -> Tensor:
        return nn.functional.normalize(self.text_projection(text), dim=-1)

    def loss(self, padded: Tensor, mask: Tensor, text: Tensor) -> Tensor:
        eeg = self.encode_eeg(padded, mask)
        text_embedding = self.encode_text(text)
        logits = eeg @ text_embedding.T / self.temperature
        labels = torch.arange(logits.shape[0], device=logits.device)
        return 0.5 * (nn.functional.cross_entropy(logits, labels) + nn.functional.cross_entropy(logits.T, labels))


def make_batch(trials: list[Trial], indices: Iterable[int], text_features: np.ndarray, device: torch.device) -> tuple[Tensor, Tensor, Tensor]:
    selected = [trials[int(index)] for index in indices]
    sequences = [torch.from_numpy(trial.eeg_units) for trial in selected]
    padded = pad_sequence(sequences, batch_first=True).to(device)
    lengths = torch.tensor([sequence.shape[0] for sequence in sequences], device=device)
    mask = torch.arange(padded.shape[1], device=device)[None, :] < lengths[:, None]
    text = torch.from_numpy(text_features[[int(index) for index in indices]]).to(device)
    return padded, mask, text


def train_head(trials: list[Trial], text_features: np.ndarray, train_idx: np.ndarray, args: argparse.Namespace, device: torch.device) -> AlignmentHead:
    head = AlignmentHead(N_CHANNELS * len(BANDS), text_features.shape[1], args.proj_dim, args.temperature).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=args.lr)
    generator = torch.Generator(device="cpu").manual_seed(args.seed + 1)
    for _epoch in range(args.epochs):
        order = train_idx[torch.randperm(len(train_idx), generator=generator).numpy()]
        head.train()
        for start in range(0, len(order), args.batch_size):
            batch_idx = order[start : start + args.batch_size]
            if len(batch_idx) < 2:
                continue
            padded, mask, text = make_batch(trials, batch_idx, text_features, device)
            loss = head.loss(padded, mask, text)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    head.eval()
    return head


def evaluate(head: AlignmentHead, trials: list[Trial], text_features: np.ndarray, test_idx: np.ndarray, args: argparse.Namespace, device: torch.device) -> dict[str, float | int]:
    stimulus_to_index: dict[str, int] = {}
    sentence_features: list[np.ndarray] = []
    for index in test_idx:
        trial = trials[int(index)]
        if trial.stimulus_id not in stimulus_to_index:
            stimulus_to_index[trial.stimulus_id] = len(sentence_features)
            sentence_features.append(text_features[int(index)])
    if len(stimulus_to_index) < args.num_candidates:
        raise RuntimeError(
            f"BLOCKER: unique test stimulus pool is smaller than N={args.num_candidates}; "
            "lower --num-candidates explicitly"
        )
    unique_ids = list(stimulus_to_index)
    unique_text = torch.from_numpy(np.stack(sentence_features)).to(device)
    with torch.no_grad():
        projected_text = head.encode_text(unique_text)
    generator = np.random.default_rng(args.seed + 2)
    recall_values: list[float] = []
    verification_scores: list[float] = []
    verification_labels: list[int] = []
    for trial_index in test_idx:
        trial = trials[int(trial_index)]
        padded, mask, _ = make_batch(trials, [int(trial_index)], text_features, device)
        with torch.no_grad():
            eeg_embedding = head.encode_eeg(padded, mask)[0]
        target_position = stimulus_to_index[trial.stimulus_id]
        negative_positions = [position for position in range(len(unique_ids)) if position != target_position]
        selected_negative = generator.choice(negative_positions, size=args.num_candidates - 1, replace=False)
        candidates = np.concatenate(([target_position], selected_negative))
        candidate_scores = eeg_embedding @ projected_text[torch.from_numpy(candidates).to(device)].T
        recall_values.append(float(int(torch.argmax(candidate_scores).item()) == 0))
        verification_scores.extend([float(candidate_scores[0].item()), float(candidate_scores[1].item())])
        verification_labels.extend([1, 0])
    return {
        "recall_at_1_n10": float(np.mean(recall_values)),
        "paired_verification_auroc": float(roc_auc_score(verification_labels, verification_scores)),
        "n_test_trials": int(len(test_idx)),
        "n_test_unique_stimuli": int(len(unique_ids)),
        "n_candidates": int(args.num_candidates),
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    started = time.perf_counter()
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trials, extraction = load_trials(args.dataset_root, args.task, args.max_trials)
    rng = np.random.default_rng(args.seed)
    permutation = rng.permutation(len(trials))
    train_size = int(len(trials) * args.train_fraction)
    if train_size < 2 or len(trials) - train_size < args.num_candidates:
        raise RuntimeError("BLOCKER: split does not leave enough training or N-way test trials")
    train_idx, test_idx = permutation[:train_size], permutation[train_size:]
    trials, standardization = fit_robust_standardizer(trials, train_idx)
    text_features = make_text_features([trial.sentence for trial in trials], args.text_dim)
    head = train_head(trials, text_features, train_idx, args, device)
    metrics = evaluate(head, trials, text_features, test_idx, args, device)
    result = {
        "status": "NON_PAPER_SMOKE",
        "seed": args.seed,
        "device": str(device),
        "task": args.task,
        "dataset_root": str(args.dataset_root),
        "split": "trial_level_random",
        "data_definition": {
            "trial": "one sentence for one subject",
            "epoch": "one valid word rawEEG segment from the MAT sentenceData structure",
            "spectral_feature": "Hanning-window FFT band power, 105 channels x 8 bands",
            "sampling_rate_hz": FS,
            "bands_hz": [{"name": name, "low": low, "high": high} for name, low, high in BANDS],
            "sequence": "valid word units in sentence order; masked mean pooling",
            "text": f"frozen HashingVectorizer n_features={args.text_dim}",
        },
        "extraction": extraction,
        "n_trials": len(trials),
        "n_subjects": len({trial.subject_id for trial in trials}),
        "n_unique_stimuli": len({trial.stimulus_id for trial in trials}),
        "eeg_unit_shape": [N_CHANNELS * len(BANDS)],
        "max_word_units": max(trial.valid_word_count for trial in trials),
        "standardization": standardization,
        "config": {
            "proj_dim": args.proj_dim,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "temperature": args.temperature,
            "train_fraction": args.train_fraction,
            "num_candidates": args.num_candidates,
            "max_trials": args.max_trials,
        },
        "metrics": metrics,
        "elapsed_sec": time.perf_counter() - started,
        "simplifications": [
            "trial-level random split instead of joint subject-and-stimulus holdout",
            "single seed and N=10 only",
            "A1 front-end uses FFT band power for the smoke path; fixed-window sensitivity is not run",
            "masked mean plus linear projections instead of the preregistered Transformer alignment encoder",
            "frozen hashing text features instead of a pretrained text encoder",
            "no Stage-1 sham probes, OOF u/u_min/G_k, ANMA-orig, or EQ-ANMA weighting",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"eq_anma_zuco1_smoke_seed_{args.seed}.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"status=NON_PAPER_SMOKE seed={args.seed} device={device}")
    print(f"samples={len(trials)} subjects={result['n_subjects']} train={len(train_idx)} test={len(test_idx)} max_units={result['max_word_units']}")
    print(f"unit_shape=({N_CHANNELS * len(BANDS)},) bands={len(BANDS)} fs={FS:g}Hz")
    print(f"metrics=R@1@N10={metrics['recall_at_1_n10']:.4f} paired_AUROC={metrics['paired_verification_auroc']:.4f}")
    print(f"ranges=std_abs_max:{standardization['all_standardized_abs_max']:.4f} iqr:[{standardization['train_iqr_min']:.4g},{standardization['train_iqr_max']:.4g}] elapsed_sec={result['elapsed_sec']:.2f} output={output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(2)
