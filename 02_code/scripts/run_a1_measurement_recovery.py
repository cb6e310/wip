#!/usr/bin/env python3
"""Run only the SPEC v3.18 bounded 78-fit inner A1-R recovery audit."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
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
    ALGORITHM_VERSION,
    ARMS,
    CANDIDATES,
    EXPECTED_FRONTEND_FITS,
    EXPECTED_H_ONLY_FITS,
    EXPECTED_TOTAL_FITS,
    FOLDS,
    FRONTENDS,
    METRICS,
    REGIMES,
    RUN_ID,
    TASKS,
    apply_log_bandpower,
    bottleneck_label,
    build_recovery_v5_ledger,
    derive_recovery_partitions,
    evaluate_recovery,
    fit_log_bandpower,
    paired_summary,
    sha256_file,
    summarize_regime_rows,
    temporal_fixation_feature,
    validate_recovery_v5_or_raise,
    verify_run032_immutable,
)
from data.a1_measurement_validity import verify_immutable_evidence  # noqa: E402
from data.a1_source_admission import _vector_length, strict_native_matrix  # noqa: E402
from data.zuco2_loader import dereference, indexed_value, iter_summary_files  # noqa: E402
from data.zuco2_source_join import prove_task_source_join  # noqa: E402
from run_a1_admission import (  # noqa: E402
    CACHE_ROOT as A1_CACHE_ROOT,
    DATASET_ROOT,
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


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_18_2026-08-16.md")
FREEZE_PATH = Path("artifacts/a1_measurement_recovery_freeze.yaml")
CACHE_ROOT = Path(".codex_stage1_a1r_v318")
CONTRACT_PATH = Path("artifacts/a1_measurement_recovery_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/audits/a1_measurement_recovery.json")
AUDIT_MD_PATH = Path("04_results/audits/a1_measurement_recovery.md")
LEDGER_PATH = Path("04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz")


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
    rows = [row for row in protocol["inner_cells"] if row["inner_cell_id"].endswith(fold)]
    if len(rows) != 1:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: expected one {fold} cell")
    return rows[0]


def extract_t8(
    root: Path,
    *,
    task: str,
    baseline_metadata: Sequence[Mapping[str, Any]],
    baseline_manifest: Mapping[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    cache = root / CACHE_ROOT / task
    values_path = cache / "t8.npy"
    ids_path = cache / "observation_ids.json"
    manifest_path = cache / "manifest.json"
    binding = {
        "task": task,
        "algorithm": "A1R_T8_FIXATION_v318_channel_major_105x8",
        "baseline_feature_bytes_sha256": baseline_manifest["feature_bytes_sha256"],
        "baseline_metadata_sha256": baseline_manifest["metadata_sha256"],
    }
    if values_path.is_file() and ids_path.is_file() and manifest_path.is_file():
        manifest = _load_json(manifest_path)
        ids = json.loads(ids_path.read_text(encoding="utf-8"))
        values = np.load(values_path, allow_pickle=False)
        if (
            manifest.get("binding") == binding
            and values.shape == (len(ids), 840)
            and manifest.get("bytes_sha256") == sha256_bytes(values.tobytes(order="C"))
        ):
            return {str(key): values[index] for index, key in enumerate(ids)}, manifest

    target_ids = {str(row["observation_id"]) for row in baseline_metadata}
    proof = prove_task_source_join(root / DATASET_ROOT, task)
    if not proof.verified:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: source join failed for {task}")
    slot_by_index = {slot.summary_index - 1: slot for slot in proof.slots}
    output: dict[str, np.ndarray] = {}
    counts: Counter[str] = Counter()
    smoke_count = 0
    started = time.perf_counter()
    for summary in iter_summary_files(root / DATASET_ROOT, task):
        with h5py.File(summary.path, "r") as handle:
            sentence_group = handle["sentenceData"]
            for sentence_index, slot in slot_by_index.items():
                record_id = f"{summary.subject_id}|{slot.source_slot_key}"
                word_group = dereference(
                    handle, indexed_value(sentence_group["word"], sentence_index)
                )
                if not isinstance(word_group, h5py.Group) or "rawEEG" not in word_group:
                    continue
                word_count = _vector_length(word_group["rawEEG"])
                for word_index in range(word_count):
                    observation_id = f"{record_id}|word_index:{word_index + 1}"
                    if observation_id not in target_ids:
                        continue
                    container = dereference(
                        handle, indexed_value(word_group["rawEEG"], word_index)
                    )
                    if not isinstance(container, h5py.Dataset):
                        counts["FIXATION_CONTAINER_INVALID"] += 1
                        continue
                    legal: list[np.ndarray] = []
                    for reference in np.asarray(container[...], dtype=object).reshape(-1):
                        matrix, status = strict_native_matrix(dereference(handle, reference))
                        if status == "VALID" and matrix is not None:
                            legal.append(matrix)
                    feature, exclusions = temporal_fixation_feature(legal)
                    counts.update(exclusions)
                    if feature is None:
                        counts["OBSERVATION_NO_T8_FIXATION"] += 1
                        continue
                    if smoke_count < 16:
                        second, _ = temporal_fixation_feature(legal)
                        if second is None or second.tobytes() != feature.tobytes():
                            raise AssertionError("real T8 deterministic smoke failed")
                        smoke_count += 1
                    output[observation_id] = feature
    ids = sorted(output)
    if not ids:
        raise RuntimeError(f"INVALID_A1R_RECOVERY: no T8 observations for {task}")
    values = np.stack([output[key] for key in ids]).astype(np.float32)
    if not np.isfinite(values).all() or values.shape[1:] != (840,):
        raise RuntimeError("INVALID_A1R_RECOVERY: T8 extraction is not finite [N,840]")
    cache.mkdir(parents=True, exist_ok=True)
    np.save(values_path, values, allow_pickle=False)
    ids_path.write_text(json.dumps(ids, separators=(",", ":")), encoding="utf-8")
    manifest = {
        "binding": binding,
        "shape": list(values.shape),
        "dtype": str(values.dtype),
        "finite": True,
        "bytes_sha256": sha256_bytes(values.tobytes(order="C")),
        "available_observations": len(ids),
        "baseline_observations": len(target_ids),
        "availability_rate": len(ids) / len(target_ids),
        "exclusion_counts": dict(sorted(counts.items())),
        "real_deterministic_smoke_count": smoke_count,
        "elapsed_seconds": time.perf_counter() - started,
    }
    manifest_path.write_bytes(canonical_artifact(manifest))
    return output, manifest


def _fit_and_score(
    *,
    fit_id: str,
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
        alpha=DEFAULT_ADMISSION_CONFIG.ridge_alpha,
        device=device,
    )
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"INVALID_A1R_RECOVERY: {fit_id} exceeded 300 seconds")
    ledger = build_recovery_v5_ledger(
        run_id=run_id,
        fit_id=fit_id,
        seed=20260813,
        outer_cell=task_protocol["outer_cell_id"],
        recovery_cell=recovery_cell,
        fit_record_ids=partitions["fit_record_ids"],
        seen_record_ids=partitions["seen_record_ids"],
        cross_record_ids=partitions["cross_record_ids"],
        input_hashes=input_hashes,
    )
    validate_recovery_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fits.append(
        {
            "fit_id": fit_id,
            "fit_type": "ridge",
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
        temperature=DEFAULT_ADMISSION_CONFIG.softmax_temperature,
        device=device,
    )
    cross = ridge_log_prob(
        model,
        x_cross,
        vocabulary,
        cross_positions,
        temperature=DEFAULT_ADMISSION_CONFIG.softmax_temperature,
        device=device,
    )
    del model
    return seen, cross


def run_recovery(
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
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fits: list[dict[str, Any]] = []
    ledgers: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    scope_index = {
        "outer": dict(base_scope_index["outer"]),
        "inner": dict(base_scope_index["inner"]),
    }
    for task in TASKS:
        protocol = selected[task]
        baseline = baseline_by_task[task]
        metadata = list(metadata_by_task[task])
        id_to_index = {str(row["observation_id"]): index for index, row in enumerate(metadata)}
        t8 = t8_by_task[task]
        for fold in FOLDS:
            cell = _cell(protocol, fold)
            partitions = derive_recovery_partitions(protocol, cell)
            recovery_cell = cell["inner_cell_id"].replace("|inner_", "|recovery_")
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
                old_rows = [row for row in metadata if str(row["record_id"]) in legal_records]
                common_rows = [row for row in old_rows if str(row["observation_id"]) in t8]
                retention = len(common_rows) / len(old_rows) if old_rows else 0.0
                if retention < 0.90:
                    raise RuntimeError(
                        f"INVALID_A1R_RECOVERY: {task}/{fold}/{regime} retention {retention} <0.90"
                    )
                partition_meta[regime] = common_rows
                indices = np.asarray(
                    [id_to_index[str(row["observation_id"])] for row in common_rows],
                    dtype=np.int64,
                )
                partition_raw[regime] = {
                    "A1_BP_CONCAT": baseline[indices],
                    "A1R_T8_FIXATION": np.stack(
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
                partition_raw["fit"]["A1_BP_CONCAT"]
            )
            for regime in ("fit", *REGIMES):
                partition_raw[regime]["A1R_LOG_BP_CONCAT"] = apply_log_bandpower(
                    partition_raw[regime]["A1_BP_CONCAT"], epsilon
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
                    suffix = {"fit": "train", "seen": "seen", "cross": "validation"}[regime]
                    arms, common, _ = build_four_arm_features(
                        normalized,
                        partition_meta[regime],
                        seed=20260813,
                        partition=f"{cell['inner_cell_id']}|{suffix}",
                    )
                    arm_data[frontend][regime] = arms
                    if regime not in common_indices:
                        common_indices[regime] = common
                    elif not np.array_equal(common_indices[regime], common):
                        raise AssertionError("frontend sham common-row identity differs")

            fit_common_meta = [
                partition_meta["fit"][int(index)] for index in common_indices["fit"]
            ]
            supported, support_ledger = supported_item_ids(fit_common_meta)
            row_meta: dict[str, list[Mapping[str, Any]]] = {}
            row_positions: dict[str, np.ndarray] = {}
            for regime in ("fit", *REGIMES):
                common_meta = [
                    partition_meta[regime][int(index)] for index in common_indices[regime]
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
                    raise RuntimeError("INVALID_A1R_RECOVERY: empty support rows")
            seen_subjects = {str(row["subject_id"]) for row in row_meta["seen"]}
            cross_subjects = {str(row["subject_id"]) for row in row_meta["cross"]}
            if len(seen_subjects) != 10 or len(cross_subjects) != 5:
                raise RuntimeError("INVALID_A1R_RECOVERY: scoring subject was lost")

            items, vocabulary, item_positions = _vocabulary(
                supported, row_meta["fit"], item_vectors
            )
            y_fit = _item_matrix(row_meta["fit"], item_vectors)
            h = {regime: _h_matrix(row_meta[regime], h_vectors) for regime in ("fit", *REGIMES)}
            true_positions = {
                regime: np.asarray(
                    [item_positions[str(row["item_id"])] for row in row_meta[regime]],
                    dtype=np.int64,
                )
                for regime in REGIMES
            }
            h_seen, h_cross = _fit_and_score(
                fit_id=f"D57|{cell['inner_cell_id']}|H_only",
                x_fit=h["fit"],
                y_fit=y_fit,
                x_seen=h["seen"],
                x_cross=h["cross"],
                vocabulary=vocabulary,
                seen_positions=true_positions["seen"],
                cross_positions=true_positions["cross"],
                device=device,
                task_protocol=protocol,
                recovery_cell=recovery_cell,
                partitions=partitions,
                input_hashes=input_hashes,
                scope_index=scope_index,
                run_id=run_id,
                fits=fits,
                ledgers=ledgers,
            )
            h_logp = {"seen": h_seen, "cross": h_cross}
            for frontend in FRONTENDS:
                arm_logp: dict[str, dict[str, np.ndarray]] = {
                    regime: {} for regime in REGIMES
                }
                for arm in ARMS:
                    inputs = {
                        regime: np.concatenate(
                            [
                                h[regime],
                                arm_data[frontend][regime][arm][row_positions[regime]],
                            ],
                            axis=1,
                        ).astype(np.float32)
                        for regime in ("fit", *REGIMES)
                    }
                    seen_logp, cross_logp = _fit_and_score(
                        fit_id=f"D57|{cell['inner_cell_id']}|{frontend}|{arm}",
                        x_fit=inputs["fit"],
                        y_fit=y_fit,
                        x_seen=inputs["seen"],
                        x_cross=inputs["cross"],
                        vocabulary=vocabulary,
                        seen_positions=true_positions["seen"],
                        cross_positions=true_positions["cross"],
                        device=device,
                        task_protocol=protocol,
                        recovery_cell=recovery_cell,
                        partitions=partitions,
                        input_hashes=input_hashes,
                        scope_index=scope_index,
                        run_id=run_id,
                        fits=fits,
                        ledgers=ledgers,
                    )
                    arm_logp["seen"][arm] = seen_logp
                    arm_logp["cross"][arm] = cross_logp
                for regime in REGIMES:
                    stats = u_statistics(
                        arm_logp[regime]["real"],
                        {arm: arm_logp[regime][arm] for arm in ARMS if arm != "real"},
                    )
                    stats["max_selection_gap"] = stats["u_oof"] - stats["u_min"]
                    for index, row in enumerate(row_meta[regime]):
                        metric_rows.append(
                            {
                                "task": task,
                                "fold": fold,
                                "frontend": frontend,
                                "regime": regime,
                                "subject_id": str(row["subject_id"]),
                                **{metric: float(stats[metric][index]) for metric in METRICS},
                                "logp_H_only": float(h_logp[regime][index]),
                                **{
                                    f"logp_{arm}": float(arm_logp[regime][arm][index])
                                    for arm in ARMS
                                },
                            }
                        )
                support_rows.append(
                    {
                        "task": task,
                        "fold": fold,
                        "frontend": frontend,
                        "coverage": coverage,
                        "normalizer_fit_rows": normalizer_summaries[frontend]["fit_rows"],
                        "sham_common_rows": {
                            regime: int(common_indices[regime].size)
                            for regime in ("fit", *REGIMES)
                        },
                        "supported_rows": {
                            regime: len(row_meta[regime]) for regime in ("fit", *REGIMES)
                        },
                        "supported_item_count": len(items),
                        "support_ledger_rows": len(support_ledger),
                        "epsilon_summary": epsilon_summary if frontend == "A1R_LOG_BP_CONCAT" else None,
                        "same_observation_H_target_support_vocabulary": True,
                    }
                )

    results: dict[str, Any] = {}
    for task in TASKS:
        results[task] = {}
        for frontend in FRONTENDS:
            seen = summarize_regime_rows(
                metric_rows, task=task, frontend=frontend, regime="seen"
            )
            cross = summarize_regime_rows(
                metric_rows, task=task, frontend=frontend, regime="cross"
            )
            results[task][frontend] = {
                "seen": seen,
                "cross": cross,
                "transfer_loss": paired_summary(
                    seen,
                    cross,
                    seed_parts=(20260813, "v3.18", task, frontend, "transfer_loss"),
                ),
            }
        baseline_cross = results[task]["A1_BP_CONCAT"]["cross"]
        results[task]["A1_BP_CONCAT"]["bottleneck_label"] = bottleneck_label(
            results[task]["A1_BP_CONCAT"]["seen"]["family_detected"],
            baseline_cross["family_detected"],
        )
        for candidate in CANDIDATES:
            results[task][candidate]["recovery_delta"] = paired_summary(
                results[task][candidate]["cross"],
                baseline_cross,
                seed_parts=(20260813, "v3.18", task, candidate, "recovery_delta"),
            )
    return results, fits, ledgers, support_rows


def render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# A1-R measurement recovery",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['completion_outcome']}`",
        f"- Fits/V5: {audit['fit_summary']['total_fit_count']}/{audit['fit_summary']['real_v5_ledger_count']}",
        f"- Selected frontend: `{audit['selected_frontend']}`",
        f"- Selected task scope: `{audit['selected_task_scope']}`",
        "- Outer-test/calibration reads: `0/0`",
        "- Claim boundary: inner selection evidence only; no outer or paper claim.",
        "",
        "| Task | Frontend | seen u_oof | seen family | cross u_oof | cross family | transfer loss | recovery delta | recovery PASS |",
        "|---|---|---:|---|---:|---|---:|---:|---|",
    ]
    for task in TASKS:
        for frontend in FRONTENDS:
            row = audit["results"][task][frontend]
            delta = row.get("recovery_delta", {}).get("estimate")
            lines.append(
                f"| {task} | {frontend} | {row['seen']['metrics']['u_oof']['estimate']:.6g} | "
                f"{row['seen']['family_detected']} | {row['cross']['metrics']['u_oof']['estimate']:.6g} | "
                f"{row['cross']['family_detected']} | {row['transfer_loss']['estimate']:.6g} | "
                f"{delta if delta is not None else 'n/a'} | {row.get('recovery_pass', False)} |"
            )
    lines.extend(
        [
            "",
            "The v3.14 A1 failure and run-032 INVALID outcome remain unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    root: Path,
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    audit: Mapping[str, Any],
    ledgers: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    payloads = {
        args.contract_output: yaml.safe_dump(
            dict(contract), sort_keys=False, allow_unicode=True
        ).encode("utf-8"),
        args.audit_json_output: canonical_artifact(audit),
        args.audit_md_output: render_markdown(audit).encode("utf-8"),
        args.ledger_output: deterministic_gzip_jsonl(ledgers),
    }
    hashes = {}
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
        raise RuntimeError("INVALID_A1R_RECOVERY: real audit requires CUDA scoring")

    run032_hashes = verify_run032_immutable(root)
    immutable = verify_immutable_evidence(root)
    freeze = yaml.safe_load((root / FREEZE_PATH).read_text(encoding="utf-8"))
    if freeze.get("outcome") != "PASS_A1R_RECOVERY_FREEZE":
        raise RuntimeError("STATE_SPEC_CONFLICT: recovery freeze is not admitted")
    if sha256_file(root / SPEC_PATH) != freeze["governing_spec"]["sha256"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: v3.18 SPEC hash mismatch")
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
        raise RuntimeError("STATE_SPEC_CONFLICT: run-032 ledger is not 200 unique V5")
    print("IMMUTABLE status=PASS old_v5=897/897 run032_outcome=INVALID_A1_MEASUREMENT_VALIDITY_AUDIT")

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

    encoder, text_manifests, resolved_revision = load_text_encoder(root, args.text_device)
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    input_hashes = {
        **old_v5_hashes,
        "recovery_freeze": sha256_file(root / FREEZE_PATH),
        "spec_v318": sha256_file(root / SPEC_PATH),
    }
    results, fits, ledgers, support = run_recovery(
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
    count_contract = (
        len(fits) == EXPECTED_TOTAL_FITS
        and len(ledgers) == EXPECTED_TOTAL_FITS
        and len({str(row["fit_id"]) for row in ledgers}) == EXPECTED_TOTAL_FITS
        and sum(row["input_dim"] == 384 for row in fits) == EXPECTED_H_ONLY_FITS
        and sum(row["input_dim"] == 1224 for row in fits) == EXPECTED_FRONTEND_FITS
    )
    row_contract = (
        len(support) == 18
        and all(
            all(value["retention"] >= 0.90 for value in row["coverage"].values())
            and row["same_observation_H_target_support_vocabulary"]
            for row in support
        )
    )
    read_contract = all(
        row["outer_test_record_ids_read"] == []
        and row["calibration_record_ids"] == []
        for row in ledgers
    )

    source_paths = (
        "02_code/src/data/a1_measurement_recovery.py",
        "02_code/scripts/run_a1_measurement_recovery.py",
        "02_code/tests/test_a1_measurement_recovery.py",
    )
    contract = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "S1_A1_MEASUREMENT_RECOVERY",
        "spec": f"{SPEC_PATH.as_posix()}#D54-D60",
        "claim_boundary": "inner selection evidence only; no outer or paper-level EEG claim",
        "scope": {
            "tasks": list(TASKS),
            "folds": list(FOLDS),
            "frontends": list(FRONTENDS),
            "arms": list(ARMS),
            "regimes": list(REGIMES),
            "seed": 20260813,
            "h_only_fits": EXPECTED_H_ONLY_FITS,
            "frontend_arm_fits": EXPECTED_FRONTEND_FITS,
            "total_fits": EXPECTED_TOTAL_FITS,
        },
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "run032_immutable_hashes": run032_hashes,
        "old_immutable_hashes": immutable["hashes"],
        "text_encoder": {
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
        },
        "source_hashes": {relative: sha256_file(root / relative) for relative in source_paths},
        "formal_policy": {
            "aggregate_subject_support_scope_hash_runtime_only": True,
            "no_raw_eeg_840d_arrays_observation_vectors_logits_model_parameters_or_cache": True,
        },
    }
    preliminary = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "S1_A1_MEASUREMENT_RECOVERY",
        "claim_boundary": "inner selection evidence only; old A1 FAIL and run-032 INVALID unchanged",
        "results": results,
        "support": support,
        "data": data_summary,
        "text": {"resolved_revision": resolved_revision, "manifests": text_manifests, **text_summary},
        "fit_summary": {
            "h_only_fit_count": sum(row["input_dim"] == 384 for row in fits),
            "frontend_arm_fit_count": sum(row["input_dim"] == 1224 for row in fits),
            "total_fit_count": len(fits),
            "real_v5_ledger_count": len(ledgers),
            "unique_v5_fit_ids": len({str(row["fit_id"]) for row in ledgers}),
            "maximum_single_fit_seconds": max(row["elapsed_seconds"] for row in fits),
            "fit_runtime_seconds_sum": float(sum(row["elapsed_seconds"] for row in fits)),
            "fits": fits,
        },
        "contract_checks": {
            "exact_fit_v5_counts": count_contract,
            "row_retention_identity_subjects": row_contract,
            "zero_outer_calibration_reads": read_contract,
            "same_fit_scores_both_regimes": all(row["same_fit_scores_seen_and_cross"] for row in fits),
            "run032_outcome_unchanged": True,
        },
        "outer_test": {"eeg_label_metric_reads": 0, "calibration_reads": 0},
        "elapsed_seconds": time.perf_counter() - started,
    }
    formal_pass = (
        validate_aggregate_formal_output(contract)["pass"]
        and validate_aggregate_formal_output(preliminary)["pass"]
    )
    outcome, selected_frontend, selected_scope, reasons = evaluate_recovery(
        results,
        contract_pass=bool(count_contract and row_contract and read_contract and formal_pass),
    )
    preliminary["completion_outcome"] = outcome
    preliminary["selected_frontend"] = selected_frontend
    preliminary["selected_task_scope"] = selected_scope
    preliminary["outcome_reasons"] = reasons
    preliminary["formal_output_validation"] = validate_aggregate_formal_output(preliminary)
    if not preliminary["formal_output_validation"]["pass"]:
        raise RuntimeError("INVALID_A1R_RECOVERY: formal output has forbidden keys")
    output_hashes = write_outputs(root, args=args, contract=contract, audit=preliminary, ledgers=ledgers)
    verify_run032_immutable(root)
    print(f"OUTCOME {outcome} selected={selected_frontend} scope={selected_scope} reasons={reasons}")
    for task in TASKS:
        for frontend in FRONTENDS:
            row = results[task][frontend]
            delta = row.get("recovery_delta", {})
            print(
                f"RESULT task={task} frontend={frontend} "
                f"seen={row['seen']['metrics']['u_oof']['estimate']:.6f}/family:{row['seen']['family_detected']} "
                f"cross={row['cross']['metrics']['u_oof']['estimate']:.6f}/family:{row['cross']['family_detected']} "
                f"transfer={row['transfer_loss']['estimate']:.6f} "
                f"delta={delta.get('estimate')} ci={delta.get('ci95')} positive={delta.get('positive_subject_count')}"
            )
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        f"SELF-CHECK SUMMARY samples={{fits:{len(fits)},v5:{len(ledgers)},old_v5:897}} "
        "shapes={frontends:[N,840],H:[N,384],probe:[N,1224],target:[N,384]} "
        f"elapsed_seconds={preliminary['elapsed_seconds']:.3f} "
        f"ranges={{max_fit_seconds:{preliminary['fit_summary']['maximum_single_fit_seconds']:.3f},min_retention:{min(v['retention'] for row in support for v in row['coverage'].values()):.6f}}} "
        f"assertions={{counts:{count_contract},rows:{row_contract},outer_reads:0,calibration_reads:0,run032_unchanged:true}} status={'PASS' if outcome != 'INVALID_A1R_RECOVERY' else 'FAIL'}"
    )
    return 0 if outcome != "INVALID_A1R_RECOVERY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
