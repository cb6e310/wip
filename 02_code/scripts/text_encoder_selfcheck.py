#!/usr/bin/env python3
"""Real-CPU admission for the exact SPEC v3.7 frozen MiniLM revision.

This is an engineering text-coordinate-system check only.  It does not load
EEG data, run alignment training, inspect held-out metrics or produce a paper
result.  Model weights remain in the Hugging Face cache outside the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import transformers
from huggingface_hub import snapshot_download


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from text.frozen_minilm import (  # noqa: E402
    DEFAULT_CONFIG,
    MODEL_ID,
    REVISION,
    FrozenMiniLMEncoder,
    aggregate_file_hash,
    exact_utf8_text_sha256,
    sha256_file,
)


RUN_ID = "2026-08-14_012_v37_text_encoder"
SEED = 20260813
FOLD = "S0-TEXT"
METHOD = "frozen-MiniLM-L6-v2"


def parse_args() -> argparse.Namespace:
    default_name = (
        f"text_encoder_selfcheck_seed{SEED}_fold{FOLD}_method{METHOD}_"
        f"cfg{DEFAULT_CONFIG.config_hash[:12]}.json"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "03_runs" / "debug_runs" / default_name,
    )
    return parser.parse_args()


def _classify_snapshot_hashes(snapshot: Path) -> dict[str, dict[str, str]]:
    all_files = {
        path.relative_to(snapshot).as_posix(): sha256_file(path)
        for path in sorted(snapshot.rglob("*"))
        if path.is_file()
    }
    tokenizer_names = {
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "vocab.txt",
        "vocab.json",
        "merges.txt",
        "sentencepiece.bpe.model",
        "spiece.model",
    }
    tokenizer = {
        name: digest for name, digest in all_files.items() if Path(name).name in tokenizer_names
    }
    model = {
        name: digest
        for name, digest in all_files.items()
        if Path(name).suffix in {".safetensors", ".bin"}
        and "optimizer" not in Path(name).name.lower()
    }
    config = {
        name: digest
        for name, digest in all_files.items()
        if Path(name).name == "config.json" or name == "sentence_bert_config.json"
    }
    if not tokenizer or not model or "config.json" not in config:
        raise RuntimeError(
            "incomplete provenance files: "
            f"tokenizer={sorted(tokenizer)}, model={sorted(model)}, config={sorted(config)}"
        )
    return {"tokenizer": tokenizer, "config": config, "model": model, "all": all_files}


def _aggregate(group: dict[str, str]) -> str:
    return aggregate_file_hash(group)


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)

    snapshot = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=REVISION,
            local_files_only=True,
            ignore_patterns=[
                "*.h5",
                "*.msgpack",
                "*.ot",
                "onnx/*",
                "openvino/*",
                "rust_model.ot",
            ],
        )
    ).resolve()
    resolved_revision = snapshot.name
    provenance = _classify_snapshot_hashes(snapshot)
    tokenizer_hash = _aggregate(provenance["tokenizer"])
    model_file_hash = _aggregate(provenance["model"])
    model_config_file_hash = _aggregate(provenance["config"])

    encoder = FrozenMiniLMEncoder(
        tokenizer_hash=tokenizer_hash,
        device="cpu",
        local_files_only=True,
    )
    config_resolved_revision = str(getattr(encoder.model.config, "_commit_hash", ""))

    short_text = "Frozen text embeddings must be deterministic."
    other_text = "A deliberately shorter input."
    first = encoder.encode(short_text)
    second = encoder.encode(short_text)
    padding_batch = encoder.encode([short_text, other_text])
    long_text = "longtoken " * (encoder.model_max_length + 64)
    long_result = encoder.encode(long_text)

    short_embedding = first.embeddings
    repeated_embedding = second.embeddings
    batch_first_embedding = padding_batch.embeddings[:1]
    short_norms = torch.linalg.vector_norm(short_embedding, dim=1)
    batch_norms = torch.linalg.vector_norm(padding_batch.embeddings, dim=1)
    long_norms = torch.linalg.vector_norm(long_result.embeddings, dim=1)
    padding_max_abs_diff = float((short_embedding - batch_first_embedding).abs().max().item())
    byte_identical = short_embedding.cpu().numpy().tobytes() == repeated_embedding.cpu().numpy().tobytes()
    long_record = long_result.records[0]

    model_file_keys = sorted(provenance["model"])
    loaded_model_weight_file = "model.safetensors"
    loaded_model_weight_sha256 = provenance["model"].get(loaded_model_weight_file, "")
    assertions = {
        "requested_revision_exact": REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "resolved_revision_exact": resolved_revision == REVISION,
        "model_config_revision_exact": config_resolved_revision == REVISION,
        "provenance_tokenizer_complete": bool(provenance["tokenizer"]),
        "provenance_config_complete": bool(provenance["config"]),
        "provenance_model_complete": bool(model_file_keys),
        "loaded_safetensors_hash_complete": len(loaded_model_weight_sha256) == 64,
        "model_eval": not encoder.model.training,
        "trainable_parameter_count_zero": encoder.trainable_parameter_count == 0,
        "short_shape_1x384": tuple(short_embedding.shape) == (1, 384),
        "short_dtype_float32": short_embedding.dtype == torch.float32,
        "short_finite": bool(torch.isfinite(short_embedding).all()),
        "short_l2_norm": bool(torch.allclose(short_norms, torch.ones_like(short_norms), atol=1e-6, rtol=1e-6)),
        "byte_identical_determinism": byte_identical,
        "padding_batch_shape_2x384": tuple(padding_batch.embeddings.shape) == (2, 384),
        "padding_batch_finite_l2": bool(
            torch.isfinite(padding_batch.embeddings).all()
            and torch.allclose(batch_norms, torch.ones_like(batch_norms), atol=1e-6, rtol=1e-6)
        ),
        "padding_mask_active": padding_max_abs_diff <= 1e-6,
        "long_shape_finite_l2": bool(
            tuple(long_result.embeddings.shape) == (1, 384)
            and torch.isfinite(long_result.embeddings).all()
            and torch.allclose(long_norms, torch.ones_like(long_norms), atol=1e-6, rtol=1e-6)
        ),
        "long_input_truncated": bool(
            long_record.truncated
            and long_record.token_count_before_truncation
            > long_record.token_count_after_truncation
        ),
    }
    passed = all(assertions.values())
    elapsed = time.perf_counter() - started
    record = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "status": "PASS" if passed else "FAIL",
        "seed": SEED,
        "fold": FOLD,
        "method": METHOD,
        "model_id": MODEL_ID,
        "requested_revision": REVISION,
        "resolved_revision": resolved_revision,
        "model_config_resolved_revision": config_resolved_revision,
        "environment": {
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "device": "cpu",
        },
        "provenance": {
            "cache_snapshot_path_recorded_as_external": str(snapshot),
            "tokenizer_file_sha256": provenance["tokenizer"],
            "config_file_sha256": provenance["config"],
            "model_file_sha256": provenance["model"],
            "loaded_model_weight_file": loaded_model_weight_file,
            "loaded_model_weight_sha256": loaded_model_weight_sha256,
            "transformer_config_sha256": provenance["config"]["config.json"],
            "tokenizer_hash": tokenizer_hash,
            "model_config_file_hash": model_config_file_hash,
            "model_file_hash": model_file_hash,
            "weights_copied_to_repository": False,
        },
        "text_encoder_config": DEFAULT_CONFIG.to_dict(),
        "text_encoder_config_hash": DEFAULT_CONFIG.config_hash,
        "input_text_sha256": {
            "short": exact_utf8_text_sha256(short_text),
            "other": exact_utf8_text_sha256(other_text),
            "long": exact_utf8_text_sha256(long_text),
        },
        "tokenization": {
            "model_max_length": encoder.model_max_length,
            "short": {
                "token_count_before_truncation": first.records[0].token_count_before_truncation,
                "token_count_after_truncation": first.records[0].token_count_after_truncation,
                "truncated": first.records[0].truncated,
            },
            "padding_batch": [
                {
                    "token_count_before_truncation": item.token_count_before_truncation,
                    "token_count_after_truncation": item.token_count_after_truncation,
                    "truncated": item.truncated,
                }
                for item in padding_batch.records
            ],
            "long": {
                "token_count_before_truncation": long_record.token_count_before_truncation,
                "token_count_after_truncation": long_record.token_count_after_truncation,
                "truncated": long_record.truncated,
            },
        },
        "outputs": {
            "short_shape": list(short_embedding.shape),
            "padding_batch_shape": list(padding_batch.embeddings.shape),
            "long_shape": list(long_result.embeddings.shape),
            "dtype": str(short_embedding.dtype).replace("torch.", ""),
            "short_norms": [float(value) for value in short_norms.tolist()],
            "padding_batch_norms": [float(value) for value in batch_norms.tolist()],
            "long_norms": [float(value) for value in long_norms.tolist()],
            "padding_max_abs_diff_vs_single": padding_max_abs_diff,
            "byte_identical_determinism": byte_identical,
        },
        "total_parameter_count": encoder.total_parameter_count,
        "trainable_parameter_count": encoder.trainable_parameter_count,
        "elapsed_seconds": elapsed,
        "assertions": assertions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("FROZEN TEXT ENCODER CPU SELF-CHECK")
    print(
        f"samples=4 shapes={{'short': {list(short_embedding.shape)}, "
        f"'padding_batch': {list(padding_batch.embeddings.shape)}, 'long': {list(long_result.embeddings.shape)}}}"
    )
    print(
        f"elapsed_seconds={elapsed:.3f} norms={{'short': {short_norms.tolist()}, "
        f"'padding_batch': {batch_norms.tolist()}, 'long': {long_norms.tolist()}}}"
    )
    print(
        f"seed={SEED} fold={FOLD} method={METHOD} "
        f"config_hash={DEFAULT_CONFIG.config_hash}"
    )
    print(f"resolved_revision={resolved_revision} assertions={len(assertions)} status={record['status']}")
    print(f"output={args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
