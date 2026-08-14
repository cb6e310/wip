"""ANMA-orig reference implementation frozen by specification §6.15.

This is the project's own reference baseline, not a reproduction of an
external implementation.  The module separates the observable construction,
2PL measurement head, Fisher information weights, sentence-level aggregation,
and diagnostics so each contract can be tested independently.

Real probe predictions and frozen text embeddings are required inputs.  The
module never creates them implicitly and never accepts a subject identifier.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn
from torch.nn import functional as F


@dataclass(frozen=True)
class ANMAConfig:
    """Only values explicitly frozen in §6.15/§6.8."""

    eta: float = 0.1
    lambda_a: float = 1e-2
    a_max: float = 10.0
    lambda_m: float = 1.0
    epsilon: float = 1e-8
    warmup_steps: int = 0
    hidden_dim: int = 64
    lambda_m_grid: tuple[float, ...] = (0.1, 0.3, 1.0, 3.0)
    n_item_grid: tuple[int, ...] = (2, 4, 10, 50)

    def __post_init__(self) -> None:
        if not 0.0 < self.eta <= 1.0:
            raise ValueError("eta must be in (0, 1]")
        if self.lambda_a < 0.0 or self.lambda_m < 0.0:
            raise ValueError("measurement regularization values must be non-negative")
        if self.a_max <= 0.0 or self.epsilon <= 0.0:
            raise ValueError("a_max and epsilon must be positive")
        if self.warmup_steps < 0 or self.hidden_dim < 1:
            raise ValueError("warmup_steps/hidden_dim must be non-negative/positive")
        if tuple(self.lambda_m_grid) != (0.1, 0.3, 1.0, 3.0):
            raise ValueError("lambda_m grid is frozen to {0.1,0.3,1.0,3.0}")
        if tuple(self.n_item_grid) != (2, 4, 10, 50):
            raise ValueError("N_item grid is frozen to {2,4,10,50}")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_CONFIG = ANMAConfig()


def config_hash(config: ANMAConfig = DEFAULT_CONFIG) -> str:
    payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_metadata(
    *, seed: int, fold: str | int, method: str = "ANMA-orig", config: ANMAConfig = DEFAULT_CONFIG
) -> dict[str, object]:
    if seed < 0 or not str(fold).strip() or not method.strip():
        raise ValueError("seed must be non-negative; fold/method must be non-empty")
    return {"seed": int(seed), "fold": str(fold), "method": method, "config_hash": config_hash(config)}


@dataclass(frozen=True)
class ObservationBatch:
    """Hard/continuous observations after candidate-set renormalization."""

    y: Tensor
    c: Tensor
    probabilities: Tensor
    candidate_mask: Tensor

    @property
    def n_observations(self) -> int:
        return int(self.y.numel())


def _validate_candidate_inputs(
    log_probs: Tensor, target_indices: Tensor, candidate_indices: Tensor, candidate_mask: Tensor | None
) -> Tensor:
    if log_probs.ndim != 2 or target_indices.ndim != 1 or candidate_indices.ndim != 2:
        raise ValueError("log_probs=(N,V), target_indices=(N,), candidates=(N,K) are required")
    n, vocab = log_probs.shape
    if target_indices.shape[0] != n or candidate_indices.shape[0] != n:
        raise ValueError("candidate/target batch sizes must agree")
    if candidate_mask is None:
        candidate_mask = torch.ones_like(candidate_indices, dtype=torch.bool)
    if candidate_mask.shape != candidate_indices.shape or candidate_mask.dtype != torch.bool:
        raise ValueError("candidate_mask must be bool with candidate_indices shape")
    if not bool(candidate_mask.any(dim=1).all()):
        raise ValueError("every candidate set must contain at least one item")
    if bool((candidate_indices < 0).any()) or bool((candidate_indices >= vocab).any()):
        raise ValueError("candidate index outside log_probs vocabulary")
    if bool((target_indices < 0).any()) or bool((target_indices >= vocab).any()):
        raise ValueError("target index outside log_probs vocabulary")
    in_candidates = (candidate_indices == target_indices[:, None]) & candidate_mask
    if not bool(in_candidates.any(dim=1).all()):
        raise ValueError("every target must occur in its candidate set")
    if not torch.isfinite(log_probs).all():
        raise ValueError("log_probs contain NaN/Inf")
    return candidate_mask


def construct_observations(
    log_probs: Tensor,
    target_indices: Tensor,
    candidate_indices: Tensor,
    candidate_mask: Tensor | None = None,
) -> ObservationBatch:
    """Implement §6.15.3 restricted correctness exactly.

    ``log_probs`` are the real-arm probe log probabilities over the complete
    item vocabulary.  Candidate sets are renormalized before top-1 and target
    probability are read; no target or candidate is inferred by this helper.
    """

    mask = _validate_candidate_inputs(log_probs, target_indices, candidate_indices, candidate_mask)
    gathered = torch.gather(log_probs, 1, candidate_indices)
    masked = gathered.masked_fill(~mask, -torch.inf)
    probabilities = torch.softmax(masked, dim=1).masked_fill(~mask, 0.0)
    target_mask = (candidate_indices == target_indices[:, None]) & mask
    target_probability = (probabilities * target_mask.to(probabilities.dtype)).sum(dim=1)
    argmax_position = probabilities.argmax(dim=1)
    predicted = candidate_indices.gather(1, argmax_position[:, None]).squeeze(1)
    y = (predicted == target_indices).to(probabilities.dtype)
    return ObservationBatch(y=y, c=target_probability, probabilities=probabilities, candidate_mask=mask)


@dataclass(frozen=True)
class NItemSelection:
    selected: int
    mean_accuracy: dict[int, float]


def select_n_item(
    training_observations: Mapping[int, Tensor],
    *,
    grid: Sequence[int] = DEFAULT_CONFIG.n_item_grid,
) -> NItemSelection:
    """Select N_item by outer-training accuracy closest to 0.5 (J23)."""

    expected = tuple(DEFAULT_CONFIG.n_item_grid)
    if tuple(grid) != expected:
        raise ValueError("N_item grid is frozen to {2,4,10,50}")
    means: dict[int, float] = {}
    for n_item in grid:
        if n_item not in training_observations:
            raise ValueError(f"missing training observation for N_item={n_item}")
        values = torch.as_tensor(training_observations[n_item], dtype=torch.float32)
        if values.numel() == 0 or not bool(torch.isfinite(values).all()):
            raise ValueError(f"invalid training observations for N_item={n_item}")
        means[int(n_item)] = float(values.mean().item())
    selected = min(grid, key=lambda value: (abs(means[int(value)] - 0.5), int(value)))
    return NItemSelection(selected=int(selected), mean_accuracy=means)


def center_scale_q(q: Tensor, *, epsilon: float = DEFAULT_CONFIG.epsilon) -> Tensor:
    """Center and scale trial states on the current training distribution."""

    if q.ndim != 1 or q.numel() < 1:
        raise ValueError("q must be a non-empty rank-1 tensor")
    mean = q.mean()
    std = q.std(unbiased=False).clamp_min(epsilon)
    return (q - mean) / std


def two_pl_probability(q: Tensor, alpha: Tensor, b: Tensor, *, a_max: float = DEFAULT_CONFIG.a_max) -> tuple[Tensor, Tensor]:
    """Return ``p=sigmoid(a*(q-b))`` and positive discrimination ``a``."""

    if q.shape != alpha.shape or q.shape != b.shape:
        raise ValueError("q, alpha, and b must have the same shape")
    if not torch.isfinite(q).all() or not torch.isfinite(alpha).all() or not torch.isfinite(b).all():
        raise ValueError("2PL inputs contain NaN/Inf")
    a = F.softplus(alpha).clamp(max=float(a_max))
    p = torch.sigmoid(a * (q - b))
    return p, a


def measurement_loss(
    y: Tensor, p: Tensor, alpha: Tensor, *, lambda_a: float = DEFAULT_CONFIG.lambda_a
) -> Tensor:
    if y.shape != p.shape:
        raise ValueError("y and p must have matching shapes")
    if alpha.ndim != 1 and (alpha.ndim != p.ndim or alpha.shape != p.shape):
        raise ValueError("alpha must be a vector of item parameters or match p")
    if not torch.isfinite(y).all() or not torch.isfinite(p).all() or not torch.isfinite(alpha).all():
        raise ValueError("measurement tensors contain NaN/Inf")
    if bool(((y < 0) | (y > 1)).any()):
        raise ValueError("hard/soft observations must be in [0,1]")
    return F.binary_cross_entropy(p.clamp(1e-7, 1.0 - 1e-7), y) + float(lambda_a) * alpha.square().mean()


def fit_2pl_parameters(
    q: Tensor,
    y: Tensor,
    *,
    steps: int = 800,
    learning_rate: float = 0.05,
    lambda_a: float = DEFAULT_CONFIG.lambda_a,
    a_max: float = DEFAULT_CONFIG.a_max,
    seed: int = 0,
) -> tuple[Tensor, Tensor, list[float]]:
    """Fit a small fixed-state 2PL head for the synthetic contract test.

    The production path uses the jointly optimized ``ANMAOrigModel``.  This
    helper intentionally has no subject or text inputs; it is a deterministic
    parameter-recovery harness for the frozen 2PL equation and its numerical
    protections.
    """

    if q.ndim != 1 or y.ndim != 2 or y.shape[0] != q.shape[0]:
        raise ValueError("q must be (N,), y must be (N,K)")
    if steps < 1 or learning_rate <= 0.0 or seed < 0:
        raise ValueError("steps/learning_rate/seed are invalid")
    if not torch.isfinite(q).all() or not torch.isfinite(y).all() or bool(((y < 0) | (y > 1)).any()):
        raise ValueError("q/y contain invalid values")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        alpha_raw = torch.zeros(y.shape[1], dtype=q.dtype, device=q.device, requires_grad=True)
        b = torch.zeros(y.shape[1], dtype=q.dtype, device=q.device, requires_grad=True)
        optimizer = torch.optim.Adam((alpha_raw, b), lr=learning_rate)
        history: list[float] = []
        for _ in range(int(steps)):
            a = F.softplus(alpha_raw).clamp(max=float(a_max))
            p = torch.sigmoid(q[:, None] * a[None, :] - a[None, :] * b[None, :])
            loss = measurement_loss(y, p, alpha_raw, lambda_a=lambda_a)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            history.append(float(loss.detach().cpu().item()))
    return (
        F.softplus(alpha_raw.detach()).clamp(max=float(a_max)),
        b.detach(),
        history,
    )


def fisher_information(a: Tensor, p: Tensor) -> Tensor:
    if a.shape != p.shape:
        raise ValueError("a and p must have matching shapes")
    return a.square() * p * (1.0 - p)


def sentence_fisher_weights(
    information: Tensor,
    item_mask: Tensor,
    *,
    eta: float = DEFAULT_CONFIG.eta,
    epsilon: float = DEFAULT_CONFIG.epsilon,
) -> tuple[Tensor, Tensor]:
    """Mean item Fisher information, floor empty sentences, batch-normalize.

    Returns ``(tilde_w, w)``.  ``w`` is detached to implement stop-gradient;
    its batch mean is one whenever the batch contains finite positive mass.
    """

    if information.ndim != 2 or item_mask.shape != information.shape or item_mask.dtype != torch.bool:
        raise ValueError("information and item_mask must be rank-2 with bool mask")
    if not torch.isfinite(information).all() or bool((information < 0).any()):
        raise ValueError("Fisher information must be finite and non-negative")
    counts = item_mask.sum(dim=1)
    sums = (information * item_mask.to(information.dtype)).sum(dim=1)
    nonempty = counts > 0
    raw = sums / counts.clamp_min(1).to(information.dtype)
    if bool(nonempty.any()):
        baseline = raw[nonempty].median()
    else:
        # The specification defines the floor relative to the batch median;
        # an all-empty batch has no such median and must be surfaced rather
        # than silently assigned an invented scale.
        raise ValueError("Fisher floor is undefined when every sentence has no supported item")
    tilde = torch.where(nonempty, raw, float(eta) * baseline)
    total = tilde.sum()
    if not bool(torch.isfinite(total)) or float(total.detach()) <= float(epsilon):
        weights = torch.ones_like(tilde)
    else:
        weights = (tilde.numel() * tilde / (total + float(epsilon))).detach()
    return tilde, weights


def apply_warmup(weights: Tensor, step: int, warmup_steps: int) -> Tensor:
    if step < 0 or warmup_steps < 0:
        raise ValueError("step and warmup_steps must be non-negative")
    if weights.ndim != 1 or not torch.isfinite(weights).all():
        raise ValueError("weights must be a finite rank-1 tensor")
    if step < warmup_steps:
        return torch.ones_like(weights)
    return weights


def weighted_alignment_objective(
    alignment_loss: Tensor,
    weights: Tensor,
    measurement: Tensor,
    *,
    lambda_m: float = DEFAULT_CONFIG.lambda_m,
) -> Tensor:
    """The sentence-level objective in §6.15.4."""

    if alignment_loss.ndim != 1 or weights.shape != alignment_loss.shape:
        raise ValueError("alignment_loss and weights must be rank-1 and aligned")
    if measurement.ndim != 0:
        raise ValueError("measurement must be scalar")
    return (weights * alignment_loss).mean() + float(lambda_m) * measurement


class TextAmortizer(nn.Module):
    """Maps frozen text embeddings to ``(alpha,b)`` item parameters."""

    def __init__(self, text_dim: int, hidden_dim: int = DEFAULT_CONFIG.hidden_dim) -> None:
        super().__init__()
        if text_dim < 1 or hidden_dim < 1:
            raise ValueError("text_dim and hidden_dim must be positive")
        self.network = nn.Sequential(
            nn.Linear(text_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 2),
        )

    def forward(self, text_embeddings: Tensor) -> tuple[Tensor, Tensor]:
        if text_embeddings.ndim != 2 or not torch.isfinite(text_embeddings).all():
            raise ValueError("text_embeddings must be finite rank-2")
        values = self.network(text_embeddings)
        return values[:, 0], values[:, 1]


class TrialStateNet(nn.Module):
    """Maps each EEG latent to a scalar trial state; no subject ID input."""

    def __init__(self, latent_dim: int, hidden_dim: int = DEFAULT_CONFIG.hidden_dim) -> None:
        super().__init__()
        if latent_dim < 1 or hidden_dim < 1:
            raise ValueError("latent_dim and hidden_dim must be positive")
        self.network = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, latent: Tensor) -> Tensor:
        if latent.ndim != 2 or latent.shape[1] < 1 or not torch.isfinite(latent).all():
            raise ValueError("latent must be finite rank-2")
        return self.network(latent).squeeze(-1)


class ANMAOrigModel(nn.Module):
    """Small executable ANMA-orig measurement/weighting reference path."""

    def __init__(
        self,
        *,
        latent_dim: int,
        text_dim: int,
        config: ANMAConfig = DEFAULT_CONFIG,
        seed: int | None = None,
    ) -> None:
        if seed is not None and seed < 0:
            raise ValueError("seed must be non-negative")
        with torch.random.fork_rng(devices=[]):
            if seed is not None:
                torch.manual_seed(seed)
            super().__init__()
            self.config = config
            self.text_amortizer = TextAmortizer(text_dim, config.hidden_dim)
            self.trial_state = TrialStateNet(latent_dim, config.hidden_dim)

    def item_parameters(self, text_embeddings: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        alpha, b = self.text_amortizer(text_embeddings)
        a = F.softplus(alpha).clamp(max=self.config.a_max)
        return alpha, b, a

    def forward(
        self,
        latent: Tensor,
        text_embeddings: Tensor,
        item_indices: Tensor,
        item_mask: Tensor,
        y: Tensor,
        alignment_loss: Tensor,
        *,
        step: int = 0,
    ) -> dict[str, Tensor]:
        if item_indices.ndim != 2 or item_mask.shape != item_indices.shape:
            raise ValueError("item_indices and item_mask must be rank-2 and aligned")
        if y.shape != item_indices.shape or latent.shape[0] != item_indices.shape[0]:
            raise ValueError("latent/y/item batch dimensions must agree")
        if item_indices.dtype != torch.long or item_mask.dtype != torch.bool:
            raise TypeError("item_indices must be long and item_mask bool")
        if bool((item_indices < 0).any()) or bool((item_indices >= text_embeddings.shape[0]).any()):
            raise ValueError("item index outside text embedding table")
        alpha_all, b_all, a_all = self.item_parameters(text_embeddings)
        alpha = alpha_all[item_indices]
        b = b_all[item_indices]
        a = a_all[item_indices]
        q = center_scale_q(self.trial_state(latent), epsilon=self.config.epsilon)
        p, _ = two_pl_probability(q[:, None].expand_as(alpha), alpha, b, a_max=self.config.a_max)
        p = p.clamp(1e-7, 1.0 - 1e-7)
        active = item_mask
        if not bool(active.any()):
            raise ValueError("ANMA measurement loss requires at least one observed item")
        measure = measurement_loss(
            y.to(p.dtype)[active], p[active], alpha_all, lambda_a=self.config.lambda_a
        )
        information = fisher_information(a, p)
        tilde, weights = sentence_fisher_weights(
            information, item_mask, eta=self.config.eta, epsilon=self.config.epsilon
        )
        weights = apply_warmup(weights, step, self.config.warmup_steps)
        total = weighted_alignment_objective(
            alignment_loss, weights, measure, lambda_m=self.config.lambda_m
        )
        return {
            "q": q,
            "alpha": alpha,
            "b": b,
            "a": a,
            "p": p,
            "information": information,
            "tilde_weights": tilde,
            "weights": weights,
            "measurement_loss": measure,
            "total_loss": total,
        }


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    sorted_values = values[order]
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def spearman(values_a: Tensor | np.ndarray, values_b: Tensor | np.ndarray) -> float:
    a = np.asarray(torch.as_tensor(values_a).detach().cpu(), dtype=np.float64).reshape(-1)
    b = np.asarray(torch.as_tensor(values_b).detach().cpu(), dtype=np.float64).reshape(-1)
    if a.shape != b.shape or a.size < 2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        return float("nan")
    ra, rb = _rankdata(a), _rankdata(b)
    if np.std(ra) == 0.0 or np.std(rb) == 0.0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def partial_spearman(
    values_a: Tensor | np.ndarray,
    values_b: Tensor | np.ndarray,
    controls: Sequence[Tensor | np.ndarray] = (),
) -> float:
    """Spearman correlation after rank-residualizing shared covariates."""

    a = np.asarray(torch.as_tensor(values_a).detach().cpu(), dtype=np.float64).reshape(-1)
    b = np.asarray(torch.as_tensor(values_b).detach().cpu(), dtype=np.float64).reshape(-1)
    control_values = [
        np.asarray(torch.as_tensor(value).detach().cpu(), dtype=np.float64).reshape(-1)
        for value in controls
    ]
    if a.shape != b.shape or a.size < 3:
        return float("nan")
    if any(value.shape != a.shape for value in control_values):
        raise ValueError("partial-Spearman controls must match the target shape")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or any(
        not np.isfinite(value).all() for value in control_values
    ):
        return float("nan")
    ranked_a, ranked_b = _rankdata(a), _rankdata(b)
    if not control_values:
        return spearman(ranked_a, ranked_b)
    design = np.column_stack(
        [np.ones(a.size, dtype=np.float64)] + [_rankdata(value) for value in control_values]
    )
    residual_a = ranked_a - design @ np.linalg.lstsq(design, ranked_a, rcond=None)[0]
    residual_b = ranked_b - design @ np.linalg.lstsq(design, ranked_b, rcond=None)[0]
    if np.std(residual_a) == 0.0 or np.std(residual_b) == 0.0:
        return 0.0
    return float(np.corrcoef(residual_a, residual_b)[0, 1])


def rank_stability(parameter_vectors: Sequence[Tensor | np.ndarray]) -> dict[str, object]:
    """Report pairwise rank stability across seeds/folds/subsets."""

    vectors = [np.asarray(torch.as_tensor(value).detach().cpu()).reshape(-1) for value in parameter_vectors]
    if len(vectors) < 2:
        raise ValueError("rank stability requires at least two parameter vectors")
    if len({value.shape for value in vectors}) != 1:
        raise ValueError("rank-stability vectors must have matching shapes")
    pairwise = [
        spearman(vectors[left], vectors[right])
        for left in range(len(vectors))
        for right in range(left + 1, len(vectors))
    ]
    finite = np.asarray([value for value in pairwise if np.isfinite(value)], dtype=np.float64)
    return {
        "replicate_count": len(vectors),
        "pairwise": pairwise,
        "pairwise_min": float(finite.min()) if finite.size else float("nan"),
        "pairwise_median": float(np.median(finite)) if finite.size else float("nan"),
        "pairwise_max": float(finite.max()) if finite.size else float("nan"),
    }


def rankfit_plateau_step(
    evaluations: Sequence[tuple[int, float]],
    *,
    threshold: float = 0.005,
    consecutive: int = 2,
) -> int | None:
    """Return the first v3.6 RankFit plateau step, or ``None`` if absent."""

    if threshold != 0.005 or consecutive != 2:
        raise ValueError("RankFit plateau is frozen to two improvements below 0.005")
    if len(evaluations) < consecutive + 1:
        return None
    previous_step = -1
    previous_value: float | None = None
    below = 0
    for step, value in evaluations:
        if int(step) <= previous_step or not math.isfinite(float(value)):
            raise ValueError("RankFit evaluations must have increasing steps and finite values")
        if previous_value is not None:
            below = below + 1 if float(value) - previous_value < threshold else 0
            if below >= consecutive:
                return int(step)
        previous_step = int(step)
        previous_value = float(value)
    return None


def auroc(scores: Tensor | np.ndarray, labels: Tensor | np.ndarray) -> float:
    s = np.asarray(torch.as_tensor(scores).detach().cpu(), dtype=np.float64).reshape(-1)
    y = np.asarray(torch.as_tensor(labels).detach().cpu(), dtype=np.float64).reshape(-1)
    positives, negatives = y == 1, y == 0
    if not positives.any() or not negatives.any():
        return float("nan")
    ranks = _rankdata(s)
    return float((ranks[positives].sum() - positives.sum() * (positives.sum() + 1) / 2) / (positives.sum() * negatives.sum()))


def diagnostics(
    y: Tensor,
    p: Tensor,
    information: Tensor,
    *,
    weights: Tensor | None = None,
    item_mask: Tensor | None = None,
    sentence_length: Tensor | None = None,
    item_frequency: Tensor | None = None,
    surprisal: Tensor | None = None,
) -> dict[str, object]:
    """Compute the mandatory §6.15.7 diagnostics and red-line flags."""

    if y.ndim == 1:
        y = y[:, None]
    if p.ndim == 1:
        p = p[:, None]
    if information.ndim == 1:
        information = information[:, None]
    if item_mask is not None and item_mask.ndim == 1:
        item_mask = item_mask[:, None]
    if y.shape != p.shape or y.shape != information.shape:
        raise ValueError("y, p, and information must have identical shapes")
    y_matrix = y.detach()
    y_flat, p_flat, i_flat = y_matrix.reshape(-1), p.detach().reshape(-1), information.detach().reshape(-1)
    active_mask = torch.ones_like(y_matrix, dtype=torch.bool)
    if item_mask is not None:
        if item_mask.shape != y.shape or item_mask.dtype != torch.bool:
            raise ValueError("item_mask must match y and be bool")
        keep = item_mask.reshape(-1)
        active_mask = item_mask
        y_flat, p_flat, i_flat = y_flat[keep], p_flat[keep], i_flat[keep]
    mean_y = float(y_flat.float().mean().item()) if y_flat.numel() else float("nan")
    rho_band = float(((p_flat > 0.2) & (p_flat < 0.8)).float().mean().item()) if p_flat.numel() else float("nan")
    rho_ip = spearman(i_flat, p_flat)
    support = active_mask.sum(dim=0)
    item_accuracy = torch.where(
        support > 0,
        (y_matrix * active_mask.to(y_matrix.dtype)).sum(dim=0) / support.clamp_min(1).to(y_matrix.dtype),
        torch.full(support.shape, float("nan"), dtype=y_matrix.dtype, device=y_matrix.device),
    )
    finite_item_accuracy = item_accuracy[torch.isfinite(item_accuracy)]
    result: dict[str, object] = {
        "n_observations": int(y_flat.numel()),
        "mean_y": mean_y,
        "item_accuracy": [float(value) for value in item_accuracy.detach().cpu().tolist()],
        "item_support": [int(value) for value in support.detach().cpu().tolist()],
        "item_accuracy_min": float(finite_item_accuracy.min().item()) if finite_item_accuracy.numel() else float("nan"),
        "item_accuracy_max": float(finite_item_accuracy.max().item()) if finite_item_accuracy.numel() else float("nan"),
        "rho_band": rho_band,
        "spearman_information_probability": rho_ip,
        "heldout_auroc": auroc(p_flat, y_flat),
        "empty_sentence_count": int((active_mask.sum(dim=1) == 0).sum().item()),
    }
    flags = {
        "mean_accuracy_outside_target": bool(np.isfinite(mean_y) and (mean_y < 0.2 or mean_y > 0.8)),
        "information_band_degenerate": bool(np.isfinite(rho_band) and rho_band < 0.05),
        "information_monotonic_degenerate": bool(np.isfinite(rho_ip) and abs(rho_ip) > 0.95),
        "measurement_auroc_below_threshold": bool(
            np.isfinite(float(result["heldout_auroc"])) and float(result["heldout_auroc"]) < 0.55
        ),
    }
    result["red_line_flags"] = flags
    if weights is not None:
        result["weight_mean"] = float(weights.detach().mean().item())
        result["weight_min"] = float(weights.detach().min().item())
        result["weight_max"] = float(weights.detach().max().item())
        covariates = {
            name: covariate
            for name, covariate in (
            ("sentence_length", sentence_length),
            ("item_frequency", item_frequency),
            ("surprisal", surprisal),
            )
            if covariate is not None and covariate.numel() == weights.numel()
        }
        for name, covariate in covariates.items():
            controls = [value for other, value in covariates.items() if other != name]
            result[f"partial_spearman_weight_{name}"] = partial_spearman(
                weights,
                covariate,
                controls,
            )
    return result


def easiness_weights(c: Tensor, *, epsilon: float = DEFAULT_CONFIG.epsilon) -> Tensor:
    """Mandatory explicit easiness fallback when Fisher weighting degenerates."""

    if c.ndim != 2 or not torch.isfinite(c).all():
        raise ValueError("c must be finite rank-2")
    values = c.mean(dim=1)
    return (values.numel() * values / (values.sum() + epsilon)).detach()
