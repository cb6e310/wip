#!/usr/bin/env python3
"""Build the real ZuCo 2.0 nested inner-fold and J17 audit artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import h5py


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from build_zuco2_joint_split import panel_records  # noqa: E402
from data.inner_split import (  # noqa: E402
    DEFAULT_SEED,
    build_inner_artifacts,
    file_sha256,
    validate_inner_artifact,
    write_canonical_json,
)
from data.joint_split import build_joint_split, canonical_json_bytes, sha256_bytes  # noqa: E402
from data.zuco2_loader import (  # noqa: E402
    TASKS,
    dereference,
    indexed_value,
    iter_summary_files,
    validate_config,
)
from data.zuco2_source_join import prove_task_source_join, read_summary_contents  # noqa: E402
from protocol.semantic_items import config_hash as semantic_config_hash  # noqa: E402
from semantic_item_audit import (  # noqa: E402
    _load_is_real_word,
    _scan_word_group,
    _sentence_rawdata_status,
)


RUN_ID = "2026-08-14_017_v39_zuco2_inner_split"
METHOD = "ZuCo2-deterministic-outer-cell-inner-split"
FROZEN_OUTER_SHA256 = "20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6"
DEFAULT_DATASET_ROOT = Path("01_data_protocol/datasets/zuco_2.0")
DEFAULT_READER = DEFAULT_DATASET_ROOT / "scripts/python_reader/data_loading_helpers.py"
DEFAULT_OUTER = Path("01_data_protocol/splits/zuco_2_0_outer_folds.json")
DEFAULT_SUPPORT = Path("04_results/audits/semantic_item/zuco2_semantic_item_support.json")
DEFAULT_OUTPUT = Path("01_data_protocol/splits/zuco_2_0_inner_folds.json")
DEFAULT_AUDIT_OUTPUT = Path("04_results/audits/zuco2_inner_split_support.json")


def _relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"input path escapes project root: {path}") from exc


def _manifest_rows(paths: list[Path]) -> list[dict[str, object]]:
    unique = {path.resolve(): path for path in paths}
    rows = []
    for resolved in sorted(unique, key=lambda value: _relative(value)):
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        rows.append(
            {
                "path": _relative(resolved),
                "bytes": resolved.stat().st_size,
                "sha256": file_sha256(resolved),
            }
        )
    return rows


def build_semantic_manifest(
    dataset_root: Path,
    reader_path: Path,
    outer_path: Path,
    support_path: Path,
) -> dict[str, object]:
    if "roamm" in str(dataset_root).casefold() or "ds007629" in str(dataset_root).casefold():
        raise ValueError("ROAMM path is forbidden for the ZuCo-only inner split")
    dataset_paths: list[Path] = [reader_path]
    for task, task_spec in TASKS.items():
        summaries = [summary.path for summary in iter_summary_files(dataset_root, task)]
        materials = sorted((dataset_root / "task_materials").glob(task_spec["material_glob"]))
        if not summaries or not materials:
            raise FileNotFoundError(f"{task}: summary/material source files are incomplete")
        dataset_paths.extend(summaries)
        dataset_paths.extend(materials)
    source_code_paths = [
        SCRIPT_ROOT / "src/protocol/semantic_items.py",
        SCRIPT_ROOT / "scripts/semantic_item_audit.py",
        SCRIPT_ROOT / "src/data/zuco2_loader.py",
        SCRIPT_ROOT / "src/data/zuco2_source_join.py",
        SCRIPT_ROOT / "src/data/inner_split.py",
        SCRIPT_ROOT / "scripts/build_zuco2_inner_split.py",
    ]
    dataset_rows = _manifest_rows(dataset_paths)
    code_rows = _manifest_rows(source_code_paths)
    read_paths = sorted(
        {row["path"] for row in dataset_rows}
        | {row["path"] for row in code_rows}
        | {_relative(outer_path), _relative(support_path)}
    )
    if any("roamm" in path.casefold() or "ds007629" in path.casefold() for path in read_paths):
        raise ValueError("semantic/source manifest unexpectedly includes ROAMM")
    return {
        "semantic_config_hash": semantic_config_hash(),
        "semantic_source_manifest_hash": sha256_bytes(canonical_json_bytes(code_rows)),
        "official_reader_sha256": file_sha256(reader_path),
        "dataset_source_manifest_hash": sha256_bytes(canonical_json_bytes(dataset_rows)),
        "semantic_support_artifact_sha256": file_sha256(support_path),
        "source_code_files": code_rows,
        "dataset_source_files": dataset_rows,
        "read_paths": read_paths,
        "roamm_paths_read": [],
    }


def verify_outer_against_sources(
    outer: dict[str, object], dataset_root: Path, *, seed: int
) -> dict[str, str]:
    """Recreate each admitted panel in memory and require byte identity."""

    verified: dict[str, str] = {}
    for task in TASKS:
        records, _ = panel_records(dataset_root, task)
        rebuilt = build_joint_split(records, dataset="zuco_2_0", task=task, seed=seed)
        admitted = outer["panels"][task]
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(admitted):
            raise RuntimeError(f"STATE_SPEC_CONFLICT: {task} source records no longer match outer artifact")
        verified[task] = admitted["input"]["input_sha256"]
    return verified


def scan_positive_observations(
    dataset_root: Path,
    reader_path: Path,
    outer: dict[str, object],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Reuse the frozen semantic audit scanner and retain identity tuples only."""

    is_real_word = _load_is_real_word(reader_path)
    observations: list[dict[str, str]] = []
    task_counts: dict[str, int] = {}
    for task in TASKS:
        join_proof = prove_task_source_join(dataset_root, task)
        if not join_proof.verified:
            raise RuntimeError(f"{task} source-slot join is not verified: {join_proof.status}")
        slots = {slot.summary_index: slot.source_slot_key for slot in join_proof.slots}
        first = next(iter_summary_files(dataset_root, task), None)
        if first is None:
            raise FileNotFoundError(f"no summary file for {task}")
        canonical_contents = read_summary_contents(first.path)
        outer_records = {str(row["record_id"]): row for row in outer["panels"][task]["records"]}
        count_before = len(observations)
        for summary in iter_summary_files(dataset_root, task):
            if read_summary_contents(summary.path) != canonical_contents:
                raise RuntimeError(f"{task}/{summary.subject_id} summary sequence changed")
            with h5py.File(summary.path, "r") as handle:
                sentence_dataset = handle.get("sentenceData/content")
                shape = getattr(sentence_dataset, "shape", ())
                sentence_total = int(max(shape)) if shape else 0
                for sentence_zero in range(sentence_total):
                    sentence_index = sentence_zero + 1
                    source_slot = slots[sentence_index]
                    record_id = f"{summary.subject_id}|{source_slot}"
                    sentence_ref = indexed_value(handle["sentenceData/rawData"], sentence_zero)
                    sentence_valid, _ = _sentence_rawdata_status(handle, sentence_ref)
                    word_ref = indexed_value(handle["sentenceData/word"], sentence_zero)
                    word_group = dereference(handle, word_ref)
                    if not isinstance(word_group, h5py.Group):
                        continue
                    local_stats = {}
                    _scan_word_group(
                        handle,
                        task=task,
                        subject=summary.subject_id,
                        sentence_index=sentence_index,
                        source_slot=source_slot,
                        word_group=word_group,
                        sentence_valid=sentence_valid,
                        is_real_word=is_real_word,
                        stats=local_stats,
                        exclusions=[],
                        reason_counts=Counter(),
                    )
                    for item_id in sorted(local_stats):
                        item = local_stats[item_id]
                        if record_id not in outer_records:
                            raise RuntimeError(
                                f"positive observation record is absent from outer artifact: {record_id}"
                            )
                        identity = outer_records[record_id]
                        if str(identity["subject_id"]) != summary.subject_id or str(identity["stimulus_id"]) != source_slot:
                            raise RuntimeError(f"outer identity mismatch for {record_id}")
                        for _ in range(item.n_observations):
                            observations.append(
                                {
                                    "task": task,
                                    "record_id": record_id,
                                    "subject_id": summary.subject_id,
                                    "stimulus_id": source_slot,
                                    "item_id": item_id,
                                }
                            )
        task_counts[task] = len(observations) - count_before
    return observations, task_counts


def verify_support_artifact(
    support_path: Path,
    *,
    task_counts: dict[str, int],
) -> dict[str, int]:
    support = json.loads(support_path.read_text(encoding="utf-8"))
    if support.get("status") != "PASS" or support.get("dataset") != "zuco_2_0":
        raise RuntimeError("semantic support artifact is not an admitted ZuCo2 PASS")
    if support.get("config_hash") != semantic_config_hash():
        raise RuntimeError("semantic support artifact config hash mismatch")
    expected = {
        task: int(support["tasks"][task]["support"]["n_observations"])
        for task in TASKS
    }
    if task_counts != expected:
        raise RuntimeError(
            f"semantic positive observation counts changed: scan={task_counts} admitted={expected}"
        )
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--reader", type=Path, default=DEFAULT_READER)
    parser.add_argument("--outer", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--semantic-support", type=Path, default=DEFAULT_SUPPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--expected-outer-sha256", default=FROZEN_OUTER_SHA256)
    args = parser.parse_args()
    if args.seed != DEFAULT_SEED:
        parser.error(f"--seed is frozen to {DEFAULT_SEED}")
    started = time.perf_counter()
    validate_config(args.dataset_root)
    outer_sha = file_sha256(args.outer)
    if outer_sha != args.expected_outer_sha256:
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: outer SHA256 {outer_sha} != {args.expected_outer_sha256}"
        )
    outer = json.loads(args.outer.read_text(encoding="utf-8"))
    verified_input_hashes = verify_outer_against_sources(outer, args.dataset_root, seed=args.seed)
    observations, task_counts = scan_positive_observations(args.dataset_root, args.reader, outer)
    verify_support_artifact(args.semantic_support, task_counts=task_counts)
    manifest = build_semantic_manifest(
        args.dataset_root, args.reader, args.outer, args.semantic_support
    )
    artifact, audit = build_inner_artifacts(
        outer,
        observations,
        outer_file_sha256=outer_sha,
        expected_outer_file_sha256=args.expected_outer_sha256,
        semantic_manifest=manifest,
        seed=args.seed,
        run_id=RUN_ID,
    )
    errors = validate_inner_artifact(artifact)
    if errors:
        raise RuntimeError(f"inner artifact validation failed: {errors}")
    split_bytes, split_sha = write_canonical_json(artifact, args.output)
    audit_bytes, audit_sha = write_canonical_json(audit, args.audit_output)
    elapsed = time.perf_counter() - started
    decisions = {task: artifact["panels"][task]["decision"] for task in TASKS}
    inner_counts = {task: artifact["panels"][task]["inner_cell_count"] for task in TASKS}
    medians = [
        partition["median"]
        for task in TASKS
        for cell in audit["tasks"][task]["outer_cells"]
        for partition in cell["provisional_inner_partitions"]
    ]
    print("ZUCO2 INNER SPLIT SELF-CHECK")
    print(
        f"samples={{positive_observations: {len(observations)}, per_task: {task_counts}}} "
        f"shapes={{outer_cells: 60, inner_cells: {inner_counts}}}"
    )
    print(
        f"elapsed_seconds={elapsed:.3f} ranges={{provisional_item_median: "
        f"[{min(medians)},{max(medians)}], artifact_bytes: [{split_bytes},{audit_bytes}]}}"
    )
    print(f"seed={args.seed} fold={artifact['fold']} method={METHOD} config_hash={artifact['config_hash']}")
    print(f"outer_sha256={outer_sha} outer_input_hashes={verified_input_hashes}")
    print(
        f"semantic_config_hash={manifest['semantic_config_hash']} "
        f"semantic_source_manifest_hash={manifest['semantic_source_manifest_hash']} "
        f"dataset_source_manifest_hash={manifest['dataset_source_manifest_hash']}"
    )
    print(f"decisions={decisions}")
    print(f"split_sha256={split_sha} audit_sha256={audit_sha}")
    print(f"assertions={artifact['assertions']} status={artifact['status']}")
    print(f"outputs={[str(args.output), str(args.audit_output)]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
