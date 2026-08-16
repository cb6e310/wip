from __future__ import annotations

import copy
import gzip
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import yaml


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.a1_failure_diagnosis import validate_aggregate_formal_output  # noqa: E402
from data.a1_measurement_recovery import (  # noqa: E402
    ARMS,
    CANDIDATES,
    EXPECTED_FRONTEND_FITS,
    EXPECTED_H_ONLY_FITS,
    EXPECTED_TOTAL_FITS,
    FOLDS,
    FRONTENDS,
    RUN032_IMMUTABLE_HASHES,
    TASKS,
    apply_log_bandpower,
    bottleneck_label,
    build_recovery_v5_ledger,
    derive_recovery_partitions,
    evaluate_recovery,
    fit_log_bandpower,
    paired_summary,
    summarize_regime_rows,
    temporal_fixation_feature,
    validate_recovery_v5_or_raise,
    verify_run032_immutable,
)


REAL_AUDIT = PROJECT_ROOT / "04_results/audits/a1_measurement_recovery.json"
REAL_LEDGER = PROJECT_ROOT / "04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz"


def _protocol_fixture() -> tuple[dict[str, object], dict[str, object]]:
    records: dict[str, dict[str, str]] = {}
    assignments = {"stim-t0": "0", "stim-t1": "1"}
    for subject_index in range(15):
        subject = f"S{subject_index:02d}"
        for text_fold in ("t0", "t1"):
            record_id = f"{subject}|{text_fold}"
            records[record_id] = {
                "subject_id": subject,
                "stimulus_id": f"stim-{text_fold}",
            }
    held = {f"S{index:02d}" for index in range(5)}
    fit = sorted(
        record for record, row in records.items()
        if row["subject_id"] not in held and record.endswith("|t1")
    )
    cross = sorted(
        record for record, row in records.items()
        if row["subject_id"] in held and record.endswith("|t0")
    )
    protocol: dict[str, object] = {
        "outer_cell_id": "task1_nr|outer_s0_t0",
        "outer_train_record_ids": sorted(records),
        "record_rows": records,
        "text_assignment": assignments,
    }
    cell: dict[str, object] = {
        "inner_cell_id": "task1_nr|outer_s0_t0|inner_s0_t0",
        "train_record_ids": fit,
        "validation_record_ids": cross,
    }
    return protocol, cell


def _metric_row(subject: str, fold: str, regime: str, value: float) -> dict[str, object]:
    row: dict[str, object] = {
        "task": "task1_nr",
        "frontend": "A1_BP_CONCAT",
        "regime": regime,
        "subject_id": subject,
        "fold": fold,
    }
    for key in (
        "u_oof",
        "u_min",
        "real_minus_trial_shuffle",
        "real_minus_within_trial_unit_assignment_shuffle",
        "real_minus_channel_block_permutation",
        "max_selection_gap",
    ):
        row[key] = value
    for arm in ("H_only", *ARMS):
        row[f"logp_{arm}"] = value
    return row


def _bootstrap_stub(values: dict[str, float], **_: object) -> dict[str, object]:
    estimate = float(np.mean(list(values.values())))
    return {
        "estimate": estimate,
        "ci95": [estimate, estimate],
        "positive_subject_count": sum(value > 0.0 for value in values.values()),
        "subject_values": dict(sorted(values.items())),
    }


def _result_fixture() -> dict[str, object]:
    results: dict[str, object] = {}
    for task in TASKS:
        task_rows: dict[str, object] = {}
        for frontend in FRONTENDS:
            task_rows[frontend] = {
                "seen": {"family_detected": False},
                "cross": {"family_detected": False},
            }
        results[task] = task_rows
    return results


class A1MeasurementRecoveryContractTests(unittest.TestCase):
    def test_exact_budget_scope_and_frontends_are_frozen(self) -> None:
        self.assertEqual(TASKS, ("task1_nr", "task2_tsr"))
        self.assertEqual(FOLDS, ("inner_s0_t0", "inner_s1_t0", "inner_s2_t0"))
        self.assertEqual(
            FRONTENDS,
            ("A1_BP_CONCAT", "A1R_LOG_BP_CONCAT", "A1R_T8_FIXATION"),
        )
        self.assertEqual(CANDIDATES, FRONTENDS[1:])
        self.assertEqual((EXPECTED_H_ONLY_FITS, EXPECTED_FRONTEND_FITS), (6, 72))
        self.assertEqual(EXPECTED_TOTAL_FITS, 78)

    def test_t8_is_exact_channel_major_signed_feature(self) -> None:
        matrix = np.arange(16 * 105, dtype=np.float64).reshape(16, 105)
        observed, exclusions = temporal_fixation_feature([matrix])
        self.assertIsNotNone(observed)
        assert observed is not None
        centered = matrix - matrix.mean(axis=0, keepdims=True)
        expected = np.stack(
            [centered[index].mean(axis=0) for index in np.array_split(np.arange(16), 8)],
            axis=1,
        ).reshape(-1).astype(np.float32)
        self.assertEqual(observed.shape, (840,))
        self.assertEqual(observed.dtype, np.float32)
        self.assertEqual(observed.tobytes(), expected.tobytes())
        self.assertLess(float(observed.min()), 0.0)
        self.assertGreater(float(observed.max()), 0.0)
        self.assertEqual(exclusions, {"TEMPORAL_T_LT_8": 0, "TEMPORAL_INVALID": 0})

    def test_t8_excludes_short_or_invalid_without_padding(self) -> None:
        short = np.ones((7, 105), dtype=np.float32)
        invalid = np.ones((8, 104), dtype=np.float32)
        observed, exclusions = temporal_fixation_feature([short, invalid])
        self.assertIsNone(observed)
        self.assertEqual(exclusions["TEMPORAL_T_LT_8"], 1)
        self.assertEqual(exclusions["TEMPORAL_INVALID"], 1)

    def test_t8_fixations_are_equal_weighted(self) -> None:
        first = np.arange(8 * 105, dtype=np.float64).reshape(8, 105)
        second = np.flip(first, axis=0).copy()
        first_feature, _ = temporal_fixation_feature([first])
        second_feature, _ = temporal_fixation_feature([second])
        combined, _ = temporal_fixation_feature([first, second])
        assert first_feature is not None and second_feature is not None and combined is not None
        expected = np.mean(
            np.stack([first_feature, second_feature]).astype(np.float64), axis=0
        ).astype(np.float32)
        self.assertEqual(combined.tobytes(), expected.tobytes())

    def test_log_bandpower_uses_positive_fit_medians_only(self) -> None:
        fit = np.tile(np.asarray([[0.0], [2.0], [6.0]], dtype=np.float32), (1, 840))
        epsilon, summary = fit_log_bandpower(fit)
        np.testing.assert_array_equal(epsilon, np.full(840, 4e-6, dtype=np.float64))
        self.assertEqual(summary["positive_dimension_count"], 840)
        seen = np.full((2, 840), 10.0, dtype=np.float32)
        transformed = apply_log_bandpower(seen, epsilon)
        self.assertEqual(transformed.shape, (2, 840))
        self.assertEqual(transformed.dtype, np.float32)
        self.assertTrue(np.isfinite(transformed).all())
        with self.assertRaisesRegex(ValueError, "no positive fit value"):
            fit_log_bandpower(np.zeros((2, 840), dtype=np.float32))

    def test_log_bandpower_has_frozen_global_scaling_behavior(self) -> None:
        fit = np.tile(np.asarray([[1.0], [3.0], [9.0]], dtype=np.float64), (1, 840))
        seen = np.tile(np.asarray([[2.0], [5.0]], dtype=np.float64), (1, 840))
        eps, _ = fit_log_bandpower(fit)
        scaled_eps, _ = fit_log_bandpower(fit * 7.0)
        original = apply_log_bandpower(seen, eps)
        scaled = apply_log_bandpower(seen * 7.0, scaled_eps)
        np.testing.assert_allclose(scaled - original, np.log(7.0), rtol=0, atol=2e-7)

    def test_partition_arithmetic_is_disjoint_ten_plus_five(self) -> None:
        protocol, cell = _protocol_fixture()
        result = derive_recovery_partitions(protocol, cell)
        self.assertEqual(len(result["fit_subject_ids"]), 10)
        self.assertEqual(len(result["seen_subject_ids"]), 10)
        self.assertEqual(len(result["cross_subject_ids"]), 5)
        fit = set(result["fit_record_ids"])
        seen = set(result["seen_record_ids"])
        cross = set(result["cross_record_ids"])
        self.assertFalse(fit & seen or fit & cross or seen & cross)
        self.assertEqual(len(fit), 10)
        self.assertEqual(len(seen), 10)
        self.assertEqual(len(cross), 5)

    def test_recovery_v5_binds_seen_and_cross_to_one_fit(self) -> None:
        protocol, cell = _protocol_fixture()
        partitions = derive_recovery_partitions(protocol, cell)
        outer = protocol["outer_cell_id"]
        recovery_cell = "task1_nr|outer_s0_t0|recovery_s0_t0"
        scope = {
            "outer": {
                outer: {
                    "train_record_ids": protocol["outer_train_record_ids"],
                    "test_record_ids": ["outer-test"],
                }
            },
            "inner": {
                recovery_cell: {
                    "outer_cell_id": outer,
                    "train_record_ids": partitions["fit_record_ids"],
                    "validation_record_ids": sorted(
                        set(partitions["seen_record_ids"]) | set(partitions["cross_record_ids"])
                    ),
                }
            },
        }
        hashes = {"protocol": "a" * 64}
        ledger = build_recovery_v5_ledger(
            run_id="run",
            fit_id="fit",
            seed=20260813,
            outer_cell=outer,
            recovery_cell=recovery_cell,
            fit_record_ids=partitions["fit_record_ids"],
            seen_record_ids=partitions["seen_record_ids"],
            cross_record_ids=partitions["cross_record_ids"],
            input_hashes=hashes,
        )
        validate_recovery_v5_or_raise(ledger, scope, hashes)
        mutations = []
        overlap = copy.deepcopy(ledger)
        overlap["recovery_scoring"]["cross_score_record_ids"].append(
            overlap["recovery_scoring"]["seen_score_record_ids"][0]
        )
        mutations.append(overlap)
        flag = copy.deepcopy(ledger)
        flag["recovery_scoring"]["same_fit_scores_both_regimes"] = False
        mutations.append(flag)
        scoring = copy.deepcopy(ledger)
        scoring["scoring_record_ids"] = scoring["scoring_record_ids"][:-1]
        mutations.append(scoring)
        outer_read = copy.deepcopy(ledger)
        outer_read["outer_test_record_ids_read"] = ["outer-test"]
        mutations.append(outer_read)
        calibration = copy.deepcopy(ledger)
        calibration["calibration_record_ids"] = ["forbidden"]
        mutations.append(calibration)
        for mutation in mutations:
            with self.assertRaises(ValueError):
                validate_recovery_v5_or_raise(mutation, scope, hashes)

    def test_seen_fold_means_are_equal_weighted_before_pairing(self) -> None:
        rows: list[dict[str, object]] = []
        for index in range(15):
            subject = f"S{index:02d}"
            rows.append(_metric_row(subject, "fold-a", "seen", 1.0))
            rows.extend(_metric_row(subject, "fold-b", "seen", 3.0) for _ in range(9))
        with patch(
            "data.a1_measurement_recovery.cluster_bootstrap",
            side_effect=_bootstrap_stub,
        ):
            summary = summarize_regime_rows(
                rows, task="task1_nr", frontend="A1_BP_CONCAT", regime="seen"
            )
        self.assertTrue(summary["seen_fold_means_equal_weighted_before_subject_pairing"])
        self.assertEqual(summary["metrics"]["u_oof"]["estimate"], 2.0)
        self.assertTrue(
            all(value == 2.0 for value in summary["metrics"]["u_oof"]["subject_values"].values())
        )

    def test_family_threshold_boundaries_are_exact(self) -> None:
        rows = [
            _metric_row(f"S{index:02d}", "fold", "cross", 1.0 if index < 12 else -0.1)
            for index in range(15)
        ]
        with patch(
            "data.a1_measurement_recovery.cluster_bootstrap",
            side_effect=_bootstrap_stub,
        ):
            summary = summarize_regime_rows(
                rows, task="task1_nr", frontend="A1_BP_CONCAT", regime="cross"
            )
        self.assertTrue(summary["family_detected"])
        rows[11]["u_oof"] = -0.1
        with patch(
            "data.a1_measurement_recovery.cluster_bootstrap",
            side_effect=_bootstrap_stub,
        ):
            failed = summarize_regime_rows(
                rows, task="task1_nr", frontend="A1_BP_CONCAT", regime="cross"
            )
        self.assertFalse(failed["family_detected"])

    def test_paired_transfer_and_delta_use_same_fifteen_subjects(self) -> None:
        left = {"metrics": {"u_oof": {"subject_values": {f"S{i:02d}": 2.0 for i in range(15)}}}}
        right = {"metrics": {"u_oof": {"subject_values": {f"S{i:02d}": 0.5 for i in range(15)}}}}
        result = paired_summary(left, right, seed_parts=(20260813, "test"))
        self.assertAlmostEqual(result["estimate"], 1.5)
        self.assertEqual(result["positive_subject_count"], 15)
        self.assertEqual(result["ci95"], [1.5, 1.5])

    def test_bottleneck_labels_are_exhaustive(self) -> None:
        self.assertEqual(bottleneck_label(True, False), "TRANSFER_DOMINANT")
        self.assertEqual(bottleneck_label(False, False), "REPRESENTATION_OR_PROBE_DOMINANT")
        self.assertEqual(bottleneck_label(True, True), "BASELINE_REPRODUCTION_DEVIATION")
        self.assertEqual(bottleneck_label(False, True), "UNEXPECTED_REGIME_ORDERING")

    def test_d59_selection_tie_break_and_legal_outcomes(self) -> None:
        results = _result_fixture()
        for task in TASKS:
            for candidate in CANDIDATES:
                results[task][candidate]["cross"]["family_detected"] = True
                results[task][candidate]["recovery_delta"] = {
                    "estimate": 0.5,
                    "ci95": [0.1, 0.8],
                    "positive_subject_count": 10,
                }
        outcome, selected, scope, reasons = evaluate_recovery(results, contract_pass=True)
        self.assertEqual(outcome, "PASS_A1R_RECOVERY_BOTH_TASKS")
        self.assertEqual(selected, "A1R_LOG_BP_CONCAT")
        self.assertEqual(scope, list(TASKS))
        self.assertEqual(reasons, [])

        failed = _result_fixture()
        for task in TASKS:
            for candidate in CANDIDATES:
                failed[task][candidate]["recovery_delta"] = {
                    "estimate": 0.5,
                    "ci95": [0.0, 0.8],
                    "positive_subject_count": 15,
                }
        self.assertEqual(evaluate_recovery(failed, contract_pass=True)[0], "FAIL_A1R_RECOVERY")
        self.assertEqual(evaluate_recovery(failed, contract_pass=False)[0], "INVALID_A1R_RECOVERY")

    def test_run032_implementation_and_evidence_are_immutable(self) -> None:
        self.assertEqual(verify_run032_immutable(PROJECT_ROOT), RUN032_IMMUTABLE_HASHES)

    @unittest.skipUnless(REAL_AUDIT.is_file() and REAL_LEDGER.is_file(), "real v3.18 audit not built")
    def test_real_outputs_have_exact_fit_v5_and_formal_contract(self) -> None:
        audit = json.loads(REAL_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(audit["fit_summary"]["total_fit_count"], 78)
        self.assertEqual(audit["fit_summary"]["real_v5_ledger_count"], 78)
        self.assertEqual(audit["fit_summary"]["unique_v5_fit_ids"], 78)
        self.assertEqual(audit["outer_test"], {"eeg_label_metric_reads": 0, "calibration_reads": 0})
        self.assertTrue(validate_aggregate_formal_output(audit)["pass"])
        with gzip.open(REAL_LEDGER, "rt", encoding="utf-8") as handle:
            ledgers = [json.loads(line) for line in handle]
        self.assertEqual(len(ledgers), 78)
        self.assertEqual(len({row["fit_id"] for row in ledgers}), 78)
        self.assertTrue(all(row["outer_test_record_ids_read"] == [] for row in ledgers))
        contract = yaml.safe_load(
            (PROJECT_ROOT / "artifacts/a1_measurement_recovery_contract.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["scope"]["total_fits"], 78)
        self.assertEqual(contract["run032_immutable_hashes"], RUN032_IMMUTABLE_HASHES)


if __name__ == "__main__":
    unittest.main()
