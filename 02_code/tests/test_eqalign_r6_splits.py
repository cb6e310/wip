"""Synthetic and adversarial checks for the namespaced R6 split surfaces."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code" / "src"))

from data.joint_split import build_joint_split, canonical_json_bytes, sha256_bytes  # noqa: E402
from eqalign_r6.split_builder import (  # noqa: E402
    build_r6_inner_artifacts,
    build_r6_outer_artifact,
    validate_r6_inner_artifact,
    validate_r6_outer_artifact,
    validate_support_audit,
)


def _records() -> dict[str, list[dict[str, object]]]:
    panels: dict[str, list[dict[str, object]]] = {}
    for task in ("task1_nr", "task2_tsr"):
        rows = []
        for subject_index in range(12):
            subject = f"{task}-sub-{subject_index:02d}"
            for stimulus_index in range(12):
                stimulus = f"{task}:slot:{stimulus_index:02d}"
                rows.append(
                    {
                        "record_id": f"{subject}|{stimulus}",
                        "subject_id": subject,
                        "stimulus_id": stimulus,
                        "source_slot": stimulus,
                        "group_key": f"{task}:group:{stimulus_index // 2:02d}",
                        "valid_sentence_trials": 1,
                        "join_status": "SOURCE_VERIFIED",
                    }
                )
        panels[task] = rows
    return panels


def _joins() -> dict[str, dict[str, object]]:
    return {
        task: {"status": "SOURCE_SLOT_JOIN_VERIFIED", "all_subject_sequences_identical": True}
        for task in ("task1_nr", "task2_tsr")
    }


def _observations(records: dict[str, list[dict[str, object]]]) -> list[dict[str, str]]:
    rows = []
    for task, records_for_task in records.items():
        for record in records_for_task:
            rows.append(
                {
                    "task": task,
                    "record_id": str(record["record_id"]),
                    "subject_id": str(record["subject_id"]),
                    "stimulus_id": str(record["stimulus_id"]),
                    "item_id": "synthetic-item",
                }
            )
    return rows


def _manifest() -> dict[str, object]:
    digest = "a" * 64
    return {
        "semantic_config_hash": digest,
        "semantic_source_manifest_hash": digest,
        "official_reader_sha256": digest,
        "dataset_source_manifest_hash": digest,
        "read_paths": ["synthetic/identity-only.json"],
        "r6_construction_source_manifest": {"files": [], "canonical_sha256": digest},
    }


def _artifacts():
    records = _records()
    outer = build_r6_outer_artifact(records, source_joins=_joins())
    outer_sha = sha256_bytes(canonical_json_bytes(outer) + b"\n")
    inner, audit = build_r6_inner_artifacts(
        outer,
        _observations(records),
        outer_file_sha256=outer_sha,
        semantic_manifest=_manifest(),
    )
    return records, outer, inner, audit


def test_outer_is_exact_6x3_and_order_invariant() -> None:
    records = _records()
    forward = build_r6_outer_artifact(records, source_joins=_joins())
    reverse = build_r6_outer_artifact(
        {task: list(reversed(rows)) for task, rows in records.items()},
        source_joins=_joins(),
    )
    assert canonical_json_bytes(forward) == canonical_json_bytes(reverse)
    assert not validate_r6_outer_artifact(forward)
    for panel in forward["panels"].values():
        assert len(panel["cells"]) == 18
        assert {cell["subject_fold"] for cell in panel["cells"]} == set("012345")
        assert {cell["text_fold"] for cell in panel["cells"]} == set("012")


def test_inner_is_exact_3x3_partitioned_and_order_invariant() -> None:
    records, outer, inner, audit = _artifacts()
    outer_sha = sha256_bytes(canonical_json_bytes(outer) + b"\n")
    reversed_inner, reversed_audit = build_r6_inner_artifacts(
        outer,
        reversed(_observations(records)),
        outer_file_sha256=outer_sha,
        semantic_manifest=_manifest(),
    )
    assert canonical_json_bytes(inner) == canonical_json_bytes(reversed_inner)
    assert canonical_json_bytes(audit) == canonical_json_bytes(reversed_audit)
    assert not validate_r6_inner_artifact(inner)
    assert not validate_support_audit(audit)
    for panel in inner["panels"].values():
        assert len(panel["outer_cells"]) == 18
        assert all(len(cell["inner_cells"]) == 9 for cell in panel["outer_cells"])


def test_outer_test_injection_is_rejected_adversarially() -> None:
    _, _, inner, _ = _artifacts()
    injected = deepcopy(inner)
    cell = injected["panels"]["task1_nr"]["outer_cells"][0]
    cell["outer_train_record_ids"][0] = cell["outer_test_record_ids"][0]
    assert validate_r6_inner_artifact(injected)


def test_sensitive_support_content_is_rejected_adversarially() -> None:
    _, _, _, audit = _artifacts()
    injected = deepcopy(audit)
    injected["eeg_array"] = [1.0, 2.0]
    assert validate_support_audit(injected)


def test_v313_joint_split_defaults_remain_6x5() -> None:
    rows = _records()["task1_nr"]
    old_default = build_joint_split(rows, dataset="zuco_2_0", task="task1_nr")
    assert old_default["fold_counts"] == {"subject": 6, "text": 5, "cells": 30}


CORE_TESTS = (
    test_outer_is_exact_6x3_and_order_invariant,
    test_inner_is_exact_3x3_partitioned_and_order_invariant,
    test_outer_test_injection_is_rejected_adversarially,
    test_sensitive_support_content_is_rejected_adversarially,
    test_v313_joint_split_defaults_remain_6x5,
)


def run_all_split_checks() -> None:
    for test in CORE_TESTS:
        test()
