from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.real_sham_r3_subject_balanced import (  # noqa: E402
    ARMS,
    BASELINE_METHOD,
    CANDIDATE_METHOD,
    EXPECTED_EEG_PROBES,
    EXPECTED_GROUP_SCOPES,
    EXPECTED_H_ONLY_FITS,
    EXPECTED_RIDGE_OPERATIONS,
    EXPECTED_V5_LEDGERS,
    METHODS,
    TASKS,
    evaluate_r3_outcome,
    subject_item_group_means,
    validate_group_summaries,
    verify_immutable_parent_r0_r1_r2,
)


class RealShamR3SubjectBalancedTests(unittest.TestCase):
    @staticmethod
    def _metadata() -> list[dict[str, str]]:
        return [
            {"subject_id": "S1", "item_id": "I1", "observation_id": "O1"},
            {"subject_id": "S1", "item_id": "I1", "observation_id": "O2"},
            {"subject_id": "S1", "item_id": "I2", "observation_id": "O3"},
            {"subject_id": "S2", "item_id": "I1", "observation_id": "O4"},
        ]

    def test_scope_and_exact_budget_are_frozen(self) -> None:
        self.assertEqual(
            METHODS, ("P0_OBSERVATION_WEIGHTED", "P1_SUBJECT_ITEM_BALANCED")
        )
        self.assertEqual(BASELINE_METHOD, METHODS[0])
        self.assertEqual(CANDIDATE_METHOD, METHODS[1])
        self.assertEqual(EXPECTED_H_ONLY_FITS, 12)
        self.assertEqual(EXPECTED_EEG_PROBES, 48)
        self.assertEqual(EXPECTED_RIDGE_OPERATIONS, 60)
        self.assertEqual(EXPECTED_V5_LEDGERS, 60)
        self.assertEqual(EXPECTED_GROUP_SCOPES, 6)

    def test_p1_is_exact_arithmetic_mean_per_fit_subject_item_group(self) -> None:
        real = np.zeros((4, 840), dtype=np.float32)
        real[:, 0] = [1.0, 3.0, 10.0, 20.0]
        arms = {arm: real + index for index, arm in enumerate(ARMS)}
        grouped, metadata, summary = subject_item_group_means(
            arms, self._metadata(), task="task1_nr", fold="inner_s0_t0"
        )
        self.assertEqual(grouped["real"].shape, (3, 840))
        np.testing.assert_allclose(grouped["real"][:, 0], [2.0, 10.0, 20.0])
        np.testing.assert_allclose(
            grouped["trial_shuffle"][:, 0], [3.0, 11.0, 21.0]
        )
        self.assertEqual(
            [(row["subject_id"], row["item_id"]) for row in metadata],
            [("S1", "I1"), ("S1", "I2"), ("S2", "I1")],
        )
        self.assertEqual(summary["fit_observation_count"], 4)
        self.assertEqual(summary["group_count"], 3)
        self.assertEqual(summary["group_size"]["maximum"], 2)
        self.assertTrue(summary["equal_group_weight"])

    def test_grouping_audit_forbids_scoring_row_or_subject_probe_use(self) -> None:
        values = np.arange(4 * 840, dtype=np.float32).reshape(4, 840)
        _, _, summary = subject_item_group_means(
            {arm: values.copy() for arm in ARMS},
            self._metadata(),
            task="task1_nr",
            fold="inner_s0_t0",
        )
        validate_group_summaries([summary], expected_count=1)
        for field in (
            "seen_cross_rows_used_for_grouping_weight_vocabulary_or_threshold",
            "subject_id_input_to_probe",
        ):
            changed = copy.deepcopy(summary)
            changed[field] = True
            with self.assertRaises(ValueError):
                validate_group_summaries([changed], expected_count=1)

    def test_grouping_rejects_nonfinite_or_wrong_basis_without_fallback(self) -> None:
        values = np.ones((4, 840), dtype=np.float32)
        bad = values.copy()
        bad[0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            subject_item_group_means(
                {arm: (bad.copy() if arm == "real" else values.copy()) for arm in ARMS},
                self._metadata(),
                task="task1_nr",
                fold="inner_s0_t0",
            )
        with self.assertRaisesRegex(ValueError, "840D"):
            subject_item_group_means(
                {arm: np.ones((4, 10), dtype=np.float32) for arm in ARMS},
                self._metadata(),
                task="task1_nr",
                fold="inner_s0_t0",
            )

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

    def test_p1_is_the_only_candidate_that_can_pass(self) -> None:
        results = {
            task: {
                BASELINE_METHOD: self._result_row(False),
                CANDIDATE_METHOD: self._result_row(True),
            }
            for task in TASKS
        }
        outcome, scope, reasons = evaluate_r3_outcome(results, contract_pass=True)
        self.assertEqual(outcome, "PASS_R3_SUBJECT_BALANCED_INNER")
        self.assertEqual(scope, list(TASKS))
        self.assertEqual(reasons, [])
        self.assertFalse(results[TASKS[0]][BASELINE_METHOD]["recovery_pass"])
        self.assertTrue(results[TASKS[0]][CANDIDATE_METHOD]["recovery_pass"])

    def test_no_candidate_is_a_valid_negative_diagnostic(self) -> None:
        results = {
            task: {method: self._result_row(False) for method in METHODS}
            for task in TASKS
        }
        outcome, scope, reasons = evaluate_r3_outcome(results, contract_pass=True)
        self.assertEqual(outcome, "FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC")
        self.assertEqual(scope, [])
        self.assertEqual(reasons, [])

    def test_contract_failure_is_invalid(self) -> None:
        outcome, scope, reasons = evaluate_r3_outcome({}, contract_pass=False)
        self.assertEqual(outcome, "INVALID_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC")
        self.assertEqual(scope, [])
        self.assertTrue(reasons)

    def test_parent_r0_r1_r2_hashes_are_immutable(self) -> None:
        observed = verify_immutable_parent_r0_r1_r2(PROJECT_ROOT)
        self.assertEqual(len(observed), 41)


if __name__ == "__main__":
    unittest.main()
