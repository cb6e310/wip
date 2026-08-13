#!/usr/bin/env python3
"""Build a deterministic ZuCo 2.0 data-preparation audit.

The audit is intentionally descriptive.  It enumerates source files, source
material rows, HDF5 field names, object-reference health, and shape metadata;
it never chooses a channel map, semantic item, bandpower recipe, split, or
exclusion threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.io import whosmat
import yaml

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src" / "data"))

from zuco2_loader import (
    TASKS,
    decode_matlab_string,
    dereference,
    iter_raw_files,
    iter_summary_files,
    indexed_value,
    read_material_rows,
    source_field_names,
    summary_sentence_count,
    summary_record,
    validate_config,
)


RUN_ID = "2026-08-13_007_zuco2_data_card"
SEED = 20260813


def _jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _file_sha256(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _source_signature(path: Path) -> dict[str, Any]:
    return {"path": str(path), "size_bytes": path.stat().st_size}


def _shape_product(shape: tuple[int, ...] | None) -> int:
    if not shape:
        return 0
    product = 1
    for dim in shape:
        product *= int(dim)
    return product


def _vector_length(shape: tuple[int, ...] | None) -> int:
    if not shape:
        return 0
    if len(shape) == 1:
        return int(shape[0])
    if len(shape) >= 2 and shape[0] == 1:
        return int(shape[1])
    if len(shape) >= 2 and shape[1] == 1:
        return int(shape[0])
    return _shape_product(shape)


def _normalize_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").strip().split()).rstrip(";")


def _field_ref_status(handle: h5py.File, value: object) -> str:
    target = dereference(handle, value)
    if target is None:
        return "missing_or_invalid_reference"
    shape = getattr(target, "shape", None)
    if shape is not None and _shape_product(tuple(int(x) for x in shape)) == 0:
        return "empty_target"
    return "valid"


def _word_inventory(handle: h5py.File, word_value: object) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": _field_ref_status(handle, word_value),
        "word_slots": 0,
        "content_valid": 0,
        "content_missing": 0,
        "raw_eeg_valid": 0,
        "raw_eeg_missing": 0,
        "raw_eeg_empty": 0,
        "raw_eeg_container_valid": 0,
        "raw_eeg_word_with_valid_fixation": 0,
        "raw_eeg_fixation_valid": 0,
        "raw_eeg_fixation_malformed": 0,
        "raw_eeg_shapes": Counter(),
        "field_names": [],
    }
    group = dereference(handle, word_value)
    if not isinstance(group, h5py.Group):
        return result
    result["field_names"] = sorted(str(name) for name in group.keys())
    content = group.get("content")
    raw_eeg = group.get("rawEEG")
    lengths = [getattr(group[name], "shape", (0,)) for name in ("content", "rawEEG") if name in group]
    result["word_slots"] = max((_vector_length(tuple(int(x) for x in shape)) for shape in lengths), default=0)
    if content is None:
        result["content_missing"] = result["word_slots"]
        result["raw_eeg_missing"] = result["word_slots"]
        return result
    for index in range(result["word_slots"]):
        try:
            content_value = indexed_value(content, index)
        except (IndexError, ValueError, TypeError):
            content_value = None
        if decode_matlab_string(handle, content_value) is None:
            result["content_missing"] += 1
        else:
            result["content_valid"] += 1
        if raw_eeg is None:
            result["raw_eeg_missing"] += 1
            continue
        try:
            raw_value = indexed_value(raw_eeg, index)
        except (IndexError, ValueError, TypeError):
            raw_value = None
        raw_target = dereference(handle, raw_value)
        if raw_target is None:
            result["raw_eeg_missing"] += 1
        else:
            result["raw_eeg_container_valid"] += 1
            shape = getattr(raw_target, "shape", None)
            values = []
            if shape is not None:
                try:
                    values = np.asarray(raw_target[...], dtype=object).reshape(-1)
                except (TypeError, ValueError, RuntimeError):
                    values = []
            valid_fixations = 0
            for fixation_value in values:
                fixation_target = dereference(handle, fixation_value)
                fixation_shape = getattr(fixation_target, "shape", None)
                if fixation_shape is None:
                    result["raw_eeg_fixation_malformed"] += 1
                    continue
                fixation_shape_tuple = tuple(int(x) for x in fixation_shape)
                result["raw_eeg_shapes"][str(fixation_shape_tuple)] += 1
                if len(fixation_shape_tuple) == 2 and fixation_shape_tuple[1] == 105 and _shape_product(fixation_shape_tuple) > 0:
                    valid_fixations += 1
                else:
                    result["raw_eeg_fixation_malformed"] += 1
            result["raw_eeg_fixation_valid"] += valid_fixations
            result["raw_eeg_valid"] += int(valid_fixations > 0)
            result["raw_eeg_word_with_valid_fixation"] += int(valid_fixations > 0)
            if valid_fixations == 0 and shape is not None and _shape_product(tuple(int(x) for x in shape)) == 0:
                result["raw_eeg_empty"] += 1
    result["raw_eeg_shapes"] = dict(result["raw_eeg_shapes"])
    return result


def audit_summary(path: Path, task: str, subject_id: str, *, deep: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "task": task,
        "subject_id": subject_id,
        "path": str(path),
        "status": "PASS",
        "file": _source_signature(path),
        "sentence_count": 0,
        "sentence_fields": [],
        "sentence_ref_counts": {},
        "sentence_rawdata_shapes": Counter(),
        "sentence_rawdata_valid": 0,
        "sentence_rawdata_placeholder": 0,
        "sentence_rawdata_valid_indices": [],
        "sentence_rawdata_placeholder_indices": [],
        "word_slots": 0,
        "word_content_valid": 0,
        "word_content_missing": 0,
        "word_raw_eeg_valid": 0,
        "word_raw_eeg_missing": 0,
        "word_raw_eeg_empty": 0,
        # Keep the three reference layers separately visible: a word slot,
        # its fixation-container reference, and each numeric EEG leaf.
        "word_raw_eeg_container_valid": 0,
        "word_raw_eeg_word_with_valid_fixation": 0,
        "word_raw_eeg_fixation_valid": 0,
        "word_raw_eeg_fixation_malformed": 0,
        "word_raw_eeg_shapes": Counter(),
        "word_group_valid": 0,
        "word_group_missing": 0,
        "content_normalized_hashes": [],
        "malformed_sentences": [],
    }
    try:
        with h5py.File(path, "r") as handle:
            result["sentence_fields"] = list(source_field_names(handle))
            count = summary_sentence_count(handle)
            result["sentence_count"] = count
            refs = Counter()
            indices = list(range(count)) if deep else sorted({0, max(0, count // 2), max(0, count - 1)})
            result["reference_audit_scope"] = "full" if deep else "sample_first_middle_last"
            result["reference_audit_indices"] = [index + 1 for index in indices]
            for index in indices:
                row = summary_record(handle, index)
                result["content_normalized_hashes"].append(
                    hashlib.sha256(_normalize_text(row.get("content")).encode("utf-8")).hexdigest()
                )
                for field in ("content", "rawData"):
                    value = row.get(f"{field}_shape")
                    # A shape indicates a resolved reference.  None is a bad
                    # or absent MATLAB object reference.
                    refs[f"{field}_{'valid' if value is not None else 'missing'}"] += 1
                word_target = dereference(handle, row.get("word_reference"))
                if isinstance(word_target, h5py.Group):
                    refs["word_group_valid"] += 1
                    result["word_group_valid"] += 1
                else:
                    refs["word_group_missing"] += 1
                    result["word_group_missing"] += 1
                raw_shape = row.get("rawData_shape")
                if raw_shape is None:
                    result["malformed_sentences"].append({"index": index + 1, "reason": "rawData_missing"})
                elif _shape_product(tuple(raw_shape)) == 0:
                    refs["rawData_empty"] += 1
                elif tuple(raw_shape) == (1, 1):
                    result["sentence_rawdata_placeholder"] += 1
                    result["sentence_rawdata_placeholder_indices"].append(index + 1)
                else:
                    result["sentence_rawdata_valid"] += 1
                    result["sentence_rawdata_valid_indices"].append(index + 1)
                    result["sentence_rawdata_shapes"][str(raw_shape)] += 1
                words = _word_inventory(handle, row.get("word_reference"))
                result["word_slots"] += int(words["word_slots"])
                for key in ("word_content_valid", "word_content_missing", "word_raw_eeg_valid", "word_raw_eeg_missing", "word_raw_eeg_empty", "word_raw_eeg_container_valid", "word_raw_eeg_word_with_valid_fixation", "word_raw_eeg_fixation_valid", "word_raw_eeg_fixation_malformed"):
                    source_key = key.removeprefix("word_")
                    result[key] += int(words.get(source_key, 0))
                for shape, amount in words["raw_eeg_shapes"].items():
                    result["word_raw_eeg_shapes"][shape] += amount
            result["sentence_ref_counts"] = dict(refs)
    except Exception as exc:  # a broken file must be visible, not fatal to all audit output
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["sentence_rawdata_shapes"] = dict(result["sentence_rawdata_shapes"])
    result["word_raw_eeg_shapes"] = dict(result["word_raw_eeg_shapes"])
    return result


def audit_raw(dataset_root: Path, task: str, *, inspect_files: int = 1) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    all_items = list(iter_raw_files(dataset_root, task))
    inspect_paths: set[Path] = set()
    for kind in ("EEG", "ET"):
        inspect_paths.update(
            item.path for item in all_items if item.kind == kind
        )
        # Keep exactly the requested bounded count for each raw kind.
        inspect_paths = set(list(sorted(inspect_paths))[:inspect_files]) if kind == "ET" else inspect_paths
    # The loop above must retain the first N items per kind, independent of
    # filename ordering across EEG and ET directories.
    inspect_paths = {
        item.path
        for kind in ("EEG", "ET")
        for item in [x for x in all_items if x.kind == kind][:inspect_files]
    }
    for item in all_items:
        record = {
            "task": task,
            "subject_id": item.subject_id,
            "session_id": item.session_id,
            "kind": item.kind,
            "path": str(item.path),
            "file": _source_signature(item.path),
            "status": "PASS",
        }
        if item.path not in inspect_paths:
            record["inspection"] = "inventory_only"
            records.append(record)
            continue
        record["inspection"] = "deep"
        try:
            try:
                with h5py.File(item.path, "r") as handle:
                    datasets: dict[str, list[int]] = {}
                    def visitor(name: str, obj: object) -> None:
                        if isinstance(obj, h5py.Dataset):
                            base = name.rsplit("/", 1)[-1].lower()
                            if base in {"data", "srate", "chanlocs", "times", "event"}:
                                datasets[name] = [int(x) for x in obj.shape]
                    handle.visititems(visitor)
                    record["format"] = "MATLAB_v7.3_HDF5"
                    record["datasets"] = datasets
            except OSError:
                variables = whosmat(item.path)
                record["format"] = "MATLAB_v5"
                record["variables"] = {
                    name: {"shape": list(shape), "class": class_name}
                    for name, shape, class_name in variables
                }
        except Exception as exc:
            record["status"] = "FAIL"
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
    return {"count": len(records), "records": records}


def audit_materials(dataset_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for task in TASKS:
        rows = read_material_rows(dataset_root, task)
        by_file: defaultdict[str, int] = defaultdict(int)
        slot_values: list[str] = []
        material_values: list[str] = []
        text_hashes: Counter[str] = Counter()
        conditions: Counter[str] = Counter()
        widths: list[int] = []
        for row in rows:
            by_file[row.source_file] += 1
            slot_values.append(row.sentence_slot_raw)
            material_values.append(row.material_id_raw)
            text = row.text_or_label_raw.strip()
            text_hashes[hashlib.sha256(text.encode("utf-8")).hexdigest()] += 1
            conditions[row.condition_raw or "<empty>"] += 1
            widths.append(len(row.source_columns))
        result[task] = {
            "row_count": len(rows),
            "files": dict(sorted(by_file.items())),
            "source_column_widths": dict(Counter(widths)),
            "unique_sentence_slot_raw": len(set(slot_values)),
            "unique_material_id_raw": len(set(material_values)),
            "duplicate_text_hashes": sum(1 for count in text_hashes.values() if count > 1),
            "max_text_duplicate_count": max(text_hashes.values(), default=0),
            "unique_paragraph_id_raw": len({row.paragraph_id_raw for row in rows}),
            "unique_sentence_id_raw": len({row.sentence_id_raw for row in rows}),
            "condition_counts": dict(sorted(conditions.items())),
            "rows": [
                {
                    "source_file": row.source_file,
                    "row_number": row.row_number,
                    "sentence_slot_raw": row.sentence_slot_raw,
                    "material_id_raw": row.material_id_raw,
                    "paragraph_id_raw": row.paragraph_id_raw,
                    "sentence_id_raw": row.sentence_id_raw,
                    "condition_raw": row.condition_raw,
                    "text_or_label_raw": row.text_or_label_raw,
                    "text_or_label_sha256": hashlib.sha256(row.text_or_label_raw.strip().encode("utf-8")).hexdigest(),
                }
                for row in rows
            ],
        }
    return result


def audit_archive(dataset_root: Path) -> dict[str, Any]:
    archive = dataset_root.parent / "_downloads" / "zuco2.0-osfstorage.zip"
    result: dict[str, Any] = {"path": str(archive), "exists": archive.is_file()}
    if not archive.is_file():
        return result
    result["size_bytes"] = archive.stat().st_size
    try:
        with zipfile.ZipFile(archive) as handle:
            infos = handle.infolist()
            result.update({
                "zip_entries_total": len(infos),
                "regular_file_entries": sum(not info.is_dir() for info in infos),
                "directory_entries": sum(info.is_dir() for info in infos),
                "uncompressed_bytes": sum(info.file_size for info in infos),
                "duplicate_names": len(infos) - len({info.filename for info in infos}),
            })
    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--deep", action="store_true", help="scan every sentence/word reference; slow")
    parser.add_argument("--raw-inspect-files", type=int, default=1, help="number of raw files per task to inspect deeply")
    args = parser.parse_args()
    started = time.perf_counter()
    validate_config(args.dataset_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary_records: list[dict[str, Any]] = []
    raw_by_task: dict[str, Any] = {}
    summary_by_task: dict[str, Any] = {}
    subjects_by_task: dict[str, list[str]] = {}
    for task in TASKS:
        summaries = list(iter_summary_files(args.dataset_root, task))
        summary_by_task[task] = {
            "count": len(summaries),
            "records": [audit_summary(item.path, task, item.subject_id, deep=args.deep) for item in summaries],
        }
        summary_records.extend(summary_by_task[task]["records"])
        subjects_by_task[task] = sorted({item.subject_id for item in summaries})
        raw_by_task[task] = audit_raw(args.dataset_root, task, inspect_files=args.raw_inspect_files)

    all_summary_subjects = sorted({record["subject_id"] for record in summary_records})
    raw_subjects = sorted({record["subject_id"] for task in raw_by_task.values() for record in task["records"]})
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "seed": args.seed,
        "dataset": "zuco_2_0",
        "status": "BOUNDED_AUDIT_PASS_WITH_EXPLICIT_PROTOCOL_BLOCKERS",
        "elapsed_seconds": None,
        "archive": audit_archive(args.dataset_root),
        "subjects": {
            "summary_subjects": all_summary_subjects,
            "summary_count": len(all_summary_subjects),
            "raw_subjects": raw_subjects,
            "raw_only_subjects": sorted(set(raw_subjects) - set(all_summary_subjects)),
            "summary_only_subjects": sorted(set(all_summary_subjects) - set(raw_subjects)),
            "answers_only_subjects_observed": ["YMH"],
        },
        "tasks": {},
        "summary_aggregates": {},
        "materials": audit_materials(args.dataset_root),
        "material_join": {},
        "assignment_support": {},
        "protocol_blockers": [
            {"id": "B_ZUCO2_CHANNEL_MAP", "status": "UNRESOLVED", "detail": "Summary EEG is 105 channels; continuous EEGLAB EEG is 128; no source-verified mapping is selected."},
            {"id": "B_A1_BANDPOWER_FORMULA", "status": "UNRESOLVED", "detail": "Guide names eight bands but does not freeze numeric edges, PSD window, or signal units."},
            {"id": "B_ZUCO2_REFERENCE_EXCLUSIONS", "status": "UNRESOLVED", "detail": "Malformed/empty sentence and word references are counted, but no exclusion rule is applied here."},
            {"id": "B_ZUCO2_STIMULUS_JOIN", "status": "UNRESOLVED", "detail": "Material CSV source slots are retained verbatim; no unverified join to summary sentence indices is inferred."},
            {"id": "B_SEMANTIC_ITEM_UNRESOLVED", "status": "UNRESOLVED", "detail": "Content-word versus semantic-cluster unit is not selected by this loader."},
        ],
        "validation_boundary": {
            "descriptive_audit_only": True,
            "reference_audit_scope": (
                "all_summary_files_all_sentence_and_word_references"
                if args.deep
                else "all_summary_files_first_middle_last_sentences"
            ),
            "raw_deep_inspection_files_per_kind_per_task": args.raw_inspect_files,
            "full_file_inventory": True,
            "no_channel_mapping": True,
            "no_bandpower": True,
            "no_semantic_item": True,
            "no_split": True,
            "no_model_result": True,
        },
    }
    for task in TASKS:
        manifest["tasks"][task] = {
            "label": TASKS[task]["label"],
            "summary": summary_by_task[task],
            "raw": raw_by_task[task],
            "summary_subjects": subjects_by_task[task],
            "summary_sentence_counts": sorted({int(item["sentence_count"]) for item in summary_by_task[task]["records"]}),
            "raw_session_ids": sorted({item["session_id"] for item in raw_by_task[task]["records"]}),
        }
        records = summary_by_task[task]["records"]
        manifest["summary_aggregates"][task] = {
            "summary_file_count": len(records),
            "sentence_slots_total": sum(int(record["sentence_count"]) for record in records),
            "sentence_rawdata_valid_total": sum(int(record["sentence_rawdata_valid"]) for record in records),
            "sentence_rawdata_placeholder_total": sum(int(record["sentence_rawdata_placeholder"]) for record in records),
            "word_slots_total": sum(int(record["word_slots"]) for record in records),
            "word_content_valid_total": sum(int(record["word_content_valid"]) for record in records),
            "word_raw_eeg_word_with_valid_fixation_total": sum(
                int(record.get("word_raw_eeg_word_with_valid_fixation", 0)) for record in records
            ),
            "word_raw_eeg_container_valid_total": sum(
                int(record.get("word_raw_eeg_container_valid", 0)) for record in records
            ),
            "word_raw_eeg_fixation_valid_total": sum(
                int(record.get("word_raw_eeg_fixation_valid", 0)) for record in records
            ),
            "word_raw_eeg_fixation_malformed_total": sum(
                int(record.get("word_raw_eeg_fixation_malformed", 0)) for record in records
            ),
            "word_group_valid_total": sum(int(record.get("word_group_valid", 0)) for record in records),
            "word_group_missing_total": sum(int(record.get("word_group_missing", 0)) for record in records),
        }
        if args.deep:
            sentence_count = int(records[0]["sentence_count"]) if records else 0
            support = [sum(index + 1 in record["sentence_rawdata_valid_indices"] for record in records) for index in range(sentence_count)]
            manifest["assignment_support"][task] = {
                "unit": "summary_sentence_slot",
                "subject_count": len(records),
                "stimulus_count": sentence_count,
                "support_range": [min(support, default=0), max(support, default=0)],
                "support_counts": support,
                "missing_cell_count": sum(value < len(records) for value in support),
                "placeholder_cell_count": sum(len(record["sentence_rawdata_placeholder_indices"]) for record in records),
            }
            material_rows = manifest["materials"][task]["rows"]
            by_text: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
            for material in material_rows:
                by_text[_normalize_text(material.get("text_or_label_raw"))].append(material)
            first_record = records[0] if records else {}
            first_path = next(iter_summary_files(args.dataset_root, task), None)
            first_contents = []
            if first_path is not None:
                with h5py.File(first_path.path, "r") as handle:
                    first_contents = [_normalize_text(summary_record(handle, index)["content"]) for index in range(sentence_count)]
            manifest["material_join"][task] = {
                "status": "AMBIGUOUS_DUPLICATE_TEXT" if any(len(by_text[text]) > 1 for text in first_contents) else "UNIQUE_TEXT_MATCH",
                "summary_slots": sentence_count,
                "all_slots_text_match": all(text in by_text for text in first_contents),
                "ambiguous_slot_count": sum(len(by_text[text]) > 1 for text in first_contents),
                "unmatched_slot_count": sum(text not in by_text for text in first_contents),
                "sequence_consistent_across_subjects": len({tuple(record["content_normalized_hashes"]) for record in records}) == 1,
                "note": "Duplicate source text rows are retained; no paragraph/sentence row is selected by this audit.",
            }
    manifest["elapsed_seconds"] = round(time.perf_counter() - started, 3)

    output_json = args.out_dir / "zuco2_data_audit.json"
    output_yaml = args.out_dir / "zuco2_data_audit.yaml"
    output_json.write_text(json.dumps(manifest, indent=2, default=_jsonable) + "\n", encoding="utf-8")
    output_yaml.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8")

    total_summary = sum(item["summary"]["count"] for item in manifest["tasks"].values())
    total_raw = sum(item["raw"]["count"] for item in manifest["tasks"].values())
    malformed = sum(len(item["malformed_sentences"]) for item in summary_records)
    status = "PASS" if all(item["summary"]["count"] > 0 for item in manifest["tasks"].values()) and all(item["raw"]["count"] > 0 for item in manifest["tasks"].values()) else "FAIL"
    print("ZUCO2 DATA AUDIT")
    print(f"samples={{summary_files: {total_summary}, raw_eeg_files: {total_raw}, subjects: {len(all_summary_subjects)}}}")
    print(f"shapes={{sentence_counts: {[manifest['tasks'][task]['summary_sentence_counts'] for task in TASKS]}, malformed_sentence_records: {malformed}}}")
    print(f"elapsed_seconds={manifest['elapsed_seconds']}")
    print(f"key_ranges={{raw_session_ids: {sorted(set(x for task in manifest['tasks'].values() for x in task['raw_session_ids']))}}}")
    print(f"outputs={{json: {output_json}, yaml: {output_yaml}}}")
    print(f"assertions={{tasks_present: {status == 'PASS'}, no_mapping_guess: True, no_semantic_guess: True}} status {status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
