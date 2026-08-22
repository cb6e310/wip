from __future__ import annotations

import copy
import gzip
import json
import sys
import unittest
from pathlib import Path

import numpy as np


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.real_sham_rescue import (  # noqa: E402
    ADMISSION_JSON,
    ADMISSION_LEDGER,
    RECOVERY_JSON,
    build_r0_diagnosis,
    channel_topology_sentinel,
    legacy_sham_contrast,
    semantic_sham_contrast,
    validate_candidate_scope,
    validate_no_outer_reads,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ledgers(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


class RealShamRescueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.admission = _load_json(PROJECT_ROOT / ADMISSION_JSON)
        cls.recovery = _load_json(PROJECT_ROOT / RECOVERY_JSON)
        cls.ledgers = _load_ledgers(PROJECT_ROOT / ADMISSION_LEDGER)

    def test_three_frozen_contrast_formulas(self) -> None:
        real = np.asarray([2.0, 1.0])
        shams = {
            "trial_shuffle": np.asarray([0.0, 2.0]),
            "within_trial_unit_assignment_shuffle": np.asarray([1.0, 0.0]),
            "channel_block_permutation": np.asarray([-1.0, 1.0]),
        }
        np.testing.assert_allclose(semantic_sham_contrast(real, shams), [1.5, 0.0])
        np.testing.assert_allclose(legacy_sham_contrast(real, shams), [2.0, 0.0])
        np.testing.assert_allclose(channel_topology_sentinel(real, shams), [3.0, 0.0])

    def test_contrasts_reject_scope_or_shape_changes(self) -> None:
        shams = {
            "trial_shuffle": np.asarray([0.0]),
            "within_trial_unit_assignment_shuffle": np.asarray([0.0]),
            "channel_block_permutation": np.asarray([0.0]),
        }
        with self.assertRaises(ValueError):
            semantic_sham_contrast([1.0], {"trial_shuffle": [0.0]})
        changed = dict(shams)
        changed["channel_block_permutation"] = np.asarray([0.0, 1.0])
        with self.assertRaises(ValueError):
            legacy_sham_contrast([1.0], changed)

    def test_candidate_scope_is_exact(self) -> None:
        result = validate_candidate_scope(self.admission)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["new_candidate_count"], 0)
        self.assertEqual(len(result["cells"]), 4)
        tampered = copy.deepcopy(self.admission)
        del tampered["results"]["task1_nr"]["A-A1"]["raw"]["metrics"][
            "real_minus_channel_block_permutation"
        ]
        with self.assertRaises(ValueError):
            validate_candidate_scope(tampered)

    def test_no_outer_or_calibration_reads(self) -> None:
        result = validate_no_outer_reads(self.admission, self.recovery, self.ledgers)
        self.assertEqual(result["parent_v5_ledgers_validated"], 639)
        self.assertEqual(result["outer_test_eeg_label_metric_reads"], 0)
        self.assertEqual(result["calibration_reads"], 0)
        tampered = copy.deepcopy(self.ledgers)
        tampered[0]["outer_test_record_ids_read"] = ["forbidden"]
        with self.assertRaises(ValueError):
            validate_no_outer_reads(self.admission, self.recovery, tampered)

    def test_parent_old_values_reproduce_and_channel_sentinel_remains(self) -> None:
        payload, ledger = build_r0_diagnosis(PROJECT_ROOT)
        self.assertEqual(payload["outcome"], "PASS_REAL_SHAM_RESCUE_FREEZE")
        self.assertEqual(payload["old_value_reproduction"]["status"], "PASS")
        self.assertEqual(payload["execution"]["new_eeg_fits"], 0)
        self.assertEqual(payload["execution"]["outer_test_eeg_label_metric_reads"], 0)
        self.assertEqual(len(ledger), 3)
        for task in payload["diagnostics"].values():
            for basis in task.values():
                self.assertIn("delta_channel", basis)
                self.assertIn(
                    "channel_block_permutation",
                    basis["legacy_sensitivity"]["single_sham_contrasts"],
                )

    def test_formal_payload_keeps_research_only_boundary(self) -> None:
        payload, _ = build_r0_diagnosis(PROJECT_ROOT)
        self.assertEqual(payload["evidence_grade"], "RESEARCH_DIAGNOSTIC_ONLY")
        self.assertFalse(payload["claim_boundary"]["real_eeg_increment_claim"])
        self.assertTrue(payload["claim_boundary"]["parent_outcomes_immutable"])
        self.assertTrue(all(value is False for value in payload["claim_boundary"]["released"].values()))
        self.assertEqual(
            payload["next_task"],
            "R1_REAL_SHAM_INNER_DIAGNOSTIC_AFTER_AUTHOR_REVIEW_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
