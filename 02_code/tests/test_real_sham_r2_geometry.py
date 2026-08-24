from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.real_sham_r2_geometry import (  # noqa: E402
    ARMS,
    BASELINE_CELL,
    BASES,
    CELLS,
    EXPECTED_GEOMETRY_PROBES,
    EXPECTED_H_ONLY_Y0,
    EXPECTED_RIDGE_OPERATIONS,
    EXPECTED_TRANSFORM_LEDGERS,
    EXPECTED_V5_LEDGERS,
    INDUCTIVE_CELL,
    TASKS,
    TRANSDUCTIVE_CELLS,
    evaluate_r2_outcome,
    full_covariance_euclidean_alignment,
    validate_transform_ledgers,
    verify_immutable_parent_r0_r1,
)


class RealShamR2GeometryTests(unittest.TestCase):
    def test_scope_and_exact_budget_are_frozen(self) -> None:
        self.assertEqual(len(CELLS), 4)
        self.assertEqual(BASES, ("B0_RAW_A1", "B1_TOKEN_LOCAL_LATENT"))
        self.assertEqual(INDUCTIVE_CELL, "M0_STRICT_INDUCTIVE/B1_TOKEN_LOCAL_LATENT")
        self.assertNotIn("F3_EVENT_LOCKED", CELLS)
        self.assertEqual(EXPECTED_H_ONLY_Y0, 6)
        self.assertEqual(EXPECTED_GEOMETRY_PROBES, 96)
        self.assertEqual(EXPECTED_RIDGE_OPERATIONS, 102)
        self.assertEqual(EXPECTED_V5_LEDGERS, 102)
        self.assertEqual(EXPECTED_TRANSFORM_LEDGERS, 300)

    def test_d102_matches_literal_full_covariance_formula(self) -> None:
        real = np.asarray([[1.0, 2.0], [2.0, 1.0], [4.0, 5.0]], np.float32)
        arms = {arm: real + index for index, arm in enumerate(ARMS)}
        aligned, ledger = full_covariance_euclidean_alignment(
            arms,
            ["S1"] * 3,
            task="task1_nr",
            fold="inner_s0_t0",
            basis="toy",
            regime="fit",
        )
        z = real.astype(np.float64) - real.astype(np.float64).mean(axis=0)
        base = z.T @ z / 2
        lam = 1e-6 * np.trace(base) / 2
        covariance = (base + lam * np.eye(2))
        covariance = (covariance + covariance.T) / 2
        values, vectors = np.linalg.eigh(covariance)
        whitening = (vectors * np.maximum(values, lam) ** -0.5) @ vectors.T
        expected = z @ whitening
        np.testing.assert_allclose(aligned["real"], expected, rtol=1e-5, atol=1e-5)
        self.assertEqual(ledger[0]["lambda"], lam)
        self.assertTrue(ledger[0]["shared_across_arms"])
        self.assertFalse(ledger[0]["labels_used"])

    def test_d102_is_per_subject_and_same_transform_is_shared_across_arms(self) -> None:
        real = np.asarray(
            [[1.0, 0.0], [3.0, 2.0], [10.0, 1.0], [14.0, 5.0]], np.float32
        )
        arms = {arm: real + index * 0.25 for index, arm in enumerate(ARMS)}
        aligned, rows = full_covariance_euclidean_alignment(
            arms,
            ["S1", "S1", "S2", "S2"],
            task="task1_nr",
            fold="inner_s0_t0",
            basis="toy",
            regime="cross",
        )
        self.assertEqual(len(rows), 2)
        for indices in ([0, 1], [2, 3]):
            real_delta = aligned["trial_shuffle"][indices] - aligned["real"][indices]
            np.testing.assert_allclose(real_delta[0], real_delta[1], atol=1e-5)

    def test_d102_rejects_zero_trace_and_nonfinite_without_fallback(self) -> None:
        constant = np.ones((3, 2), np.float32)
        with self.assertRaisesRegex(ValueError, "zero/nonfinite trace"):
            full_covariance_euclidean_alignment(
                {arm: constant.copy() for arm in ARMS},
                ["S1"] * 3,
                task="task1_nr",
                fold="inner_s0_t0",
                basis="toy",
                regime="fit",
            )
        bad = constant.copy()
        bad[0, 0] = np.nan
        with self.assertRaises(ValueError):
            full_covariance_euclidean_alignment(
                {arm: bad.copy() for arm in ARMS},
                ["S1"] * 3,
                task="task1_nr",
                fold="inner_s0_t0",
                basis="toy",
                regime="fit",
            )

    def test_transform_ledger_validation_rejects_labels_or_fallback(self) -> None:
        real = np.asarray([[1.0, 0.0], [2.0, 3.0]], np.float32)
        _, rows = full_covariance_euclidean_alignment(
            {arm: real.copy() for arm in ARMS},
            ["S1", "S1"],
            task="task1_nr",
            fold="inner_s0_t0",
            basis="toy",
            regime="seen",
        )
        validate_transform_ledgers(rows, expected_count=1)
        for key in ("labels_used", "fallback_used"):
            changed = copy.deepcopy(rows)
            changed[0][key] = True
            with self.assertRaises(ValueError):
                validate_transform_ledgers(changed, expected_count=1)

    @staticmethod
    def _result_row(passing: bool) -> dict:
        subject_values = {f"S{i:02d}": float(passing) for i in range(15)}
        return {
            "seen": {},
            "cross": {
                "family_detected": passing,
                "metrics": {"delta_semantic": {"subject_values": subject_values}},
            },
        }

    def test_inductive_outcome_has_priority(self) -> None:
        results = {
            task: {cell: self._result_row(cell == INDUCTIVE_CELL) for cell in CELLS}
            for task in TASKS
        }
        for task in TASKS:
            results[task][BASELINE_CELL] = self._result_row(False)
        outcome, scope, reasons = evaluate_r2_outcome(results, contract_pass=True)
        self.assertEqual(outcome, "PASS_R2_INDUCTIVE_GEOMETRY")
        self.assertEqual(scope, list(TASKS))
        self.assertEqual(reasons, [])

    def test_m1_success_is_transductive_only(self) -> None:
        passing_cell = TRANSDUCTIVE_CELLS[0]
        results = {
            task: {cell: self._result_row(cell == passing_cell) for cell in CELLS}
            for task in TASKS
        }
        for task in TASKS:
            results[task][BASELINE_CELL] = self._result_row(False)
        outcome, scope, _ = evaluate_r2_outcome(results, contract_pass=True)
        self.assertEqual(outcome, "PASS_R2_TRANSDUCTIVE_GEOMETRY_ONLY")
        self.assertEqual(scope, list(TASKS))

    def test_contract_failure_is_invalid(self) -> None:
        outcome, scope, reasons = evaluate_r2_outcome({}, contract_pass=False)
        self.assertEqual(outcome, "INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC")
        self.assertEqual(scope, [])
        self.assertTrue(reasons)

    def test_parent_r0_r1_hashes_are_immutable(self) -> None:
        observed = verify_immutable_parent_r0_r1(PROJECT_ROOT)
        self.assertEqual(len(observed), 30)


if __name__ == "__main__":
    unittest.main()
