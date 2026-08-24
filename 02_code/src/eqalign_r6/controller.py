"""Pure, fit-only R6 controller transforms on already-computed scores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Sequence

import torch
from torch import Tensor


EPSILON = 1e-8
W_MIN = 0.2
W_MAX = 3.0
H_CLIP = 3.0
GAMMA_GRID = (0.0, 0.25, 0.5, 1.0)


@dataclass(frozen=True)
class SentenceScoreStats:
    mu: Tensor
    sigma: Tensor


@dataclass(frozen=True)
class WeightDiagnostics:
    lower_clip_count: int
    upper_clip_count: int
    normalization_floor_used: bool


@dataclass(frozen=True)
class BoundedWeightResult:
    raw_weight: Tensor
    normalized_weight: Tensor
    diagnostics: WeightDiagnostics


def _finite_vector(values: Tensor, name: str) -> Tensor:
    tensor = torch.as_tensor(values)
    if tensor.ndim != 1:
        raise ValueError(f"{name} must be rank 1")
    if not tensor.is_floating_point():
        tensor = tensor.to(torch.float64)
    if not bool(torch.isfinite(tensor).all()):
        raise ValueError(f"{name} contains NaN/Inf")
    return tensor


def fit_sentence_score_stats(
    scores: Tensor,
    fit_mask: Tensor,
    *,
    epsilon: float = EPSILON,
) -> SentenceScoreStats:
    values = _finite_vector(scores, "scores")
    mask = torch.as_tensor(fit_mask, device=values.device)
    if mask.dtype != torch.bool or mask.shape != values.shape:
        raise ValueError("fit_mask must be a bool vector aligned with scores")
    if not bool(mask.any()):
        raise ValueError("fit_mask selects no rows")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    fit_values = values[mask]
    mu = fit_values.mean().detach()
    sigma = fit_values.std(unbiased=False).clamp_min(float(epsilon)).detach()
    return SentenceScoreStats(mu=mu, sigma=sigma)


def standardize_and_clip(
    scores: Tensor,
    stats: SentenceScoreStats,
    *,
    h_clip: float = H_CLIP,
) -> Tensor:
    values = _finite_vector(scores, "scores")
    if h_clip != H_CLIP:
        raise ValueError("h_clip is frozen to 3.0")
    if float(stats.sigma) <= 0 or not bool(torch.isfinite(stats.sigma)):
        raise ValueError("stats.sigma must be finite and positive")
    return ((values - stats.mu.to(values)) / stats.sigma.to(values)).clamp(-h_clip, h_clip)


def bounded_weights(
    h: Tensor,
    gamma: float,
    *,
    w_min: float = W_MIN,
    w_max: float = W_MAX,
    epsilon: float = EPSILON,
) -> BoundedWeightResult:
    values = _finite_vector(h, "h")
    if float(gamma) not in GAMMA_GRID:
        raise ValueError("gamma is frozen to {0,0.25,0.5,1}")
    if w_min != W_MIN or w_max != W_MAX:
        raise ValueError("weight bounds are frozen to [0.2,3.0]")
    if values.numel() == 0:
        raise ValueError("h must not be empty")
    unclipped = 1.0 + float(gamma) * values
    raw = unclipped.clamp(w_min, w_max)
    total = raw.sum()
    floor_used = not bool(torch.isfinite(total)) or float(total.detach()) <= epsilon
    normalized = torch.ones_like(raw) if floor_used else raw.numel() * raw / total
    return BoundedWeightResult(
        raw_weight=raw.detach(),
        normalized_weight=normalized.detach(),
        diagnostics=WeightDiagnostics(
            lower_clip_count=int((unclipped < w_min).sum().item()),
            upper_clip_count=int((unclipped > w_max).sum().item()),
            normalization_floor_used=floor_used,
        ),
    )


def sentence_fisher_score(information: Tensor, item_mask: Tensor) -> Tensor:
    values = torch.as_tensor(information)
    mask = torch.as_tensor(item_mask, device=values.device)
    if values.ndim != 2 or mask.shape != values.shape or mask.dtype != torch.bool:
        raise ValueError("information and bool item_mask must be aligned rank-2 tensors")
    if not values.is_floating_point():
        values = values.to(torch.float64)
    if not bool(torch.isfinite(values).all()):
        raise ValueError("information contains NaN/Inf")
    counts = mask.sum(dim=1)
    sums = (values * mask.to(values.dtype)).sum(dim=1)
    return torch.where(counts > 0, sums / counts.clamp_min(1).to(values.dtype), torch.zeros_like(sums))


def direct_matched_h(score: Tensor, fit_mask: Tensor) -> Tensor:
    return standardize_and_clip(score, fit_sentence_score_stats(score, fit_mask))


def _group_keys(subject_ids: Sequence[Hashable] | Tensor, count: int) -> list[Hashable]:
    if isinstance(subject_ids, Tensor):
        ids = subject_ids.detach().cpu().tolist()
    else:
        ids = list(subject_ids)
    if len(ids) != count:
        raise ValueError("subject_ids must align with h")
    keys: list[Hashable] = []
    for value in ids:
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise ValueError("each shuffle key must be (outer_cell, task, subject)")
        keys.append(tuple(value))
    return keys


def shuffle_h_within_subject_trial(
    h: Tensor,
    subject_ids: Sequence[Hashable] | Tensor,
    seed: int,
) -> Tensor:
    """Permute trials inside each frozen composite group with a private RNG."""

    values = _finite_vector(h, "h")
    keys = _group_keys(subject_ids, values.numel())
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(seed))
    output = values.clone()
    groups: dict[Hashable, list[int]] = {}
    for index, key in enumerate(keys):
        groups.setdefault(key, []).append(index)
    for indices in groups.values():
        permutation = torch.randperm(len(indices), generator=generator).tolist()
        destination = torch.tensor(indices, device=values.device)
        source = torch.tensor([indices[item] for item in permutation], device=values.device)
        output[destination] = values[source]
    return output.detach()
