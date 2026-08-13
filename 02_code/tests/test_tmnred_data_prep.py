from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "02_code" / "scripts" / "tmnred_data_prep_selfcheck.py"
SPEC = importlib.util.spec_from_file_location("tmnred_data_prep_selfcheck", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TMNREDDataPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = PROJECT_ROOT / "01_data_protocol" / "datasets" / "tmnred_ds005383_v1.0.0"
        if not cls.root.is_dir():
            raise unittest.SkipTest("TMNRED snapshot is not present")
        cls.report = MODULE.audit(cls.root)

    def test_event_and_subject_inventory(self) -> None:
        self.assertEqual(self.report["participants"]["count"], 30)
        self.assertEqual(self.report["events"]["file_count"], 240)
        self.assertEqual(self.report["events"]["stimulus_count"], 50)
        self.assertEqual(self.report["events"]["row_count"], 11991)
        self.assertEqual(self.report["events"]["stimulus_ids"], [str(value) for value in range(15, 65)])

    def test_known_missing_event_cell_is_explicit(self) -> None:
        exceptions = self.report["events"]["known_exceptions"]
        self.assertEqual(len(exceptions), 1)
        self.assertEqual(exceptions[0]["subject"], "sub-23")
        self.assertEqual(exceptions[0]["session"], "ses-1")
        self.assertTrue(exceptions[0]["is_known_exception"])
        self.assertEqual(len(exceptions[0]["missing_stimulus_ids"]), 9)

    def test_participant_demographics_are_not_repaired(self) -> None:
        self.assertEqual(
            self.report["participants"]["demographics_status"],
            "UNUSABLE_MISALIGNED_COLUMNS",
        )
        self.assertEqual(
            self.report["participants"]["analysis_subject_source"],
            "BIDS subject entities and event paths only",
        )

    def test_text_and_eeg_schema(self) -> None:
        self.assertEqual(self.report["text"]["row_count"], 50)
        self.assertFalse(self.report["text"]["exact_duplicate_pairs"])
        self.assertFalse(self.report["text"]["normalized_duplicate_pairs"])
        self.assertEqual(self.report["eeg"]["edf_count"], 240)
        self.assertEqual(self.report["eeg"]["sampling_frequency_hz"], 200.0)
        self.assertEqual(self.report["eeg"]["eeg_channels"], 30)
        self.assertEqual(self.report["eeg"]["trigger_channels"], 1)

    def test_audit_pass_does_not_mean_experiment_ready(self) -> None:
        self.assertEqual(self.report["status"], "PASS")
        self.assertFalse(self.report["experiment_ready"])
        self.assertIn("semantic item definition is not frozen", self.report["unresolved"])


if __name__ == "__main__":
    unittest.main()
