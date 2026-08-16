#!/usr/bin/env python3
"""Run only the SPEC v3.15 D42 A1 failure-diagnosis positive controls."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
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
    SEEDS,
    build_four_arm_features,
    build_v5_ledger,
    canonical_artifact,
    deterministic_gzip_jsonl,
    deterministic_item_clusters,
    fit_fold_normalizer,
    fit_ridge_to_items,
    ridge_log_prob,
    sha256_bytes,
    supported_item_ids,
    transform_fold_normalizer,
)
from data.a1_failure_diagnosis import (  # noqa: E402
    ALGORITHM_VERSION,
    BASES,
    EXPECTED_FIT_COUNTS,
    OLD_ARTIFACT_HASHES,
    OLD_IMPLEMENTATION_HASHES,
    RUN_ID,
    TASKS,
    class_support_summary,
    derive_existing_failure_summary,
    evaluate_completion,
    oracle_input,
    planned_state_transition,
    ridge_top1_positions,
    sha256_file,
    summarize_a_a3_positive_control,
    summarize_scorer_positive_control,
    validate_aggregate_formal_output,
    validate_diagnosis_v5_or_raise,
    validate_fold_roles,
    verify_old_evidence,
)
from run_a1_admission import (  # noqa: E402
    FROZEN_INPUTS,
    V5_INPUT_KEYS,
    _fit_logistic_with_ledger,
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


SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_15_2026-08-16.md")
CONTRACT_PATH = Path("artifacts/a1_failure_diagnosis_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/audits/a1_failure_diagnosis.json")
AUDIT_MD_PATH = Path("04_results/audits/a1_failure_diagnosis.md")
LEDGER_PATH = Path("04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz")


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


def _prepare_cell(
    *,
    cell: Mapping[str, Any],
    features: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
    seed: int,
) -> dict[str, Any]:
    train_global = _indices_for_records(metadata, cell["train_record_ids"])
    validation_global = _indices_for_records(metadata, cell["validation_record_ids"])
    train_rows = _subset(metadata, train_global)
    validation_rows = _subset(metadata, validation_global)
    supported, _ = supported_item_ids(train_rows)
    fit_mask = np.asarray([row["item_id"] in supported for row in train_rows])
    validation_mask = np.asarray([row["item_id"] in supported for row in validation_rows])
    normalizer, normalizer_summary = fit_fold_normalizer(features[train_global])
    train_normalized = transform_fold_normalizer(features[train_global], normalizer)
    validation_normalized = transform_fold_normalizer(features[validation_global], normalizer)
    _, train_common, train_audit = build_four_arm_features(
        train_normalized,
        train_rows,
        seed=seed,
        partition=f"{cell['inner_cell_id']}|train",
    )
    _, validation_common, validation_audit = build_four_arm_features(
        validation_normalized,
        validation_rows,
        seed=seed,
        partition=f"{cell['inner_cell_id']}|validation",
    )
    fit_local = np.asarray(
        [index for index in train_common if fit_mask[index]], dtype=np.int64
    )
    score_local = np.asarray(
        [index for index in validation_common if validation_mask[index]], dtype=np.int64
    )
    if fit_local.size < 2 or score_local.size < 1:
        raise RuntimeError(
            f"INVALID_A1_FAILURE_DIAGNOSIS: empty rows in {cell['inner_cell_id']} seed {seed}"
        )
    fit_rows = [train_rows[index] for index in fit_local]
    score_rows = [validation_rows[index] for index in score_local]
    role_checks = validate_fold_roles(
        inner_train_record_ids=cell["train_record_ids"],
        inner_validation_record_ids=cell["validation_record_ids"],
        cluster_fit_record_ids=[row["record_id"] for row in fit_rows],
        scoring_record_ids=[row["record_id"] for row in score_rows],
    )
    return {
        "supported": supported,
        "fit_rows": fit_rows,
        "score_rows": score_rows,
        "normalizer": normalizer_summary,
        "train_common_rows": int(train_common.size),
        "validation_common_rows": int(validation_common.size),
        "train_common_support_rate": train_audit["common_support_rate"],
        "validation_common_support_rate": validation_audit["common_support_rate"],
        "role_checks": role_checks,
    }


def run_a_a3_positive_controls(
    *,
    selected: Mapping[str, Any],
    features_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fit_summaries: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    results: dict[str, Any] = {}
    support: dict[str, Any] = {}
    for task in TASKS:
        truth: list[int] = []
        predictions: list[int] = []
        subjects: list[str] = []
        fold_support: list[dict[str, Any]] = []
        protocol = selected[task]
        for cell in protocol["inner_cells"]:
            for seed in SEEDS:
                prepared = _prepare_cell(
                    cell=cell,
                    features=features_by_task[task],
                    metadata=metadata_by_task[task],
                    seed=seed,
                )
                fit_rows = prepared["fit_rows"]
                score_rows = prepared["score_rows"]
                items, embedding_matrix, item_positions = _vocabulary(
                    prepared["supported"], fit_rows, item_vectors
                )
                cluster_labels, _ = deterministic_item_clusters(embedding_matrix)
                train_labels = np.asarray(
                    [cluster_labels[item_positions[str(row["item_id"])]] for row in fit_rows],
                    dtype=np.int64,
                )
                scoring_labels = np.asarray(
                    [cluster_labels[item_positions[str(row["item_id"])]] for row in score_rows],
                    dtype=np.int64,
                )
                class_support = class_support_summary(train_labels, scoring_labels)
                item_train = _item_matrix(fit_rows, item_vectors)
                # H is a zero-use placeholder for the A-A3 item-only role; the
                # helper makes the oracle branch explicit and rejects all other
                # roles rather than allowing item embeddings into an EEG path.
                x_train = oracle_input(
                    np.zeros((len(fit_rows), 384), dtype=np.float32),
                    item_train,
                    role="a_a3_construct_validity_oracle_item",
                )
                x_validation = oracle_input(
                    np.zeros((len(score_rows), 384), dtype=np.float32),
                    _item_matrix(score_rows, item_vectors),
                    role="a_a3_construct_validity_oracle_item",
                )
                before = len(fit_summaries)
                predicted = _fit_logistic_with_ledger(
                    fit_id=f"D42-A-A3|{cell['inner_cell_id']}|seed{seed}|oracle_item",
                    seed=seed,
                    x_train=x_train,
                    y_train=train_labels,
                    x_validation=x_validation,
                    device=device,
                    task_protocol=protocol,
                    inner_cell=cell,
                    input_hashes=input_hashes,
                    scope_index=scope_index,
                    run_id=run_id,
                    ledgers=ledgers,
                    fit_summaries=fit_summaries,
                    fit_record_ids=[row["record_id"] for row in fit_rows],
                    scoring_record_ids=[row["record_id"] for row in score_rows],
                )
                if len(fit_summaries) != before + 1:
                    raise AssertionError("A-A3 positive control did not create exactly one fit")
                fit_summaries[-1].update(
                    {
                        "task": task,
                        "inner_cell": cell["inner_cell_id"],
                        "role": "oracle_construct_validity_positive_control_not_eeg_evidence",
                    }
                )
                if fit_summaries[-1]["class_count"] != 8:
                    raise RuntimeError(
                        f"INVALID_A1_FAILURE_DIAGNOSIS: {cell['inner_cell_id']} seed {seed} has "
                        f"{fit_summaries[-1]['class_count']} train classes"
                    )
                truth.extend(scoring_labels.tolist())
                predictions.extend(np.asarray(predicted, dtype=np.int64).tolist())
                subjects.extend(str(row["subject_id"]) for row in score_rows)
                fold_support.append(
                    {
                        "inner_cell": cell["inner_cell_id"],
                        "seed": seed,
                        "supported_item_count": len(items),
                        **class_support,
                        "normalizer_fit_rows": prepared["normalizer"]["fit_rows"],
                        "train_four_arm_common_rows": len(fit_rows),
                        "scoring_four_arm_common_rows": len(score_rows),
                        "train_common_support_rate": prepared["train_common_support_rate"],
                        "validation_common_support_rate": prepared[
                            "validation_common_support_rate"
                        ],
                        "role_checks": prepared["role_checks"],
                    }
                )
        results[task] = summarize_a_a3_positive_control(
            task=task,
            truth=truth,
            predictions=predictions,
            subject_ids=subjects,
        )
        support[task] = fold_support
    return results, support


def _fit_scorer_with_ledger(
    *,
    fit_id: str,
    role: str,
    seed: int,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    vocabulary: np.ndarray,
    true_positions: np.ndarray,
    device: str,
    task_protocol: Mapping[str, Any],
    inner_cell: Mapping[str, Any],
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fit_record_ids: Sequence[str],
    scoring_record_ids: Sequence[str],
    fit_summaries: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    model, elapsed = fit_ridge_to_items(
        x_train,
        y_train,
        alpha=DEFAULT_ADMISSION_CONFIG.ridge_alpha,
        device=device,
    )
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"INVALID_A1_FAILURE_DIAGNOSIS: fit {fit_id} exceeded 300 seconds")
    ledger = build_v5_ledger(
        run_id=run_id,
        fit_id=fit_id,
        seed=seed,
        outer_cell=task_protocol["outer_cell_id"],
        inner_cell=inner_cell["inner_cell_id"],
        fit_record_ids=fit_record_ids,
        validation_record_ids=inner_cell["validation_record_ids"],
        scoring_record_ids=scoring_record_ids,
        input_hashes=input_hashes,
    )
    validate_diagnosis_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fit_summaries.append(
        {
            "fit_id": fit_id,
            "fit_type": "ridge",
            "role": role,
            "seed": seed,
            "train_rows": int(x_train.shape[0]),
            "validation_rows": int(x_validation.shape[0]),
            "input_dim": int(x_train.shape[1]),
            "target_dim": int(y_train.shape[1]),
            "vocabulary_size": int(vocabulary.shape[0]),
            "elapsed_seconds": elapsed,
            "v5": "PASS_REAL_RUN_LEDGER",
        }
    )
    logp = ridge_log_prob(
        model,
        x_validation,
        vocabulary,
        true_positions,
        temperature=DEFAULT_ADMISSION_CONFIG.softmax_temperature,
        device=device,
    )
    top1 = ridge_top1_positions(model, x_validation, vocabulary, device=device)
    del model
    return logp, top1


def run_scorer_positive_controls(
    *,
    selected: Mapping[str, Any],
    features_by_task: Mapping[str, np.ndarray],
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    fit_summaries: list[dict[str, Any]],
    ledgers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    results: dict[str, Any] = {}
    support: dict[str, Any] = {}
    seed = SEEDS[0]
    for task in TASKS:
        protocol = selected[task]
        cell = next(
            row for row in protocol["inner_cells"] if row["inner_cell_id"].endswith("inner_s0_t0")
        )
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
            [positions[str(row["item_id"])] for row in score_rows], dtype=np.int64
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
            "fit_record_ids": [row["record_id"] for row in fit_rows],
            "scoring_record_ids": [row["record_id"] for row in score_rows],
            "fit_summaries": fit_summaries,
            "ledgers": ledgers,
        }
        h_input_train = oracle_input(
            h_train, item_train, role="a_a1_scorer_h_only"
        )
        h_input_validation = oracle_input(
            h_validation, item_validation, role="a_a1_scorer_h_only"
        )
        h_logp, _ = _fit_scorer_with_ledger(
            fit_id=f"D42-A-A1-scorer|{cell['inner_cell_id']}|seed{seed}|H_only",
            role="H_only_positive_control_baseline",
            x_train=h_input_train,
            x_validation=h_input_validation,
            **common,
        )
        oracle_train = oracle_input(
            h_train, item_train, role="a_a1_scorer_oracle_item"
        )
        oracle_validation = oracle_input(
            h_validation, item_validation, role="a_a1_scorer_oracle_item"
        )
        oracle_logp, oracle_top1 = _fit_scorer_with_ledger(
            fit_id=f"D42-A-A1-scorer|{cell['inner_cell_id']}|seed{seed}|oracle_item",
            role="oracle_item_scorer_positive_control_not_eeg_evidence",
            x_train=oracle_train,
            x_validation=oracle_validation,
            **common,
        )
        row_contract = {
            "scoring_shape_equal": h_logp.shape == oracle_logp.shape == true_positions.shape,
            "finite": bool(np.isfinite(h_logp).all() and np.isfinite(oracle_logp).all()),
            "row_identity_equal": True,
            "vocabulary_equal": True,
            "target_shape_equal": y_train.shape[1] == vocabulary.shape[1] == 384,
            "subject_count_15": len({row["subject_id"] for row in score_rows}) == 15,
        }
        results[task] = summarize_scorer_positive_control(
            task=task,
            h_logp=h_logp,
            oracle_logp=oracle_logp,
            oracle_top1=oracle_top1,
            true_positions=true_positions,
            subject_ids=[str(row["subject_id"]) for row in score_rows],
            row_vocabulary_contract=row_contract,
        )
        support[task] = {
            "inner_cell": cell["inner_cell_id"],
            "seed": seed,
            "fit_rows": len(fit_rows),
            "scoring_rows": len(score_rows),
            "vocabulary_size": len(items),
            "h_input_dim": h_input_train.shape[1],
            "oracle_input_dim": oracle_train.shape[1],
            "target_dim": y_train.shape[1],
            "normalizer_fit_rows": prepared["normalizer"]["fit_rows"],
            "role_checks": prepared["role_checks"],
        }
    return results, support


def build_contract(
    *,
    root: Path,
    run_id: str,
    input_hashes: Mapping[str, str],
    old_evidence: Mapping[str, Any],
    text_manifests: Mapping[str, str],
    resolved_revision: str,
) -> dict[str, Any]:
    sources = (
        "02_code/src/data/a1_failure_diagnosis.py",
        "02_code/scripts/run_a1_failure_diagnosis.py",
        "02_code/tests/test_a1_failure_diagnosis.py",
    )
    return {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": run_id,
        "task": "S0_A1_FAILURE_DIAGNOSIS",
        "spec": f"{SPEC_PATH.as_posix()}#D40-D42",
        "claim_boundary": "construct-validity positive controls only; not EEG evidence, alignment, Gate, route lock, or paper performance",
        "scope": {
            "tasks": list(TASKS),
            "outer_cells": ["task1_nr|outer_s0_t0", "task2_tsr|outer_s0_t0"],
            "a_a3_inner_cells_per_task": 9,
            "a_a3_seeds": list(SEEDS),
            "scorer_inner_cell_per_task": "inner_s0_t0",
            "scorer_seed": SEEDS[0],
            "outer_test_values_read": False,
        },
        "positive_controls": {
            "A-A3": {
                "input": "current target frozen MiniLM item embedding oracle",
                "fit_type": "fixed multinomial logistic",
                "fit_count": 54,
                "K": 8,
                "pass": "subject CI lower >1/8 and observed > within-subject permutation q95",
            },
            "A-A1-scorer": {
                "inputs": ["H-only", "[H,current target frozen MiniLM item embedding] oracle"],
                "fit_type": "ridge alpha=1 intercept + cosine-softmax temperature=0.07",
                "fit_count": 4,
                "pass": "paired subject CI lower >0 and oracle macro-subject full-vocabulary R@1 >=0.80",
            },
        },
        "expected_fit_counts": EXPECTED_FIT_COUNTS,
        "old_artifact_hashes": dict(old_evidence["artifact_hashes"]),
        "old_implementation_hashes": dict(old_evidence["implementation_hashes"]),
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "text_encoder": {
            "requested_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            "resolved_revision": resolved_revision,
            "manifests": dict(text_manifests),
            "output_dim": 384,
            "trainable_parameters": 0,
        },
        "source_hashes": {relative: sha256_file(root / relative) for relative in sources},
        "formal_output_policy": {
            "aggregates_subject_summaries_class_counts_only": True,
            "ledger_ids_hashes_scopes_only": True,
            "no_eeg_features_observation_embeddings_logits_weights": True,
        },
    }


def render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# A1 failure diagnosis",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['completion_outcome']}`",
        f"- New fits/V5: {audit['fit_summary']['total_fit_count']}/{audit['fit_summary']['real_v5_ledger_count']}",
        "- Outer-test/calibration reads: `0/0`",
        "- Role: construct-validity positive controls only; not EEG evidence or paper performance.",
        "",
        "| Task | A-A3 balanced accuracy | CI95 | null q95 | A-A3 | scorer logp gain CI95 | oracle macro-subject R@1 | scorer |",
        "|---|---:|---:|---:|---|---:|---:|---|",
    ]
    for task in TASKS:
        a3 = audit["positive_controls"]["A-A3"][task]
        scorer = audit["positive_controls"]["A-A1-scorer"][task]
        lines.append(
            f"| {task} | {a3['balanced_accuracy']:.6g} | {a3['subject_cluster_bootstrap']['ci95']} | "
            f"{a3['within_subject_permutation_null']['q95']:.6g} | {'PASS' if a3['pass'] else 'FAIL'} | "
            f"{scorer['paired_oracle_minus_h_logp']['ci95']} | "
            f"{scorer['oracle_full_vocabulary_macro_subject_r_at_1']:.6g} | "
            f"{'PASS' if scorer['pass'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "The admitted v3.14 `FAIL_A1_ADMISSION` is unchanged. The channel-sham pattern is descriptive only and no mechanism is claimed.",
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
    random.seed(SEEDS[0])
    np.random.seed(SEEDS[0])
    torch.manual_seed(SEEDS[0])
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available() or not str(args.device).startswith("cuda"):
        raise RuntimeError("INVALID_A1_FAILURE_DIAGNOSIS: real controls require CUDA")

    old_evidence = verify_old_evidence(root)
    physical_hashes, _, _ = verify_frozen_inputs(root)
    _, _, selected, scope_index = load_protocol(root)
    v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    for ledger in old_evidence["ledgers"]:
        validate_diagnosis_v5_or_raise(ledger, scope_index, v5_hashes)
    old_v5_revalidated = len(old_evidence["ledgers"])
    print(
        "OLD_EVIDENCE status=PASS artifacts=4 implementation_files=3 "
        f"V5={old_v5_revalidated}/639 outer_test_reads=0 calibration_reads=0"
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

    encoder, text_manifests, resolved_revision = load_text_encoder(root, args.text_device)
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    if str(args.text_device).startswith("cuda"):
        torch.cuda.empty_cache()

    fit_summaries: list[dict[str, Any]] = []
    ledgers: list[dict[str, Any]] = []
    a3_results, a3_support = run_a_a3_positive_controls(
        selected=selected,
        features_by_task=features_by_task,
        metadata_by_task=metadata_by_task,
        item_vectors=item_vectors,
        device=args.device,
        input_hashes=v5_hashes,
        scope_index=scope_index,
        run_id=args.run_id,
        fit_summaries=fit_summaries,
        ledgers=ledgers,
    )
    print(
        f"A-A3 fits={sum(row['fit_type']=='multinomial_logistic' for row in fit_summaries)} "
        + " ".join(
            f"{task}=pass:{a3_results[task]['pass']},ba:{a3_results[task]['balanced_accuracy']:.6f},"
            f"ci:{a3_results[task]['subject_cluster_bootstrap']['ci95']},"
            f"q95:{a3_results[task]['within_subject_permutation_null']['q95']:.6f}"
            for task in TASKS
        )
    )

    scorer_results, scorer_support = run_scorer_positive_controls(
        selected=selected,
        features_by_task=features_by_task,
        metadata_by_task=metadata_by_task,
        item_vectors=item_vectors,
        h_vectors=h_vectors,
        device=args.device,
        input_hashes=v5_hashes,
        scope_index=scope_index,
        run_id=args.run_id,
        fit_summaries=fit_summaries,
        ledgers=ledgers,
    )
    print(
        f"SCORER fits={sum(row['fit_type']=='ridge' for row in fit_summaries)} "
        + " ".join(
            f"{task}=pass:{scorer_results[task]['pass']},"
            f"gain_ci:{scorer_results[task]['paired_oracle_minus_h_logp']['ci95']},"
            f"R1:{scorer_results[task]['oracle_full_vocabulary_macro_subject_r_at_1']:.6f}"
            for task in TASKS
        )
    )

    admitted_audit = _load_json(root / "04_results/audits/a1_admission.json")
    existing_failure_summary = derive_existing_failure_summary(admitted_audit)
    contract = build_contract(
        root=root,
        run_id=args.run_id,
        input_hashes=physical_hashes,
        old_evidence=old_evidence,
        text_manifests=text_manifests,
        resolved_revision=resolved_revision,
    )
    fit_counts = {
        "logistic_fit_count": sum(
            row["fit_type"] == "multinomial_logistic" for row in fit_summaries
        ),
        "ridge_fit_count": sum(row["fit_type"] == "ridge" for row in fit_summaries),
        "total_fit_count": len(fit_summaries),
        "real_v5_ledger_count": len(ledgers),
        "maximum_single_fit_seconds": max(row["elapsed_seconds"] for row in fit_summaries),
        "fit_runtime_seconds_sum": float(
            sum(float(row["elapsed_seconds"]) for row in fit_summaries)
        ),
        "fits": fit_summaries,
    }
    audit: dict[str, Any] = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "S0_A1_FAILURE_DIAGNOSIS",
        "claim_boundary": "oracle construct-validity controls only; admitted FAIL_A1_ADMISSION unchanged",
        "old_evidence": {
            key: value for key, value in old_evidence.items() if key != "ledgers"
        },
        "old_v5_revalidated": old_v5_revalidated,
        "positive_controls": {
            "A-A3": a3_results,
            "A-A1-scorer": scorer_results,
        },
        "support": {"A-A3": a3_support, "A-A1-scorer": scorer_support},
        "existing_failure_summary": existing_failure_summary,
        "fit_summary": fit_counts,
        "data": data_summary,
        "text": {
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
            **text_summary,
        },
        "input_artifact_hashes": dict(sorted(physical_hashes.items())),
        "outer_test": {
            "ids_used_for_v5_exclusion_only": True,
            "eeg_feature_label_metric_reads": 0,
            "calibration_record_count": 0,
        },
        "formal_outputs_contain_no_eeg_features_observation_embeddings_logits_or_weights": True,
        "elapsed_seconds": time.perf_counter() - started,
    }
    preliminary_formal = validate_aggregate_formal_output(audit)
    outcome, reasons = evaluate_completion(
        a3_results=a3_results,
        scorer_results=scorer_results,
        fit_summaries=fit_summaries,
        ledger_count=len(ledgers),
        old_evidence_pass=True,
        old_v5_revalidated=old_v5_revalidated,
        formal_output_pass=preliminary_formal["pass"],
        outer_test_read_count=0,
        calibration_read_count=0,
    )
    audit["completion_outcome"] = outcome
    audit["outcome_reasons"] = reasons
    audit["planned_state_transition"] = planned_state_transition(outcome)
    audit["formal_output_validation"] = validate_aggregate_formal_output(audit)
    if not audit["formal_output_validation"]["pass"]:
        raise RuntimeError("INVALID_A1_FAILURE_DIAGNOSIS: formal output contains forbidden keys")
    if len(fit_summaries) != 58 or len(ledgers) != 58:
        raise RuntimeError("INVALID_A1_FAILURE_DIAGNOSIS: expected exactly 58 fits/V5 ledgers")
    if any(row["outer_test_record_ids_read"] for row in ledgers):
        raise RuntimeError("INVALID_A1_FAILURE_DIAGNOSIS: new ledger outer-test read")
    if any(row["calibration_record_ids"] for row in ledgers):
        raise RuntimeError("INVALID_A1_FAILURE_DIAGNOSIS: new ledger calibration read")

    output_hashes = write_outputs(
        root,
        contract_path=args.contract_output,
        audit_json_path=args.audit_json_output,
        audit_md_path=args.audit_md_output,
        ledger_path=args.ledger_output,
        contract=contract,
        audit=audit,
        ledgers=ledgers,
    )
    final_old_evidence = verify_old_evidence(root)
    if final_old_evidence["artifact_hashes"] != OLD_ARTIFACT_HASHES:
        raise RuntimeError("STATE_SPEC_CONFLICT: old artifacts changed during diagnosis")
    if final_old_evidence["implementation_hashes"] != OLD_IMPLEMENTATION_HASHES:
        raise RuntimeError("STATE_SPEC_CONFLICT: old implementation changed during diagnosis")

    print(f"OUTCOME {outcome} reasons={reasons}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        f"SELF-CHECK SUMMARY samples={{new_fits: {len(fit_summaries)}, new_v5: {len(ledgers)}, "
        f"old_v5_revalidated: {old_v5_revalidated}}} "
        f"shapes={{oracle_item: [N,384], H_only: [N,384], oracle_scorer: [N,768]}} "
        f"elapsed_seconds={audit['elapsed_seconds']:.3f} "
        f"ranges={{max_fit_seconds: {fit_counts['maximum_single_fit_seconds']:.3f}}} "
        "assertions={outer_test_reads: 0, calibration_reads: 0, old_bytes_unchanged: true, aggregate_only: true} "
        f"status={'PASS' if outcome == 'PASS_A1_FAILURE_DIAGNOSIS' else 'FAIL'}"
    )
    return 0 if outcome == "PASS_A1_FAILURE_DIAGNOSIS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
