#!/usr/bin/env python3
"""Build the real ZuCo 2.0 task-local 6x5 outer-fold artifact.

The script first proves the ordered source-slot join for each task, verifies
that every subject exposes the identical summary sequence, applies the v3.6
numeric/non-placeholder sentence policy, and only then invokes the shared
deterministic splitter.  It never uses text or a text hash as stimulus ID.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import h5py


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from data.joint_split import (  # noqa: E402
    DEFAULT_SEED,
    build_joint_split,
    canonical_json_bytes,
    sha256_bytes,
    validate_artifact,
    write_artifact,
)
from data.zuco2_loader import (  # noqa: E402
    TASKS,
    indexed_value,
    iter_summary_files,
    numeric_eeg_reference_status,
    validate_config,
)
from data.zuco2_source_join import (  # noqa: E402
    prove_task_source_join,
    read_summary_contents,
)


RUN_ID = "2026-08-14_010_v36_stage0_recovery"
METHOD = "ZuCo2-deterministic-joint-split"


def panel_records(dataset_root: Path, task: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    proof = prove_task_source_join(dataset_root, task)
    if not proof.verified:
        raise RuntimeError(f"{task} source-slot join blocked: {proof.status}")
    first = next(iter_summary_files(dataset_root, task), None)
    if first is None:
        raise FileNotFoundError(f"no summary file for {task}")
    canonical_contents = read_summary_contents(first.path)
    slots = {slot.summary_index: slot for slot in proof.slots}
    records: list[dict[str, object]] = []
    subject_sequence_hashes: dict[str, str] = {}
    for summary in iter_summary_files(dataset_root, task):
        contents = read_summary_contents(summary.path)
        sequence_hash = sha256_bytes(canonical_json_bytes(contents))
        subject_sequence_hashes[summary.subject_id] = sequence_hash
        if contents != canonical_contents:
            raise RuntimeError(
                f"{task}/{summary.subject_id} summary order differs from the verified source-slot sequence"
            )
        with h5py.File(summary.path, "r") as handle:
            raw_data = handle.get("sentenceData/rawData")
            if raw_data is None:
                raise RuntimeError(f"{task}/{summary.subject_id} has no sentenceData/rawData")
            if len(slots) != len(contents):
                raise RuntimeError(f"{task} join size changed during split construction")
            for sentence_index in range(1, len(contents) + 1):
                slot = slots[sentence_index]
                valid, reason = numeric_eeg_reference_status(
                    handle,
                    indexed_value(raw_data, sentence_index - 1),
                )
                records.append(
                    {
                        "record_id": f"{summary.subject_id}|{slot.source_slot_key}",
                        "subject_id": summary.subject_id,
                        "stimulus_id": slot.source_slot_key,
                        "group_key": slot.group_key,
                        "source_slot": slot.source_slot_key,
                        "valid_sentence_trials": 1 if valid else 0,
                        "join_status": "SOURCE_VERIFIED",
                        "eligible": valid,
                        "exclusion_reason": "" if valid else reason.upper(),
                    }
                )
    sequence_values = set(subject_sequence_hashes.values())
    metadata = proof.to_dict(include_slots=False)
    metadata["subject_sequence_sha256"] = subject_sequence_hashes
    metadata["all_subject_sequences_identical"] = len(sequence_values) == 1
    if not metadata["all_subject_sequences_identical"]:
        raise RuntimeError(f"{task} subject summary sequences are not identical")
    return records, metadata


def build_zuco2_artifact(dataset_root: Path, *, seed: int = DEFAULT_SEED) -> dict[str, object]:
    panels: dict[str, object] = {}
    joins: dict[str, object] = {}
    deterministic: dict[str, bool] = {}
    for task in TASKS:
        records, join = panel_records(dataset_root, task)
        first = build_joint_split(records, dataset="zuco_2_0", task=task, seed=seed)
        second = build_joint_split(list(reversed(records)), dataset="zuco_2_0", task=task, seed=seed)
        deterministic[task] = canonical_json_bytes(first) == canonical_json_bytes(second)
        if validate_artifact(first):
            raise RuntimeError(f"{task} split validation failed: {validate_artifact(first)}")
        panels[task] = first
        joins[task] = join

    config = {
        "spec": "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_6_2026-08-11.md#4.2.1",
        "method": METHOD,
        "seed": int(seed),
        "subject_folds": 6,
        "text_folds": 5,
        "tasks": list(TASKS),
        "source_identity": "source_file|row_number|paragraph_id_raw|sentence_id_raw",
        "text_hash_is_identity": False,
    }
    assertions = {
        "two_task_local_panels_present": set(panels) == set(TASKS),
        "all_source_joins_verified": all(
            value["status"] == "SOURCE_SLOT_JOIN_VERIFIED" for value in joins.values()
        ),
        "all_subject_sequences_identical": all(
            bool(value["all_subject_sequences_identical"]) for value in joins.values()
        ),
        "all_panel_contracts_pass": all(not validate_artifact(value) for value in panels.values()),
        "same_seed_is_byte_deterministic": all(deterministic.values()),
        "text_hash_is_not_identity": True,
    }
    artifact: dict[str, object] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "dataset": "zuco_2_0",
        "seed": int(seed),
        "fold": "task-local-6x5",
        "method": METHOD,
        "config": config,
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
        "source_joins": joins,
        "panels": panels,
        "assertions": assertions,
        "status": "PASS" if all(assertions.values()) else "FAIL",
    }
    payload = canonical_json_bytes(artifact)
    artifact["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": "canonical JSON artifact without integrity field",
    }
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("01_data_protocol/splits/zuco_2_0_outer_folds.json"),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error("--seed must be non-negative")
    started = time.perf_counter()
    validate_config(args.dataset_root)
    artifact = build_zuco2_artifact(args.dataset_root, seed=args.seed)
    byte_count, file_sha = write_artifact(artifact, args.output)
    panel_values = list(artifact["panels"].values())
    eligible = sum(len(panel["records"]) for panel in panel_values)
    excluded = sum(len(panel["exclusions"]) for panel in panel_values)
    subjects = [panel["subjects"]["count"] for panel in panel_values]
    stimuli = [panel["text"]["stimulus_count"] for panel in panel_values]
    cell_counts = [cell["test_record_count"] for panel in panel_values for cell in panel["cells"]]
    elapsed = time.perf_counter() - started
    print("ZUCO2 JOINT SPLIT SELF-CHECK")
    print(
        f"samples={{eligible_records: {eligible}, excluded_records: {excluded}}} "
        f"shapes={{panels: {len(panel_values)}, subjects: {subjects}, stimuli: {stimuli}, folds: [6,5]}}"
    )
    print(
        f"elapsed_seconds={elapsed:.3f} "
        f"ranges={{cell_test_records: [{min(cell_counts)},{max(cell_counts)}], artifact_bytes: {byte_count}}}"
    )
    print(
        f"seed={args.seed} fold={artifact['fold']} method={METHOD} "
        f"config_hash={artifact['config_hash']} artifact_sha256={file_sha}"
    )
    print(f"assertions={artifact['assertions']} status={artifact['status']}")
    print(f"output={args.output}")
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
