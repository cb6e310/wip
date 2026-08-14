from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.zuco2_loader import MaterialRow  # noqa: E402
from data.zuco2_source_join import prove_ordered_source_join  # noqa: E402


def row(number: int, text: str, *, source_file: str = "part.csv") -> MaterialRow:
    return MaterialRow("task1_nr", source_file, number, (f"doc-{number // 3}", str(number), text, ""))


class Zuco2SourceJoinTests(unittest.TestCase):
    def test_order_proves_duplicate_text_without_using_text_as_identity(self) -> None:
        materials = [row(1, "skip"), row(2, "same"), row(3, "middle"), row(4, "same")]
        proof = prove_ordered_source_join(
            materials,
            ["same", "middle", "same"],
            dataset="zuco_2_0",
            task="task1_nr",
        )
        self.assertTrue(proof.verified)
        self.assertEqual([slot.row_number for slot in proof.slots], [2, 3, 4])
        self.assertFalse(proof.to_dict()["text_hash_is_identity"])
        self.assertEqual(proof.slots[0].source_slot_key, "zuco_2_0|task1_nr|part.csv|2|doc-0|2")

    def test_ambiguous_single_duplicate_is_blocked(self) -> None:
        proof = prove_ordered_source_join(
            [row(1, "same"), row(2, "same")],
            ["same"],
            dataset="zuco_2_0",
            task="task1_nr",
        )
        self.assertFalse(proof.verified)
        self.assertEqual(proof.status, "BLOCKED_NONUNIQUE_ORDERED_JOIN")

    def test_unmatched_sequence_is_blocked(self) -> None:
        proof = prove_ordered_source_join(
            [row(1, "one")],
            ["missing"],
            dataset="zuco_2_0",
            task="task1_nr",
        )
        self.assertFalse(proof.verified)
        self.assertEqual(proof.status, "BLOCKED_UNMATCHED_ORDERED_JOIN")

    def test_nfkc_is_consistency_normalization_only(self) -> None:
        proof = prove_ordered_source_join(
            [row(1, "  CAFE\u0301  ")],
            ["CAFÉ"],
            dataset="zuco_2_0",
            task="task1_nr",
        )
        self.assertTrue(proof.verified)
        self.assertEqual(proof.slots[0].row_number, 1)


if __name__ == "__main__":
    unittest.main()
