from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_code" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.candidate_common_support import (  # noqa: E402
    BASE_FILE_SHA256,
    EXCLUSION_REASON,
    canonical_triplet_bytes,
    derive_common_support,
    file_sha256,
    load_verified_base_triplet,
    reverse_scope_target_order,
    validate_common_support,
)
from data.joint_split import canonical_json_bytes, sha256_bytes  # noqa: E402


BASE_PATHS = (
    ROOT / "01_data_protocol/candidates/candidate_lists.json",
    ROOT / "01_data_protocol/candidates/paired_verification_pairs.json",
    ROOT / "04_results/audits/zuco2_candidate_feasibility.json",
)
OUTPUT_PATHS = (
    ROOT / "01_data_protocol/candidates/candidate_lists_n10_common_support.json",
    ROOT / "01_data_protocol/candidates/paired_verification_pairs_n10.json",
    ROOT / "04_results/audits/zuco2_n10_common_support_audit.json",
)


def _integrity(label: str) -> dict[str, object]:
    return {"canonical_payload_sha256": "0" * 64, "canonical_payload_bytes": 0, "hash_scope": label}


def _synthetic() -> tuple[dict, dict, dict]:
    stimuli = [
        {
            "stimulus_id": f"zuco_2_0|task1_nr|doc.csv|{index}|{index}|0",
            "task": "task1_nr",
            "exact_text_sha256": hashlib.sha256(f"text-{index}".encode()).hexdigest(),
            "token_length": 10 + index,
            "h_full_source_indices": [],
        }
        for index in range(11)
    ]

    def target(target_index: int, legal_count: int) -> dict:
        negatives = [value for value in range(11) if value != target_index][:legal_count]
        repeats = []
        for repeat in range(5):
            repeats.append(
                {
                    "repeat": repeat,
                    "maximal_legal_negative_indices": negatives,
                    "n_lists": {
                        "10": {
                            "available": legal_count >= 9,
                            "negative_prefix_length": 9 if legal_count >= 9 else 0,
                            "target_position": repeat if legal_count >= 9 else None,
                        }
                    },
                }
            )
        return {"target_index": target_index, "legal_count": legal_count, "repeats": repeats}

    def audit_target(target_index: int, legal_count: int) -> dict:
        counts = {
            "raw_pool": 11,
            "after_target_exclusion": 10,
            "length_pass": legal_count,
            "cosine_pass": legal_count,
            "h_full_pass": legal_count,
            "legal_count": legal_count,
        }
        return {
            "target_index": target_index,
            "counts": counts,
            "sequential_exclusions": {
                "target_identity_excluded": 1,
                "length_excluded": 10 - legal_count,
                "cosine_excluded": 0,
                "h_full_identity_excluded": 0,
            },
        }

    scope_identities = [
        {
            "task": "task1_nr",
            "scope_type": "outer_test",
            "scope_id": "task1_nr|outer_t0",
            "outer_text_fold": "0",
            "reuse_outer_subject_folds": [str(value) for value in range(6)],
        },
        {
            "task": "task1_nr",
            "scope_type": "inner_validation",
            "scope_id": "task1_nr|outer_s0_t0|inner_t0",
            "outer_cell_id": "task1_nr|outer_s0_t0",
            "outer_subject_fold": "0",
            "outer_text_fold": "0",
            "inner_text_fold": "0",
            "reuse_inner_subject_folds": ["0", "1", "2"],
        },
    ]
    candidate_scopes = [
        {
            **identity,
            "pool_stimulus_indices": list(range(11)),
            "target_count": 2,
            "targets": [target(0, 8), target(1, 9)],
        }
        for identity in scope_identities
    ]
    pair_scopes = [{**identity, "targets": []} for identity in scope_identities]
    audit_scopes = [
        {**identity, "targets": [audit_target(0, 8), audit_target(1, 9)]}
        for identity in scope_identities
    ]
    provenance = {"fixture": "json-only", "roamm_paths_read": []}
    candidates = {
        "dataset": "zuco_2_0",
        "seed": 20260813,
        "run_id": "fixture",
        "provenance": provenance,
        "identity_encoding": "fixture",
        "integrity": _integrity("fixture"),
        "stimuli": stimuli,
        "scopes": candidate_scopes,
    }
    pairs = {
        "dataset": "zuco_2_0",
        "seed": 20260813,
        "run_id": "fixture",
        "provenance": provenance,
        "integrity": _integrity("fixture"),
        "scopes": pair_scopes,
    }
    audit = {
        "dataset": "zuco_2_0",
        "seed": 20260813,
        "run_id": "fixture",
        "provenance": provenance,
        "integrity": _integrity("fixture"),
        "scopes": audit_scopes,
    }
    return candidates, pairs, audit


def _derive_fixture() -> tuple[dict, dict, dict]:
    return derive_common_support(
        *_synthetic(),
        base_file_hashes={key: value for key, value in BASE_FILE_SHA256.items()},
        run_id="fixture-common-support",
        enforce_frozen_counts=False,
    )


class CandidateCommonSupportSyntheticTests(unittest.TestCase):
    def test_eight_nine_boundary_and_excluded_ledger(self) -> None:
        candidates, _, audit = _derive_fixture()
        for scope in candidates["scopes"]:
            excluded, included = scope["targets"]
            self.assertFalse(excluded["eligible"])
            self.assertEqual(excluded["exclusion_reason"], EXCLUSION_REASON)
            self.assertEqual(excluded["sequential_counts"]["legal_count"], 8)
            self.assertTrue(included["eligible"])
            self.assertIsNone(included["exclusion_reason"])
        self.assertEqual(audit["assertions"]["training_records_removed"], 0)
        self.assertEqual(audit["count_summary"]["overall"], {
            "eligible": 2, "total": 4, "excluded": 2, "coverage": 0.5,
            "scope_count": 2, "minimum_scope_coverage": 0.5,
        })

    def test_five_repeats_prefix_target_position_and_pairs(self) -> None:
        candidates, pairs, _ = _derive_fixture()
        base_candidates, _, _ = _synthetic()
        base_scope_map = {row["scope_id"]: row for row in base_candidates["scopes"]}
        pair_scope_map = {row["scope_id"]: row for row in pairs["scopes"]}
        for scope in candidates["scopes"]:
            included = scope["targets"][1]
            base_included = base_scope_map[scope["scope_id"]]["targets"][1]
            paired = pair_scope_map[scope["scope_id"]]["targets"][1]
            self.assertEqual(len(included["repeats"]), 5)
            for repeat, base_repeat, pair_repeat in zip(
                included["repeats"], base_included["repeats"], paired["repeats"], strict=True
            ):
                self.assertEqual(repeat["negative_indices"], base_repeat["maximal_legal_negative_indices"][:9])
                self.assertEqual(repeat["target_position"], base_repeat["n_lists"]["10"]["target_position"])
                self.assertEqual(len(set(repeat["negative_indices"])), 9)
                self.assertEqual(pair_repeat["auroc_1_to_1"]["negative_index"], repeat["negative_indices"][0])
                self.assertEqual(pair_repeat["auprc_1_to_9"]["negative_indices"], repeat["negative_indices"])
                self.assertEqual(pair_repeat["auprc_1_to_9"]["positive_prevalence"], 0.1)

    def test_scope_identity_and_reverse_order_determinism(self) -> None:
        base = _synthetic()
        forward = derive_common_support(
            *base, base_file_hashes=BASE_FILE_SHA256, run_id="fixture", enforce_frozen_counts=False
        )
        reverse = derive_common_support(
            *(reverse_scope_target_order(value) for value in base),
            base_file_hashes=BASE_FILE_SHA256,
            run_id="fixture",
            enforce_frozen_counts=False,
        )
        self.assertEqual(canonical_triplet_bytes(forward), canonical_triplet_bytes(reverse))
        identities = [(row["scope_type"], row["scope_id"]) for row in forward[0]["scopes"]]
        self.assertEqual(identities, sorted(identities, key=lambda value: ("task1_nr", value[0], value[1])))

    def test_physical_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / name for name in ("c.json", "p.json", "a.json")]
            for path, value in zip(paths, _synthetic(), strict=True):
                path.write_bytes(canonical_json_bytes(value) + b"\n")
            with self.assertRaisesRegex(ValueError, "physical SHA256 mismatch"):
                load_verified_base_triplet(*paths, expected_file_sha256=BASE_FILE_SHA256)

    def test_canonical_hash_mismatch_is_rejected_after_physical_admission(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / name for name in ("c.json", "p.json", "a.json")]
            for path, value in zip(paths, _synthetic(), strict=True):
                path.write_bytes(canonical_json_bytes(value) + b"\n")
            expected = {
                "candidate_lists": file_sha256(paths[0]),
                "paired_verification_pairs": file_sha256(paths[1]),
                "candidate_feasibility": file_sha256(paths[2]),
            }
            with self.assertRaisesRegex(ValueError, "canonical SHA256 mismatch"):
                load_verified_base_triplet(*paths, expected_file_sha256=expected)

    def test_source_has_no_forbidden_runtime_imports(self) -> None:
        forbidden = {"transformers", "sentence_transformers", "torch", "mne", "h5py"}
        for path in (
            ROOT / "02_code/src/data/candidate_common_support.py",
            ROOT / "02_code/scripts/build_zuco2_n10_common_support.py",
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertTrue(forbidden.isdisjoint(imports), (path, imports & forbidden))


class CandidateCommonSupportRealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = load_verified_base_triplet(*BASE_PATHS)
        cls.derived = derive_common_support(
            *cls.base[:3], base_file_hashes=cls.base[3]
        )
        cls.second = derive_common_support(
            *cls.base[:3], base_file_hashes=cls.base[3]
        )
        cls.reverse = derive_common_support(
            *(reverse_scope_target_order(value) for value in cls.base[:3]),
            base_file_hashes=cls.base[3],
        )
        cls.formal = tuple(json.loads(path.read_text(encoding="utf-8")) for path in OUTPUT_PATHS)

    def test_real_counts_coverage_failure_stages_and_bindings(self) -> None:
        audit = self.derived[2]
        summary = audit["count_summary"]
        self.assertEqual((summary["outer"]["task1_nr"]["eligible"], summary["outer"]["task1_nr"]["total"]), (306, 349))
        self.assertEqual((summary["outer"]["task2_tsr"]["eligible"], summary["outer"]["task2_tsr"]["total"]), (359, 390))
        self.assertEqual((summary["inner"]["task1_nr"]["eligible"], summary["inner"]["task1_nr"]["total"]), (7553, 8376))
        self.assertEqual((summary["inner"]["task2_tsr"]["eligible"], summary["inner"]["task2_tsr"]["total"]), (8843, 9360))
        self.assertEqual((summary["overall"]["eligible"], summary["overall"]["total"], summary["overall"]["excluded"]), (17061, 18475, 1414))
        self.assertGreaterEqual(summary["outer"]["total"]["minimum_scope_coverage"], 6 / 7)
        self.assertGreaterEqual(summary["inner"]["total"]["minimum_scope_coverage"], 77 / 93)
        self.assertEqual(audit["failure_stage_counts"], {"length": 1402, "cosine": 0, "H": 12})
        self.assertEqual(self.base[3], BASE_FILE_SHA256)
        self.assertEqual(validate_common_support(*self.derived), [])

    def test_real_twice_reverse_and_formal_are_byte_identical(self) -> None:
        expected = canonical_triplet_bytes(self.derived)
        self.assertEqual(expected, canonical_triplet_bytes(self.second))
        self.assertEqual(expected, canonical_triplet_bytes(self.reverse))
        self.assertEqual(expected, canonical_triplet_bytes(self.formal))
        self.assertEqual(
            [file_sha256(path) for path in OUTPUT_PATHS],
            [sha256_bytes(value) for value in expected],
        )


if __name__ == "__main__":
    unittest.main()
