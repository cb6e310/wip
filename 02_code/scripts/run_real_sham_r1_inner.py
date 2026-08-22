#!/usr/bin/env python3
"""Run only the v3.22 156-operation inner real-vs-sham R1 diagnostic."""

from __future__ import annotations

import argparse
import gzip
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
    apply_log_bandpower,
    build_recovery_v5_ledger,
    derive_recovery_partitions,
    fit_log_bandpower,
    sha256_file,
    validate_recovery_v5_or_raise,
    verify_run032_immutable,
)
from data.a1_measurement_validity import verify_immutable_evidence  # noqa: E402
from data.real_sham_r1_inner import (  # noqa: E402
    ALGORITHM_VERSION,
    ARMS,
    BASELINE_CANDIDATE,
    CANDIDATES,
    EXPECTED_EEG_PROBES,
    EXPECTED_EEG_V5_LEDGERS,
    EXPECTED_H_ONLY_Y0,
    EXPECTED_RIDGE_OPERATIONS,
    EXPECTED_TEXT_LEDGERS,
    EXPECTED_TEXT_RESIDUALIZERS,
    FOLDS,
    FRONTENDS,
    METRICS,
    REGIMES,
    RUN_ID,
    TARGETS,
    TASKS,
    build_normalized_residual_vocabulary,
    build_text_residualizer_ledger,
    evaluate_r1_outcome,
    paired_cross_recovery,
    summarize_subject_first,
    target_rows,
    validate_text_residualizer_ledger,
    verify_immutable_parent_r0,
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
from run_a1_measurement_recovery import extract_t8  # noqa: E402


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_22_2026-08-22.md")
FREEZE_PATH = Path("artifacts/real_sham_r1_freeze.yaml")
CONTRACT_PATH = Path("artifacts/real_sham_r1_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/diagnostics/real_sham_r1_inner.json")
AUDIT_MD_PATH = Path("04_results/diagnostics/real_sham_r1_inner.md")
LEDGER_PATH = Path("04_results/diagnostics/real_sham_r1_inner_run_ledger.jsonl.gz")
EXPECTED_FREEZE_SHA256 = "d08719f3f2a5c9c21ceb80de2fff5949ccb8ac891750482f58768dfaa36b09a5"
EXPECTED_SPEC_SHA256 = "2d334869985b914ffcb5d3a70af1e7c1d4fe1c18210e447736105e7c3941c95e"

FRONTEND_PARENT_NAMES = {
    "F0_A1_BP_CONCAT": "A1_BP_CONCAT",
    "F1_LOGREL_BP": "A1R_LOG_BP_CONCAT",
    "F2_T8_FIXATION": "A1R_T8_FIXATION",
}


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
    if _git(root, "branch", "--show-current") != "research/real-sham-r1-inner":
        raise RuntimeError("STATE_SPEC_CONFLICT: R1 runner is on the wrong branch")
    if _git(root, "rev-parse", "HEAD") != "ec7ced2708fe68ae8614b6b89b03256d88d1b541":
        raise RuntimeError("STATE_SPEC_CONFLICT: R1 execution HEAD is not the frozen base")
    if sha256_file(root / FREEZE_PATH) != EXPECTED_FREEZE_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.22 freeze bytes changed")
    if sha256_file(root / SPEC_PATH) != EXPECTED_SPEC_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.22 SPEC bytes changed")
    freeze = yaml.safe_load((root / FREEZE_PATH).read_text(encoding="utf-8"))
    if not isinstance(freeze, dict):
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.22 freeze is not a mapping")
    if freeze.get("outcome_before_execution") != "READY":
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.22 freeze is not READY")
    if freeze.get("base_commit") != "ec7ced2708fe68ae8614b6b89b03256d88d1b541":
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.22 freeze base changed")
    return freeze


def _write_contract(root: Path, output: Path, contract: Mapping[str, Any]) -> str:
    payload = yaml.safe_dump(dict(contract), sort_keys=False, allow_unicode=True).encode(
        "utf-8"
    )
    path = root / output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def _fit_eeg_v5_and_score(
    *,
    operation_id: str,
    operation_kind: str,
    frontend: str | None,
    target: str,
    arm: str | None,
    x_fit: np.ndarray,
    y_fit: np.ndarray,
    x_seen: np.ndarray,
    x_cross: np.ndarray,
    vocabulary: np.ndarray,
    seen_positions: np.ndarray,
    cross_positions: np.ndarray,
    device: str,
    task_protocol: Mapping[str, Any],
    recovery_cell: str,
    partitions: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fits: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    model, elapsed = fit_ridge_to_items(
        x_fit,
        y_fit,
        alpha=1.0,
        device=device,
    )
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC: {operation_id} >300s")
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
    ledger["ledger_type"] = "EEG_V5"
    ledger["r1_scope"] = {
        "operation_kind": operation_kind,
        "frontend": frontend,
        "target": target,
        "arm": arm,
        "alignment": "M0_STRICT_INDUCTIVE",
    }
    validate_recovery_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fits.append(
        {
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "fit_type": "ridge",
            "frontend": frontend,
            "target": target,
            "arm": arm,
            "train_rows": int(x_fit.shape[0]),
            "seen_rows": int(x_seen.shape[0]),
            "cross_rows": int(x_cross.shape[0]),
            "input_dim": int(x_fit.shape[1]),
            "target_dim": int(y_fit.shape[1]),
            "vocabulary_size": int(vocabulary.shape[0]),
            "elapsed_seconds": elapsed,
            "same_fit_scores_seen_and_cross": True,
            "v5": "PASS_REAL_RUN_LEDGER",
        }
    )
    seen = ridge_log_prob(
        model,
        x_seen,
        vocabulary,
        seen_positions,
        temperature=0.07,
        device=device,
    )
    cross = ridge_log_prob(
        model,
        x_cross,
        vocabulary,
        cross_positions,
        temperature=0.07,
        device=device,
    )
    del model
    return seen, cross


def _fit_y1_residualizer(
    *,
    task: str,
    fold: str,
    rows: Sequence[Mapping[str, Any]],
    supported: set[str],
    h_fit: np.ndarray,
    y0_fit: np.ndarray,
    partitions: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    device: str,
    fits: list[dict[str, Any]],
    text_ledgers: list[dict[str, Any]],
) -> tuple[list[str], np.ndarray, dict[str, int], dict[str, Any]]:
    operation_id = f"R1|{task}|{fold}|Y1_TEXT_RESIDUALIZER"
    model, elapsed = fit_ridge_to_items(h_fit, y0_fit, alpha=1.0, device=device)
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC: {operation_id} >300s")
    items, vocabulary, positions, summary = build_normalized_residual_vocabulary(
        rows=rows,
        supported=supported,
        h_fit=h_fit,
        y0_fit=y0_fit,
        model=model,
    )
    ledger = build_text_residualizer_ledger(
        operation_id=operation_id,
        task=task,
        fold=fold,
        fit_record_ids=partitions["fit_record_ids"],
        fit_row_count=len(rows),
        summary=summary,
        input_hashes=input_hashes,
    )
    validate_text_residualizer_ledger(ledger)
    text_ledgers.append(ledger)
    fits.append(
        {
            "operation_id": operation_id,
            "operation_kind": "Y1_TEXT_RESIDUALIZER",
            "fit_type": "ridge",
            "frontend": None,
            "target": "Y1_H_RESIDUAL_MINILM",
            "arm": None,
            "train_rows": int(h_fit.shape[0]),
            "seen_rows": 0,
            "cross_rows": 0,
            "input_dim": 384,
            "target_dim": 384,
            "vocabulary_size": len(items),
            "elapsed_seconds": elapsed,
            "same_fit_scores_seen_and_cross": False,
            "ledger": "PASS_TEXT_ONLY_RESIDUALIZER_LEDGER",
            "eeg_loaded_for_operation": False,
        }
    )
    del model
    return items, vocabulary, positions, summary


def run_r1(
    *,
    selected: Mapping[str, Any],
    baseline_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    t8_by_task: Mapping[str, Mapping[str, np.ndarray]],
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
    fits: list[dict[str, Any]] = []
    eeg_ledgers: list[dict[str, Any]] = []
    text_ledgers: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    residualizer_summaries: list[dict[str, Any]] = []
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
        t8 = t8_by_task[task]
        for fold in FOLDS:
            cell = _cell(protocol, fold)
            partitions = derive_recovery_partitions(protocol, cell)
            recovery_cell = cell["inner_cell_id"].replace("|inner_", "|r1_inner_")
            validation_union = sorted(
                set(partitions["seen_record_ids"]) | set(partitions["cross_record_ids"])
            )
            scope_index["inner"][recovery_cell] = {
                "outer_cell_id": protocol["outer_cell_id"],
                "train_record_ids": partitions["fit_record_ids"],
                "validation_record_ids": validation_union,
            }
            partition_meta: dict[str, list[Mapping[str, Any]]] = {}
            partition_raw: dict[str, dict[str, np.ndarray]] = {}
            coverage: dict[str, Any] = {}
            for regime, record_key in (
                ("fit", "fit_record_ids"),
                ("seen", "seen_record_ids"),
                ("cross", "cross_record_ids"),
            ):
                legal_records = set(partitions[record_key])
                old_rows = [
                    row for row in metadata if str(row["record_id"]) in legal_records
                ]
                common_rows = [
                    row for row in old_rows if str(row["observation_id"]) in t8
                ]
                retention = len(common_rows) / len(old_rows) if old_rows else 0.0
                if retention < 0.90:
                    raise RuntimeError(
                        "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC: "
                        f"{task}/{fold}/{regime} retention {retention} <0.90"
                    )
                partition_meta[regime] = common_rows
                indices = np.asarray(
                    [id_to_index[str(row["observation_id"])] for row in common_rows],
                    dtype=np.int64,
                )
                partition_raw[regime] = {
                    "F0_A1_BP_CONCAT": baseline[indices],
                    "F2_T8_FIXATION": np.stack(
                        [t8[str(row["observation_id"])] for row in common_rows]
                    ).astype(np.float32),
                }
                coverage[regime] = {
                    "old_a1_available_rows": len(old_rows),
                    "three_frontend_common_rows": len(common_rows),
                    "retention": retention,
                    "subjects": sorted({str(row["subject_id"]) for row in common_rows}),
                }
            epsilon, epsilon_summary = fit_log_bandpower(
                partition_raw["fit"]["F0_A1_BP_CONCAT"]
            )
            for regime in ("fit", *REGIMES):
                partition_raw[regime]["F1_LOGREL_BP"] = apply_log_bandpower(
                    partition_raw[regime]["F0_A1_BP_CONCAT"], epsilon
                )

            arm_data: dict[str, dict[str, dict[str, np.ndarray]]] = {}
            common_indices: dict[str, np.ndarray] = {}
            normalizer_summaries: dict[str, Any] = {}
            for frontend in FRONTENDS:
                state, summary = fit_fold_normalizer(partition_raw["fit"][frontend])
                normalizer_summaries[frontend] = summary
                arm_data[frontend] = {}
                for regime in ("fit", *REGIMES):
                    normalized = transform_fold_normalizer(
                        partition_raw[regime][frontend], state
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
                    if set(arms) != set(ARMS):
                        raise RuntimeError("R1 four-arm scope changed")
                    if any(arms[arm].shape != arms["real"].shape for arm in ARMS):
                        raise RuntimeError("R1 four-arm capacity changed")
                    if not sham_audit["row_ids_identical"]:
                        raise RuntimeError("R1 four-arm row identity failed")
                    arm_data[frontend][regime] = arms
                    if regime not in common_indices:
                        common_indices[regime] = common
                    elif not np.array_equal(common_indices[regime], common):
                        raise RuntimeError("R1 frontend common-row identity differs")

            fit_common_meta = [
                partition_meta["fit"][int(index)] for index in common_indices["fit"]
            ]
            supported, support_ledger = supported_item_ids(fit_common_meta)
            row_meta: dict[str, list[Mapping[str, Any]]] = {}
            row_positions: dict[str, np.ndarray] = {}
            for regime in ("fit", *REGIMES):
                common_meta = [
                    partition_meta[regime][int(index)]
                    for index in common_indices[regime]
                ]
                positions = np.asarray(
                    [
                        index
                        for index, row in enumerate(common_meta)
                        if str(row["item_id"]) in supported
                    ],
                    dtype=np.int64,
                )
                row_positions[regime] = positions
                row_meta[regime] = [common_meta[int(index)] for index in positions]
                if not row_meta[regime]:
                    raise RuntimeError("R1 support rows are empty")
            if len({str(row["subject_id"]) for row in row_meta["seen"]}) != 10:
                raise RuntimeError("R1 seen subject count changed")
            if len({str(row["subject_id"]) for row in row_meta["cross"]}) != 5:
                raise RuntimeError("R1 cross subject count changed")

            y0_items, y0_vocabulary, y0_positions = _vocabulary(
                supported, row_meta["fit"], item_vectors
            )
            y0_fit = _item_matrix(row_meta["fit"], item_vectors)
            h = {
                regime: _h_matrix(row_meta[regime], h_vectors)
                for regime in ("fit", *REGIMES)
            }
            true_positions_y0 = {
                regime: np.asarray(
                    [y0_positions[str(row["item_id"])] for row in row_meta[regime]],
                    dtype=np.int64,
                )
                for regime in REGIMES
            }
            h_seen, h_cross = _fit_eeg_v5_and_score(
                operation_id=f"R1|{task}|{fold}|H_ONLY|Y0_RAW_MINILM",
                operation_kind="H_ONLY_Y0",
                frontend=None,
                target="Y0_RAW_MINILM",
                arm=None,
                x_fit=h["fit"],
                y_fit=y0_fit,
                x_seen=h["seen"],
                x_cross=h["cross"],
                vocabulary=y0_vocabulary,
                seen_positions=true_positions_y0["seen"],
                cross_positions=true_positions_y0["cross"],
                device=device,
                task_protocol=protocol,
                recovery_cell=recovery_cell,
                partitions=partitions,
                input_hashes=input_hashes,
                scope_index=scope_index,
                run_id=run_id,
                fits=fits,
                ledgers=eeg_ledgers,
            )
            h_only_y0 = {"seen": h_seen, "cross": h_cross}

            y1_items, y1_vocabulary, y1_positions, y1_summary = _fit_y1_residualizer(
                task=task,
                fold=fold,
                rows=row_meta["fit"],
                supported=supported,
                h_fit=h["fit"],
                y0_fit=y0_fit,
                partitions=partitions,
                input_hashes=input_hashes,
                device=device,
                fits=fits,
                text_ledgers=text_ledgers,
            )
            if y1_items != sorted(supported) or y0_items != sorted(supported):
                raise RuntimeError("R1 target vocabularies do not share supported items")
            y1_fit = target_rows(row_meta["fit"], y1_vocabulary, y1_positions)
            true_positions_y1 = {
                regime: np.asarray(
                    [y1_positions[str(row["item_id"])] for row in row_meta[regime]],
                    dtype=np.int64,
                )
                for regime in REGIMES
            }
            residualizer_summaries.append(
                {"task": task, "fold": fold, **y1_summary}
            )
            target_contracts = {
                "Y0_RAW_MINILM": {
                    "fit": y0_fit,
                    "vocabulary": y0_vocabulary,
                    "true_positions": true_positions_y0,
                },
                "Y1_H_RESIDUAL_MINILM": {
                    "fit": y1_fit,
                    "vocabulary": y1_vocabulary,
                    "true_positions": true_positions_y1,
                },
            }

            for frontend in FRONTENDS:
                for target in TARGETS:
                    candidate = f"{frontend}/{target}"
                    target_contract = target_contracts[target]
                    arm_logp: dict[str, dict[str, np.ndarray]] = {
                        regime: {} for regime in REGIMES
                    }
                    for arm in ARMS:
                        inputs = {
                            regime: np.concatenate(
                                [
                                    h[regime],
                                    arm_data[frontend][regime][arm][
                                        row_positions[regime]
                                    ],
                                ],
                                axis=1,
                            ).astype(np.float32)
                            for regime in ("fit", *REGIMES)
                        }
                        seen_logp, cross_logp = _fit_eeg_v5_and_score(
                            operation_id=(
                                f"R1|{task}|{fold}|{frontend}|{target}|{arm}"
                            ),
                            operation_kind="EEG_PROBE",
                            frontend=frontend,
                            target=target,
                            arm=arm,
                            x_fit=inputs["fit"],
                            y_fit=target_contract["fit"],
                            x_seen=inputs["seen"],
                            x_cross=inputs["cross"],
                            vocabulary=target_contract["vocabulary"],
                            seen_positions=target_contract["true_positions"]["seen"],
                            cross_positions=target_contract["true_positions"]["cross"],
                            device=device,
                            task_protocol=protocol,
                            recovery_cell=recovery_cell,
                            partitions=partitions,
                            input_hashes=input_hashes,
                            scope_index=scope_index,
                            run_id=run_id,
                            fits=fits,
                            ledgers=eeg_ledgers,
                        )
                        arm_logp["seen"][arm] = seen_logp
                        arm_logp["cross"][arm] = cross_logp
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
                            + stats[
                                "real_minus_within_trial_unit_assignment_shuffle"
                            ]
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
                                    "candidate": candidate,
                                    "frontend": frontend,
                                    "target": target,
                                    "regime": regime,
                                    "subject_id": str(row["subject_id"]),
                                    **{
                                        metric: float(stats[metric][index])
                                        for metric in METRICS
                                    },
                                    **{
                                        f"logp_{arm}": float(
                                            arm_logp[regime][arm][index]
                                        )
                                        for arm in ARMS
                                    },
                                }
                            )
                    support_rows.append(
                        {
                            "task": task,
                            "fold": fold,
                            "candidate": candidate,
                            "frontend": frontend,
                            "target": target,
                            "coverage": coverage,
                            "normalizer_fit_rows": normalizer_summaries[frontend][
                                "fit_rows"
                            ],
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
                            "epsilon_summary": (
                                epsilon_summary if frontend == "F1_LOGREL_BP" else None
                            ),
                            "same_rows_all_four_arms": True,
                            "same_fit_seen_cross_vocabulary": True,
                            "h_only_y0_scored_both_regimes": (
                                len(h_only_y0["seen"]) == len(row_meta["seen"])
                                and len(h_only_y0["cross"]) == len(row_meta["cross"])
                            ),
                        }
                    )

    results: dict[str, Any] = {}
    all_candidates = (BASELINE_CANDIDATE, *CANDIDATES)
    for task in TASKS:
        results[task] = {}
        for candidate in all_candidates:
            seen = summarize_subject_first(
                metric_rows, task=task, candidate=candidate, regime="seen"
            )
            cross = summarize_subject_first(
                metric_rows, task=task, candidate=candidate, regime="cross"
            )
            results[task][candidate] = {"seen": seen, "cross": cross}
        baseline_cross = results[task][BASELINE_CANDIDATE]["cross"]
        for candidate in CANDIDATES:
            results[task][candidate]["cross_recovery"] = paired_cross_recovery(
                results[task][candidate]["cross"],
                baseline_cross,
                task=task,
                candidate_id=candidate,
            )
    return (
        results,
        fits,
        eeg_ledgers,
        text_ledgers,
        support_rows,
        residualizer_summaries,
    )


def _render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# Real-vs-sham R1 inner diagnostic",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['outcome']}`",
        "- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`",
        f"- Selected candidate: `{audit['selected_candidate']}`",
        f"- Selected task scope: `{audit['selected_task_scope']}`",
        "- Ridge operations: `156`",
        "- EEG V5/text-only ledgers: `150/6`",
        "- Outer-test/calibration reads: `0/0`",
        "",
        "| Task | Candidate | seen semantic | seen family | cross semantic | cross family | recovery delta | recovery pass |",
        "|---|---|---:|---|---:|---|---:|---|",
    ]
    for task in TASKS:
        for candidate, row in audit["results"][task].items():
            recovery = row.get("cross_recovery")
            recovery_value = "n/a" if recovery is None else f"{recovery['estimate']:.6g}"
            lines.append(
                f"| {task} | {candidate} | "
                f"{row['seen']['metrics']['delta_semantic']['estimate']:.6g} | "
                f"{row['seen']['family_detected']} | "
                f"{row['cross']['metrics']['delta_semantic']['estimate']:.6g} | "
                f"{row['cross']['family_detected']} | {recovery_value} | "
                f"{row.get('recovery_pass', False)} |"
            )
    lines.extend(
        [
            "",
            "Channel-block permutation remains reported only as a topology sentinel; "
            "legacy u_oof/u_min are retained sensitivities.",
            "",
            "This is inner-only `RESEARCH_DIAGNOSTIC_ONLY` evidence. Parent/R0 "
            "outcomes are immutable. No outer confirmation, calibration, alignment, "
            "direct u+, EQ-ANMA, A3, ROAMM, or Gate is released.",
            "",
            "The only possible next step is author review of "
            "`R2_REAL_SHAM_OUTER_CONFIRMATION_FREEZE_IF_R1_PASS`; R2 was not run.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(
    root: Path,
    *,
    args: argparse.Namespace,
    audit: Mapping[str, Any],
    ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    payloads = {
        args.audit_json_output: canonical_artifact(audit),
        args.audit_md_output: _render_markdown(audit).encode("utf-8"),
        args.ledger_output: deterministic_gzip_jsonl(ledgers),
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
        raise RuntimeError(
            "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC: CUDA scoring unavailable"
        )

    freeze = _validate_branch_and_freeze(root)
    immutable_parent_r0 = verify_immutable_parent_r0(root)
    run032_hashes = verify_run032_immutable(root)
    immutable = verify_immutable_evidence(root)
    physical_hashes, _, _ = verify_frozen_inputs(root)
    _, _, selected, base_scope = load_protocol(root)
    old_v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    for ledger in [*immutable["admission_ledgers"], *immutable["diagnosis_ledgers"]]:
        validate_diagnosis_v5_or_raise(ledger, base_scope, old_v5_hashes)
    with gzip.open(
        root / "04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz",
        "rt",
        encoding="utf-8",
    ) as handle:
        run032_ledgers = [json.loads(line) for line in handle]
    for ledger in run032_ledgers:
        validate_diagnosis_v5_or_raise(ledger, base_scope, old_v5_hashes)
    if len(run032_ledgers) != 200 or len({row["fit_id"] for row in run032_ledgers}) != 200:
        raise RuntimeError("STATE_SPEC_CONFLICT: run-032 V5 count changed")

    source_paths = (
        "02_code/src/data/real_sham_r1_inner.py",
        "02_code/scripts/run_real_sham_r1_inner.py",
        "02_code/tests/test_real_sham_r1_inner.py",
    )
    input_hashes = {
        **old_v5_hashes,
        "r1_freeze": sha256_file(root / FREEZE_PATH),
        "spec_v322": sha256_file(root / SPEC_PATH),
        "r0_contract": immutable_parent_r0[
            "artifacts/real_sham_rescue_contract.yaml"
        ],
    }
    contract = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "branch": "research/real-sham-r1-inner",
        "base_commit": "ec7ced2708fe68ae8614b6b89b03256d88d1b541",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "governing_spec": {
            "path": SPEC_PATH.as_posix(),
            "sha256": EXPECTED_SPEC_SHA256,
        },
        "author_freeze": {
            "path": FREEZE_PATH.as_posix(),
            "sha256": EXPECTED_FREEZE_SHA256,
            "outcome_before_execution": freeze["outcome_before_execution"],
        },
        "scope": {
            "tasks": list(TASKS),
            "folds": list(FOLDS),
            "frontends": list(FRONTENDS),
            "targets": list(TARGETS),
            "arms": list(ARMS),
            "regimes": list(REGIMES),
            "alignment": "M0_STRICT_INDUCTIVE",
            "seed": 20260813,
            "ridge_alpha": 1.0,
            "temperature": 0.07,
            "minimum_retention": 0.90,
            "h_only_y0_operations": EXPECTED_H_ONLY_Y0,
            "text_residualizer_operations": EXPECTED_TEXT_RESIDUALIZERS,
            "eeg_probe_operations": EXPECTED_EEG_PROBES,
            "total_ridge_operations": EXPECTED_RIDGE_OPERATIONS,
            "eeg_v5_ledgers": EXPECTED_EEG_V5_LEDGERS,
            "text_only_ledgers": EXPECTED_TEXT_LEDGERS,
        },
        "y1_definition": {
            "fit_scope_only": True,
            "h_full_to_y0_ridge_alpha": 1.0,
            "float64_solve": True,
            "intercept_penalized": False,
            "canonical_fit_row_per_supported_item": True,
            "residual": "Y0 - prediction(H_full)",
            "finite_required": True,
            "minimum_l2_norm_exclusive": 1e-8,
            "l2_normalized": True,
            "seen_cross_refit_count": 0,
            "fallback_allowed": False,
        },
        "estimands": {
            "delta_semantic": "real - mean(trial_shuffle, within_trial_unit_assignment_shuffle)",
            "delta_legacy": "real - mean(all_three_shams)",
            "delta_channel": "real - channel_block_permutation",
        },
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "immutable_parent_r0_hashes": immutable_parent_r0,
        "run032_immutable_hashes": run032_hashes,
        "source_hashes": {relative: sha256_file(root / relative) for relative in source_paths},
        "forbidden": [
            "F3_EVENT_LOCKED",
            "M1_TRANS_UNLABELED_EA_SECONDARY",
            "outer_confirmation",
            "calibration",
            "alignment_training",
            "direct_u_plus",
            "EQ_ANMA",
            "A3",
            "ROAMM",
            "Gate_A_or_B",
        ],
    }
    contract_validation = validate_aggregate_formal_output(contract)
    if not contract_validation["pass"]:
        raise RuntimeError("R1 contract formal payload contains forbidden keys")
    contract_hash = _write_contract(root, args.contract_output, contract)
    print(f"CONTRACT frozen sha256={contract_hash} before_fits=true")

    contexts = build_text_contexts(root)
    baseline_by_task: dict[str, np.ndarray] = {}
    metadata_by_task: dict[str, list[dict[str, Any]]] = {}
    t8_by_task: dict[str, dict[str, np.ndarray]] = {}
    data_summary: dict[str, Any] = {}
    for task in TASKS:
        baseline, metadata, manifest = extract_task_observations(
            root,
            task=task,
            task_protocol=selected[task],
            contexts=contexts,
            rebuild=False,
        )
        t8, t8_manifest = extract_t8(
            root, task=task, baseline_metadata=metadata, baseline_manifest=manifest
        )
        baseline_by_task[task] = baseline
        metadata_by_task[task] = metadata
        t8_by_task[task] = t8
        data_summary[task] = {
            "old_a1_observations": len(metadata),
            "t8_available_observations": len(t8),
            "t8_availability_rate": len(t8) / len(metadata),
            "t8_manifest": t8_manifest,
        }
        print(
            f"DATA task={task} old_a1={len(metadata)} t8={len(t8)} "
            f"retention={len(t8)/len(metadata):.6f}"
        )

    encoder, text_manifests, resolved_revision = load_text_encoder(
        root, args.text_device
    )
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    (
        results,
        fits,
        eeg_ledgers,
        text_ledgers,
        support,
        residualizers,
    ) = run_r1(
        selected=selected,
        baseline_by_task=baseline_by_task,
        metadata_by_task=metadata_by_task,
        t8_by_task=t8_by_task,
        item_vectors=item_vectors,
        h_vectors=h_vectors,
        device=args.device,
        input_hashes=input_hashes,
        base_scope_index=base_scope,
        run_id=args.run_id,
    )

    operation_ids = [str(row["operation_id"]) for row in fits]
    count_contract = (
        len(fits) == EXPECTED_RIDGE_OPERATIONS
        and len(set(operation_ids)) == EXPECTED_RIDGE_OPERATIONS
        and sum(row["operation_kind"] == "H_ONLY_Y0" for row in fits)
        == EXPECTED_H_ONLY_Y0
        and sum(row["operation_kind"] == "Y1_TEXT_RESIDUALIZER" for row in fits)
        == EXPECTED_TEXT_RESIDUALIZERS
        and sum(row["operation_kind"] == "EEG_PROBE" for row in fits)
        == EXPECTED_EEG_PROBES
        and len(eeg_ledgers) == EXPECTED_EEG_V5_LEDGERS
        and len({str(row["fit_id"]) for row in eeg_ledgers})
        == EXPECTED_EEG_V5_LEDGERS
        and len(text_ledgers) == EXPECTED_TEXT_LEDGERS
        and len({str(row["operation_id"]) for row in text_ledgers})
        == EXPECTED_TEXT_LEDGERS
    )
    read_contract = all(
        row["outer_test_record_ids_read"] == []
        and row["calibration_record_ids"] == []
        for row in eeg_ledgers
    ) and all(
        row["outer_test_read"] is False
        and row["calibration_read"] is False
        and row["outer_test_record_ids_read"] == []
        and row["calibration_record_ids"] == []
        for row in text_ledgers
    )
    scope_contract = (
        len(support) == 36
        and all(
            set(row["coverage"]) == {"fit", "seen", "cross"}
            and all(value["retention"] >= 0.90 for value in row["coverage"].values())
            and row["same_rows_all_four_arms"]
            and row["same_fit_seen_cross_vocabulary"]
            for row in support
        )
        and len(residualizers) == 6
        and all(
            row["finite"]
            and row["l2_normalized"]
            and not row["fallback_used"]
            and row["seen_cross_refit_count"] == 0
            and row["residual_norm_min"] > 1e-8
            for row in residualizers
        )
    )
    immutable_after = verify_immutable_parent_r0(root)
    hash_contract = immutable_after == immutable_parent_r0

    preliminary: dict[str, Any] = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "results": results,
        "support": support,
        "residualizers": residualizers,
        "data": data_summary,
        "text": {
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
            **text_summary,
        },
        "fit_summary": {
            "h_only_y0": sum(
                row["operation_kind"] == "H_ONLY_Y0" for row in fits
            ),
            "text_residualizers": sum(
                row["operation_kind"] == "Y1_TEXT_RESIDUALIZER" for row in fits
            ),
            "eeg_probes": sum(
                row["operation_kind"] == "EEG_PROBE" for row in fits
            ),
            "total_ridge_operations": len(fits),
            "eeg_v5_ledgers": len(eeg_ledgers),
            "text_only_ledgers": len(text_ledgers),
            "unique_operation_ids": len(set(operation_ids)),
            "maximum_single_fit_seconds": max(row["elapsed_seconds"] for row in fits),
            "fit_runtime_seconds_sum": float(
                sum(row["elapsed_seconds"] for row in fits)
            ),
            "operations": fits,
        },
        "contract_checks": {
            "exact_operation_and_ledger_counts": count_contract,
            "scope_retention_row_identity": scope_contract,
            "zero_outer_calibration_reads": read_contract,
            "immutable_parent_r0_hashes": hash_contract,
            "y1_no_fallback_or_seen_cross_refit": all(
                not row["fallback_used"] and row["seen_cross_refit_count"] == 0
                for row in residualizers
            ),
            "forbidden_scope_executed": [],
        },
        "outer_test": {
            "eeg_label_metric_reads": 0,
            "calibration_reads": 0,
        },
        "claim_boundary": {
            "parent_and_r0_outcomes_immutable": True,
            "outer_confirmation_released": False,
            "paper_level_real_eeg_claim": False,
            "alignment_direct_eq_anma_a3_roamm_gate_released": False,
        },
        "immutable_parent_r0_hashes": immutable_after,
        "contract_sha256": contract_hash,
        "elapsed_seconds": time.perf_counter() - started,
        "next_task": "R2_REAL_SHAM_OUTER_CONFIRMATION_FREEZE_IF_R1_PASS_AFTER_AUTHOR_REVIEW_ONLY",
    }
    formal_pass = validate_aggregate_formal_output(preliminary)["pass"]
    contract_pass = bool(
        count_contract
        and read_contract
        and scope_contract
        and hash_contract
        and formal_pass
    )
    outcome, selected_candidate, selected_scope, ranking, reasons = evaluate_r1_outcome(
        results, contract_pass=contract_pass
    )
    preliminary["outcome"] = outcome
    preliminary["selected_candidate"] = selected_candidate
    preliminary["selected_task_scope"] = selected_scope
    preliminary["candidate_ranking"] = ranking
    preliminary["outcome_reasons"] = reasons
    preliminary["formal_output_validation"] = validate_aggregate_formal_output(
        preliminary
    )
    if not preliminary["formal_output_validation"]["pass"]:
        raise RuntimeError(
            "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC: formal output contains forbidden keys"
        )
    output_hashes = _write_outputs(
        root,
        args=args,
        audit=preliminary,
        ledgers=[*eeg_ledgers, *text_ledgers],
    )
    verify_immutable_parent_r0(root)

    print(
        f"OUTCOME {outcome} selected={selected_candidate} scope={selected_scope} "
        f"reasons={reasons}"
    )
    for task in TASKS:
        for candidate, row in results[task].items():
            recovery = row.get("cross_recovery", {})
            print(
                f"RESULT task={task} candidate={candidate} "
                f"seen_semantic={row['seen']['metrics']['delta_semantic']['estimate']:.6f} "
                f"seen_family={row['seen']['family_detected']} "
                f"cross_semantic={row['cross']['metrics']['delta_semantic']['estimate']:.6f} "
                f"cross_family={row['cross']['family_detected']} "
                f"recovery={recovery.get('estimate')} ci={recovery.get('ci95')} "
                f"positive={recovery.get('positive_subject_count')} "
                f"pass={row.get('recovery_pass', False)}"
            )
    print(f"OUTPUT {args.contract_output.as_posix()} sha256={contract_hash}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        "SELF-CHECK SUMMARY "
        f"operations={len(fits)} eeg_v5={len(eeg_ledgers)} "
        f"text_ledgers={len(text_ledgers)} outer_reads=0 calibration_reads=0 "
        f"counts={count_contract} scope={scope_contract} hashes={hash_contract} "
        f"status={'PASS' if outcome != 'INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC' else 'FAIL'}"
    )
    return 0 if outcome != "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC" else 2


def _write_invalid_stub(args: argparse.Namespace, error: BaseException) -> None:
    root = args.project_root.resolve()
    payload = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "outcome": "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "error_type": type(error).__name__,
        "error": str(error),
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "next_task": None,
    }
    path = root / args.audit_json_output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_artifact(payload))
    markdown = (
        "# R1 inner diagnostic\n\n"
        "- Outcome: `INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC`\n"
        "- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`\n"
        "- Outer-test/calibration reads: `0/0`\n\n"
        f"Execution stopped: `{type(error).__name__}: {error}`\n"
    )
    (root / args.audit_md_output).write_text(markdown, encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        return execute(args)
    except BaseException as error:
        traceback.print_exc()
        try:
            _write_invalid_stub(args, error)
        except BaseException:
            traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
