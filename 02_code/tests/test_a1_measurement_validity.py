from __future__ import annotations

import copy
import gzip
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import yaml


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))
sys.path.insert(0, str(CODE_ROOT / "scripts"))

from data.a1_admission import deterministic_gzip_jsonl  # noqa: E402
from data.a1_failure_diagnosis import validate_aggregate_formal_output  # noqa: E402
from data.a1_measurement_validity import (  # noqa: E402
    ALPHAS,
    EXPECTED_AMENDMENT_FITS,
    EXPECTED_INJECTION_FITS,
    EXPECTED_TOTAL_FITS,
    IMMUTABLE_HASHES,
    SUBJECT_FOLDS,
    combine_amendment_summaries,
    inject_after_normalizer,
    projection_matrix,
    semantic_code,
    spearman_rho,
    summarize_amendment_fold,
    summarize_curve,
    summarize_injection_rows,
    verify_immutable_evidence,
)
from run_a1_measurement_validity import (  # noqa: E402
    evaluate_outcome,
    planned_state_transition,
)


TASKS = ("task1_nr", "task2_tsr")
REAL_AUDIT = PROJECT_ROOT / "04_results/audits/a1_measurement_validity.json"


class A1MeasurementValidityContractTests(unittest.TestCase):
    def test_exact_fit_grid_subject_contract_and_projection_are_frozen(self) -> None:
        self.assertEqual(EXPECTED_AMENDMENT_FITS, 8)
        self.assertEqual(EXPECTED_INJECTION_FITS, 192)
        self.assertEqual(EXPECTED_TOTAL_FITS, 200)
        self.assertEqual(ALPHAS, (0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0))
        for task in TASKS:
            folds = SUBJECT_FOLDS[task]
            union = set().union(*(set(value) for value in folds.values()))
            self.assertEqual(sum(len(value) for value in folds.values()), 15)
            self.assertEqual(len(union), 15)
        first, first_meta = projection_matrix()
        second, second_meta = projection_matrix()
        self.assertEqual(first.shape, (840, 384))
        self.assertEqual(first.dtype, np.dtype("<f4"))
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(first_meta, second_meta)

    def test_semantic_code_is_finite_840d_and_has_frozen_norm(self) -> None:
        matrix, _ = projection_matrix()
        embedding = np.linspace(-1.0, 1.0, 384, dtype=np.float32)
        code = semantic_code(matrix, embedding)
        self.assertEqual(code.shape, (840,))
        self.assertEqual(code.dtype, np.dtype("<f4"))
        self.assertTrue(np.isfinite(code).all())
        self.assertAlmostEqual(float(np.linalg.norm(code)), np.sqrt(840.0), places=4)
        with self.assertRaises(ValueError):
            semantic_code(matrix, np.ones(383, dtype=np.float32))

    def test_injection_is_row_item_bound_and_alpha_zero_byte_identical(self) -> None:
        matrix, _ = projection_matrix()
        normalized = np.arange(3 * 840, dtype=np.float32).reshape(3, 840) / 1000
        rows = [{"surface": "a"}, {"surface": "b"}, {"surface": "a"}]
        vectors = {
            "a": np.linspace(-1.0, 1.0, 384, dtype=np.float32),
            "b": np.linspace(1.0, -1.0, 384, dtype=np.float32),
        }
        zero = inject_after_normalizer(
            normalized, rows, alpha=0.0, matrix=matrix, item_vectors=vectors
        )
        self.assertEqual(zero.tobytes(), normalized.tobytes())
        injected = inject_after_normalizer(
            normalized, rows, alpha=0.3, matrix=matrix, item_vectors=vectors
        )
        np.testing.assert_allclose(
            injected[0] - normalized[0],
            injected[2] - normalized[2],
            rtol=1e-5,
            atol=2e-7,
        )
        self.assertFalse(
            np.array_equal(injected[0] - normalized[0], injected[1] - normalized[1])
        )
        with self.assertRaises(ValueError):
            inject_after_normalizer(
                normalized, rows, alpha=0.2, matrix=matrix, item_vectors=vectors
            )

    def test_d49_requires_exact_frozen_subject_set_and_combines_15_equally(self) -> None:
        task = "task1_nr"
        old_subjects = SUBJECT_FOLDS[task]["inner_s0_t0"]
        old = {
            "paired_oracle_minus_h_logp": {
                "subject_values": {subject: 1.0 for subject in old_subjects}
            },
            "per_subject_r_at_1": {subject: 1.0 for subject in old_subjects},
        }
        new = []
        for fold in ("inner_s1_t0", "inner_s2_t0"):
            subjects = SUBJECT_FOLDS[task][fold]
            new.append(
                {
                    "fold": fold,
                    "subjects": list(subjects),
                    "subject_mean_logp_gains": {
                        subject: 1.0 for subject in subjects
                    },
                    "per_subject_oracle_r_at_1": {
                        subject: 1.0 for subject in subjects
                    },
                }
            )
        result = combine_amendment_summaries(task=task, old_s0=old, new_folds=new)
        self.assertEqual(result["subject_count"], 15)
        self.assertEqual(result["paired_oracle_minus_h_logp"]["n_subjects"], 15)
        self.assertTrue(result["pass"])
        broken = copy.deepcopy(new)
        broken[0]["subjects"][0] = old_subjects[0]
        with self.assertRaises(ValueError):
            combine_amendment_summaries(task=task, old_s0=old, new_folds=broken)

    def test_d49_fold_rejects_missing_subject_and_row_contract_mutation(self) -> None:
        task = "task2_tsr"
        fold = "inner_s1_t0"
        subjects = list(SUBJECT_FOLDS[task][fold])
        repeated = [subject for subject in subjects for _ in range(2)]
        result = summarize_amendment_fold(
            task=task,
            fold=fold,
            h_logp=np.zeros(10),
            oracle_logp=np.ones(10),
            oracle_top1=np.zeros(10, dtype=np.int64),
            true_positions=np.zeros(10, dtype=np.int64),
            subject_ids=repeated,
            row_contract={"rows": True, "vocabulary": True},
        )
        self.assertEqual(set(result["subjects"]), set(subjects))
        with self.assertRaises(ValueError):
            summarize_amendment_fold(
                task=task,
                fold=fold,
                h_logp=np.zeros(8),
                oracle_logp=np.ones(8),
                oracle_top1=np.zeros(8, dtype=np.int64),
                true_positions=np.zeros(8, dtype=np.int64),
                subject_ids=repeated[:-2],
                row_contract={"rows": True},
            )
        with self.assertRaises(ValueError):
            summarize_amendment_fold(
                task=task,
                fold=fold,
                h_logp=np.zeros(10),
                oracle_logp=np.ones(10),
                oracle_top1=np.zeros(10, dtype=np.int64),
                true_positions=np.zeros(10, dtype=np.int64),
                subject_ids=repeated,
                row_contract={"rows": False},
            )

    @staticmethod
    def _metric_rows(*, alpha: float, positive: bool) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        subjects = sorted(
            set().union(*(set(value) for value in SUBJECT_FOLDS["task1_nr"].values()))
        )
        sign = 1.0 if positive else -1.0
        for index, subject in enumerate(subjects):
            rows.append(
                {
                    "task": "task1_nr",
                    "fold": "f",
                    "alpha": alpha,
                    "subject_id": subject,
                    "u_oof": sign * (1.0 + index / 100),
                    "u_min": sign * (0.5 + index / 100),
                    "real_minus_trial_shuffle": sign,
                    "real_minus_within_trial_unit_assignment_shuffle": sign,
                    "real_minus_channel_block_permutation": sign,
                    "max_selection_gap": 0.5,
                }
            )
        return rows

    def test_subject_first_detection_boundaries_and_legacy_are_separate(self) -> None:
        rows = self._metric_rows(alpha=10.0, positive=True)
        result = summarize_injection_rows(rows, task="task1_nr", alpha=10.0)
        self.assertEqual(result["subject_count"], 15)
        self.assertTrue(result["family_mean_detected"])
        self.assertTrue(result["legacy_full_detected"])
        for row in rows[:4]:
            row["u_oof"] = -1.0
        result = summarize_injection_rows(rows, task="task1_nr", alpha=10.0)
        self.assertFalse(result["family_mean_detected"])
        legacy_only = self._metric_rows(alpha=10.0, positive=True)
        for row in legacy_only:
            row["u_min"] = -1.0
        result = summarize_injection_rows(
            legacy_only, task="task1_nr", alpha=10.0
        )
        self.assertTrue(result["family_mean_detected"])
        self.assertFalse(result["legacy_full_detected"])

    def test_curve_uses_all_eight_points_and_exact_floors_and_rho(self) -> None:
        alpha_results = []
        for index, alpha in enumerate(ALPHAS):
            alpha_results.append(
                {
                    "alpha": alpha,
                    "family_mean_detected": index >= 5,
                    "legacy_full_detected": index >= 7,
                    "metrics": {"u_oof": {"estimate": float(index)}},
                }
            )
        result = summarize_curve(alpha_results)
        self.assertEqual(result["alpha_family_floor"], 1.0)
        self.assertEqual(result["alpha_legacy_floor"], 10.0)
        self.assertEqual(result["spearman_rho_alpha_vs_u_oof"], 1.0)
        self.assertTrue(result["pass"])
        self.assertEqual(spearman_rho(ALPHAS, list(range(8))), 1.0)
        with self.assertRaises(ValueError):
            summarize_curve(alpha_results[:-1])

    def test_outcome_and_state_transition_require_200_unique_v5_and_both_paths(self) -> None:
        d49 = {task: {"pass": True} for task in TASKS}
        curves = {
            task: {
                "alpha_10_family_mean_detected": True,
                "spearman_rho_alpha_vs_u_oof": 1.0,
            }
            for task in TASKS
        }
        fits = [{"fit_id": f"fit-{index}"} for index in range(200)]
        ledgers = [
            {
                "fit_id": f"fit-{index}",
                "outer_test_record_ids_read": [],
                "calibration_record_ids": [],
            }
            for index in range(200)
        ]
        checks = {
            "all_alpha_zero_byte_identical": True,
            "all_common_row_contracts_pass": True,
        }
        outcome, reasons = evaluate_outcome(
            d49=d49,
            curves=curves,
            fits=fits,
            ledgers=ledgers,
            checks=checks,
            formal_pass=True,
        )
        self.assertEqual((outcome, reasons), ("PASS_A1_MEASUREMENT_VALIDITY_AUDIT", []))
        transition = planned_state_transition(outcome)
        self.assertEqual(transition["route_primary"], "MEASUREMENT-RECOVERY")
        self.assertEqual(transition["route_backup"], "NEGATIVE-DIAGNOSTIC")
        self.assertIsNone(transition["route_locked"])
        self.assertEqual(
            transition["recommended_next_task"],
            "S0_A1_MEASUREMENT_RECOVERY_FREEZE",
        )
        outcome, reasons = evaluate_outcome(
            d49=d49,
            curves=curves,
            fits=fits[:-1],
            ledgers=ledgers[:-1],
            checks=checks,
            formal_pass=True,
        )
        self.assertEqual(outcome, "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT")
        self.assertTrue(reasons)

    def test_formal_outputs_reject_arrays_projection_and_model_payloads(self) -> None:
        self.assertTrue(validate_aggregate_formal_output({"projection_hash": "a"})["pass"])
        for key in ("features", "embeddings", "logits", "weights", "trial_assignment"):
            self.assertFalse(validate_aggregate_formal_output({key: [1]})["pass"])


class A1MeasurementValidityRealArtifactTests(unittest.TestCase):
    def test_immutable_admission_and_diagnosis_evidence_is_byte_identical(self) -> None:
        evidence = verify_immutable_evidence(PROJECT_ROOT)
        self.assertEqual(evidence["hashes"], IMMUTABLE_HASHES)
        self.assertEqual(evidence["admission"]["rows"], 639)
        self.assertEqual(evidence["diagnosis"]["rows"], 58)

    @unittest.skipUnless(REAL_AUDIT.is_file(), "real v3.17 audit has not run yet")
    def test_real_conditional_audit_has_exact_counts_metrics_and_no_reads(self) -> None:
        audit = json.loads(REAL_AUDIT.read_text(encoding="utf-8"))
        self.assertIn(
            audit["completion_outcome"],
            {
                "PASS_A1_MEASUREMENT_VALIDITY_AUDIT",
                "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT",
            },
        )
        self.assertEqual(audit["fit_summary"]["D49_ridge_fit_count"], 8)
        for task in TASKS:
            self.assertEqual(audit["D49_15_subject_amendment"][task]["subject_count"], 15)
        if all(audit["D49_15_subject_amendment"][task]["pass"] for task in TASKS):
            self.assertEqual(audit["fit_summary"]["D50_ridge_fit_count"], 192)
            self.assertEqual(audit["fit_summary"]["total_fit_count"], 200)
            self.assertEqual(audit["fit_summary"]["real_v5_ledger_count"], 200)
            self.assertEqual(len(audit["D50_support"]), 48)
            for task in TASKS:
                self.assertEqual(
                    len(audit["D50_injection_curves"][task]["alpha_results"]), 8
                )
        else:
            self.assertEqual(audit["fit_summary"]["total_fit_count"], 8)
            self.assertIsNone(audit["D50_injection_curves"])
        self.assertEqual(audit["outer_test"]["eeg_feature_label_metric_reads"], 0)
        self.assertEqual(audit["outer_test"]["calibration_record_count"], 0)
        self.assertTrue(validate_aggregate_formal_output(audit)["pass"])

    @unittest.skipUnless(REAL_AUDIT.is_file(), "real v3.17 audit has not run yet")
    def test_real_ledger_is_deterministic_unique_scope_only_and_array_free(self) -> None:
        path = PROJECT_ROOT / "04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz"
        payload = path.read_bytes()
        rows = [json.loads(line) for line in gzip.decompress(payload).splitlines()]
        audit = json.loads(REAL_AUDIT.read_text(encoding="utf-8"))
        expected = audit["fit_summary"]["total_fit_count"]
        self.assertEqual(len(rows), expected)
        self.assertEqual(len({row["fit_id"] for row in rows}), expected)
        self.assertEqual(deterministic_gzip_jsonl(rows), payload)
        self.assertTrue(all(row["outer_test_record_ids_read"] == [] for row in rows))
        self.assertTrue(all(row["calibration_record_ids"] == [] for row in rows))
        serialized = json.dumps(rows, sort_keys=True)
        for forbidden in ("features", "embeddings", "logits", "weights"):
            self.assertNotIn(f'"{forbidden}"', serialized)

    @unittest.skipUnless(REAL_AUDIT.is_file(), "real v3.17 audit has not run yet")
    def test_real_contract_binds_projection_item_hash_old_hashes_and_new_sources(self) -> None:
        contract = yaml.safe_load(
            (
                PROJECT_ROOT / "artifacts/a1_measurement_validity_contract.yaml"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(contract["immutable_evidence_hashes"], IMMUTABLE_HASHES)
        self.assertEqual(contract["projection"]["shape"], [840, 384])
        self.assertEqual(len(contract["projection"]["c_order_sha256"]), 64)
        self.assertEqual(len(contract["item_vector_canonical_mapping_sha256"]), 64)
        for relative, digest in contract["source_hashes"].items():
            self.assertEqual(
                digest,
                __import__("hashlib").sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
