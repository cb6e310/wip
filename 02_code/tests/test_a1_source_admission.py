from __future__ import annotations

import gzip
import hashlib
import inspect
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backbones.a1_spectral import (  # noqa: E402
    analysis_spectrum_phase_rotation_features,
    bandpower_features,
)
from data.a1_source_admission import (  # noqa: E402
    ValidRecord,
    assert_repeat_bytes,
    assert_unique_identities,
    deterministic_gzip_jsonl,
    forbid_out_of_scope_operations,
    select_smoke_records,
    strict_native_matrix,
    validate_channel_evidence,
    validate_required_fields,
    validate_sampling_evidence,
    validate_unit_evidence,
)


class A1SourceAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.good = np.zeros((500, 105), dtype=np.float64)
        self.labels = tuple(f"E{index}" for index in range(105))

    def test_exact_native_shape_is_accepted(self) -> None:
        array, status = strict_native_matrix(self.good)
        self.assertEqual(status, "VALID")
        self.assertEqual(array.shape, (500, 105))  # type: ignore[union-attr]

    def test_missing_placeholder_rank_and_empty_are_rejected(self) -> None:
        cases = [
            (None, "OBJECT_PLACEHOLDER_OR_DANGLING_REFERENCE"),
            (np.zeros((1, 1)), "OBJECT_PLACEHOLDER_1X1"),
            (np.zeros((105,)), "RANK_NOT_2"),
            (np.zeros((0, 105)), "EMPTY_NUMERIC_LEAF"),
        ]
        for value, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(strict_native_matrix(value)[1], expected)

    def test_104_and_106_channels_are_rejected(self) -> None:
        self.assertEqual(strict_native_matrix(np.zeros((20, 104)))[1], "CHANNEL_AXIS_104_NOT_105")
        self.assertEqual(strict_native_matrix(np.zeros((20, 106)))[1], "CHANNEL_AXIS_106_NOT_105")

    def test_source_transpose_is_rejected(self) -> None:
        self.assertEqual(strict_native_matrix(np.zeros((105, 500)))[1], "SOURCE_TRANSPOSE_FORBIDDEN")

    def test_nan_posinf_neginf_are_rejected(self) -> None:
        for value in (np.nan, np.inf, -np.inf):
            matrix = self.good.copy(); matrix[3, 7] = value
            with self.subTest(value=value):
                self.assertEqual(strict_native_matrix(matrix)[1], "NONFINITE_VALUE")

    def test_non_numeric_leaf_is_rejected(self) -> None:
        self.assertEqual(strict_native_matrix(np.full((2, 105), "x"))[1], "NON_NUMERIC_LEAF")

    def test_missing_or_wrong_field_is_rejected(self) -> None:
        validate_required_fields(("content", "rawData", "word"))
        with self.assertRaises(ValueError):
            validate_required_fields(("content", "rawEEG", "word"))

    def test_mixed_or_unverified_sampling_is_rejected(self) -> None:
        self.assertEqual(validate_sampling_evidence([500.0, 500.0], official_rate_hz=500.0), "PASS")
        self.assertEqual(validate_sampling_evidence([500.0, 250.0], official_rate_hz=500.0),
                         "SOURCE_SAMPLING_UNVERIFIED")
        self.assertEqual(validate_sampling_evidence([500.0], official_rate_hz=None),
                         "SOURCE_SAMPLING_UNVERIFIED")

    def test_channel_labels_must_be_unique_stable_and_linked(self) -> None:
        self.assertEqual(validate_channel_evidence([self.labels, self.labels], summary_exact_links=2,
                                                   expected_links=2), "PASS")
        duplicate = self.labels[:-1] + (self.labels[-2],)
        changed = self.labels[:-1] + ("OTHER",)
        reordered = tuple(reversed(self.labels))
        for sequences, links in [([duplicate], 2), ([self.labels, changed], 2),
                                 ([self.labels, reordered], 2), ([self.labels], 0)]:
            with self.subTest(sequences=len(sequences), links=links):
                self.assertEqual(validate_channel_evidence(sequences, summary_exact_links=links,
                                                           expected_links=2), "SOURCE_ORDER_UNVERIFIED")

    def test_unit_never_uses_magnitude_or_conversion(self) -> None:
        self.assertEqual(validate_unit_evidence(exact_unscaled_links=4, expected_links=4),
                         "release_native_amplitude_unit_unlabelled")
        self.assertEqual(validate_unit_evidence(exact_unscaled_links=4, expected_links=4,
                                                conversion_requested=True), "SOURCE_SCALE_UNVERIFIED")
        self.assertEqual(validate_unit_evidence(exact_unscaled_links=4, expected_links=4,
                                                magnitude_inference=True), "SOURCE_SCALE_UNVERIFIED")

    def test_unstable_native_scale_is_rejected(self) -> None:
        self.assertEqual(validate_unit_evidence(exact_unscaled_links=3, expected_links=4),
                         "SOURCE_SCALE_UNVERIFIED")

    def test_duplicate_and_incomplete_identity_are_rejected(self) -> None:
        identity = ("task1_nr", "YAC", "sentence", "slot1", "sentence:1")
        with self.assertRaises(ValueError):
            assert_unique_identities([identity, identity])
        with self.assertRaises(ValueError):
            assert_unique_identities([("task1_nr", "", "sentence", "slot1")])

    def test_ledger_is_order_independent_and_mtime_zero(self) -> None:
        rows = [{"reason": "B", "task": "t"}, {"reason": "A", "task": "t"}]
        first = deterministic_gzip_jsonl(rows)
        second = deterministic_gzip_jsonl(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual(first[4:8], b"\x00\x00\x00\x00")

    def test_nondeterministic_bytes_are_rejected(self) -> None:
        assert_repeat_bytes(b"same", b"same")
        with self.assertRaises(ValueError):
            assert_repeat_bytes(b"first", b"second")

    def test_smoke_selection_is_order_independent(self) -> None:
        records = [ValidRecord("task1_nr", "YAC", "word", f"slot{i}", f"loc{i}",
                               Path("x"), i, 0, 0, 100) for i in range(6)]
        first = [record.identity for record in select_smoke_records(records)]
        second = [record.identity for record in select_smoke_records(list(reversed(records)))]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)

    def test_normalizer_model_and_metric_calls_are_forbidden(self) -> None:
        forbid_out_of_scope_operations(())
        for name in ("normalizer.fit", "torch_model", "text_encoder", "candidate_score",
                     "outer_test_metric", "probe_training", "sham_training"):
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                forbid_out_of_scope_operations([name])

    def test_analysis_spectrum_phase_invariance(self) -> None:
        epoch = np.random.default_rng(20260813).normal(size=(700, 105)).astype(np.float32)
        original = bandpower_features(epoch)
        rotated = analysis_spectrum_phase_rotation_features(epoch, seed=20260813)
        np.testing.assert_allclose(rotated, original, rtol=1e-5, atol=1e-7)

    def test_source_module_has_no_nan_to_num_or_model_construction(self) -> None:
        import data.a1_source_admission as module
        source = inspect.getsource(module)
        self.assertNotIn("nan_to_num", source)
        self.assertNotIn("A1AlignmentEncoder(", source)
        self.assertNotIn("RobustFeatureNormalizer(", source)


class A1SourceAdmissionRealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = ROOT.parent
        cls.contract_path = cls.project_root / "artifacts/a1_real_source_contract.yaml"
        cls.ledger_path = cls.project_root / "01_data_protocol/a1_source_exclusions.jsonl.gz"
        cls.audit_path = cls.project_root / "04_results/audits/zuco2_a1_source_admission.json"
        cls.contract = yaml.safe_load(cls.contract_path.read_text(encoding="utf-8"))
        cls.audit = json.loads(cls.audit_path.read_text(encoding="utf-8"))

    def test_formal_artifact_hashes_and_outcome(self) -> None:
        expected = {
            self.contract_path: "bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c",
            self.ledger_path: "250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c",
            self.audit_path: "07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f",
        }
        for path, digest in expected.items():
            with self.subTest(path=path.name):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertEqual(self.contract["outcome"], "PASS_REAL_A1_SOURCE")
        self.assertEqual(self.audit["overall_outcome"], "PASS_REAL_A1_SOURCE")
        self.assertTrue(all(self.audit["checks"].values()))

    def test_real_exact_coverage_and_source_bindings(self) -> None:
        self.assertEqual(self.audit["input_bindings"]["summary_file_count"], 36)
        self.assertEqual(self.contract["channel_labels_sha256"],
                         "23b8d1ee22d87560fe1a6384141b2713c450ca34ef9eeff8241e7bd3bd885ef5")
        self.assertEqual(self.contract["sampling_status"], "PASS")
        self.assertEqual(self.contract["amplitude_unit_status"],
                         "release_native_amplitude_unit_unlabelled")
        expected = {
            "task1_nr": (5915, 5838, 122213),
            "task2_tsr": (6588, 6441, 109703),
        }
        for task, (sentence, ge500, word) in expected.items():
            rows = self.audit["coverage"]["by_task_subject"][task]
            self.assertEqual(len(rows), 18)
            self.assertEqual(sum(row.get("sentence_valid", 0) for row in rows.values()), sentence)
            self.assertEqual(sum(row.get("sentence_ge_500", 0) for row in rows.values()), ge500)
            self.assertEqual(sum(row.get("word_valid", 0) for row in rows.values()), word)

    def test_real_ledger_is_canonical_and_array_free(self) -> None:
        payload = self.ledger_path.read_bytes()
        self.assertEqual(payload[4:8], b"\x00\x00\x00\x00")
        lines = gzip.decompress(payload).splitlines()
        self.assertEqual(len(lines), 214496)
        rows = [json.loads(line) for line in lines]
        self.assertEqual(lines, sorted(lines))
        self.assertEqual(sum(self.audit["exclusion_reason_counts"].values()), len(rows))
        for row in rows[:100] + rows[-100:]:
            self.assertEqual(set(row), {"task", "subject", "source_slot", "source_kind",
                                        "reference_locator", "reason"})
        for key in ("no_normalizer_fit", "no_model_or_probe_training", "no_heldout_metric",
                    "no_eeg_array_committed"):
            self.assertTrue(self.audit[key])


if __name__ == "__main__":
    unittest.main()
