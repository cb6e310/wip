from __future__ import annotations

import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from methods.eq_anma import (  # noqa: E402
    EQANMAModel,
    contribution_soft_response,
    measurement_parameter_names,
)


def _batch(variant: str) -> tuple[EQANMAModel, dict[str, torch.Tensor]]:
    torch.manual_seed(7)
    model = EQANMAModel(feature_dim=6, text_dim=5, hidden_dim=8, variant=variant, lambda_m=1.0, seed=9)
    features = torch.randn(12, 6)
    text = torch.randn(7, 5)
    items = torch.tensor([[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6]] * 2)
    mask = torch.ones_like(items, dtype=torch.bool)
    u = torch.linspace(-2.0, 2.0, items.numel()).reshape_as(items)
    obs = contribution_soft_response(u, tau=0.7)
    gate = torch.tensor([1, 1, 0, 1, 0, 1, 1], dtype=torch.float32)
    return model, {"features": features, "text_embeddings": text, "item_indices": items, "item_mask": mask, "soft_observations": obs, "u_oof": u, "gate_by_item": gate}


def test_v0_v1_v2_are_finite_positive_and_stop_gradient() -> None:
    for variant in ("V0", "V1", "V2"):
        model, values = _batch(variant)
        result = model(**values, reference_features=values["features"])
        assert torch.isfinite(result.measurement_loss)
        assert torch.all(result.a > 0)
        assert abs(float(result.q.mean())) < 1e-5
        assert abs(float(result.q.std(unbiased=False)) - 1.0) < 1e-4
        assert not result.weights.requires_grad
        assert abs(float(result.weights.mean()) - 1.0) < 1e-5


def test_gate_and_v2_evidence_change_only_weight_mapping() -> None:
    v0, values = _batch("V0")
    v1, _ = _batch("V1")
    v2, _ = _batch("V2")
    v1.load_state_dict(v0.state_dict())
    v2.load_state_dict(v0.state_dict())
    r0 = v0(**values)
    r1 = v1(**values)
    r2 = v2(**values)
    assert torch.allclose(r0.p, r1.p)
    assert torch.allclose(r1.p, r2.p)
    assert not torch.allclose(r0.raw_sentence_score, r1.raw_sentence_score)
    assert not torch.allclose(r1.raw_sentence_score, r2.raw_sentence_score)


def test_no_subject_identifier_parameter_or_argument() -> None:
    model, _ = _batch("V1")
    assert all("subject" not in name.lower() for name in measurement_parameter_names(model))
    assert "subject" not in EQANMAModel.forward.__annotations__


def test_parameter_recovery_smoke_from_allowed_inputs() -> None:
    torch.manual_seed(4)
    n, k = 160, 4
    q_signal = torch.linspace(-2.5, 2.5, n)
    features = torch.stack([q_signal, q_signal.square(), torch.sin(q_signal)], dim=1)
    text = torch.eye(k)
    true_a = torch.tensor([0.7, 1.0, 1.4, 1.8])
    true_b = torch.tensor([-0.8, -0.2, 0.3, 0.9])
    items = torch.arange(k).repeat(n, 1)
    mask = torch.ones_like(items, dtype=torch.bool)
    probability = torch.sigmoid(true_a[None, :] * (q_signal[:, None] - true_b[None, :]))
    u = torch.logit(probability.clamp(1e-4, 1 - 1e-4))
    model = EQANMAModel(feature_dim=3, text_dim=k, hidden_dim=12, variant="V0", lambda_m=1.0, seed=3)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.03)
    for _ in range(240):
        result = model(features, text, items, mask, probability, u, torch.ones(k), reference_features=features)
        optimizer.zero_grad()
        result.measurement_loss.backward()
        optimizer.step()
    with torch.no_grad():
        alpha, fitted_b, fitted_a = model.item_parameters(text)
        rho_a = torch.corrcoef(torch.stack([fitted_a, true_a]))[0, 1]
        rho_b = torch.corrcoef(torch.stack([fitted_b, true_b]))[0, 1]
    assert float(rho_a) > 0.7
    assert float(rho_b) > 0.7
    assert torch.all(torch.nn.functional.softplus(alpha) > 0)
