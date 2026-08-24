"""Unified weight-only surfaces for the five frozen R6 arms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Sequence

import torch
from torch import Tensor

from methods.direct_u_plus import direct_u_plus_weights

from .controller import bounded_weights, direct_matched_h, shuffle_h_within_subject_trial
from .ledger import ComputeCounters


BASE = "BASE"
DIRECT = "DIRECT"
EQ_ANMA = "EQ_ANMA"
EQ_SHUFFLE = "EQ_SHUFFLE"
DIRECT_MATCHED = "DIRECT_MATCHED"
ARM_IDS = (BASE, DIRECT, EQ_ANMA, EQ_SHUFFLE, DIRECT_MATCHED)


@dataclass(frozen=True)
class R6ArmResult:
    arm_id: str
    variant_id: str
    raw_weight: Tensor
    normalized_weight: Tensor
    controller_fit_record_ids: tuple[Hashable, ...]
    data_examples_seen: int
    compute_counters: ComputeCounters


def r6_direct_variant_ids() -> tuple[str, ...]:
    no_warmup = tuple(
        f"direct|gamma={gamma:g}|score={score}|warmup=none"
        for gamma in (0.5, 1.0, 2.0)
        for score in ("u_oof", "u_min")
    )
    matched = tuple(
        f"direct|gamma=1|score={score}|warmup=EQ_matched"
        for score in ("u_oof", "u_min")
    )
    return no_warmup + matched


def _result(
    arm_id: str,
    variant_id: str,
    raw: Tensor,
    normalized: Tensor,
    fit_ids: Sequence[Hashable],
    examples: int,
    counters: ComputeCounters,
) -> R6ArmResult:
    if arm_id not in ARM_IDS:
        raise ValueError("unknown R6 arm")
    if int(examples) != int(normalized.numel()):
        raise ValueError("data_examples_seen must equal the weight vector length")
    return R6ArmResult(
        arm_id=arm_id,
        variant_id=variant_id,
        raw_weight=raw.detach(),
        normalized_weight=normalized.detach(),
        controller_fit_record_ids=tuple(fit_ids),
        data_examples_seen=int(examples),
        compute_counters=counters,
    )


def base_arm(count: int, counters: ComputeCounters) -> R6ArmResult:
    ones = torch.ones(int(count), dtype=torch.float64)
    return _result(BASE, "base", ones, ones, (), count, counters)


def eq_anma_arm(
    h: Tensor,
    gamma: float,
    fit_ids: Sequence[Hashable],
    counters: ComputeCounters,
) -> R6ArmResult:
    weights = bounded_weights(h, gamma)
    return _result(EQ_ANMA, f"eq|gamma={gamma:g}", weights.raw_weight, weights.normalized_weight, fit_ids, h.numel(), counters)


def eq_shuffle_arm(
    h: Tensor,
    gamma: float,
    group_ids: Sequence[Hashable] | Tensor,
    seed: int,
    fit_ids: Sequence[Hashable],
    counters: ComputeCounters,
) -> R6ArmResult:
    shuffled = shuffle_h_within_subject_trial(h, group_ids, seed)
    weights = bounded_weights(shuffled, gamma)
    return _result(EQ_SHUFFLE, f"eq_shuffle|gamma={gamma:g}|seed={int(seed)}", weights.raw_weight, weights.normalized_weight, fit_ids, h.numel(), counters)


def direct_matched_arm(
    score: Tensor,
    fit_mask: Tensor,
    gamma: float,
    fit_ids: Sequence[Hashable],
    counters: ComputeCounters,
) -> R6ArmResult:
    h = direct_matched_h(score, fit_mask)
    weights = bounded_weights(h, gamma)
    return _result(DIRECT_MATCHED, f"direct_matched|gamma={gamma:g}", weights.raw_weight, weights.normalized_weight, fit_ids, score.numel(), counters)


def direct_arm(
    scores: Tensor,
    item_mask: Tensor,
    *,
    gamma: float,
    score_version: str,
    warmup: str,
    fit_ids: Sequence[Hashable],
    counters: ComputeCounters,
) -> R6ArmResult:
    variant_id = f"direct|gamma={gamma:g}|score={score_version}|warmup={warmup}"
    if variant_id not in r6_direct_variant_ids():
        raise ValueError("DIRECT variant is outside the frozen eight-point grid")
    result = direct_u_plus_weights(
        scores,
        item_mask,
        gamma=float(gamma),
        step=0,
        warmup_steps=1 if warmup == "EQ_matched" else 0,
    )
    return _result(DIRECT, variant_id, result.floored_score, result.weights, fit_ids, scores.shape[0], counters)
