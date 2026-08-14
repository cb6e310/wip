#!/usr/bin/env python3
"""Synthetic contract tests for the SPEC v3.9 ZuCo2 inner splitter."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "src"))

from data.inner_split import (  # noqa: E402
    DEFAULT_SEED,
    build_inner_artifacts,
    validate_inner_artifact,
)
from data.joint_split import (  # noqa: E402
    build_joint_split,
    canonical_json_bytes,
    sha256_bytes,
)


OUTER_FILE_SHA = "1" * 64
MANIFEST = {
    "semantic_config_hash": "2" * 64,
    "semantic_source_manifest_hash": "3" * 64,
    "official_reader_sha256": "4" * 64,
    "dataset_source_manifest_hash": "5" * 64,
    "read_paths": ["01_data_protocol/datasets/zuco_2.0/synthetic.mat"],
    "roamm_paths_read": [],
}


def synthetic_panel(task: str, *, subject_count: int = 18) -> dict[str, object]:
    records = []
    for subject_index in range(subject_count):
        subject = f"S{subject_index:02d}"
        for stimulus_index in range(20):
            stimulus = f"zuco_2_0|{task}|doc.csv|{stimulus_index + 1}|p{stimulus_index // 2}|s{stimulus_index}"
            records.append(
                {
                    "record_id": f"{subject}|{stimulus}",
                    "subject_id": subject,
                    "stimulus_id": stimulus,
                    "group_key": f"zuco_2_0|{task}|doc.csv|p{stimulus_index // 2}",
                    "source_slot": stimulus,
                    "valid_sentence_trials": 1,
                    "join_status": "SOURCE_VERIFIED",
                    "eligible": True,
                }
            )
    return build_joint_split(records, dataset="zuco_2_0", task=task, seed=DEFAULT_SEED)


def outer_artifact(*, nr_subjects: int = 18, tsr_subjects: int = 18) -> dict[str, object]:
    panels = {
        "task1_nr": synthetic_panel("task1_nr", subject_count=nr_subjects),
        "task2_tsr": synthetic_panel("task2_tsr", subject_count=tsr_subjects),
    }
    config = {"method": "synthetic-outer", "seed": DEFAULT_SEED, "tasks": sorted(panels)}
    artifact: dict[str, object] = {
        "schema_version": 1,
        "dataset": "zuco_2_0",
        "seed": DEFAULT_SEED,
        "status": "PASS",
        "config": config,
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
        "panels": panels,
    }
    payload = canonical_json_bytes(artifact)
    artifact["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
    }
    return artifact


def observations(
    outer: dict[str, object], *, low_tasks: set[str] | None = None
) -> list[dict[str, str]]:
    low_tasks = low_tasks or set()
    rows = []
    for task, panel in outer["panels"].items():
        for record in panel["records"]:
            item = (
                f"zuco_2_0|{task}|unique-{record['record_id']}"
                if task in low_tasks
                else f"zuco_2_0|{task}|common"
            )
            rows.append(
                {
                    "task": task,
                    "record_id": record["record_id"],
                    "subject_id": record["subject_id"],
                    "stimulus_id": record["stimulus_id"],
                    "item_id": item,
                }
            )
    return rows


def build(outer: dict[str, object], rows: list[dict[str, str]]):
    return build_inner_artifacts(
        outer,
        rows,
        outer_file_sha256=OUTER_FILE_SHA,
        expected_outer_file_sha256=OUTER_FILE_SHA,
        semantic_manifest=MANIFEST,
        seed=DEFAULT_SEED,
        run_id="synthetic-test",
    )


class InnerSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer = outer_artifact()
        cls.high_rows = observations(cls.outer)

    def test_provisional_4x4_is_kept_when_j17_does_not_trigger(self):
        artifact, audit = build(self.outer, self.high_rows)
        self.assertEqual(artifact["status"], "PASS")
        self.assertEqual(validate_inner_artifact(artifact), [])
        for task in ("task1_nr", "task2_tsr"):
            decision = artifact["panels"][task]["decision"]
            self.assertFalse(decision["downgraded"])
            self.assertEqual((decision["final_subject_folds"], decision["final_text_folds"]), (4, 4))
            self.assertEqual(artifact["panels"][task]["inner_cell_count"], 480)
            self.assertGreaterEqual(decision["minimum_provisional_item_support_median"], 10)
        self.assertTrue(audit["assertions"]["all_60_outer_cells_audited"])

    def test_subject_below_12_triggers_task_global_3x3(self):
        outer = outer_artifact(nr_subjects=12, tsr_subjects=18)
        artifact, _ = build(outer, observations(outer))
        nr = artifact["panels"]["task1_nr"]
        tsr = artifact["panels"]["task2_tsr"]
        self.assertTrue(nr["decision"]["subject_trigger_any_cell"])
        self.assertEqual({cell["fold_counts"]["subject"] for cell in nr["outer_cells"]}, {3})
        self.assertFalse(tsr["decision"]["downgraded"])

    def test_item_median_below_10_triggers_all_task_cells(self):
        rows = observations(self.outer, low_tasks={"task1_nr"})
        artifact, audit = build(self.outer, rows)
        decision = artifact["panels"]["task1_nr"]["decision"]
        self.assertTrue(decision["item_trigger_any_partition"])
        self.assertEqual(decision["minimum_provisional_item_support_median"], 1.0)
        self.assertEqual(
            {cell["fold_counts"]["subject"] for cell in artifact["panels"]["task1_nr"]["outer_cells"]},
            {3},
        )
        self.assertTrue(any(cell["item_trigger"] for cell in audit["tasks"]["task1_nr"]["outer_cells"]))

    def test_nr_and_tsr_decisions_are_independent(self):
        artifact, _ = build(self.outer, observations(self.outer, low_tasks={"task1_nr"}))
        self.assertTrue(artifact["panels"]["task1_nr"]["decision"]["downgraded"])
        self.assertFalse(artifact["panels"]["task2_tsr"]["decision"]["downgraded"])

    def test_groups_are_atomic_and_outer_test_is_isolated(self):
        artifact, _ = build(self.outer, self.high_rows)
        for panel in artifact["panels"].values():
            for cell in panel["outer_cells"]:
                group_folds = {}
                for group in cell["text_group_assignments"]:
                    group_folds.setdefault(group["group_key"], set()).add(group["inner_text_fold"])
                self.assertTrue(all(len(folds) == 1 for folds in group_folds.values()))
                outer_test_records = set(cell["outer_test_record_ids"])
                outer_test_subjects = set(cell["outer_test_subject_ids"])
                outer_test_stimuli = set(cell["outer_test_stimulus_ids"])
                for inner in cell["inner_cells"]:
                    for prefix in ("train", "validation", "held_out_only"):
                        resolved_records = {
                            cell["outer_train_record_ids"][index]
                            for index in inner[f"{prefix}_record_id_indices"]
                        }
                        self.assertFalse(resolved_records & outer_test_records)
                        self.assertFalse(set(inner[f"{prefix}_subject_ids"]) & outer_test_subjects)
                        self.assertFalse(set(inner[f"{prefix}_stimulus_ids"]) & outer_test_stimuli)

    def test_same_seed_reverse_input_is_byte_identical(self):
        first = build(self.outer, self.high_rows)
        second = build(self.outer, list(reversed(self.high_rows)))
        self.assertEqual(canonical_json_bytes(first[0]), canonical_json_bytes(second[0]))
        self.assertEqual(canonical_json_bytes(first[1]), canonical_json_bytes(second[1]))

    def test_wrong_outer_file_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "disagrees"):
            build_inner_artifacts(
                self.outer,
                self.high_rows,
                outer_file_sha256="9" * 64,
                expected_outer_file_sha256=OUTER_FILE_SHA,
                semantic_manifest=MANIFEST,
            )

    def test_nonpass_outer_status_is_rejected(self):
        broken = copy.deepcopy(self.outer)
        broken["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "status must be PASS"):
            build(broken, self.high_rows)

    def test_empty_or_malformed_observation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ledger is empty"):
            build(self.outer, [])
        malformed = copy.deepcopy(self.high_rows)
        malformed[0]["item_id"] = ""
        with self.assertRaisesRegex(ValueError, "empty required field"):
            build(self.outer, malformed)

    def test_roamm_manifest_path_is_rejected(self):
        manifest = dict(MANIFEST)
        manifest["read_paths"] = ["01_data_protocol/datasets/roamm_ds007629_v1.3.0/file.pkl"]
        with self.assertRaisesRegex(ValueError, "ROAMM path"):
            build_inner_artifacts(
                self.outer,
                self.high_rows,
                outer_file_sha256=OUTER_FILE_SHA,
                expected_outer_file_sha256=OUTER_FILE_SHA,
                semantic_manifest=manifest,
            )


if __name__ == "__main__":
    unittest.main()
