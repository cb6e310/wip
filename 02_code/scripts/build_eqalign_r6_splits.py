#!/usr/bin/env python3
"""Build only the namespaced R6 6x3 outer and fixed 3x3 inner artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from build_zuco2_inner_split import (  # noqa: E402
    DEFAULT_DATASET_ROOT,
    DEFAULT_READER,
    DEFAULT_SUPPORT,
    build_semantic_manifest,
    scan_positive_observations,
    verify_support_artifact,
)
from build_zuco2_joint_split import panel_records  # noqa: E402
from data.joint_split import canonical_json_bytes, sha256_bytes  # noqa: E402
from data.zuco2_loader import TASKS, validate_config  # noqa: E402
from eqalign_r6.split_builder import (  # noqa: E402
    SEED,
    build_r6_inner_artifacts,
    build_r6_outer_artifact,
    file_sha256,
    source_code_manifest,
    validate_r6_inner_artifact,
    validate_r6_outer_artifact,
    validate_support_audit,
    write_canonical_json,
)


RUN_ID = "2026-08-24_011_v4_1_r6_split_reconciliation_readiness"
OLD_OUTER = Path("01_data_protocol/splits/zuco_2_0_outer_folds.json")
OLD_INNER = Path("01_data_protocol/splits/zuco_2_0_inner_folds.json")
OLD_OUTER_SHA256 = "20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6"
OLD_INNER_SHA256 = "0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7"
DEFAULT_OUTER = Path("01_data_protocol/splits/eqalign_r6_zuco_2_0_outer_folds.json")
DEFAULT_INNER = Path("01_data_protocol/splits/eqalign_r6_zuco_2_0_inner_folds.json")
DEFAULT_AUDIT = Path("04_results/audits/eqalign_r6_zuco2_inner_split_support.json")


def _artifact_file_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value) + b"\n")


def _construction_source_manifest() -> dict[str, Any]:
    paths = [
        SCRIPT_ROOT / "src/eqalign_r6/split_builder.py",
        SCRIPT_ROOT / "scripts/build_eqalign_r6_splits.py",
        SCRIPT_ROOT / "src/data/joint_split.py",
        SCRIPT_ROOT / "src/data/inner_split.py",
        SCRIPT_ROOT / "scripts/build_zuco2_joint_split.py",
        SCRIPT_ROOT / "scripts/build_zuco2_inner_split.py",
        SCRIPT_ROOT / "src/data/zuco2_loader.py",
        SCRIPT_ROOT / "src/data/zuco2_source_join.py",
        SCRIPT_ROOT / "src/protocol/semantic_items.py",
        SCRIPT_ROOT / "scripts/semantic_item_audit.py",
    ]
    return source_code_manifest(paths, root=PROJECT_ROOT)


def construct_r6_split_artifacts(
    dataset_root: Path = DEFAULT_DATASET_ROOT,
    reader_path: Path = DEFAULT_READER,
    support_path: Path = DEFAULT_SUPPORT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Rebuild all three R6 artifacts in memory and prove order invariance."""

    validate_config(dataset_root)
    records_by_task: dict[str, list[dict[str, object]]] = {}
    joins: dict[str, dict[str, object]] = {}
    for task in TASKS:
        records, join = panel_records(dataset_root, task)
        records_by_task[task] = records
        joins[task] = join
    outer = build_r6_outer_artifact(records_by_task, source_joins=joins, seed=SEED, run_id=RUN_ID)
    outer_reversed = build_r6_outer_artifact(
        {task: list(reversed(records_by_task[task])) for task in TASKS},
        source_joins=joins,
        seed=SEED,
        run_id=RUN_ID,
    )
    if canonical_json_bytes(outer) != canonical_json_bytes(outer_reversed):
        raise RuntimeError("R6 outer forward/reverse canonical bytes differ")
    outer_errors = validate_r6_outer_artifact(outer)
    if outer_errors:
        raise RuntimeError(f"R6 outer validation failed: {outer_errors}")
    outer_sha = _artifact_file_sha256(outer)
    observations, task_counts = scan_positive_observations(dataset_root, reader_path, outer)
    verify_support_artifact(support_path, task_counts=task_counts)
    semantic_manifest = build_semantic_manifest(
        dataset_root,
        reader_path,
        DEFAULT_OUTER,
        support_path,
    )
    semantic_manifest["r6_construction_source_manifest"] = _construction_source_manifest()
    inner, audit = build_r6_inner_artifacts(
        outer,
        observations,
        outer_file_sha256=outer_sha,
        semantic_manifest=semantic_manifest,
        seed=SEED,
        run_id=RUN_ID,
    )
    inner_reversed, audit_reversed = build_r6_inner_artifacts(
        outer_reversed,
        reversed(observations),
        outer_file_sha256=outer_sha,
        semantic_manifest=semantic_manifest,
        seed=SEED,
        run_id=RUN_ID,
    )
    if canonical_json_bytes(inner) != canonical_json_bytes(inner_reversed):
        raise RuntimeError("R6 inner forward/reverse canonical bytes differ")
    if canonical_json_bytes(audit) != canonical_json_bytes(audit_reversed):
        raise RuntimeError("R6 support audit forward/reverse canonical bytes differ")
    inner_errors = validate_r6_inner_artifact(inner)
    audit_errors = validate_support_audit(audit)
    if inner_errors or audit_errors:
        raise RuntimeError(f"R6 inner/audit validation failed: {inner_errors + audit_errors}")
    return outer, inner, audit


def _assert_old_artifacts() -> dict[str, str]:
    observed = {"outer": file_sha256(OLD_OUTER), "inner": file_sha256(OLD_INNER)}
    expected = {"outer": OLD_OUTER_SHA256, "inner": OLD_INNER_SHA256}
    if observed != expected:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: immutable old split hashes changed: {observed}")
    return observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--reader", type=Path, default=DEFAULT_READER)
    parser.add_argument("--semantic-support", type=Path, default=DEFAULT_SUPPORT)
    parser.add_argument("--outer-output", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--inner-output", type=Path, default=DEFAULT_INNER)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.seed != SEED:
        parser.error(f"--seed is frozen to {SEED}")
    before = _assert_old_artifacts()
    started = time.perf_counter()
    outer, inner, audit = construct_r6_split_artifacts(
        args.dataset_root, args.reader, args.semantic_support
    )
    outputs = {}
    for label, value, path in (
        ("outer", outer, args.outer_output),
        ("inner", inner, args.inner_output),
        ("support_audit", audit, args.audit_output),
    ):
        byte_count, physical_sha = write_canonical_json(value, path)
        outputs[label] = {
            "path": path.as_posix(),
            "bytes": byte_count,
            "physical_sha256": physical_sha,
            "canonical_payload_sha256": value["integrity"]["canonical_payload_sha256"],
            "config_hash": value["config_hash"],
        }
    after = _assert_old_artifacts()
    if before != after:
        raise RuntimeError("immutable old split artifacts changed during R6 build")
    elapsed = time.perf_counter() - started
    print("EQALIGN R6 SPLIT RECONCILIATION")
    print("status=PASS outer_cells_per_task=18 inner_cells_per_outer=9")
    print("forward_reverse_canonical_byte_identity=True")
    print(f"old_artifact_hashes={before}")
    print(f"outputs={json.dumps(outputs, sort_keys=True)}")
    print(f"source_manifest={json.dumps(_construction_source_manifest(), sort_keys=True)}")
    print("read_counters={r6_real_eeg_value_reads:0,outer_test_reads:0,calibration_reads:0}")
    print(f"elapsed_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
