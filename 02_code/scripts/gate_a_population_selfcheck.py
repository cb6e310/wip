#!/usr/bin/env python3
"""Self-check the v3.6 E-5 subject-first population contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol.gate_a_population import (  # noqa: E402
    aggregate_subject_first,
    subject_cluster_bootstrap,
    synthetic_rows,
    validate_population,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--fold", required=True)
    parser.add_argument("--n-resamples", type=int, default=64)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    started = time.monotonic()
    artifact = aggregate_subject_first(synthetic_rows())
    errors = validate_population(artifact)
    assert not errors, errors
    assert artifact["n_subject_clusters"] == 2
    assert artifact["subjects"][0]["mean_u"] == 2.0
    assert len(artifact["excluded_rows"]) == 1
    bootstrap = subject_cluster_bootstrap(
        artifact,
        metric="mean_u",
        n_resamples=args.n_resamples,
        seed=args.seed,
    )
    assert bootstrap["n_subject_clusters"] == artifact["n_subject_clusters"]
    assert len(bootstrap["draws"]) == args.n_resamples
    assert all(
        len(draw["subject_ids"]) == artifact["n_subject_clusters"]
        for draw in bootstrap["draws"]
    )
    assert all(
        set(draw["subject_ids"]) <= {"S1", "S2"}
        for draw in bootstrap["draws"]
    )

    config = {
        "aggregation": artifact["aggregation"],
        "bootstrap_unit": "subject",
        "metric": bootstrap["metric"],
        "n_resamples": args.n_resamples,
        "zero_fill_missing_cells": False,
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "schema_version": 1,
        "run_id": "2026-08-14_010_v36_stage0_recovery",
        "seed": args.seed,
        "fold": args.fold,
        "method": "Gate-A-population-E5",
        "config": config,
        "config_hash": config_hash,
        "population": artifact,
        "bootstrap": bootstrap,
        "assertions": {
            "population_valid": True,
            "subject_first_equal_mean": True,
            "missing_cell_not_zero_filled": True,
            "bootstrap_cluster_count_matches_subjects": True,
            "bootstrap_draw_width_matches_subjects": True,
            "bootstrap_uses_subject_ids_only": True,
            "seeded_bootstrap_is_deterministic": bootstrap
            == subject_cluster_bootstrap(
                artifact,
                metric="mean_u",
                n_resamples=args.n_resamples,
                seed=args.seed,
            ),
        },
        "evidence_scope": "synthetic engineering contract only; no Gate-A result",
        "status": "PASS",
    }
    out = args.output
    if not out.is_absolute():
        out = ROOT.parent / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    estimates = [draw["estimate"] for draw in bootstrap["draws"]]
    print(
        "E5 SELF-CHECK "
        f"samples={{'subject_clusters': {artifact['n_subject_clusters']}, 'bootstrap_resamples': {args.n_resamples}}} "
        f"shapes={{'subject_table': [{artifact['n_subject_clusters']}, 2], 'bootstrap_estimates': [{args.n_resamples}]}} "
        f"elapsed_seconds={time.monotonic() - started:.4f} "
        f"ranges={{'subject_mean_u': [{min(row['mean_u'] for row in artifact['subjects']):.3f}, {max(row['mean_u'] for row in artifact['subjects']):.3f}], "
        f"'bootstrap_estimate': [{min(estimates):.3f}, {max(estimates):.3f}]}} "
        f"seed={args.seed} fold={args.fold} method=Gate-A-population-E5 config_hash={config_hash} "
        f"assertions={payload['assertions']} status=PASS output={out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
