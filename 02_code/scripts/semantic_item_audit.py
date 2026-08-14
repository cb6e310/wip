#!/usr/bin/env python3
"""Audit the v3.6 released lexical content-word item contract.

The ZuCo path reads only released word-level fields and the official reader's
``is_real_word`` function.  The TMNRED path intentionally stops when those
fields are absent: its sentence-level Chinese material is not tokenised here.
The script emits a compact JSON summary plus a deterministic, gzip-compressed
exclusion ledger.  It is an audit artifact, not a model result or a paper
admission decision.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

import h5py
import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "src" / "data"))

from protocol.semantic_items import (  # noqa: E402
    ItemStats,
    add_observation,
    config_dict,
    config_hash,
    decide_item,
    serialize_items,
    summarize_stats,
)
from zuco2_loader import (  # noqa: E402
    TASKS,
    decode_matlab_string,
    dereference,
    indexed_value,
    iter_summary_files,
    numeric_eeg_reference_status,
    validate_config,
)
from data.zuco2_source_join import prove_task_source_join, read_summary_contents  # noqa: E402


DEFAULT_RUN_ID = "2026-08-14_010_v36_stage0_recovery"
DEFAULT_SEED = 20260813


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sentence_rawdata_status(handle: h5py.File, value: object) -> tuple[bool, str]:
    valid, reason = numeric_eeg_reference_status(handle, value)
    return valid, "sentence_rawData_" + reason


def _fixation_status(handle: h5py.File, value: object) -> tuple[bool, str]:
    return numeric_eeg_reference_status(handle, value)


def _load_is_real_word(reader_path: Path) -> Callable[[str], object]:
    if not reader_path.is_file():
        raise FileNotFoundError(f"official reader not found: {reader_path}")
    spec = importlib.util.spec_from_file_location("zuco_release_reader", reader_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load official reader: {reader_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    predicate = getattr(module, "is_real_word", None)
    if not callable(predicate):
        raise AttributeError(f"official reader has no callable is_real_word: {reader_path}")
    return predicate


def _exclusion(
    *,
    task: str,
    subject: str,
    sentence_index: int,
    word_index: int | None,
    reason: str,
    raw_reference_type: str,
    source_slot: str | None = None,
    detail: str | None = None,
    fixation_index: int | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "dataset": "zuco_2_0",
        "task": TASKS[task]["label"],
        "subject": subject,
        "stimulus_source_slot": source_slot or f"summary_sentence_index:{sentence_index}",
        "reason": reason,
        "raw_reference_type": raw_reference_type,
        "sentence_index": sentence_index,
    }
    if word_index is not None:
        record["word_index"] = word_index
    if fixation_index is not None:
        record["fixation_index"] = fixation_index
    if detail is not None:
        record["detail"] = detail
    return record


def _scan_word_group(
    handle: h5py.File,
    *,
    task: str,
    subject: str,
    sentence_index: int,
    source_slot: str,
    word_group: h5py.Group,
    sentence_valid: bool,
    is_real_word: Callable[[str], object],
    stats: dict[str, ItemStats],
    exclusions: list[dict[str, object]],
    reason_counts: Counter[str],
) -> dict[str, int]:
    fields = set(str(name) for name in word_group.keys())
    content = word_group.get("content")
    raw_eeg = word_group.get("rawEEG")
    lengths = []
    for field in (content, raw_eeg):
        shape = getattr(field, "shape", None)
        if shape is not None:
            lengths.append(max(tuple(int(value) for value in shape)))
    word_count = max(lengths, default=0)
    local = Counter()
    if content is None:
        reason = "word_content_field_missing"
        reason_counts[reason] += word_count
        for word_index in range(word_count):
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="word.content",
                    source_slot=source_slot,
                )
            )
        return {"word_slots": word_count}
    for word_index in range(word_count):
        content_ref = indexed_value(content, word_index)
        raw = decode_matlab_string(handle, content_ref)
        if raw is None:
            reason = "word_content_missing_or_invalid_reference"
            reason_counts[reason] += 1
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="word.content",
                    source_slot=source_slot,
                )
            )
            continue
        try:
            decision = decide_item(
                raw,
                dataset="zuco_2_0",
                task=TASKS[task]["label"],
                is_real_word=is_real_word,
            )
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        if not decision.accepted:
            reason = decision.reason
            reason_counts[reason] += 1
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="official_reader.is_real_word",
                    source_slot=source_slot,
                )
            )
            continue

        # Inspect every fixation reference so malformed rows remain visible,
        # while one valid fixation is sufficient for a word observation.
        raw_ref = indexed_value(raw_eeg, word_index) if raw_eeg is not None else None
        container = dereference(handle, raw_ref)
        valid_fixations = 0
        fixation_total = 0
        if container is not None and hasattr(container, "shape"):
            values = np.asarray(container[...], dtype=object).reshape(-1)
            fixation_total = len(values)
            for fixation_index, fixation_ref in enumerate(values, start=1):
                valid, detail = _fixation_status(handle, fixation_ref)
                if valid:
                    valid_fixations += 1
                else:
                    reason = "word_rawEEG_fixation_malformed"
                    reason_counts[reason] += 1
                    exclusions.append(
                        _exclusion(
                            task=task,
                            subject=subject,
                            sentence_index=sentence_index,
                            word_index=word_index + 1,
                            fixation_index=fixation_index,
                            reason=reason,
                            raw_reference_type="word.rawEEG.fixation",
                            source_slot=source_slot,
                            detail=detail,
                        )
                    )
        elif raw_eeg is None or raw_ref is None or container is None:
            reason = "word_rawEEG_container_missing_or_invalid"
            reason_counts[reason] += 1
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="word.rawEEG",
                    source_slot=source_slot,
                )
            )
        if not sentence_valid:
            reason = "sentence_rawData_invalid_or_placeholder"
            reason_counts[reason] += 1
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="sentence.rawData",
                    source_slot=source_slot,
                )
            )
            continue
        if valid_fixations <= 0:
            reason = "word_has_no_parseable_fixation"
            reason_counts[reason] += 1
            exclusions.append(
                _exclusion(
                    task=task,
                    subject=subject,
                    sentence_index=sentence_index,
                    word_index=word_index + 1,
                    reason=reason,
                    raw_reference_type="word.rawEEG.fixation",
                    source_slot=source_slot,
                )
            )
            continue
        assert decision.item_id is not None
        add_observation(
            stats,
            decision,
            subject_id=subject,
            trial_id=f"{subject}|{source_slot}|word_index:{word_index + 1}",
        )
        local["accepted_observations"] += 1
        local["valid_fixations"] += valid_fixations
        local["fixation_rows"] += fixation_total
    local["word_slots"] = word_count
    return dict(local)


def audit_zuco(dataset_root: Path, reader_path: Path, *, exclusions_path: Path) -> dict[str, object]:
    is_real_word = _load_is_real_word(reader_path)
    tasks: dict[str, object] = {}
    all_exclusions: list[dict[str, object]] = []
    for task in TASKS:
        join_proof = prove_task_source_join(dataset_root, task)
        if not join_proof.verified:
            raise RuntimeError(
                f"{task} source-slot join is not verified: {join_proof.status}; "
                "material identity must not be guessed"
            )
        source_slots = {slot.summary_index: slot.source_slot_key for slot in join_proof.slots}
        first_summary = next(iter_summary_files(dataset_root, task), None)
        if first_summary is None:
            raise FileNotFoundError(f"no summary files for {task}")
        canonical_contents = read_summary_contents(first_summary.path)
        stats: dict[str, ItemStats] = {}
        exclusions: list[dict[str, object]] = []
        reason_counts: Counter[str] = Counter()
        subject_ids: list[str] = []
        per_subject: dict[str, object] = {}
        for summary in iter_summary_files(dataset_root, task):
            if read_summary_contents(summary.path) != canonical_contents:
                raise RuntimeError(
                    f"{task}/{summary.subject_id} summary sequence disagrees with the verified source join"
                )
            subject_ids.append(summary.subject_id)
            started_subject = time.perf_counter()
            accepted = 0
            sentence_valid_count = 0
            sentence_total = 0
            word_slots = 0
            with h5py.File(summary.path, "r") as handle:
                # Avoid relying on a private field: the content vector defines
                # the sentence count in the released loader.
                sentence_dataset = handle.get("sentenceData/content")
                shape = getattr(sentence_dataset, "shape", ())
                sentence_total = int(max(shape)) if shape else 0
                for sentence_zero in range(sentence_total):
                    sentence_index = sentence_zero + 1
                    source_slot = source_slots[sentence_index]
                    sentence_ref = indexed_value(handle["sentenceData/rawData"], sentence_zero)
                    sentence_valid, sentence_reason = _sentence_rawdata_status(handle, sentence_ref)
                    sentence_valid_count += int(sentence_valid)
                    if not sentence_valid:
                        reason_counts[sentence_reason] += 1
                        exclusions.append(
                            _exclusion(
                                task=task,
                                subject=summary.subject_id,
                                sentence_index=sentence_index,
                                word_index=None,
                                reason=sentence_reason,
                                raw_reference_type="sentence.rawData",
                                source_slot=source_slot,
                            )
                        )
                    word_ref = indexed_value(handle["sentenceData/word"], sentence_zero)
                    word_group = dereference(handle, word_ref)
                    if not isinstance(word_group, h5py.Group):
                        reason = "word_group_missing_or_invalid_reference"
                        reason_counts[reason] += 1
                        exclusions.append(
                            _exclusion(
                                task=task,
                                subject=summary.subject_id,
                                sentence_index=sentence_index,
                                word_index=None,
                                reason=reason,
                                raw_reference_type="sentence.word",
                                source_slot=source_slot,
                            )
                        )
                        continue
                    local = _scan_word_group(
                        handle,
                        task=task,
                        subject=summary.subject_id,
                        sentence_index=sentence_index,
                        source_slot=source_slot,
                        word_group=word_group,
                        sentence_valid=sentence_valid,
                        is_real_word=is_real_word,
                        stats=stats,
                        exclusions=exclusions,
                        reason_counts=reason_counts,
                    )
                    word_slots += int(local.get("word_slots", 0))
                    accepted += int(local.get("accepted_observations", 0))
            per_subject[summary.subject_id] = {
                "sentence_count": sentence_total,
                "sentence_rawData_valid": sentence_valid_count,
                "word_slots": word_slots,
                "accepted_observations": accepted,
                "elapsed_seconds": round(time.perf_counter() - started_subject, 3),
            }
        support = summarize_stats(stats, subject_ids=subject_ids)
        support_pass = support["support_redline_status"] == "PASS"
        all_exclusions.extend(exclusions)
        tasks[task] = {
            "label": TASKS[task]["label"],
            "status": "PASS" if support_pass else "NO_GO_LOW_SUPPORT",
            "paper_eligible": bool(join_proof.verified and support_pass),
            "trial_id_type": "verified_source_slot_key",
            "material_join": join_proof.to_dict(include_slots=False),
            "subjects": sorted(subject_ids),
            "per_subject": per_subject,
            "support": support,
            "items": serialize_items(stats),
            "exclusion_reason_counts": dict(sorted(reason_counts.items())),
        }
    exclusions_path.parent.mkdir(parents=True, exist_ok=True)
    with exclusions_path.open("wb") as raw_handle:
        with gzip.GzipFile(fileobj=raw_handle, mode="wb", filename="", mtime=0) as handle:
            for record in all_exclusions:
                line = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
                handle.write(line.encode("utf-8"))
    return {
        "dataset": "zuco_2_0",
        "status": "PASS" if all(bool(item["paper_eligible"]) for item in tasks.values()) else "NO_GO_LOW_SUPPORT",
        "paper_eligible": all(bool(item["paper_eligible"]) for item in tasks.values()),
        "definition": config_dict(),
        "config_hash": config_hash(),
        "official_reader": str(reader_path),
        "tasks": tasks,
        "exclusions": {
            "path": str(exclusions_path),
            "sha256": _sha256(exclusions_path),
            "record_count": len(all_exclusions),
        },
    }


def audit_tmnred(dataset_root: Path) -> dict[str, object]:
    """Refuse sentence-level retokenization when released word fields are absent."""

    material = dataset_root / "derivatives" / "source material" / "source material_ses.csv"
    return {
        "dataset": "TMNRED",
        "status": "BLOCKED_MISSING_RELEASED_WORD_LEVEL_CONTENT",
        "paper_eligible": False,
        "definition": config_dict(),
        "config_hash": config_hash(),
        "blocking_facts": [
            "TMNRED snapshot exposes sentence-level Chinese material only; no released word-level content field.",
            "No official is_real_word predicate is present in the dataset release.",
            "This audit does not tokenize, stem, translate, or infer lexical items from sentence text.",
        ],
        "material_path": str(material),
        "material_present": material.is_file(),
        "support": {
            "item_count": 0,
            "supported_item_count": 0,
            "supported_item_rate": None,
            "support_redline_status": "BLOCKED_NO_LEDGER",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("zuco2", "tmnred"), required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--reader", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclusions-output", type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--fold", default="stage0_global_diagnostic")
    parser.add_argument("--method", default="semantic_item_support_audit")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.dataset == "zuco2":
        validate_config(args.dataset_root)
        reader = args.reader or (args.dataset_root / "scripts/python_reader/data_loading_helpers.py")
        exclusions_path = args.exclusions_output or args.output.with_suffix(".exclusions.jsonl.gz")
        result = audit_zuco(args.dataset_root, reader, exclusions_path=exclusions_path)
    else:
        result = audit_tmnred(args.dataset_root)
    result.update(
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "seed": args.seed,
            "fold": args.fold,
            "method": args.method,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    )
    result["assertions"] = {
        "frozen_normalization": result["definition"]["normalization"] == "NFKC|strip|casefold",
        "official_predicate_required": result["definition"]["official_predicate"] == "required_release_reader_is_real_word",
        "no_sentence_retokenization": result["definition"]["no_sentence_retokenization"],
        "status_is_explicit": result["status"] in {
            "PASS",
            "NO_GO_LOW_SUPPORT",
            "BLOCKED_MISSING_RELEASED_WORD_LEVEL_CONTENT",
        },
    }
    result["status"] = result["status"] if all(result["assertions"].values()) else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    observations = 0
    items = 0
    if args.dataset == "zuco2":
        observations = sum(int(task["support"]["n_observations"]) for task in result["tasks"].values())
        items = sum(int(task["support"]["item_count"]) for task in result["tasks"].values())
    print("SEMANTIC ITEM AUDIT")
    print(f"samples={{observations: {observations}, items: {items}}}")
    print(f"shapes={{tasks: {len(result.get('tasks', {}))}, exclusions: {result.get('exclusions', {}).get('record_count', 0)}}}")
    print(f"elapsed_seconds={result['elapsed_seconds']} ranges={{config_hash: {result['config_hash']}}}")
    print(f"seed={args.seed} fold={args.fold} method={args.method} config_hash={result['config_hash']}")
    print(f"assertions={result['assertions']} status={result['status']}")
    print(f"output={args.output}")
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
