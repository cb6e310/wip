#!/usr/bin/env python3
"""Synthetic ANMA-orig/H contract self-check.

This run has no ZuCo/TMNRED input and is not paper evidence.  It validates the
frozen formulas, parameter-recovery harness, H leakage assertions, finite
weights, and mandatory diagnostics while recording seed/fold/config hashes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from methods.anma_orig import (  # noqa: E402
    ANMAConfig,
    ANMAOrigModel,
    config_hash as anma_config_hash,
    diagnostics,
    fit_2pl_parameters,
    rank_stability,
    rankfit_plateau_step,
    run_metadata as anma_metadata,
)
from protocol.h_definition import (  # noqa: E402
    audit_h_context,
    build_h_empty,
    build_h_full,
    config_hash as h_config_hash,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--fold", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    q = torch.linspace(-3.0, 3.0, 512)
    true_a = torch.tensor([1.6, 0.8, 2.4])
    true_b = torch.tensor([-0.4, 0.2, 0.7])
    true_p = torch.sigmoid(true_a[None, :] * (q[:, None] - true_b[None, :]))
    y = torch.bernoulli(true_p)
    fitted_a, fitted_b, history = fit_2pl_parameters(q, y, steps=1200, seed=args.seed)
    fitted_p = torch.sigmoid(fitted_a[None, :] * (q[:, None] - fitted_b[None, :]))

    model = ANMAOrigModel(latent_dim=4, text_dim=5, seed=args.seed)
    latent = torch.randn(6, 4)
    text = torch.randn(3, 5)
    item_indices = torch.tensor([[0, 1], [1, 2], [0, 2], [0, 1], [1, 2], [0, 2]])
    item_mask = torch.ones_like(item_indices, dtype=torch.bool)
    y_batch = torch.tensor([[1, 0], [1, 1], [0, 1], [1, 0], [0, 1], [1, 1]], dtype=torch.float32)
    alignment = torch.linspace(0.1, 0.6, 6)
    result = model(latent, text, item_indices, item_mask, y_batch, alignment)
    report = diagnostics(
        result["y"] if "y" in result else y_batch,
        result["p"],
        result["information"],
        item_mask=item_mask,
        weights=result["weights"],
        sentence_length=torch.tensor([8, 11, 7, 15, 9, 13], dtype=torch.float32),
        item_frequency=torch.tensor([4, 9, 7, 3, 8, 5], dtype=torch.float32),
        surprisal=torch.tensor([2.1, 1.8, 2.5, 1.2, 2.0, 1.5], dtype=torch.float32),
    )
    stability = rank_stability((fitted_a, fitted_a + torch.tensor([0.01, -0.01, 0.0])))
    warmup_plateau = rankfit_plateau_step(((10, 0.40), (20, 0.403), (30, 0.406)))

    sentences = (("A", "context"), ("Another", "sentence"), ("Target", "word"))
    h_full = build_h_full(sentences, target_sentence_index=2, target_tokens=("Target", "word"), position_index=2)
    h_empty = build_h_empty(target_sentence_index=2, position_index=2)
    h_assertions = {
        "full": audit_h_context(h_full, target_tokens=("Target", "word"), future_sentence_indices=()),
        "empty": audit_h_context(h_empty),
    }
    assertions = {
        "parameter_loss_decreases": history[-1] < history[0],
        "parameter_rank_recovery": float(torch.corrcoef(torch.stack((fitted_a, true_a)))[0, 1]) > 0.9,
        "threshold_rank_recovery": float(torch.corrcoef(torch.stack((fitted_b, true_b)))[0, 1]) > 0.8,
        "model_finite": bool(torch.isfinite(result["total_loss"]).item()),
        "weights_detached": not result["weights"].requires_grad,
        "weights_mean_one": abs(float(result["weights"].mean()) - 1.0) < 1e-5,
        "h_full_checks": all(h_assertions["full"].values()),
        "h_empty_checks": all(h_assertions["empty"].values()),
        "diagnostics_finite": bool(np.isfinite(float(report["rho_band"]))),
        "partial_correlations_finite": all(
            np.isfinite(float(report[f"partial_spearman_weight_{name}"]))
            for name in ("sentence_length", "item_frequency", "surprisal")
        ),
        "rank_stability_finite": bool(np.isfinite(float(stability["pairwise_median"]))),
        "rankfit_plateau_rule": warmup_plateau == 30,
    }
    passed = all(assertions.values())
    metadata = anma_metadata(seed=args.seed, fold=args.fold, config=ANMAConfig())
    record = {
        **metadata,
        "status": "PASS" if passed else "FAIL",
        "scope": "synthetic engineering contract only; no paper evidence",
        "anma_config_hash": anma_config_hash(),
        "h_config_hash": h_config_hash(),
        "samples": {"parameter_recovery_observations": int(y.numel()), "model_sentences": int(latent.shape[0])},
        "shapes": {"q": list(q.shape), "y": list(y.shape), "model_p": list(result["p"].shape), "weights": list(result["weights"].shape)},
        "ranges": {"fitted_a": [float(fitted_a.min()), float(fitted_a.max())], "fitted_b": [float(fitted_b.min()), float(fitted_b.max())], "weights": [float(result["weights"].min()), float(result["weights"].max())]},
        "diagnostics": report,
        "parameter_rank_stability": stability,
        "rankfit_plateau_step": warmup_plateau,
        "h_assertions": h_assertions,
        "assertions": assertions,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    print("ANMA-ORIG / H SELF-CHECK")
    print(f"samples={record['samples']} shapes={record['shapes']}")
    print(f"elapsed_seconds={record['elapsed_seconds']:.3f} ranges={record['ranges']}")
    print(f"seed={args.seed} fold={args.fold} method={metadata['method']} config_hash={metadata['config_hash']}")
    print(f"assertions={assertions} status={record['status']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
        print(f"output={args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
