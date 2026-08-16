from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_code" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from protocol.h_definition import build_h_full  # noqa: E402
from protocol.leakage_audit import (  # noqa: E402
    EXPECTED_INPUTS,
    audit_h_payload,
    build_pre_run_audit,
    build_scope_index,
    mutate_ledger,
    synthetic_valid_run_ledger,
    validate_candidate_h_boundary,
    validate_exact_bindings,
    validate_protocol_view,
    validate_repeat_projection,
    validate_run_ledger,
    validate_scope_projection,
    validate_scoring_contract,
    verify_json_integrity,
)


def synthetic_protocol_view() -> dict:
    record_subject = {
        "fit": "s1",
        "inner-held": "s1",
        "validation": "s3",
        "outer-test": "s2",
        "outer-held": "s1",
    }
    record_stimulus = {
        "fit": "stim-a",
        "inner-held": "stim-a2",
        "validation": "stim-c",
        "outer-test": "stim-b",
        "outer-held": "stim-b2",
    }
    record_group = {
        "fit": "group-a",
        "inner-held": "group-a2",
        "validation": "group-c",
        "outer-test": "group-b",
        "outer-held": "group-b2",
    }
    all_ids = list(record_subject)
    outer = {
        "task": "task1_nr",
        "outer_cell_id": "task1_nr|outer_s0_t0",
        "all_record_ids": all_ids,
        "train_record_ids": ["fit", "inner-held", "validation"],
        "test_record_ids": ["outer-test"],
        "held_out_only_record_ids": ["outer-held"],
        "train_subject_ids": ["s1", "s3"],
        "test_subject_ids": ["s2"],
        "train_stimulus_ids": ["stim-a", "stim-a2", "stim-c"],
        "test_stimulus_ids": ["stim-b"],
        "train_group_ids": ["group-a", "group-a2", "group-c"],
        "test_group_ids": ["group-b"],
        "held_out_only_group_ids": ["group-b2"],
        "record_subject": record_subject,
        "record_stimulus": record_stimulus,
        "record_group": record_group,
        "record_subject_fold": {
            "fit": "1",
            "inner-held": "1",
            "validation": "2",
            "outer-test": "0",
            "outer-held": "0",
        },
        "record_text_fold": {
            "fit": "1",
            "inner-held": "2",
            "validation": "3",
            "outer-test": "0",
            "outer-held": "2",
        },
        "subject_fold": "0",
        "text_fold": "0",
    }
    inner = {
        "task": "task1_nr",
        "outer_cell_id": outer["outer_cell_id"],
        "inner_cell_id": outer["outer_cell_id"] + "|inner_s0_t0",
        "outer_train_record_ids": outer["train_record_ids"],
        "outer_test_record_ids": outer["test_record_ids"],
        "outer_test_subject_ids": outer["test_subject_ids"],
        "outer_test_stimulus_ids": outer["test_stimulus_ids"],
        "outer_test_group_ids": outer["test_group_ids"],
        "train_record_ids": ["fit"],
        "validation_record_ids": ["validation"],
        "held_out_only_record_ids": ["inner-held"],
        "train_subject_ids": ["s1"],
        "validation_subject_ids": ["s3"],
        "train_stimulus_ids": ["stim-a"],
        "validation_stimulus_ids": ["stim-c"],
        "train_group_ids": ["group-a"],
        "validation_group_ids": ["group-c"],
        "held_out_only_group_ids": ["group-a2"],
        "record_subject": record_subject,
        "record_stimulus": record_stimulus,
        "record_group": record_group,
    }
    return {"outer_cells": [outer], "inner_cells": [inner]}


def synthetic_projection() -> tuple[dict, dict, dict, dict]:
    base_repeats = []
    derived_repeats = []
    pair_repeats = []
    for repeat in range(5):
        negatives = list(range(1, 10))
        base_repeats.append(
            {
                "repeat": repeat,
                "maximal_legal_negative_indices": negatives,
                "n_lists": {"10": {"target_position": repeat}},
            }
        )
        derived_repeats.append(
            {"repeat": repeat, "negative_indices": negatives, "target_position": repeat}
        )
        pair_repeats.append(
            {
                "repeat": repeat,
                "auroc_1_to_1": {"negative_index": 1},
                "auprc_1_to_9": {
                    "negative_indices": negatives,
                    "positive_prevalence": 0.1,
                },
            }
        )
    base = {"target_index": 0, "legal_count": 9, "repeats": base_repeats}
    derived = {
        "target_index": 0,
        "legal_count": 9,
        "eligible": True,
        "exclusion_reason": None,
        "repeats": derived_repeats,
    }
    pair = {
        "target_index": 0,
        "eligible": True,
        "exclusion_reason": None,
        "repeats": pair_repeats,
    }
    audit = {"target_index": 0, "eligible": True, "exclusion_reason": None}
    return base, derived, pair, audit


class LeakageAuditSyntheticTests(unittest.TestCase):
    def test_valid_protocol_view_passes_v1_v2(self) -> None:
        self.assertEqual(validate_protocol_view(synthetic_protocol_view()), {"V1": [], "V2": []})

    def test_outer_subject_and_record_leakage_rejected(self) -> None:
        view = synthetic_protocol_view()
        view["outer_cells"][0]["train_record_ids"].append("outer-test")
        view["outer_cells"][0]["train_subject_ids"].append("s2")
        errors = validate_protocol_view(view)["V1"]
        self.assertTrue(any("overlap" in error for error in errors), errors)
        self.assertTrue(any("subject enters train" in error for error in errors), errors)

    def test_inner_record_outside_outer_train_rejected(self) -> None:
        view = synthetic_protocol_view()
        view["inner_cells"][0]["validation_record_ids"].append("outer-test")
        errors = validate_protocol_view(view)["V1"]
        self.assertTrue(any("outer-test record" in error or "outer-train partition" in error for error in errors), errors)

    def test_outer_test_stimulus_and_material_in_train_rejected(self) -> None:
        view = synthetic_protocol_view()
        view["outer_cells"][0]["train_stimulus_ids"].append("stim-b")
        view["outer_cells"][0]["train_group_ids"].append("group-b")
        errors = validate_protocol_view(view)["V2"]
        self.assertTrue(any("stimulus enters train" in error for error in errors), errors)
        self.assertTrue(any("material group crosses" in error for error in errors), errors)

    def test_atomic_inner_group_crossing_rejected(self) -> None:
        view = synthetic_protocol_view()
        view["inner_cells"][0]["train_group_ids"].append("group-c")
        errors = validate_protocol_view(view)["V2"]
        self.assertTrue(any("atomic material group" in error for error in errors), errors)

    def test_h_current_future_target_statistics_candidate_and_et_rejected(self) -> None:
        context = build_h_full(
            [["prior"], ["near"], ["target"]],
            target_sentence_index=2,
            target_tokens=["target"],
            position_index=2,
        )
        cases = [
            {"current_token": "x"},
            {"future_tokens": ["x"]},
            {"sentence_length": 10},
            {"candidate_ids": ["x"]},
            {"eye_tracking": [1]},
        ]
        for payload in cases:
            self.assertTrue(audit_h_payload(context, target_tokens=["target"], payload=payload), payload)
        self.assertIn(
            "future_sentences_absent",
            audit_h_payload(context, future_sentence_indices=[2]),
        )

    def test_hash_and_provenance_mutations_rejected(self) -> None:
        expected = {"base": "a" * 64, "derived": "b" * 64}
        actual = dict(expected)
        actual["derived"] = "c" * 64
        self.assertTrue(validate_exact_bindings(actual, expected, "artifact provenance"))

    def test_scope_and_target_mutations_rejected(self) -> None:
        target = {"target_index": 0}
        base = {
            "task": "task1_nr",
            "scope_type": "outer_test",
            "scope_id": "scope",
            "pool_stimulus_indices": [0],
            "targets": [target],
        }
        derived = copy.deepcopy(base)
        pair = copy.deepcopy(base)
        audit = copy.deepcopy(base)
        derived["pool_stimulus_indices"] = [1]
        pair["targets"] = [{"target_index": 1}]
        errors = validate_scope_projection(base, derived, pair, audit)
        self.assertTrue(any("pool" in error for error in errors), errors)
        self.assertTrue(any("target" in error for error in errors), errors)

    def test_h_content_in_candidate_artifact_rejected(self) -> None:
        candidate = {
            "config": {"h_exclusion": "all_exact_H_full_source_identities"},
            "provenance": {"h_artifact_sha256": "a" * 64},
            "stimuli": [
                {
                    "task": "task1_nr",
                    "stimulus_id": "x",
                    "exact_text_sha256": "b" * 64,
                    "token_length": 2,
                    "h_full_source_indices": [],
                    "h_tokens": ["forbidden"],
                }
            ],
        }
        self.assertTrue(validate_candidate_h_boundary(candidate))

    def test_prefix_position_common_support_and_paired_mutations_rejected(self) -> None:
        base, derived, pair, audit = synthetic_projection()
        self.assertEqual(validate_repeat_projection(base, derived, pair, audit), [])
        mutations = []
        value = copy.deepcopy((base, derived, pair, audit))
        value[1]["repeats"][0]["negative_indices"][0] = 99
        mutations.append(value)
        value = copy.deepcopy((base, derived, pair, audit))
        value[1]["repeats"][0]["target_position"] = 9
        mutations.append(value)
        value = copy.deepcopy((base, derived, pair, audit))
        value[1]["eligible"] = False
        mutations.append(value)
        value = copy.deepcopy((base, derived, pair, audit))
        value[2]["repeats"][0]["auprc_1_to_9"]["negative_indices"] = [1]
        mutations.append(value)
        for mutation in mutations:
            self.assertTrue(validate_repeat_projection(*mutation), mutation)

    def test_scoring_only_and_training_removal_mutations_rejected(self) -> None:
        candidate = {"assertions": {"scoring_only": True, "training_records_removed": 0}}
        pairs = {"assertions": {"scoring_only": True, "training_records_removed": 0}}
        audit = {
            "assertions": {"scoring_only": False, "training_records_removed": 1},
            "claim_population": "wrong",
        }
        errors = validate_scoring_contract(candidate, pairs, audit)
        self.assertGreaterEqual(len(errors), 3)

    def test_v5_valid_ledger_passes(self) -> None:
        scope_index = build_scope_index(synthetic_protocol_view())
        hashes = {"outer": "a" * 64, "inner": "b" * 64}
        ledger = synthetic_valid_run_ledger(scope_index, hashes)
        self.assertEqual(validate_run_ledger(ledger, scope_index, expected_input_hashes=hashes), [])

    def test_v5_fit_scope_and_inner_validation_fit_rejected(self) -> None:
        scope_index = build_scope_index(synthetic_protocol_view())
        hashes = {"outer": "a" * 64}
        base = synthetic_valid_run_ledger(scope_index, hashes)
        for record_id in ("outside", "validation"):
            ledger = mutate_ledger(base)
            ledger["stages"][0]["fit_record_ids"] = [record_id]
            errors = validate_run_ledger(ledger, scope_index, expected_input_hashes=hashes)
            self.assertTrue(any("fit IDs" in error for error in errors), errors)

    def test_v5_outer_test_selection_threshold_tuning_rejected(self) -> None:
        scope_index = build_scope_index(synthetic_protocol_view())
        hashes = {"outer": "a" * 64}
        ledger = synthetic_valid_run_ledger(scope_index, hashes)
        ledger["stages"][1]["selection_record_ids"] = ["outer-test"]
        ledger["stages"][1]["outer_test_record_ids_read"] = ["outer-test"]
        errors = validate_run_ledger(ledger, scope_index, expected_input_hashes=hashes)
        self.assertTrue(any("selection" in error for error in errors), errors)
        self.assertTrue(any("before final scoring" in error for error in errors), errors)

    def test_v5_nonzero_test_calibration_rejected(self) -> None:
        scope_index = build_scope_index(synthetic_protocol_view())
        hashes = {"outer": "a" * 64}
        ledger = synthetic_valid_run_ledger(scope_index, hashes)
        ledger["stages"][2]["calibration_record_ids"] = ["outer-test"]
        errors = validate_run_ledger(ledger, scope_index, expected_input_hashes=hashes)
        self.assertTrue(any("calibration count" in error for error in errors), errors)


class LeakageAuditRealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = build_pre_run_audit(ROOT)

    def test_real_v1_v4_and_pre_run_v5_outcomes(self) -> None:
        self.assertEqual(self.audit["overall_outcome"], "PASS_PRE_RUN_V1_V5")
        for check in ("V1", "V2", "V3", "V4"):
            self.assertEqual(self.audit["checks"][check]["outcome"], "PASS_REAL_ARTIFACTS")
        self.assertEqual(self.audit["checks"]["V5"]["outcome"], "PASS_PRE_RUN_CONTRACT")
        self.assertIs(self.audit["future_run_admission_required"], True)
        self.assertEqual(self.audit["real_training_ledgers_audited"], 0)
        self.assertEqual(verify_json_integrity(self.audit, "formal audit")["canonical_payload_bytes"], self.audit["integrity"]["canonical_payload_bytes"])

    def test_real_exact_counts_and_boundaries(self) -> None:
        self.assertEqual(self.audit["checks"]["V1"]["outer_cell_count"], 60)
        self.assertEqual(self.audit["checks"]["V1"]["inner_cell_count"], 540)
        self.assertEqual(self.audit["checks"]["V4"]["source_scope_count"], 190)
        self.assertEqual(self.audit["checks"]["V4"]["target_count"], 18475)
        self.assertEqual(self.audit["checks"]["V4"]["repeat_count"], 92375)
        self.assertEqual(self.audit["checks"]["V4"]["eligible_target_count"], 17061)
        self.assertEqual(self.audit["checks"]["V4"]["training_records_removed"], 0)
        self.assertFalse(self.audit["assertions"]["eeg_read"])
        self.assertFalse(self.audit["assertions"]["training_run"])

    def test_real_physical_hashes_match_frozen_contract(self) -> None:
        actual = {
            name: value["file_sha256"] for name, value in self.audit["input_bindings"].items()
        }
        expected = {name: value[1] for name, value in EXPECTED_INPUTS.items()}
        self.assertEqual(actual, expected)

    def test_formal_artifact_matches_rebuild(self) -> None:
        path = ROOT / "04_results/audits/zuco2_pre_run_leakage_audit.json"
        formal = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(formal, self.audit)


if __name__ == "__main__":
    unittest.main()
