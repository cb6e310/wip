"""Pure existing-artifact diagnostics for the v3.21 real-vs-sham freeze."""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from data.a1_admission import (
    DEFAULT_ADMISSION_CONFIG,
    cluster_bootstrap,
    stable_seed,
    u_statistics,
)
from data.a1_failure_diagnosis import sha256_file, verify_old_evidence


ALGORITHM_VERSION = "real-sham-rescue-r0-v321-d83-d86-v1"
RUN_ID = "2026-08-22_002_v321_real_sham_rescue_r0"
TASKS = ("task1_nr", "task2_tsr")
BASES = ("raw", "token_local_frozen_initial_latent")
SHAMS = (
    "trial_shuffle",
    "within_trial_unit_assignment_shuffle",
    "channel_block_permutation",
)
OLD_METRICS = (
    "u_oof",
    "u_min",
    "real_minus_trial_shuffle",
    "real_minus_within_trial_unit_assignment_shuffle",
    "real_minus_channel_block_permutation",
)
ABSOLUTE_REPRODUCTION_TOLERANCE = 1e-12

ADMISSION_JSON = Path("04_results/audits/a1_admission.json")
ADMISSION_LEDGER = Path("04_results/audits/a1_admission_run_ledger.jsonl.gz")
RECOVERY_JSON = Path("04_results/audits/a1_measurement_recovery.json")

PARENT_FORMAL_HASHES = {
    "04_results/audits/a1_admission.json": "b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e",
    "04_results/audits/a1_admission.md": "e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e",
    "04_results/audits/a1_admission_run_ledger.jsonl.gz": "fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd",
    "04_results/audits/a1_measurement_recovery.json": "cf68c0ca170152a79f163ed001706df80ea649ea854da85b09fef1f638e8b51a",
    "04_results/audits/a1_measurement_recovery.md": "fc039ae77043619e562eb942898287321882189736bdd8219fc3c6a71cc87004",
    "04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz": "90326ad6ed2bb981df0c0d8559102dd73c56a16ce7de6923973bad42529debc7",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark.json": "f496f308688df7ff68b82f2a5c38fedc971032801b6060f7ed1e61e64e21d2ea",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark.md": "94e580531f16e8886949b7196c2d47889f360997bda6d467fb044f619c54d9ea",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark_run_ledger.jsonl.gz": "705e9b034794f77eac0f91355f093e7dc70a5d2bb2a13fa2f7da784a0e8b2601",
}


def _arm_array(value: Any, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{label} must be a finite nonempty one-dimensional array")
    return array


def _validated_arms(real: Any, shams: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if set(shams) != set(SHAMS):
        raise ValueError(f"sham scope must be exactly {SHAMS}")
    real_values = _arm_array(real, "real")
    values = {name: _arm_array(shams[name], name) for name in SHAMS}
    if any(value.shape != real_values.shape for value in values.values()):
        raise ValueError("real and sham arrays must have identical shapes")
    return real_values, values


def semantic_sham_contrast(real: Any, shams: Mapping[str, Any]) -> np.ndarray:
    """Return real minus the two exchangeability-preserving semantic shams."""

    real_values, values = _validated_arms(real, shams)
    semantic_mean = np.stack(
        [values["trial_shuffle"], values["within_trial_unit_assignment_shuffle"]]
    ).mean(axis=0)
    return real_values - semantic_mean


def legacy_sham_contrast(real: Any, shams: Mapping[str, Any]) -> np.ndarray:
    """Return the inherited real-minus-three-sham mean using the parent helper."""

    real_values, values = _validated_arms(real, shams)
    return u_statistics(real_values, values)["u_oof"]


def channel_topology_sentinel(real: Any, shams: Mapping[str, Any]) -> np.ndarray:
    """Return real minus channel-block permutation without hiding the sentinel."""

    real_values, values = _validated_arms(real, shams)
    return real_values - values["channel_block_permutation"]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _load_jsonl_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: every JSONL row must be an object")
    return rows


def validate_candidate_scope(admission: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen task, basis, sham, metric, and subject populations."""

    results = admission.get("results")
    if not isinstance(results, Mapping) or set(results) != set(TASKS):
        raise ValueError(f"admission task scope must be exactly {TASKS}")
    cells: dict[str, Any] = {}
    for task in TASKS:
        a_a1 = results[task].get("A-A1")
        if not isinstance(a_a1, Mapping) or set(a_a1) != set(BASES):
            raise ValueError(f"{task}: basis scope must be exactly {BASES}")
        for basis in BASES:
            metrics = a_a1[basis].get("metrics")
            if not isinstance(metrics, Mapping) or set(metrics) != set(OLD_METRICS):
                raise ValueError(f"{task}/{basis}: old metric scope changed")
            subject_sets = {
                metric: set(summary.get("subject_values", {}))
                for metric, summary in metrics.items()
            }
            if any(len(subjects) != 15 for subjects in subject_sets.values()):
                raise ValueError(f"{task}/{basis}: expected 15 subjects for every metric")
            if len({tuple(sorted(subjects)) for subjects in subject_sets.values()}) != 1:
                raise ValueError(f"{task}/{basis}: metric subject identities differ")
            cells[f"{task}/{basis}"] = {
                "subject_count": 15,
                "subject_ids": sorted(next(iter(subject_sets.values()))),
                "old_metrics": list(OLD_METRICS),
            }
    return {
        "status": "PASS",
        "tasks": list(TASKS),
        "bases": list(BASES),
        "shams": list(SHAMS),
        "cells": cells,
        "new_candidate_count": 0,
        "new_seed_count": 0,
        "new_fold_count": 0,
        "new_sham_count": 0,
        "new_threshold_count": 0,
    }


def validate_no_outer_reads(
    admission: Mapping[str, Any],
    recovery: Mapping[str, Any],
    ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require zero outer-test and calibration reads in parents and every V5 stage."""

    outer = admission.get("outer_test", {})
    if outer.get("eeg_feature_label_metric_reads") != 0:
        raise ValueError("A1 admission reports outer-test EEG/label/metric reads")
    if outer.get("calibration_record_count") != 0:
        raise ValueError("A1 admission reports calibration reads")
    recovery_outer = recovery.get("outer_test", {})
    if recovery_outer.get("eeg_label_metric_reads") != 0:
        raise ValueError("A1 recovery reports outer-test EEG/label/metric reads")
    if recovery_outer.get("calibration_reads") != 0:
        raise ValueError("A1 recovery reports calibration reads")

    outer_reads = 0
    calibration_reads = 0
    for row in ledgers:
        outer_ids = row.get("outer_test_record_ids_read")
        calibration_ids = row.get("calibration_record_ids")
        if not isinstance(outer_ids, list) or not isinstance(calibration_ids, list):
            raise ValueError("parent V5 ledger lacks explicit read ledgers")
        outer_reads += len(outer_ids)
        calibration_reads += len(calibration_ids)
        for stage in row.get("stages", []):
            stage_outer = stage.get("outer_test_record_ids_read", [])
            stage_calibration = stage.get("calibration_record_ids", [])
            if not isinstance(stage_outer, list) or not isinstance(stage_calibration, list):
                raise ValueError("parent V5 stage read ledgers are malformed")
            outer_reads += len(stage_outer)
            calibration_reads += len(stage_calibration)
    if outer_reads or calibration_reads:
        raise ValueError(
            f"parent V5 ledgers contain outer/calibration reads: {outer_reads}/{calibration_reads}"
        )
    fit_ids = [str(row.get("fit_id")) for row in ledgers]
    if len(ledgers) != 639 or len(set(fit_ids)) != 639:
        raise ValueError("A1 admission ledger must contain exactly 639 unique V5 fits")
    return {
        "status": "PASS",
        "parent_v5_ledgers_validated": len(ledgers),
        "unique_parent_fit_ids": len(set(fit_ids)),
        "outer_test_eeg_label_metric_reads": 0,
        "calibration_reads": 0,
    }


def _summary_from_subject_values(
    values: Mapping[str, float], *, task: str, basis: str, metric: str
) -> dict[str, Any]:
    return cluster_bootstrap(
        values,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(20260813, "A-A1", task, basis, metric),
    )


def _numeric_max_error(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max((_numeric_max_error(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, Sequence) and not isinstance(left, (str, bytes)):
        if not isinstance(right, Sequence) or isinstance(right, (str, bytes)) or len(left) != len(right):
            return math.inf
        return max((_numeric_max_error(a, b) for a, b in zip(left, right, strict=True)), default=0.0)
    if isinstance(left, bool) or isinstance(right, bool):
        return 0.0 if left == right else math.inf
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


def _single_contrast_arms(metrics: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, np.ndarray], list[str]]:
    subjects = sorted(metrics["u_oof"]["subject_values"])
    real = np.zeros(len(subjects), dtype=np.float64)
    shams = {
        name: -np.asarray(
            [metrics[f"real_minus_{name}"]["subject_values"][subject] for subject in subjects],
            dtype=np.float64,
        )
        for name in SHAMS
    }
    return real, shams, subjects


def _diagnose_cell(task: str, basis: str, metrics: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    reproduction: dict[str, Any] = {}
    for metric in OLD_METRICS:
        rebuilt = _summary_from_subject_values(
            metrics[metric]["subject_values"], task=task, basis=basis, metric=metric
        )
        error = _numeric_max_error(rebuilt, metrics[metric])
        reproduction[metric] = {
            "reproduced": error <= ABSOLUTE_REPRODUCTION_TOLERANCE,
            "max_abs_error": error,
            "old_summary": dict(metrics[metric]),
        }

    real, shams, subjects = _single_contrast_arms(metrics)
    semantic_values = semantic_sham_contrast(real, shams)
    legacy_values = legacy_sham_contrast(real, shams)
    channel_values = channel_topology_sentinel(real, shams)
    old_u_oof = np.asarray(
        [metrics["u_oof"]["subject_values"][subject] for subject in subjects], dtype=np.float64
    )
    legacy_subject_max_error = float(np.max(np.abs(legacy_values - old_u_oof)))
    reproduction["u_oof_from_three_single_shams"] = {
        "reproduced": legacy_subject_max_error <= ABSOLUTE_REPRODUCTION_TOLERANCE,
        "max_abs_error": legacy_subject_max_error,
    }
    diagnostics = {
        "delta_semantic": _summary_from_subject_values(
            dict(zip(subjects, semantic_values.tolist(), strict=True)),
            task=task,
            basis=basis,
            metric="delta_semantic",
        ),
        "delta_legacy": _summary_from_subject_values(
            dict(zip(subjects, legacy_values.tolist(), strict=True)),
            task=task,
            basis=basis,
            metric="u_oof",
        ),
        "delta_channel": _summary_from_subject_values(
            dict(zip(subjects, channel_values.tolist(), strict=True)),
            task=task,
            basis=basis,
            metric="real_minus_channel_block_permutation",
        ),
        "legacy_sensitivity": {
            "u_oof": dict(metrics["u_oof"]),
            "u_min": dict(metrics["u_min"]),
            "single_sham_contrasts": {
                name: dict(metrics[f"real_minus_{name}"]) for name in SHAMS
            },
        },
    }
    return diagnostics, reproduction


def verify_parent_formal_hashes(root: Path) -> dict[str, str]:
    observed = {relative: sha256_file(root / relative) for relative in PARENT_FORMAL_HASHES}
    if observed != PARENT_FORMAL_HASHES:
        changed = {
            relative: {"expected": PARENT_FORMAL_HASHES[relative], "observed": observed[relative]}
            for relative in PARENT_FORMAL_HASHES
            if observed[relative] != PARENT_FORMAL_HASHES[relative]
        }
        raise RuntimeError(f"STATE_SPEC_CONFLICT: immutable parent formal artifacts changed: {changed}")
    return observed


def build_r0_diagnosis(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build the complete R0 result without fitting or reading outer outcomes."""

    project = root.resolve()
    observed_hashes = verify_parent_formal_hashes(project)
    immutable = verify_old_evidence(project)
    admission = _load_json(project / ADMISSION_JSON)
    recovery = _load_json(project / RECOVERY_JSON)
    ledgers = immutable["ledgers"]
    scope = validate_candidate_scope(admission)
    read_audit = validate_no_outer_reads(admission, recovery, ledgers)
    if admission.get("completion_outcome") != "FAIL_A1_ADMISSION":
        raise RuntimeError("STATE_SPEC_CONFLICT: parent A1 admission outcome changed")
    if recovery.get("completion_outcome") != "FAIL_A1R_RECOVERY":
        raise RuntimeError("STATE_SPEC_CONFLICT: parent A1 recovery outcome changed")
    if recovery.get("selected_frontend") is not None:
        raise RuntimeError("STATE_SPEC_CONFLICT: parent recovery unexpectedly selected a frontend")
    if not recovery.get("contract_checks", {}).get("run032_outcome_unchanged"):
        raise RuntimeError("STATE_SPEC_CONFLICT: run-032 immutable outcome check is absent")

    diagnostics: dict[str, Any] = {}
    reproduction: dict[str, Any] = {}
    for task in TASKS:
        diagnostics[task] = {}
        reproduction[task] = {}
        for basis in BASES:
            metrics = admission["results"][task]["A-A1"][basis]["metrics"]
            cell_diagnostics, cell_reproduction = _diagnose_cell(task, basis, metrics)
            diagnostics[task][basis] = cell_diagnostics
            reproduction[task][basis] = cell_reproduction
    reproduction_pass = all(
        check["reproduced"]
        for task in reproduction.values()
        for basis in task.values()
        for check in basis.values()
    )
    outcome = (
        "PASS_REAL_SHAM_RESCUE_FREEZE"
        if reproduction_pass
        else "INVALID_REAL_SHAM_RESCUE_R0"
    )
    payload = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "task": "R0_REAL_SHAM_RESCUE_FREEZE",
        "run_id": RUN_ID,
        "outcome": outcome,
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "claim_boundary": {
            "parent_outcomes_immutable": True,
            "real_eeg_increment_claim": False,
            "released": {
                "alignment": False,
                "direct_u_plus": False,
                "EQ_ANMA": False,
                "Gate_A": False,
                "Gate_B": False,
                "A3": False,
                "ROAMM": False,
            },
        },
        "parent_outcomes": {
            "a1_admission": "FAIL_A1_ADMISSION",
            "a1_recovery": "FAIL_A1R_RECOVERY",
            "run_032": "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT",
            "synthetic_eq_anma": "FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE",
            "outer_negative_confirmation": "READY_NOT_RUN",
        },
        "execution": {
            "existing_artifact_reanalysis_only": True,
            "new_eeg_fits": 0,
            "outer_test_eeg_label_metric_reads": 0,
            "calibration_reads": 0,
            "source_v5_ledgers_validated": read_audit["parent_v5_ledgers_validated"],
        },
        "scope_validation": scope,
        "read_validation": read_audit,
        "old_value_reproduction": {
            "status": "PASS" if reproduction_pass else "FAIL",
            "absolute_tolerance": ABSOLUTE_REPRODUCTION_TOLERANCE,
            "checks": reproduction,
        },
        "diagnostic_estimands": {
            "delta_semantic": "real - mean(trial_shuffle, within_trial_unit_assignment_shuffle)",
            "delta_legacy": "real - mean(trial_shuffle, within_trial_unit_assignment_shuffle, channel_block_permutation)",
            "delta_channel": "real - channel_block_permutation",
            "channel_block_role": "topology_sentinel_retained",
        },
        "diagnostics": diagnostics,
        "parent_formal_hashes": observed_hashes,
        "next_task": "R1_REAL_SHAM_INNER_DIAGNOSTIC_AFTER_AUTHOR_REVIEW_ONLY",
    }
    ledger_rows = [
        {
            "schema_version": 1,
            "run_id": RUN_ID,
            "activity_id": "R0|a1_admission_aggregate_read",
            "activity": "existing_artifact_read",
            "source_path": str(ADMISSION_JSON),
            "source_sha256": observed_hashes[str(ADMISSION_JSON)],
            "fit_id": None,
            "new_eeg_fit_count": 0,
            "outer_test_record_ids_read": [],
            "calibration_record_ids": [],
        },
        {
            "schema_version": 1,
            "run_id": RUN_ID,
            "activity_id": "R0|a1_admission_v5_ledger_validation",
            "activity": "existing_v5_ledger_validation",
            "source_path": str(ADMISSION_LEDGER),
            "source_sha256": observed_hashes[str(ADMISSION_LEDGER)],
            "parent_v5_ledger_count": 639,
            "unique_parent_fit_ids": 639,
            "fit_id": None,
            "new_eeg_fit_count": 0,
            "outer_test_record_ids_read": [],
            "calibration_record_ids": [],
        },
        {
            "schema_version": 1,
            "run_id": RUN_ID,
            "activity_id": "R0|a1_measurement_recovery_aggregate_read",
            "activity": "existing_artifact_read",
            "source_path": str(RECOVERY_JSON),
            "source_sha256": observed_hashes[str(RECOVERY_JSON)],
            "fit_id": None,
            "new_eeg_fit_count": 0,
            "outer_test_record_ids_read": [],
            "calibration_record_ids": [],
        },
    ]
    return payload, ledger_rows
