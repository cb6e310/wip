"""Synthetic SPEC v3.10 candidate-contract tests; no dataset or EEG reads."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.candidates import (  # noqa: E402
    DEFAULT_REPEATS,
    FROZEN_PROVENANCE,
    FROZEN_SOURCE_JOIN_MAPPING,
    NEGATIVE_COUNTS,
    N_VALUES,
    build_candidate_artifacts,
    cosine_is_legal,
    hash_rank_key,
    length_is_legal,
    validate_candidate_artifacts,
)
from data.joint_split import canonical_json_bytes  # noqa: E402


def provenance() -> dict[str, object]:
    value: dict[str, object] = {
        **FROZEN_PROVENANCE,
        "released_text_manifest_sha256": "5" * 64,
        "h_identity_manifest_sha256": "7" * 64,
        "source_join_mapping_sha256": dict(FROZEN_SOURCE_JOIN_MAPPING),
        "encoder_model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "encoder_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "read_fields": ["sentenceData/content", "task_materials"],
        "roamm_paths_read": [],
    }
    return value


def stimulus(index: int, *, dim: int = 205) -> dict[str, object]:
    vector = np.zeros(dim, dtype=np.float32)
    vector[index] = 1.0
    identity = f"zuco_2_0|task1_nr|nr.csv|{index + 1}|doc|{index + 1}"
    return {
        "task": "task1_nr",
        "stimulus_id": identity,
        "exact_text_sha256": f"{index + 1000:064x}"[-64:],
        "token_length": 10,
        "h_source_ids": [],
        "embedding": vector,
    }


def scopes(ids: list[str]) -> list[dict[str, object]]:
    return [
        {
            "task": "task1_nr",
            "scope_type": "outer_test",
            "scope_id": "task1_nr|outer_t0",
            "outer_text_fold": "0",
            "reuse_outer_subject_folds": [str(value) for value in range(6)],
            "pool_ids": ids,
        },
        {
            "task": "task1_nr",
            "scope_type": "inner_validation",
            "scope_id": "task1_nr|outer_s0_t1|inner_t0",
            "outer_cell_id": "task1_nr|outer_s0_t1",
            "outer_subject_fold": "0",
            "outer_text_fold": "1",
            "inner_text_fold": "0",
            "reuse_inner_subject_folds": [str(value) for value in range(3)],
            "pool_ids": ids,
        },
    ]


class CandidateBoundaryTests(unittest.TestCase):
    def test_inclusive_integer_length_boundaries_and_outside(self) -> None:
        self.assertTrue(length_is_legal(4, 3))
        self.assertTrue(length_is_legal(4, 5))
        self.assertFalse(length_is_legal(4, 2))
        self.assertFalse(length_is_legal(4, 6))

    def test_cosine_strict_boundary(self) -> None:
        self.assertTrue(cosine_is_legal(0.9))
        self.assertTrue(cosine_is_legal(0.899999))
        self.assertFalse(cosine_is_legal(0.900001))

    def test_hash_rank_is_stable_and_repeat_sensitive(self) -> None:
        kwargs = dict(
            seed=20260813,
            task="task1_nr",
            scope_id="scope",
            target_id="target",
            negative_id="negative",
        )
        self.assertEqual(hash_rank_key(repeat=0, **kwargs), hash_rank_key(repeat=0, **kwargs))
        self.assertNotEqual(hash_rank_key(repeat=0, **kwargs), hash_rank_key(repeat=1, **kwargs))


class CandidateArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stimuli = [stimulus(index) for index in range(205)]
        cls.ids = [str(row["stimulus_id"]) for row in cls.stimuli]
        cls.scope_rows = scopes(cls.ids)
        cls.artifacts = build_candidate_artifacts(
            cls.stimuli, cls.scope_rows, provenance=provenance()
        )

    def test_every_n_prefix_is_available_nested_and_without_replacement(self) -> None:
        candidates = self.artifacts[0]
        target = candidates["scopes"][0]["targets"][0]
        self.assertEqual(len(target["repeats"]), DEFAULT_REPEATS)
        for repeat in target["repeats"]:
            ordering = repeat["maximal_legal_negative_indices"]
            self.assertEqual(len(ordering), len(set(ordering)))
            self.assertNotIn(target["target_index"], ordering)
            for n in N_VALUES:
                row = repeat["n_lists"][str(n)]
                self.assertTrue(row["available"])
                self.assertEqual(row["negative_prefix_length"], NEGATIVE_COUNTS[n])
            self.assertEqual(ordering[:9], ordering[:49][:9])
            self.assertEqual(ordering[:49], ordering[:99][:49])
            self.assertEqual(ordering[:99], ordering[:199][:99])

    def test_all_targets_retained_in_both_confined_scopes(self) -> None:
        candidates = self.artifacts[0]
        self.assertEqual(len(candidates["scopes"]), 2)
        for scope in candidates["scopes"]:
            pool = set(scope["pool_stimulus_indices"])
            targets = {row["target_index"] for row in scope["targets"]}
            self.assertEqual(pool, targets)
            for target in scope["targets"]:
                for repeat in target["repeats"]:
                    self.assertLessEqual(
                        set(repeat["maximal_legal_negative_indices"]), pool
                    )

    def test_outer_and_inner_reuse_contracts_are_recorded(self) -> None:
        by_type = {row["scope_type"]: row for row in self.artifacts[0]["scopes"]}
        self.assertEqual(
            by_type["inner_validation"]["reuse_inner_subject_folds"], ["0", "1", "2"]
        )
        self.assertEqual(
            by_type["outer_test"]["reuse_outer_subject_folds"],
            ["0", "1", "2", "3", "4", "5"],
        )

    def test_paired_verification_is_derived_from_same_ordering(self) -> None:
        candidates, pairs, _ = self.artifacts
        candidate_target = candidates["scopes"][0]["targets"][0]
        paired_target = pairs["scopes"][0]["targets"][0]
        for frozen, paired in zip(
            candidate_target["repeats"], paired_target["repeats"], strict=True
        ):
            ordering = frozen["maximal_legal_negative_indices"]
            self.assertEqual(paired["auroc_1_to_1"]["negative_index"], ordering[0])
            self.assertEqual(paired["auprc_1_to_49"]["negative_indices"], ordering[:49])

    def test_forward_reverse_input_is_canonical_byte_identical(self) -> None:
        reverse = build_candidate_artifacts(
            reversed(self.stimuli), reversed(self.scope_rows), provenance=provenance()
        )
        for forward_value, reverse_value in zip(self.artifacts, reverse, strict=True):
            self.assertEqual(
                canonical_json_bytes(forward_value), canonical_json_bytes(reverse_value)
            )

    def test_wrong_frozen_manifest_is_rejected(self) -> None:
        wrong = provenance()
        wrong["encoder_tokenizer_manifest_hash"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "frozen encoder_tokenizer_manifest_hash"):
            build_candidate_artifacts(self.stimuli[:4], scopes(self.ids[:4]), provenance=wrong)

    def test_cross_artifact_provenance_mismatch_is_rejected(self) -> None:
        candidates, pairs, audit = copy.deepcopy(self.artifacts)
        pairs["provenance"]["released_text_manifest_sha256"] = "a" * 64
        self.assertTrue(validate_candidate_artifacts(candidates, pairs, audit))

    def test_wrong_scope_identity_is_rejected(self) -> None:
        wrong_scopes = scopes(self.ids[:4])
        wrong_scopes[0]["pool_ids"].append("zuco_2_0|task2_tsr|tsr.csv|1|doc|1")
        with self.assertRaisesRegex(ValueError, "outside task"):
            build_candidate_artifacts(self.stimuli[:4], wrong_scopes, provenance=provenance())

    def test_reuse_contract_cannot_be_silently_changed(self) -> None:
        wrong_scopes = scopes(self.ids[:4])
        wrong_scopes[0]["reuse_outer_subject_folds"] = ["0"]
        with self.assertRaisesRegex(ValueError, "six subject folds"):
            build_candidate_artifacts(self.stimuli[:4], wrong_scopes, provenance=provenance())

    def test_forbidden_eeg_and_roamm_inputs_are_rejected(self) -> None:
        bad_stimuli = copy.deepcopy(self.stimuli[:4])
        bad_stimuli[0]["eeg_values"] = [0.0]
        with self.assertRaisesRegex(ValueError, "forbidden EEG"):
            build_candidate_artifacts(bad_stimuli, scopes(self.ids[:4]), provenance=provenance())
        bad_provenance = provenance()
        bad_provenance["roamm_paths_read"] = ["ds007629"]
        with self.assertRaisesRegex(ValueError, "forbidden EEG/ROAMM"):
            build_candidate_artifacts(
                self.stimuli[:4], scopes(self.ids[:4]), provenance=bad_provenance
            )

    def test_h_exact_source_identity_is_excluded_after_cosine(self) -> None:
        small = [stimulus(index, dim=4) for index in range(4)]
        ids = [str(row["stimulus_id"]) for row in small]
        small[0]["h_source_ids"] = [ids[1]]
        candidates, _, audit = build_candidate_artifacts(
            small, scopes(ids), provenance=provenance()
        )
        target = candidates["scopes"][0]["targets"][0]
        stimulus_ids = [row["stimulus_id"] for row in candidates["stimuli"]]
        h_index = stimulus_ids.index(ids[1])
        self.assertNotIn(h_index, target["repeats"][0]["maximal_legal_negative_indices"])
        ledger = audit["scopes"][0]["targets"][0]
        self.assertEqual(ledger["sequential_exclusions"]["h_full_identity_excluded"], 1)

    def test_cosine_equal_retained_and_greater_excluded_in_ledger(self) -> None:
        small = [stimulus(index, dim=4) for index in range(4)]
        small[0]["embedding"] = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        small[1]["embedding"] = np.array([0.9, np.sqrt(0.19), 0.0, 0.0], dtype=np.float32)
        small[2]["embedding"] = np.array([0.91, np.sqrt(1 - 0.91**2), 0.0, 0.0], dtype=np.float32)
        ids = [str(row["stimulus_id"]) for row in small]
        _, _, audit = build_candidate_artifacts(small, scopes(ids), provenance=provenance())
        ledger = audit["scopes"][0]["targets"][0]
        self.assertEqual(ledger["sequential_exclusions"]["cosine_excluded"], 1)
        self.assertEqual(ledger["counts"]["cosine_pass"], 2)


if __name__ == "__main__":
    unittest.main()
