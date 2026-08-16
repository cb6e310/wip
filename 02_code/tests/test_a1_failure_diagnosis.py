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

from data.a1_admission import (  # noqa: E402
    build_v5_ledger,
    deterministic_gzip_jsonl,
)
from data.a1_failure_diagnosis import (  # noqa: E402
    EXPECTED_FIT_COUNTS,
    OLD_ARTIFACT_HASHES,
    OLD_IMPLEMENTATION_HASHES,
    a3_threshold_pass,
    class_support_summary,
    evaluate_completion,
    oracle_input,
    planned_state_transition,
    scorer_threshold_pass,
    summarize_scorer_positive_control,
    validate_aggregate_formal_output,
    validate_diagnosis_v5_or_raise,
    validate_fold_roles,
    verify_old_evidence,
)


class A1FailureDiagnosisContractTests(unittest.TestCase):
    def test_oracle_item_is_restricted_to_registered_positive_control_roles(self) -> None:
        h = np.zeros((3, 384), dtype=np.float32)
        item = np.ones((3, 384), dtype=np.float32)
        np.testing.assert_array_equal(
            oracle_input(h, item, role="a_a3_construct_validity_oracle_item"), item
        )
        np.testing.assert_array_equal(
            oracle_input(h, item, role="a_a1_scorer_h_only"), h
        )
        combined = oracle_input(h, item, role="a_a1_scorer_oracle_item")
        self.assertEqual(combined.shape, (3, 768))
        np.testing.assert_array_equal(combined[:, :384], h)
        np.testing.assert_array_equal(combined[:, 384:], item)
        for forbidden_role in ("eeg", "alignment", "gate", "paper_result", "raw"):
            with self.assertRaisesRegex(ValueError, "forbidden"):
                oracle_input(h, item, role=forbidden_role)

    def test_cluster_fit_is_inner_train_only_and_validation_is_scoring_only(self) -> None:
        result = validate_fold_roles(
            inner_train_record_ids=["train-a", "train-b"],
            inner_validation_record_ids=["validation"],
            cluster_fit_record_ids=["train-a"],
            scoring_record_ids=["validation"],
        )
        self.assertTrue(all(result.values()))
        for mutation in ("cluster_validation", "score_train", "partition_overlap"):
            kwargs = {
                "inner_train_record_ids": ["train-a", "train-b"],
                "inner_validation_record_ids": ["validation"],
                "cluster_fit_record_ids": ["train-a"],
                "scoring_record_ids": ["validation"],
            }
            if mutation == "cluster_validation":
                kwargs["cluster_fit_record_ids"] = ["validation"]
            elif mutation == "score_train":
                kwargs["scoring_record_ids"] = ["train-a"]
            else:
                kwargs["inner_validation_record_ids"] = ["train-a"]
            with self.assertRaises(ValueError):
                validate_fold_roles(**kwargs)

    def test_class_support_reports_all_eight_classes_and_empty_classes(self) -> None:
        summary = class_support_summary(
            [0, 0, 1, 2, 3, 4, 5, 6, 7], [0, 2, 2, 7]
        )
        self.assertEqual(summary["train_class_counts"], [2, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(summary["train_empty_classes"], [])
        self.assertEqual(summary["scoring_empty_classes"], [1, 3, 4, 5, 6])
        self.assertEqual(summary["train_min_class_support"], 1)
        self.assertEqual(summary["scoring_min_class_support"], 0)

    def test_ci_null_and_r_at_1_boundaries_are_exact(self) -> None:
        self.assertFalse(a3_threshold_pass(ci_low=1.0 / 8.0, observed=0.9, null_q95=0.2))
        self.assertFalse(a3_threshold_pass(ci_low=0.2, observed=0.3, null_q95=0.3))
        self.assertTrue(a3_threshold_pass(ci_low=0.1250001, observed=0.3001, null_q95=0.3))
        self.assertFalse(scorer_threshold_pass(ci_low=0.0, macro_subject_r1=1.0))
        self.assertFalse(scorer_threshold_pass(ci_low=0.1, macro_subject_r1=0.799999))
        self.assertTrue(scorer_threshold_pass(ci_low=0.1, macro_subject_r1=0.80))

        subjects = [f"S{index:02d}" for index in range(15)]
        truth = np.zeros(15, dtype=np.int64)
        top1 = np.asarray([0] * 12 + [1] * 3, dtype=np.int64)
        result = summarize_scorer_positive_control(
            task="task1_nr",
            h_logp=np.zeros(15),
            oracle_logp=np.ones(15),
            oracle_top1=top1,
            true_positions=truth,
            subject_ids=subjects,
            row_vocabulary_contract={"rows": True, "vocabulary": True, "finite": True},
        )
        self.assertAlmostEqual(result["oracle_full_vocabulary_macro_subject_r_at_1"], 0.80)
        self.assertTrue(result["pass"])

    def test_exact_54_plus_4_fit_counts_and_pass_invalid_outcomes(self) -> None:
        self.assertEqual(EXPECTED_FIT_COUNTS, {"logistic": 54, "ridge": 4, "total": 58})
        fits = [
            {"fit_type": "multinomial_logistic"} for _ in range(54)
        ] + [{"fit_type": "ridge"} for _ in range(4)]
        passed = {task: {"pass": True} for task in ("task1_nr", "task2_tsr")}
        outcome, reasons = evaluate_completion(
            a3_results=passed,
            scorer_results=passed,
            fit_summaries=fits,
            ledger_count=58,
            old_evidence_pass=True,
            old_v5_revalidated=639,
            formal_output_pass=True,
            outer_test_read_count=0,
            calibration_read_count=0,
        )
        self.assertEqual((outcome, reasons), ("PASS_A1_FAILURE_DIAGNOSIS", []))
        failed = copy.deepcopy(passed)
        failed["task2_tsr"]["pass"] = False
        outcome, reasons = evaluate_completion(
            a3_results=failed,
            scorer_results=passed,
            fit_summaries=fits[:-1],
            ledger_count=57,
            old_evidence_pass=True,
            old_v5_revalidated=639,
            formal_output_pass=True,
            outer_test_read_count=0,
            calibration_read_count=0,
        )
        self.assertEqual(outcome, "INVALID_A1_FAILURE_DIAGNOSIS")
        self.assertTrue(reasons)

    def test_pass_and_invalid_state_transitions_are_bounded(self) -> None:
        passed = planned_state_transition("PASS_A1_FAILURE_DIAGNOSIS")
        self.assertEqual(passed["diagnosis_status"], "DONE")
        self.assertEqual(passed["route_primary"], "NEGATIVE-DIAGNOSTIC")
        self.assertIsNone(passed["route_locked"])
        self.assertEqual(
            passed["recommended_next_task"], "S0_A1_NEGATIVE_CONFIRMATION_FREEZE"
        )
        self.assertEqual(passed["negative_confirmation_run_status"], "BLOCKED")
        invalid = planned_state_transition("INVALID_A1_FAILURE_DIAGNOSIS")
        self.assertEqual(invalid["diagnosis_status"], "BLOCKED")
        self.assertTrue(invalid["route_unchanged"])
        self.assertIsNone(invalid["recommended_next_task"])

    def test_v5_outer_test_calibration_hash_and_scope_mutations_are_rejected(self) -> None:
        hashes = {name: str(index) * 64 for index, name in enumerate(
            ("source", "a1", "outer", "inner", "semantic", "h", "text"), 1
        )}
        scope = {
            "outer": {
                "task1_nr|outer_s0_t0": {
                    "train_record_ids": ["train-a", "validation"],
                    "test_record_ids": ["outer-test"],
                }
            },
            "inner": {
                "task1_nr|outer_s0_t0|inner_s0_t0": {
                    "outer_cell_id": "task1_nr|outer_s0_t0",
                    "train_record_ids": ["train-a"],
                    "validation_record_ids": ["validation"],
                }
            },
        }
        ledger = build_v5_ledger(
            run_id="run",
            fit_id="fit",
            seed=20260813,
            outer_cell="task1_nr|outer_s0_t0",
            inner_cell="task1_nr|outer_s0_t0|inner_s0_t0",
            fit_record_ids=["train-a"],
            validation_record_ids=["validation"],
            scoring_record_ids=["validation"],
            input_hashes=hashes,
        )
        validate_diagnosis_v5_or_raise(ledger, scope, hashes)
        for mutation in ("outer_test", "calibration", "hash", "scope"):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(ledger)
                if mutation == "outer_test":
                    bad["outer_test_record_ids_read"] = ["outer-test"]
                elif mutation == "calibration":
                    bad["calibration_record_ids"] = ["outer-test"]
                elif mutation == "hash":
                    bad["input_artifact_hashes"]["source"] = "f" * 64
                else:
                    bad["stages"][0]["inner_cell"] = (
                        "task1_nr|outer_s0_t0|inner_s9_t9"
                    )
                with self.assertRaises(ValueError):
                    validate_diagnosis_v5_or_raise(bad, scope, hashes)

    def test_formal_output_rejects_arrays_logits_weights_and_assignments(self) -> None:
        self.assertTrue(validate_aggregate_formal_output({"metric": 1.0})["pass"])
        for key in ("features", "embeddings", "logits", "weights", "trial_assignment"):
            result = validate_aggregate_formal_output({"nested": {key: [1.0]}})
            self.assertFalse(result["pass"])
            self.assertEqual(result["forbidden_keys_present"], [key])


class A1FailureDiagnosisRealArtifactTests(unittest.TestCase):
    def test_old_artifacts_implementation_and_639_ledgers_remain_byte_identical(self) -> None:
        evidence = verify_old_evidence(PROJECT_ROOT)
        self.assertEqual(evidence["artifact_hashes"], OLD_ARTIFACT_HASHES)
        self.assertEqual(evidence["implementation_hashes"], OLD_IMPLEMENTATION_HASHES)
        self.assertEqual(evidence["ledger_rows"], 639)
        self.assertEqual(evidence["unique_fit_ids"], 639)
        self.assertEqual(evidence["outer_test_read_count"], 0)
        self.assertEqual(evidence["calibration_read_count"], 0)

    def test_real_positive_controls_have_58_fits_v5_and_precise_invalid_outcome(self) -> None:
        audit_path = PROJECT_ROOT / "04_results/audits/a1_failure_diagnosis.json"
        audit_bytes = audit_path.read_bytes()
        audit = json.loads(audit_bytes)
        self.assertEqual(audit["completion_outcome"], "INVALID_A1_FAILURE_DIAGNOSIS")
        self.assertEqual(audit["fit_summary"]["logistic_fit_count"], 54)
        self.assertEqual(audit["fit_summary"]["ridge_fit_count"], 4)
        self.assertEqual(audit["fit_summary"]["total_fit_count"], 58)
        self.assertEqual(audit["fit_summary"]["real_v5_ledger_count"], 58)
        self.assertEqual(audit["old_v5_revalidated"], 639)
        self.assertEqual(audit["outer_test"]["eeg_feature_label_metric_reads"], 0)
        self.assertEqual(audit["outer_test"]["calibration_record_count"], 0)
        for task in ("task1_nr", "task2_tsr"):
            self.assertTrue(audit["positive_controls"]["A-A3"][task]["pass"])
            scorer = audit["positive_controls"]["A-A1-scorer"][task]
            self.assertFalse(scorer["pass"])
            self.assertGreater(scorer["paired_oracle_minus_h_logp"]["ci95"][0], 0.0)
            self.assertEqual(scorer["oracle_full_vocabulary_macro_subject_r_at_1"], 1.0)
            self.assertEqual(scorer["paired_oracle_minus_h_logp"]["n_subjects"], 5)
            self.assertFalse(scorer["row_vocabulary_contract"]["subject_count_15"])
            self.assertIn(
                f"{task}:A-A1_SCORER_SUBJECT_COUNT_5_NOT_FROZEN_15",
                audit["outcome_reasons"],
            )
        self.assertTrue(validate_aggregate_formal_output(audit)["pass"])
        self.assertEqual(
            json.dumps(audit, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n",
            audit_bytes,
        )

    def test_real_ledger_is_deterministic_scope_only_and_array_free(self) -> None:
        path = PROJECT_ROOT / "04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz"
        payload = path.read_bytes()
        rows = [json.loads(line) for line in gzip.decompress(payload).splitlines()]
        self.assertEqual(len(rows), 58)
        self.assertEqual(len({row["fit_id"] for row in rows}), 58)
        self.assertEqual(deterministic_gzip_jsonl(rows), payload)
        self.assertTrue(all(row["outer_test_record_ids_read"] == [] for row in rows))
        self.assertTrue(all(row["calibration_record_ids"] == [] for row in rows))
        serialized = json.dumps(rows, sort_keys=True)
        for forbidden in ("features", "embeddings", "logits", "weights"):
            self.assertNotIn(f'"{forbidden}"', serialized)

    def test_real_contract_binds_exact_old_and_new_sources(self) -> None:
        contract = yaml.safe_load(
            (PROJECT_ROOT / "artifacts/a1_failure_diagnosis_contract.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["old_artifact_hashes"], OLD_ARTIFACT_HASHES)
        self.assertEqual(contract["old_implementation_hashes"], OLD_IMPLEMENTATION_HASHES)
        self.assertEqual(contract["expected_fit_counts"], EXPECTED_FIT_COUNTS)
        transition = json.loads(
            (PROJECT_ROOT / "04_results/audits/a1_failure_diagnosis.json").read_text(
                encoding="utf-8"
            )
        )["planned_state_transition"]
        self.assertTrue(transition["route_unchanged"])
        self.assertIsNone(transition["recommended_next_task"])


if __name__ == "__main__":
    unittest.main()
