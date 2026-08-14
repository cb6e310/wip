#!/usr/bin/env python3
"""Run the deterministic A1 contract self-check on synthetic EEG only.

This is an engineering validation, not a ZuCo result and not an admission
probe.  It prints a compact sample/shape/range/PASS summary and can write a
JSON record whose name and fields include seed, fold, method, and config hash.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from backbones.a1_spectral import (  # noqa: E402
    A1AlignmentEncoder,
    DEFAULT_CONFIG,
    RobustFeatureNormalizer,
    config_hash,
    extract_fixed_window_sequence,
    extract_word_level_sequence,
    pad_feature_sequences,
    run_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--fold", default="S0-TEXT")
    parser.add_argument("--method", default="A1")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    rng = np.random.default_rng(args.seed)
    epochs = [rng.normal(size=(DEFAULT_CONFIG.n_channels, 512)).astype(np.float32) for _ in range(4)]
    word_sequence = extract_word_level_sequence(epochs)
    fixed_sequence = extract_fixed_window_sequence(np.concatenate(epochs, axis=1))
    normalizer = RobustFeatureNormalizer().fit([word_sequence])
    normalized = normalizer.transform_many([word_sequence, fixed_sequence])
    padded, mask = pad_feature_sequences(normalized)
    encoder = A1AlignmentEncoder(seed=args.seed)
    output = encoder(padded, mask)
    metadata = run_metadata(seed=args.seed, fold=args.fold, method=args.method)
    elapsed = time.perf_counter() - started
    assertions = {
        "word_feature_dim": word_sequence.shape[1] == DEFAULT_CONFIG.feature_dim,
        "fixed_feature_dim": fixed_sequence.shape[1] == DEFAULT_CONFIG.feature_dim,
        "mask_bool": str(mask.dtype) == "torch.bool",
        "output_shape": tuple(output.shape) == (2, DEFAULT_CONFIG.d_align),
        "finite": bool(np.isfinite(word_sequence).all() and np.isfinite(fixed_sequence).all()),
        "parameter_limit": encoder.parameter_count <= DEFAULT_CONFIG.max_encoder_params,
    }
    passed = all(assertions.values())
    record = {
        **metadata,
        "status": "PASS" if passed else "FAIL",
        "samples": {"word_sequences": 1, "fixed_sequences": 1, "synthetic_epochs": len(epochs)},
        "shapes": {
            "word_sequence": list(word_sequence.shape),
            "fixed_sequence": list(fixed_sequence.shape),
            "padded": list(padded.shape),
            "mask": list(mask.shape),
            "output": list(output.shape),
        },
        "ranges": {
            "word_min": float(word_sequence.min()),
            "word_max": float(word_sequence.max()),
            "normalized_abs_max": float(max(np.max(np.abs(item)) for item in normalized)),
            "output_abs_max": float(output.detach().abs().max().item()),
        },
        "parameter_count": encoder.parameter_count,
        "elapsed_seconds": elapsed,
        "assertions": assertions,
        "config_hash": config_hash(),
    }
    print("A1 CONTRACT SELF-CHECK")
    print(f"samples={record['samples']} shapes={record['shapes']}")
    print(f"elapsed_seconds={elapsed:.3f} ranges={record['ranges']}")
    print(f"seed={args.seed} fold={args.fold} method={args.method} config_hash={record['config_hash']}")
    print(f"assertions={assertions} status={record['status']}")
    output_path = args.output
    if output_path is None:
        output_path = (
            SCRIPT_ROOT.parent
            / "03_runs"
            / "debug_runs"
            / (
                f"a1_contract_selfcheck_seed{args.seed}_fold{args.fold}_"
                f"method{args.method}_cfg{record['config_hash'][:12]}.json"
            )
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"output={output_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
