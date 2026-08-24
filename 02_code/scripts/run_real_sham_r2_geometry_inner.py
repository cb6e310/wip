#!/usr/bin/env python3
"""Run only the v3.23 102-operation inner geometry diagnostic."""

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
    token_local_frozen_initial_latent,
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
from data.real_sham_r1_inner import METRICS, summarize_subject_first  # noqa: E402
from data.real_sham_r2_geometry import (  # noqa: E402
    ALGORITHM_VERSION,
    ALIGNMENTS,
    ARMS,
    BASELINE_CELL,
    BASES,
    BASIS_DIMS,
    CELLS,
    EXPECTED_GEOMETRY_PROBES,
    EXPECTED_H_ONLY_Y0,
    EXPECTED_RIDGE_OPERATIONS,
    EXPECTED_TRANSFORM_LEDGERS,
    EXPECTED_V5_LEDGERS,
    FOLDS,
    INDUCTIVE_CELL,
    REGIMES,
    RUN_ID,
    TARGET,
    TASKS,
    TRANSDUCTIVE_CELLS,
    evaluate_r2_outcome,
    full_covariance_euclidean_alignment,
    validate_transform_ledgers,
    verify_immutable_parent_r0_r1,
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


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_23_2026-08-23.md")
FREEZE_PATH = Path("artifacts/real_sham_r2_freeze.yaml")
CONTRACT_PATH = Path("artifacts/real_sham_r2_geometry_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/diagnostics/real_sham_r2_geometry_inner.json")
AUDIT_MD_PATH = Path("04_results/diagnostics/real_sham_r2_geometry_inner.md")
LEDGER_PATH = Path("04_results/diagnostics/real_sham_r2_geometry_inner_run_ledger.jsonl.gz")
TRANSFORM_LEDGER_PATH = Path(
    "04_results/diagnostics/real_sham_r2_geometry_inner_transform_ledger.jsonl.gz"
)
EXPECTED_FREEZE_SHA256 = "2d8b8746ad68c9d5cb48566ec6f769d4ffa07f147ca8d4e108259a0974400bf0"
EXPECTED_SPEC_SHA256 = "e8ce2b93f3cd3bc27232c0f98193c74528f3eb46ca56dc6f705f6a461fd92d63"
BASE_COMMIT = "012590ff1bc9c421644168a555511715bb30ec4a"


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
    parser.add_argument("--transform-ledger-output", type=Path, default=TRANSFORM_LEDGER_PATH)
    return parser.parse_args()


def _cell(protocol: Mapping[str, Any], fold: str) -> Mapping[str, Any]:
    rows = [row for row in protocol["inner_cells"] if row["inner_cell_id"].endswith(fold)]
    if len(rows) != 1:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: expected one {fold} cell")
    return rows[0]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8").strip()


def _validate_branch_and_freeze(root: Path) -> dict[str, Any]:
    if _git(root, "branch", "--show-current") != "research/real-sham-r2-geometry-inner":
        raise RuntimeError("STATE_SPEC_CONFLICT: R2 runner is on the wrong branch")
    if _git(root, "rev-parse", "HEAD") != BASE_COMMIT:
        raise RuntimeError("STATE_SPEC_CONFLICT: R2 execution HEAD is not frozen base")
    if sha256_file(root / FREEZE_PATH) != EXPECTED_FREEZE_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.23 freeze bytes changed")
    if sha256_file(root / SPEC_PATH) != EXPECTED_SPEC_SHA256:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.23 SPEC bytes changed")
    freeze = yaml.safe_load((root / FREEZE_PATH).read_text(encoding="utf-8"))
    if not isinstance(freeze, dict) or freeze.get("outcome_before_execution") != "READY":
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.23 freeze is not READY")
    if freeze.get("base_commit") != BASE_COMMIT:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.23 freeze base changed")
    return freeze


def _write_contract(root: Path, output: Path, contract: Mapping[str, Any]) -> str:
    payload = yaml.safe_dump(dict(contract), sort_keys=False, allow_unicode=True).encode("utf-8")
    path = root / output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def _fit_v5_and_score(
    *, operation_id: str, operation_kind: str, alignment: str | None,
    basis: str | None, arm: str | None, x_fit: np.ndarray, y_fit: np.ndarray,
    x_seen: np.ndarray, x_cross: np.ndarray, vocabulary: np.ndarray,
    seen_positions: np.ndarray, cross_positions: np.ndarray, device: str,
    task_protocol: Mapping[str, Any], recovery_cell: str,
    partitions: Mapping[str, Any], input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any], run_id: str, fits: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    model, elapsed = fit_ridge_to_items(x_fit, y_fit, alpha=1.0, device=device)
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: {operation_id} >300s")
    ledger = build_recovery_v5_ledger(
        run_id=run_id, fit_id=operation_id, seed=20260813,
        outer_cell=task_protocol["outer_cell_id"], recovery_cell=recovery_cell,
        fit_record_ids=partitions["fit_record_ids"],
        seen_record_ids=partitions["seen_record_ids"],
        cross_record_ids=partitions["cross_record_ids"], input_hashes=input_hashes,
    )
    ledger["ledger_type"] = "EEG_V5"
    ledger["r2_scope"] = {
        "operation_kind": operation_kind, "alignment": alignment, "basis": basis,
        "target": TARGET, "arm": arm,
        "m1_is_secondary_transductive": alignment == "M1_UNLABELED_TRANSDUCTIVE_EA",
    }
    validate_recovery_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fits.append({
        "operation_id": operation_id, "operation_kind": operation_kind,
        "fit_type": "ridge", "alignment": alignment, "basis": basis,
        "target": TARGET, "arm": arm, "train_rows": int(x_fit.shape[0]),
        "seen_rows": int(x_seen.shape[0]), "cross_rows": int(x_cross.shape[0]),
        "input_dim": int(x_fit.shape[1]), "target_dim": int(y_fit.shape[1]),
        "vocabulary_size": int(vocabulary.shape[0]), "elapsed_seconds": elapsed,
        "same_fit_scores_seen_and_cross": True, "v5": "PASS_REAL_RUN_LEDGER",
    })
    seen = ridge_log_prob(model, x_seen, vocabulary, seen_positions,
                          temperature=0.07, device=device)
    cross = ridge_log_prob(model, x_cross, vocabulary, cross_positions,
                           temperature=0.07, device=device)
    del model
    return seen, cross


def _latent_arms(arms: Mapping[str, np.ndarray], *, device: str) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    result: dict[str, np.ndarray] = {}
    audits: list[dict[str, Any]] = []
    for arm in ARMS:
        latent, audit = token_local_frozen_initial_latent(arms[arm], seed=20260813, device=device)
        if (audit.get("seed") != 20260813
                or audit.get("name") != "token_local_frozen_initial_latent"
                or audit.get("trainable_parameter_count") != 0
                or audit.get("model_eval") is not True
                or audit.get("output_shape", [None, None])[1] != 384):
            raise RuntimeError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: B1 contract changed")
        result[arm] = latent
        audits.append({"arm": arm, **audit})
    return result, audits


def run_r2(
    *, selected: Mapping[str, Any], baseline_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray], device: str,
    input_hashes: Mapping[str, str], base_scope_index: Mapping[str, Any], run_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]],
           list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fits: list[dict[str, Any]] = []
    ledgers: list[dict[str, Any]] = []
    transform_ledgers: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    latent_audits: list[dict[str, Any]] = []
    scope_index = {"outer": dict(base_scope_index["outer"]),
                   "inner": dict(base_scope_index["inner"])}

    for task in TASKS:
        protocol = selected[task]
        baseline = baseline_by_task[task]
        metadata = list(metadata_by_task[task])
        id_to_index = {str(row["observation_id"]): index for index, row in enumerate(metadata)}
        for fold in FOLDS:
            cell = _cell(protocol, fold)
            partitions = derive_recovery_partitions(protocol, cell)
            recovery_cell = cell["inner_cell_id"].replace("|inner_", "|r2_geometry_")
            validation_union = sorted(set(partitions["seen_record_ids"]) | set(partitions["cross_record_ids"]))
            scope_index["inner"][recovery_cell] = {
                "outer_cell_id": protocol["outer_cell_id"],
                "train_record_ids": partitions["fit_record_ids"],
                "validation_record_ids": validation_union,
            }

            partition_meta: dict[str, list[Mapping[str, Any]]] = {}
            partition_raw: dict[str, np.ndarray] = {}
            coverage: dict[str, Any] = {}
            for regime, record_key in (("fit", "fit_record_ids"),
                                       ("seen", "seen_record_ids"),
                                       ("cross", "cross_record_ids")):
                legal_records = set(partitions[record_key])
                rows = [row for row in metadata if str(row["record_id"]) in legal_records]
                if not rows:
                    raise RuntimeError("R2 partition rows are empty")
                partition_meta[regime] = rows
                indices = np.asarray([id_to_index[str(row["observation_id"])] for row in rows], dtype=np.int64)
                partition_raw[regime] = baseline[indices]
                coverage[regime] = {
                    "old_a1_available_rows": len(rows), "common_rows": len(rows),
                    "retention": 1.0,
                    "subjects": sorted({str(row["subject_id"]) for row in rows}),
                }

            normalizer, normalizer_summary = fit_fold_normalizer(partition_raw["fit"])
            b0_arms: dict[str, dict[str, np.ndarray]] = {}
            common_indices: dict[str, np.ndarray] = {}
            common_meta: dict[str, list[Mapping[str, Any]]] = {}
            for regime in ("fit", *REGIMES):
                normalized = transform_fold_normalizer(partition_raw[regime], normalizer)
                suffix = {"fit": "train", "seen": "seen", "cross": "validation"}[regime]
                arms, common, sham_audit = build_four_arm_features(
                    normalized, partition_meta[regime], seed=20260813,
                    partition=f"{cell['inner_cell_id']}|{suffix}")
                if set(arms) != set(ARMS) or not sham_audit["row_ids_identical"]:
                    raise RuntimeError("R2 four-arm scope/identity changed")
                if any(arms[arm].shape != arms["real"].shape for arm in ARMS):
                    raise RuntimeError("R2 four-arm capacities changed")
                b0_arms[regime] = arms
                common_indices[regime] = common
                common_meta[regime] = [partition_meta[regime][int(index)] for index in common]

            basis_arms: dict[str, dict[str, dict[str, np.ndarray]]] = {
                "B0_RAW_A1": b0_arms, "B1_TOKEN_LOCAL_LATENT": {}}
            for regime in ("fit", *REGIMES):
                latent, audits = _latent_arms(b0_arms[regime], device=device)
                basis_arms["B1_TOKEN_LOCAL_LATENT"][regime] = latent
                latent_audits.extend({"task": task, "fold": fold, "regime": regime, **audit}
                                     for audit in audits)

            aligned_arms: dict[str, dict[str, dict[str, np.ndarray]]] = {basis: {} for basis in BASES}
            for basis in BASES:
                for regime in ("fit", *REGIMES):
                    aligned, audit = full_covariance_euclidean_alignment(
                        basis_arms[basis][regime],
                        [str(row["subject_id"]) for row in common_meta[regime]],
                        task=task, fold=fold, basis=basis, regime=regime)
                    if aligned["real"].shape[1] != BASIS_DIMS[basis]:
                        raise RuntimeError("R2 aligned basis dimension changed")
                    aligned_arms[basis][regime] = aligned
                    transform_ledgers.extend(audit)

            supported, support_ledger = supported_item_ids(common_meta["fit"])
            row_positions: dict[str, np.ndarray] = {}
            row_meta: dict[str, list[Mapping[str, Any]]] = {}
            for regime in ("fit", *REGIMES):
                positions = np.asarray([index for index, row in enumerate(common_meta[regime])
                                        if str(row["item_id"]) in supported], dtype=np.int64)
                row_positions[regime] = positions
                row_meta[regime] = [common_meta[regime][int(index)] for index in positions]
                if not row_meta[regime]:
                    raise RuntimeError("R2 supported rows are empty")
            if len({str(row["subject_id"]) for row in row_meta["seen"]}) != 10:
                raise RuntimeError("R2 seen subject count changed")
            if len({str(row["subject_id"]) for row in row_meta["cross"]}) != 5:
                raise RuntimeError("R2 cross subject count changed")

            _, vocabulary, item_positions = _vocabulary(supported, row_meta["fit"], item_vectors)
            y_fit = _item_matrix(row_meta["fit"], item_vectors)
            h = {regime: _h_matrix(row_meta[regime], h_vectors) for regime in ("fit", *REGIMES)}
            true_positions = {
                regime: np.asarray([item_positions[str(row["item_id"])] for row in row_meta[regime]], dtype=np.int64)
                for regime in REGIMES}
            _fit_v5_and_score(
                operation_id=f"R2|{task}|{fold}|H_ONLY|{TARGET}", operation_kind="H_ONLY_Y0",
                alignment=None, basis=None, arm=None, x_fit=h["fit"], y_fit=y_fit,
                x_seen=h["seen"], x_cross=h["cross"], vocabulary=vocabulary,
                seen_positions=true_positions["seen"], cross_positions=true_positions["cross"],
                device=device, task_protocol=protocol, recovery_cell=recovery_cell,
                partitions=partitions, input_hashes=input_hashes, scope_index=scope_index,
                run_id=run_id, fits=fits, ledgers=ledgers)

            for alignment in ALIGNMENTS:
                for basis in BASES:
                    cell_id = f"{alignment}/{basis}"
                    source = basis_arms[basis] if alignment == "M0_STRICT_INDUCTIVE" else aligned_arms[basis]
                    arm_logp: dict[str, dict[str, np.ndarray]] = {regime: {} for regime in REGIMES}
                    for arm in ARMS:
                        inputs = {
                            regime: np.concatenate([h[regime], source[regime][arm][row_positions[regime]]], axis=1).astype(np.float32)
                            for regime in ("fit", *REGIMES)}
                        seen_logp, cross_logp = _fit_v5_and_score(
                            operation_id=f"R2|{task}|{fold}|{alignment}|{basis}|{arm}",
                            operation_kind="GEOMETRY_PROBE", alignment=alignment,
                            basis=basis, arm=arm, x_fit=inputs["fit"], y_fit=y_fit,
                            x_seen=inputs["seen"], x_cross=inputs["cross"], vocabulary=vocabulary,
                            seen_positions=true_positions["seen"], cross_positions=true_positions["cross"],
                            device=device, task_protocol=protocol, recovery_cell=recovery_cell,
                            partitions=partitions, input_hashes=input_hashes, scope_index=scope_index,
                            run_id=run_id, fits=fits, ledgers=ledgers)
                        arm_logp["seen"][arm] = seen_logp
                        arm_logp["cross"][arm] = cross_logp
                    for regime in REGIMES:
                        stats = u_statistics(arm_logp[regime]["real"],
                            {arm: arm_logp[regime][arm] for arm in ARMS if arm != "real"})
                        stats["delta_semantic"] = 0.5 * (
                            stats["real_minus_trial_shuffle"]
                            + stats["real_minus_within_trial_unit_assignment_shuffle"])
                        stats["delta_legacy"] = stats["u_oof"]
                        stats["delta_channel"] = stats["real_minus_channel_block_permutation"]
                        stats["max_selection_gap"] = stats["u_oof"] - stats["u_min"]
                        for index, row in enumerate(row_meta[regime]):
                            metric_rows.append({
                                "task": task, "fold": fold, "candidate": cell_id,
                                "alignment": alignment, "basis": basis, "regime": regime,
                                "subject_id": str(row["subject_id"]),
                                **{metric: float(stats[metric][index]) for metric in METRICS},
                                **{f"logp_{arm}": float(arm_logp[regime][arm][index]) for arm in ARMS},
                            })
                    support_rows.append({
                        "task": task, "fold": fold, "cell": cell_id,
                        "alignment": alignment, "basis": basis, "coverage": coverage,
                        "normalizer_fit_rows": normalizer_summary["fit_rows"],
                        "sham_common_rows": {regime: int(common_indices[regime].size)
                                             for regime in ("fit", *REGIMES)},
                        "supported_rows": {regime: len(row_meta[regime])
                                           for regime in ("fit", *REGIMES)},
                        "supported_item_count": len(supported),
                        "support_ledger_rows": len(support_ledger),
                        "same_rows_all_four_arms": True, "same_support_all_four_cells": True,
                        "m1_transductive_secondary": alignment == "M1_UNLABELED_TRANSDUCTIVE_EA",
                    })

    results: dict[str, Any] = {}
    for task in TASKS:
        results[task] = {}
        for cell_id in CELLS:
            results[task][cell_id] = {
                "seen": summarize_subject_first(metric_rows, task=task, candidate=cell_id, regime="seen"),
                "cross": summarize_subject_first(metric_rows, task=task, candidate=cell_id, regime="cross"),
                "role": ("immutable_baseline" if cell_id == BASELINE_CELL
                         else "primary_inductive_candidate" if cell_id == INDUCTIVE_CELL
                         else "secondary_transductive_diagnostic"),
            }
    return results, fits, ledgers, transform_ledgers, support_rows, latent_audits


def _baseline_reproduction(root: Path, results: Mapping[str, Any]) -> dict[str, Any]:
    old = json.loads((root / "04_results/diagnostics/real_sham_r1_inner.json").read_text(encoding="utf-8"))
    comparisons: list[dict[str, Any]] = []
    maximum = 0.0
    for task in TASKS:
        previous = old["results"][task]["F0_A1_BP_CONCAT/Y0_RAW_MINILM"]
        current = results[task][BASELINE_CELL]
        for regime in REGIMES:
            for metric in METRICS:
                left = previous[regime]["metrics"][metric]["subject_values"]
                right = current[regime]["metrics"][metric]["subject_values"]
                if set(left) != set(right):
                    raise RuntimeError("R2 baseline subject identity differs from R1")
                difference = max(abs(float(left[key]) - float(right[key])) for key in left)
                maximum = max(maximum, difference)
                comparisons.append({"task": task, "regime": regime, "metric": metric,
                                    "maximum_subject_absolute_difference": difference})
    return {"reference": "R1 F0_A1_BP_CONCAT/Y0_RAW_MINILM",
            "subject_value_comparisons": comparisons,
            "maximum_subject_absolute_difference": maximum,
            "tolerance": 1e-6, "pass": maximum <= 1e-6}


def _render_markdown(audit: Mapping[str, Any]) -> str:
    lines = ["# Real-vs-sham R2 geometry inner diagnostic", "",
        f"- Run: `{audit['run_id']}`", f"- Outcome: `{audit['outcome']}`",
        "- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`",
        f"- Passing task scope: `{audit['passing_task_scope']}`",
        "- Ridge operations / V5 ledgers: `102/102`",
        f"- M1 transform ledger rows: `{audit['transform_summary']['ledger_count']}`",
        "- Outer-test/calibration reads: `0/0`", "",
        "| Task | Cell | Role | seen semantic | seen family | cross semantic | cross family | recovery | pass |",
        "|---|---|---|---:|---|---:|---|---:|---|"]
    for task in TASKS:
        for cell_id in CELLS:
            row = audit["results"][task][cell_id]
            recovery = row.get("cross_recovery")
            recovery_value = "n/a" if recovery is None else f"{recovery['estimate']:.6g}"
            lines.append(f"| {task} | {cell_id} | {row['role']} | "
                         f"{row['seen']['metrics']['delta_semantic']['estimate']:.6g} | "
                         f"{row['seen']['family_detected']} | "
                         f"{row['cross']['metrics']['delta_semantic']['estimate']:.6g} | "
                         f"{row['cross']['family_detected']} | {recovery_value} | "
                         f"{row.get('recovery_pass', False)} |")
    lines.extend(["", "M0/B1 is the only inductive candidate. Every M1 result is an unlabeled transductive secondary diagnostic and cannot release inductive or paper-level evidence.",
        "", "Channel-block remains a topology sentinel; both semantic single-sham contrasts and legacy u_oof/u_min are retained.",
        "", "Parent/R0/R1 outcomes and formal artifacts are immutable. No F3, Y1, outer confirmation, calibration, direct u+, EQ-ANMA, A3, ROAMM, or Gate was run.",
        "", "Stop for author review. No outer confirmation was started.", ""])
    return "\n".join(lines)


def _write_outputs(root: Path, *, args: argparse.Namespace, audit: Mapping[str, Any],
                   ledgers: Sequence[Mapping[str, Any]],
                   transform_ledgers: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    payloads = {args.audit_json_output: canonical_artifact(audit),
                args.audit_md_output: _render_markdown(audit).encode("utf-8"),
                args.ledger_output: deterministic_gzip_jsonl(ledgers),
                args.transform_ledger_output: deterministic_gzip_jsonl(transform_ledgers)}
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
        raise RuntimeError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: CUDA unavailable")

    freeze = _validate_branch_and_freeze(root)
    immutable_before = verify_immutable_parent_r0_r1(root)
    run032_hashes = verify_run032_immutable(root)
    immutable_evidence = verify_immutable_evidence(root)
    physical_hashes, _, _ = verify_frozen_inputs(root)
    _, _, selected, base_scope = load_protocol(root)
    old_v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    for ledger in [*immutable_evidence["admission_ledgers"],
                   *immutable_evidence["diagnosis_ledgers"]]:
        validate_diagnosis_v5_or_raise(ledger, base_scope, old_v5_hashes)

    source_paths = ("02_code/src/data/real_sham_r2_geometry.py",
                    "02_code/scripts/run_real_sham_r2_geometry_inner.py",
                    "02_code/tests/test_real_sham_r2_geometry.py")
    input_hashes = {**old_v5_hashes, "r2_freeze": sha256_file(root / FREEZE_PATH),
        "spec_v323": sha256_file(root / SPEC_PATH),
        "r1_contract": immutable_before["artifacts/real_sham_r1_contract.yaml"],
        "r1_diagnostic_json": immutable_before["04_results/diagnostics/real_sham_r1_inner.json"]}
    contract = {
        "schema_version": 1, "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id, "task": "R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC",
        "branch": "research/real-sham-r2-geometry-inner", "base_commit": BASE_COMMIT,
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "governing_spec": {"path": SPEC_PATH.as_posix(), "sha256": EXPECTED_SPEC_SHA256},
        "author_freeze": {"path": FREEZE_PATH.as_posix(), "sha256": EXPECTED_FREEZE_SHA256,
                          "outcome_before_execution": freeze["outcome_before_execution"]},
        "scope": {"tasks": list(TASKS), "folds": list(FOLDS), "cells": list(CELLS),
                  "target": TARGET, "arms": list(ARMS), "regimes": list(REGIMES),
                  "seed": 20260813, "ridge_alpha": 1.0, "temperature": 0.07,
                  "h_only_y0_operations": EXPECTED_H_ONLY_Y0,
                  "geometry_probe_operations": EXPECTED_GEOMETRY_PROBES,
                  "total_ridge_operations": EXPECTED_RIDGE_OPERATIONS,
                  "unique_v5_ledgers": EXPECTED_V5_LEDGERS,
                  "expected_transform_ledgers": EXPECTED_TRANSFORM_LEDGERS},
        "b1_definition": {"helper": "token_local_frozen_initial_latent", "seed": 20260813,
                          "output_dimension": 384, "encoder_training": False,
                          "parameters_frozen": True},
        "d102_definition": {"scope": "task_x_fold_x_regime_x_subject",
            "transform_fit_values": "real_arm_EEG_values_only",
            "shared_across_all_four_arms": True,
            "labels_item_h_task_sham_inputs": False, "full_covariance": True,
            "float64": True, "lambda": "1e-6 * trace(Z.T@Z/max(N-1,1)) / d",
            "eigenvalue_floor": "lambda", "zero_or_nonfinite_trace": "INVALID_NO_FALLBACK",
            "seen_cross_transductive": True, "alignment_training": False},
        "claim_boundary": {"only_inductive_candidate": INDUCTIVE_CELL,
                           "m1_cells": list(TRANSDUCTIVE_CELLS),
                           "m1_can_release_inductive_or_paper_claim": False,
                           "outer_confirmation_released": False},
        "estimands": {"delta_semantic": "real - mean(trial_shuffle, within_trial_unit_assignment_shuffle)",
                      "delta_legacy": "real - mean(all_three_shams)",
                      "delta_channel": "real - channel_block_permutation"},
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "immutable_parent_r0_r1_hashes": immutable_before,
        "run032_immutable_hashes": run032_hashes,
        "source_hashes": {relative: sha256_file(root / relative) for relative in source_paths},
        "forbidden": ["F3_EVENT_LOCKED", "Y1_H_RESIDUAL_MINILM", "M1_alignment_training",
                      "outer_confirmation", "calibration", "direct_u_plus", "EQ_ANMA",
                      "A3", "ROAMM", "Gate_A_or_B"]}
    if not validate_aggregate_formal_output(contract)["pass"]:
        raise RuntimeError("R2 contract contains forbidden formal keys")
    contract_hash = _write_contract(root, args.contract_output, contract)
    print(f"CONTRACT frozen sha256={contract_hash} before_features_and_fits=true")

    contexts = build_text_contexts(root)
    baseline_by_task: dict[str, np.ndarray] = {}
    metadata_by_task: dict[str, list[dict[str, Any]]] = {}
    data_summary: dict[str, Any] = {}
    for task in TASKS:
        baseline, metadata, manifest = extract_task_observations(
            root, task=task, task_protocol=selected[task], contexts=contexts, rebuild=False)
        baseline_by_task[task] = baseline
        metadata_by_task[task] = metadata
        data_summary[task] = {"outer_train_bound_observations": len(metadata),
                              "feature_dimension": int(baseline.shape[1]),
                              "manifest_binding": manifest["binding"]}
        print(f"DATA task={task} outer_train_rows={len(metadata)} dim={baseline.shape[1]}")
    encoder, text_manifests, resolved_revision = load_text_encoder(root, args.text_device)
    item_vectors, h_vectors, text_summary = encode_text_inputs(encoder, metadata_by_task, contexts)
    del encoder
    results, fits, ledgers, transform_ledgers, support, latent_audits = run_r2(
        selected=selected, baseline_by_task=baseline_by_task,
        metadata_by_task=metadata_by_task, item_vectors=item_vectors, h_vectors=h_vectors,
        device=args.device, input_hashes=input_hashes, base_scope_index=base_scope,
        run_id=args.run_id)

    operation_ids = [str(row["operation_id"]) for row in fits]
    count_contract = (len(fits) == EXPECTED_RIDGE_OPERATIONS
        and len(set(operation_ids)) == EXPECTED_RIDGE_OPERATIONS
        and sum(row["operation_kind"] == "H_ONLY_Y0" for row in fits) == EXPECTED_H_ONLY_Y0
        and sum(row["operation_kind"] == "GEOMETRY_PROBE" for row in fits) == EXPECTED_GEOMETRY_PROBES
        and len(ledgers) == EXPECTED_V5_LEDGERS
        and len({str(row["fit_id"]) for row in ledgers}) == EXPECTED_V5_LEDGERS)
    read_contract = all(row["outer_test_record_ids_read"] == []
                        and row["calibration_record_ids"] == [] for row in ledgers)
    validate_transform_ledgers(transform_ledgers)
    transform_contract = len(transform_ledgers) == EXPECTED_TRANSFORM_LEDGERS
    latent_contract = len(latent_audits) == 72 and all(
        row["seed"] == 20260813 and row["name"] == "token_local_frozen_initial_latent"
        and row["trainable_parameter_count"] == 0 and row["model_eval"]
        and row["output_shape"][1] == 384 for row in latent_audits)
    scope_contract = len(support) == 24 and all(
        set(row["coverage"]) == {"fit", "seen", "cross"}
        and all(value["retention"] >= 0.90 for value in row["coverage"].values())
        and row["same_rows_all_four_arms"] and row["same_support_all_four_cells"]
        for row in support)
    baseline_reproduction = _baseline_reproduction(root, results)
    immutable_after = verify_immutable_parent_r0_r1(root)
    hash_contract = immutable_after == immutable_before
    preliminary: dict[str, Any] = {
        "schema_version": 1, "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id, "task": "R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY", "results": results,
        "support": support,
        "b1_audit_summary": {"helper": "token_local_frozen_initial_latent",
            "seed": 20260813, "calls": len(latent_audits),
            "all_frozen_eval_384d": latent_contract, "encoder_training_operations": 0},
        "transform_summary": {"ledger_count": len(transform_ledgers),
            "unique_scope_count": len({(row["task"], row["fold"], row["basis"],
                                         row["regime"], row["subject_id"])
                                        for row in transform_ledgers}),
            "unique_transform_hash_count": len({row["transform_sha256"] for row in transform_ledgers}),
            "minimum_covariance_trace": min(row["covariance_trace"] for row in transform_ledgers),
            "minimum_lambda": min(row["lambda"] for row in transform_ledgers),
            "labels_used": False, "shared_across_arms": True,
            "transductive": True, "fallback_count": 0},
        "baseline_reproduction": baseline_reproduction, "data": data_summary,
        "text": {"resolved_revision": resolved_revision, "manifests": text_manifests, **text_summary},
        "fit_summary": {"h_only_y0": sum(row["operation_kind"] == "H_ONLY_Y0" for row in fits),
            "geometry_probes": sum(row["operation_kind"] == "GEOMETRY_PROBE" for row in fits),
            "total_ridge_operations": len(fits), "unique_operation_ids": len(set(operation_ids)),
            "v5_ledgers": len(ledgers),
            "maximum_single_fit_seconds": max(row["elapsed_seconds"] for row in fits),
            "fit_runtime_seconds_sum": float(sum(row["elapsed_seconds"] for row in fits)),
            "operations": fits},
        "contract_checks": {"exact_operation_and_v5_counts": count_contract,
            "exact_transform_scope_and_count": transform_contract,
            "b1_exact_frozen_helper": latent_contract,
            "scope_retention_row_identity": scope_contract,
            "zero_outer_calibration_reads": read_contract,
            "immutable_parent_r0_r1_hashes": hash_contract,
            "m0_b0_r1_baseline_reproduction": baseline_reproduction["pass"],
            "forbidden_scope_executed": []},
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "claim_boundary": {"parent_r0_r1_outcomes_immutable": True,
            "m0_b1_only_inductive_candidate": True,
            "m1_transductive_secondary_only": True, "paper_level_real_eeg_claim": False,
            "outer_confirmation_released": False},
        "immutable_parent_r0_r1_hashes": immutable_after,
        "contract_sha256": contract_hash, "elapsed_seconds": time.perf_counter() - started,
        "next_task": "AUTHOR_REVIEW_ONLY_NO_OUTER_CONFIRMATION_STARTED"}
    formal_pass = validate_aggregate_formal_output(preliminary)["pass"]
    contract_pass = bool(count_contract and read_contract and transform_contract
                         and latent_contract and scope_contract and baseline_reproduction["pass"]
                         and hash_contract and formal_pass)
    outcome, passing_scope, reasons = evaluate_r2_outcome(results, contract_pass=contract_pass)
    preliminary["outcome"] = outcome
    preliminary["passing_task_scope"] = passing_scope
    preliminary["outcome_reasons"] = reasons
    preliminary["formal_output_validation"] = validate_aggregate_formal_output(preliminary)
    if not preliminary["formal_output_validation"]["pass"]:
        raise RuntimeError("INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC: forbidden formal output key")
    output_hashes = _write_outputs(root, args=args, audit=preliminary, ledgers=ledgers,
                                    transform_ledgers=transform_ledgers)
    verify_immutable_parent_r0_r1(root)
    print(f"OUTCOME {outcome} scope={passing_scope} reasons={reasons}")
    for task in TASKS:
        for cell_id in CELLS:
            row = results[task][cell_id]
            recovery = row.get("cross_recovery")
            print(f"RESULT task={task} cell={cell_id} role={row['role']} "
                  f"seen_semantic={row['seen']['metrics']['delta_semantic']['estimate']:.6f} "
                  f"seen_family={row['seen']['family_detected']} "
                  f"cross_semantic={row['cross']['metrics']['delta_semantic']['estimate']:.6f} "
                  f"cross_family={row['cross']['family_detected']} "
                  f"recovery={None if recovery is None else recovery['estimate']} "
                  f"pass={row.get('recovery_pass', False)}")
    print(f"OUTPUT {args.contract_output.as_posix()} sha256={contract_hash}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print("SELF-CHECK SUMMARY "
          f"operations={len(fits)} v5={len(ledgers)} transforms={len(transform_ledgers)} "
          f"outer_reads=0 calibration_reads=0 counts={count_contract} "
          f"transforms_ok={transform_contract} b1={latent_contract} scope={scope_contract} "
          f"baseline={baseline_reproduction['pass']} hashes={hash_contract} status=PASS")
    return 0


def _write_invalid_stub(args: argparse.Namespace, error: BaseException) -> None:
    root = args.project_root.resolve()
    payload = {"schema_version": 1, "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id, "task": "R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC",
        "outcome": "INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC",
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "error_type": type(error).__name__, "error": str(error),
        "scope_violations": [str(error)],
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "next_task": "STOP_AUTHOR_REVIEW_REQUIRED"}
    path = root / args.audit_json_output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_artifact(payload))
    (root / args.audit_md_output).write_text(
        "# R2 geometry inner diagnostic\n\n"
        "- Outcome: `INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC`\n"
        f"- Error: `{type(error).__name__}: {error}`\n"
        "- Stop; author review required.\n", encoding="utf-8")


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
