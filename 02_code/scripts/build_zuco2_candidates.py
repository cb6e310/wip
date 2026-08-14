#!/usr/bin/env python3
"""Build frozen ZuCo 2.0 sentence candidates without reading EEG values."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch
import yaml
from huggingface_hub import snapshot_download


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from data.candidates import (  # noqa: E402
    DEFAULT_SEED,
    FROZEN_PROVENANCE,
    FROZEN_SOURCE_JOIN_MAPPING,
    build_candidate_artifacts,
    exact_text_sha256,
    file_sha256,
    validate_candidate_artifacts,
    write_candidate_triplet,
)
from data.inner_split import validate_inner_artifact  # noqa: E402
from data.joint_split import canonical_json_bytes, sha256_bytes, validate_artifact  # noqa: E402
from data.zuco2_loader import TASKS, iter_summary_files, validate_config  # noqa: E402
from data.zuco2_source_join import prove_task_source_join, read_summary_contents  # noqa: E402
from text.frozen_minilm import (  # noqa: E402
    DEFAULT_CONFIG,
    MODEL_ID,
    REVISION,
    FrozenMiniLMEncoder,
    aggregate_file_hash,
    sha256_file,
)
from text_encoder_selfcheck import _classify_snapshot_hashes  # noqa: E402


RUN_ID = "2026-08-14_019_v310_zuco2_candidates"
DEFAULT_DATASET_ROOT = Path("01_data_protocol/datasets/zuco_2.0")
DEFAULT_OUTER = Path("01_data_protocol/splits/zuco_2_0_outer_folds.json")
DEFAULT_INNER = Path("01_data_protocol/splits/zuco_2_0_inner_folds.json")
DEFAULT_INNER_SUPPORT = Path("04_results/audits/zuco2_inner_split_support.json")
DEFAULT_SOURCE_JOIN = Path("artifacts/zuco2_source_slot_join.yaml")
DEFAULT_H = Path("artifacts/h_definition.yaml")
DEFAULT_ENCODER = Path("artifacts/text_encoder_freeze.yaml")
DEFAULT_CANDIDATES = Path("01_data_protocol/candidates/candidate_lists.json")
DEFAULT_PAIRS = Path("01_data_protocol/candidates/paired_verification_pairs.json")
DEFAULT_AUDIT = Path("04_results/audits/zuco2_candidate_feasibility.json")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_integrity(value: Mapping[str, Any], label: str) -> str:
    block = value.get("integrity")
    if not isinstance(block, Mapping):
        raise RuntimeError(f"STATE_SPEC_CONFLICT: {label} has no integrity block")
    payload = dict(value)
    payload.pop("integrity", None)
    encoded = canonical_json_bytes(payload)
    digest = sha256_bytes(encoded)
    if block.get("canonical_payload_sha256") != digest or block.get(
        "canonical_payload_bytes"
    ) != len(encoded):
        raise RuntimeError(f"STATE_SPEC_CONFLICT: {label} canonical integrity mismatch")
    return digest


def _verify_frozen_inputs(
    outer_path: Path,
    inner_path: Path,
    support_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    expected = {
        outer_path: FROZEN_PROVENANCE["outer_file_sha256"],
        inner_path: FROZEN_PROVENANCE["inner_file_sha256"],
        support_path: FROZEN_PROVENANCE["inner_support_file_sha256"],
    }
    for path, digest in expected.items():
        observed = file_sha256(path)
        if observed != digest:
            raise RuntimeError(
                f"STATE_SPEC_CONFLICT: {path} SHA256 {observed} != frozen {digest}"
            )
    outer, inner, support = (_load_json(path) for path in (outer_path, inner_path, support_path))
    outer_errors = [
        f"top-level assertion failed: {key}"
        for key, value in outer.get("assertions", {}).items()
        if value is not True
    ]
    outer_errors.extend(
        f"{task}: {error}"
        for task, panel in outer["panels"].items()
        for error in validate_artifact(panel)
    )
    if outer_errors:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: outer validation failed: {outer_errors}")
    inner_errors = validate_inner_artifact(inner)
    if inner_errors:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: inner validation failed: {inner_errors}")
    canonical = {
        "outer_canonical_payload_sha256": _verify_integrity(outer, "outer"),
        "inner_canonical_payload_sha256": _verify_integrity(inner, "inner"),
        "inner_support_canonical_payload_sha256": _verify_integrity(
            support, "inner support"
        ),
    }
    if inner.get("outer_file_sha256") != expected[outer_path]:
        raise RuntimeError("STATE_SPEC_CONFLICT: inner artifact binds a different outer file")
    shared_inner_fields = (
        "run_id",
        "config_hash",
        "outer_file_sha256",
        "outer_canonical_payload_sha256",
        "semantic_manifest",
        "observation_ledger",
    )
    if any(inner.get(key) != support.get(key) for key in shared_inner_fields):
        raise RuntimeError("STATE_SPEC_CONFLICT: inner support is not the admitted split's audit")
    return outer, inner, support, canonical


def _verify_contract_artifacts(
    source_join_path: Path,
    h_path: Path,
    encoder_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_join = yaml.safe_load(source_join_path.read_text(encoding="utf-8"))
    h_artifact = yaml.safe_load(h_path.read_text(encoding="utf-8"))
    encoder_artifact = yaml.safe_load(encoder_path.read_text(encoding="utf-8"))
    if source_join.get("status") != "PASS":
        raise RuntimeError("STATE_SPEC_CONFLICT: source-join artifact is not PASS")
    observed_mapping = {
        task: source_join["panels"][task]["mapping_sha256"] for task in TASKS
    }
    if observed_mapping != FROZEN_SOURCE_JOIN_MAPPING:
        raise RuntimeError("STATE_SPEC_CONFLICT: source-join artifact mapping mismatch")
    if file_sha256(h_path) != FROZEN_PROVENANCE["h_artifact_sha256"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: H artifact SHA256 mismatch")
    if h_artifact.get("config_hash") != FROZEN_PROVENANCE["h_config_hash"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: H config hash mismatch")
    if file_sha256(encoder_path) != FROZEN_PROVENANCE["encoder_artifact_sha256"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: text encoder artifact SHA256 mismatch")
    expected_encoder = {
        "encoder_tokenizer_manifest_hash": encoder_artifact["provenance"][
            "tokenizer_manifest_hash"
        ],
        "encoder_config_manifest_hash": encoder_artifact["provenance"][
            "encoder_config_manifest_hash"
        ],
        "encoder_model_manifest_hash": encoder_artifact["provenance"][
            "model_file_manifest_hash"
        ],
        "encoder_scientific_config_hash": encoder_artifact["model"][
            "scientific_config_hash"
        ],
    }
    for key, observed in expected_encoder.items():
        if observed != FROZEN_PROVENANCE[key]:
            raise RuntimeError(f"STATE_SPEC_CONFLICT: text encoder {key} mismatch")
    return source_join, h_artifact, encoder_artifact


def _material_manifest(dataset_root: Path) -> tuple[list[dict[str, Any]], str]:
    paths: list[Path] = []
    for task_spec in TASKS.values():
        paths.extend(sorted((dataset_root / "task_materials").glob(task_spec["material_glob"])))
    if not paths:
        raise FileNotFoundError("no released task-material files")
    rows = [
        {
            "path": path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in sorted(paths)
    ]
    return rows, sha256_bytes(canonical_json_bytes(rows))


def _released_rows(
    dataset_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str], dict[str, str]]:
    rows: list[dict[str, Any]] = []
    mappings: dict[str, str] = {}
    projections: dict[str, str] = {}
    sequences: dict[str, str] = {}
    for task in TASKS:
        proof = prove_task_source_join(dataset_root, task)
        if not proof.verified or proof.mapping_sha256 != FROZEN_SOURCE_JOIN_MAPPING[task]:
            raise RuntimeError(f"STATE_SPEC_CONFLICT: live {task} source join mismatch")
        first = next(iter_summary_files(dataset_root, task), None)
        if first is None:
            raise FileNotFoundError(f"{task}: no summary files")
        contents = read_summary_contents(first.path)
        for summary in iter_summary_files(dataset_root, task):
            if read_summary_contents(summary.path) != contents:
                raise RuntimeError(f"STATE_SPEC_CONFLICT: {task} subject text sequence differs")
        preceding_by_file: dict[str, list[str]] = {}
        for slot in proof.slots:
            text = contents[slot.summary_index - 1]
            text_hash = exact_text_sha256(text)
            if text_hash != slot.text_sha256:
                raise RuntimeError(f"STATE_SPEC_CONFLICT: exact text hash changed for {slot.source_slot_key}")
            preceding = preceding_by_file.setdefault(slot.source_file, [])
            rows.append(
                {
                    "task": task,
                    "stimulus_id": slot.source_slot_key,
                    "source_file": slot.source_file,
                    "row_number": slot.row_number,
                    "exact_text": text,
                    "exact_text_sha256": text_hash,
                    "h_source_ids": preceding[-2:],
                }
            )
            preceding.append(slot.source_slot_key)
        mappings[task] = proof.mapping_sha256
        projections[task] = proof.material_projection_sha256
        sequences[task] = proof.summary_sequence_sha256
    rows.sort(key=lambda row: (row["task"], row["stimulus_id"]))
    if len(rows) != 739 or len({row["stimulus_id"] for row in rows}) != 739:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: expected 739 unique stimuli, got {len(rows)}")
    return rows, mappings, projections, sequences


def _token_count(tokenizer: Any, text: str) -> int:
    value = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        padding=False,
        return_attention_mask=False,
    )["input_ids"]
    if value and isinstance(value[0], (list, tuple)):
        value = value[0]
    count = len(value)
    if count <= 0:
        raise RuntimeError("released sentence produced no raw tokens")
    return count


def _load_encoder() -> tuple[FrozenMiniLMEncoder, dict[str, str], str]:
    snapshot = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=REVISION,
            local_files_only=True,
            ignore_patterns=["*.h5", "*.msgpack", "*.ot", "onnx/*", "openvino/*"],
        )
    ).resolve()
    if snapshot.name != REVISION:
        raise RuntimeError("STATE_SPEC_CONFLICT: resolved encoder revision differs")
    groups = _classify_snapshot_hashes(snapshot)
    manifests = {
        "tokenizer": aggregate_file_hash(groups["tokenizer"]),
        "encoder_config": aggregate_file_hash(groups["encoder_config"]),
        "model": aggregate_file_hash(groups["model"]),
        "scientific_config": DEFAULT_CONFIG.scientific_config_hash,
    }
    expected = {
        "tokenizer": FROZEN_PROVENANCE["encoder_tokenizer_manifest_hash"],
        "encoder_config": FROZEN_PROVENANCE["encoder_config_manifest_hash"],
        "model": FROZEN_PROVENANCE["encoder_model_manifest_hash"],
        "scientific_config": FROZEN_PROVENANCE["encoder_scientific_config_hash"],
    }
    if manifests != expected:
        raise RuntimeError(f"STATE_SPEC_CONFLICT: encoder cache manifests differ: {manifests}")
    encoder = FrozenMiniLMEncoder(
        tokenizer_manifest_hash=manifests["tokenizer"],
        encoder_config_manifest_hash=manifests["encoder_config"],
        device="cpu",
        local_files_only=True,
    )
    if encoder.trainable_parameter_count or encoder.model.training:
        raise RuntimeError("STATE_SPEC_CONFLICT: encoder is not frozen eval/no-grad")
    return encoder, manifests, snapshot.name


def _encode_rows(
    rows: list[dict[str, Any]], encoder: FrozenMiniLMEncoder, *, batch_size: int
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for start in range(0, len(rows), batch_size):
        batch_rows = rows[start : start + batch_size]
        encoded = encoder.encode([row["exact_text"] for row in batch_rows])
        array = encoded.embeddings.cpu().numpy().astype(np.float32, copy=False)
        for row, embedding in zip(batch_rows, array, strict=True):
            result.append(
                {
                    "task": row["task"],
                    "stimulus_id": row["stimulus_id"],
                    "exact_text_sha256": row["exact_text_sha256"],
                    "token_length": _token_count(encoder.tokenizer, row["exact_text"]),
                    "h_source_ids": list(row["h_source_ids"]),
                    "embedding": embedding,
                }
            )
    return result


def _build_scopes(outer: Mapping[str, Any], inner: Mapping[str, Any]) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    for task in TASKS:
        panel = outer["panels"][task]
        stimulus_fold = panel["text"]["stimulus_fold"]
        for text_fold in range(5):
            pool = sorted(key for key, value in stimulus_fold.items() if str(value) == str(text_fold))
            matching_cells = [cell for cell in panel["cells"] if str(cell["text_fold"]) == str(text_fold)]
            if len(matching_cells) != 6 or any(sorted(cell["test_stimulus_ids"]) != pool for cell in matching_cells):
                raise RuntimeError(f"STATE_SPEC_CONFLICT: {task}/outer_t{text_fold} reuse mismatch")
            scopes.append(
                {
                    "task": task,
                    "scope_type": "outer_test",
                    "scope_id": f"{task}|outer_t{text_fold}",
                    "outer_text_fold": str(text_fold),
                    "reuse_outer_subject_folds": [str(value) for value in range(6)],
                    "pool_ids": pool,
                }
            )
        outer_record_stimulus = {
            row["record_id"]: row["stimulus_id"] for row in panel["records"]
        }
        for cell in inner["panels"][task]["outer_cells"]:
            outer_train = {
                outer_record_stimulus[record_id] for record_id in cell["outer_train_record_ids"]
            }
            outer_test = set(cell["outer_test_stimulus_ids"])
            assigned = {
                stimulus_id: str(group["inner_text_fold"])
                for group in cell["text_group_assignments"]
                for stimulus_id in group["stimulus_ids"]
            }
            if set(assigned) != outer_train or set(assigned) & outer_test:
                raise RuntimeError(f"STATE_SPEC_CONFLICT: {cell['outer_cell_id']} inner scope isolation")
            for inner_fold in range(3):
                pool = sorted(key for key, value in assigned.items() if value == str(inner_fold))
                scopes.append(
                    {
                        "task": task,
                        "scope_type": "inner_validation",
                        "scope_id": f"{cell['outer_cell_id']}|inner_t{inner_fold}",
                        "outer_cell_id": cell["outer_cell_id"],
                        "outer_subject_fold": str(cell["outer_subject_fold"]),
                        "outer_text_fold": str(cell["outer_text_fold"]),
                        "inner_text_fold": str(inner_fold),
                        "reuse_inner_subject_folds": [str(value) for value in range(3)],
                        "pool_ids": pool,
                    }
                )
    outer_count = sum(scope["scope_type"] == "outer_test" for scope in scopes)
    inner_count = sum(scope["scope_type"] == "inner_validation" for scope in scopes)
    if (outer_count, inner_count) != (10, 180):
        raise RuntimeError(f"STATE_SPEC_CONFLICT: scope counts {(outer_count, inner_count)}")
    return scopes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--outer", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--inner", type=Path, default=DEFAULT_INNER)
    parser.add_argument("--inner-support", type=Path, default=DEFAULT_INNER_SUPPORT)
    parser.add_argument("--source-join", type=Path, default=DEFAULT_SOURCE_JOIN)
    parser.add_argument("--h-artifact", type=Path, default=DEFAULT_H)
    parser.add_argument("--encoder-artifact", type=Path, default=DEFAULT_ENCODER)
    parser.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--pairs-output", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    if args.seed != DEFAULT_SEED or args.batch_size <= 0:
        parser.error(f"seed is frozen to {DEFAULT_SEED}; batch size must be positive")
    if "roamm" in str(args.dataset_root).casefold() or "ds007629" in str(args.dataset_root).casefold():
        parser.error("ROAMM paths are forbidden")

    started = time.perf_counter()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    validate_config(args.dataset_root)
    outer, inner, _support, canonical = _verify_frozen_inputs(
        args.outer, args.inner, args.inner_support
    )
    _source_join_artifact, _h_artifact, _encoder_artifact = _verify_contract_artifacts(
        args.source_join, args.h_artifact, args.encoder_artifact
    )
    released, mappings, projections, sequences = _released_rows(args.dataset_root)
    material_rows, material_manifest_hash = _material_manifest(args.dataset_root)
    released_manifest = [
        {
            "task": row["task"],
            "stimulus_id": row["stimulus_id"],
            "exact_text_sha256": row["exact_text_sha256"],
        }
        for row in released
    ]
    h_manifest = [
        {"stimulus_id": row["stimulus_id"], "h_source_ids": row["h_source_ids"]}
        for row in released
    ]
    encoder, _manifests, resolved_revision = _load_encoder()
    stimuli = _encode_rows(released, encoder, batch_size=args.batch_size)
    scopes = _build_scopes(outer, inner)
    provenance = {
        "outer_file_sha256": file_sha256(args.outer),
        "outer_canonical_payload_sha256": canonical["outer_canonical_payload_sha256"],
        "inner_file_sha256": file_sha256(args.inner),
        "inner_canonical_payload_sha256": canonical["inner_canonical_payload_sha256"],
        "inner_support_file_sha256": file_sha256(args.inner_support),
        "inner_support_canonical_payload_sha256": canonical[
            "inner_support_canonical_payload_sha256"
        ],
        "source_join_artifact_sha256": file_sha256(args.source_join),
        "source_join_mapping_sha256": mappings,
        "source_join_material_projection_sha256": projections,
        "source_join_summary_sequence_sha256": sequences,
        "released_material_file_manifest": material_rows,
        "released_material_file_manifest_sha256": material_manifest_hash,
        "released_text_manifest_sha256": sha256_bytes(canonical_json_bytes(released_manifest)),
        "h_artifact_sha256": file_sha256(args.h_artifact),
        "h_source_sha256": sha256_file(SCRIPT_ROOT / "src/protocol/h_definition.py"),
        "h_config_hash": FROZEN_PROVENANCE["h_config_hash"],
        "h_identity_manifest_sha256": sha256_bytes(canonical_json_bytes(h_manifest)),
        "encoder_artifact_sha256": file_sha256(args.encoder_artifact),
        "encoder_implementation_sha256": sha256_file(SCRIPT_ROOT / "src/text/frozen_minilm.py"),
        "encoder_model_id": MODEL_ID,
        "encoder_revision": REVISION,
        "encoder_resolved_revision": resolved_revision,
        "encoder_tokenizer_manifest_hash": FROZEN_PROVENANCE[
            "encoder_tokenizer_manifest_hash"
        ],
        "encoder_config_manifest_hash": FROZEN_PROVENANCE[
            "encoder_config_manifest_hash"
        ],
        "encoder_model_manifest_hash": FROZEN_PROVENANCE[
            "encoder_model_manifest_hash"
        ],
        "encoder_scientific_config_hash": FROZEN_PROVENANCE[
            "encoder_scientific_config_hash"
        ],
        "read_fields": ["sentenceData/content", "task_materials"],
        "roamm_paths_read": [],
    }
    artifacts = build_candidate_artifacts(
        stimuli, scopes, provenance=provenance, seed=args.seed, run_id=RUN_ID
    )
    reverse = build_candidate_artifacts(
        reversed(stimuli), reversed(scopes), provenance=provenance, seed=args.seed, run_id=RUN_ID
    )
    if any(canonical_json_bytes(a) != canonical_json_bytes(b) for a, b in zip(artifacts, reverse, strict=True)):
        raise RuntimeError("reverse-input candidate construction is not byte-identical")
    errors = validate_candidate_artifacts(*artifacts)
    if errors:
        raise RuntimeError(f"candidate validation failed: {errors}")
    written = write_candidate_triplet(
        *artifacts,
        candidate_path=args.candidate_output,
        pair_path=args.pairs_output,
        audit_path=args.audit_output,
    )
    audit = artifacts[2]
    elapsed = time.perf_counter() - started
    counts = {
        task: {
            scope: audit["tasks"][task][scope]["target_count"]
            for scope in ("outer_test", "inner_validation")
        }
        for task in TASKS
    }
    legal = {
        task: {
            scope: audit["tasks"][task][scope]["stage_count_distributions"]["legal_count"]
            for scope in ("outer_test", "inner_validation")
        }
        for task in TASKS
    }
    print("ZUCO2 CANDIDATE SELF-CHECK")
    print(f"samples=739 embedding_shape={[len(stimuli), 384]} dtype=float32 scopes=190 targets={audit['target_count']}")
    print(f"target_counts={json.dumps(counts, sort_keys=True)}")
    print(f"legal_count_summary={json.dumps(legal, sort_keys=True)}")
    print(f"n_availability={json.dumps(audit['overall_n_availability'], sort_keys=True)}")
    print(f"seed={args.seed} repeats=5 method=ZuCo2-frozen-sentence-candidate-lists elapsed_seconds={elapsed:.3f}")
    print(f"artifact_sha256={json.dumps(written, sort_keys=True)}")
    print(f"reverse_input_byte_identical=true trainable_parameter_count={encoder.trainable_parameter_count} status=PASS outcome={audit['n50_outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
