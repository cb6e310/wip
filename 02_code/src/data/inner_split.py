"""Deterministic ZuCo 2.0 nested inner splits for SPEC v3.9 M.4.

This module is deliberately data-agnostic.  It consumes the already-admitted
outer artifact plus compact, positive semantic-item observations.  It never
opens EEG, text, ROAMM, or held-out outcome files.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from data.joint_split import canonical_json_bytes, sha256_bytes, sha256_text


DEFAULT_SEED = 20260813
PROVISIONAL_FOLDS = 4
DOWNGRADED_FOLDS = 3
MIN_OUTER_TRAIN_SUBJECTS = 12
MIN_ITEM_SUPPORT_MEDIAN = 10.0
EXPECTED_TASKS = ("task1_nr", "task2_tsr")
ALGORITHM_VERSION = "zuco2-inner-split-v39-m4-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _integrity_payload(value: Mapping[str, Any]) -> bytes:
    payload = dict(value)
    payload.pop("integrity", None)
    return canonical_json_bytes(payload)


def _verify_integrity(value: Mapping[str, Any], label: str) -> None:
    integrity = value.get("integrity")
    if not isinstance(integrity, Mapping):
        raise ValueError(f"{label}: missing integrity block")
    payload = _integrity_payload(value)
    if integrity.get("canonical_payload_sha256") != sha256_bytes(payload):
        raise ValueError(f"{label}: canonical payload SHA256 mismatch")
    if integrity.get("canonical_payload_bytes") != len(payload):
        raise ValueError(f"{label}: canonical payload byte count mismatch")


def _verify_config_hash(value: Mapping[str, Any], label: str) -> None:
    config = value.get("config")
    if not isinstance(config, Mapping):
        raise ValueError(f"{label}: missing config")
    if value.get("config_hash") != sha256_bytes(canonical_json_bytes(config)):
        raise ValueError(f"{label}: config hash mismatch")


def validate_outer_artifact(
    outer: Mapping[str, Any],
    *,
    outer_file_sha256: str,
    expected_outer_file_sha256: str | None = None,
) -> None:
    """Hard-fail on any non-admitted or internally inconsistent outer input."""

    if not _SHA256_RE.fullmatch(str(outer_file_sha256)):
        raise ValueError("outer file SHA256 is missing or malformed")
    if expected_outer_file_sha256 is not None and outer_file_sha256 != expected_outer_file_sha256:
        raise ValueError("outer file SHA256 disagrees with the frozen expected value")
    if outer.get("status") != "PASS":
        raise ValueError("outer artifact status must be PASS")
    if outer.get("dataset") != "zuco_2_0":
        raise ValueError("outer artifact dataset must be zuco_2_0")
    _verify_integrity(outer, "outer artifact")
    _verify_config_hash(outer, "outer artifact")
    panels = outer.get("panels")
    if not isinstance(panels, Mapping) or tuple(sorted(panels)) != EXPECTED_TASKS:
        raise ValueError("outer artifact must contain exactly task1_nr and task2_tsr")
    for task in EXPECTED_TASKS:
        panel = panels[task]
        if not isinstance(panel, Mapping):
            raise ValueError(f"outer/{task}: panel is malformed")
        if panel.get("dataset") != "zuco_2_0" or panel.get("task") != task:
            raise ValueError(f"outer/{task}: dataset/task mismatch")
        if panel.get("seed") != outer.get("seed"):
            raise ValueError(f"outer/{task}: seed mismatch")
        _verify_integrity(panel, f"outer/{task}")
        _verify_config_hash(panel, f"outer/{task}")
        input_block = panel.get("input")
        if not isinstance(input_block, Mapping) or not _SHA256_RE.fullmatch(
            str(input_block.get("input_sha256", ""))
        ):
            raise ValueError(f"outer/{task}: input hash is missing or malformed")
        if not bool(panel.get("assertions", {}).get("all_checks_pass")):
            raise ValueError(f"outer/{task}: outer assertions do not pass")
        records = panel.get("records")
        cells = panel.get("cells")
        if not isinstance(records, list) or not records:
            raise ValueError(f"outer/{task}: no records")
        if not isinstance(cells, list) or len(cells) != 30:
            raise ValueError(f"outer/{task}: expected 30 outer cells")
        record_ids = [str(row.get("record_id", "")) for row in records]
        if not all(record_ids) or len(record_ids) != len(set(record_ids)):
            raise ValueError(f"outer/{task}: record IDs must be non-empty and unique")
        expected_cells = {(str(s), str(t)) for s in range(6) for t in range(5)}
        actual_cells = {(str(row.get("subject_fold")), str(row.get("text_fold"))) for row in cells}
        if actual_cells != expected_cells:
            raise ValueError(f"outer/{task}: outer 6x5 cell grid is incomplete")
        if any(row.get("status") != "PASS" for row in cells):
            raise ValueError(f"outer/{task}: every outer cell must be PASS")


def _normalise_observations(
    observations: Iterable[Mapping[str, Any]], outer: Mapping[str, Any]
) -> tuple[list[dict[str, str]], str, dict[str, Counter[str]]]:
    panels = outer["panels"]
    record_lookup: dict[str, tuple[str, str, str]] = {}
    for task in EXPECTED_TASKS:
        for row in panels[task]["records"]:
            record_id = str(row["record_id"])
            identity = (task, str(row["subject_id"]), str(row["stimulus_id"]))
            if record_id in record_lookup:
                raise ValueError(f"record ID occurs in multiple panels: {record_id}")
            record_lookup[record_id] = identity

    normalised: list[dict[str, str]] = []
    by_record: dict[str, Counter[str]] = defaultdict(Counter)
    for index, raw in enumerate(observations):
        row = {
            "task": str(raw.get("task", "")).strip(),
            "record_id": str(raw.get("record_id", "")).strip(),
            "subject_id": str(raw.get("subject_id", "")).strip(),
            "stimulus_id": str(raw.get("stimulus_id", raw.get("source_slot", ""))).strip(),
            "item_id": str(raw.get("item_id", "")).strip(),
        }
        if not all(row.values()):
            raise ValueError(f"observation {index} has an empty required field")
        expected = record_lookup.get(row["record_id"])
        if expected is None:
            raise ValueError(f"observation {index} record is absent from the admitted outer artifact")
        if expected != (row["task"], row["subject_id"], row["stimulus_id"]):
            raise ValueError(f"observation {index} identity disagrees with the outer artifact")
        if row["record_id"] != f"{row['subject_id']}|{row['stimulus_id']}":
            raise ValueError(f"observation {index} violates record_id=subject_id|source_slot")
        normalised.append(row)
        by_record[row["record_id"]][row["item_id"]] += 1
    if not normalised:
        raise ValueError("positive semantic-item observation ledger is empty")
    normalised.sort(key=canonical_json_bytes)
    return normalised, sha256_bytes(canonical_json_bytes(normalised)), dict(by_record)


def _subject_assignment(records: Sequence[Mapping[str, Any]], k: int) -> tuple[dict[str, str], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    for row in records:
        count = row.get("valid_sentence_trials")
        if not isinstance(count, int) or count <= 0:
            raise ValueError("outer-train record has non-positive valid_sentence_trials")
        counts[str(row["subject_id"])] += count
    ordered = sorted(counts, key=lambda value: (-counts[value], value))
    if len(ordered) < k:
        raise ValueError("too few outer-train subjects to populate inner folds")
    assignment = {subject: str(index % k) for index, subject in enumerate(ordered)}
    table = [
        {
            "subject_id": subject,
            "valid_sentence_trial_count": counts[subject],
            "inner_subject_fold": assignment[subject],
        }
        for subject in ordered
    ]
    return assignment, table


def _text_assignment(
    records: Sequence[Mapping[str, Any]], *, seed: int, outer_cell_id: str, k: int
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    group_stimuli: dict[str, set[str]] = defaultdict(set)
    stimulus_groups: dict[str, set[str]] = defaultdict(set)
    for row in records:
        group = str(row.get("group_key", "")).strip()
        stimulus = str(row.get("stimulus_id", "")).strip()
        if not group or not stimulus:
            raise ValueError("outer-train record has empty group/stimulus identity")
        group_stimuli[group].add(stimulus)
        stimulus_groups[stimulus].add(group)
    conflicts = sorted(stimulus for stimulus, groups in stimulus_groups.items() if len(groups) != 1)
    if conflicts:
        raise ValueError(f"outer-train stimuli cross group keys: {conflicts[:3]}")
    rows = [
        {
            "group_key": group,
            "stimulus_ids": sorted(stimuli),
            "effective_stimulus_count": len(stimuli),
            "group_hash": sha256_text(f"{seed}|{outer_cell_id}|inner|{group}"),
        }
        for group, stimuli in group_stimuli.items()
    ]
    rows.sort(key=lambda row: (-row["effective_stimulus_count"], row["group_hash"], row["group_key"]))
    totals = [0] * k
    assignment: dict[str, str] = {}
    for row in rows:
        fold = min(range(k), key=lambda index: (totals[index], index))
        row["inner_text_fold"] = str(fold)
        totals[fold] += int(row["effective_stimulus_count"])
        for stimulus in row["stimulus_ids"]:
            assignment[stimulus] = str(fold)
    if len(set(assignment.values())) != k:
        raise ValueError("inner text folds are not all populated")
    return assignment, rows


def _partition_rows(
    records: Sequence[Mapping[str, Any]],
    subject_assignment: Mapping[str, str],
    text_assignment: Mapping[str, str],
    *,
    k: int,
) -> list[dict[str, Any]]:
    assigned = [
        {
            "record_id": str(row["record_id"]),
            "subject_id": str(row["subject_id"]),
            "stimulus_id": str(row["stimulus_id"]),
            "group_key": str(row["group_key"]),
            "inner_subject_fold": subject_assignment[str(row["subject_id"])],
            "inner_text_fold": text_assignment[str(row["stimulus_id"])],
        }
        for row in records
    ]
    assigned.sort(key=lambda row: row["record_id"])
    partitions: list[dict[str, Any]] = []
    for subject_fold in range(k):
        for text_fold in range(k):
            sf, tf = str(subject_fold), str(text_fold)
            validation = [row for row in assigned if row["inner_subject_fold"] == sf and row["inner_text_fold"] == tf]
            train = [row for row in assigned if row["inner_subject_fold"] != sf and row["inner_text_fold"] != tf]
            held = [row for row in assigned if (row["inner_subject_fold"] == sf) ^ (row["inner_text_fold"] == tf)]

            def ids(rows: Sequence[Mapping[str, str]], key: str) -> list[str]:
                return sorted({str(row[key]) for row in rows})

            partitions.append(
                {
                    "inner_subject_fold": sf,
                    "inner_text_fold": tf,
                    "train_record_ids": [row["record_id"] for row in train],
                    "validation_record_ids": [row["record_id"] for row in validation],
                    "held_out_only_record_ids": [row["record_id"] for row in held],
                    "train_subject_ids": ids(train, "subject_id"),
                    "validation_subject_ids": ids(validation, "subject_id"),
                    "held_out_only_subject_ids": ids(held, "subject_id"),
                    "train_stimulus_ids": ids(train, "stimulus_id"),
                    "validation_stimulus_ids": ids(validation, "stimulus_id"),
                    "held_out_only_stimulus_ids": ids(held, "stimulus_id"),
                    "train_record_count": len(train),
                    "validation_record_count": len(validation),
                    "held_out_only_record_count": len(held),
                }
            )
    return partitions


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        raise ValueError("inner-train partition has no observed semantic item")
    middle = len(ordered) // 2
    median = float(ordered[middle]) if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return {
        "item_count": len(ordered),
        "median": median,
        "iqr": [float(ordered[(len(ordered) - 1) // 4]), float(ordered[(3 * (len(ordered) - 1)) // 4])],
        "min": int(ordered[0]),
        "max": int(ordered[-1]),
    }


def _support_for_partition(
    train_record_ids: Sequence[str], by_record: Mapping[str, Counter[str]]
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for record_id in train_record_ids:
        counts.update(by_record.get(record_id, {}))
    summary = _distribution(list(counts.values()))
    summary["item_trigger"] = bool(summary["median"] < MIN_ITEM_SUPPORT_MEDIAN)
    return summary


def _outer_cell_id(task: str, cell: Mapping[str, Any]) -> str:
    return f"{task}|outer_s{cell['subject_fold']}_t{cell['text_fold']}"


def _build_cell(
    task: str,
    panel: Mapping[str, Any],
    outer_cell: Mapping[str, Any],
    *,
    seed: int,
    k: int,
    compact_record_ids: bool = False,
) -> dict[str, Any]:
    outer_records = {str(row["record_id"]): row for row in panel["records"]}
    train_ids = [str(value) for value in outer_cell["train_record_ids"]]
    if len(train_ids) != len(set(train_ids)) or any(record_id not in outer_records for record_id in train_ids):
        raise ValueError("outer cell train_record_ids are invalid")
    records = [outer_records[record_id] for record_id in train_ids]
    outer_cell_id = _outer_cell_id(task, outer_cell)
    subject_assignment, subjects = _subject_assignment(records, k)
    text_assignment, groups = _text_assignment(records, seed=seed, outer_cell_id=outer_cell_id, k=k)
    partitions = _partition_rows(records, subject_assignment, text_assignment, k=k)
    if compact_record_ids:
        record_index = {record_id: index for index, record_id in enumerate(sorted(train_ids))}
        for partition in partitions:
            for prefix in ("train", "validation", "held_out_only"):
                values = partition.pop(f"{prefix}_record_ids")
                partition[f"{prefix}_record_id_indices"] = [record_index[value] for value in values]
            partition["record_id_encoding"] = "zero_based_indices_into_outer_train_record_ids"
    config = {
        "algorithm_version": ALGORITHM_VERSION,
        "seed": int(seed),
        "outer_cell_id": outer_cell_id,
        "subject_folds": k,
        "text_folds": k,
        "subject_order": "descending outer-train valid_sentence_trials then subject_id",
        "subject_assignment": "round_robin",
        "text_order": "descending unique outer-train stimuli then SHA256(seed|outer_cell_id|inner|group_id)",
        "text_assignment": "greedy minimum stimulus total then fold number",
        "partition_semantics": "validation=subject_fold_intersection_text_fold; train=neither; held_out_only=xor",
        "record_id_storage": (
            "lossless zero-based indices into outer_train_record_ids"
            if compact_record_ids
            else "explicit outer record IDs"
        ),
    }
    result: dict[str, Any] = {
        "outer_cell_id": outer_cell_id,
        "outer_subject_fold": str(outer_cell["subject_fold"]),
        "outer_text_fold": str(outer_cell["text_fold"]),
        "outer_test_subject_ids": sorted(str(value) for value in outer_cell["test_subject_ids"]),
        "outer_test_stimulus_ids": sorted(str(value) for value in outer_cell["test_stimulus_ids"]),
        "outer_test_record_ids": sorted(str(value) for value in outer_cell["test_record_ids"]),
        "outer_train_record_ids": sorted(train_ids),
        "fold_counts": {"subject": k, "text": k, "inner_cells": k * k},
        "subject_assignments": subjects,
        "text_group_assignments": groups,
        "inner_cells": partitions,
        "config": config,
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
    }
    _assert_cell(result)
    payload = canonical_json_bytes(result)
    result["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": "canonical JSON outer-cell object without integrity field",
    }
    return result


def _assert_cell(cell: Mapping[str, Any]) -> None:
    outer_train = set(cell["outer_train_record_ids"])
    outer_test_records = set(cell["outer_test_record_ids"])
    outer_test_subjects = set(cell["outer_test_subject_ids"])
    outer_test_stimuli = set(cell["outer_test_stimulus_ids"])
    validation_subjects: set[str] = set()
    validation_stimuli: set[str] = set()
    expected_subjects = {str(row["subject_id"]) for row in cell["subject_assignments"]}
    expected_stimuli = {
        str(stimulus)
        for group in cell["text_group_assignments"]
        for stimulus in group["stimulus_ids"]
    }
    subject_fold = {
        str(row["subject_id"]): str(row["inner_subject_fold"])
        for row in cell["subject_assignments"]
    }
    stimulus_fold = {
        str(stimulus): str(group["inner_text_fold"])
        for group in cell["text_group_assignments"]
        for stimulus in group["stimulus_ids"]
    }
    record_identity: dict[str, tuple[str, str]] = {}
    for record_id in outer_train:
        subject, separator, stimulus = str(record_id).partition("|")
        if not separator or subject not in subject_fold or stimulus not in stimulus_fold:
            raise ValueError("outer-train record ID cannot be resolved through inner assignments")
        record_identity[str(record_id)] = (subject, stimulus)
    for partition in cell["inner_cells"]:
        def partition_record_ids(prefix: str) -> set[str]:
            explicit = partition.get(f"{prefix}_record_ids")
            if isinstance(explicit, list):
                return {str(value) for value in explicit}
            indices = partition.get(f"{prefix}_record_id_indices")
            if not isinstance(indices, list) or partition.get("record_id_encoding") != "zero_based_indices_into_outer_train_record_ids":
                raise ValueError("inner partition record ID encoding is missing or malformed")
            if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
                raise ValueError("inner partition record ID index is not an integer")
            table = cell["outer_train_record_ids"]
            if any(index < 0 or index >= len(table) for index in indices):
                raise ValueError("inner partition record ID index is out of range")
            if len(indices) != len(set(indices)):
                raise ValueError("inner partition record ID indices contain duplicates")
            return {str(table[index]) for index in indices}

        train = partition_record_ids("train")
        validation = partition_record_ids("validation")
        held = partition_record_ids("held_out_only")
        if train & validation or train & held or validation & held or train | validation | held != outer_train:
            raise ValueError("inner partition does not disjointly cover outer train")
        if (train | validation | held) & outer_test_records:
            raise ValueError("inner partition overlaps outer-test records")
        sf = str(partition["inner_subject_fold"])
        tf = str(partition["inner_text_fold"])
        expected_validation = {
            record_id
            for record_id, (subject, stimulus) in record_identity.items()
            if subject_fold[subject] == sf and stimulus_fold[stimulus] == tf
        }
        expected_train = {
            record_id
            for record_id, (subject, stimulus) in record_identity.items()
            if subject_fold[subject] != sf and stimulus_fold[stimulus] != tf
        }
        expected_held = outer_train - expected_validation - expected_train
        if validation != expected_validation or train != expected_train or held != expected_held:
            raise ValueError("inner partition violates Cartesian train/validation/held-out-only semantics")
        for prefix in ("train", "validation", "held_out_only"):
            if set(partition[f"{prefix}_subject_ids"]) & outer_test_subjects:
                raise ValueError("inner partition overlaps outer-test subjects")
            if set(partition[f"{prefix}_stimulus_ids"]) & outer_test_stimuli:
                raise ValueError("inner partition overlaps outer-test stimuli")
        validation_subjects.update(partition["validation_subject_ids"])
        validation_stimuli.update(partition["validation_stimulus_ids"])
    if validation_subjects != expected_subjects or validation_stimuli != expected_stimuli:
        raise ValueError("not every outer-train subject/stimulus appears in inner validation")
    group_folds: dict[str, set[str]] = defaultdict(set)
    for group in cell["text_group_assignments"]:
        group_folds[str(group["group_key"])].add(str(group["inner_text_fold"]))
    if any(len(folds) != 1 for folds in group_folds.values()):
        raise ValueError("group crosses inner text folds")


def _validate_semantic_manifest(manifest: Mapping[str, Any]) -> None:
    required = (
        "semantic_config_hash",
        "semantic_source_manifest_hash",
        "official_reader_sha256",
        "dataset_source_manifest_hash",
    )
    for key in required:
        if not _SHA256_RE.fullmatch(str(manifest.get(key, ""))):
            raise ValueError(f"semantic manifest missing valid {key}")
    paths = manifest.get("read_paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("semantic manifest read_paths are missing")
    if any("roamm" in str(path).casefold() or "ds007629" in str(path).casefold() for path in paths):
        raise ValueError("ROAMM path is forbidden in ZuCo inner split inputs")


def build_inner_artifacts(
    outer: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
    *,
    outer_file_sha256: str,
    semantic_manifest: Mapping[str, Any],
    seed: int = DEFAULT_SEED,
    expected_outer_file_sha256: str | None = None,
    run_id: str = "2026-08-14_017_v39_zuco2_inner_split",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the final split artifact and provisional J17 support audit."""

    if int(seed) != DEFAULT_SEED:
        raise ValueError(f"SPEC v3.9 freezes seed={DEFAULT_SEED}")
    validate_outer_artifact(
        outer,
        outer_file_sha256=outer_file_sha256,
        expected_outer_file_sha256=expected_outer_file_sha256,
    )
    _validate_semantic_manifest(semantic_manifest)
    normalised, ledger_hash, by_record = _normalise_observations(observations, outer)

    provisional_by_task: dict[str, list[dict[str, Any]]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    for task in EXPECTED_TASKS:
        panel = outer["panels"][task]
        audit_cells: list[dict[str, Any]] = []
        task_subject_trigger = False
        task_item_trigger = False
        for outer_cell in panel["cells"]:
            provisional = _build_cell(
                task, panel, outer_cell, seed=int(seed), k=PROVISIONAL_FOLDS
            )
            subject_count = len(provisional["subject_assignments"])
            subject_trigger = subject_count < MIN_OUTER_TRAIN_SUBJECTS
            partition_support: list[dict[str, Any]] = []
            for partition in provisional["inner_cells"]:
                support = _support_for_partition(partition["train_record_ids"], by_record)
                partition_support.append(
                    {
                        "inner_subject_fold": partition["inner_subject_fold"],
                        "inner_text_fold": partition["inner_text_fold"],
                        **support,
                    }
                )
            item_trigger = any(bool(row["item_trigger"]) for row in partition_support)
            task_subject_trigger = task_subject_trigger or subject_trigger
            task_item_trigger = task_item_trigger or item_trigger
            audit_cells.append(
                {
                    "outer_cell_id": provisional["outer_cell_id"],
                    "outer_train_unique_valid_subject_count": subject_count,
                    "subject_trigger": subject_trigger,
                    "provisional_inner_partitions": partition_support,
                    "item_trigger": item_trigger,
                    "minimum_provisional_item_support_median": min(
                        row["median"] for row in partition_support
                    ),
                }
            )
        downgraded = task_subject_trigger or task_item_trigger
        decisions[task] = {
            "provisional_subject_folds": PROVISIONAL_FOLDS,
            "provisional_text_folds": PROVISIONAL_FOLDS,
            "final_subject_folds": DOWNGRADED_FOLDS if downgraded else PROVISIONAL_FOLDS,
            "final_text_folds": DOWNGRADED_FOLDS if downgraded else PROVISIONAL_FOLDS,
            "downgraded": downgraded,
            "subject_trigger_any_cell": task_subject_trigger,
            "item_trigger_any_partition": task_item_trigger,
            "minimum_outer_train_unique_valid_subject_count": min(
                row["outer_train_unique_valid_subject_count"] for row in audit_cells
            ),
            "minimum_provisional_item_support_median": min(
                row["minimum_provisional_item_support_median"] for row in audit_cells
            ),
            "rule": "downgrade all 30 task cells to 3x3 if any subject_count<12 or any provisional median<10",
        }
        provisional_by_task[task] = audit_cells

    final_panels: dict[str, Any] = {}
    total_inner_cells = 0
    for task in EXPECTED_TASKS:
        k = int(decisions[task]["final_subject_folds"])
        outer_cells = [
            _build_cell(
                task,
                outer["panels"][task],
                cell,
                seed=int(seed),
                k=k,
                compact_record_ids=True,
            )
            for cell in outer["panels"][task]["cells"]
        ]
        total_inner_cells += sum(len(cell["inner_cells"]) for cell in outer_cells)
        final_panels[task] = {
            "decision": decisions[task],
            "outer_cell_count": len(outer_cells),
            "inner_cell_count": sum(len(cell["inner_cells"]) for cell in outer_cells),
            "outer_cells": outer_cells,
        }

    config = {
        "spec": "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_9_2026-08-14.md#M.4",
        "algorithm_version": ALGORITHM_VERSION,
        "seed": int(seed),
        "provisional_folds": [PROVISIONAL_FOLDS, PROVISIONAL_FOLDS],
        "downgraded_folds": [DOWNGRADED_FOLDS, DOWNGRADED_FOLDS],
        "j17_subject_threshold": MIN_OUTER_TRAIN_SUBJECTS,
        "j17_item_median_threshold": MIN_ITEM_SUPPORT_MEDIAN,
        "tasks": list(EXPECTED_TASKS),
    }
    shared = {
        "schema_version": 1,
        "run_id": run_id,
        "dataset": "zuco_2_0",
        "seed": int(seed),
        "method": "ZuCo2-deterministic-outer-cell-inner-split",
        "algorithm_version": ALGORITHM_VERSION,
        "outer_file_sha256": outer_file_sha256,
        "outer_canonical_payload_sha256": outer["integrity"]["canonical_payload_sha256"],
        "outer_panel_hashes": {
            task: {
                "config_hash": outer["panels"][task]["config_hash"],
                "input_sha256": outer["panels"][task]["input"]["input_sha256"],
                "canonical_payload_sha256": outer["panels"][task]["integrity"]["canonical_payload_sha256"],
            }
            for task in EXPECTED_TASKS
        },
        "semantic_manifest": dict(semantic_manifest),
        "observation_ledger": {
            "tuple_fields": ["task", "record_id", "subject_id", "stimulus_id", "item_id"],
            "positive_observation_count": len(normalised),
            "canonical_sha256": ledger_hash,
            "embedded": False,
            "contains_no_eeg_values": True,
        },
        "config": config,
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
    }
    artifact: dict[str, Any] = {
        **shared,
        "fold": "task-local-outer-cell-inner",
        "panels": final_panels,
        "assertions": {
            "two_task_local_panels_present": tuple(sorted(final_panels)) == EXPECTED_TASKS,
            "sixty_outer_cells_present": sum(panel["outer_cell_count"] for panel in final_panels.values()) == 60,
            "inner_cell_count_matches_task_decisions": total_inner_cells
            == sum(30 * int(decisions[task]["final_subject_folds"]) ** 2 for task in EXPECTED_TASKS),
            "all_partitions_are_outer_train_only": True,
            "outer_test_record_subject_stimulus_isolation": True,
            "all_partitions_disjointly_cover_outer_train": True,
            "all_groups_are_atomic": True,
            "all_outer_train_subjects_and_stimuli_are_validated": True,
            "roamm_paths_read": [],
            "contains_no_eeg_values": True,
        },
        "status": "PASS",
    }
    artifact_payload = canonical_json_bytes(artifact)
    artifact["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(artifact_payload),
        "canonical_payload_bytes": len(artifact_payload),
        "hash_scope": "canonical JSON artifact without integrity field",
    }

    audit: dict[str, Any] = {
        **shared,
        "fold": "provisional-task-local-4x4-j17-audit",
        "thresholds": {
            "outer_train_unique_subjects_below": MIN_OUTER_TRAIN_SUBJECTS,
            "observed_item_support_median_below": MIN_ITEM_SUPPORT_MEDIAN,
        },
        "tasks": {
            task: {
                "decision": decisions[task],
                "outer_cells": provisional_by_task[task],
            }
            for task in EXPECTED_TASKS
        },
        "assertions": {
            "all_support_is_inner_train_only": True,
            "all_60_outer_cells_audited": sum(len(value) for value in provisional_by_task.values()) == 60,
            "nr_tsr_decided_independently": True,
            "no_per_cell_fold_mixing": True,
            "contains_eeg_values": False,
            "roamm_paths_read": [],
        },
        "status": "PASS",
    }
    audit_payload = canonical_json_bytes(audit)
    audit["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(audit_payload),
        "canonical_payload_bytes": len(audit_payload),
        "hash_scope": "canonical JSON audit without integrity field",
    }
    return artifact, audit


def validate_inner_artifact(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if artifact.get("status") != "PASS":
            raise ValueError("status is not PASS")
        _verify_config_hash(artifact, "inner artifact")
        _verify_integrity(artifact, "inner artifact")
        if not all(value is True or value == [] for value in artifact.get("assertions", {}).values()):
            raise ValueError("root assertion failed")
        panels = artifact.get("panels", {})
        if tuple(sorted(panels)) != EXPECTED_TASKS:
            raise ValueError("task panels mismatch")
        for task in EXPECTED_TASKS:
            panel = panels[task]
            k = int(panel["decision"]["final_subject_folds"])
            if len(panel["outer_cells"]) != 30:
                raise ValueError(f"{task}: outer cell count mismatch")
            if any(len(cell["inner_cells"]) != k * k for cell in panel["outer_cells"]):
                raise ValueError(f"{task}: inner cell count mismatch")
            for cell in panel["outer_cells"]:
                _verify_config_hash(cell, cell["outer_cell_id"])
                _verify_integrity(cell, cell["outer_cell_id"])
                _assert_cell(cell)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def write_canonical_json(value: Mapping[str, Any], path: str | Path) -> tuple[int, str]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    output.write_bytes(payload)
    return len(payload), sha256_bytes(payload)
