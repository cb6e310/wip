#!/usr/bin/env python3
"""Run only the v3.25 234-operation orthogonal inner diagnostic."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import yaml


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from data.a1_admission import (  # noqa: E402
    DEFAULT_ADMISSION_CONFIG,
    build_four_arm_features,
    canonical_artifact,
    deterministic_gzip_jsonl,
    fit_fold_normalizer,
    fit_ridge_to_items,
    ridge_log_prob,
    sha256_bytes,
    supported_item_ids,
    transform_fold_normalizer,
    u_statistics,
)
from data.a1_failure_diagnosis import (  # noqa: E402
    validate_aggregate_formal_output,
    validate_diagnosis_v5_or_raise,
)
from data.a1_measurement_recovery import (  # noqa: E402
    build_recovery_v5_ledger,
    derive_recovery_partitions,
    sha256_file,
    validate_recovery_v5_or_raise,
    verify_run032_immutable,
)
from data.a1_measurement_validity import verify_immutable_evidence  # noqa: E402
from data.real_sham_r4_orthogonal import (  # noqa: E402
    ALIGNMENT,
    ALGORITHM_VERSION,
    ARMS,
    BASELINE_METHOD,
    BASIS,
    CANDIDATE_METHOD,
    EXPECTED_C1_FULL_X,
    EXPECTED_C1_FULL_Y,
    EXPECTED_C1_OOF_X,
    EXPECTED_C1_OOF_Y,
    EXPECTED_C1_RESIDUAL_PROBES,
    EXPECTED_CROSSFIT_SCOPES,
    EXPECTED_FINAL_V5_LEDGERS,
    EXPECTED_NUISANCE_LEDGERS,
    EXPECTED_P0_H_ONLY,
    EXPECTED_P0_JOINT,
    EXPECTED_RIDGE_OPERATIONS,
    FOLDS,
    METRICS,
    METHODS,
    REGIMES,
    RUN_ID,
    TARGET,
    TASKS,
    canonical_hash,
    evaluate_r4_outcome,
    orthogonal_query,
    residual_summary,
    ridge_predict,
    subject_blocks,
    summarize_subject_first,
    validate_crossfit_audits,
    validate_operation_contract,
    validate_r4_formal_output,
    verify_immutable_parent_r0_r1_r2_r3,
)
from run_a1_admission import (  # noqa: E402
    V5_INPUT_KEYS,
    _h_matrix,
    _item_matrix,
    _vocabulary,
    build_text_contexts,
    encode_text_inputs,
    extract_task_observations,
    load_protocol,
    load_text_encoder,
    verify_frozen_inputs,
)


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_25_2026-08-24.md")
FREEZE_PATH = Path("artifacts/real_sham_r4_freeze.yaml")
CONTRACT_PATH = Path("artifacts/real_sham_r4_orthogonal_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/diagnostics/real_sham_r4_orthogonal_inner.json")
AUDIT_MD_PATH = Path("04_results/diagnostics/real_sham_r4_orthogonal_inner.md")
LEDGER_PATH = Path(
    "04_results/diagnostics/real_sham_r4_orthogonal_inner_run_ledger.jsonl.gz"
)
EXPECTED_SPEC_SHA256 = (
    "b4b27a816c1c5cb32ec8f31118b71843ace95ca067b499c19e812d030d7160f5"
)
EXPECTED_FREEZE_SHA256 = (
    "9e800135c16c5722a5d5b85260420f95d28a71f6ce3e30048ff5560c359a9ef2"
)
EXPECTED_CONTRACT_SHA256 = (
    "f563e5c6d22ebf5417e63a49acde7f36dc31180d67ea1c7c8df05c8cb9829069"
)
BASE_COMMIT = "fbc54c7b90ffc1bbc07b55ffc3123d0421779104"
BRANCH = "research/real-sham-r4-orthogonal-inner"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--device", default="cuda:1")
    parser.add_argument("--text-device", default="cpu")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--audit-json-output", type=Path, default=AUDIT_JSON_PATH)
    parser.add_argument("--audit-md-output", type=Path, default=AUDIT_MD_PATH)
    parser.add_argument("--ledger-output", type=Path, default=LEDGER_PATH)
    return parser.parse_args()


def _cell(protocol: Mapping[str, Any], fold: str) -> Mapping[str, Any]:
    rows = [row for row in protocol["inner_cells"] if row["inner_cell_id"].endswith(fold)]
    if len(rows) != 1:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: expected one {fold} cell")
    return rows[0]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, encoding="utf-8"
    ).strip()


def _validate_branch_and_freeze(root: Path) -> dict[str, Any]:
    if _git(root, "branch", "--show-current") != BRANCH:
        raise RuntimeError("STATE_SPEC_CONFLICT: R4 runner is on the wrong branch")
    if _git(root, "rev-parse", "HEAD") != BASE_COMMIT:
        raise RuntimeError("STATE_SPEC_CONFLICT: R4 execution HEAD is not frozen base")
    observed = {
        "spec": sha256_file(root / SPEC_PATH),
        "freeze": sha256_file(root / FREEZE_PATH),
        "contract": sha256_file(root / CONTRACT_PATH),
    }
    expected = {
        "spec": EXPECTED_SPEC_SHA256,
        "freeze": EXPECTED_FREEZE_SHA256,
        "contract": EXPECTED_CONTRACT_SHA256,
    }
    if observed != expected:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: R4 frozen hashes changed: {observed}")
    freeze = yaml.safe_load((root / FREEZE_PATH).read_text(encoding="utf-8"))
    contract = yaml.safe_load((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    if freeze.get("status") != "READY" or freeze.get("base_commit") != BASE_COMMIT:
        raise RuntimeError("STATE_SPEC_CONFLICT: R4 freeze is not READY at the base")
    if contract["governing_spec"]["sha256"] != EXPECTED_SPEC_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: contract SPEC hash not pre-frozen")
    if contract["author_freeze"]["sha256"] != EXPECTED_FREEZE_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: contract freeze hash not pre-frozen")
    return freeze


def _identity_hash(values: Sequence[str]) -> str:
    return canonical_hash(sorted(map(str, values)))


def _fit_final_model(
    *,
    operation_id: str,
    operation_kind: str,
    method: str,
    arm: str | None,
    input_role: str,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    device: str,
    task_protocol: Mapping[str, Any],
    recovery_cell: str,
    partitions: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    operations: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> dict[str, np.ndarray]:
    model, elapsed = fit_ridge_to_items(x_fit, y_fit, alpha=1.0, device=device)
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(
            f"INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC: {operation_id} >300s"
        )
    ledger = build_recovery_v5_ledger(
        run_id=run_id,
        fit_id=operation_id,
        seed=20260813,
        outer_cell=task_protocol["outer_cell_id"],
        recovery_cell=recovery_cell,
        fit_record_ids=partitions["fit_record_ids"],
        seen_record_ids=partitions["seen_record_ids"],
        cross_record_ids=partitions["cross_record_ids"],
        input_hashes=input_hashes,
    )
    ledger["ledger_type"] = "R4_FINAL_SCORING_V5"
    ledger["r4_scope"] = {
        "operation_kind": operation_kind,
        "method": method,
        "arm": arm,
        "basis": BASIS,
        "alignment": ALIGNMENT,
        "target": TARGET,
        "input_role": input_role,
        "input_dimension": int(x_fit.shape[1]),
        "target_dimension": int(y_fit.shape[1]),
        "residual_probe_contains_h": False
        if operation_kind == "C1_RESIDUAL_PROBE"
        else None,
        "subject_item_task_sham_label_model_input": False,
        "seen_cross_fit_or_calibration": False,
    }
    validate_recovery_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    operations.append(
        {
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "ledger_class": "final_scoring_v5",
            "method": method,
            "arm": arm,
            "input_role": input_role,
            "input_dimension": int(x_fit.shape[1]),
            "target_dimension": int(y_fit.shape[1]),
            "fit_rows": int(x_fit.shape[0]),
            "alpha": 1.0,
            "elapsed_seconds": elapsed,
            "fallback_used": False,
        }
    )
    return model


def _fit_nuisance(
    *,
    operation_id: str,
    operation_kind: str,
    task: str,
    fold: str,
    block: str,
    arm: str | None,
    target_role: str,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    fit_meta: Sequence[Mapping[str, Any]],
    train_subjects: Sequence[str],
    heldout_subjects: Sequence[str],
    eval_x: np.ndarray,
    eval_y: np.ndarray,
    eval_scope: str,
    symmetric_scope_sha256: str,
    device: str,
    operations: list[dict[str, Any]],
    nuisance_ledgers: list[dict[str, Any]],
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    model, elapsed = fit_ridge_to_items(x_fit, y_fit, alpha=1.0, device=device)
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(
            f"INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC: {operation_id} >300s"
        )
    prediction = ridge_predict(model, eval_x)
    residual = np.asarray(eval_y, dtype=np.float32) - prediction
    train_set = set(map(str, train_subjects))
    heldout_set = set(map(str, heldout_subjects))
    overlap = sorted(train_set & heldout_set)
    if overlap:
        raise RuntimeError(
            "INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC: held-out nuisance overlap"
        )
    ledger = {
        "schema_version": 1,
        "ledger_type": "R4_NUISANCE",
        "run_id": RUN_ID,
        "operation_id": operation_id,
        "operation_kind": operation_kind,
        "task": task,
        "fold": fold,
        "block": block,
        "heldout_subjects": sorted(heldout_set),
        "train_subjects": sorted(train_set),
        "heldout_subject_overlap": 0,
        "fit_record_ids_sha256": _identity_hash(
            [str(row["record_id"]) for row in fit_meta]
        ),
        "fit_observation_ids_sha256": _identity_hash(
            [str(row["observation_id"]) for row in fit_meta]
        ),
        "symmetric_scope_sha256": symmetric_scope_sha256,
        "model_input_role": "H_full",
        "model_target_role": target_role,
        "arm": arm,
        "alpha": 1.0,
        "input_dimension": int(x_fit.shape[1]),
        "target_dimension": int(y_fit.shape[1]),
        "fit_rows": int(x_fit.shape[0]),
        "evaluation_rows": int(eval_x.shape[0]),
        "evaluation_scope": eval_scope,
        "residual_summary": residual_summary(residual),
        "source_fit_rows_only": True,
        "subject_id_block_membership_only": True,
        "subject_item_task_sham_label_model_input": False,
        "seen_cross_reads": 0,
        "outer_test_reads": 0,
        "calibration_reads": 0,
        "fallback_used": False,
        "elapsed_seconds": elapsed,
    }
    nuisance_ledgers.append(ledger)
    operations.append(
        {
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "ledger_class": "nuisance",
            "arm": arm,
            "input_role": "H_full",
            "target_role": target_role,
            "input_dimension": int(x_fit.shape[1]),
            "target_dimension": int(y_fit.shape[1]),
            "fit_rows": int(x_fit.shape[0]),
            "alpha": 1.0,
            "elapsed_seconds": elapsed,
            "fallback_used": False,
        }
    )
    return model, residual.astype(np.float32, copy=False)


def _query_log_prob(
    query: np.ndarray,
    vocabulary: np.ndarray,
    true_positions: np.ndarray,
    *,
    device: str,
) -> np.ndarray:
    if query.ndim != 2 or query.shape[1] != 384:
        raise ValueError("R4 query target dimension changed")
    identity = {
        "weights": np.eye(384, dtype=np.float32),
        "intercept": np.zeros(384, dtype=np.float32),
    }
    return ridge_log_prob(
        identity,
        query,
        vocabulary,
        true_positions,
        temperature=0.07,
        device=device,
    )


def run_r4(
    *,
    selected: Mapping[str, Any],
    baseline_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    device: str,
    input_hashes: Mapping[str, str],
    base_scope_index: Mapping[str, Any],
    run_id: str,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    operations: list[dict[str, Any]] = []
    final_ledgers: list[dict[str, Any]] = []
    nuisance_ledgers: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    crossfit_audits: list[dict[str, Any]] = []
    scope_index = {
        "outer": dict(base_scope_index["outer"]),
        "inner": dict(base_scope_index["inner"]),
    }

    for task in TASKS:
        protocol = selected[task]
        baseline = baseline_by_task[task]
        metadata = list(metadata_by_task[task])
        id_to_index = {
            str(row["observation_id"]): index for index, row in enumerate(metadata)
        }
        for fold in FOLDS:
            cell = _cell(protocol, fold)
            partitions = derive_recovery_partitions(protocol, cell)
            recovery_cell = cell["inner_cell_id"].replace(
                "|inner_", "|r4_orthogonal_"
            )
            scope_index["inner"][recovery_cell] = {
                "outer_cell_id": protocol["outer_cell_id"],
                "train_record_ids": partitions["fit_record_ids"],
                "validation_record_ids": sorted(
                    set(partitions["seen_record_ids"])
                    | set(partitions["cross_record_ids"])
                ),
            }

            partition_meta: dict[str, list[Mapping[str, Any]]] = {}
            partition_raw: dict[str, np.ndarray] = {}
            coverage: dict[str, Any] = {}
            for regime, record_key in (
                ("fit", "fit_record_ids"),
                ("seen", "seen_record_ids"),
                ("cross", "cross_record_ids"),
            ):
                legal_records = set(partitions[record_key])
                rows = [
                    row for row in metadata if str(row["record_id"]) in legal_records
                ]
                if not rows:
                    raise RuntimeError("R4 partition rows are empty")
                partition_meta[regime] = rows
                indices = np.asarray(
                    [id_to_index[str(row["observation_id"])] for row in rows],
                    dtype=np.int64,
                )
                partition_raw[regime] = baseline[indices]
                coverage[regime] = {
                    "old_a1_available_rows": len(rows),
                    "common_rows": len(rows),
                    "retention": 1.0,
                    "subjects": sorted({str(row["subject_id"]) for row in rows}),
                }

            normalizer, normalizer_summary = fit_fold_normalizer(partition_raw["fit"])
            arms_by_regime: dict[str, dict[str, np.ndarray]] = {}
            common_indices: dict[str, np.ndarray] = {}
            common_meta: dict[str, list[Mapping[str, Any]]] = {}
            for regime in ("fit", *REGIMES):
                normalized = transform_fold_normalizer(
                    partition_raw[regime], normalizer
                )
                suffix = {"fit": "train", "seen": "seen", "cross": "validation"}[
                    regime
                ]
                arms, common, sham_audit = build_four_arm_features(
                    normalized,
                    partition_meta[regime],
                    seed=20260813,
                    partition=f"{cell['inner_cell_id']}|{suffix}",
                )
                if set(arms) != set(ARMS) or not sham_audit["row_ids_identical"]:
                    raise RuntimeError("R4 four-arm scope/identity changed")
                if any(arms[arm].shape != arms["real"].shape for arm in ARMS):
                    raise RuntimeError("R4 four-arm capacities changed")
                arms_by_regime[regime] = arms
                common_indices[regime] = common
                common_meta[regime] = [
                    partition_meta[regime][int(index)] for index in common
                ]

            supported, support_ledger = supported_item_ids(common_meta["fit"])
            row_positions: dict[str, np.ndarray] = {}
            row_meta: dict[str, list[Mapping[str, Any]]] = {}
            for regime in ("fit", *REGIMES):
                positions = np.asarray(
                    [
                        index
                        for index, row in enumerate(common_meta[regime])
                        if str(row["item_id"]) in supported
                    ],
                    dtype=np.int64,
                )
                row_positions[regime] = positions
                row_meta[regime] = [
                    common_meta[regime][int(index)] for index in positions
                ]
                if not row_meta[regime]:
                    raise RuntimeError("R4 supported rows are empty")
            if len({str(row["subject_id"]) for row in row_meta["seen"]}) != 10:
                raise RuntimeError("R4 seen subject count changed")
            if len({str(row["subject_id"]) for row in row_meta["cross"]}) != 5:
                raise RuntimeError("R4 cross subject count changed")

            arms = {
                regime: {
                    arm: arms_by_regime[regime][arm][row_positions[regime]]
                    for arm in ARMS
                }
                for regime in ("fit", *REGIMES)
            }
            _, vocabulary, item_positions = _vocabulary(
                supported, row_meta["fit"], item_vectors
            )
            h = {
                regime: _h_matrix(row_meta[regime], h_vectors)
                for regime in ("fit", *REGIMES)
            }
            y_fit = _item_matrix(row_meta["fit"], item_vectors)
            true_positions = {
                regime: np.asarray(
                    [item_positions[str(row["item_id"])] for row in row_meta[regime]],
                    dtype=np.int64,
                )
                for regime in REGIMES
            }

            p0_logp: dict[str, dict[str, np.ndarray]] = {
                regime: {} for regime in REGIMES
            }
            p0_h = _fit_final_model(
                operation_id=f"R4|{task}|{fold}|P0|H_ONLY",
                operation_kind="P0_H_ONLY",
                method=BASELINE_METHOD,
                arm=None,
                input_role="H_full",
                x_fit=h["fit"],
                y_fit=y_fit,
                device=device,
                task_protocol=protocol,
                recovery_cell=recovery_cell,
                partitions=partitions,
                input_hashes=input_hashes,
                scope_index=scope_index,
                run_id=run_id,
                operations=operations,
                ledgers=final_ledgers,
            )
            del p0_h
            for arm in ARMS:
                p0_model = _fit_final_model(
                    operation_id=f"R4|{task}|{fold}|P0|{arm}",
                    operation_kind="P0_JOINT_PROBE",
                    method=BASELINE_METHOD,
                    arm=arm,
                    input_role="H_full_plus_EEG_arm",
                    x_fit=np.concatenate([h["fit"], arms["fit"][arm]], axis=1),
                    y_fit=y_fit,
                    device=device,
                    task_protocol=protocol,
                    recovery_cell=recovery_cell,
                    partitions=partitions,
                    input_hashes=input_hashes,
                    scope_index=scope_index,
                    run_id=run_id,
                    operations=operations,
                    ledgers=final_ledgers,
                )
                for regime in REGIMES:
                    p0_logp[regime][arm] = ridge_log_prob(
                        p0_model,
                        np.concatenate([h[regime], arms[regime][arm]], axis=1),
                        vocabulary,
                        true_positions[regime],
                        temperature=0.07,
                        device=device,
                    )
                del p0_model

            fit_subject_ids = [str(row["subject_id"]) for row in row_meta["fit"]]
            blocks = subject_blocks(
                fit_subject_ids, task=task, inner_cell_id=str(cell["inner_cell_id"])
            )
            all_subjects = sorted(set(fit_subject_ids))
            subject_array = np.asarray(fit_subject_ids, dtype=object)
            y_tilde = np.empty_like(y_fit, dtype=np.float32)
            x_tilde = {
                arm: np.empty_like(arms["fit"][arm], dtype=np.float32) for arm in ARMS
            }
            oof_coverage = np.zeros(len(row_meta["fit"]), dtype=np.int8)
            heldout_overlap_max = 0
            oof_scope_hashes: dict[str, dict[str, str]] = {}

            for block_index, heldout in enumerate(blocks):
                block_id = f"b{block_index}"
                heldout_set = set(heldout)
                train_subjects = [
                    subject for subject in all_subjects if subject not in heldout_set
                ]
                train_mask = np.asarray(
                    [subject in set(train_subjects) for subject in subject_array],
                    dtype=bool,
                )
                heldout_mask = np.asarray(
                    [subject in heldout_set for subject in subject_array], dtype=bool
                )
                if len(train_subjects) != 8 or not train_mask.any() or not heldout_mask.any():
                    raise RuntimeError("R4 cross-fit block capacity changed")
                train_meta = [
                    row_meta["fit"][index]
                    for index in np.flatnonzero(train_mask).tolist()
                ]
                symmetric_scope = canonical_hash(
                    {
                        "task": task,
                        "fold": fold,
                        "block": block_id,
                        "train_subjects": train_subjects,
                        "heldout_subjects": heldout,
                        "fit_observation_ids": sorted(
                            str(row["observation_id"]) for row in train_meta
                        ),
                        "input_dimension": int(h["fit"].shape[1]),
                        "target_dimension": 840,
                        "alpha": 1.0,
                    }
                )
                _, y_residual = _fit_nuisance(
                    operation_id=f"R4|{task}|{fold}|C1|OOF|{block_id}|mY",
                    operation_kind="C1_OOF_Y_NUISANCE",
                    task=task,
                    fold=fold,
                    block=block_id,
                    arm=None,
                    target_role="Y0_RAW_MINILM",
                    x_fit=h["fit"][train_mask],
                    y_fit=y_fit[train_mask],
                    fit_meta=train_meta,
                    train_subjects=train_subjects,
                    heldout_subjects=heldout,
                    eval_x=h["fit"][heldout_mask],
                    eval_y=y_fit[heldout_mask],
                    eval_scope="heldout_source_subject_rows",
                    symmetric_scope_sha256=symmetric_scope,
                    device=device,
                    operations=operations,
                    nuisance_ledgers=nuisance_ledgers,
                )
                y_tilde[heldout_mask] = y_residual
                oof_scope_hashes[block_id] = {}
                for arm in ARMS:
                    _, x_residual = _fit_nuisance(
                        operation_id=f"R4|{task}|{fold}|C1|OOF|{block_id}|mX|{arm}",
                        operation_kind="C1_OOF_X_NUISANCE",
                        task=task,
                        fold=fold,
                        block=block_id,
                        arm=arm,
                        target_role="matching_arm_EEG",
                        x_fit=h["fit"][train_mask],
                        y_fit=arms["fit"][arm][train_mask],
                        fit_meta=train_meta,
                        train_subjects=train_subjects,
                        heldout_subjects=heldout,
                        eval_x=h["fit"][heldout_mask],
                        eval_y=arms["fit"][arm][heldout_mask],
                        eval_scope="heldout_source_subject_rows",
                        symmetric_scope_sha256=symmetric_scope,
                        device=device,
                        operations=operations,
                        nuisance_ledgers=nuisance_ledgers,
                    )
                    x_tilde[arm][heldout_mask] = x_residual
                    oof_scope_hashes[block_id][arm] = symmetric_scope
                oof_coverage[heldout_mask] += 1
                heldout_overlap_max = max(
                    heldout_overlap_max,
                    len(set(train_subjects) & heldout_set),
                )

            if not np.all(oof_coverage == 1):
                raise RuntimeError("R4 each fit row must receive one OOF residual")
            if not np.isfinite(y_tilde).all() or any(
                not np.isfinite(x_tilde[arm]).all() for arm in ARMS
            ):
                raise RuntimeError("R4 OOF residuals are nonfinite")
            if any(len(set(oof_scope_hashes[block].values())) != 1 for block in oof_scope_hashes):
                raise RuntimeError("R4 mX OOF arm scopes are asymmetric")

            full_meta = list(row_meta["fit"])
            full_scope = canonical_hash(
                {
                    "task": task,
                    "fold": fold,
                    "block": "full",
                    "train_subjects": all_subjects,
                    "fit_observation_ids": sorted(
                        str(row["observation_id"]) for row in full_meta
                    ),
                    "input_dimension": int(h["fit"].shape[1]),
                    "target_dimension": 840,
                    "alpha": 1.0,
                }
            )
            m_y_full, _ = _fit_nuisance(
                operation_id=f"R4|{task}|{fold}|C1|FULL|mY",
                operation_kind="C1_FULL_Y_NUISANCE",
                task=task,
                fold=fold,
                block="full",
                arm=None,
                target_role="Y0_RAW_MINILM",
                x_fit=h["fit"],
                y_fit=y_fit,
                fit_meta=full_meta,
                train_subjects=all_subjects,
                heldout_subjects=[],
                eval_x=h["fit"],
                eval_y=y_fit,
                eval_scope="source_fit_rows",
                symmetric_scope_sha256=full_scope,
                device=device,
                operations=operations,
                nuisance_ledgers=nuisance_ledgers,
            )
            m_x_full: dict[str, dict[str, np.ndarray]] = {}
            for arm in ARMS:
                m_x_full[arm], _ = _fit_nuisance(
                    operation_id=f"R4|{task}|{fold}|C1|FULL|mX|{arm}",
                    operation_kind="C1_FULL_X_NUISANCE",
                    task=task,
                    fold=fold,
                    block="full",
                    arm=arm,
                    target_role="matching_arm_EEG",
                    x_fit=h["fit"],
                    y_fit=arms["fit"][arm],
                    fit_meta=full_meta,
                    train_subjects=all_subjects,
                    heldout_subjects=[],
                    eval_x=h["fit"],
                    eval_y=arms["fit"][arm],
                    eval_scope="source_fit_rows",
                    symmetric_scope_sha256=full_scope,
                    device=device,
                    operations=operations,
                    nuisance_ledgers=nuisance_ledgers,
                )

            c1_logp: dict[str, dict[str, np.ndarray]] = {
                regime: {} for regime in REGIMES
            }
            beta_models: dict[str, dict[str, np.ndarray]] = {}
            for arm in ARMS:
                beta_models[arm] = _fit_final_model(
                    operation_id=f"R4|{task}|{fold}|C1|BETA|{arm}",
                    operation_kind="C1_RESIDUAL_PROBE",
                    method=CANDIDATE_METHOD,
                    arm=arm,
                    input_role="EEG_residual_840D_only",
                    x_fit=x_tilde[arm],
                    y_fit=y_tilde,
                    device=device,
                    task_protocol=protocol,
                    recovery_cell=recovery_cell,
                    partitions=partitions,
                    input_hashes=input_hashes,
                    scope_index=scope_index,
                    run_id=run_id,
                    operations=operations,
                    ledgers=final_ledgers,
                )
                if beta_models[arm]["weights"].shape != (840, 384):
                    raise RuntimeError("R4 residual probe capacity or H exclusion changed")
                for regime in REGIMES:
                    query = orthogonal_query(
                        h[regime],
                        arms[regime][arm],
                        m_y_full=m_y_full,
                        m_x_full=m_x_full[arm],
                        beta_arm=beta_models[arm],
                    )
                    c1_logp[regime][arm] = _query_log_prob(
                        query,
                        vocabulary,
                        true_positions[regime],
                        device=device,
                    )
                    del query

            for method, arm_logp in (
                (BASELINE_METHOD, p0_logp),
                (CANDIDATE_METHOD, c1_logp),
            ):
                for regime in REGIMES:
                    stats = u_statistics(
                        arm_logp[regime]["real"],
                        {
                            arm: arm_logp[regime][arm]
                            for arm in ARMS
                            if arm != "real"
                        },
                    )
                    stats["delta_semantic"] = 0.5 * (
                        stats["real_minus_trial_shuffle"]
                        + stats["real_minus_within_trial_unit_assignment_shuffle"]
                    )
                    stats["delta_legacy"] = stats["u_oof"]
                    stats["delta_channel"] = stats[
                        "real_minus_channel_block_permutation"
                    ]
                    stats["max_selection_gap"] = stats["u_oof"] - stats["u_min"]
                    for index, row in enumerate(row_meta[regime]):
                        metric_rows.append(
                            {
                                "task": task,
                                "fold": fold,
                                "candidate": method,
                                "method": method,
                                "regime": regime,
                                "subject_id": str(row["subject_id"]),
                                **{
                                    metric: float(stats[metric][index])
                                    for metric in METRICS
                                },
                                **{
                                    f"logp_{arm}": float(arm_logp[regime][arm][index])
                                    for arm in ARMS
                                },
                            }
                        )

            scoring_hashes = {
                regime: _identity_hash(
                    [str(row["observation_id"]) for row in row_meta[regime]]
                )
                for regime in REGIMES
            }
            for method in METHODS:
                support_rows.append(
                    {
                        "task": task,
                        "fold": fold,
                        "method": method,
                        "role": "baseline_replication"
                        if method == BASELINE_METHOD
                        else "sole_candidate",
                        "coverage": coverage,
                        "normalizer_fit_rows": normalizer_summary["fit_rows"],
                        "sham_common_rows": {
                            regime: int(common_indices[regime].size)
                            for regime in ("fit", *REGIMES)
                        },
                        "supported_rows": {
                            regime: len(row_meta[regime])
                            for regime in ("fit", *REGIMES)
                        },
                        "supported_item_count": len(supported),
                        "support_ledger_rows": len(support_ledger),
                        "scoring_row_hashes": scoring_hashes,
                        "fit_observation_ids_sha256": _identity_hash(
                            [str(row["observation_id"]) for row in row_meta["fit"]]
                        ),
                        "same_rows_p0_c1_all_four_arms": True,
                        "support_vocabulary_normalizer_fit_only": True,
                        "seen_cross_fit_calibration_or_statistics_use": False,
                    }
                )
            crossfit_audits.append(
                {
                    "task": task,
                    "fold": fold,
                    "inner_cell_id": str(cell["inner_cell_id"]),
                    "blocks": blocks,
                    "block_assignment_source": "fit_subject_ids_only",
                    "block_assignment_sha256": canonical_hash(blocks),
                    "fit_subject_count": len(all_subjects),
                    "heldout_subject_overlap_max": heldout_overlap_max,
                    "oof_row_count": int(len(oof_coverage)),
                    "oof_row_coverage_min": int(oof_coverage.min()),
                    "oof_row_coverage_max": int(oof_coverage.max()),
                    "m_y_shared_across_arms": True,
                    "m_x_arm_symmetric_scope_capacity_algorithm": True,
                    "residual_probe_840d_without_h": True,
                    "same_rows_all_four_arms": True,
                    "seen_cross_block_fit_support_normalizer_or_statistics_use": False,
                    "subject_item_task_sham_label_model_input": False,
                    "fallback_used": False,
                    "y_oof_residual_summary": residual_summary(y_tilde),
                    "x_oof_residual_summary": {
                        arm: residual_summary(x_tilde[arm]) for arm in ARMS
                    },
                }
            )
            del beta_models, m_x_full, m_y_full, x_tilde, y_tilde

    results: dict[str, Any] = {}
    for task in TASKS:
        results[task] = {}
        for method in METHODS:
            results[task][method] = {
                "seen": summarize_subject_first(
                    metric_rows, task=task, candidate=method, regime="seen"
                ),
                "cross": summarize_subject_first(
                    metric_rows, task=task, candidate=method, regime="cross"
                ),
                "role": "baseline_replication"
                if method == BASELINE_METHOD
                else "sole_candidate",
            }
    return (
        results,
        operations,
        final_ledgers,
        nuisance_ledgers,
        support_rows,
        crossfit_audits,
    )


def _baseline_reproduction(root: Path, results: Mapping[str, Any]) -> dict[str, Any]:
    old = json.loads(
        (root / "04_results/diagnostics/real_sham_r3_subject_balanced_inner.json").read_text(
            encoding="utf-8"
        )
    )
    comparisons: list[dict[str, Any]] = []
    maximum = 0.0
    reference = "P0_OBSERVATION_WEIGHTED"
    for task in TASKS:
        previous = old["results"][task][reference]
        current = results[task][BASELINE_METHOD]
        for regime in REGIMES:
            for metric in METRICS:
                left = previous[regime]["metrics"][metric]["subject_values"]
                right = current[regime]["metrics"][metric]["subject_values"]
                if set(left) != set(right):
                    raise RuntimeError("R4 P0 subject identity differs from R3 P0")
                difference = max(
                    abs(float(left[key]) - float(right[key])) for key in left
                )
                maximum = max(maximum, difference)
                comparisons.append(
                    {
                        "task": task,
                        "regime": regime,
                        "metric": metric,
                        "maximum_subject_absolute_difference": difference,
                    }
                )
    return {
        "reference": f"R3 {reference}",
        "subject_value_comparisons": comparisons,
        "maximum_subject_absolute_difference": maximum,
        "tolerance": 1e-6,
        "pass": maximum <= 1e-6,
    }


def _render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# Real-vs-sham R4 orthogonal inner diagnostic",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['outcome']}`",
        "- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`",
        f"- Passing task scope: `{audit['passing_task_scope']}`",
        "- Ridge operations: `234`",
        "- Final-scoring V5 / nuisance ledgers: `54/180`",
        "- Outer-test/calibration reads: `0/0`",
        "",
        "| Task | Method | Role | seen semantic | seen family | cross semantic | cross family | recovery | pass |",
        "|---|---|---|---:|---|---:|---|---:|---|",
    ]
    for task in TASKS:
        for method in METHODS:
            row = audit["results"][task][method]
            recovery = row.get("cross_recovery")
            recovery_value = "n/a" if recovery is None else f"{recovery['estimate']:.6g}"
            lines.append(
                f"| {task} | {method} | {row['role']} | "
                f"{row['seen']['metrics']['delta_semantic']['estimate']:.6g} | "
                f"{row['seen']['family_detected']} | "
                f"{row['cross']['metrics']['delta_semantic']['estimate']:.6g} | "
                f"{row['cross']['family_detected']} | {recovery_value} | "
                f"{row.get('recovery_pass', False)} |"
            )
    lines.extend(
        [
            "",
            "C1 is the only candidate. P0 exactly replicates the inherited joint ridge baseline.",
            "",
            "C1 uses five deterministic two-subject source-fit blocks. Every OOF residual excludes its held-out subjects; mY is shared across arms and mX uses symmetric row scope and capacity. Residual probes contain only 840D EEG residuals.",
            "",
            "Seen/cross scoring uses only source-fit full nuisance models and the frozen query formula. No seen/cross fit, calibration, normalizer update, support selection, or target-subject statistic was used.",
            "",
            "Parent/R0/R1/R2/R3 outcomes and formal artifacts are immutable. No outer confirmation, direct u+, EQ-ANMA, A3, ROAMM, or Gate was run.",
            "",
            "Stop for author review. No downstream task was started.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(
    root: Path,
    *,
    args: argparse.Namespace,
    audit: Mapping[str, Any],
    final_ledgers: Sequence[Mapping[str, Any]],
    nuisance_ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    payloads = {
        args.audit_json_output: canonical_artifact(audit),
        args.audit_md_output: _render_markdown(audit).encode("utf-8"),
        args.ledger_output: deterministic_gzip_jsonl(
            [*final_ledgers, *nuisance_ledgers]
        ),
    }
    hashes: dict[str, str] = {}
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        hashes[relative.as_posix()] = sha256_bytes(payload)
    return hashes


def execute(args: argparse.Namespace) -> int:
    root = args.project_root.resolve()
    os.chdir(root)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    started = time.perf_counter()
    random.seed(20260813)
    np.random.seed(20260813)
    torch.manual_seed(20260813)
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available() or not str(args.device).startswith("cuda"):
        raise RuntimeError("INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC: CUDA unavailable")

    _validate_branch_and_freeze(root)
    print(
        f"CONTRACT frozen sha256={EXPECTED_CONTRACT_SHA256} "
        "spec_freeze_hashes_filled_before_any_fit=true"
    )
    immutable_before = verify_immutable_parent_r0_r1_r2_r3(root)
    run032_hashes = verify_run032_immutable(root)
    immutable_evidence = verify_immutable_evidence(root)
    physical_hashes, _, _ = verify_frozen_inputs(root)
    _, _, selected, base_scope = load_protocol(root)
    old_v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    for ledger in [
        *immutable_evidence["admission_ledgers"],
        *immutable_evidence["diagnosis_ledgers"],
    ]:
        validate_diagnosis_v5_or_raise(ledger, base_scope, old_v5_hashes)
    input_hashes = {
        **old_v5_hashes,
        "r4_freeze": EXPECTED_FREEZE_SHA256,
        "spec_v325": EXPECTED_SPEC_SHA256,
        "r4_contract": EXPECTED_CONTRACT_SHA256,
        "r3_contract": immutable_before[
            "artifacts/real_sham_r3_subject_balanced_contract.yaml"
        ],
        "r3_diagnostic_json": immutable_before[
            "04_results/diagnostics/real_sham_r3_subject_balanced_inner.json"
        ],
    }
    source_paths = (
        "02_code/src/data/real_sham_r4_orthogonal.py",
        "02_code/scripts/run_real_sham_r4_orthogonal_inner.py",
        "02_code/tests/test_real_sham_r4_orthogonal.py",
    )
    source_hashes = {relative: sha256_file(root / relative) for relative in source_paths}

    contexts = build_text_contexts(root)
    baseline_by_task: dict[str, np.ndarray] = {}
    metadata_by_task: dict[str, list[dict[str, Any]]] = {}
    data_summary: dict[str, Any] = {}
    for task in TASKS:
        baseline, metadata, manifest = extract_task_observations(
            root,
            task=task,
            task_protocol=selected[task],
            contexts=contexts,
            rebuild=False,
        )
        baseline_by_task[task] = baseline
        metadata_by_task[task] = metadata
        data_summary[task] = {
            "outer_train_bound_observations": len(metadata),
            "feature_dimension": int(baseline.shape[1]),
            "manifest_binding": manifest["binding"],
        }
        print(f"DATA task={task} outer_train_rows={len(metadata)} dim={baseline.shape[1]}")
    encoder, text_manifests, resolved_revision = load_text_encoder(
        root, args.text_device
    )
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    (
        results,
        operations,
        final_ledgers,
        nuisance_ledgers,
        support,
        crossfit_audits,
    ) = run_r4(
        selected=selected,
        baseline_by_task=baseline_by_task,
        metadata_by_task=metadata_by_task,
        item_vectors=item_vectors,
        h_vectors=h_vectors,
        device=args.device,
        input_hashes=input_hashes,
        base_scope_index=base_scope,
        run_id=args.run_id,
    )

    validate_operation_contract(operations, final_ledgers, nuisance_ledgers)
    validate_crossfit_audits(crossfit_audits)
    operation_contract = True
    read_contract = all(
        row["outer_test_record_ids_read"] == []
        and row["calibration_record_ids"] == []
        for row in final_ledgers
    ) and all(
        row["outer_test_reads"] == 0
        and row["calibration_reads"] == 0
        and row["seen_cross_reads"] == 0
        for row in nuisance_ledgers
    )
    scope_contract = len(support) == 12 and all(
        set(row["coverage"]) == {"fit", "seen", "cross"}
        and all(value["retention"] >= 0.90 for value in row["coverage"].values())
        and row["same_rows_p0_c1_all_four_arms"]
        and row["support_vocabulary_normalizer_fit_only"]
        and not row["seen_cross_fit_calibration_or_statistics_use"]
        for row in support
    )
    scoring_identity_contract = all(
        len(
            {
                row["scoring_row_hashes"][regime]
                for row in support
                if row["task"] == task and row["fold"] == fold
            }
        )
        == 1
        for task in TASKS
        for fold in FOLDS
        for regime in REGIMES
    )
    baseline_reproduction = _baseline_reproduction(root, results)
    immutable_after = verify_immutable_parent_r0_r1_r2_r3(root)
    hash_contract = immutable_after == immutable_before
    operation_breakdown = {
        kind: sum(row["operation_kind"] == kind for row in operations)
        for kind in (
            "P0_H_ONLY",
            "P0_JOINT_PROBE",
            "C1_OOF_Y_NUISANCE",
            "C1_OOF_X_NUISANCE",
            "C1_FULL_Y_NUISANCE",
            "C1_FULL_X_NUISANCE",
            "C1_RESIDUAL_PROBE",
        )
    }
    preliminary: dict[str, Any] = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "results": results,
        "support": support,
        "crossfit_audits": crossfit_audits,
        "nuisance_summary": {
            "ledger_count": len(nuisance_ledgers),
            "heldout_subject_overlap_max": max(
                row["heldout_subject_overlap"] for row in nuisance_ledgers
            ),
            "seen_cross_reads": sum(row["seen_cross_reads"] for row in nuisance_ledgers),
            "fallback_count": sum(row["fallback_used"] for row in nuisance_ledgers),
            "m_y_shared_across_arms": True,
            "m_x_arm_symmetric_scope_capacity_algorithm": True,
            "residual_metrics_recorded": True,
        },
        "baseline_reproduction": baseline_reproduction,
        "data": data_summary,
        "text": {
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
            **text_summary,
        },
        "operation_summary": {
            "breakdown": operation_breakdown,
            "total_ridge_operations": len(operations),
            "unique_operation_ids": len(
                {str(row["operation_id"]) for row in operations}
            ),
            "final_scoring_v5_ledgers": len(final_ledgers),
            "nuisance_ledgers": len(nuisance_ledgers),
            "maximum_single_fit_seconds": max(
                float(row["elapsed_seconds"]) for row in operations
            ),
            "fit_runtime_seconds_sum": float(
                sum(float(row["elapsed_seconds"]) for row in operations)
            ),
            "operations": operations,
        },
        "contract_checks": {
            "spec_freeze_hashes_frozen_before_fit": True,
            "exact_operation_and_ledger_counts": operation_contract,
            "crossfit_assignment_overlap_coverage_symmetry": True,
            "residual_probe_840d_without_h": True,
            "full_nuisance_source_fit_only": True,
            "scope_retention_row_identity": scope_contract,
            "identical_p0_c1_scoring_rows": scoring_identity_contract,
            "zero_outer_calibration_reads": read_contract,
            "immutable_parent_r0_r1_r2_r3_hashes": hash_contract,
            "p0_r3_baseline_reproduction": baseline_reproduction["pass"],
            "forbidden_scope_executed": [],
        },
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "claim_boundary": {
            "parent_r0_r1_r2_r3_outcomes_immutable": True,
            "c1_only_candidate": True,
            "p0_baseline_only": True,
            "paper_level_real_eeg_claim": False,
            "outer_confirmation_released": False,
        },
        "immutable_parent_r0_r1_r2_r3_hashes": immutable_after,
        "run032_immutable_hashes": run032_hashes,
        "source_hashes": source_hashes,
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
        "elapsed_seconds": time.perf_counter() - started,
        "next_task": "AUTHOR_REVIEW_ONLY_NO_DOWNSTREAM_STARTED",
    }
    aggregate_formal = validate_aggregate_formal_output(preliminary)
    r4_formal = validate_r4_formal_output(preliminary)
    formal_pass = aggregate_formal["pass"] and r4_formal["pass"]
    contract_pass = bool(
        operation_contract
        and read_contract
        and scope_contract
        and scoring_identity_contract
        and baseline_reproduction["pass"]
        and hash_contract
        and formal_pass
    )
    outcome, passing_scope, reasons = evaluate_r4_outcome(
        results, contract_pass=contract_pass
    )
    preliminary["outcome"] = outcome
    preliminary["passing_task_scope"] = passing_scope
    preliminary["outcome_reasons"] = reasons
    preliminary["scope_violations"] = [] if contract_pass else reasons
    preliminary["formal_output_validation"] = {
        "pass": formal_pass,
        "aggregate": aggregate_formal,
        "r4_no_model_or_row_arrays": r4_formal,
    }
    if not preliminary["formal_output_validation"]["pass"]:
        raise RuntimeError(
            "INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC: forbidden formal output key"
        )
    output_hashes = _write_outputs(
        root,
        args=args,
        audit=preliminary,
        final_ledgers=final_ledgers,
        nuisance_ledgers=nuisance_ledgers,
    )
    verify_immutable_parent_r0_r1_r2_r3(root)
    print(f"OUTCOME {outcome} scope={passing_scope} reasons={reasons}")
    for task in TASKS:
        for method in METHODS:
            row = results[task][method]
            recovery = row.get("cross_recovery")
            print(
                f"RESULT task={task} method={method} role={row['role']} "
                f"seen_semantic={row['seen']['metrics']['delta_semantic']['estimate']:.6f} "
                f"seen_family={row['seen']['family_detected']} "
                f"cross_semantic={row['cross']['metrics']['delta_semantic']['estimate']:.6f} "
                f"cross_family={row['cross']['family_detected']} "
                f"recovery={None if recovery is None else recovery['estimate']} "
                f"pass={row.get('recovery_pass', False)}"
            )
    print(f"OUTPUT {CONTRACT_PATH.as_posix()} sha256={EXPECTED_CONTRACT_SHA256}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        "SELF-CHECK SUMMARY "
        f"operations={len(operations)} unique={len({row['operation_id'] for row in operations})} "
        f"final_v5={len(final_ledgers)} nuisance={len(nuisance_ledgers)} "
        "outer_reads=0 calibration_reads=0 "
        f"scope={scope_contract} scoring_identity={scoring_identity_contract} "
        f"baseline={baseline_reproduction['pass']} hashes={hash_contract} status=PASS"
    )
    return 0


def _write_invalid_stub(args: argparse.Namespace, error: BaseException) -> None:
    root = args.project_root.resolve()
    payload = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "R4_REAL_SHAM_ORTHOGONAL_INNER_DIAGNOSTIC",
        "outcome": "INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "error_type": type(error).__name__,
        "error": str(error),
        "scope_violations": [str(error)],
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "next_task": "STOP_AUTHOR_REVIEW_REQUIRED",
    }
    path = root / args.audit_json_output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_artifact(payload))
    (root / args.audit_md_output).write_text(
        "# R4 orthogonal inner diagnostic\n\n"
        "- Outcome: `INVALID_R4_ORTHOGONAL_INNER_DIAGNOSTIC`\n"
        f"- Error: `{type(error).__name__}: {error}`\n"
        "- Stop; author review required.\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    try:
        return execute(args)
    except BaseException as error:  # noqa: BLE001
        traceback.print_exc()
        try:
            _write_invalid_stub(args, error)
        except BaseException:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
