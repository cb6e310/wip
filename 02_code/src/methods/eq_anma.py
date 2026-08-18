"""Reusable EQ-ANMA V0/V1/V2 measurement and weighting module.

The implementation shares the frozen ANMA-orig numerical components and
admits only text embeddings and EEG-shaped features.  Subject identifiers and
generator truth are deliberately absent from every fitted API.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from methods.anma_orig import (
    DEFAULT_CONFIG,
    TextAmortizer,
    TrialStateNet,
    fisher_information,
    measurement_loss,
)


VARIANTS = ("V0", "V1", "V2")
LAMBDA_M_GRID = (0.1, 0.3, 1.0, 3.0)


@dataclass(frozen=True)
class EQWeightResult:
    q: Tensor
    alpha: Tensor
    a: Tensor
    b: Tensor
    p: Tensor
    information: Tensor
    raw_sentence_score: Tensor
    floored_score: Tensor
    weights: Tensor
    floor_hit: Tensor
    all_zero_batch: bool
    measurement_loss: Tensor


def contribution_soft_response(u_oof: Tensor, *, tau: float) -> Tensor:
    if tau <= 0 or not torch.isfinite(torch.tensor(float(tau))):
        raise ValueError("tau must be finite and positive")
    if not bool(torch.isfinite(u_oof).all()):
        raise ValueError("u_oof contains NaN/Inf")
    return torch.sigmoid(u_oof / float(tau))


def _positive_mass_floor(
    raw: Tensor, *, eta: float = DEFAULT_CONFIG.eta, epsilon: float = DEFAULT_CONFIG.epsilon
) -> tuple[Tensor, Tensor, Tensor, bool]:
    has_mass = raw > 0
    all_zero = not bool(has_mass.any())
    if all_zero:
        floored = torch.ones_like(raw)
        floor_hit = torch.zeros_like(has_mass)
    else:
        floor_hit = ~has_mass
        floored = torch.where(has_mass, raw, float(eta) * raw[has_mass].median())
    total = floored.sum()
    if not bool(torch.isfinite(total)) or float(total.detach()) <= float(epsilon):
        normalized = torch.ones_like(floored)
        floor_hit = torch.zeros_like(has_mass)
        all_zero = True
    else:
        normalized = floored.numel() * floored / (total + float(epsilon))
    return floored, normalized.detach(), floor_hit.detach(), all_zero


class EQANMAModel(nn.Module):
    """Exact V0/V1/V2 2PL head plus Fisher sentence weighting."""

    def __init__(
        self,
        *,
        feature_dim: int = 840,
        text_dim: int = 384,
        hidden_dim: int = 64,
        variant: str = "V1",
        lambda_m: float = 1.0,
        seed: int = 0,
    ) -> None:
        if variant not in VARIANTS:
            raise ValueError("variant must be V0, V1, or V2")
        if float(lambda_m) not in LAMBDA_M_GRID:
            raise ValueError("lambda_m is frozen to {0.1,0.3,1,3}")
        if seed < 0:
            raise ValueError("seed must be non-negative")
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            super().__init__()
            self.text_amortizer = TextAmortizer(text_dim, hidden_dim)
            self.trial_state = TrialStateNet(feature_dim, hidden_dim)
        self.variant = variant
        self.lambda_m = float(lambda_m)
        self.lambda_a = DEFAULT_CONFIG.lambda_a
        self.a_max = DEFAULT_CONFIG.a_max
        self.eta = DEFAULT_CONFIG.eta
        self.epsilon = DEFAULT_CONFIG.epsilon

    def item_parameters(self, text_embeddings: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        alpha, b = self.text_amortizer(text_embeddings)
        a = F.softplus(alpha).clamp(max=self.a_max)
        return alpha, b, a

    def trial_q(
        self, features: Tensor, *, reference_features: Tensor | None = None
    ) -> Tensor:
        raw = self.trial_state(features)
        reference_raw = raw if reference_features is None else self.trial_state(reference_features)
        mean = reference_raw.mean()
        std = reference_raw.std(unbiased=False).clamp_min(self.epsilon)
        return (raw - mean) / std

    def forward(
        self,
        features: Tensor,
        text_embeddings: Tensor,
        item_indices: Tensor,
        item_mask: Tensor,
        soft_observations: Tensor,
        u_oof: Tensor,
        gate_by_item: Tensor,
        *,
        reference_features: Tensor | None = None,
        step: int = 0,
        warmup_steps: int = 0,
    ) -> EQWeightResult:
        if features.ndim != 2 or item_indices.ndim != 2:
            raise ValueError("features and item_indices must be rank-2")
        if item_mask.shape != item_indices.shape or item_mask.dtype != torch.bool:
            raise ValueError("item_mask must be bool and match item_indices")
        if soft_observations.shape != item_indices.shape or u_oof.shape != item_indices.shape:
            raise ValueError("observations/u_oof must match item_indices")
        if features.shape[0] != item_indices.shape[0]:
            raise ValueError("feature and item batch sizes differ")
        if gate_by_item.ndim != 1 or gate_by_item.shape[0] != text_embeddings.shape[0]:
            raise ValueError("gate_by_item must match the text item table")
        if item_indices.dtype != torch.long or bool((item_indices < 0).any()) or bool(
            (item_indices >= text_embeddings.shape[0]).any()
        ):
            raise ValueError("item_indices are invalid")
        if step < 0 or warmup_steps < 0:
            raise ValueError("step/warmup_steps must be non-negative")

        alpha_all, b_all, a_all = self.item_parameters(text_embeddings)
        alpha = alpha_all[item_indices]
        b = b_all[item_indices]
        a = a_all[item_indices]
        q = self.trial_q(features, reference_features=reference_features)
        p = torch.sigmoid(a * (q[:, None] - b)).clamp(1e-7, 1.0 - 1e-7)
        if not bool(item_mask.any()):
            raise ValueError("measurement batch contains no active item")
        measure = measurement_loss(
            soft_observations[item_mask], p[item_mask], alpha_all, lambda_a=self.lambda_a
        )
        information = fisher_information(a, p)

        active = item_mask
        if self.variant != "V0":
            active = active & (gate_by_item[item_indices] > 0)
        value = information
        if self.variant == "V2":
            value = value * u_oof.clamp_min(0.0)
        counts = active.sum(dim=1)
        raw = (value * active.to(value.dtype)).sum(dim=1) / counts.clamp_min(1).to(value.dtype)
        raw = torch.where(counts > 0, raw, torch.zeros_like(raw))
        floored, weights, floor_hit, all_zero = _positive_mass_floor(
            raw, eta=self.eta, epsilon=self.epsilon
        )
        if step < warmup_steps:
            weights = torch.ones_like(weights)
        return EQWeightResult(
            q=q,
            alpha=alpha,
            a=a,
            b=b,
            p=p,
            information=information,
            raw_sentence_score=raw,
            floored_score=floored,
            weights=weights,
            floor_hit=floor_hit,
            all_zero_batch=all_zero,
            measurement_loss=measure,
        )


def measurement_parameter_names(model: EQANMAModel) -> tuple[str, ...]:
    names = tuple(name for name, _ in model.named_parameters())
    if any("subject" in name.lower() for name in names):
        raise AssertionError("subject identifier entered the EQ-ANMA module")
    return names
