from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.a1_failure_diagnosis import validate_aggregate_formal_output  # noqa: E402
from data.real_sham_r4_orthogonal import (  # noqa: E402
    ARMS,
    BASELINE_METHOD,
    CANDIDATE_METHOD,
    EXPECTED_C1_FULL_X,
    EXPECTED_C1_FULL_Y,
    EXPECTED_C1_OOF_X,
    EXPECTED_C1_OOF_Y,
    EXPECTED_C1_RESIDUAL_PROBES,
    EXPECTED_FINAL_V5_LEDGERS,
    EXPECTED_NUISANCE_LEDGERS,
    EXPECTED_P0_H_ONLY,
    EXPECTED_P0_JOINT,
    EXPECTED_RIDGE_OPERATIONS,
    METHODS,
    TASKS,
    evaluate_r4_outcome,
    orthogonal_query,
    subject_blocks,
    validate_crossfit_audits,
    validate_nuisance_ledgers,
    validate_operation_contract,
    validate_r4_formal_output,
    verify_immutable_parent_r0_r1_r2_r3,
)


class RealShamR4OrthogonalTests(unittest.TestCase):
    def test_scope_and_exact_budget_are_frozen(self) -> None:
        self.assertEqual(
            METHODS,
            ("P0_JOINT_RIDGE_REPLICATION", "C1_SUBJECT_BLOCK_ORTHOGONAL"),
        )
        self.assertEqual(EXPECTED_P0_H_ONLY, 6)
        self.assertEqual(EXPECTED_P0_JOINT, 24)
        self.assertEqual(EXPECTED_C1_OOF_Y, 30)
        self.assertEqual(EXPECTED_C1_OOF_X, 120)
        self.assertEqual(EXPECTED_C1_FULL_Y, 6)
        self.assertEqual(EXPECTED_C1_FULL_X, 24)
        self.assertEqual(EXPECTED_C1_RESIDUAL_PROBES, 24)
        self.assertEqual(EXPECTED_RIDGE_OPERATIONS, 234)
        self.assertEqual(EXPECTED_FINAL_V5_LEDGERS, 54)
        self.assertEqual(EXPECTED_NUISANCE_LEDGERS, 180)

    def test_subject_blocks_are_exact_deterministic_sha256_5x2(self) -> None:
        subjects = [f"S{i:02d}" for i in range(10)]
        blocks = subject_blocks(
            list(reversed(subjects)), task="task1_nr", inner_cell_id="cell-A"
        )
        ordered = sorted(
            subjects,
            key=lambda subject: (
                hashlib.sha256(
                    f"20260813|task1_nr|cell-A|{subject}".encode("utf-8")
                ).hexdigest(),
                subject,
            ),
        )
        self.assertEqual(blocks, [ordered[index : index + 2] for index in range(0, 10, 2)])
        self.assertEqual(len(blocks), 5)
        self.assertTrue(all(len(block) == 2 for block in blocks))

    def test_subject_blocks_reject_non_ten_source_subjects(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            subject_blocks(
                [f"S{i}" for i in range(9)], task="task1_nr", inner_cell_id="cell"
            )

    @staticmethod
    def _audit() -> dict:
        return {
            "task": "task1_nr",
            "fold": "inner_s0_t0",
            "blocks": [[f"S{i}", f"S{i+1}"] for i in range(0, 10, 2)],
            "block_assignment_source": "fit_subject_ids_only",
            "heldout_subject_overlap_max": 0,
            "oof_row_coverage_min": 1,
            "oof_row_coverage_max": 1,
            "m_y_shared_across_arms": True,
            "m_x_arm_symmetric_scope_capacity_algorithm": True,
            "residual_probe_840d_without_h": True,
            "same_rows_all_four_arms": True,
            "seen_cross_block_fit_support_normalizer_or_statistics_use": False,
            "subject_item_task_sham_label_model_input": False,
            "fallback_used": False,
        }

    def test_crossfit_audit_enforces_zero_overlap_one_oof_and_symmetry(self) -> None:
        audit = self._audit()
        validate_crossfit_audits([audit], expected_count=1)
        for key, value in (
            ("heldout_subject_overlap_max", 1),
            ("oof_row_coverage_max", 2),
            ("m_y_shared_across_arms", False),
            ("m_x_arm_symmetric_scope_capacity_algorithm", False),
            ("residual_probe_840d_without_h", False),
            ("seen_cross_block_fit_support_normalizer_or_statistics_use", True),
        ):
            changed = copy.deepcopy(audit)
            changed[key] = value
            with self.assertRaises(ValueError):
                validate_crossfit_audits([changed], expected_count=1)

    def test_full_source_scoring_formula_is_literal(self) -> None:
        h = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        x = np.arange(2 * 840, dtype=np.float32).reshape(2, 840) / 1000.0
        m_y = {
            "weights": np.zeros((2, 384), dtype=np.float32),
            "intercept": np.ones(384, dtype=np.float32),
        }
        m_x = {
            "weights": np.zeros((2, 840), dtype=np.float32),
            "intercept": np.full(840, 0.25, dtype=np.float32),
        }
        beta_weights = np.zeros((840, 384), dtype=np.float32)
        beta_weights[:384] = np.eye(384, dtype=np.float32)
        beta = {
            "weights": beta_weights,
            "intercept": np.full(384, 0.5, dtype=np.float32),
        }
        observed = orthogonal_query(
            h, x, m_y_full=m_y, m_x_full=m_x, beta_arm=beta
        )
        expected = 1.0 + (x[:, :384] - 0.25) + 0.5
        np.testing.assert_allclose(observed, expected, rtol=1e-6, atol=1e-6)

    @staticmethod
    def _nuisance(index: int) -> dict:
        return {
            "operation_id": f"n{index}",
            "heldout_subjects": ["S0", "S1"] if index < 150 else [],
            "train_subjects": [f"S{i}" for i in range(2, 10)]
            if index < 150
            else [f"S{i}" for i in range(10)],
            "heldout_subject_overlap": 0,
            "alpha": 1.0,
            "fallback_used": False,
            "model_input_role": "H_full",
            "model_target_role": "matching_arm_EEG",
            "arm": ARMS[index % 4],
            "target_dimension": 840,
            "seen_cross_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
            "fit_record_ids_sha256": "a" * 64,
            "fit_observation_ids_sha256": "b" * 64,
            "symmetric_scope_sha256": "c" * 64,
        }

    def test_nuisance_ledger_rejects_heldout_overlap_and_forbidden_inputs(self) -> None:
        row = self._nuisance(0)
        validate_nuisance_ledgers([row], expected_count=1)
        changed = copy.deepcopy(row)
        changed["train_subjects"].append("S0")
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_nuisance_ledgers([changed], expected_count=1)
        changed = copy.deepcopy(row)
        changed["model_input_role"] = "H_plus_subject_id"
        with self.assertRaisesRegex(ValueError, "H only"):
            validate_nuisance_ledgers([changed], expected_count=1)

    def test_operation_contract_enforces_234_54_180_and_residual_without_h(self) -> None:
        breakdown = (
            [("P0_H_ONLY", 6), ("P0_JOINT_PROBE", 24),
             ("C1_OOF_Y_NUISANCE", 30), ("C1_OOF_X_NUISANCE", 120),
             ("C1_FULL_Y_NUISANCE", 6), ("C1_FULL_X_NUISANCE", 24),
             ("C1_RESIDUAL_PROBE", 24)]
        )
        operations = []
        index = 0
        for kind, count in breakdown:
            for _ in range(count):
                operations.append(
                    {
                        "operation_id": f"f{index}" if index < 54 else f"n{index-54}",
                        "operation_kind": kind,
                        "input_role": "EEG_residual_840D_only"
                        if kind == "C1_RESIDUAL_PROBE"
                        else "H_full",
                        "input_dimension": 840 if kind == "C1_RESIDUAL_PROBE" else 2,
                        "target_dimension": 384,
                    }
                )
                index += 1
        final = [
            {
                "fit_id": f"f{i}",
                "outer_test_record_ids_read": [],
                "calibration_record_ids": [],
                "r4_scope": {},
            }
            for i in range(54)
        ]
        nuisance = [self._nuisance(i) for i in range(180)]
        validate_operation_contract(operations, final, nuisance)
        changed = copy.deepcopy(operations)
        residual = next(
            row for row in changed if row["operation_kind"] == "C1_RESIDUAL_PROBE"
        )
        residual["input_dimension"] = 842
        with self.assertRaisesRegex(ValueError, "contains H"):
            validate_operation_contract(changed, final, nuisance)

    @staticmethod
    def _result_row(passing: bool) -> dict:
        values = {f"S{i:02d}": float(passing) for i in range(15)}
        return {
            "seen": {},
            "cross": {
                "family_detected": passing,
                "metrics": {"delta_semantic": {"subject_values": values}},
            },
        }

    def test_outcomes_cover_both_limited_fail_and_invalid(self) -> None:
        for passing_tasks, expected in (
            (set(TASKS), "PASS_R4_ORTHOGONAL_BOTH_TASKS"),
            ({TASKS[0]}, "PASS_R4_ORTHOGONAL_LIMITED_ONE_TASK"),
            (set(), "FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC"),
        ):
            results = {
                task: {
                    BASELINE_METHOD: self._result_row(False),
                    CANDIDATE_METHOD: self._result_row(task in passing_tasks),
                }
                for task in TASKS
            }
            outcome, scope, reasons = evaluate_r4_outcome(results, contract_pass=True)
            self.assertEqual(outcome, expected)
            self.assertEqual(scope, [task for task in TASKS if task in passing_tasks])
            self.assertEqual(reasons, [])
        outcome, scope, reasons = evaluate_r4_outcome({}, contract_pass=False)
        self.assertEqual(outcome, "INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC")
        self.assertEqual(scope, [])
        self.assertTrue(reasons)

    def test_formal_contract_contains_no_model_arrays(self) -> None:
        contract = {
            "methods": list(METHODS),
            "residual_probe_contains_h": False,
            "outer_reads": 0,
            "calibration_reads": 0,
        }
        self.assertTrue(validate_aggregate_formal_output(contract)["pass"])
        self.assertTrue(validate_r4_formal_output(contract)["pass"])
        for forbidden in ("weights", "features", "query", "queries", "logits"):
            self.assertFalse(validate_r4_formal_output({forbidden: []})["pass"])

    def test_parent_r0_r1_r2_r3_hashes_are_immutable(self) -> None:
        observed = verify_immutable_parent_r0_r1_r2_r3(PROJECT_ROOT)
        self.assertEqual(len(observed), 51)


if __name__ == "__main__":
    unittest.main()
