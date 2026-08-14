from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.joint_split import (  # noqa: E402
    build_joint_split,
    canonical_json_bytes,
    synthetic_records,
    validate_artifact,
    write_artifact,
)


def fixture_records() -> list[dict]:
    return synthetic_records()


class JointSplitContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = fixture_records()
        self.artifact = build_joint_split(
            self.records,
            dataset="zuco_2_0",
            task="task1_NR",
            seed=20260813,
        )

    def test_contract_shape_and_self_check(self) -> None:
        self.assertEqual(self.artifact["fold_counts"], {"subject": 6, "text": 5, "cells": 30})
        self.assertEqual(len(self.artifact["cells"]), 30)
        self.assertEqual(len(self.artifact["subjects"]["records"]), 12)
        self.assertEqual(self.artifact["text"]["stimulus_count"], 15)
        self.assertEqual(len(self.artifact["exclusions"]), 1)
        self.assertEqual(validate_artifact(self.artifact), [])

    def test_subject_order_is_count_descending_then_id(self) -> None:
        table = self.artifact["subjects"]["records"]
        counts = [row["valid_sentence_trial_count"] for row in table]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(
            [row["subject_id"] for row in table],
            [f"sub-{index:02d}" for index in range(1, 13)],
        )
        # Round-robin gives two subjects per subject fold for 12 subjects.  The
        # totals are intentionally not equal because ordering is driven by the
        # frozen valid-trial counts, not by a post-hoc balancing adjustment.
        self.assertEqual(
            self.artifact["subjects"]["fold_valid_sentence_trial_totals"],
            [540, 510, 480, 450, 420, 390],
        )

    def test_group_is_atomic_and_stimuli_have_one_text_fold(self) -> None:
        for group in self.artifact["text"]["groups"]:
            self.assertIn(group["group_key"], group["groups_in_fold"])
            folds = {
                record["text_fold"]
                for record in self.artifact["records"]
                if record["group_key"] == group["group_key"]
            }
            self.assertEqual(folds, {group["text_fold"]})
        self.assertEqual(len(set(self.artifact["text"]["stimulus_fold"].values())), 5)

    def test_cells_have_no_train_test_intersection(self) -> None:
        all_record_ids = {record["record_id"] for record in self.artifact["records"]}
        for cell in self.artifact["cells"]:
            self.assertFalse(set(cell["test_record_ids"]) & set(cell["train_record_ids"]))
            self.assertFalse(set(cell["test_subject_ids"]) & set(cell["train_subject_ids"]))
            self.assertFalse(set(cell["test_stimulus_ids"]) & set(cell["train_stimulus_ids"]))
            self.assertEqual(
                set(cell["test_record_ids"])
                | set(cell["train_record_ids"])
                | set(cell["held_out_only_record_ids"]),
                all_record_ids,
            )
            target_subject_fold = cell["subject_fold"]
            target_text_fold = cell["text_fold"]
            for record in self.artifact["records"]:
                if record["record_id"] in cell["test_record_ids"]:
                    self.assertEqual(record["subject_fold"], target_subject_fold)
                    self.assertEqual(record["text_fold"], target_text_fold)
                if record["record_id"] in cell["train_record_ids"]:
                    self.assertNotEqual(record["subject_fold"], target_subject_fold)
                    self.assertNotEqual(record["text_fold"], target_text_fold)

    def test_all_ids_are_held_out_in_at_least_one_cell(self) -> None:
        subject_ids = {row["subject_id"] for row in self.artifact["subjects"]["records"]}
        stimulus_ids = set(self.artifact["text"]["stimulus_ids"])
        held_subjects = set().union(*(set(cell["test_subject_ids"]) for cell in self.artifact["cells"]))
        held_stimuli = set().union(*(set(cell["test_stimulus_ids"]) for cell in self.artifact["cells"]))
        self.assertEqual(held_subjects, subject_ids)
        self.assertEqual(held_stimuli, stimulus_ids)

    def test_unverified_join_excludes_affected_stimulus(self) -> None:
        # Add one ambiguous occurrence for an otherwise verified stimulus.
        rows = copy.deepcopy(self.records)
        rows.append(
            {
                "record_id": "ambiguous-existing",
                "subject_id": "sub-02",
                "stimulus_id": "stim-01",
                "group_key": "different-group",
                "valid_sentence_trials": 2,
                "join_status": "AMBIGUOUS_DUPLICATE_TEXT",
            }
        )
        artifact = build_joint_split(rows, dataset="zuco_2_0", task="task1_NR")
        self.assertNotIn("stim-01", artifact["text"]["stimulus_ids"])
        excluded_ids = {item["record_id"] for item in artifact["exclusions"]}
        self.assertIn("ambiguous-existing", excluded_ids)
        self.assertIn("sub-01|stim-01", excluded_ids)
        reasons = next(item["reasons"] for item in artifact["exclusions"] if item["record_id"] == "sub-01|stim-01")
        self.assertIn("STIMULUS_GROUP_IDENTITY_CONFLICT", reasons)

    def test_same_seed_is_byte_deterministic(self) -> None:
        first = build_joint_split(list(reversed(self.records)), dataset="zuco_2_0", task="task1_NR", seed=20260813)
        second = build_joint_split(self.records, dataset="zuco_2_0", task="task1_NR", seed=20260813)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        self.assertEqual(first["integrity"], second["integrity"])

    def test_artifact_file_is_canonical_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outer_folds.json"
            byte_count, file_sha = write_artifact(self.artifact, path)
            self.assertEqual(byte_count, path.stat().st_size)
            self.assertEqual(file_sha, __import__("hashlib").sha256(path.read_bytes()).hexdigest())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_artifact(loaded), [])


if __name__ == "__main__":
    unittest.main()
