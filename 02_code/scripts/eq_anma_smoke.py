#!/usr/bin/env python3
"""Minimal, reproducible ZuCo 1.0 EEG-text alignment smoke test.

This intentionally does not guess a ZuCo file format or a backbone. The two
dataset-specific pieces are injected through importable factories:

  --data-loader package.module:function
      function(dataset_root) -> dict with at least:
        eeg: float array [n_trials, n_channels, n_time] (or [n_trials, n_time, n_channels])
        sentences: sequence[str] of length n_trials
      Optional keys: subject_ids, stimulus_ids, trial_ids.

  --backbone-factory package.module:function
      function(device) -> object with:
        encode_eeg(torch.Tensor) -> torch.Tensor [n_trials, eeg_dim]
        encode_text(sequence[str]) -> torch.Tensor [n_trials, text_dim]

The adapter owns raw ZuCo parsing and epoch extraction because the project
spec does not define a file/schema contract. This script performs train-fold
channel standardization, freezes the supplied backbone, trains a symmetric
InfoNCE projection head, and evaluates N=10 Recall@1 plus paired AUROC.
"""

from __future__ import annotations

import argparse
import importlib
import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch import Tensor, nn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--data-loader", required=True, help="module:function")
    parser.add_argument("--backbone-factory", required=True, help="module:function")
    parser.add_argument("--eeg-layout", required=True, choices=("NCT", "NTC"))
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("smoke_runs"))
    parser.add_argument("--proj-dim", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    parser.add_argument("--num-candidates", type=int, default=10)
    return parser.parse_args()


def resolve_factory(spec: str) -> Callable[..., Any]:
    try:
        module_name, function_name = spec.rsplit(":", 1)
        module = importlib.import_module(module_name)
        factory = getattr(module, function_name)
    except (ValueError, ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"BLOCKER: cannot import factory {spec!r}; expected module:function ({exc})"
        ) from exc
    if not callable(factory):
        raise RuntimeError(f"BLOCKER: factory {spec!r} is not callable")
    return factory


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False


def validate_args(args: argparse.Namespace) -> None:
    if not 0.0 < args.train_fraction < 1.0:
        raise RuntimeError("BLOCKER: --train-fraction must be strictly between 0 and 1")
    if args.num_candidates < 2:
        raise RuntimeError("BLOCKER: --num-candidates must be at least 2")
    if args.proj_dim < 1:
        raise RuntimeError("BLOCKER: --proj-dim must be positive")
    if args.epochs < 1:
        raise RuntimeError("BLOCKER: --epochs must be positive")
    if args.batch_size < 2:
        raise RuntimeError("BLOCKER: --batch-size must be at least 2 for InfoNCE negatives")
    if args.lr <= 0.0:
        raise RuntimeError("BLOCKER: --lr must be positive")
    if args.temperature <= 0.0:
        raise RuntimeError("BLOCKER: --temperature must be positive")


def as_float_tensor(value: Any, name: str) -> Tensor:
    tensor = value if isinstance(value, Tensor) else torch.as_tensor(value)
    if tensor.ndim == 0 or not torch.is_floating_point(tensor):
        tensor = tensor.float()
    if not torch.isfinite(tensor).all():
        raise RuntimeError(f"BLOCKER: {name} contains NaN/Inf")
    return tensor.float().contiguous()


def validate_bundle(bundle: Mapping[str, Any], layout: str) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise RuntimeError("BLOCKER: data loader must return a mapping")
    for key in ("eeg", "sentences"):
        if key not in bundle:
            raise RuntimeError(f"BLOCKER: data loader output is missing {key!r}")

    eeg = as_float_tensor(bundle["eeg"], "eeg")
    if eeg.ndim != 3:
        raise RuntimeError(
            "BLOCKER: eeg must be rank-3 epochs; raw epoch/event schema is not defined "
            f"(received shape={tuple(eeg.shape)})"
        )
    if layout == "NTC":
        eeg = eeg.transpose(1, 2).contiguous()
    n_trials, n_channels, n_time = eeg.shape
    if n_trials < 2 or n_channels < 1 or n_time < 1:
        raise RuntimeError(f"BLOCKER: invalid EEG epoch shape {tuple(eeg.shape)}")

    sentences = [str(item) for item in bundle["sentences"]]
    if len(sentences) != n_trials:
        raise RuntimeError(
            f"BLOCKER: len(sentences)={len(sentences)} does not match EEG trials={n_trials}"
        )
    if any(not sentence.strip() for sentence in sentences):
        raise RuntimeError("BLOCKER: empty sentence found")

    normalized: dict[str, Any] = {"eeg": eeg, "sentences": sentences}
    for key in ("subject_ids", "stimulus_ids", "trial_ids"):
        if key in bundle and bundle[key] is not None:
            values = list(bundle[key])
            if len(values) != n_trials:
                raise RuntimeError(
                    f"BLOCKER: len({key})={len(values)} does not match EEG trials={n_trials}"
                )
            normalized[key] = [str(value) for value in values]
    return normalized


def standardize_train_fold(eeg: Tensor, train_idx: Tensor) -> tuple[Tensor, dict[str, Any]]:
    # EEG is [trial, channel, time]. Fit all preprocessing statistics on train only.
    train = eeg.index_select(0, train_idx)
    mean = train.mean(dim=(0, 2), keepdim=True)
    std = train.std(dim=(0, 2), unbiased=False, keepdim=True).clamp_min(1e-6)
    standardized = (eeg - mean) / std
    stats = {
        "train_mean_abs_max": float(mean.abs().max().item()),
        "train_std_min": float(std.min().item()),
        "train_std_max": float(std.max().item()),
        "standardized_abs_max": float(standardized.abs().max().item()),
    }
    return standardized, stats


def freeze_backbone(backbone: Any) -> None:
    if hasattr(backbone, "eval"):
        backbone.eval()
    parameters = getattr(backbone, "parameters", None)
    if callable(parameters):
        for parameter in parameters():
            parameter.requires_grad_(False)


def encode(backbone: Any, eeg: Tensor, sentences: Sequence[str], device: torch.device) -> tuple[Tensor, Tensor]:
    if not callable(getattr(backbone, "encode_eeg", None)):
        raise RuntimeError("BLOCKER: backbone must expose encode_eeg(tensor)")
    if not callable(getattr(backbone, "encode_text", None)):
        raise RuntimeError("BLOCKER: backbone must expose encode_text(sentences)")
    with torch.no_grad():
        eeg_latent = as_float_tensor(backbone.encode_eeg(eeg.to(device)), "EEG latent")
        text_latent = as_float_tensor(backbone.encode_text(list(sentences)), "text latent")
    if eeg_latent.ndim != 2 or text_latent.ndim != 2:
        raise RuntimeError(
            "BLOCKER: backbone encoders must return rank-2 [batch, dim] latents; "
            f"got EEG={tuple(eeg_latent.shape)}, text={tuple(text_latent.shape)}"
        )
    if eeg_latent.shape[0] != eeg.shape[0] or text_latent.shape[0] != eeg.shape[0]:
        raise RuntimeError("BLOCKER: encoder batch dimension does not match trial count")
    if eeg_latent.shape[1] < 1 or text_latent.shape[1] < 1:
        raise RuntimeError("BLOCKER: encoder returned an empty latent dimension")
    return eeg_latent, text_latent


class InfoNCEHead(nn.Module):
    def __init__(self, eeg_dim: int, text_dim: int, proj_dim: int, temperature: float) -> None:
        super().__init__()
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.eeg_projection = nn.Linear(eeg_dim, proj_dim)
        self.text_projection = nn.Linear(text_dim, proj_dim)
        self.temperature = temperature

    def project(self, eeg_latent: Tensor, text_latent: Tensor) -> tuple[Tensor, Tensor]:
        eeg = nn.functional.normalize(self.eeg_projection(eeg_latent), dim=-1)
        text = nn.functional.normalize(self.text_projection(text_latent), dim=-1)
        return eeg, text

    def loss(self, eeg_latent: Tensor, text_latent: Tensor) -> Tensor:
        eeg, text = self.project(eeg_latent, text_latent)
        logits = eeg @ text.T / self.temperature
        labels = torch.arange(logits.shape[0], device=logits.device)
        return 0.5 * (
            nn.functional.cross_entropy(logits, labels)
            + nn.functional.cross_entropy(logits.T, labels)
        )


def train_head(
    eeg_latent: Tensor,
    text_latent: Tensor,
    train_idx: Tensor,
    args: argparse.Namespace,
    device: torch.device,
) -> InfoNCEHead:
    head = InfoNCEHead(
        eeg_dim=eeg_latent.shape[1],
        text_dim=text_latent.shape[1],
        proj_dim=args.proj_dim,
        temperature=args.temperature,
    ).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=args.lr)
    generator = torch.Generator(device="cpu").manual_seed(args.seed + 1)
    for _epoch in range(args.epochs):
        order = train_idx[torch.randperm(len(train_idx), generator=generator)]
        head.train()
        for start in range(0, len(order), args.batch_size):
            batch_idx = order[start : start + args.batch_size].to(device)
            loss = head.loss(eeg_latent[batch_idx], text_latent[batch_idx])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    head.eval()
    return head


def similarity_matrix(head: InfoNCEHead, eeg_latent: Tensor, text_latent: Tensor) -> Tensor:
    with torch.no_grad():
        eeg, text = head.project(eeg_latent, text_latent)
    return eeg @ text.T


def evaluate(
    head: InfoNCEHead,
    eeg_latent: Tensor,
    text_latent: Tensor,
    test_idx: Tensor,
    args: argparse.Namespace,
) -> dict[str, float | int]:
    if len(test_idx) < args.num_candidates:
        raise RuntimeError(
            f"BLOCKER: test trials={len(test_idx)} < N={args.num_candidates}; "
            "provide more trials or lower --num-candidates explicitly"
        )
    test_idx = test_idx.to(eeg_latent.device)
    scores = similarity_matrix(
        head,
        eeg_latent[test_idx],
        text_latent[test_idx],
    )
    generator = torch.Generator(device="cpu").manual_seed(args.seed + 2)
    recalls: list[float] = []
    verification_scores: list[float] = []
    labels: list[int] = []
    n = len(test_idx)
    for row in range(n):
        all_rows = torch.arange(n, device=scores.device)
        negatives = all_rows[all_rows != row]
        negative_order = torch.randperm(len(negatives), generator=generator)
        candidate_rows = torch.cat(
            [
                torch.tensor([row], device=scores.device),
                negatives[negative_order[: args.num_candidates - 1]],
            ]
        )
        rank = int(torch.argsort(scores[row, candidate_rows], descending=True)[0].item())
        recalls.append(float(rank == 0))
        verification_scores.append(float(scores[row, row].item()))
        labels.append(1)
        negative_row = int(candidate_rows[1].item())
        verification_scores.append(float(scores[row, negative_row].item()))
        labels.append(0)
    try:
        auroc = float(roc_auc_score(labels, verification_scores))
    except ValueError as exc:
        raise RuntimeError(f"BLOCKER: paired verification AUROC is undefined: {exc}") from exc
    return {
        "recall_at_1_n10": float(np.mean(recalls)),
        "paired_verification_auroc": auroc,
        "n_test_trials": n,
        "n_candidates": args.num_candidates,
    }


def main() -> int:
    args = parse_args()
    validate_args(args)
    started = time.perf_counter()
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    loader = resolve_factory(args.data_loader)
    backbone_factory = resolve_factory(args.backbone_factory)
    if not args.dataset_root.exists():
        raise RuntimeError(f"BLOCKER: dataset root does not exist: {args.dataset_root}")

    bundle = validate_bundle(loader(args.dataset_root), args.eeg_layout)
    eeg = bundle["eeg"]
    n_trials = eeg.shape[0]
    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    permutation = torch.randperm(n_trials, generator=generator)
    train_size = int(n_trials * args.train_fraction)
    if train_size < 2:
        raise RuntimeError("BLOCKER: trial split leaves fewer than 2 training trials for InfoNCE")
    if n_trials - train_size < args.num_candidates:
        raise RuntimeError(
            f"BLOCKER: test trials={n_trials - train_size} < N={args.num_candidates}; "
            "adjust the split or lower --num-candidates explicitly"
        )
    train_idx, test_idx = permutation[:train_size], permutation[train_size:]
    eeg, standardization = standardize_train_fold(eeg, train_idx)

    backbone = backbone_factory(str(device))
    freeze_backbone(backbone)
    eeg_latent, text_latent = encode(backbone, eeg, bundle["sentences"], device)
    eeg_latent = eeg_latent.to(device)
    text_latent = text_latent.to(device)
    head = train_head(eeg_latent, text_latent, train_idx, args, device)
    metrics = evaluate(head, eeg_latent, text_latent, test_idx, args)

    result = {
        "status": "NON_PAPER_SMOKE",
        "seed": args.seed,
        "device": str(device),
        "dataset_root": str(args.dataset_root),
        "split": "trial_level_random",
        "config": {
            "eeg_layout": args.eeg_layout,
            "proj_dim": args.proj_dim,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "temperature": args.temperature,
            "train_fraction": args.train_fraction,
            "num_candidates": args.num_candidates,
        },
        "n_trials": n_trials,
        "eeg_shape_nct": list(eeg.shape),
        "latent_shapes": {"eeg": list(eeg_latent.shape), "text": list(text_latent.shape)},
        "standardization": standardization,
        "metrics": metrics,
        "elapsed_sec": time.perf_counter() - started,
        "simplifications": [
            "trial-level random split instead of subject-and-stimulus joint holdout",
            "single user-supplied seed",
            "N=10 candidate retrieval only",
            "no sham probes, OOF u, u_min, delta, G_k, or ANMA weighting",
            "dataset-specific epoch extraction and backbone are delegated adapters",
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"eq_anma_smoke_seed_{args.seed}.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"status=NON_PAPER_SMOKE seed={args.seed} device={device}")
    print(f"samples={n_trials} train={len(train_idx)} test={len(test_idx)} eeg_shape={tuple(eeg.shape)}")
    print(f"latent_shapes=eeg:{tuple(eeg_latent.shape)} text:{tuple(text_latent.shape)}")
    print(
        "metrics="
        f"R@1@N10={metrics['recall_at_1_n10']:.4f} "
        f"paired_AUROC={metrics['paired_verification_auroc']:.4f}"
    )
    print(
        f"elapsed_sec={result['elapsed_sec']:.2f} "
        f"std_abs_max={standardization['standardized_abs_max']:.4f} output={output_path}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(2)
