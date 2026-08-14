from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "02_code" / "src"
sys.path.insert(0, str(SOURCE))
from protocol.semantic_items import (  # noqa: E402
    ItemStats,
    add_observation,
    config_hash,
    decide_item,
    normalize_surface,
    summarize_stats,
)


class SemanticItemContractTests(unittest.TestCase):
    @staticmethod
    def official(value: str) -> bool:
        return any(char.isascii() and char.isalnum() for char in value)

    def test_normalization_does_not_stem_or_strip_attached_punctuation(self) -> None:
        self.assertEqual(normalize_surface("  CAFE\u0301  "), "café")
        decision = decide_item(" Ford, ", dataset="zuco_2_0", task="task1_NR", is_real_word=self.official)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.item_id, "zuco_2_0|task1_NR|ford,")

    def test_official_predicate_and_numeric_exclusion_are_independent(self) -> None:
        rejected = decide_item("123", dataset="d", task="t", is_real_word=self.official)
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.reason, "numeric_or_nonlexical")
        rejected = decide_item("!!!", dataset="d", task="t", is_real_word=self.official)
        self.assertEqual(rejected.reason, "official_is_real_word_false")

    def test_support_gate_requires_both_observation_and_subject_thresholds(self) -> None:
        stats: dict[str, ItemStats] = {}
        decision = decide_item("signal", dataset="d", task="t", is_real_word=self.official)
        for index in range(20):
            add_observation(stats, decision, subject_id=f"s{index % 5}", trial_id=f"s{index % 5}|i{index}")
        report = summarize_stats(stats, subject_ids=[f"s{index}" for index in range(5)])
        self.assertEqual(report["supported_item_count"], 1)
        self.assertEqual(report["support_redline_status"], "PASS")
        self.assertEqual(report["supported_item_rate"], 1.0)

    def test_low_support_redline_is_explicit(self) -> None:
        stats: dict[str, ItemStats] = {}
        for name in ("one", "two", "three", "four", "five", "six"):
            decision = decide_item(name, dataset="d", task="t", is_real_word=self.official)
            add_observation(stats, decision, subject_id="s0", trial_id=f"s0|{name}")
        report = summarize_stats(stats, subject_ids=["s0"])
        self.assertEqual(report["supported_item_count"], 0)
        self.assertEqual(report["support_redline_status"], "NO_GO")

    def test_config_hash_is_stable(self) -> None:
        self.assertEqual(len(config_hash()), 64)
        self.assertEqual(config_hash(), config_hash())


if __name__ == "__main__":
    unittest.main()
