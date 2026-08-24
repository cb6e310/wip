"""Pure contracts for the v3.23 R2 inner-only geometry diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from data.a1_failure_diagnosis import sha256_file
from data.real_sham_r1_inner import (
    ARMS,
    FOLDS,
    METRICS,
    REGIMES,
    TASKS,
    paired_cross_recovery,
    summarize_subject_first,
    verify_immutable_parent_r0,
)


ALGORITHM_VERSION = "real-sham-r2-geometry-v323-d100-d105-v1"
RUN_ID = "2026-08-23_004_v323_real_sham_r2_geometry_inner"
TARGET = "Y0_RAW_MINILM"
ALIGNMENTS = ("M0_STRICT_INDUCTIVE", "M1_UNLABELED_TRANSDUCTIVE_EA")
BASES = ("B0_RAW_A1", "B1_TOKEN_LOCAL_LATENT")
CELLS = tuple(f"{alignment}/{basis}" for alignment in ALIGNMENTS for basis in BASES)
BASELINE_CELL = "M0_STRICT_INDUCTIVE/B0_RAW_A1"
INDUCTIVE_CELL = "M0_STRICT_INDUCTIVE/B1_TOKEN_LOCAL_LATENT"
TRANSDUCTIVE_CELLS = (
    "M1_UNLABELED_TRANSDUCTIVE_EA/B0_RAW_A1",
    "M1_UNLABELED_TRANSDUCTIVE_EA/B1_TOKEN_LOCAL_LATENT",
)
BASIS_DIMS = {"B0_RAW_A1": 840, "B1_TOKEN_LOCAL_LATENT": 384}

EXPECTED_H_ONLY_Y0 = 6
EXPECTED_GEOMETRY_PROBES = 96
EXPECTED_RIDGE_OPERATIONS = 102
EXPECTED_V5_LEDGERS = 102
EXPECTED_TRANSFORM_LEDGERS = 300

IMMUTABLE_R1_HASHES = {
    "artifacts/real_sham_r1_freeze.yaml": "d08719f3f2a5c9c21ceb80de2fff5949ccb8ac891750482f58768dfaa36b09a5",
    "artifacts/real_sham_r1_contract.yaml": "50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed",
    "04_results/diagnostics/real_sham_r1_inner.json": "610e40bf09959fb30f2a08f998b42148e9967168263a64c3ba37969194e964ff",
    "04_results/diagnostics/real_sham_r1_inner.md": "a858a7475b486bd874ace44435cc2de074c57391f6cdc9ffc102cb7f78c5beed",
    "04_results/diagnostics/real_sham_r1_inner_run_ledger.jsonl.gz": "28fc32b5103a1ba19b9c2cd2c724da5d7d3aff17f53f5ac72e3993e64db9314a",
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_22_2026-08-22.md": "2d334869985b914ffcb5d3a70af1e7c1d4fe1c18210e447736105e7c3941c95e",
    "runs/research/2026-08-22_003_v322_real_sham_r1_freeze.md": "9cef46f9612a988139d5f05a528a3a449119f59c7bb4f65d6b2ccd6b4dd800a9",
    "02_code/src/data/real_sham_r1_inner.py": "4a070945d55bbbf0a31f749fa15c12efd862151e3133f402cbbc33f096136029",
    "02_code/scripts/run_real_sham_r1_inner.py": "f3f218336df34f5342dfba28415bba7f80e836476d02fcfbca8d753c5d24e9ed",
    "02_code/tests/test_real_sham_r1_inner.py": "a63a2ce66dfa6eb16817483f10ad40d90ccc5a9486cc3b421d35eee8e3f6c670",
}


def verify_immutable_parent_r0_r1(root: Path) -> dict[str, str]:
    observed = verify_immutable_parent_r0(root)
    observed_r1 = {
        relative: sha256_file(root / relative) for relative in IMMUTABLE_R1_HASHES
    }
    if observed_r1 != IMMUTABLE_R1_HASHES:
        changed = {
            relative: {
                "expected": IMMUTABLE_R1_HASHES[relative],
                "observed": observed_r1[relative],
            }
            for relative in IMMUTABLE_R1_HASHES
            if observed_r1[relative] != IMMUTABLE_R1_HASHES[relative]
        }
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: immutable R1 artifacts changed: {changed}"
        )
    return {**observed, **observed_r1}


def _array_hash(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        value = np.ascontiguousarray(array)
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
        digest.update(value.tobytes())
    return digest.hexdigest()


def full_covariance_euclidean_alignment(
    arms: Mapping[str, np.ndarray],
    subject_ids: Sequence[str],
    *,
    task: str,
    fold: str,
    basis: str,
    regime: str,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    """Apply exact D102 real-only full-covariance EA per subject."""

    if set(arms) != set(ARMS):
        raise ValueError("D102 requires exactly the frozen four arms")
    matrices = {key: np.asarray(arms[key], dtype=np.float32) for key in ARMS}
    shapes = {value.shape for value in matrices.values()}
    if len(shapes) != 1:
        raise ValueError("D102 four-arm capacities differ")
    shape = next(iter(shapes))
    if len(shape) != 2 or shape[0] != len(subject_ids) or shape[1] < 1:
        raise ValueError("D102 requires aligned rank-2 arm matrices")
    if any(not np.isfinite(value).all() for value in matrices.values()):
        raise ValueError("D102 arm values must be finite")
    subjects = np.asarray(list(map(str, subject_ids)), dtype=object)
    if any(not value for value in subjects):
        raise ValueError("D102 requires non-empty subject scope keys")

    output = {key: np.empty(shape, dtype=np.float32) for key in ARMS}
    ledger: list[dict[str, Any]] = []
    d = shape[1]
    for subject in sorted(set(subjects.tolist())):
        indices = np.flatnonzero(subjects == subject)
        real = matrices["real"][indices].astype(np.float64)
        mu = real.mean(axis=0)
        z = real - mu
        denominator = max(len(indices) - 1, 1)
        base_covariance = (z.T @ z) / denominator
        base_trace = float(np.trace(base_covariance))
        regularization = 1e-6 * base_trace / d
        covariance = base_covariance + regularization * np.eye(d, dtype=np.float64)
        covariance = (covariance + covariance.T) * 0.5
        covariance_trace = float(np.trace(covariance))
        if (
            not np.isfinite(mu).all()
            or not np.isfinite(covariance).all()
            or not np.isfinite(base_trace)
            or not np.isfinite(regularization)
            or not np.isfinite(covariance_trace)
            or covariance_trace <= 0.0
            or regularization <= 0.0
        ):
            raise ValueError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: D102 zero/nonfinite trace")
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        if not np.isfinite(eigenvalues).all() or not np.isfinite(eigenvectors).all():
            raise ValueError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: D102 eigendecomposition nonfinite")
        floored = np.maximum(eigenvalues, regularization)
        whitening = (eigenvectors * np.power(floored, -0.5)) @ eigenvectors.T
        whitening = (whitening + whitening.T) * 0.5
        if not np.isfinite(whitening).all():
            raise ValueError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: D102 transform nonfinite")
        for arm in ARMS:
            aligned = (matrices[arm][indices].astype(np.float64) - mu) @ whitening
            if not np.isfinite(aligned).all():
                raise ValueError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: aligned arm nonfinite")
            output[arm][indices] = aligned.astype(np.float32)
        ledger.append(
            {
                "schema_version": 1,
                "ledger_type": "M1_D102_TRANSFORM",
                "run_id": RUN_ID,
                "task": task,
                "fold": fold,
                "basis": basis,
                "regime": regime,
                "subject_id": subject,
                "subject_id_used_for_grouping_only": True,
                "row_count": int(len(indices)),
                "feature_dim": int(d),
                "real_arm_values_only": True,
                "labels_used": False,
                "item_ids_used": False,
                "h_used": False,
                "task_label_used_as_feature": False,
                "sham_labels_used_to_fit": False,
                "shared_across_arms": True,
                "transductive": True,
                "float64_covariance_and_eigendecomposition": True,
                "denominator": int(denominator),
                "unregularized_trace": base_trace,
                "lambda": float(regularization),
                "covariance_trace": covariance_trace,
                "eigenvalue_floor": float(regularization),
                "minimum_eigenvalue_before_floor": float(eigenvalues.min()),
                "minimum_eigenvalue_after_floor": float(floored.min()),
                "real_input_sha256": _array_hash(real),
                "transform_sha256": _array_hash(mu, whitening),
                "row_indices_sha256": _array_hash(indices.astype(np.int64)),
                "fallback_used": False,
            }
        )
    if any(not np.isfinite(value).all() for value in output.values()):
        raise ValueError("D102 output contains nonfinite values")
    return output, ledger


def validate_transform_ledgers(
    rows: Sequence[Mapping[str, Any]], *, expected_count: int = EXPECTED_TRANSFORM_LEDGERS
) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"D102 transform ledger count {len(rows)} != {expected_count}")
    identities = {
        (
            row.get("task"),
            row.get("fold"),
            row.get("basis"),
            row.get("regime"),
            row.get("subject_id"),
        )
        for row in rows
    }
    if len(identities) != expected_count:
        raise ValueError("D102 transform scopes are not unique")
    for row in rows:
        if row.get("ledger_type") != "M1_D102_TRANSFORM":
            raise ValueError("unexpected transform ledger type")
        required_true = (
            "subject_id_used_for_grouping_only",
            "real_arm_values_only",
            "shared_across_arms",
            "transductive",
            "float64_covariance_and_eigendecomposition",
        )
        required_false = (
            "labels_used",
            "item_ids_used",
            "h_used",
            "task_label_used_as_feature",
            "sham_labels_used_to_fit",
            "fallback_used",
        )
        if any(row.get(key) is not True for key in required_true):
            raise ValueError("D102 required transform flag changed")
        if any(row.get(key) is not False for key in required_false):
            raise ValueError("D102 forbidden transform input or fallback detected")
        if row.get("lambda", 0.0) <= 0.0 or row.get("covariance_trace", 0.0) <= 0.0:
            raise ValueError("D102 trace/lambda contract failed")
        if row.get("eigenvalue_floor") != row.get("lambda"):
            raise ValueError("D102 eigenvalue floor changed")
        for key in ("real_input_sha256", "transform_sha256", "row_indices_sha256"):
            value = row.get(key)
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError(f"D102 missing {key}")


def evaluate_r2_outcome(
    results: Mapping[str, Any], *, contract_pass: bool
) -> tuple[str, list[str], list[str]]:
    if not contract_pass:
        return (
            "INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC",
            [],
            ["SCOPE_TRANSFORM_LEDGER_READ_COUNT_TEST_OR_HASH_CONTRACT_FAILED"],
        )
    baseline = {task: results[task][BASELINE_CELL]["cross"] for task in TASKS}
    for task in TASKS:
        for cell in CELLS:
            row = results[task][cell]
            if cell == BASELINE_CELL:
                row["cross_recovery"] = None
                row["recovery_pass"] = False
                continue
            recovery = paired_cross_recovery(
                row["cross"], baseline[task], task=task, candidate_id=cell
            )
            passed = (
                row["cross"]["family_detected"]
                and recovery["ci95"][0] > 0.0
                and recovery["positive_subject_count"] >= 10
            )
            row["cross_recovery"] = recovery
            row["recovery_pass"] = bool(passed)
    inductive_tasks = [
        task for task in TASKS if results[task][INDUCTIVE_CELL]["recovery_pass"]
    ]
    if inductive_tasks:
        return "PASS_R2_INDUCTIVE_GEOMETRY", inductive_tasks, []
    transductive_tasks = sorted(
        {
            task
            for task in TASKS
            for cell in TRANSDUCTIVE_CELLS
            if results[task][cell]["recovery_pass"]
        }
    )
    if transductive_tasks:
        return "PASS_R2_TRANSDUCTIVE_GEOMETRY_ONLY", transductive_tasks, []
    return "FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC", [], []


__all__ = [
    "ALIGNMENTS",
    "ALGORITHM_VERSION",
    "ARMS",
    "BASELINE_CELL",
    "BASES",
    "BASIS_DIMS",
    "CELLS",
    "EXPECTED_GEOMETRY_PROBES",
    "EXPECTED_H_ONLY_Y0",
    "EXPECTED_RIDGE_OPERATIONS",
    "EXPECTED_TRANSFORM_LEDGERS",
    "EXPECTED_V5_LEDGERS",
    "FOLDS",
    "INDUCTIVE_CELL",
    "METRICS",
    "REGIMES",
    "RUN_ID",
    "TARGET",
    "TASKS",
    "TRANSDUCTIVE_CELLS",
    "evaluate_r2_outcome",
    "full_covariance_euclidean_alignment",
    "summarize_subject_first",
    "validate_transform_ledgers",
    "verify_immutable_parent_r0_r1",
]
