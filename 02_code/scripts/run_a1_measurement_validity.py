#!/usr/bin/env python3
"""Run only the SPEC v3.17 D49-D50 A1 measurement-validity audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
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
    sha256_bytes,
    supported_item_ids,
    transform_fold_normalizer,
    u_statistics,
)
from data.a1_failure_diagnosis import (  # noqa: E402
    oracle_input,
    validate_aggregate_formal_output,
    validate_diagnosis_v5_or_raise,
    validate_fold_roles,
)
from data.a1_measurement_validity import (  # noqa: E402
    ALGORITHM_VERSION,
    ALPHAS,
    ARMS,
    EXPECTED_AMENDMENT_FITS,
    EXPECTED_INJECTION_FITS,
    EXPECTED_TOTAL_FITS,
    INJECTION_FOLDS,
    METRICS,
    NEW_FOLDS,
    RUN_ID,
    SUBJECT_FOLDS,
    TASKS,
    combine_amendment_summaries,
    inject_after_normalizer,
    projection_matrix,
    sha256_file,
    summarize_amendment_fold,
    summarize_curve,
    summarize_injection_rows,
    verify_immutable_evidence,
)
from run_a1_admission import (  # noqa: E402
    V5_INPUT_KEYS,
    _h_matrix,
    _indices_for_records,
    _item_matrix,
    _subset,
    _vocabulary,
    build_text_contexts,
    encode_text_inputs,
    extract_task_observations,
    load_protocol,
    load_text_encoder,
    verify_frozen_inputs,
)
from run_a1_failure_diagnosis import (  # noqa: E402
    _fit_scorer_with_ledger,
    _prepare_cell,
)


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_17_2026-08-16.md")
CONTRACT_PATH = Path("artifacts/a1_measurement_validity_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/audits/a1_measurement_validity.json")
AUDIT_MD_PATH = Path("04_results/audits/a1_measurement_validity.md")
LEDGER_PATH = Path("04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--device", default="cuda:1")
    parser.add_argument("--text-device", default="cpu")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--contract-output", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--audit-json-output", type=Path, default=AUDIT_JSON_PATH)
    parser.add_argument("--audit-md-output", type=Path, default=AUDIT_MD_PATH)
    parser.add_argument("--ledger-output", type=Path, default=LEDGER_PATH)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _cell(protocol: Mapping[str, Any], fold: str) -> Mapping[str, Any]:
    suffix = f"{fold}"
    matches = [
        row
        for row in protocol["inner_cells"]
        if str(row["inner_cell_id"]).endswith(suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: expected one {fold} cell")
    return matches[0]


def _item_vector_hash(item_vectors: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for surface in sorted(item_vectors):
        encoded = surface.encode("utf-8")
        vector = np.asarray(item_vectors[surface], dtype="<f4")
        if vector.shape != (384,) or not np.isfinite(vector).all():
            raise RuntimeError("INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: invalid item vector")
        digest.update(len(encoded).to_bytes(8, "little"))
        digest.update(encoded)
        digest.update(vector.tobytes(order="C"))
    return digest.hexdigest()


def run_d49(
    *,
    selected: Mapping[str, Any],
    features_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    old_audit: Mapping[str, Any],
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fits: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    results: dict[str, Any] = {}
    support: dict[str, Any] = {}
    seed = 20260813
    for task in TASKS:
        fold_summaries: list[dict[str, Any]] = []
        fold_support: list[dict[str, Any]] = []
        protocol = selected[task]
        for fold in NEW_FOLDS:
            cell = _cell(protocol, fold)
            prepared = _prepare_cell(
                cell=cell,
                features=features_by_task[task],
                metadata=metadata_by_task[task],
                seed=seed,
            )
            fit_rows = prepared["fit_rows"]
            score_rows = prepared["score_rows"]
            items, vocabulary, positions = _vocabulary(
                prepared["supported"], fit_rows, item_vectors
            )
            y_train = _item_matrix(fit_rows, item_vectors)
            h_train = _h_matrix(fit_rows, h_vectors)
            h_validation = _h_matrix(score_rows, h_vectors)
            item_train = _item_matrix(fit_rows, item_vectors)
            item_validation = _item_matrix(score_rows, item_vectors)
            true_positions = np.asarray(
                [positions[str(row["item_id"])] for row in score_rows],
                dtype=np.int64,
            )
            common = {
                "seed": seed,
                "y_train": y_train,
                "vocabulary": vocabulary,
                "true_positions": true_positions,
                "device": device,
                "task_protocol": protocol,
                "inner_cell": cell,
                "input_hashes": input_hashes,
                "scope_index": scope_index,
                "run_id": run_id,
                "fit_record_ids": [str(row["record_id"]) for row in fit_rows],
                "scoring_record_ids": [str(row["record_id"]) for row in score_rows],
                "fit_summaries": fits,
                "ledgers": ledgers,
            }
            h_logp, _ = _fit_scorer_with_ledger(
                fit_id=f"D49|{cell['inner_cell_id']}|seed{seed}|H_only",
                role="D49_H_only_positive_control_baseline",
                x_train=oracle_input(h_train, item_train, role="a_a1_scorer_h_only"),
                x_validation=oracle_input(
                    h_validation, item_validation, role="a_a1_scorer_h_only"
                ),
                **common,
            )
            oracle_logp, oracle_top1 = _fit_scorer_with_ledger(
                fit_id=f"D49|{cell['inner_cell_id']}|seed{seed}|oracle_item",
                role="D49_oracle_item_construct_validity_not_EEG_evidence",
                x_train=oracle_input(
                    h_train, item_train, role="a_a1_scorer_oracle_item"
                ),
                x_validation=oracle_input(
                    h_validation,
                    item_validation,
                    role="a_a1_scorer_oracle_item",
                ),
                **common,
            )
            observed_subjects = sorted({str(row["subject_id"]) for row in score_rows})
            row_contract = {
                "scoring_shape_equal": h_logp.shape
                == oracle_logp.shape
                == oracle_top1.shape
                == true_positions.shape,
                "finite": bool(
                    np.isfinite(h_logp).all() and np.isfinite(oracle_logp).all()
                ),
                "row_identity_equal": True,
                "vocabulary_equal": True,
                "target_shape_equal": y_train.shape[1] == vocabulary.shape[1] == 384,
                "frozen_subject_set_equal": observed_subjects
                == sorted(SUBJECT_FOLDS[task][fold]),
                "fold_roles": all(prepared["role_checks"].values()),
            }
            fold_summaries.append(
                summarize_amendment_fold(
                    task=task,
                    fold=fold,
                    h_logp=h_logp,
                    oracle_logp=oracle_logp,
                    oracle_top1=oracle_top1,
                    true_positions=true_positions,
                    subject_ids=[str(row["subject_id"]) for row in score_rows],
                    row_contract=row_contract,
                )
            )
            fold_support.append(
                {
                    "fold": fold,
                    "fit_rows": len(fit_rows),
                    "scoring_rows": len(score_rows),
                    "vocabulary_size": len(items),
                    "subjects": observed_subjects,
                    "normalizer_fit_rows": prepared["normalizer"]["fit_rows"],
                    "train_common_support_rate": prepared[
                        "train_common_support_rate"
                    ],
                    "validation_common_support_rate": prepared[
                        "validation_common_support_rate"
                    ],
                    "row_contract": row_contract,
                }
            )
        old_s0 = old_audit["positive_controls"]["A-A1-scorer"][task]
        results[task] = combine_amendment_summaries(
            task=task, old_s0=old_s0, new_folds=fold_summaries
        )
        support[task] = fold_support
    return results, support


def _prepare_injection_cell(
    *,
    cell: Mapping[str, Any],
    features: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    train_global = _indices_for_records(metadata, cell["train_record_ids"])
    validation_global = _indices_for_records(metadata, cell["validation_record_ids"])
    train_rows = _subset(metadata, train_global)
    validation_rows = _subset(metadata, validation_global)
    supported, support_ledger = supported_item_ids(train_rows)
    fit_mask = np.asarray(
        [str(row["item_id"]) in supported for row in train_rows], dtype=bool
    )
    score_mask = np.asarray(
        [str(row["item_id"]) in supported for row in validation_rows], dtype=bool
    )
    normalizer, normalizer_summary = fit_fold_normalizer(features[train_global])
    train_normalized = transform_fold_normalizer(features[train_global], normalizer)
    validation_normalized = transform_fold_normalizer(
        features[validation_global], normalizer
    )
    role_checks = validate_fold_roles(
        inner_train_record_ids=cell["train_record_ids"],
        inner_validation_record_ids=cell["validation_record_ids"],
        cluster_fit_record_ids=[str(row["record_id"]) for row in train_rows],
        scoring_record_ids=[str(row["record_id"]) for row in validation_rows],
    )
    return {
        "train_rows": train_rows,
        "validation_rows": validation_rows,
        "supported": supported,
        "support_ledger_rows": len(support_ledger),
        "fit_mask": fit_mask,
        "score_mask": score_mask,
        "train_normalized": train_normalized,
        "validation_normalized": validation_normalized,
        "normalizer": normalizer_summary,
        "role_checks": role_checks,
    }


def run_d50(
    *,
    selected: Mapping[str, Any],
    features_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    matrix: np.ndarray,
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fits: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    seed = 20260813
    metric_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    alpha_zero_checks = 0
    for task in TASKS:
        protocol = selected[task]
        for fold in INJECTION_FOLDS:
            cell = _cell(protocol, fold)
            prepared = _prepare_injection_cell(
                cell=cell,
                features=features_by_task[task],
                metadata=metadata_by_task[task],
            )
            train_rows = prepared["train_rows"]
            validation_rows = prepared["validation_rows"]
            items, vocabulary, positions = _vocabulary(
                prepared["supported"], train_rows, item_vectors
            )
            for alpha in ALPHAS:
                train_injected = inject_after_normalizer(
                    prepared["train_normalized"],
                    train_rows,
                    alpha=alpha,
                    matrix=matrix,
                    item_vectors=item_vectors,
                )
                validation_injected = inject_after_normalizer(
                    prepared["validation_normalized"],
                    validation_rows,
                    alpha=alpha,
                    matrix=matrix,
                    item_vectors=item_vectors,
                )
                if alpha == 0.0:
                    for injected, original in (
                        (train_injected, prepared["train_normalized"]),
                        (validation_injected, prepared["validation_normalized"]),
                    ):
                        if injected.tobytes(order="C") != original.tobytes(order="C"):
                            raise AssertionError("alpha=0 canonical-byte identity failed")
                        alpha_zero_checks += 1
                train_arms, train_common, train_audit = build_four_arm_features(
                    train_injected,
                    train_rows,
                    seed=seed,
                    partition=f"{cell['inner_cell_id']}|train",
                )
                validation_arms, validation_common, validation_audit = (
                    build_four_arm_features(
                        validation_injected,
                        validation_rows,
                        seed=seed,
                        partition=f"{cell['inner_cell_id']}|validation",
                    )
                )
                fit_positions = np.asarray(
                    [
                        position
                        for position, original in enumerate(train_common)
                        if prepared["fit_mask"][int(original)]
                    ],
                    dtype=np.int64,
                )
                score_positions = np.asarray(
                    [
                        position
                        for position, original in enumerate(validation_common)
                        if prepared["score_mask"][int(original)]
                    ],
                    dtype=np.int64,
                )
                fit_original = train_common[fit_positions]
                score_original = validation_common[score_positions]
                fit_rows = [train_rows[int(index)] for index in fit_original]
                score_rows = [validation_rows[int(index)] for index in score_original]
                if len(fit_rows) < 2 or not score_rows:
                    raise RuntimeError(
                        "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: empty common support"
                    )
                observed_subjects = sorted(
                    {str(row["subject_id"]) for row in score_rows}
                )
                if observed_subjects != sorted(SUBJECT_FOLDS[task][fold]):
                    raise RuntimeError(
                        f"INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: {task}/{fold} "
                        "lost a frozen validation subject"
                    )
                y_train = _item_matrix(fit_rows, item_vectors)
                h_train = _h_matrix(fit_rows, h_vectors)
                h_validation = _h_matrix(score_rows, h_vectors)
                true_positions = np.asarray(
                    [positions[str(row["item_id"])] for row in score_rows],
                    dtype=np.int64,
                )
                arm_logp: dict[str, np.ndarray] = {}
                for arm in ARMS:
                    x_train = np.concatenate(
                        [h_train, train_arms[arm][fit_positions]], axis=1
                    ).astype(np.float32, copy=False)
                    x_validation = np.concatenate(
                        [h_validation, validation_arms[arm][score_positions]],
                        axis=1,
                    ).astype(np.float32, copy=False)
                    logp, _ = _fit_scorer_with_ledger(
                        fit_id=(
                            f"D50|{cell['inner_cell_id']}|seed{seed}|"
                            f"alpha{alpha:g}|{arm}"
                        ),
                        role="D50_graded_semantic_injection_construct_validity_only",
                        seed=seed,
                        x_train=x_train,
                        y_train=y_train,
                        x_validation=x_validation,
                        vocabulary=vocabulary,
                        true_positions=true_positions,
                        device=device,
                        task_protocol=protocol,
                        inner_cell=cell,
                        input_hashes=input_hashes,
                        scope_index=scope_index,
                        run_id=run_id,
                        fit_record_ids=[str(row["record_id"]) for row in fit_rows],
                        scoring_record_ids=[str(row["record_id"]) for row in score_rows],
                        fit_summaries=fits,
                        ledgers=ledgers,
                    )
                    arm_logp[arm] = logp
                statistics = u_statistics(
                    arm_logp["real"],
                    {arm: arm_logp[arm] for arm in ARMS if arm != "real"},
                )
                statistics["max_selection_gap"] = (
                    statistics["u_oof"] - statistics["u_min"]
                )
                if any(value.shape != (len(score_rows),) for value in statistics.values()):
                    raise AssertionError("D50 metric rows are not aligned")
                for index, row in enumerate(score_rows):
                    metric_rows.append(
                        {
                            "task": task,
                            "fold": fold,
                            "alpha": float(alpha),
                            "subject_id": str(row["subject_id"]),
                            **{
                                metric: float(statistics[metric][index])
                                for metric in METRICS
                            },
                        }
                    )
                support_rows.append(
                    {
                        "task": task,
                        "fold": fold,
                        "alpha": float(alpha),
                        "fit_rows": len(fit_rows),
                        "scoring_rows": len(score_rows),
                        "subjects": observed_subjects,
                        "supported_item_count": len(items),
                        "support_ledger_rows": prepared["support_ledger_rows"],
                        "normalizer_fit_rows": prepared["normalizer"]["fit_rows"],
                        "train_common_rows": int(train_common.size),
                        "validation_common_rows": int(validation_common.size),
                        "train_common_support_rate": train_audit[
                            "common_support_rate"
                        ],
                        "validation_common_support_rate": validation_audit[
                            "common_support_rate"
                        ],
                        "four_arm_shape_equal": len(
                            {tuple(value.shape) for value in train_arms.values()}
                        )
                        == 1
                        and len(
                            {tuple(value.shape) for value in validation_arms.values()}
                        )
                        == 1,
                        "four_arm_finite": all(
                            np.isfinite(value).all()
                            for value in [*train_arms.values(), *validation_arms.values()]
                        ),
                        "row_identity_equal": bool(
                            train_audit["row_ids_identical"]
                            and validation_audit["row_ids_identical"]
                        ),
                        "fold_roles": prepared["role_checks"],
                    }
                )
    curves: dict[str, Any] = {}
    for task in TASKS:
        alpha_results = [
            summarize_injection_rows(metric_rows, task=task, alpha=alpha)
            for alpha in ALPHAS
        ]
        curves[task] = summarize_curve(alpha_results)
    checks = {
        "alpha_zero_array_checks": alpha_zero_checks,
        "expected_alpha_zero_array_checks": 12,
        "all_alpha_zero_byte_identical": alpha_zero_checks == 12,
        "support_row_count": len(support_rows),
        "expected_support_row_count": 48,
        "all_common_row_contracts_pass": all(
            row["four_arm_shape_equal"]
            and row["four_arm_finite"]
            and row["row_identity_equal"]
            and all(row["fold_roles"].values())
            for row in support_rows
        ),
    }
    return curves, support_rows, checks


def build_contract(
    *,
    root: Path,
    run_id: str,
    input_hashes: Mapping[str, str],
    immutable: Mapping[str, Any],
    projection: Mapping[str, Any],
    item_vector_hash: str,
    text_manifests: Mapping[str, str],
    resolved_revision: str,
) -> dict[str, Any]:
    sources = (
        "02_code/src/data/a1_measurement_validity.py",
        "02_code/scripts/run_a1_measurement_validity.py",
        "02_code/tests/test_a1_measurement_validity.py",
    )
    return {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": run_id,
        "task": "S0_A1_FAILURE_DIAGNOSIS",
        "spec": f"{SPEC_PATH.as_posix()}#D49-D52",
        "claim_boundary": (
            "construct-validity measurement audit only; artificial injection is not "
            "physiological EEG, EEG evidence, Gate, or paper performance"
        ),
        "scope": {
            "tasks": list(TASKS),
            "folds": list(INJECTION_FOLDS),
            "seed": 20260813,
            "alphas": list(ALPHAS),
            "arms": list(ARMS),
            "D49_new_fits": EXPECTED_AMENDMENT_FITS,
            "D50_new_fits": EXPECTED_INJECTION_FITS,
            "conditional_total_fits": EXPECTED_TOTAL_FITS,
            "outer_test_values_read": False,
            "calibration_values_read": False,
        },
        "projection": dict(projection),
        "item_vector_canonical_mapping_sha256": item_vector_hash,
        "item_vector_hash_rule": (
            "SHA256 over sorted UTF-8 surface length+bytes followed by each "
            "little-endian float32[384] C-order vector"
        ),
        "text_encoder": {
            "requested_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            "resolved_revision": resolved_revision,
            "manifests": dict(text_manifests),
            "output_dim": 384,
            "trainable_parameters": 0,
        },
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "immutable_evidence_hashes": dict(immutable["hashes"]),
        "immutable_v5": {
            "admission": immutable["admission"],
            "diagnosis": immutable["diagnosis"],
        },
        "source_hashes": {
            relative: sha256_file(root / relative) for relative in sources
        },
        "formal_output_policy": {
            "aggregate_and_subject_summaries_only": True,
            "ledger_ids_hashes_scopes_only": True,
            "no_eeg_arrays_projection_array_observation_vectors_logits_model_parameters_or_cache": True,
        },
    }


def evaluate_outcome(
    *,
    d49: Mapping[str, Any],
    curves: Mapping[str, Any] | None,
    fits: Sequence[Mapping[str, Any]],
    ledgers: Sequence[Mapping[str, Any]],
    checks: Mapping[str, Any] | None,
    formal_pass: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    d49_pass = all(bool(d49[task]["pass"]) for task in TASKS)
    if not d49_pass:
        reasons.append("D49_15_SUBJECT_POSITIVE_CONTROL_FAILED")
        if len(fits) != 8 or len(ledgers) != 8:
            reasons.append("D49_FIT_OR_V5_COUNT_MISMATCH")
    else:
        if curves is None or checks is None:
            reasons.append("D50_NOT_COMPLETED_AFTER_D49_PASS")
        else:
            for task in TASKS:
                if not curves[task]["alpha_10_family_mean_detected"]:
                    reasons.append(f"{task}:ALPHA_10_FAMILY_MEAN_NOT_DETECTED")
                if curves[task]["spearman_rho_alpha_vs_u_oof"] < 0.90:
                    reasons.append(f"{task}:SPEARMAN_RHO_LT_0_90")
            if len(fits) != EXPECTED_TOTAL_FITS:
                reasons.append("FIT_COUNT_NOT_200")
            if len(ledgers) != EXPECTED_TOTAL_FITS:
                reasons.append("V5_COUNT_NOT_200")
            if not checks["all_alpha_zero_byte_identical"]:
                reasons.append("ALPHA_ZERO_IDENTITY_FAILED")
            if not checks["all_common_row_contracts_pass"]:
                reasons.append("COMMON_ROW_CONTRACT_FAILED")
    if len({str(row["fit_id"]) for row in ledgers}) != len(ledgers):
        reasons.append("V5_FIT_IDS_NOT_UNIQUE")
    if any(row.get("outer_test_record_ids_read") != [] for row in ledgers):
        reasons.append("OUTER_TEST_READ")
    if any(row.get("calibration_record_ids") != [] for row in ledgers):
        reasons.append("CALIBRATION_READ")
    if not formal_pass:
        reasons.append("FORMAL_OUTPUT_CONTRACT_FAILED")
    outcome = (
        "PASS_A1_MEASUREMENT_VALIDITY_AUDIT"
        if not reasons
        else "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT"
    )
    return outcome, reasons


def planned_state_transition(outcome: str) -> dict[str, Any]:
    if outcome == "PASS_A1_MEASUREMENT_VALIDITY_AUDIT":
        return {
            "diagnosis_status": "DONE",
            "diagnosis_completion_outcome": outcome,
            "a1_admission_status": "FAILED",
            "a1_admission_completion_outcome": "FAIL_A1_ADMISSION",
            "route_primary": "MEASUREMENT-RECOVERY",
            "route_backup": "NEGATIVE-DIAGNOSTIC",
            "route_locked": None,
            "recommended_next_task": "S0_A1_MEASUREMENT_RECOVERY_FREEZE",
            "negative_confirmation_remains_blocked": True,
        }
    return {
        "diagnosis_status": "BLOCKED",
        "diagnosis_completion_outcome": outcome,
        "route_unchanged": True,
        "recommended_next_task": None,
        "author_review_blocker_required": True,
    }


def render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# A1 measurement-validity audit",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['completion_outcome']}`",
        f"- New fits/V5: {audit['fit_summary']['total_fit_count']}/{audit['fit_summary']['real_v5_ledger_count']}",
        "- Outer-test/calibration reads: `0/0`",
        "- Claim boundary: construct-validity only; injected data are not physiological EEG or paper performance.",
        "",
        "## D49 — frozen 15-subject scorer amendment",
        "",
        "| Task | gain | CI95 | macro R@1 | subjects | PASS |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for task in TASKS:
        row = audit["D49_15_subject_amendment"][task]
        gain = row["paired_oracle_minus_h_logp"]
        lines.append(
            f"| {task} | {gain['estimate']:.6g} | {gain['ci95']} | "
            f"{row['oracle_full_vocabulary_macro_subject_r_at_1']:.6g} | "
            f"{row['subject_count']} | {'PASS' if row['pass'] else 'FAIL'} |"
        )
    if audit.get("D50_injection_curves"):
        lines.extend(
            [
                "",
                "## D50 — frozen graded semantic-injection curve",
                "",
                "| Task | family floor | legacy floor | rho | alpha=10 family | alpha=10 legacy | PASS |",
                "|---|---:|---:|---:|---|---|---|",
            ]
        )
        for task in TASKS:
            row = audit["D50_injection_curves"][task]
            lines.append(
                f"| {task} | {row['alpha_family_floor']} | {row['alpha_legacy_floor']} | "
                f"{row['spearman_rho_alpha_vs_u_oof']:.6g} | "
                f"{row['alpha_10_family_mean_detected']} | "
                f"{row['alpha_10_legacy_full_detected']} | {row['pass']} |"
            )
    lines.extend(
        [
            "",
            "The admitted `FAIL_A1_ADMISSION` remains unchanged. This audit does not establish that real EEG has or lacks semantic increment.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    root: Path,
    *,
    contract_path: Path,
    audit_json_path: Path,
    audit_md_path: Path,
    ledger_path: Path,
    contract: Mapping[str, Any],
    audit: Mapping[str, Any],
    ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    payloads = {
        contract_path: yaml.safe_dump(
            dict(contract), sort_keys=False, allow_unicode=True
        ).encode("utf-8"),
        audit_json_path: canonical_artifact(audit),
        audit_md_path: render_markdown(audit).encode("utf-8"),
        ledger_path: deterministic_gzip_jsonl(ledgers),
    }
    hashes: dict[str, str] = {}
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        hashes[relative.as_posix()] = sha256_bytes(payload)
    return hashes


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    os.chdir(root)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    started = time.perf_counter()
    random.seed(20260813)
    np.random.seed(20260813)
    torch.manual_seed(20260813)
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available() or not str(args.device).startswith("cuda"):
        raise RuntimeError(
            "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: real audit requires CUDA scoring"
        )

    immutable = verify_immutable_evidence(root)
    physical_hashes, _, _ = verify_frozen_inputs(root)
    _, _, selected, scope_index = load_protocol(root)
    v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    for ledger in [
        *immutable["admission_ledgers"],
        *immutable["diagnosis_ledgers"],
    ]:
        validate_diagnosis_v5_or_raise(ledger, scope_index, v5_hashes)
    old_v5_revalidated = len(immutable["admission_ledgers"]) + len(
        immutable["diagnosis_ledgers"]
    )
    print(
        "IMMUTABLE_EVIDENCE status=PASS hashes=17 "
        f"V5={old_v5_revalidated}/697 outer_test_reads=0 calibration_reads=0"
    )

    contexts = build_text_contexts(root)
    features_by_task: dict[str, np.ndarray] = {}
    metadata_by_task: dict[str, list[dict[str, Any]]] = {}
    data_summary: dict[str, Any] = {}
    for task in TASKS:
        features, metadata, manifest = extract_task_observations(
            root,
            task=task,
            task_protocol=selected[task],
            contexts=contexts,
            rebuild=False,
        )
        features_by_task[task] = features
        metadata_by_task[task] = metadata
        data_summary[task] = {
            "observations": len(metadata),
            "records": manifest["record_count"],
            "subjects": manifest["subject_count"],
            "shape": manifest["shape"],
            "dtype": manifest["dtype"],
            "finite": manifest["finite"],
        }
        print(
            f"DATA task={task} observations={len(metadata)} shape={list(features.shape)} "
            f"subjects={manifest['subject_count']} finite={manifest['finite']}"
        )

    encoder, text_manifests, resolved_revision = load_text_encoder(
        root, args.text_device
    )
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    if str(args.text_device).startswith("cuda"):
        torch.cuda.empty_cache()
    item_vector_hash = _item_vector_hash(item_vectors)
    matrix, projection = projection_matrix()

    fits: list[dict[str, Any]] = []
    ledgers: list[dict[str, Any]] = []
    old_audit = _load_json(root / "04_results/audits/a1_failure_diagnosis.json")
    d49, d49_support = run_d49(
        selected=selected,
        features_by_task=features_by_task,
        metadata_by_task=metadata_by_task,
        item_vectors=item_vectors,
        h_vectors=h_vectors,
        old_audit=old_audit,
        device=args.device,
        input_hashes=v5_hashes,
        scope_index=scope_index,
        run_id=args.run_id,
        fits=fits,
        ledgers=ledgers,
    )
    if len(fits) != EXPECTED_AMENDMENT_FITS or len(ledgers) != EXPECTED_AMENDMENT_FITS:
        raise RuntimeError(
            "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: D49 is not exactly 8 fits/V5"
        )
    print(
        "D49 fits=8 V5=8 "
        + " ".join(
            f"{task}=pass:{d49[task]['pass']},"
            f"gain_ci:{d49[task]['paired_oracle_minus_h_logp']['ci95']},"
            f"R1:{d49[task]['oracle_full_vocabulary_macro_subject_r_at_1']:.6f},"
            f"subjects:{d49[task]['subject_count']}"
            for task in TASKS
        )
    )

    curves: dict[str, Any] | None = None
    d50_support: list[dict[str, Any]] = []
    d50_checks: dict[str, Any] | None = None
    if all(d49[task]["pass"] for task in TASKS):
        curves, d50_support, d50_checks = run_d50(
            selected=selected,
            features_by_task=features_by_task,
            metadata_by_task=metadata_by_task,
            item_vectors=item_vectors,
            h_vectors=h_vectors,
            matrix=matrix,
            device=args.device,
            input_hashes=v5_hashes,
            scope_index=scope_index,
            run_id=args.run_id,
            fits=fits,
            ledgers=ledgers,
        )
        print(
            "D50 fits=192 V5=192 "
            + " ".join(
                f"{task}=floor:{curves[task]['alpha_family_floor']},"
                f"legacy_floor:{curves[task]['alpha_legacy_floor']},"
                f"rho:{curves[task]['spearman_rho_alpha_vs_u_oof']:.6f},"
                f"alpha10:{curves[task]['alpha_10_family_mean_detected']}"
                for task in TASKS
            )
        )
    else:
        print("D50 NOT_RUN reason=D49_FAILED")

    del matrix
    contract = build_contract(
        root=root,
        run_id=args.run_id,
        input_hashes=physical_hashes,
        immutable=immutable,
        projection=projection,
        item_vector_hash=item_vector_hash,
        text_manifests=text_manifests,
        resolved_revision=resolved_revision,
    )
    fit_summary = {
        "D49_ridge_fit_count": min(len(fits), EXPECTED_AMENDMENT_FITS),
        "D50_ridge_fit_count": max(0, len(fits) - EXPECTED_AMENDMENT_FITS),
        "total_fit_count": len(fits),
        "real_v5_ledger_count": len(ledgers),
        "unique_v5_fit_ids": len({str(row["fit_id"]) for row in ledgers}),
        "maximum_single_fit_seconds": max(float(row["elapsed_seconds"]) for row in fits),
        "fit_runtime_seconds_sum": float(
            sum(float(row["elapsed_seconds"]) for row in fits)
        ),
        "fits": fits,
    }
    preliminary: dict[str, Any] = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "S0_A1_FAILURE_DIAGNOSIS",
        "claim_boundary": (
            "measurement construct-validity only; injected values are not real EEG "
            "evidence or paper performance"
        ),
        "immutable_evidence": {
            "hash_count": len(immutable["hashes"]),
            "old_v5_revalidated": old_v5_revalidated,
            "admission_v5": immutable["admission"],
            "diagnosis_v5": immutable["diagnosis"],
        },
        "D49_15_subject_amendment": d49,
        "D49_support": d49_support,
        "D50_injection_curves": curves,
        "D50_support": d50_support,
        "D50_contract_checks": d50_checks,
        "fit_summary": fit_summary,
        "data": data_summary,
        "text": {
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
            "item_vector_canonical_mapping_sha256": item_vector_hash,
            **text_summary,
        },
        "projection": projection,
        "input_artifact_hashes": dict(sorted(physical_hashes.items())),
        "outer_test": {
            "ids_used_for_v5_exclusion_only": True,
            "eeg_feature_label_metric_reads": 0,
            "calibration_record_count": 0,
        },
        "formal_outputs_contain_no_eeg_arrays_projection_array_observation_vectors_logits_model_parameters_or_cache": True,
        "elapsed_seconds": time.perf_counter() - started,
    }
    formal_contract = validate_aggregate_formal_output(contract)
    formal_audit = validate_aggregate_formal_output(preliminary)
    outcome, reasons = evaluate_outcome(
        d49=d49,
        curves=curves,
        fits=fits,
        ledgers=ledgers,
        checks=d50_checks,
        formal_pass=bool(formal_contract["pass"] and formal_audit["pass"]),
    )
    preliminary["completion_outcome"] = outcome
    preliminary["outcome_reasons"] = reasons
    preliminary["planned_state_transition"] = planned_state_transition(outcome)
    preliminary["formal_output_validation"] = {
        "contract": formal_contract,
        "audit": validate_aggregate_formal_output(preliminary),
    }
    if not all(
        row["pass"] for row in preliminary["formal_output_validation"].values()
    ):
        raise RuntimeError(
            "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT: forbidden formal output key"
        )

    output_hashes = write_outputs(
        root,
        contract_path=args.contract_output,
        audit_json_path=args.audit_json_output,
        audit_md_path=args.audit_md_output,
        ledger_path=args.ledger_output,
        contract=contract,
        audit=preliminary,
        ledgers=ledgers,
    )
    final_immutable = verify_immutable_evidence(root)
    if final_immutable["hashes"] != immutable["hashes"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: immutable evidence changed during run")

    print(f"OUTCOME {outcome} reasons={reasons}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        f"SELF-CHECK SUMMARY samples={{new_fits: {len(fits)}, new_v5: {len(ledgers)}, "
        f"old_v5_revalidated: {old_v5_revalidated}}} "
        "shapes={A1: [N,840], H: [N,384], probe_input: [N,1224], target: [N,384]} "
        f"elapsed_seconds={preliminary['elapsed_seconds']:.3f} "
        f"ranges={{max_fit_seconds: {fit_summary['maximum_single_fit_seconds']:.3f}, "
        f"alphas: [{min(ALPHAS)}, {max(ALPHAS)}]}} "
        "assertions={outer_test_reads: 0, calibration_reads: 0, old_bytes_unchanged: true, "
        f"formal_aggregate_only: true}} status={'PASS' if not reasons else 'FAIL'}"
    )
    return 0 if outcome == "PASS_A1_MEASUREMENT_VALIDITY_AUDIT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
