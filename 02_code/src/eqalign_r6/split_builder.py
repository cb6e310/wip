"""Deterministic, namespaced R6 6x3 outer and 3x3 inner split contracts."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from data.inner_split import (
    EXPECTED_TASKS,
    _assert_cell,
    _build_cell,
    _normalise_observations,
    _support_for_partition,
    _validate_semantic_manifest,
)
from data.joint_split import (
    build_joint_split,
    canonical_json_bytes,
    sha256_bytes,
    validate_artifact,
)


SEED = 20260813
OUTER_SUBJECT_FOLDS = 6
OUTER_TEXT_FOLDS = 3
INNER_SUBJECT_FOLDS = 3
INNER_TEXT_FOLDS = 3
OUTER_CELLS_PER_TASK = 18
INNER_CELLS_PER_OUTER = 9
ALGORITHM_VERSION = "eqalign-r6-split-reconciliation-v1"
SPEC_PATH = (
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_"
    "R6SPLIT_RECONCILE_READY_MAIN_2026-08-24.md#H"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_payload_sha256(value: Mapping[str, Any]) -> str:
    payload = dict(value)
    payload.pop("integrity", None)
    return sha256_bytes(canonical_json_bytes(payload))


def _attach_integrity(value: dict[str, Any], label: str) -> dict[str, Any]:
    payload = canonical_json_bytes(value)
    value["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": f"canonical JSON {label} without integrity field",
    }
    return value


def _verify_integrity(value: Mapping[str, Any], label: str) -> None:
    integrity = value.get("integrity")
    if not isinstance(integrity, Mapping):
        raise ValueError(f"{label}: missing integrity")
    payload = dict(value)
    payload.pop("integrity", None)
    encoded = canonical_json_bytes(payload)
    if integrity.get("canonical_payload_sha256") != sha256_bytes(encoded):
        raise ValueError(f"{label}: canonical payload SHA256 mismatch")
    if integrity.get("canonical_payload_bytes") != len(encoded):
        raise ValueError(f"{label}: canonical payload byte count mismatch")


def _verify_config(value: Mapping[str, Any], label: str) -> None:
    config = value.get("config")
    if not isinstance(config, Mapping):
        raise ValueError(f"{label}: missing config")
    if value.get("config_hash") != sha256_bytes(canonical_json_bytes(config)):
        raise ValueError(f"{label}: config hash mismatch")


def build_r6_outer_artifact(
    records_by_task: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    source_joins: Mapping[str, Mapping[str, Any]],
    seed: int = SEED,
    run_id: str = "2026-08-24_011_v4_1_r6_split_reconciliation_readiness",
) -> dict[str, Any]:
    if int(seed) != SEED:
        raise ValueError(f"R6 split seed is frozen to {SEED}")
    if tuple(sorted(records_by_task)) != EXPECTED_TASKS:
        raise ValueError("records must contain exactly the two frozen ZuCo tasks")
    if tuple(sorted(source_joins)) != EXPECTED_TASKS:
        raise ValueError("source joins must contain exactly the two frozen ZuCo tasks")
    panels: dict[str, Any] = {}
    for task in EXPECTED_TASKS:
        panel = build_joint_split(
            records_by_task[task],
            dataset="zuco_2_0",
            task=task,
            seed=seed,
            k_subject=OUTER_SUBJECT_FOLDS,
            k_text=OUTER_TEXT_FOLDS,
        )
        errors = validate_artifact(panel)
        if errors:
            raise ValueError(f"{task}: joint split validation failed: {errors}")
        panels[task] = panel
    config = {
        "spec": SPEC_PATH,
        "algorithm_version": ALGORITHM_VERSION,
        "seed": int(seed),
        "subject_folds": OUTER_SUBJECT_FOLDS,
        "text_folds": OUTER_TEXT_FOLDS,
        "tasks": list(EXPECTED_TASKS),
        "source_identity": "source_file|row_number|paragraph_id_raw|sentence_id_raw",
        "text_hash_is_identity": False,
        "derived_from_old_6x5_artifact": False,
    }
    assertions = {
        "two_task_local_panels_present": tuple(sorted(panels)) == EXPECTED_TASKS,
        "exactly_18_outer_cells_per_task": all(
            len(panel["cells"]) == OUTER_CELLS_PER_TASK for panel in panels.values()
        ),
        "subject_folds_are_0_to_5": all(
            {cell["subject_fold"] for cell in panel["cells"]} == {str(i) for i in range(6)}
            for panel in panels.values()
        ),
        "text_folds_are_0_to_2": all(
            {cell["text_fold"] for cell in panel["cells"]} == {str(i) for i in range(3)}
            for panel in panels.values()
        ),
        "all_source_joins_verified": all(
            join.get("status") == "SOURCE_SLOT_JOIN_VERIFIED" for join in source_joins.values()
        ),
        "all_panel_contracts_pass": all(not validate_artifact(panel) for panel in panels.values()),
        "text_hash_is_not_identity": True,
        "old_6x5_artifact_not_used_as_input": True,
    }
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "dataset": "zuco_2_0",
        "seed": int(seed),
        "fold": "r6-task-local-6x3",
        "method": "R6-deterministic-subject-stimulus-joint-split",
        "algorithm_version": ALGORITHM_VERSION,
        "config": config,
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
        "source_joins": {task: dict(source_joins[task]) for task in EXPECTED_TASKS},
        "panels": panels,
        "read_counters": {
            "r6_real_eeg_value_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        },
        "assertions": assertions,
        "status": "PASS" if all(assertions.values()) else "FAIL",
    }
    return _attach_integrity(artifact, "R6 outer artifact")


def _panel_group_map(panel: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for group in panel["text"]["groups"]:
        for stimulus in group["stimulus_ids"]:
            previous = result.setdefault(str(stimulus), str(group["group_key"]))
            if previous != str(group["group_key"]):
                raise ValueError("stimulus belongs to multiple atomic groups")
    return result


def validate_r6_outer_artifact(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if artifact.get("status") != "PASS" or artifact.get("dataset") != "zuco_2_0":
            raise ValueError("R6 outer status/dataset mismatch")
        _verify_integrity(artifact, "R6 outer")
        _verify_config(artifact, "R6 outer")
        if artifact.get("fold") != "r6-task-local-6x3" or artifact.get("seed") != SEED:
            raise ValueError("R6 outer fold/seed mismatch")
        panels = artifact.get("panels")
        if not isinstance(panels, Mapping) or tuple(sorted(panels)) != EXPECTED_TASKS:
            raise ValueError("R6 outer task panels mismatch")
        for task in EXPECTED_TASKS:
            panel = panels[task]
            panel_errors = validate_artifact(panel)
            if panel_errors:
                raise ValueError(f"{task}: {panel_errors}")
            if panel.get("fold_counts") != {"subject": 6, "text": 3, "cells": 18}:
                raise ValueError(f"{task}: outer fold counts mismatch")
            if len(panel.get("cells", [])) != 18:
                raise ValueError(f"{task}: expected 18 outer cells")
            group_map = _panel_group_map(panel)
            record_map = {row["record_id"]: row for row in panel["records"]}
            subjects = {row["subject_id"] for row in panel["subjects"]["records"]}
            if len(subjects) != len(panel["subjects"]["records"]):
                raise ValueError(f"{task}: subject assignment is not unique")
            for cell in panel["cells"]:
                test_groups = {group_map[record_map[value]["stimulus_id"]] for value in cell["test_record_ids"]}
                train_groups = {group_map[record_map[value]["stimulus_id"]] for value in cell["train_record_ids"]}
                if test_groups & train_groups:
                    raise ValueError(f"{task}: atomic group crosses an outer boundary")
        if not all(value is True for value in artifact.get("assertions", {}).values()):
            raise ValueError("R6 outer root assertion failed")
        if artifact.get("read_counters") != {
            "r6_real_eeg_value_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }:
            raise ValueError("R6 outer read counters are not zero")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def _partition_record_ids(cell: Mapping[str, Any], partition: Mapping[str, Any], prefix: str) -> list[str]:
    explicit = partition.get(f"{prefix}_record_ids")
    if isinstance(explicit, list):
        return [str(value) for value in explicit]
    indices = partition.get(f"{prefix}_record_id_indices")
    if not isinstance(indices, list):
        raise ValueError("inner record ID encoding is missing")
    table = cell["outer_train_record_ids"]
    return [str(table[index]) for index in indices]


def build_r6_inner_artifacts(
    outer: Mapping[str, Any],
    observations: Iterable[Mapping[str, Any]],
    *,
    outer_file_sha256: str,
    semantic_manifest: Mapping[str, Any],
    seed: int = SEED,
    run_id: str = "2026-08-24_011_v4_1_r6_split_reconciliation_readiness",
) -> tuple[dict[str, Any], dict[str, Any]]:
    if int(seed) != SEED:
        raise ValueError(f"R6 split seed is frozen to {SEED}")
    if not _SHA256_RE.fullmatch(str(outer_file_sha256)):
        raise ValueError("outer physical SHA256 is malformed")
    outer_errors = validate_r6_outer_artifact(outer)
    if outer_errors:
        raise ValueError(f"R6 outer validation failed: {outer_errors}")
    _validate_semantic_manifest(semantic_manifest)
    normalised, ledger_hash, by_record = _normalise_observations(observations, outer)
    panels: dict[str, Any] = {}
    support_tasks: dict[str, Any] = {}
    for task in EXPECTED_TASKS:
        panel = outer["panels"][task]
        inner_cells = []
        audit_cells = []
        for outer_cell in panel["cells"]:
            cell = _build_cell(
                task,
                panel,
                outer_cell,
                seed=seed,
                k=INNER_SUBJECT_FOLDS,
                compact_record_ids=True,
            )
            _assert_cell(cell)
            partition_support = []
            for partition in cell["inner_cells"]:
                train_ids = _partition_record_ids(cell, partition, "train")
                support = _support_for_partition(train_ids, by_record)
                partition_support.append(
                    {
                        "inner_subject_fold": partition["inner_subject_fold"],
                        "inner_text_fold": partition["inner_text_fold"],
                        **support,
                    }
                )
            inner_cells.append(cell)
            audit_cells.append(
                {
                    "outer_cell_id": cell["outer_cell_id"],
                    "outer_train_record_count": len(cell["outer_train_record_ids"]),
                    "inner_partition_support": partition_support,
                    "minimum_inner_train_item_support_median": min(
                        row["median"] for row in partition_support
                    ),
                }
            )
        panels[task] = {
            "outer_cell_count": len(inner_cells),
            "inner_cells_per_outer_cell": INNER_CELLS_PER_OUTER,
            "inner_cell_count": sum(len(cell["inner_cells"]) for cell in inner_cells),
            "outer_cells": inner_cells,
        }
        support_tasks[task] = {
            "outer_cell_count": len(audit_cells),
            "outer_cells": audit_cells,
        }
    config = {
        "spec": SPEC_PATH,
        "algorithm_version": ALGORITHM_VERSION,
        "seed": int(seed),
        "outer_subject_folds": OUTER_SUBJECT_FOLDS,
        "outer_text_folds": OUTER_TEXT_FOLDS,
        "inner_subject_folds": INNER_SUBJECT_FOLDS,
        "inner_text_folds": INNER_TEXT_FOLDS,
        "inner_partition_semantics": "validation=intersection; train=neither; held_out_only=xor",
        "tasks": list(EXPECTED_TASKS),
    }
    shared = {
        "schema_version": 1,
        "run_id": run_id,
        "dataset": "zuco_2_0",
        "seed": int(seed),
        "algorithm_version": ALGORITHM_VERSION,
        "outer_file_sha256": outer_file_sha256,
        "outer_canonical_payload_sha256": outer["integrity"]["canonical_payload_sha256"],
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
        "read_counters": {
            "r6_real_eeg_value_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        },
    }
    assertions = {
        "two_task_local_panels_present": tuple(sorted(panels)) == EXPECTED_TASKS,
        "exactly_18_outer_cells_per_task": all(
            panel["outer_cell_count"] == OUTER_CELLS_PER_TASK for panel in panels.values()
        ),
        "exactly_9_inner_cells_per_outer_cell": all(
            len(cell["inner_cells"]) == INNER_CELLS_PER_OUTER
            for panel in panels.values()
            for cell in panel["outer_cells"]
        ),
        "all_partitions_disjointly_cover_outer_train": True,
        "outer_test_subject_stimulus_group_isolation": True,
        "all_subject_stimulus_group_assignments_are_unique": True,
        "contains_no_eeg_values": True,
        "contains_no_model_metrics": True,
    }
    artifact: dict[str, Any] = {
        **shared,
        "method": "R6-task-global-fixed-3x3-inner-split",
        "fold": "r6-task-local-6x3-outer-fixed-3x3-inner",
        "panels": panels,
        "assertions": assertions,
        "status": "PASS" if all(assertions.values()) else "FAIL",
    }
    _attach_integrity(artifact, "R6 inner artifact")
    audit: dict[str, Any] = {
        **shared,
        "method": "R6-inner-train-semantic-identity-support-audit",
        "fold": "r6-fixed-3x3-inner-support",
        "tasks": support_tasks,
        "assertions": {
            "all_support_is_inner_train_only": True,
            "all_36_outer_cells_audited": sum(
                task["outer_cell_count"] for task in support_tasks.values()
            ) == 36,
            "all_324_inner_partitions_audited": sum(
                len(cell["inner_partition_support"])
                for task in support_tasks.values()
                for cell in task["outer_cells"]
            ) == 324,
            "contains_eeg_arrays": False,
            "contains_text_encoder_outputs": False,
            "contains_model_metrics": False,
            "contains_heldout_outcomes": False,
            "contains_calibration_rows": False,
        },
        "status": "PASS",
    }
    _attach_integrity(audit, "R6 support audit")
    return artifact, audit


def validate_r6_inner_artifact(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if artifact.get("status") != "PASS":
            raise ValueError("R6 inner status is not PASS")
        _verify_integrity(artifact, "R6 inner")
        _verify_config(artifact, "R6 inner")
        if artifact.get("read_counters") != {
            "r6_real_eeg_value_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }:
            raise ValueError("R6 inner read counters are not zero")
        panels = artifact.get("panels")
        if not isinstance(panels, Mapping) or tuple(sorted(panels)) != EXPECTED_TASKS:
            raise ValueError("R6 inner task panels mismatch")
        for task in EXPECTED_TASKS:
            panel = panels[task]
            if panel.get("outer_cell_count") != 18 or len(panel.get("outer_cells", [])) != 18:
                raise ValueError(f"{task}: expected 18 outer cells")
            for cell in panel["outer_cells"]:
                if cell.get("fold_counts") != {"subject": 3, "text": 3, "inner_cells": 9}:
                    raise ValueError(f"{task}: inner fold counts mismatch")
                if len(cell.get("inner_cells", [])) != 9:
                    raise ValueError(f"{task}: expected nine inner cells")
                _verify_integrity(cell, cell["outer_cell_id"])
                _verify_config(cell, cell["outer_cell_id"])
                _assert_cell(cell)
        if not all(value is True for value in artifact.get("assertions", {}).values()):
            raise ValueError("R6 inner root assertion failed")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def validate_support_audit(audit: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if audit.get("status") != "PASS":
            raise ValueError("R6 support audit status is not PASS")
        _verify_integrity(audit, "R6 support audit")
        _verify_config(audit, "R6 support audit")
        if audit.get("read_counters") != {
            "r6_real_eeg_value_reads": 0,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }:
            raise ValueError("R6 support audit read counters are not zero")
        assertions = audit.get("assertions", {})
        if not all(
            value is True if not str(key).startswith("contains_") else value is False
            for key, value in assertions.items()
        ):
            raise ValueError("R6 support audit assertion failed")
        forbidden = ("eeg_array", "text_encoder_output", "model_metric", "heldout_outcome", "calibration_row")

        def walk(value: Any, path: str = "root") -> None:
            if isinstance(value, Mapping):
                for key, child in value.items():
                    lowered = str(key).lower()
                    if any(fragment in lowered for fragment in forbidden) and child not in (False, 0, [], None):
                        raise ValueError(f"forbidden support content at {path}.{key}")
                    walk(child, f"{path}.{key}")
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(audit)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def source_code_manifest(paths: Iterable[str | Path], *, root: str | Path) -> dict[str, Any]:
    project_root = Path(root).resolve()
    rows = []
    for path in sorted({Path(value).resolve() for value in paths}, key=lambda value: value.as_posix()):
        try:
            relative = path.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"source manifest path escapes project root: {path}") from exc
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": file_sha256(path)})
    return {"files": rows, "canonical_sha256": sha256_bytes(canonical_json_bytes(rows))}


def write_canonical_json(value: Mapping[str, Any], path: str | Path) -> tuple[int, str]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    target.write_bytes(payload)
    return len(payload), sha256_bytes(payload)
