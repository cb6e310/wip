from __future__ import annotations

import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from methods.direct_u_plus import direct_u_plus_weights, variant_ids, weight_diagnostics  # noqa: E402


def test_positive_mass_median_excludes_zeros_and_detaches() -> None:
    scores = torch.tensor([[1.0, 3.0], [-1.0, 0.0], [4.0, 0.0]], requires_grad=True)
    mask = torch.ones_like(scores, dtype=torch.bool)
    result = direct_u_plus_weights(scores, mask, gamma=1.0)
    assert torch.allclose(result.raw_sentence_score, torch.tensor([2.0, 0.0, 2.0]))
    assert torch.allclose(result.floored_score, torch.tensor([2.0, 0.2, 2.0]))
    assert result.floor_hit.tolist() == [False, True, False]
    assert not result.all_zero_batch
    assert not result.weights.requires_grad
    assert torch.allclose(result.weights.mean(), torch.tensor(1.0), atol=1e-6)


def test_all_zero_batch_is_uniform_and_not_floor_hit() -> None:
    scores = -torch.ones(4, 3)
    result = direct_u_plus_weights(scores, torch.ones_like(scores, dtype=torch.bool), gamma=2.0)
    assert result.all_zero_batch
    assert not bool(result.floor_hit.any())
    assert torch.equal(result.weights, torch.ones(4))


def test_empty_and_gated_sentences_receive_floor() -> None:
    scores = torch.tensor([[2.0, 1.0], [5.0, 4.0]])
    mask = torch.tensor([[True, True], [False, False]])
    gate = torch.tensor([1.0, 0.0])
    result = direct_u_plus_weights(scores, mask, gamma=0.5, gate=gate)
    assert result.raw_sentence_score[0] > 0
    assert result.raw_sentence_score[1] == 0
    assert bool(result.floor_hit[1])


def test_warmup_is_uniform_and_variant_grid_is_exact() -> None:
    scores = torch.tensor([[1.0], [4.0]])
    mask = torch.ones_like(scores, dtype=torch.bool)
    result = direct_u_plus_weights(scores, mask, gamma=1.0, step=2, warmup_steps=3)
    assert torch.equal(result.weights, torch.ones(2))
    assert len(variant_ids(gated=False)) == 12
    assert len(set(variant_ids(gated=True))) == 12


def test_weight_diagnostics_are_finite() -> None:
    report = weight_diagnostics(torch.tensor([0.5, 1.0, 1.5]))
    assert 0 <= report["normalized_entropy"] <= 1
    assert 0 <= report["gini"] <= 1
    assert len(report["quantiles_5_50_95"]) == 3
