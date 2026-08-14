from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol.h_definition import (  # noqa: E402
    HConfig,
    audit_h_context,
    build_h_empty,
    build_h_full,
    config_hash,
)


class HDefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentences = (
            ("A", "small", "bird", "sang"),
            ("The", "reader", "smiled"),
            ("A", "second", "context", "sentence"),
            ("Target", "sentence", "here"),
            ("Future", "material"),
        )

    def test_full_is_preceding_only_bounded_and_target_free(self) -> None:
        context = build_h_full(
            self.sentences,
            target_sentence_index=3,
            target_tokens=("Target", "sentence", "here"),
            position_index=3,
        )
        self.assertEqual(context.version, "H_full")
        self.assertLessEqual(len(context.tokens), 64)
        self.assertEqual(context.source_sentence_indices, (1, 2))
        self.assertNotIn("target", {token.casefold() for token in context.tokens})
        checks = audit_h_context(
            context,
            target_tokens=("Target", "sentence", "here"),
            future_sentence_indices=(),
        )
        self.assertTrue(all(checks.values()), checks)
        forbidden = audit_h_context(
            context,
            target_tokens=("Target", "sentence", "here"),
            future_sentence_indices=(4,),
        )
        self.assertFalse(forbidden["future_sentences_absent"])

    def test_full_drops_repeated_target_surface_forms(self) -> None:
        sentences = (("repeat",), ("Target", "repeat"), ("Target",))
        context = build_h_full(
            sentences, target_sentence_index=2, target_tokens=("TARGET", "repeat"), position_index=2
        )
        self.assertNotIn("repeat", {token.casefold() for token in context.tokens})

    def test_empty_has_position_only(self) -> None:
        context = build_h_empty(target_sentence_index=7, position_index=7)
        self.assertEqual(context.version, "H_empty")
        self.assertEqual(context.tokens, ())
        self.assertEqual(context.source_sentence_indices, ())
        self.assertTrue(all(audit_h_context(context).values()))

    def test_forbidden_payload_is_rejected_by_audit(self) -> None:
        context = build_h_empty(target_sentence_index=1, position_index=1)
        checks = audit_h_context(context, payload={"eye_tracking": [1.0]})
        self.assertFalse(checks["eye_tracking_inputs_absent"])
        checks = audit_h_context(context, payload={"sentence_length": 5})
        self.assertFalse(checks["target_statistics_absent"])
        checks = audit_h_context(context, payload={"target_sentence": "answer"})
        self.assertFalse(checks["target_payload_absent"])
        checks = audit_h_context(context, payload={"future_tokens": ["leak"]})
        self.assertFalse(checks["future_sentences_absent"])
        checks = audit_h_context(context, payload={"candidate_answers": ["leak"]})
        self.assertFalse(checks["candidate_inputs_absent"])

    def test_config_is_hashable_and_frozen(self) -> None:
        self.assertEqual(len(config_hash(HConfig())), 64)
        with self.assertRaises(ValueError):
            HConfig(max_tokens=32)


if __name__ == "__main__":
    unittest.main()
