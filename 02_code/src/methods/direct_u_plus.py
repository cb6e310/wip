"""Exact v3.13 section 6.16 direct-u-plus weighting.

The module contains no measurement head.  It accepts already-frozen OOF
contribution scores, aggregates positive evidence by sentence, applies the
positive-mass median floor, normalizes each batch to mean weight one, and
detaches the result from autograd.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import Tensor


GAMMA_GRID = (0.5, 1.0, 2.0)
SCORE_VERSIONS = ("u_oof", "u_min")
WARMUP_VERSIONS = ("none", "EQ_matched")
ETA = 0.1
EPSILON = 1e-8


@dataclass(frozen=True)
class DirectWeightResult:
    raw_sentence_score: Tensor
    floored_score: Tensor
    weights: Tensor
    floor_hit: Tensor
    all_zero_batch: bool


def direct_u_plus_weights(
    scores: Tensor,
    item_mask: Tensor,
    *,
    gamma: float,
    gate: Tensor | None = None,
    eta: float = ETA,
    epsilon: float = EPSILON,
    step: int = 0,
    warmup_steps: int = 0,
) -> DirectWeightResult:
    """Compute the exact positive-mass-floor direct weights.

    ``scores`` and ``item_mask`` are ``[batch, items]``.  A gate is an item
    vector or an aligned matrix and is interpreted only as the frozen
    ``G_k > 0`` veto used by gated direct.  Empty/all-zero sentences receive
    the positive-mass median floor; a wholly zero batch falls back to uniform.
    """

    if scores.ndim != 2 or item_mask.shape != scores.shape:
        raise ValueError("scores and item_mask must be aligned rank-2 tensors")
    if item_mask.dtype != torch.bool:
        raise TypeError("item_mask must be bool")
    if float(gamma) not in GAMMA_GRID:
        raise ValueError("gamma is frozen to {0.5,1,2}")
    if eta != ETA or epsilon != EPSILON:
        raise ValueError("eta/epsilon are frozen to 0.1/1e-8")
    if step < 0 or warmup_steps < 0:
        raise ValueError("step and warmup_steps must be non-negative")
    if not bool(torch.isfinite(scores).all()):
        raise ValueError("scores contain NaN/Inf")

    active = item_mask
    if gate is not None:
        gate_values = torch.as_tensor(gate, device=scores.device)
        if gate_values.ndim == 1:
            if gate_values.shape[0] != scores.shape[1]:
                raise ValueError("one-dimensional gate must match item width")
            gate_values = gate_values[None, :].expand_as(scores)
        if gate_values.shape != scores.shape:
            raise ValueError("gate must be item-vector or scores-shaped")
        active = active & (gate_values > 0)

    positive = scores.clamp_min(0.0).pow(float(gamma))
    counts = active.sum(dim=1)
    raw = (positive * active.to(positive.dtype)).sum(dim=1) / counts.clamp_min(1).to(positive.dtype)
    raw = torch.where(counts > 0, raw, torch.zeros_like(raw))
    has_mass = raw > 0
    all_zero = not bool(has_mass.any())
    if all_zero:
        floored = torch.ones_like(raw)
        floor_hit = torch.zeros_like(has_mass)
    else:
        positive_median = raw[has_mass].median()
        floor_hit = ~has_mass
        floored = torch.where(has_mass, raw, float(eta) * positive_median)
    total = floored.sum()
    if not bool(torch.isfinite(total)) or float(total.detach()) <= float(epsilon):
        normalized = torch.ones_like(floored)
        all_zero = True
        floor_hit = torch.zeros_like(has_mass)
    else:
        normalized = floored.numel() * floored / (total + float(epsilon))
    weights = normalized.detach()
    if step < warmup_steps:
        weights = torch.ones_like(weights)
    return DirectWeightResult(
        raw_sentence_score=raw.detach(),
        floored_score=floored.detach(),
        weights=weights,
        floor_hit=floor_hit.detach(),
        all_zero_batch=all_zero,
    )


def weight_diagnostics(weights: Tensor) -> dict[str, object]:
    """Return the v3.13 entropy/Gini/linear-quantile diagnostics."""

    values = np.asarray(torch.as_tensor(weights).detach().cpu(), dtype=np.float64).reshape(-1)
    if values.size < 1 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("weights must be a finite non-negative vector")
    total = float(values.sum())
    if total <= 0:
        raise ValueError("weight diagnostics require positive mass")
    probabilities = values / total
    entropy = 1.0 if values.size == 1 else float(
        -(probabilities[probabilities > 0] * np.log(probabilities[probabilities > 0])).sum()
        / np.log(values.size)
    )
    gini = float(np.abs(values[:, None] - values[None, :]).sum() / (2 * values.size * total))
    quantiles = np.quantile(values, [0.05, 0.5, 0.95], method="linear")
    return {
        "normalized_entropy": entropy,
        "gini": gini,
        "quantiles_5_50_95": [float(value) for value in quantiles],
        "numpy_quantile_method": "linear",
        "count": int(values.size),
    }


def variant_ids(*, gated: bool) -> tuple[str, ...]:
    prefix = "gated_direct" if gated else "direct"
    return tuple(
        f"{prefix}|gamma={gamma:g}|score={score}|warmup={warmup}"
        for gamma in GAMMA_GRID
        for score in SCORE_VERSIONS
        for warmup in WARMUP_VERSIONS
    )
