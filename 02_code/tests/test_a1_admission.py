from __future__ import annotations

import copy
import gzip
import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import torch


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.a1_admission import (  # noqa: E402
    ARMS,
    BASES,
    DEFAULT_ADMISSION_CONFIG,
    apply_trial_shuffle,
    build_four_arm_features,
    build_v5_ledger,
    canonical_artifact,
    channel_block_permutation,
    cluster_bootstrap,
    config_hash,
    deterministic_gzip_jsonl,
    deterministic_item_clusters,
    evaluate_a_a4,
    evaluate_completion_outcome,
    fit_fixed_logistic,
    fit_fold_normalizer,
    paired_subject_bootstrap,
    permutation_null_fixed_predictions,
    percentile_interval,
    sattolo_cycle,
    supported_item_ids,
    token_local_frozen_initial_latent,
    transform_fold_normalizer,
    trial_shuffle_assignment,
    u_statistics,
    validate_v5_or_raise,
    within_trial_assignment,
)
from protocol.h_definition import audit_h_context, build_h_full  # noqa: E402


def _trials() -> list[dict[str, object]]:
    return [
        {
            "record_id": f"S1|slot-{index}",
            "subject_id": "S1",
            "session_id": "1",
            "source_mode": "word_aligned",
            "group_key": f"group-{index}",
            "unit_count": 3 + (index % 2),
        }
        for index in range(5)
    ]


def _observations() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trial in _trials():
        for position in range(int(trial["unit_count"])):
            rows.append(
                {
                    **trial,
                    "observation_id": f"{trial['record_id']}|word:{position}",
                    "item_id": f"item-{position}",
                    "surface": f"surface-{position}",
                }
            )
    return rows


class A1AdmissionContractTests(unittest.TestCase):
    def test_frozen_config(self) -> None:
        config = DEFAULT_ADMISSION_CONFIG
        self.assertEqual(config.ridge_alpha, 1.0)
        self.assertEqual(config.softmax_temperature, 0.07)
        self.assertEqual(config.bootstrap_resamples, 10_000)
        self.assertEqual(config.permutation_resamples, 1_000)
        self.assertEqual((config.feature_dim, config.latent_dim), (840, 384))
        self.assertEqual(len(config_hash()), 64)

    def test_sattolo_is_deterministic_permutation_with_no_fixed_points(self) -> None:
        first = sattolo_cycle(17, seed_parts=(20260813, "unit", "fold", "trial"))
        second = sattolo_cycle(17, seed_parts=(20260813, "unit", "fold", "trial"))
        np.testing.assert_array_equal(first, second)
        self.assertEqual(sorted(first.tolist()), list(range(17)))
        self.assertFalse(np.any(first == np.arange(17)))
        with self.assertRaises(ValueError):
            sattolo_cycle(1, seed_parts=(1,))

    def test_channel_block_permutation_preserves_band_axis(self) -> None:
        row = np.arange(840, dtype=np.float32).reshape(1, 840)
        first, permutation = channel_block_permutation(
            row, seed=20260813, partition="train", record_id="S1|trial"
        )
        second, second_permutation = channel_block_permutation(
            row, seed=20260813, partition="train", record_id="S1|trial"
        )
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(permutation, second_permutation)
        np.testing.assert_array_equal(first.reshape(105, 8), row.reshape(105, 8)[permutation])
        self.assertFalse(np.any(permutation == np.arange(105)))

    def test_within_trial_unit_assignment_has_no_fixed_points(self) -> None:
        permutation = within_trial_assignment(
            8, seed=20260813, partition="validation", record_id="S1|trial"
        )
        self.assertFalse(np.any(permutation == np.arange(8)))
        self.assertEqual(sorted(permutation.tolist()), list(range(8)))

    def test_trial_shuffle_scope_length_and_determinism(self) -> None:
        first, exclusions = trial_shuffle_assignment(
            _trials(), seed=20260813, partition="inner-train"
        )
        second, second_exclusions = trial_shuffle_assignment(
            list(reversed(_trials())), seed=20260813, partition="inner-train"
        )
        self.assertEqual(first, second)
        self.assertEqual(exclusions, second_exclusions)
        self.assertEqual(set(first), set(first.values()))
        for target, donor in first.items():
            self.assertNotEqual(target, donor)

    def test_trial_shuffle_rejects_cross_partition_subject_session_and_outer_test(self) -> None:
        rows = _trials()[:1]
        rows.extend(
            [
                {**_trials()[1], "record_id": "S2|cross-subject", "subject_id": "S2"},
                {**_trials()[2], "record_id": "S1|cross-session", "session_id": "2"},
                {**_trials()[3], "record_id": "S1|outer-test", "partition": "outer-test"},
            ]
        )
        assignment, exclusions = trial_shuffle_assignment(
            rows[:3], seed=20260813, partition="inner-train"
        )
        self.assertEqual(assignment, {})
        self.assertTrue(exclusions)
        self.assertNotIn("S1|outer-test", assignment)
        with self.assertRaisesRegex(ValueError, "crossed the requested partition"):
            trial_shuffle_assignment(
                [
                    {**row, "partition": "inner-train"}
                    for row in _trials()
                ]
                + [
                    {
                        **_trials()[0],
                        "record_id": "S1|outer-test",
                        "group_key": "outer-group",
                        "partition": "outer-test",
                    }
                ],
                seed=20260813,
                partition="inner-train",
            )

    def test_four_arms_have_identical_rows_capacity_and_are_deterministic(self) -> None:
        rows = _observations()
        rng = np.random.default_rng(7)
        features = rng.normal(size=(len(rows), 840)).astype(np.float32)
        first, common, audit = build_four_arm_features(
            features, rows, seed=20260813, partition="inner-train"
        )
        second, second_common, second_audit = build_four_arm_features(
            features, rows, seed=20260813, partition="inner-train"
        )
        self.assertEqual(set(first), set(ARMS))
        self.assertEqual({value.shape for value in first.values()}, {(len(common), 840)})
        np.testing.assert_array_equal(common, second_common)
        for arm in ARMS:
            np.testing.assert_array_equal(first[arm], second[arm])
        self.assertTrue(audit["trial_no_fixed_points"])
        self.assertTrue(audit["unit_no_fixed_points"])
        self.assertTrue(audit["channel_no_fixed_points"])
        self.assertEqual(audit, second_audit)

    def test_fold_local_normalizer_is_finite_and_validation_independent(self) -> None:
        rng = np.random.default_rng(11)
        train = rng.normal(size=(40, 840)).astype(np.float32)
        validation = rng.normal(loc=100, size=(5, 840)).astype(np.float32)
        state, summary = fit_fold_normalizer(train)
        changed_validation = validation.copy()
        changed_validation[0] += 10_000
        np.testing.assert_array_equal(
            transform_fold_normalizer(train, state),
            transform_fold_normalizer(train, state),
        )
        self.assertTrue(np.isfinite(transform_fold_normalizer(validation, state)).all())
        self.assertEqual(summary["fit_rows"], 40)
        state_again, _ = fit_fold_normalizer(train)
        for key in state:
            np.testing.assert_array_equal(state[key], state_again[key])
        # Validation cannot move the fit statistics; both extreme variants are
        # independently clipped by the train-only bounds.
        self.assertTrue(np.array_equal(
            transform_fold_normalizer(validation, state),
            transform_fold_normalizer(changed_validation, state),
        ))

    def test_support_is_inner_train_only(self) -> None:
        rows = []
        for item in ("a", "b"):
            for index in range(20 if item == "a" else 19):
                rows.append(
                    {
                        "item_id": item,
                        "surface": item,
                        "subject_id": f"S{index % 5}",
                    }
                )
        supported, ledger = supported_item_ids(rows)
        self.assertEqual(supported, {"a"})
        self.assertEqual([row["supported"] for row in ledger], [True, False])

    def test_kmeans_is_fold_local_and_deterministic(self) -> None:
        rng = np.random.default_rng(13)
        values = rng.normal(size=(16, 384)).astype(np.float32)
        values /= np.linalg.norm(values, axis=1, keepdims=True)
        first, model = deterministic_item_clusters(values)
        second, _ = deterministic_item_clusters(values)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(model.n_clusters, 8)
        with self.assertRaises(ValueError):
            deterministic_item_clusters(values[:7])

    def test_token_local_latent_is_frozen_finite_384d_and_deterministic(self) -> None:
        values = np.random.default_rng(17).normal(size=(5, 840)).astype(np.float32)
        first, first_audit = token_local_frozen_initial_latent(
            values, seed=20260813, device="cpu", batch_size=2
        )
        second, second_audit = token_local_frozen_initial_latent(
            values, seed=20260813, device="cpu", batch_size=2
        )
        self.assertEqual(first.shape, (5, 384))
        self.assertEqual(first.dtype, np.float32)
        self.assertTrue(np.isfinite(first).all())
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first_audit["trainable_parameter_count"], 0)
        self.assertTrue(first_audit["model_eval"])
        self.assertEqual(first_audit["sequence_length"], 1)
        self.assertTrue(first_audit["mask_all_true"])
        self.assertEqual(first_audit["parameter_count"], second_audit["parameter_count"])

    def test_fixed_logistic_probe_is_deterministic(self) -> None:
        x = np.asarray(
            [[-2.0, 0.0], [-1.0, 0.1], [1.0, -0.1], [2.0, 0.0]], dtype=np.float32
        )
        y = np.asarray(["left", "left", "right", "right"])
        torch.manual_seed(20260813)
        first, _ = fit_fixed_logistic(x, y, device="cpu")
        torch.manual_seed(20260813)
        second, _ = fit_fixed_logistic(x, y, device="cpu")
        np.testing.assert_array_equal(first.predict(x), y)
        np.testing.assert_array_equal(first.predict(x), second.predict(x))

    def test_h_forbidden_fields_are_rejected_by_audit(self) -> None:
        context = build_h_full(
            [["earlier", "sentence"], ["target", "word"]],
            target_sentence_index=1,
            target_tokens=["target", "word"],
            position_index=1,
        )
        clean = audit_h_context(context, target_tokens=["target", "word"], payload={"history": list(context.tokens)})
        self.assertTrue(all(clean.values()))
        forbidden = audit_h_context(
            context,
            target_tokens=["target", "word"],
            future_sentence_indices=[1],
            payload={
                "target_tokens": ["target"],
                "future_sentence": ["future"],
                "word_count": 2,
                "candidates": ["x"],
                "eye_tracking": 1.0,
            },
        )
        for key in (
            "target_payload_absent",
            "future_sentences_absent",
            "target_statistics_absent",
            "candidate_inputs_absent",
            "eye_tracking_inputs_absent",
        ):
            self.assertFalse(forbidden[key])

    def test_u_oof_and_u_min_formula(self) -> None:
        real = np.asarray([2.0, 1.0])
        shams = {
            "trial_shuffle": np.asarray([0.0, 2.0]),
            "within_trial_unit_assignment_shuffle": np.asarray([1.0, 0.0]),
            "channel_block_permutation": np.asarray([-1.0, 1.0]),
        }
        result = u_statistics(real, shams)
        np.testing.assert_allclose(result["u_oof"], [2.0, 0.0])
        np.testing.assert_allclose(result["u_min"], [1.0, -1.0])

    def test_subject_bootstraps_are_deterministic_and_paired(self) -> None:
        raw = {f"S{i}": float(i) for i in range(15)}
        latent = {f"S{i}": float(i + 1) for i in range(15)}
        first = paired_subject_bootstrap(raw, latent, n_resamples=100, seed=20260813)
        second = paired_subject_bootstrap(raw, latent, n_resamples=100, seed=20260813)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["estimate"], 1.0)
        self.assertEqual(percentile_interval(np.ones(20)), [1.0, 1.0])
        clustered = cluster_bootstrap(raw, n_resamples=100, seed=20260813)
        self.assertEqual(clustered["n_subjects"], 15)

    def test_blockwise_permutation_null_is_deterministic(self) -> None:
        truth = [0, 1, 0, 1, 0, 1, 0, 1]
        prediction = [0, 0, 1, 1, 0, 1, 1, 0]
        blocks = ["a"] * 4 + ["b"] * 4
        first = permutation_null_fixed_predictions(
            truth, prediction, blocks, n_resamples=100, seed=20260813
        )
        second = permutation_null_fixed_predictions(
            truth, prediction, blocks, n_resamples=100, seed=20260813
        )
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["q95"], 0.0)
        self.assertLessEqual(first["q95"], 1.0)

    def test_a_a4_and_all_four_outcomes(self) -> None:
        subjects = {f"S{i}": 0.2 for i in range(15)}
        metric = {
            "pass": True,
            "metrics": {"u_min": {"subject_values": subjects}},
        }
        classification = {"pass": True, "per_subject_recall": subjects}
        a4 = evaluate_a_a4(metric, metric, classification, classification, classification, classification, task="task1_nr")
        self.assertTrue(a4["pass"])

        def a1(passed: bool, estimate: float = 0.2, ci=(-0.1, 0.4)) -> dict[str, object]:
            return {
                "pass": passed,
                "metrics": {
                    "u_oof": {"estimate": estimate, "ci95": list(ci)},
                    "u_min": {"estimate": estimate, "ci95": list(ci), "subject_values": subjects},
                },
            }

        def result(task_passes=(True, True), diagnostics=True):
            value = {}
            for index, task in enumerate(("task1_nr", "task2_tsr")):
                value[task] = {
                    "A-A1": {basis: a1(task_passes[index]) for basis in BASES},
                    "A-A2": {basis: {"pass": diagnostics} for basis in BASES},
                    "A-A3": {basis: {"pass": diagnostics} for basis in BASES},
                    "A-A4": {"pass": diagnostics, "invalid_basis_order": False, "co_n1_latent_loss": False},
                }
            return value

        self.assertEqual(evaluate_completion_outcome(result())[0], "PASS_A1_ADMISSION_BOTH_TASKS")
        self.assertEqual(evaluate_completion_outcome(result((True, False)))[0], "PASS_LIMITED_A1_ADMISSION_ONE_TASK")
        self.assertEqual(evaluate_completion_outcome(result((False, False)))[0], "FAIL_A1_ADMISSION")
        outcome, reasons = evaluate_completion_outcome(result((False, False), diagnostics=False))
        self.assertEqual(outcome, "FAIL_A1_ADMISSION")
        self.assertIn("task1_nr:raw:A-A1_FAIL", reasons)
        self.assertIn("task1_nr:raw:A-A3_FAIL", reasons)
        self.assertNotIn("A-A2_A-A3_OR_A-A4_DIAGNOSTIC_FAILURE", reasons)
        invalid = result()
        invalid["task1_nr"]["A-A4"]["invalid_basis_order"] = True
        self.assertEqual(evaluate_completion_outcome(invalid)[0], "INVALID_A1_ADMISSION")

    def test_v5_real_fit_ledger_and_adversarial_mutations(self) -> None:
        hashes = {name: str(index) * 64 for index, name in enumerate(("source", "a1", "outer", "inner", "semantic", "h", "text"), 1)}
        scope = {
            "outer": {
                "task1_nr|outer_s0_t0": {
                    "train_record_ids": ["train-a", "train-b"],
                    "test_record_ids": ["outer-test"],
                }
            },
            "inner": {
                "task1_nr|outer_s0_t0|inner_s0_t0": {
                    "outer_cell_id": "task1_nr|outer_s0_t0",
                    "train_record_ids": ["train-a"],
                    "validation_record_ids": ["train-b"],
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
            validation_record_ids=["train-b"],
            scoring_record_ids=["train-b"],
            input_hashes=hashes,
        )
        validate_v5_or_raise(ledger, scope, hashes)
        for mutation in ("outer_test_fit", "validation_fit", "calibration", "hash"):
            bad = copy.deepcopy(ledger)
            if mutation == "outer_test_fit":
                bad["stages"][0]["fit_record_ids"] = ["outer-test"]
            elif mutation == "validation_fit":
                bad["stages"][0]["fit_record_ids"] = ["train-b"]
            elif mutation == "calibration":
                bad["stages"][0]["calibration_record_ids"] = ["outer-test"]
            else:
                bad["input_artifact_hashes"]["source"] = "f" * 64
            with self.assertRaises(ValueError):
                validate_v5_or_raise(bad, scope, hashes)

    def test_canonical_bytes_and_deterministic_gzip(self) -> None:
        value = {"z": 1, "a": [2, 3]}
        self.assertEqual(canonical_artifact(value), canonical_artifact(dict(reversed(list(value.items())))))
        first = deterministic_gzip_jsonl([{"b": 2}, {"a": 1}])
        second = deterministic_gzip_jsonl([{"a": 1}, {"b": 2}])
        self.assertEqual(first, second)
        decoded = [json.loads(line) for line in gzip.decompress(first).splitlines()]
        self.assertEqual(decoded, [{"a": 1}, {"b": 2}])


class A1AdmissionRealArtifactTests(unittest.TestCase):
    EXPECTED_HASHES = {
        "artifacts/a1_admission_contract.yaml": "c9c5a94b8227b6e43ecfc6d61b9b10b33f9340f7c845ca7dbaa0e0a3e65d9f4b",
        "04_results/audits/a1_admission.json": "b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e",
        "04_results/audits/a1_admission.md": "e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e",
        "04_results/audits/a1_admission_run_ledger.jsonl.gz": "fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd",
    }

    def test_formal_artifact_hashes_counts_and_outcome(self) -> None:
        for relative, expected in self.EXPECTED_HASHES.items():
            payload = (PROJECT_ROOT / relative).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected, relative)
        audit_path = PROJECT_ROOT / "04_results/audits/a1_admission.json"
        audit_bytes = audit_path.read_bytes()
        audit = json.loads(audit_bytes)
        self.assertEqual(canonical_artifact(audit), audit_bytes)
        self.assertEqual(audit["completion_outcome"], "FAIL_A1_ADMISSION")
        self.assertEqual(audit["fit_summary"]["total_fit_count"], 639)
        self.assertEqual(audit["fit_summary"]["real_v5_ledger_count"], 639)
        self.assertEqual(audit["fit_summary"]["ridge_fit_count"], 495)
        self.assertEqual(audit["fit_summary"]["logistic_fit_count"], 144)
        self.assertEqual(audit["data"]["task1_nr"]["observations"], 48_347)
        self.assertEqual(audit["data"]["task2_tsr"]["observations"], 45_392)
        self.assertEqual(audit["outer_test"]["eeg_feature_label_metric_reads"], 0)

    def test_formal_outputs_are_aggregate_only_and_ledger_is_deterministic(self) -> None:
        audit_bytes = (PROJECT_ROOT / "04_results/audits/a1_admission.json").read_bytes()
        audit = json.loads(audit_bytes)
        forbidden_keys = {
            "trial_assignment",
            "trial_exclusions",
            "unit_exclusions",
            "weights",
            "logits",
        }

        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value)) if value else set()
            return set()

        self.assertTrue(forbidden_keys.isdisjoint(keys(audit)))
        self.assertEqual(audit["preflight"]["train_sham"]["trial_assignment_count"], 1303)
        ledger_bytes = (
            PROJECT_ROOT / "04_results/audits/a1_admission_run_ledger.jsonl.gz"
        ).read_bytes()
        rows = [json.loads(line) for line in gzip.decompress(ledger_bytes).splitlines()]
        self.assertEqual(len(rows), 639)
        self.assertEqual(len({row["fit_id"] for row in rows}), 639)
        self.assertEqual(deterministic_gzip_jsonl(rows), ledger_bytes)
        self.assertTrue(all(row["outer_test_record_ids_read"] == [] for row in rows))
        self.assertTrue(all(row["calibration_record_ids"] == [] for row in rows))


if __name__ == "__main__":
    unittest.main()
