from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol.gate_a_population import (  # noqa: E402
    aggregate_subject_first,
    subject_cluster_bootstrap,
    synthetic_rows,
    validate_population,
)


class GateAPopulationTests(unittest.TestCase):
    def test_subject_first_equal_mean_and_no_zero_fill(self) -> None:
        artifact = aggregate_subject_first(synthetic_rows())
        self.assertEqual(validate_population(artifact), [])
        self.assertEqual(artifact["n_subject_clusters"], 2)
        self.assertEqual(artifact["subjects"][0]["mean_u"], 2.0)
        self.assertEqual(len(artifact["excluded_rows"]), 1)

    def test_order_is_byte_stable(self) -> None:
        first = aggregate_subject_first(list(reversed(synthetic_rows())))
        second = aggregate_subject_first(synthetic_rows())
        self.assertEqual(first, second)

    def test_cluster_bootstrap_is_subject_level_and_deterministic(self) -> None:
        artifact = aggregate_subject_first(synthetic_rows())
        first = subject_cluster_bootstrap(
            artifact, metric="mean_u", n_resamples=16, seed=20260813
        )
        second = subject_cluster_bootstrap(
            artifact, metric="mean_u", n_resamples=16, seed=20260813
        )
        self.assertEqual(first, second)
        self.assertEqual(first["n_subject_clusters"], 2)
        self.assertEqual(len(first["draws"]), 16)
        self.assertTrue(
            all(len(draw["subject_ids"]) == 2 for draw in first["draws"])
        )
        self.assertTrue(
            all(set(draw["subject_ids"]) <= {"S1", "S2"} for draw in first["draws"])
        )

    def test_cluster_bootstrap_rejects_cell_rows_and_implicit_randomness(self) -> None:
        with self.assertRaises(ValueError):
            subject_cluster_bootstrap(
                {"subjects": synthetic_rows()},
                metric="mean_u",
                n_resamples=4,
                seed=20260813,
            )
        artifact = aggregate_subject_first(synthetic_rows())
        with self.assertRaises(ValueError):
            subject_cluster_bootstrap(
                artifact, metric="mean_u", n_resamples=0, seed=20260813
            )


if __name__ == "__main__":
    unittest.main()
