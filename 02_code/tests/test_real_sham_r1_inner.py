from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.real_sham_r1_inner import (  # noqa: E402
    ARMS,
    BASELINE_CANDIDATE,
    CANDIDATES,
    EXPECTED_EEG_PROBES,
    EXPECTED_EEG_V5_LEDGERS,
    EXPECTED_H_ONLY_Y0,
    EXPECTED_RIDGE_OPERATIONS,
    EXPECTED_TEXT_LEDGERS,
    EXPECTED_TEXT_RESIDUALIZERS,
    FOLDS,
    FRONTENDS,
    METRICS,
    TARGETS,
    TASKS,
    build_normalized_residual_vocabulary,
    build_text_residualizer_ledger,
    canonical_fit_row_indices,
    evaluate_r1_outcome,
    summarize_subject_first,
    target_rows,
    validate_text_residualizer_ledger,
    verify_immutable_parent_r0,
)


class RealShamR1InnerTests(unittest.TestCase):
    def test_scope_and_exact_budget_are_frozen(self) -> None:
        self.assertEqual(TASKS, ("task1_nr", "task2_tsr"))
        self.assertEqual(FOLDS, ("inner_s0_t0", "inner_s1_t0", "inner_s2_t0"))
        self.assertEqual(
            FRONTENDS,
            ("F0_A1_BP_CONCAT", "F1_LOGREL_BP", "F2_T8_FIXATION"),
        )
        self.assertEqual(TARGETS, ("Y0_RAW_MINILM", "Y1_H_RESIDUAL_MINILM"))
        self.assertEqual(
            ARMS,
            (
                "real",
                "trial_shuffle",
                "within_trial_unit_assignment_shuffle",
                "channel_block_permutation",
            ),
        )
        self.assertEqual(EXPECTED_H_ONLY_Y0, 6)
        self.assertEqual(EXPECTED_TEXT_RESIDUALIZERS, 6)
        self.assertEqual(EXPECTED_EEG_PROBES, 144)
        self.assertEqual(EXPECTED_RIDGE_OPERATIONS, 156)
        self.assertEqual(EXPECTED_EEG_V5_LEDGERS, 150)
        self.assertEqual(EXPECTED_TEXT_LEDGERS, 6)
        self.assertNotIn("F3_EVENT_LOCKED", FRONTENDS)
        self.assertEqual(len(CANDIDATES), 5)

    def test_canonical_fit_row_is_lexically_deterministic(self) -> None:
        rows = [
            {"item_id": "b", "observation_id": "obs-2"},
            {"item_id": "a", "observation_id": "obs-3"},
            {"item_id": "a", "observation_id": "obs-1"},
            {"item_id": "b", "observation_id": "obs-4"},
        ]
        items, indices, identities = canonical_fit_row_indices(rows, {"a", "b"})
        self.assertEqual(items, ["a", "b"])
        np.testing.assert_array_equal(indices, [2, 0])
        self.assertEqual(identities, ["obs-1", "obs-2"])

    def test_y1_residual_vocabulary_is_fixed_finite_and_normalized(self) -> None:
        rows = [
            {"item_id": "a", "observation_id": "a-2"},
            {"item_id": "a", "observation_id": "a-1"},
            {"item_id": "b", "observation_id": "b-1"},
        ]
        h = np.zeros((3, 384), dtype=np.float32)
        y0 = np.zeros((3, 384), dtype=np.float32)
        y0[0, 0] = 1.0
        y0[1, 1] = 1.0
        y0[2, 2] = 1.0
        model = {
            "weights": np.zeros((384, 384), dtype=np.float32),
            "intercept": np.zeros(384, dtype=np.float32),
        }
        items, vocabulary, positions, summary = build_normalized_residual_vocabulary(
            rows=rows,
            supported={"a", "b"},
            h_fit=h,
            y0_fit=y0,
            model=model,
        )
        self.assertEqual(items, ["a", "b"])
        self.assertEqual(positions, {"a": 0, "b": 1})
        np.testing.assert_allclose(np.linalg.norm(vocabulary, axis=1), 1.0)
        self.assertFalse(summary["fallback_used"])
        self.assertEqual(summary["seen_cross_refit_count"], 0)
        fixed = target_rows(rows, vocabulary, positions)
        np.testing.assert_array_equal(fixed[0], fixed[1])

    def test_y1_rejects_small_residual_without_fallback(self) -> None:
        rows = [{"item_id": "a", "observation_id": "a-1"}]
        zeros = np.zeros((1, 384), dtype=np.float32)
        model = {
            "weights": np.zeros((384, 384), dtype=np.float32),
            "intercept": np.zeros(384, dtype=np.float32),
        }
        with self.assertRaises(ValueError):
            build_normalized_residual_vocabulary(
                rows=rows,
                supported={"a"},
                h_fit=zeros,
                y0_fit=zeros,
                model=model,
            )

    def test_text_only_ledger_forbids_eeg_outer_and_refit(self) -> None:
        ledger = build_text_residualizer_ledger(
            operation_id="R1|task1_nr|inner_s0_t0|Y1_TEXT_RESIDUALIZER",
            task="task1_nr",
            fold="inner_s0_t0",
            fit_record_ids=["r1", "r2"],
            fit_row_count=2,
            summary={
                "supported_item_count": 2,
                "canonical_fit_observation_ids_sha256": "a" * 64,
            },
            input_hashes={"frozen": "b" * 64},
        )
        validate_text_residualizer_ledger(ledger)
        for field in ("eeg_loaded", "outer_test_read", "calibration_read"):
            changed = copy.deepcopy(ledger)
            changed[field] = True
            with self.assertRaises(ValueError):
                validate_text_residualizer_ledger(changed)
        changed = copy.deepcopy(ledger)
        changed["seen_cross_refit_count"] = 1
        with self.assertRaises(ValueError):
            validate_text_residualizer_ledger(changed)

    def test_family_uses_semantic_shams_not_channel_sentinel(self) -> None:
        rows = []
        for index in range(15):
            row = {
                "task": "task1_nr",
                "candidate": BASELINE_CANDIDATE,
                "regime": "cross",
                "subject_id": f"S{index:02d}",
                "fold": f"inner_s{index % 3}_t0",
                "delta_semantic": 1.0,
                "delta_legacy": -1.0,
                "delta_channel": -5.0,
                "u_oof": -1.0,
                "u_min": -6.0,
                "real_minus_trial_shuffle": 1.0,
                "real_minus_within_trial_unit_assignment_shuffle": 1.0,
                "real_minus_channel_block_permutation": -5.0,
                "max_selection_gap": 5.0,
            }
            row.update({f"logp_{arm}": -2.0 for arm in ARMS})
            rows.append(row)
        summary = summarize_subject_first(
            rows,
            task="task1_nr",
            candidate=BASELINE_CANDIDATE,
            regime="cross",
        )
        self.assertTrue(summary["family_detected"])
        self.assertLess(
            summary["metrics"]["real_minus_channel_block_permutation"]["estimate"],
            0.0,
        )

    def test_outcome_selection_uses_recovery_task_count_and_minimum(self) -> None:
        def candidate_row(delta: float, passing: bool) -> dict:
            return {
                "seen": {},
                "cross": {"family_detected": passing},
                "cross_recovery": {
                    "estimate": delta,
                    "ci95": [delta - 0.01, delta + 0.01],
                    "positive_subject_count": 15 if passing else 0,
                },
            }

        results = {task: {} for task in TASKS}
        for task in TASKS:
            for index, candidate in enumerate(CANDIDATES):
                results[task][candidate] = candidate_row(
                    0.10 + index * 0.01,
                    candidate in CANDIDATES[:2],
                )
        outcome, selected, scope, ranking, reasons = evaluate_r1_outcome(
            results, contract_pass=True
        )
        self.assertEqual(outcome, "PASS_R1_BOTH_TASKS")
        self.assertEqual(selected, CANDIDATES[1])
        self.assertEqual(scope, list(TASKS))
        self.assertEqual(ranking[0]["recovered_task_count"], 2)
        self.assertEqual(reasons, [])

    def test_contract_failure_has_only_invalid_outcome(self) -> None:
        outcome, selected, scope, ranking, reasons = evaluate_r1_outcome(
            {}, contract_pass=False
        )
        self.assertEqual(outcome, "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC")
        self.assertIsNone(selected)
        self.assertEqual(scope, [])
        self.assertEqual(ranking, [])
        self.assertTrue(reasons)

    def test_parent_and_r0_hashes_are_immutable(self) -> None:
        observed = verify_immutable_parent_r0(PROJECT_ROOT)
        self.assertEqual(len(observed), 20)


if __name__ == "__main__":
    unittest.main()
