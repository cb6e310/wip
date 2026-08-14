#!/usr/bin/env python3
"""Run the reproducible, non-paper v3.6 A3 preparation audit.

The audit validates source-channel inventory, checkpoint bytes, constructor
compatibility, and a synthetic no-gradient shape smoke.  It does not claim a
semantic EGI-to-LaBraM map or real MAT extraction admission.  CO-N7 and local
checkpoint-use policy are scientific/provenance decisions recorded by v3.6,
not conclusions inferred from this engineering smoke.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


# This digest was independently computed from the pinned official download.
EXPECTED_CHECKPOINT_SHA256 = "7c50583826afac76c4ab18f43d958df40496c8229accc09ed6a227c9bb57c37c"
EXPECTED_CHECKPOINT_BYTES = 96_612_769
EXPECTED_RAW_LABELS = tuple(f"E{i}" for i in range(1, 129))
REQUIRED_RUNTIME_MODULES = {
    "torch": "torch",
    "numpy": "numpy",
    "scipy": "scipy",
    "einops": "einops",
    "timm": "timm",
}
VENDOR_OPTIONAL_MODULES = {
    "tensorboardX": "tensorboardX",
    "pyhealth": "pyhealth",
    "deepspeed": "deepspeed",
    "braindecode": "braindecode",
}


def _label(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _mat_labels(path: Path) -> tuple[str, ...]:
    from scipy.io import loadmat

    mat = loadmat(path, squeeze_me=True, struct_as_record=False)
    eeg = mat["EEG"]
    chanlocs = np.asarray(eeg.chanlocs, dtype=object).reshape(-1)
    labels = []
    for loc in chanlocs:
        labels.append(_label(getattr(loc, "labels", loc)))
    return tuple(labels)


def inspect_raw_inventory(dataset_root: Path) -> dict[str, Any]:
    files = sorted(dataset_root.glob("task* - */Raw data/*/*_EEG.mat"))
    if not files:
        raise FileNotFoundError(f"no continuous raw EEG files under {dataset_root}")
    sequences: list[tuple[str, ...]] = []
    records: list[dict[str, Any]] = []
    for path in files:
        labels = _mat_labels(path)
        sequences.append(labels)
        records.append({"file": str(path.relative_to(dataset_root)), "n_channels": len(labels), "labels": list(labels)})
    sequence_hash = hashlib.sha256("|".join(sequences[0]).encode("ascii")).hexdigest()
    return {
        "file_count": len(files),
        "all_128_channels": all(len(labels) == 128 for labels in sequences),
        "all_same_order": all(labels == sequences[0] for labels in sequences),
        "label_sequence": list(sequences[0]),
        "label_sequence_sha256": sequence_hash,
        "expected_e1_to_e128": sequences[0] == EXPECTED_RAW_LABELS,
        "records": records,
    }


def inspect_checkpoint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": actual,
        "expected_bytes": EXPECTED_CHECKPOINT_BYTES,
        "expected_sha256": EXPECTED_CHECKPOINT_SHA256,
        "identity_pass": path.stat().st_size == EXPECTED_CHECKPOINT_BYTES and actual == EXPECTED_CHECKPOINT_SHA256,
        "pinned_url": "https://raw.githubusercontent.com/935963004/LaBraM/d52cb6d1801bb038e10ea1b6b3292c0bd569a9d5/checkpoints/labram-base.pth",
        "source_commit": "c431221e6cfd23dbfa9950e0180682fb322b0548",
        "checkpoint_file_commit": "d52cb6d1801bb038e10ea1b6b3292c0bd569a9d5",
        "rights_status": "v3.6 local-research-inference working assumption; disclose provenance and do not redistribute checkpoint",
    }


def inspect_runtime() -> dict[str, Any]:
    from importlib import import_module
    from importlib.util import find_spec

    def version(name: str) -> str | None:
        try:
            module = import_module(name)
            return str(getattr(module, "__version__", "present"))
        except Exception:
            return None

    required = {name: version(module) if find_spec(module) else None for name, module in REQUIRED_RUNTIME_MODULES.items()}
    optional = {name: version(module) if find_spec(module) else None for name, module in VENDOR_OPTIONAL_MODULES.items()}
    return {
        "required": required,
        "required_pass": all(value is not None for value in required.values()),
        "vendor_optional": optional,
        "wrapper_does_not_import_optional_vendor_utils": True,
    }


def run_smoke(project_root: Path, seed: int, config) -> dict[str, Any]:
    np.random.seed(seed)
    random.seed(seed)
    import torch
    torch.manual_seed(seed)

    sys.path.insert(0, str(project_root / "02_code" / "src"))
    from backbones.a3_labram import A3Config, load_labram_base, preprocess_raw_signal, window_signal

    config = A3Config(filter_order=4, notch_q=30.0)
    checkpoint = project_root / "02_code" / "vendor" / "checkpoints" / "labram-base.pth"
    vendor = project_root / "02_code" / "vendor" / "LaBraM"
    model = load_labram_base(checkpoint, vendor, config)
    before = hashlib.sha256(
        b"".join(parameter.detach().cpu().numpy().tobytes() for parameter in model.parameters())
    ).hexdigest()
    raw = np.random.default_rng(seed).standard_normal((128, 4000), dtype=np.float32)
    preprocessed = preprocess_raw_signal(raw, config)
    windows = window_signal(preprocessed, config)
    ordered = torch.as_tensor(windows, dtype=torch.float32).reshape(-1, 128, 5, 200)
    with torch.no_grad():
        pooled = model(ordered, input_chans=list(range(129)), return_patch_tokens=False)
    after = hashlib.sha256(
        b"".join(parameter.detach().cpu().numpy().tobytes() for parameter in model.parameters())
    ).hexdigest()
    return {
        "input_windows_shape": list(windows.shape),
        "raw_source_shape": list(raw.shape),
        "preprocessed_shape": list(preprocessed.shape),
        "preprocessed_min": float(preprocessed.min()),
        "preprocessed_max": float(preprocessed.max()),
        "preprocessed_finite": bool(np.isfinite(preprocessed).all()),
        "pooled_shape": list(pooled.shape),
        "pooled_min": float(pooled.min().item()),
        "pooled_max": float(pooled.max().item()),
        "pooled_finite": bool(torch.isfinite(pooled).all().item()),
        "requires_grad": any(parameter.requires_grad for parameter in model.parameters()),
        "weights_unchanged": before == after,
        "weights_hash_before": before,
        "weights_hash_after": after,
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "pooling": "official release path: fc_norm(mean(non_cls_patch_tokens))",
        "preprocessing_status": "engineering_candidate_only; filter_order=4 and notch_q=30 are not guide-frozen",
        "note": "synthetic identity channel positions only; not a semantic EGI mapping",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--fold", default="A3-contract-1")
    args = parser.parse_args()
    started = time.perf_counter()
    project_root = args.project_root.resolve()
    dataset_root = (args.dataset_root or project_root / "01_data_protocol" / "datasets" / "zuco_2.0").resolve()
    checkpoint = (args.checkpoint or project_root / "02_code" / "vendor" / "checkpoints" / "labram-base.pth").resolve()
    sys.path.insert(0, str(project_root / "02_code" / "src"))
    from backbones.a3_labram import A3Config, config_hash

    audit_config = A3Config(filter_order=4, notch_q=30.0)
    cfg_hash = config_hash(audit_config)
    method_slug = "A3-LaBraM-Base-preparation"
    default_name = f"a3_labram_preparation_seed{args.seed}_fold{args.fold}_method{method_slug}_cfg{cfg_hash[:12]}.json"
    output = (args.output or project_root / "03_runs" / "debug_runs" / default_name).resolve()

    inventory = inspect_raw_inventory(dataset_root)
    checkpoint_info = inspect_checkpoint(checkpoint)
    runtime = inspect_runtime()
    smoke = run_smoke(project_root, args.seed, audit_config)
    assertions = {
        "raw_file_count_nonzero": inventory["file_count"] > 0,
        "raw_all_128": inventory["all_128_channels"],
        "raw_order_stable": inventory["all_same_order"],
        "raw_labels_e1_to_e128": inventory["expected_e1_to_e128"],
        "checkpoint_identity": checkpoint_info["identity_pass"],
        "runtime_required": runtime["required_pass"],
        "preprocessing_shape": smoke["preprocessed_shape"] == [128, 1600],
        "preprocessing_finite": smoke["preprocessed_finite"],
        "smoke_pooled_200": smoke["pooled_shape"][1:] == [200],
        "smoke_finite": smoke["pooled_finite"],
        "smoke_no_grad": not smoke["requires_grad"],
        "smoke_weights_unchanged": smoke["weights_unchanged"],
    }
    status = "PASS_WITH_BLOCKERS" if all(assertions.values()) else "FAIL"
    result = {
        "status": status,
        "run_id": "2026-08-14_010_v36_stage0_recovery",
        "spec_version": "v3.6",
        "scope": "engineering preparation only; no paper evidence and no real extraction admission",
        "seed": args.seed,
        "fold": args.fold,
        "method": method_slug,
        "config_hash": cfg_hash,
        "raw_inventory": inventory,
        "checkpoint": checkpoint_info,
        "runtime": runtime,
        "smoke": smoke,
        "assertions": assertions,
        "scientific_decisions_not_inferred_from_smoke": {
            "co_n7": "CLEARED_BY_V3_6_APPENDIX_D_AUDIT",
            "checkpoint_local_use": "WORKING_ASSUMPTION_DISCLOSE_AND_DO_NOT_REDISTRIBUTE",
        },
        "unresolved_blockers": [
            "EGI128-to-LaBraM semantic channel map is not frozen",
            "ZuCo continuous-MAT raw signal unit is not verified",
            "filter order and notch Q are engineering candidates, not guide-frozen values",
            "real EEG preprocessing and mapped extraction are not validated",
        ],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("A3 PREPARATION SELF-CHECK")
    print(f"samples={inventory['file_count']} raw_shape=[128,T] windows={smoke['input_windows_shape']}")
    print(f"preprocessed={smoke['preprocessed_shape']} pooled={smoke['pooled_shape']} range=[{smoke['pooled_min']:.6g},{smoke['pooled_max']:.6g}]")
    print(
        f"seed={args.seed} fold={args.fold} method={method_slug} "
        f"config_hash={cfg_hash} elapsed_s={result['elapsed_seconds']} status={status}"
    )
    for name, passed in assertions.items():
        print(f"ASSERT {name}={'PASS' if passed else 'FAIL'}")
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
