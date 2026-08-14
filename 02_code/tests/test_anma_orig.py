from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from methods.anma_orig import (  # noqa: E402
    ANMAConfig,
    ANMAOrigModel,
    apply_warmup,
    construct_observations,
    diagnostics,
    fisher_information,
    fit_2pl_parameters,
    measurement_loss,
    partial_spearman,
    rank_stability,
    rankfit_plateau_step,
    select_n_item,
    sentence_fisher_weights,
    spearman,
    two_pl_probability,
)


class ANMAOrigTests(unittest.TestCase):
    def test_restricted_observations_renormalize_candidates(self) -> None:
        log_probs = torch.log_softmax(torch.tensor([[3.0, 1.0, 0.0], [0.0, 2.0, 1.0]]), dim=1)
        observed = construct_observations(
            log_probs,
            torch.tensor([0, 1]),
            torch.tensor([[0, 1], [1, 2]]),
        )
        self.assertTrue(torch.equal(observed.y, torch.ones(2)))
        self.assertTrue(torch.allclose(observed.c, torch.tensor([0.880797, 0.731059]), atol=1e-5))

    def test_n_item_selection_is_closest_to_half_with_deterministic_tie(self) -> None:
        values = {
            2: torch.tensor([0.2, 0.3]),
            4: torch.tensor([0.45, 0.55]),
            10: torch.tensor([0.4, 0.4]),
            50: torch.tensor([0.7, 0.7]),
        }
        selected = select_n_item(values)
        self.assertEqual(selected.selected, 4)
        self.assertAlmostEqual(selected.mean_accuracy[4], 0.5)

    def test_2pl_parameter_recovery_and_positive_discrimination(self) -> None:
        torch.manual_seed(42)
        q = torch.linspace(-3.0, 3.0, 512)
        true_a = torch.tensor([1.6, 0.8, 2.4])
        true_b = torch.tensor([-0.4, 0.2, 0.7])
        probabilities = torch.sigmoid(true_a[None, :] * (q[:, None] - true_b[None, :]))
        observations = torch.bernoulli(probabilities)
        fitted_a, fitted_b, history = fit_2pl_parameters(q, observations, steps=1200, seed=4)
        self.assertLess(history[-1], history[0])
        self.assertTrue(torch.all(fitted_a > 0))
        self.assertGreater(float(torch.corrcoef(torch.stack((fitted_a, true_a)))[0, 1]), 0.9)
        self.assertGreater(float(torch.corrcoef(torch.stack((fitted_b, true_b)))[0, 1]), 0.8)

    def test_fisher_mean_floor_and_stop_gradient(self) -> None:
        q = torch.tensor([-1.0, 0.0, 1.0])
        alpha = torch.tensor([0.0, 0.5, 1.0])
        p, a = two_pl_probability(q, alpha, torch.zeros(3))
        information = fisher_information(a, p)
        mask = torch.tensor([[True, True], [True, False], [False, False]])
        info = torch.tensor([[0.1, 0.2], [0.2, 0.3], [0.4, 0.5]])
        tilde, weights = sentence_fisher_weights(info, mask)
        self.assertTrue(torch.isfinite(tilde).all())
        self.assertTrue(torch.isfinite(weights).all())
        self.assertAlmostEqual(float(weights.mean()), 1.0, places=5)
        self.assertFalse(weights.requires_grad)
        self.assertTrue(torch.equal(apply_warmup(weights, 0, 2), torch.ones(3)))

    def test_model_has_no_subject_input_and_finite_objective(self) -> None:
        torch.manual_seed(3)
        model = ANMAOrigModel(latent_dim=4, text_dim=5, seed=3)
        latent = torch.randn(6, 4)
        text = torch.randn(3, 5)
        item_indices = torch.tensor([[0, 1], [1, 2], [0, 2], [0, 1], [1, 2], [0, 2]])
        item_mask = torch.ones_like(item_indices, dtype=torch.bool)
        y = torch.tensor([[1, 0], [1, 1], [0, 1], [1, 0], [0, 1], [1, 1]], dtype=torch.float32)
        alignment = torch.linspace(0.1, 0.6, 6)
        result = model(latent, text, item_indices, item_mask, y, alignment)
        self.assertTrue(torch.isfinite(result["total_loss"]))
        self.assertTrue(torch.isfinite(result["weights"]).all())
        self.assertFalse(result["weights"].requires_grad)
        self.assertAlmostEqual(float(result["weights"].mean()), 1.0, places=5)

    def test_alpha_regularization_is_over_item_parameters_not_repeated_trials(self) -> None:
        y = torch.tensor([1.0, 0.0])
        p = torch.tensor([0.8, 0.2])
        alpha = torch.tensor([0.3, -0.7, 1.1])
        loss = measurement_loss(y, p, alpha, lambda_a=1.0)
        expected = torch.nn.functional.binary_cross_entropy(p, y) + alpha.square().mean()
        self.assertTrue(torch.allclose(loss, expected))

    def test_diagnostics_raise_degenerate_information_flags(self) -> None:
        y = torch.zeros(20)
        p = torch.linspace(0.99, 0.999, 20)
        info = p.clone()
        report = diagnostics(y, p, info)
        flags = report["red_line_flags"]
        self.assertTrue(flags["mean_accuracy_outside_target"])
        self.assertTrue(flags["information_band_degenerate"])
        self.assertTrue(flags["information_monotonic_degenerate"])

    def test_spearman_constant_is_finite_fallback(self) -> None:
        self.assertEqual(spearman(torch.ones(4), torch.arange(4)), 0.0)

    def test_partial_correlations_rank_stability_and_warmup_plateau(self) -> None:
        control = torch.arange(20, dtype=torch.float32)
        x = control + torch.tensor([0.0, 1.0] * 10)
        y = control + torch.tensor([1.0, 0.0] * 10)
        value = partial_spearman(x, y, controls=[control])
        self.assertTrue(np.isfinite(value))
        stability = rank_stability([torch.arange(8), torch.arange(8) + 0.01])
        self.assertAlmostEqual(stability["pairwise_min"], 1.0)
        self.assertEqual(
            rankfit_plateau_step([(10, 0.4), (20, 0.403), (30, 0.406)]),
            30,
        )
        self.assertIsNone(rankfit_plateau_step([(10, 0.4), (20, 0.5), (30, 0.6)]))


if __name__ == "__main__":
    unittest.main()
