"""Pure contracts for the v3.25 R4 orthogonal inner diagnostic."""

from __future__ import annotations

import hashlib
import json
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
)
from data.real_sham_r3_subject_balanced import verify_immutable_parent_r0_r1_r2


ALGORITHM_VERSION = "real-sham-r4-orthogonal-v325-d114-d119-v1"
RUN_ID = "2026-08-24_006_v325_real_sham_r4_orthogonal_inner"
TARGET = "Y0_RAW_MINILM"
BASIS = "B0_RAW_A1"
ALIGNMENT = "M0_STRICT_INDUCTIVE"
METHODS = ("P0_JOINT_RIDGE_REPLICATION", "C1_SUBJECT_BLOCK_ORTHOGONAL")
BASELINE_METHOD = METHODS[0]
CANDIDATE_METHOD = METHODS[1]

EXPECTED_P0_H_ONLY = 6
EXPECTED_P0_JOINT = 24
EXPECTED_C1_OOF_Y = 30
EXPECTED_C1_OOF_X = 120
EXPECTED_C1_FULL_Y = 6
EXPECTED_C1_FULL_X = 24
EXPECTED_C1_RESIDUAL_PROBES = 24
EXPECTED_RIDGE_OPERATIONS = 234
EXPECTED_FINAL_V5_LEDGERS = 54
EXPECTED_NUISANCE_LEDGERS = 180
EXPECTED_CROSSFIT_SCOPES = 6

IMMUTABLE_R3_HASHES = {
    "artifacts/real_sham_r3_freeze.yaml": "cbc4386823b38f30d00aa29f862dfd818873a2e83edf0f2cffd6c2534187a94b",
    "artifacts/real_sham_r3_subject_balanced_contract.yaml": "04f67c0cc4762ee93eb13fbcb26e57c20a65e3ec57cdfbd0b2f5fe107f9b1f92",
    "04_results/diagnostics/real_sham_r3_subject_balanced_inner.json": "ccf89fb575c9bcd35a866ccf53c1d0f8fcc56bd9a17cffea3c1bb85261258812",
    "04_results/diagnostics/real_sham_r3_subject_balanced_inner.md": "1822c9efa69496f089858c1f266d75b8e87b0e42faa2c709ec7a8976d8c06cc9",
    "04_results/diagnostics/real_sham_r3_subject_balanced_inner_run_ledger.jsonl.gz": "417070b98346de0a3e9015922cc06afd32988d298f6b28b7110c766ffefa292d",
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_24_2026-08-24.md": "4e17a8499a61e5e53fc416b128ab6b153f48b56e7e4230b7ff1c9f4eef3a00b3",
    "runs/research/2026-08-24_005_v324_real_sham_r3_subject_balanced_freeze.md": "33cbbfb10720218a9c72df70805a24687e2e8a7793cbb116682bb8f83895673b",
    "02_code/src/data/real_sham_r3_subject_balanced.py": "8d283ca328c1b2c6319ed1985a4d9fb19942ca5e42458fa575336eee2fc6f35f",
    "02_code/scripts/run_real_sham_r3_subject_balanced.py": "b1e578dd442c0f84170eff71f1cf94c80162d69ff84d473800d22070abd55249",
    "02_code/tests/test_real_sham_r3_subject_balanced.py": "d8a364df2496eb4910660c2bb250068be9c2123cf2f0af7f319f9e398797cd0c",
}


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_immutable_parent_r0_r1_r2_r3(root: Path) -> dict[str, str]:
    observed = verify_immutable_parent_r0_r1_r2(root)
    observed_r3 = {
        relative: sha256_file(root / relative) for relative in IMMUTABLE_R3_HASHES
    }
    if observed_r3 != IMMUTABLE_R3_HASHES:
        changed = {
            relative: {
                "expected": IMMUTABLE_R3_HASHES[relative],
                "observed": observed_r3[relative],
            }
            for relative in IMMUTABLE_R3_HASHES
            if observed_r3[relative] != IMMUTABLE_R3_HASHES[relative]
        }
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: immutable R3 artifacts changed: {changed}"
        )
    return {**observed, **observed_r3}


def subject_blocks(
    fit_subject_ids: Sequence[str], *, task: str, inner_cell_id: str
) -> list[list[str]]:
    subjects = sorted(set(map(str, fit_subject_ids)))
    if len(subjects) != 10 or any(not subject for subject in subjects):
        raise ValueError("R4 requires exactly 10 non-empty source fit subjects")
    ordered = sorted(
        subjects,
        key=lambda subject: (
            hashlib.sha256(
                f"20260813|{task}|{inner_cell_id}|{subject}".encode("utf-8")
            ).hexdigest(),
            subject,
        ),
    )
    blocks = [ordered[index : index + 2] for index in range(0, 10, 2)]
    if len(blocks) != 5 or any(len(block) != 2 for block in blocks):
        raise ValueError("R4 subject block assignment is not 5x2")
    return blocks


def ridge_predict(model: Mapping[str, np.ndarray], values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=np.float32)
    weights = np.asarray(model["weights"], dtype=np.float32)
    intercept = np.asarray(model["intercept"], dtype=np.float32)
    if x.ndim != 2 or weights.ndim != 2 or intercept.ndim != 1:
        raise ValueError("R4 ridge prediction requires rank-2 X/weights")
    if x.shape[1] != weights.shape[0] or weights.shape[1] != intercept.shape[0]:
        raise ValueError("R4 ridge prediction dimensions differ")
    result = x @ weights + intercept
    if not np.isfinite(result).all():
        raise ValueError("R4 ridge prediction is nonfinite")
    return result.astype(np.float32, copy=False)


def orthogonal_query(
    h: np.ndarray,
    x_arm: np.ndarray,
    *,
    m_y_full: Mapping[str, np.ndarray],
    m_x_full: Mapping[str, np.ndarray],
    beta_arm: Mapping[str, np.ndarray],
) -> np.ndarray:
    h_values = np.asarray(h, dtype=np.float32)
    x_values = np.asarray(x_arm, dtype=np.float32)
    if h_values.shape[0] != x_values.shape[0] or x_values.shape[1] != 840:
        raise ValueError("R4 orthogonal scoring rows or raw A1 capacity changed")
    x_residual = x_values - ridge_predict(m_x_full, h_values)
    if beta_arm["weights"].shape[0] != 840:
        raise ValueError("R4 residual probe must contain only 840D EEG residual")
    query = ridge_predict(m_y_full, h_values) + ridge_predict(beta_arm, x_residual)
    if query.shape[1] != 384 or not np.isfinite(query).all():
        raise ValueError("R4 orthogonal query target capacity changed")
    return query.astype(np.float32, copy=False)


def residual_summary(residual: np.ndarray) -> dict[str, float]:
    values = np.asarray(residual, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all() or values.shape[0] < 1:
        raise ValueError("R4 residual summary requires finite rank-2 rows")
    row_norms = np.linalg.norm(values, axis=1)
    return {
        "mse": float(np.mean(np.square(values))),
        "mean_row_l2_norm": float(row_norms.mean()),
        "minimum_row_l2_norm": float(row_norms.min()),
        "maximum_row_l2_norm": float(row_norms.max()),
    }


def validate_r4_formal_output(value: Any) -> dict[str, Any]:
    """Reject model arrays and row-level scoring payloads from formal outputs."""

    forbidden = {"weights", "features", "feature", "query", "queries", "logits"}
    violations: list[str] = []

    def visit(current: Any, path: str) -> None:
        if isinstance(current, Mapping):
            for key, child in current.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key).lower() in forbidden:
                    violations.append(child_path)
                visit(child, child_path)
        elif isinstance(current, (list, tuple)):
            for index, child in enumerate(current):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return {"pass": not violations, "violations": violations}


def validate_crossfit_audits(
    rows: Sequence[Mapping[str, Any]], *, expected_count: int = EXPECTED_CROSSFIT_SCOPES
) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"R4 cross-fit scope count {len(rows)} != {expected_count}")
    scopes = {(row.get("task"), row.get("fold")) for row in rows}
    if len(scopes) != expected_count:
        raise ValueError("R4 cross-fit scopes are not unique")
    for row in rows:
        blocks = row.get("blocks", [])
        if len(blocks) != 5 or any(len(block) != 2 for block in blocks):
            raise ValueError("R4 cross-fit assignment is not 5x2")
        flattened = [subject for block in blocks for subject in block]
        if len(set(flattened)) != 10:
            raise ValueError("R4 cross-fit subjects are not unique")
        if row.get("block_assignment_source") != "fit_subject_ids_only":
            raise ValueError("R4 block assignment used a forbidden scope")
        if row.get("heldout_subject_overlap_max") != 0:
            raise ValueError("R4 held-out subject entered a nuisance fit")
        if row.get("oof_row_coverage_min") != 1 or row.get("oof_row_coverage_max") != 1:
            raise ValueError("R4 each fit row must receive exactly one OOF residual")
        required_true = (
            "m_y_shared_across_arms",
            "m_x_arm_symmetric_scope_capacity_algorithm",
            "residual_probe_840d_without_h",
            "same_rows_all_four_arms",
        )
        if any(row.get(key) is not True for key in required_true):
            raise ValueError("R4 cross-fit symmetry or residual probe contract failed")
        required_false = (
            "seen_cross_block_fit_support_normalizer_or_statistics_use",
            "subject_item_task_sham_label_model_input",
            "fallback_used",
        )
        if any(row.get(key) is not False for key in required_false):
            raise ValueError("R4 forbidden cross-fit input or fallback detected")


def validate_nuisance_ledgers(
    rows: Sequence[Mapping[str, Any]], *, expected_count: int = EXPECTED_NUISANCE_LEDGERS
) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"R4 nuisance ledger count {len(rows)} != {expected_count}")
    operation_ids = [str(row.get("operation_id")) for row in rows]
    if len(set(operation_ids)) != expected_count:
        raise ValueError("R4 nuisance operation IDs are not unique")
    for row in rows:
        heldout = set(map(str, row.get("heldout_subjects", [])))
        train = set(map(str, row.get("train_subjects", [])))
        if heldout & train or row.get("heldout_subject_overlap") != 0:
            raise ValueError("R4 nuisance ledger has held-out subject overlap")
        if row.get("alpha") != 1.0 or row.get("fallback_used") is not False:
            raise ValueError("R4 nuisance alpha/fallback contract failed")
        if row.get("model_input_role") != "H_full":
            raise ValueError("R4 nuisance model input is not H only")
        role = row.get("model_target_role")
        if role == "Y0_RAW_MINILM":
            if row.get("arm") is not None or row.get("target_dimension") != 384:
                raise ValueError("R4 mY arm/capacity contract failed")
        elif role == "matching_arm_EEG":
            if row.get("arm") not in ARMS or row.get("target_dimension") != 840:
                raise ValueError("R4 mX arm/capacity contract failed")
        else:
            raise ValueError("R4 nuisance target role changed")
        if row.get("seen_cross_reads") != 0:
            raise ValueError("R4 nuisance ledger contains seen/cross reads")
        if row.get("outer_test_reads") != 0 or row.get("calibration_reads") != 0:
            raise ValueError("R4 nuisance ledger contains forbidden reads")
        for key in (
            "fit_record_ids_sha256",
            "fit_observation_ids_sha256",
            "symmetric_scope_sha256",
        ):
            value = row.get(key)
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError(f"R4 nuisance ledger missing {key}")


def validate_operation_contract(
    operations: Sequence[Mapping[str, Any]],
    final_ledgers: Sequence[Mapping[str, Any]],
    nuisance_ledgers: Sequence[Mapping[str, Any]],
) -> None:
    expected = {
        "P0_H_ONLY": EXPECTED_P0_H_ONLY,
        "P0_JOINT_PROBE": EXPECTED_P0_JOINT,
        "C1_OOF_Y_NUISANCE": EXPECTED_C1_OOF_Y,
        "C1_OOF_X_NUISANCE": EXPECTED_C1_OOF_X,
        "C1_FULL_Y_NUISANCE": EXPECTED_C1_FULL_Y,
        "C1_FULL_X_NUISANCE": EXPECTED_C1_FULL_X,
        "C1_RESIDUAL_PROBE": EXPECTED_C1_RESIDUAL_PROBES,
    }
    if len(operations) != EXPECTED_RIDGE_OPERATIONS:
        raise ValueError("R4 ridge operation count changed")
    operation_ids = [str(row.get("operation_id")) for row in operations]
    if len(set(operation_ids)) != EXPECTED_RIDGE_OPERATIONS:
        raise ValueError("R4 ridge operation IDs are not unique")
    observed = {
        kind: sum(row.get("operation_kind") == kind for row in operations)
        for kind in expected
    }
    if observed != expected:
        raise ValueError(f"R4 operation breakdown changed: {observed}")
    residual_operations = [
        row for row in operations if row.get("operation_kind") == "C1_RESIDUAL_PROBE"
    ]
    if any(
        row.get("input_role") != "EEG_residual_840D_only"
        or row.get("input_dimension") != 840
        or row.get("target_dimension") != 384
        for row in residual_operations
    ):
        raise ValueError("R4 residual probe contains H or changed capacity")
    if len(final_ledgers) != EXPECTED_FINAL_V5_LEDGERS:
        raise ValueError("R4 final-scoring V5 ledger count changed")
    if len({str(row.get("fit_id")) for row in final_ledgers}) != EXPECTED_FINAL_V5_LEDGERS:
        raise ValueError("R4 final-scoring V5 fit IDs are not unique")
    for row in final_ledgers:
        if row.get("outer_test_record_ids_read") != [] or row.get("calibration_record_ids") != []:
            raise ValueError("R4 final-scoring V5 contains forbidden reads")
        scope = row.get("r4_scope", {})
        if scope.get("operation_kind") == "C1_RESIDUAL_PROBE" and (
            scope.get("input_role") != "EEG_residual_840D_only"
            or scope.get("input_dimension") != 840
            or scope.get("residual_probe_contains_h") is not False
        ):
            raise ValueError("R4 final ledger residual probe contains H")
    validate_nuisance_ledgers(nuisance_ledgers)
    all_ids = {str(row.get("fit_id")) for row in final_ledgers} | {
        str(row.get("operation_id")) for row in nuisance_ledgers
    }
    if len(all_ids) != EXPECTED_RIDGE_OPERATIONS:
        raise ValueError("R4 final/nuisance operation IDs overlap")


def evaluate_r4_outcome(
    results: Mapping[str, Any], *, contract_pass: bool
) -> tuple[str, list[str], list[str]]:
    if not contract_pass:
        return (
            "INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC",
            [],
            ["CROSSFIT_SYMMETRY_OPERATION_LEDGER_READ_HASH_OR_TEST_CONTRACT_FAILED"],
        )
    passing_tasks: list[str] = []
    for task in TASKS:
        baseline = results[task][BASELINE_METHOD]["cross"]
        candidate = results[task][CANDIDATE_METHOD]
        recovery = paired_cross_recovery(
            candidate["cross"], baseline, task=task, candidate_id=CANDIDATE_METHOD
        )
        passed = (
            candidate["cross"]["family_detected"]
            and recovery["ci95"][0] > 0.0
            and recovery["positive_subject_count"] >= 10
        )
        candidate["cross_recovery"] = recovery
        candidate["recovery_pass"] = bool(passed)
        results[task][BASELINE_METHOD]["cross_recovery"] = None
        results[task][BASELINE_METHOD]["recovery_pass"] = False
        if passed:
            passing_tasks.append(task)
    if len(passing_tasks) == 2:
        return "PASS_R4_ORTHOGONAL_BOTH_TASKS", passing_tasks, []
    if len(passing_tasks) == 1:
        return "PASS_R4_ORTHOGONAL_LIMITED_ONE_TASK", passing_tasks, []
    return "FAIL_R4_ORTHOGONAL_INNER_DIAGNOSTIC", [], []


__all__ = [
    "ALIGNMENT",
    "ALGORITHM_VERSION",
    "ARMS",
    "BASELINE_METHOD",
    "BASIS",
    "CANDIDATE_METHOD",
    "EXPECTED_C1_FULL_X",
    "EXPECTED_C1_FULL_Y",
    "EXPECTED_C1_OOF_X",
    "EXPECTED_C1_OOF_Y",
    "EXPECTED_C1_RESIDUAL_PROBES",
    "EXPECTED_CROSSFIT_SCOPES",
    "EXPECTED_FINAL_V5_LEDGERS",
    "EXPECTED_NUISANCE_LEDGERS",
    "EXPECTED_P0_H_ONLY",
    "EXPECTED_P0_JOINT",
    "EXPECTED_RIDGE_OPERATIONS",
    "FOLDS",
    "METRICS",
    "METHODS",
    "REGIMES",
    "RUN_ID",
    "TARGET",
    "TASKS",
    "canonical_hash",
    "evaluate_r4_outcome",
    "orthogonal_query",
    "residual_summary",
    "ridge_predict",
    "subject_blocks",
    "summarize_subject_first",
    "validate_crossfit_audits",
    "validate_nuisance_ledgers",
    "validate_operation_contract",
    "validate_r4_formal_output",
    "verify_immutable_parent_r0_r1_r2_r3",
]
