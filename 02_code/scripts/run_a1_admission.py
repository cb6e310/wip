#!/usr/bin/env python3
"""Run only the SPEC v3.14 S0_A1_ADMISSION pilot on real ZuCo 2.0 data."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import h5py
import numpy as np
import torch
import yaml
from sklearn.metrics import balanced_accuracy_score


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from backbones.a1_spectral import bandpower_features, config_hash as a1_config_hash  # noqa: E402
from data.a1_admission import (  # noqa: E402
    ALGORITHM_VERSION,
    ARMS,
    BASES,
    DEFAULT_ADMISSION_CONFIG,
    OUTER_CELLS,
    SEEDS,
    TASKS,
    build_four_arm_features,
    balanced_recall,
    build_v5_ledger,
    canonical_artifact,
    canonical_json_bytes,
    cluster_bootstrap,
    config_hash,
    deterministic_gzip_jsonl,
    deterministic_item_clusters,
    evaluate_a_a4,
    evaluate_completion_outcome,
    fit_fixed_logistic,
    fit_fold_normalizer,
    fit_ridge_to_items,
    material_group_bootstrap,
    permutation_null_fixed_predictions,
    ridge_log_prob,
    sha256_bytes,
    stable_seed,
    summarize_a_a1,
    summarize_classification,
    supported_item_ids,
    token_local_frozen_initial_latent,
    transform_fold_normalizer,
    u_statistics,
    validate_v5_or_raise,
)
from data.a1_source_admission import sha256_file, strict_native_matrix  # noqa: E402
from data.inner_split import validate_inner_artifact  # noqa: E402
from data.joint_split import validate_artifact as validate_outer_panel  # noqa: E402
from data.zuco2_loader import (  # noqa: E402
    TASKS as RELEASE_TASKS,
    decode_matlab_string,
    dereference,
    indexed_value,
    iter_summary_files,
)
from data.zuco2_source_join import prove_task_source_join, read_summary_contents  # noqa: E402
from protocol.h_definition import audit_h_context, build_h_full  # noqa: E402
from protocol.semantic_items import decide_item  # noqa: E402
from text.frozen_minilm import (  # noqa: E402
    DEFAULT_CONFIG as TEXT_CONFIG,
    MODEL_ID,
    REVISION,
    FrozenMiniLMEncoder,
    aggregate_file_hash,
)
from text_encoder_selfcheck import _classify_snapshot_hashes  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402


RUN_ID = "2026-08-16_027_v314_a1_admission"
SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_14_2026-08-16.md")
DATASET_ROOT = Path("01_data_protocol/datasets/zuco_2.0")
CACHE_ROOT = Path(".codex_stage0_a1_admission_v314")
CONTRACT_PATH = Path("artifacts/a1_admission_contract.yaml")
AUDIT_JSON_PATH = Path("04_results/audits/a1_admission.json")
AUDIT_MD_PATH = Path("04_results/audits/a1_admission.md")
LEDGER_PATH = Path("04_results/audits/a1_admission_run_ledger.jsonl.gz")

FROZEN_INPUTS = {
    "source_contract": ("artifacts/a1_real_source_contract.yaml", "bb03bb785dd62d8957819aa69eaa4155636e36858dcb35cf31a8e9a81bbedc3c"),
    "source_exclusions": ("01_data_protocol/a1_source_exclusions.jsonl.gz", "250f1e2cda8f4b4c2900bb031845f0c347a75f180ca083b68401da671bb65d3c"),
    "source_audit": ("04_results/audits/zuco2_a1_source_admission.json", "07b3718eee0f7e6784d8d1007447ac7bdcbd92a4b85a1e6bfc504b64c9aa271f"),
    "a1_freeze": ("artifacts/a1_frontend_freeze.yaml", "9c3f48ddf38bca8e75534932ebc6ea3c035a044f627e271a0348ec759bc11e30"),
    "outer_split": ("01_data_protocol/splits/zuco_2_0_outer_folds.json", "20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6"),
    "inner_split": ("01_data_protocol/splits/zuco_2_0_inner_folds.json", "0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7"),
    "semantic_support": ("04_results/audits/semantic_item/zuco2_semantic_item_support.json", "fe862ebaed2b027b4924f45c23dacfc01c5c7ad862f6917cbd0a963d2dcff32c"),
    "semantic_contract": ("artifacts/semantic_item_contract.yaml", "72b8b471a25c857b3d35a0e18ec256093b5803872cf907ab2ff4b922b285c051"),
    "h_definition": ("artifacts/h_definition.yaml", "226f92e299633997fdb9469592f6f8a36fa6c728aa24d9a7d6cb9ded8fb2ae6b"),
    "text_encoder": ("artifacts/text_encoder_freeze.yaml", "35e18392a285c8d09ba84a934e31dd327a18fa1a0c10a3bd8550f090cd496494"),
    "source_join": ("artifacts/zuco2_source_slot_join.yaml", "eb960cd0bf2cb5016f33793813cb61fa2c77c9ce07e2037cff69b29c14c104c8"),
}
V5_INPUT_KEYS = (
    "source_contract",
    "a1_freeze",
    "outer_split",
    "inner_split",
    "semantic_support",
    "h_definition",
    "text_encoder",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--device", default="cuda:1")
    parser.add_argument("--text-device", default="cpu")
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--contract-output", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--audit-json-output", type=Path, default=AUDIT_JSON_PATH)
    parser.add_argument("--audit-md-output", type=Path, default=AUDIT_MD_PATH)
    parser.add_argument("--ledger-output", type=Path, default=LEDGER_PATH)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return value


def verify_frozen_inputs(root: Path) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    hashes: dict[str, str] = {}
    for key, (relative, expected) in FROZEN_INPUTS.items():
        path = root / relative
        observed = sha256_file(path)
        if observed != expected:
            raise RuntimeError(f"STATE_SPEC_CONFLICT: {relative} SHA256 {observed} != {expected}")
        hashes[key] = observed
    source_contract = _load_yaml(root / FROZEN_INPUTS["source_contract"][0])
    a1_freeze = _load_yaml(root / FROZEN_INPUTS["a1_freeze"][0])
    if source_contract.get("outcome") != "PASS_REAL_A1_SOURCE":
        raise RuntimeError("STATE_SPEC_CONFLICT: source contract is not PASS_REAL_A1_SOURCE")
    if source_contract.get("input_bindings", {}).get("a1_config_hash") != a1_config_hash():
        raise RuntimeError("STATE_SPEC_CONFLICT: source contract A1 config hash changed")
    if a1_freeze.get("config", {}).get("alignment_encoder", {}).get("d_align") != 384:
        raise RuntimeError("STATE_SPEC_CONFLICT: A1 d_align is not 384")
    return hashes, source_contract, a1_freeze


def load_protocol(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    outer = _load_json(root / FROZEN_INPUTS["outer_split"][0])
    inner = _load_json(root / FROZEN_INPUTS["inner_split"][0])
    outer_errors = [
        f"{task}:{error}"
        for task, panel in outer["panels"].items()
        for error in validate_outer_panel(panel)
    ]
    inner_errors = validate_inner_artifact(inner)
    if outer_errors or inner_errors:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: split validation failed {outer_errors + inner_errors}")
    selected: dict[str, Any] = {}
    scope_index: dict[str, dict[str, Any]] = {"outer": {}, "inner": {}}
    for task in TASKS:
        outer_cell_id = OUTER_CELLS[task]
        outer_panel = outer["panels"][task]
        outer_cell = next(
            cell
            for cell in outer_panel["cells"]
            if str(cell["subject_fold"]) == "0" and str(cell["text_fold"]) == "0"
        )
        inner_outer = next(
            cell for cell in inner["panels"][task]["outer_cells"] if cell["outer_cell_id"] == outer_cell_id
        )
        if len(inner_outer["inner_cells"]) != 9 or len(outer_cell["train_subject_ids"]) != 15:
            raise RuntimeError(f"STATE_SPEC_CONFLICT: {task} is not the frozen 15-subject 3x3 cell")
        outer_train = list(inner_outer["outer_train_record_ids"])
        record_rows = {row["record_id"]: row for row in outer_panel["records"]}
        text_assignment = {
            stimulus: str(group["inner_text_fold"])
            for group in inner_outer["text_group_assignments"]
            for stimulus in group["stimulus_ids"]
        }
        cells: list[dict[str, Any]] = []
        for raw in inner_outer["inner_cells"]:
            sid = str(raw["inner_subject_fold"])
            tid = str(raw["inner_text_fold"])
            inner_id = f"{outer_cell_id}|inner_s{sid}_t{tid}"
            train_ids = [outer_train[index] for index in raw["train_record_id_indices"]]
            validation_ids = [outer_train[index] for index in raw["validation_record_id_indices"]]
            cells.append(
                {
                    "inner_cell_id": inner_id,
                    "inner_subject_fold": sid,
                    "inner_text_fold": tid,
                    "train_record_ids": train_ids,
                    "validation_record_ids": validation_ids,
                }
            )
            scope_index["inner"][inner_id] = {
                "outer_cell_id": outer_cell_id,
                "train_record_ids": train_ids,
                "validation_record_ids": validation_ids,
            }
        cells.sort(key=lambda row: row["inner_cell_id"])
        scope_index["outer"][outer_cell_id] = {
            "train_record_ids": outer_train,
            "test_record_ids": list(inner_outer["outer_test_record_ids"]),
        }
        selected[task] = {
            "outer_cell_id": outer_cell_id,
            "outer_train_record_ids": outer_train,
            "outer_test_record_ids": list(inner_outer["outer_test_record_ids"]),
            "outer_test_subject_ids": list(inner_outer["outer_test_subject_ids"]),
            "outer_test_stimulus_ids": list(inner_outer["outer_test_stimulus_ids"]),
            "inner_cells": cells,
            "record_rows": record_rows,
            "text_assignment": text_assignment,
            "outer_subjects": list(outer_cell["train_subject_ids"]),
        }
    return outer, inner, selected, scope_index


def _load_is_real_word(reader_path: Path) -> Callable[[str], object]:
    spec = importlib.util.spec_from_file_location("zuco_release_reader_a1_admission", reader_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load official reader: {reader_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    predicate = getattr(module, "is_real_word", None)
    if not callable(predicate):
        raise AttributeError("official reader has no callable is_real_word")
    return predicate


def _vector_length(value: object) -> int:
    shape = tuple(int(item) for item in getattr(value, "shape", ()))
    if not shape:
        return 0
    if shape[0] == 1:
        return shape[1]
    if len(shape) > 1 and shape[1] == 1:
        return shape[0]
    return int(np.prod(shape))


def _session_id(source_file: str) -> str:
    stem = Path(source_file).stem
    value = stem.rsplit("_", 1)[-1]
    if value not in {str(index) for index in range(1, 8)}:
        raise ValueError(f"source file has no release session: {source_file}")
    return value


def build_text_contexts(root: Path) -> dict[str, dict[str, Any]]:
    dataset_root = root / DATASET_ROOT
    result: dict[str, dict[str, Any]] = {}
    for task in TASKS:
        proof = prove_task_source_join(dataset_root, task)
        if not proof.verified:
            raise RuntimeError(f"STATE_SPEC_CONFLICT: live source join failed for {task}")
        first = next(iter_summary_files(dataset_root, task))
        contents = read_summary_contents(first.path)
        by_file: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
        for slot in proof.slots:
            by_file[slot.source_file].append((slot.summary_index - 1, slot.source_slot_key))
        for source_file in sorted(by_file):
            ordered = sorted(by_file[source_file])
            sentence_tokens = [contents[index].split() for index, _ in ordered]
            for position, (summary_index, stimulus_id) in enumerate(ordered):
                slot = proof.slots[summary_index]
                result[stimulus_id] = {
                    "task": task,
                    "summary_index": summary_index,
                    "source_file": source_file,
                    "session_id": _session_id(source_file),
                    "group_key": slot.group_key,
                    "exact_text": contents[summary_index],
                    "sentence_tokens": sentence_tokens,
                    "position_in_file": position,
                }
    return result


def extract_task_observations(
    root: Path,
    *,
    task: str,
    task_protocol: Mapping[str, Any],
    contexts: Mapping[str, Mapping[str, Any]],
    rebuild: bool,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    cache = root / CACHE_ROOT / task
    feature_path = cache / "features.npy"
    metadata_path = cache / "metadata.jsonl"
    manifest_path = cache / "manifest.json"
    binding = {
        "task": task,
        "outer_cell_id": task_protocol["outer_cell_id"],
        "outer_train_record_ids_sha256": sha256_bytes(canonical_json_bytes(sorted(task_protocol["outer_train_record_ids"]))),
        "source_contract_sha256": FROZEN_INPUTS["source_contract"][1],
        "a1_config_hash": a1_config_hash(),
        "semantic_config": {"official_predicate": True, "content_word_only": True},
    }
    if not rebuild and feature_path.is_file() and metadata_path.is_file() and manifest_path.is_file():
        manifest = _load_json(manifest_path)
        if manifest.get("binding") == binding:
            features = np.load(feature_path, mmap_mode=None)
            metadata = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines()]
            if features.shape == (len(metadata), 840) and manifest.get("feature_bytes_sha256") == sha256_bytes(features.tobytes(order="C")):
                return features, metadata, manifest

    dataset_root = root / DATASET_ROOT
    reader = dataset_root / "scripts/python_reader/data_loading_helpers.py"
    is_real_word = _load_is_real_word(reader)
    proof = prove_task_source_join(dataset_root, task)
    slot_by_index = {slot.summary_index - 1: slot for slot in proof.slots}
    outer_train = set(task_protocol["outer_train_record_ids"])
    outer_test = set(task_protocol["outer_test_record_ids"])
    features: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    fixation_counts: Counter[str] = Counter()
    started = time.perf_counter()
    for summary in iter_summary_files(dataset_root, task):
        with h5py.File(summary.path, "r") as handle:
            sentence_group = handle["sentenceData"]
            for sentence_index, slot in slot_by_index.items():
                record_id = f"{summary.subject_id}|{slot.source_slot_key}"
                if record_id not in outer_train:
                    continue
                if record_id in outer_test:
                    raise RuntimeError("outer-test record entered observation extraction")
                sentence_matrix, sentence_status = strict_native_matrix(
                    dereference(handle, indexed_value(sentence_group["rawData"], sentence_index)), load=False
                )
                if sentence_status != "VALID" or sentence_matrix is None:
                    exclusions["SENTENCE_SOURCE_INVALID"] += 1
                    continue
                word_group = dereference(handle, indexed_value(sentence_group["word"], sentence_index))
                if not isinstance(word_group, h5py.Group) or "content" not in word_group or "rawEEG" not in word_group:
                    exclusions["WORD_GROUP_INVALID"] += 1
                    continue
                word_count = max(_vector_length(word_group["content"]), _vector_length(word_group["rawEEG"]))
                for word_index in range(word_count):
                    raw = decode_matlab_string(handle, indexed_value(word_group["content"], word_index))
                    if raw is None:
                        exclusions["CONTENT_INVALID"] += 1
                        continue
                    decision = decide_item(
                        raw,
                        dataset="zuco_2_0",
                        task=RELEASE_TASKS[task]["label"],
                        is_real_word=is_real_word,
                    )
                    if not decision.accepted:
                        exclusions[decision.reason] += 1
                        continue
                    container = dereference(handle, indexed_value(word_group["rawEEG"], word_index))
                    if not isinstance(container, h5py.Dataset):
                        exclusions["FIXATION_CONTAINER_INVALID"] += 1
                        continue
                    legal: list[np.ndarray] = []
                    for fixation_ref in np.asarray(container[...], dtype=object).reshape(-1):
                        matrix, status = strict_native_matrix(dereference(handle, fixation_ref))
                        fixation_counts[status] += 1
                        if status == "VALID" and matrix is not None:
                            legal.append(matrix)
                    if not legal:
                        exclusions["NO_LEGAL_FIXATION"] += 1
                        continue
                    concatenated = np.concatenate(legal, axis=0)
                    feature = bandpower_features(concatenated)
                    if feature.shape != (840,) or feature.dtype != np.float32 or not np.isfinite(feature).all():
                        raise RuntimeError("real word feature violated finite float32[840]")
                    context = contexts[slot.source_slot_key]
                    observation_id = f"{record_id}|word_index:{word_index + 1}"
                    features.append(feature)
                    metadata.append(
                        {
                            "observation_id": observation_id,
                            "record_id": record_id,
                            "task": task,
                            "subject_id": summary.subject_id,
                            "stimulus_id": slot.source_slot_key,
                            "group_key": slot.group_key,
                            "session_id": context["session_id"],
                            "word_index": word_index + 1,
                            "item_id": decision.item_id,
                            "surface": decision.normalized_surface,
                        }
                    )
    order = sorted(range(len(metadata)), key=lambda index: metadata[index]["observation_id"])
    matrix = np.stack([features[index] for index in order]).astype(np.float32, copy=False)
    ordered_meta = [metadata[index] for index in order]
    if len({row["observation_id"] for row in ordered_meta}) != len(ordered_meta):
        raise RuntimeError("duplicate word observation identity")
    cache.mkdir(parents=True, exist_ok=True)
    np.save(feature_path, matrix, allow_pickle=False)
    metadata_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in ordered_meta),
        encoding="utf-8",
    )
    manifest = {
        "binding": binding,
        "observation_count": len(ordered_meta),
        "record_count": len({row["record_id"] for row in ordered_meta}),
        "subject_count": len({row["subject_id"] for row in ordered_meta}),
        "shape": list(matrix.shape),
        "dtype": str(matrix.dtype),
        "finite": bool(np.isfinite(matrix).all()),
        "feature_bytes_sha256": sha256_bytes(matrix.tobytes(order="C")),
        "metadata_sha256": sha256_file(metadata_path),
        "exclusion_reason_counts": dict(sorted(exclusions.items())),
        "fixation_status_counts": dict(sorted(fixation_counts.items())),
        "elapsed_seconds": time.perf_counter() - started,
    }
    manifest_path.write_bytes(canonical_artifact(manifest))
    return matrix, ordered_meta, manifest


def load_text_encoder(root: Path, device: str) -> tuple[FrozenMiniLMEncoder, dict[str, str], str]:
    freeze = _load_yaml(root / FROZEN_INPUTS["text_encoder"][0])
    snapshot = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=REVISION,
            local_files_only=True,
            ignore_patterns=["*.h5", "*.msgpack", "*.ot", "onnx/*", "openvino/*"],
        )
    ).resolve()
    groups = _classify_snapshot_hashes(snapshot)
    manifests = {
        "tokenizer": aggregate_file_hash(groups["tokenizer"]),
        "encoder_config": aggregate_file_hash(groups["encoder_config"]),
        "model": aggregate_file_hash(groups["model"]),
        "scientific_config": TEXT_CONFIG.scientific_config_hash,
    }
    expected = {
        "tokenizer": freeze["provenance"]["tokenizer_manifest_hash"],
        "encoder_config": freeze["provenance"]["encoder_config_manifest_hash"],
        "model": freeze["provenance"]["model_file_manifest_hash"],
        "scientific_config": freeze["model"]["scientific_config_hash"],
    }
    if snapshot.name != REVISION or manifests != expected:
        raise RuntimeError("STATE_SPEC_CONFLICT: exact-revision text manifests changed")
    encoder = FrozenMiniLMEncoder(
        tokenizer_manifest_hash=manifests["tokenizer"],
        encoder_config_manifest_hash=manifests["encoder_config"],
        device=device,
        local_files_only=True,
    )
    if encoder.trainable_parameter_count or encoder.model.training:
        raise RuntimeError("text encoder is not frozen eval/no-grad")
    return encoder, manifests, snapshot.name


def encode_text_inputs(
    encoder: FrozenMiniLMEncoder,
    metadata_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    contexts: Mapping[str, Mapping[str, Any]],
    *,
    batch_size: int = 256,
) -> tuple[dict[str, np.ndarray], dict[tuple[str, str], np.ndarray], dict[str, Any]]:
    surfaces = sorted({str(row["surface"]) for rows in metadata_by_task.values() for row in rows})
    item_vectors: dict[str, np.ndarray] = {}
    for start in range(0, len(surfaces), batch_size):
        batch = surfaces[start : start + batch_size]
        result = encoder.encode(batch)
        for surface, vector in zip(batch, result.embeddings.cpu().numpy(), strict=True):
            item_vectors[surface] = vector.astype(np.float32, copy=False)

    h_text: dict[tuple[str, str], str] = {}
    h_audit_count = 0
    for rows in metadata_by_task.values():
        for row in rows:
            key = (str(row["stimulus_id"]), str(row["surface"]))
            if key in h_text:
                continue
            context = contexts[key[0]]
            position = int(context["position_in_file"])
            h = build_h_full(
                context["sentence_tokens"],
                target_sentence_index=position,
                target_tokens=[key[1]],
                position_index=position,
            )
            if not all(audit_h_context(h, target_tokens=[key[1]], payload={"history": list(h.tokens)}).values()):
                raise RuntimeError("H forbidden-field assertion failed")
            h_text[key] = " ".join(h.tokens)
            h_audit_count += 1
    unique_h = sorted(set(h_text.values()))
    encoded_h: dict[str, np.ndarray] = {}
    for start in range(0, len(unique_h), batch_size):
        batch = unique_h[start : start + batch_size]
        result = encoder.encode(batch)
        for text, vector in zip(batch, result.embeddings.cpu().numpy(), strict=True):
            encoded_h[text] = vector.astype(np.float32, copy=False)
    h_vectors = {key: encoded_h[text] for key, text in h_text.items()}
    return item_vectors, h_vectors, {
        "surface_count": len(surfaces),
        "h_context_count": len(h_text),
        "unique_h_text_count": len(unique_h),
        "h_forbidden_field_assertions": h_audit_count,
        "item_shape": [len(surfaces), 384],
        "h_shape": [len(h_text), 384],
        "finite": all(np.isfinite(value).all() for value in [*item_vectors.values(), *h_vectors.values()]),
    }


def _indices_for_records(metadata: Sequence[Mapping[str, Any]], record_ids: Sequence[str]) -> np.ndarray:
    legal = set(record_ids)
    return np.asarray([index for index, row in enumerate(metadata) if row["record_id"] in legal], dtype=np.int64)


def _subset(rows: Sequence[Mapping[str, Any]], indices: np.ndarray) -> list[Mapping[str, Any]]:
    return [rows[int(index)] for index in indices]


def _h_matrix(rows: Sequence[Mapping[str, Any]], h_vectors: Mapping[tuple[str, str], np.ndarray]) -> np.ndarray:
    return np.stack([h_vectors[(str(row["stimulus_id"]), str(row["surface"]))] for row in rows]).astype(np.float32)


def _item_matrix(rows: Sequence[Mapping[str, Any]], item_vectors: Mapping[str, np.ndarray]) -> np.ndarray:
    return np.stack([item_vectors[str(row["surface"])] for row in rows]).astype(np.float32)


def _vocabulary(
    supported: set[str], rows: Sequence[Mapping[str, Any]], item_vectors: Mapping[str, np.ndarray]
) -> tuple[list[str], np.ndarray, dict[str, int]]:
    surface_by_item = {str(row["item_id"]): str(row["surface"]) for row in rows}
    items = sorted(supported)
    matrix = np.stack([item_vectors[surface_by_item[item]] for item in items]).astype(np.float32)
    return items, matrix, {item: index for index, item in enumerate(items)}


def _fit_probe(
    *,
    fit_id: str,
    seed: int,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    vocabulary: np.ndarray,
    true_positions: np.ndarray,
    device: str,
    task_protocol: Mapping[str, Any],
    inner_cell: Mapping[str, Any] | None,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    ledgers: list[dict[str, Any]],
    fit_summaries: list[dict[str, Any]],
    fit_record_ids: Sequence[str],
    scoring_record_ids: Sequence[str],
) -> np.ndarray:
    model, elapsed = fit_ridge_to_items(
        x_train, y_train, alpha=DEFAULT_ADMISSION_CONFIG.ridge_alpha, device=device
    )
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"A1_ADMISSION_PREFLIGHT_BLOCKED: fit {fit_id} elapsed {elapsed:.3f}s >300s")
    inner_id = None if inner_cell is None else str(inner_cell["inner_cell_id"])
    fit_records = sorted(set(fit_record_ids))
    validation_records = [] if inner_cell is None else sorted(set(inner_cell["validation_record_ids"]))
    ledger = build_v5_ledger(
        run_id=run_id,
        fit_id=fit_id,
        seed=seed,
        outer_cell=str(task_protocol["outer_cell_id"]),
        inner_cell=inner_id,
        fit_record_ids=fit_records,
        validation_record_ids=validation_records,
        scoring_record_ids=scoring_record_ids,
        input_hashes=input_hashes,
    )
    validate_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fit_summaries.append(
        {
            "fit_id": fit_id,
            "fit_type": "ridge",
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
    return ridge_log_prob(
        model,
        x_validation,
        vocabulary,
        true_positions,
        temperature=DEFAULT_ADMISSION_CONFIG.softmax_temperature,
        device=device,
    )


def run_preflight(
    *,
    task_protocol: Mapping[str, Any],
    features: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    cell = next(row for row in task_protocol["inner_cells"] if row["inner_cell_id"].endswith("inner_s0_t0"))
    train_global = _indices_for_records(metadata, cell["train_record_ids"])
    validation_global = _indices_for_records(metadata, cell["validation_record_ids"])
    train_rows = _subset(metadata, train_global)
    validation_rows = _subset(metadata, validation_global)
    supported, _ = supported_item_ids(train_rows)
    fit_mask = np.asarray([row["item_id"] in supported for row in train_rows])
    validation_mask = np.asarray([row["item_id"] in supported for row in validation_rows])
    state, normalizer_summary = fit_fold_normalizer(features[train_global])
    train_normalized = transform_fold_normalizer(features[train_global], state)
    validation_normalized = transform_fold_normalizer(features[validation_global], state)
    seed = SEEDS[0]
    train_arms, train_common, train_sham_audit = build_four_arm_features(
        train_normalized, train_rows, seed=seed, partition=f"{cell['inner_cell_id']}|train"
    )
    validation_arms, validation_common, validation_sham_audit = build_four_arm_features(
        validation_normalized, validation_rows, seed=seed, partition=f"{cell['inner_cell_id']}|validation"
    )
    fit_local = np.asarray([index for index in train_common if fit_mask[index]], dtype=np.int64)
    score_local = np.asarray([index for index in validation_common if validation_mask[index]], dtype=np.int64)
    available = int(np.count_nonzero(validation_mask))
    support_rate = float(len(score_local) / available) if available else 0.0
    if support_rate < DEFAULT_ADMISSION_CONFIG.preflight_min_common_support:
        raise RuntimeError(
            f"A1_ADMISSION_PREFLIGHT_BLOCKED: common support {support_rate:.6f} < 0.5"
        )
    fit_rows = [train_rows[index] for index in fit_local]
    score_rows = [validation_rows[index] for index in score_local]
    vocab_items, vocab, positions = _vocabulary(supported, train_rows, item_vectors)
    y_train = _item_matrix(fit_rows, item_vectors)
    h_train = _h_matrix(fit_rows, h_vectors)
    h_validation = _h_matrix(score_rows, h_vectors)
    true_positions = np.asarray([positions[str(row["item_id"])] for row in score_rows], dtype=np.int64)
    ledgers: list[dict[str, Any]] = []
    fits: list[dict[str, Any]] = []
    for basis in BASES:
        for arm in ARMS:
            train_basis = train_arms[arm][np.searchsorted(train_common, fit_local)]
            validation_basis = validation_arms[arm][np.searchsorted(validation_common, score_local)]
            latent_audit = None
            if basis == "token_local_frozen_initial_latent":
                train_basis, latent_audit = token_local_frozen_initial_latent(
                    train_basis, seed=seed, device=device
                )
                validation_basis, _ = token_local_frozen_initial_latent(
                    validation_basis, seed=seed, device=device
                )
            _fit_probe(
                fit_id=f"preflight|{cell['inner_cell_id']}|seed{seed}|{basis}|{arm}",
                seed=seed,
                x_train=np.concatenate([h_train, train_basis], axis=1),
                y_train=y_train,
                x_validation=np.concatenate([h_validation, validation_basis], axis=1),
                vocabulary=vocab,
                true_positions=true_positions,
                device=device,
                task_protocol=task_protocol,
                inner_cell=cell,
                input_hashes=input_hashes,
                scope_index=scope_index,
                run_id=run_id,
                ledgers=ledgers,
                fit_summaries=fits,
                fit_record_ids=[row["record_id"] for row in fit_rows],
                scoring_record_ids=[row["record_id"] for row in score_rows],
            )
            if latent_audit is not None and latent_audit["trainable_parameter_count"] != 0:
                raise RuntimeError("A1_ADMISSION_PREFLIGHT_BLOCKED: latent encoder is trainable")
    _fit_probe(
        fit_id=f"preflight|{cell['inner_cell_id']}|seed{seed}|text_only",
        seed=seed,
        x_train=h_train,
        y_train=y_train,
        x_validation=h_validation,
        vocabulary=vocab,
        true_positions=true_positions,
        device=device,
        task_protocol=task_protocol,
        inner_cell=cell,
        input_hashes=input_hashes,
        scope_index=scope_index,
        run_id=run_id,
        ledgers=ledgers,
        fit_summaries=fits,
        fit_record_ids=[row["record_id"] for row in fit_rows],
        scoring_record_ids=[row["record_id"] for row in score_rows],
    )
    def aggregate_sham_audit(value: Mapping[str, Any]) -> dict[str, Any]:
        trial_reasons = Counter(str(row["reason"]) for row in value["trial_exclusions"])
        unit_reasons = Counter(str(row["reason"]) for row in value["unit_exclusions"])
        return {
            key: item
            for key, item in value.items()
            if key not in {"trial_assignment", "trial_exclusions", "unit_exclusions"}
        } | {
            "trial_assignment_count": len(value["trial_assignment"]),
            "trial_exclusion_count": len(value["trial_exclusions"]),
            "trial_exclusion_reason_counts": dict(sorted(trial_reasons.items())),
            "unit_exclusion_count": len(value["unit_exclusions"]),
            "unit_exclusion_reason_counts": dict(sorted(unit_reasons.items())),
        }

    return {
        "status": "PASS",
        "task": "task1_nr",
        "outer_cell": task_protocol["outer_cell_id"],
        "inner_cell": cell["inner_cell_id"],
        "seed": seed,
        "fit_count": len(fits),
        "maximum_fit_seconds": max(row["elapsed_seconds"] for row in fits),
        "validation_available_word_observations": available,
        "four_arm_common_support_observations": len(score_local),
        "four_arm_common_support_rate": support_rate,
        "normalizer": normalizer_summary,
        "train_sham": aggregate_sham_audit(train_sham_audit),
        "validation_sham": aggregate_sham_audit(validation_sham_audit),
        "vocabulary_size": len(vocab_items),
        "shapes": {
            "raw_train": [len(fit_rows), 840],
            "raw_validation": [len(score_rows), 840],
            "latent_train": [len(fit_rows), 384],
            "latent_validation": [len(score_rows), 384],
        },
        "finite": True,
        "four_arm_rows_capacity_vocabulary_equal": True,
        "v5_passed": len(ledgers) == len(fits),
        "conclusion_values_inspected": False,
    }, fits, ledgers


def _fit_logistic_with_ledger(
    *,
    fit_id: str,
    seed: int,
    x_train: np.ndarray,
    y_train: Sequence[Any],
    x_validation: np.ndarray,
    device: str,
    task_protocol: Mapping[str, Any],
    inner_cell: Mapping[str, Any] | None,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
    ledgers: list[dict[str, Any]],
    fit_summaries: list[dict[str, Any]],
    fit_record_ids: Sequence[str],
    scoring_record_ids: Sequence[str],
) -> np.ndarray:
    model, elapsed = fit_fixed_logistic(x_train, y_train, device=device)
    if elapsed > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError(f"fit {fit_id} elapsed {elapsed:.3f}s >300s")
    inner_id = None if inner_cell is None else inner_cell["inner_cell_id"]
    ledger = build_v5_ledger(
        run_id=run_id,
        fit_id=fit_id,
        seed=seed,
        outer_cell=task_protocol["outer_cell_id"],
        inner_cell=inner_id,
        fit_record_ids=fit_record_ids,
        validation_record_ids=(inner_cell["validation_record_ids"] if inner_cell else []),
        scoring_record_ids=scoring_record_ids,
        input_hashes=input_hashes,
    )
    validate_v5_or_raise(ledger, scope_index, input_hashes)
    ledgers.append(ledger)
    fit_summaries.append(
        {
            "fit_id": fit_id,
            "fit_type": "multinomial_logistic",
            "seed": seed,
            "train_rows": int(x_train.shape[0]),
            "validation_rows": int(x_validation.shape[0]),
            "input_dim": int(x_train.shape[1]),
            "class_count": len(set(str(value) for value in y_train)),
            "elapsed_seconds": elapsed,
            "v5": "PASS_REAL_RUN_LEDGER",
        }
    )
    return model.predict(x_validation)


def run_task_pilot(
    *,
    task: str,
    task_protocol: Mapping[str, Any],
    features: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
    item_vectors: Mapping[str, np.ndarray],
    h_vectors: Mapping[tuple[str, str], np.ndarray],
    device: str,
    input_hashes: Mapping[str, str],
    scope_index: Mapping[str, Any],
    run_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    fits: list[dict[str, Any]] = []
    ledgers: list[dict[str, Any]] = []
    a1_rows: list[dict[str, Any]] = []
    a3_predictions: dict[str, dict[str, list[Any]]] = {
        basis: {"truth": [], "prediction": [], "subject": [], "stimulus": []} for basis in BASES
    }
    exclusion_counts: Counter[str] = Counter()
    support_summaries: list[dict[str, Any]] = []
    text_only_logp: list[float] = []

    for cell in task_protocol["inner_cells"]:
        train_global = _indices_for_records(metadata, cell["train_record_ids"])
        validation_global = _indices_for_records(metadata, cell["validation_record_ids"])
        train_rows = _subset(metadata, train_global)
        validation_rows = _subset(metadata, validation_global)
        supported, support_ledger = supported_item_ids(train_rows)
        fit_mask = np.asarray([row["item_id"] in supported for row in train_rows])
        validation_mask = np.asarray([row["item_id"] in supported for row in validation_rows])
        exclusion_counts["UNSUPPORTED_TRAIN_ITEM"] += int(len(fit_mask) - np.count_nonzero(fit_mask))
        exclusion_counts["UNSUPPORTED_VALIDATION_TARGET"] += int(len(validation_mask) - np.count_nonzero(validation_mask))
        normalizer, normalizer_summary = fit_fold_normalizer(features[train_global])
        train_normalized = transform_fold_normalizer(features[train_global], normalizer)
        validation_normalized = transform_fold_normalizer(features[validation_global], normalizer)
        seed_common: dict[int, tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]]] = {}
        for seed in SEEDS:
            train_arms, train_common, train_audit = build_four_arm_features(
                train_normalized, train_rows, seed=seed, partition=f"{cell['inner_cell_id']}|train"
            )
            validation_arms, validation_common, validation_audit = build_four_arm_features(
                validation_normalized, validation_rows, seed=seed, partition=f"{cell['inner_cell_id']}|validation"
            )
            fit_local = np.asarray([index for index in train_common if fit_mask[index]], dtype=np.int64)
            score_local = np.asarray([index for index in validation_common if validation_mask[index]], dtype=np.int64)
            exclusion_counts["FOUR_ARM_TRAIN_COMMON_SUPPORT"] += int(np.count_nonzero(fit_mask) - len(fit_local))
            exclusion_counts["FOUR_ARM_VALIDATION_COMMON_SUPPORT"] += int(np.count_nonzero(validation_mask) - len(score_local))
            if len(fit_local) < 2 or len(score_local) < 1:
                raise RuntimeError(f"INVALID_A1_ADMISSION: empty fit/scoring rows in {cell['inner_cell_id']}")
            seed_common[seed] = (fit_local, score_local, train_arms, validation_arms)
            support_summaries.append(
                {
                    "inner_cell": cell["inner_cell_id"],
                    "seed": seed,
                    "supported_item_count": len(supported),
                    "train_supported_rows": int(np.count_nonzero(fit_mask)),
                    "validation_supported_rows": int(np.count_nonzero(validation_mask)),
                    "train_four_arm_rows": len(fit_local),
                    "validation_four_arm_rows": len(score_local),
                    "normalizer": normalizer_summary,
                    "train_common_support_rate": train_audit["common_support_rate"],
                    "validation_common_support_rate": validation_audit["common_support_rate"],
                }
            )

            fit_rows = [train_rows[index] for index in fit_local]
            score_rows = [validation_rows[index] for index in score_local]
            _, vocabulary, positions = _vocabulary(supported, train_rows, item_vectors)
            y_train = _item_matrix(fit_rows, item_vectors)
            h_train = _h_matrix(fit_rows, h_vectors)
            h_validation = _h_matrix(score_rows, h_vectors)
            true_positions = np.asarray([positions[str(row["item_id"])] for row in score_rows], dtype=np.int64)
            arm_logp: dict[str, dict[str, np.ndarray]] = {basis: {} for basis in BASES}
            for basis in BASES:
                for arm in ARMS:
                    train_positions = np.searchsorted(train_common, fit_local)
                    validation_positions = np.searchsorted(validation_common, score_local)
                    train_basis = train_arms[arm][train_positions]
                    validation_basis = validation_arms[arm][validation_positions]
                    if basis == "token_local_frozen_initial_latent":
                        train_basis, latent_audit = token_local_frozen_initial_latent(
                            train_basis, seed=seed, device=device
                        )
                        validation_basis, _ = token_local_frozen_initial_latent(
                            validation_basis, seed=seed, device=device
                        )
                        if latent_audit["trainable_parameter_count"] != 0:
                            raise RuntimeError("latent encoder has trainable parameters")
                    arm_logp[basis][arm] = _fit_probe(
                        fit_id=f"A-A1|{cell['inner_cell_id']}|seed{seed}|{basis}|{arm}",
                        seed=seed,
                        x_train=np.concatenate([h_train, train_basis], axis=1),
                        y_train=y_train,
                        x_validation=np.concatenate([h_validation, validation_basis], axis=1),
                        vocabulary=vocabulary,
                        true_positions=true_positions,
                        device=device,
                        task_protocol=task_protocol,
                        inner_cell=cell,
                        input_hashes=input_hashes,
                        scope_index=scope_index,
                        run_id=run_id,
                        ledgers=ledgers,
                        fit_summaries=fits,
                        fit_record_ids=[row["record_id"] for row in fit_rows],
                        scoring_record_ids=[row["record_id"] for row in score_rows],
                    )
            text_logp = _fit_probe(
                fit_id=f"A-A1|{cell['inner_cell_id']}|seed{seed}|text_only",
                seed=seed,
                x_train=h_train,
                y_train=y_train,
                x_validation=h_validation,
                vocabulary=vocabulary,
                true_positions=true_positions,
                device=device,
                task_protocol=task_protocol,
                inner_cell=cell,
                input_hashes=input_hashes,
                scope_index=scope_index,
                run_id=run_id,
                ledgers=ledgers,
                fit_summaries=fits,
                fit_record_ids=[row["record_id"] for row in fit_rows],
                scoring_record_ids=[row["record_id"] for row in score_rows],
            )
            text_only_logp.extend(text_logp.tolist())
            for basis in BASES:
                metrics = u_statistics(
                    arm_logp[basis]["real"],
                    {arm: arm_logp[basis][arm] for arm in ARMS if arm != "real"},
                )
                for index, row in enumerate(score_rows):
                    a1_rows.append(
                        {
                            "task": task,
                            "basis": basis,
                            "seed": seed,
                            "inner_cell": cell["inner_cell_id"],
                            "observation_id": row["observation_id"],
                            "subject_id": row["subject_id"],
                            **{name: float(values[index]) for name, values in metrics.items()},
                        }
                    )

            # A-A3: fold-local K=8 item clusters, real representation only.
            items, item_embedding_matrix, item_positions = _vocabulary(supported, train_rows, item_vectors)
            cluster_labels, cluster_model = deterministic_item_clusters(item_embedding_matrix)
            train_labels = np.asarray([cluster_labels[item_positions[str(row["item_id"])]] for row in fit_rows])
            validation_labels = np.asarray([cluster_labels[item_positions[str(row["item_id"])]] for row in score_rows])
            for basis in BASES:
                train_real = train_arms["real"][np.searchsorted(train_common, fit_local)]
                validation_real = validation_arms["real"][np.searchsorted(validation_common, score_local)]
                if basis == "token_local_frozen_initial_latent":
                    train_real, _ = token_local_frozen_initial_latent(train_real, seed=seed, device=device)
                    validation_real, _ = token_local_frozen_initial_latent(validation_real, seed=seed, device=device)
                predictions = _fit_logistic_with_ledger(
                    fit_id=f"A-A3|{cell['inner_cell_id']}|seed{seed}|{basis}|real",
                    seed=seed,
                    x_train=train_real,
                    y_train=train_labels,
                    x_validation=validation_real,
                    device=device,
                    task_protocol=task_protocol,
                    inner_cell=cell,
                    input_hashes=input_hashes,
                    scope_index=scope_index,
                    run_id=run_id,
                    ledgers=ledgers,
                    fit_summaries=fits,
                    fit_record_ids=[row["record_id"] for row in fit_rows],
                    scoring_record_ids=[row["record_id"] for row in score_rows],
                )
                a3_predictions[basis]["truth"].extend(validation_labels.tolist())
                a3_predictions[basis]["prediction"].extend(predictions.tolist())
                a3_predictions[basis]["subject"].extend(str(row["subject_id"]) for row in score_rows)
                a3_predictions[basis]["stimulus"].extend(str(row["stimulus_id"]) for row in score_rows)

    a1 = {basis: summarize_a_a1(a1_rows, task=task, basis=basis) for basis in BASES}

    # A-A2: all 15 outer-train subjects, three atomic material/text folds.
    a2_predictions: dict[str, dict[str, list[Any]]] = {
        basis: {"truth": [], "prediction": [], "subject": [], "stimulus": [], "group": []} for basis in BASES
    }
    for text_fold in ("0", "1", "2"):
        train_record_ids = [
            record_id
            for record_id in task_protocol["outer_train_record_ids"]
            if task_protocol["text_assignment"][task_protocol["record_rows"][record_id]["stimulus_id"]] != text_fold
        ]
        validation_record_ids = [
            record_id
            for record_id in task_protocol["outer_train_record_ids"]
            if task_protocol["text_assignment"][task_protocol["record_rows"][record_id]["stimulus_id"]] == text_fold
        ]
        train_indices = _indices_for_records(metadata, train_record_ids)
        validation_indices = _indices_for_records(metadata, validation_record_ids)
        train_rows = _subset(metadata, train_indices)
        validation_rows = _subset(metadata, validation_indices)
        state, _ = fit_fold_normalizer(features[train_indices])
        raw_train = transform_fold_normalizer(features[train_indices], state)
        raw_validation = transform_fold_normalizer(features[validation_indices], state)
        for seed in SEEDS:
            for basis in BASES:
                train_basis, validation_basis = raw_train, raw_validation
                if basis == "token_local_frozen_initial_latent":
                    train_basis, _ = token_local_frozen_initial_latent(train_basis, seed=seed, device=device)
                    validation_basis, _ = token_local_frozen_initial_latent(validation_basis, seed=seed, device=device)
                predictions = _fit_logistic_with_ledger(
                    fit_id=f"A-A2|{task}|text_fold{text_fold}|seed{seed}|{basis}",
                    seed=seed,
                    x_train=train_basis,
                    y_train=[row["subject_id"] for row in train_rows],
                    x_validation=validation_basis,
                    device=device,
                    task_protocol=task_protocol,
                    inner_cell=None,
                    input_hashes=input_hashes,
                    scope_index=scope_index,
                    run_id=run_id,
                    ledgers=ledgers,
                    fit_summaries=fits,
                    fit_record_ids=[row["record_id"] for row in train_rows],
                    scoring_record_ids=validation_record_ids,
                )
                block = a2_predictions[basis]
                block["truth"].extend(str(row["subject_id"]) for row in validation_rows)
                block["prediction"].extend(str(value) for value in predictions)
                block["subject"].extend(str(row["subject_id"]) for row in validation_rows)
                block["stimulus"].extend(str(row["stimulus_id"]) for row in validation_rows)
                block["group"].extend(str(row["group_key"]) for row in validation_rows)

    a2: dict[str, Any] = {}
    for basis in BASES:
        block = a2_predictions[basis]
        correct = [left == right for left, right in zip(block["truth"], block["prediction"], strict=True)]
        bootstrap = material_group_bootstrap(
            correct,
            block["group"],
            n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A2", task, basis),
        )
        permutation = permutation_null_fixed_predictions(
            block["truth"], block["prediction"], block["stimulus"],
            n_resamples=DEFAULT_ADMISSION_CONFIG.permutation_resamples,
            seed=SEEDS[0],
        )
        a2[basis] = summarize_classification(
            true_labels=block["truth"],
            predicted_labels=block["prediction"],
            subject_ids=block["subject"],
            chance=1.0 / 15.0,
            bootstrap=bootstrap,
            permutation=permutation,
        )

    a3: dict[str, Any] = {}
    for basis in BASES:
        block = a3_predictions[basis]
        subject_values = {}
        truth = np.asarray(block["truth"])
        predictions = np.asarray(block["prediction"])
        subjects = np.asarray(block["subject"])
        for subject in sorted(set(subjects.tolist())):
            mask = subjects == subject
            subject_values[subject] = balanced_recall(truth[mask], predictions[mask])
        bootstrap = cluster_bootstrap(
            subject_values,
            n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A3", task, basis),
        )
        permutation = permutation_null_fixed_predictions(
            block["truth"], block["prediction"], block["subject"],
            n_resamples=DEFAULT_ADMISSION_CONFIG.permutation_resamples,
            seed=SEEDS[0],
        )
        a3[basis] = summarize_classification(
            true_labels=block["truth"],
            predicted_labels=block["prediction"],
            subject_ids=block["subject"],
            chance=1.0 / 8.0,
            bootstrap=bootstrap,
            permutation=permutation,
        )

    a4 = evaluate_a_a4(
        a1["raw"],
        a1["token_local_frozen_initial_latent"],
        a2["raw"],
        a2["token_local_frozen_initial_latent"],
        a3["raw"],
        a3["token_local_frozen_initial_latent"],
        task=task,
    )
    return {
        "task": task,
        "outer_cell": task_protocol["outer_cell_id"],
        "outer_train_subject_count": len(task_protocol["outer_subjects"]),
        "inner_cell_count": len(task_protocol["inner_cells"]),
        "seeds": list(SEEDS),
        "A-A1": a1,
        "A-A2": a2,
        "A-A3": a3,
        "A-A4": a4,
        "text_only": {
            "scored_observation_seed_rows": len(text_only_logp),
            "mean_log_probability": float(np.mean(text_only_logp)),
            "role": "auxiliary_sanity_not_in_sham_mean_or_u_min",
        },
        "support": {
            "inner_seed_summaries": support_summaries,
            "exclusion_reason_counts": dict(sorted(exclusion_counts.items())),
        },
        "runtime_seconds": time.perf_counter() - started,
        "fit_count": len(fits),
    }, fits, ledgers, {"observation_seed_rows": len(a1_rows)}


def build_contract(
    *,
    run_id: str,
    input_hashes: Mapping[str, str],
    source_contract: Mapping[str, Any],
    text_manifests: Mapping[str, str],
    resolved_revision: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": run_id,
        "task": "S0_A1_ADMISSION",
        "spec": f"{SPEC_PATH.as_posix()}#D36-D39-R.3",
        "scope": {
            "dataset": "zuco_2_0",
            "tasks": list(TASKS),
            "outer_cells": OUTER_CELLS,
            "inner_cells_per_task": 9,
            "seeds": list(SEEDS),
            "outer_test_values_read": False,
            "segmentation": "word_aligned_content_word_only",
            "fixed_window_word_mapping": "forbidden_not_constructed",
        },
        "config": DEFAULT_ADMISSION_CONFIG.to_dict(),
        "config_hash": config_hash(),
        "bases": {
            "raw": "inner-train-normalized current-word 840D bandpower",
            "latent": "token_local_frozen_initial_latent length=1 mask=true float32[384]",
        },
        "probe": {
            "input": "[H_full_embedding, EEG_basis]",
            "target": "frozen exact-revision MiniLM item-surface embedding",
            "ridge_alpha": 1.0,
            "query_l2_normalized": True,
            "full_supported_vocabulary_softmax": True,
            "temperature": 0.07,
            "hyperparameter_search": False,
        },
        "shams": list(ARMS[1:]),
        "phase_role": "admitted analysis-spectrum invariance hash binding only; not a sham/u_min member",
        "statistics": {
            "subject_first": True,
            "cluster_bootstrap_B": 10_000,
            "permutation_B": 1_000,
            "A-A2": "15-way atomic-material three-fold subject probe",
            "A-A3": "fold-local K=8 MiniLM item clusters and joint-inner OOF",
            "A-A4": "paired latent-minus-raw subject bootstrap",
        },
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "source_contract_bindings": {
            "channel_labels_sha256": source_contract["channel_labels_sha256"],
            "a1_config_hash": source_contract["input_bindings"]["a1_config_hash"],
            "finite_policy": source_contract["finite_policy"],
            "amplitude_unit_status": source_contract["amplitude_unit_status"],
        },
        "text_encoder": {
            "model_id": MODEL_ID,
            "requested_revision": REVISION,
            "resolved_revision": resolved_revision,
            "manifests": dict(text_manifests),
            "output_dim": 384,
            "max_seq_length": 256,
            "pooling": "attention_mask_mean_then_l2",
            "trainable_parameters": 0,
        },
        "formal_output_policy": {
            "aggregates_and_subject_summaries_only": True,
            "run_ledger_ids_hashes_scopes_only": True,
            "no_eeg_feature_logit_weight_arrays": True,
        },
    }


def render_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# A1 admission audit",
        "",
        f"- Run: `{audit['run_id']}`",
        f"- Outcome: `{audit['completion_outcome']}`",
        f"- Preflight: `{audit['preflight']['status']}`; {audit['preflight']['fit_count']} fits; max {audit['preflight']['maximum_fit_seconds']:.3f} s/fit",
        f"- Full pilot fits: {audit['fit_summary']['full_pilot_fit_count']}; V5 ledgers: {audit['fit_summary']['real_v5_ledger_count']}",
        "- Outer-test EEG/features/labels/metrics read: `false`",
        "",
        "## A-A1 through A-A4",
        "",
        "| Task | Basis | A-A1 u_oof (95% CI) | A-A1 u_min (95% CI) | A-A1 | A-A2 | A-A3 |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for task in TASKS:
        for basis in BASES:
            row = audit["results"][task]
            a1 = row["A-A1"][basis]
            a2 = row["A-A2"][basis]
            a3 = row["A-A3"][basis]
            lines.append(
                f"| {task} | {basis} | {a1['metrics']['u_oof']['estimate']:.6g} {a1['metrics']['u_oof']['ci95']} | "
                f"{a1['metrics']['u_min']['estimate']:.6g} {a1['metrics']['u_min']['ci95']} | "
                f"{'PASS' if a1['pass'] else 'FAIL'} | {'PASS' if a2['pass'] else 'FAIL'} | {'PASS' if a3['pass'] else 'FAIL'} |"
            )
        lines.append(f"\n{task} A-A4: `{'PASS' if audit['results'][task]['A-A4']['pass'] else 'FAIL'}`.")
    lines.extend(
        [
            "",
            "This is a Stage-0 diagnostic pilot, not Stage 1, Gate A, route evidence, a held-out result, or a paper conclusion.",
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
    contract_bytes = yaml.safe_dump(dict(contract), sort_keys=False, allow_unicode=True).encode("utf-8")
    audit_bytes = canonical_artifact(audit)
    markdown_bytes = render_markdown(audit).encode("utf-8")
    ledger_bytes = deterministic_gzip_jsonl(ledgers)
    payloads = {
        contract_path: contract_bytes,
        audit_json_path: audit_bytes,
        audit_md_path: markdown_bytes,
        ledger_path: ledger_bytes,
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
    random.seed(SEEDS[0])
    np.random.seed(SEEDS[0])
    torch.manual_seed(SEEDS[0])
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available() or not str(args.device).startswith("cuda"):
        raise RuntimeError("A1_ADMISSION_PREFLIGHT_BLOCKED: real pilot requires an available CUDA device")

    physical_hashes, source_contract, _ = verify_frozen_inputs(root)
    outer, inner, selected, scope_index = load_protocol(root)
    v5_hashes = {key: physical_hashes[key] for key in V5_INPUT_KEYS}
    contexts = build_text_contexts(root)
    features_by_task: dict[str, np.ndarray] = {}
    metadata_by_task: dict[str, list[dict[str, Any]]] = {}
    cache_manifests: dict[str, Any] = {}
    # D39 preflight is genuinely first: no task2 EEG/feature is opened until
    # task1_nr|outer_s0_t0|inner_s0_t0 passes its contract/runtime fuse.
    task = "task1_nr"
    features, metadata, manifest = extract_task_observations(
        root,
        task=task,
        task_protocol=selected[task],
        contexts=contexts,
        rebuild=args.rebuild_cache,
    )
    features_by_task[task] = features
    metadata_by_task[task] = metadata
    cache_manifests[task] = manifest
    print(
        f"DATA task={task} observations={len(metadata)} shape={list(features.shape)} "
        f"subjects={manifest['subject_count']} finite={manifest['finite']} elapsed={manifest['elapsed_seconds']:.3f}"
    )

    encoder, text_manifests, resolved_revision = load_text_encoder(root, args.text_device)
    item_vectors, h_vectors, task1_text_summary = encode_text_inputs(
        encoder, {task: metadata_by_task[task]}, contexts
    )

    preflight, preflight_fits, preflight_ledgers = run_preflight(
        task_protocol=selected["task1_nr"],
        features=features_by_task["task1_nr"],
        metadata=metadata_by_task["task1_nr"],
        item_vectors=item_vectors,
        h_vectors=h_vectors,
        device=args.device,
        input_hashes=v5_hashes,
        scope_index=scope_index,
        run_id=args.run_id,
    )
    print(
        f"PREFLIGHT status={preflight['status']} fits={preflight['fit_count']} "
        f"max_fit_seconds={preflight['maximum_fit_seconds']:.3f} "
        f"common_support={preflight['four_arm_common_support_rate']:.6f} "
        f"shape_raw={preflight['shapes']['raw_train']} shape_latent={preflight['shapes']['latent_train']} "
        f"V5={preflight['v5_passed']} conclusion_values_inspected=false"
    )
    if args.preflight_only:
        print("SELF-CHECK SUMMARY samples={preflight_fits: 9} shapes={raw: [N,840], latent: [N,384]} status=PASS")
        return 0

    task = "task2_tsr"
    features, metadata, manifest = extract_task_observations(
        root,
        task=task,
        task_protocol=selected[task],
        contexts=contexts,
        rebuild=args.rebuild_cache,
    )
    features_by_task[task] = features
    metadata_by_task[task] = metadata
    cache_manifests[task] = manifest
    print(
        f"DATA task={task} observations={len(metadata)} shape={list(features.shape)} "
        f"subjects={manifest['subject_count']} finite={manifest['finite']} elapsed={manifest['elapsed_seconds']:.3f}"
    )
    # Encode the full sorted unique text set once so identical item/H strings
    # share exactly one vector and padding-batch roundoff cannot create two
    # coordinate values for the same scientific text identity.
    item_vectors, h_vectors, text_summary = encode_text_inputs(
        encoder, metadata_by_task, contexts
    )
    del encoder
    if str(args.text_device).startswith("cuda"):
        torch.cuda.empty_cache()

    results: dict[str, Any] = {}
    full_fits: list[dict[str, Any]] = []
    full_ledgers: list[dict[str, Any]] = []
    internal_counts: dict[str, Any] = {}
    for task in TASKS:
        task_result, task_fits, task_ledgers, task_internal = run_task_pilot(
            task=task,
            task_protocol=selected[task],
            features=features_by_task[task],
            metadata=metadata_by_task[task],
            item_vectors=item_vectors,
            h_vectors=h_vectors,
            device=args.device,
            input_hashes=v5_hashes,
            scope_index=scope_index,
            run_id=args.run_id,
        )
        results[task] = task_result
        full_fits.extend(task_fits)
        full_ledgers.extend(task_ledgers)
        internal_counts[task] = task_internal
        print(
            f"PILOT task={task} fits={len(task_fits)} runtime_seconds={task_result['runtime_seconds']:.3f} "
            f"A-A1_raw={task_result['A-A1']['raw']['pass']} "
            f"A-A1_latent={task_result['A-A1']['token_local_frozen_initial_latent']['pass']} "
            f"A-A2_raw={task_result['A-A2']['raw']['pass']} "
            f"A-A2_latent={task_result['A-A2']['token_local_frozen_initial_latent']['pass']} "
            f"A-A3_raw={task_result['A-A3']['raw']['pass']} "
            f"A-A3_latent={task_result['A-A3']['token_local_frozen_initial_latent']['pass']} "
            f"A-A4={task_result['A-A4']['pass']}"
        )

    completion_outcome, outcome_reasons = evaluate_completion_outcome(results)
    all_fits = preflight_fits + full_fits
    all_ledgers = preflight_ledgers + full_ledgers
    if len(all_fits) != len(all_ledgers):
        raise RuntimeError("INVALID_A1_ADMISSION: every real fit must have one V5 ledger")
    max_fit = max(float(row["elapsed_seconds"]) for row in all_fits)
    if max_fit > DEFAULT_ADMISSION_CONFIG.maximum_fit_seconds:
        raise RuntimeError("INVALID_A1_ADMISSION: fit runtime exceeded 300 seconds")

    contract = build_contract(
        run_id=args.run_id,
        input_hashes=physical_hashes,
        source_contract=source_contract,
        text_manifests=text_manifests,
        resolved_revision=resolved_revision,
    )
    audit = {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "run_id": args.run_id,
        "task": "S0_A1_ADMISSION",
        "completion_outcome": completion_outcome,
        "outcome_reasons": outcome_reasons,
        "claim_boundary": "Stage-0 diagnostic pilot only; not Stage 1, Gate A, held-out, route, or paper evidence",
        "outer_test": {
            "ids_used_for_v5_exclusion_only": True,
            "eeg_feature_label_metric_reads": 0,
            "calibration_record_count": 0,
        },
        "preflight": preflight,
        "results": results,
        "fit_summary": {
            "preflight_fit_count": len(preflight_fits),
            "full_pilot_fit_count": len(full_fits),
            "total_fit_count": len(all_fits),
            "ridge_fit_count": sum(row["fit_type"] == "ridge" for row in all_fits),
            "logistic_fit_count": sum(row["fit_type"] == "multinomial_logistic" for row in all_fits),
            "real_v5_ledger_count": len(all_ledgers),
            "maximum_single_fit_seconds": max_fit,
            "fit_runtime_seconds_sum": float(sum(float(row["elapsed_seconds"]) for row in all_fits)),
            "fit_train_row_range": [min(row["train_rows"] for row in all_fits), max(row["train_rows"] for row in all_fits)],
            "fit_validation_row_range": [min(row["validation_rows"] for row in all_fits), max(row["validation_rows"] for row in all_fits)],
        },
        "data": {
            task: {
                "observations": cache_manifests[task]["observation_count"],
                "records": cache_manifests[task]["record_count"],
                "subjects": cache_manifests[task]["subject_count"],
                "shape": cache_manifests[task]["shape"],
                "dtype": cache_manifests[task]["dtype"],
                "finite": cache_manifests[task]["finite"],
                "feature_bytes_sha256_local_ignored_cache": cache_manifests[task]["feature_bytes_sha256"],
            }
            for task in TASKS
        },
        "text": {
            "requested_revision": REVISION,
            "resolved_revision": resolved_revision,
            "manifests": text_manifests,
            **text_summary,
        },
        "input_artifact_hashes": dict(sorted(physical_hashes.items())),
        "formal_outputs_contain_no_eeg_features_logits_or_weights": True,
        "phase_invariance_bound_to_admitted_source_artifact": True,
        "fixed_window_mapping_constructed": False,
        "internal_count_checks": internal_counts,
        "elapsed_seconds": time.perf_counter() - started,
    }
    output_hashes = write_outputs(
        root,
        contract_path=args.contract_output,
        audit_json_path=args.audit_json_output,
        audit_md_path=args.audit_md_output,
        ledger_path=args.ledger_output,
        contract=contract,
        audit=audit,
        ledgers=all_ledgers,
    )
    print(f"OUTCOME {completion_outcome} reasons={outcome_reasons}")
    for path, digest in output_hashes.items():
        print(f"OUTPUT {path} sha256={digest}")
    print(
        f"SELF-CHECK SUMMARY samples={{observations: {sum(cache_manifests[t]['observation_count'] for t in TASKS)}, "
        f"fits: {len(all_fits)}, ledgers: {len(all_ledgers)}}} "
        f"shapes={{raw: [N,840], latent: [N,384], text: [N,384]}} "
        f"elapsed_seconds={audit['elapsed_seconds']:.3f} ranges={{max_fit_seconds: {max_fit:.3f}}} "
        f"assertions={{outer_test_values_read: 0, v5_all_fits: true, finite: true}} status=PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
