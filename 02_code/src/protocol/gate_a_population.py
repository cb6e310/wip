"""v3.5 E-5 subject-first Gate-A population aggregation.

The population unit is a subject, never a repeated subject/cell pair.  Each
subject is first averaged across eligible outer cells, then the resulting
subject table is the only input to a cluster bootstrap.  Missing subject-cell
observations are omitted, never zero-filled.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from typing import Any, Iterable, Mapping


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def aggregate_subject_first(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate cell-level metrics to one row per subject.

    Each row must contain ``subject_id``, ``outer_cell``, ``eligible`` and
    finite numeric ``mean_u`` and ``pi_g``.  A subject with no eligible row is
    excluded and explicitly reported.
    """

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded: list[dict[str, Any]] = []
    for raw in rows:
        subject = str(raw.get("subject_id", "")).strip()
        cell = str(raw.get("outer_cell", "")).strip()
        eligible = bool(raw.get("eligible", True))
        if not subject or not cell:
            excluded.append({"row": dict(raw), "reason": "MISSING_SUBJECT_OR_CELL"})
            continue
        if not eligible:
            excluded.append({"subject_id": subject, "outer_cell": cell, "reason": str(raw.get("exclusion_reason", "INELIGIBLE_CELL"))})
            continue
        try:
            mean_u = float(raw["mean_u"])
            pi_g = float(raw["pi_g"])
        except (KeyError, TypeError, ValueError):
            excluded.append({"subject_id": subject, "outer_cell": cell, "reason": "INVALID_METRIC"})
            continue
        if not (mean_u == mean_u and pi_g == pi_g):
            excluded.append({"subject_id": subject, "outer_cell": cell, "reason": "NONFINITE_METRIC"})
            continue
        grouped[subject].append({"outer_cell": cell, "mean_u": mean_u, "pi_g": pi_g})

    subjects: list[dict[str, Any]] = []
    for subject in sorted(grouped):
        cells = sorted(grouped[subject], key=lambda row: row["outer_cell"])
        subjects.append(
            {
                "subject_id": subject,
                "eligible_outer_cells": [row["outer_cell"] for row in cells],
                "n_eligible_cells": len(cells),
                "mean_u": sum(row["mean_u"] for row in cells) / len(cells),
                "pi_g": sum(row["pi_g"] for row in cells) / len(cells),
            }
        )

    artifact: dict[str, Any] = {
        "schema_version": 1,
        "contract": "EEG_Text_Bprime_Unified_Paper_Spec_v3_5__7.2.1_E5",
        "aggregation": "equal_mean_within_subject_across_eligible_outer_cells_then_subject_cluster",
        "zero_fill_missing_cells": False,
        "subjects": subjects,
        "excluded_rows": excluded,
        "n_subject_clusters": len(subjects),
    }
    artifact["canonical_sha256"] = hashlib.sha256(_canonical({k: v for k, v in artifact.items() if k != "canonical_sha256"})).hexdigest()
    return artifact


def validate_population(artifact: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    subjects = artifact.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        errors.append("subject population is empty")
        return errors
    ids = [str(row.get("subject_id", "")) for row in subjects]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        errors.append("subject IDs must be unique and non-empty")
    if any(int(row.get("n_eligible_cells", 0)) < 1 for row in subjects):
        errors.append("subjects with no eligible cells must be excluded, not zero-filled")
    payload = {k: v for k, v in artifact.items() if k != "canonical_sha256"}
    expected = hashlib.sha256(_canonical(payload)).hexdigest()
    if artifact.get("canonical_sha256") != expected:
        errors.append("canonical_sha256 mismatch")
    return errors


def subject_cluster_bootstrap(
    artifact: Mapping[str, Any],
    *,
    metric: str,
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    """Bootstrap one already subject-aggregated metric.

    The function deliberately accepts only the output of
    :func:`aggregate_subject_first`.  Consequently, a repeated outer-cell row
    can never be mistaken for an independent bootstrap cluster.  The caller
    must provide both the seed and resample count; this engineering helper does
    not freeze a paper-level bootstrap budget.
    """

    errors = validate_population(artifact)
    if errors:
        raise ValueError("invalid subject-first artifact: " + "; ".join(errors))
    if metric not in {"mean_u", "pi_g"}:
        raise ValueError("metric must be 'mean_u' or 'pi_g'")
    if isinstance(n_resamples, bool) or int(n_resamples) != n_resamples or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if isinstance(seed, bool) or int(seed) != seed:
        raise ValueError("seed must be an integer")

    subjects = list(artifact["subjects"])
    subject_ids = [str(row["subject_id"]) for row in subjects]
    values = [float(row[metric]) for row in subjects]
    n_subjects = len(subjects)
    rng = random.Random(int(seed))

    draws: list[dict[str, Any]] = []
    for resample_index in range(int(n_resamples)):
        indices = [rng.randrange(n_subjects) for _ in range(n_subjects)]
        draws.append(
            {
                "resample_index": resample_index,
                "subject_ids": [subject_ids[index] for index in indices],
                "estimate": sum(values[index] for index in indices) / n_subjects,
            }
        )

    result: dict[str, Any] = {
        "schema_version": 1,
        "method": "subject_cluster_bootstrap_after_subject_first_aggregation",
        "metric": metric,
        "seed": int(seed),
        "n_resamples": int(n_resamples),
        "n_subject_clusters": n_subjects,
        "source_population_sha256": artifact["canonical_sha256"],
        "draws": draws,
    }
    result["canonical_sha256"] = hashlib.sha256(
        _canonical({key: value for key, value in result.items() if key != "canonical_sha256"})
    ).hexdigest()
    return result


def synthetic_rows() -> list[dict[str, Any]]:
    return [
        {"subject_id": "S1", "outer_cell": "0-0", "mean_u": 1.0, "pi_g": 0.2},
        {"subject_id": "S1", "outer_cell": "0-1", "mean_u": 3.0, "pi_g": 0.4},
        {"subject_id": "S2", "outer_cell": "0-0", "mean_u": -1.0, "pi_g": 0.0},
        {"subject_id": "S2", "outer_cell": "0-1", "mean_u": 1.0, "pi_g": 0.2},
        {"subject_id": "S3", "outer_cell": "0-0", "eligible": False, "exclusion_reason": "NO_VALID_ITEM"},
    ]
