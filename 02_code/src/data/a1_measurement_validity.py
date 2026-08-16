"""Pure contracts for the SPEC v3.17 A1 measurement-validity audit."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import rankdata

from data.a1_admission import (
    DEFAULT_ADMISSION_CONFIG,
    cluster_bootstrap,
    stable_seed,
)
from data.a1_failure_diagnosis import scorer_threshold_pass


ALGORITHM_VERSION = "a1-measurement-validity-v317-d49-d50-v1"
RUN_ID = "2026-08-16_032_v317_a1_measurement_validity"
TASKS = ("task1_nr", "task2_tsr")
ALPHAS = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)
NEW_FOLDS = ("inner_s1_t0", "inner_s2_t0")
INJECTION_FOLDS = ("inner_s0_t0", "inner_s1_t0", "inner_s2_t0")
ARMS = (
    "real",
    "trial_shuffle",
    "within_trial_unit_assignment_shuffle",
    "channel_block_permutation",
)
METRICS = (
    "u_oof",
    "u_min",
    "real_minus_trial_shuffle",
    "real_minus_within_trial_unit_assignment_shuffle",
    "real_minus_channel_block_permutation",
    "max_selection_gap",
)
EXPECTED_AMENDMENT_FITS = 8
EXPECTED_INJECTION_FITS = 192
EXPECTED_TOTAL_FITS = 200

SUBJECT_FOLDS = {
    "task1_nr": {
        "inner_s0_t0": ("YDG", "YRH", "YRP", "YSD", "YSL"),
        "inner_s1_t0": ("YFR", "YFS", "YHS", "YLS", "YTL"),
        "inner_s2_t0": ("YAC", "YAK", "YIS", "YMD", "YMS"),
    },
    "task2_tsr": {
        "inner_s0_t0": ("YFS", "YHS", "YLS", "YRH", "YTL"),
        "inner_s1_t0": ("YAC", "YIS", "YRK", "YSD", "YSL"),
        "inner_s2_t0": ("YAG", "YAK", "YFR", "YMD", "YMS"),
    },
}

IMMUTABLE_HASHES = {
    "artifacts/a1_admission_contract.yaml": "c9c5a94b8227b6e43ecfc6d61b9b10b33f9340f7c845ca7dbaa0e0a3e65d9f4b",
    "04_results/audits/a1_admission.json": "b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e",
    "04_results/audits/a1_admission.md": "e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e",
    "04_results/audits/a1_admission_run_ledger.jsonl.gz": "fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd",
    "02_code/src/data/a1_admission.py": "14e45bc194cdfcbb03ef01a3862dfb331b916a7e425e7a74a8adffecb5ab96b4",
    "02_code/scripts/run_a1_admission.py": "a671a65dd4fb533cb92b820d9e723e3963c99168c96a3cf77bf9bfcd8f9fb099",
    "02_code/tests/test_a1_admission.py": "3866756f6d4b56f1f33ea81b6eccaed5ffc3fe385a319795a8e425afd75aa238",
    "artifacts/a1_failure_diagnosis_contract.yaml": "1796f58bd7786a682f65f944e29b975b87289fab2e944730bfe9b25ad99d9b1b",
    "04_results/audits/a1_failure_diagnosis.json": "56b3e6e42d8611072ecc62f10de60badf57bfc752954ba63ebe2941af6a9a38e",
    "04_results/audits/a1_failure_diagnosis.md": "a3e1b735a5cfca01a320cdae5d8c92b7cc8c1f54d4af8e6be8b6b1e11e6797f6",
    "04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz": "80cb11bc7ab12b59c00eb38c6cd03318f1ac2f347505e6940d8aeab5b434e6c4",
    "02_code/src/data/a1_failure_diagnosis.py": "b9e85d500f4968711c3282b2207a1eb1c2cbe226c793c6deb2f821e01a2828f3",
    "02_code/scripts/run_a1_failure_diagnosis.py": "13fa54fa422b7ab2a7cebb469678d5aaaecd07d2e3202790c0a07c493be92f1d",
    "02_code/tests/test_a1_failure_diagnosis.py": "4499d7ae057d4080619349816c3f31c14292f25b73999e2b6b07dcefe59df0bf",
    "runs/2026-08-16_029_v315_a1_failure_diagnosis.md": "ee8b4b2acf8a77f641429975c2e113bb67c4611995c1878aecd2c0529cace234",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def verify_immutable_evidence(root: Path) -> dict[str, Any]:
    observed = {relative: sha256_file(root / relative) for relative in IMMUTABLE_HASHES}
    if observed != IMMUTABLE_HASHES:
        changed = {
            key: {"expected": IMMUTABLE_HASHES[key], "observed": observed[key]}
            for key in IMMUTABLE_HASHES
            if observed[key] != IMMUTABLE_HASHES[key]
        }
        raise RuntimeError(f"STATE_SPEC_CONFLICT: immutable evidence changed: {changed}")
    admission = _read_gzip_jsonl(
        root / "04_results/audits/a1_admission_run_ledger.jsonl.gz"
    )
    diagnosis = _read_gzip_jsonl(
        root / "04_results/audits/a1_failure_diagnosis_run_ledger.jsonl.gz"
    )
    for name, rows, expected in (
        ("admission", admission, 639),
        ("diagnosis", diagnosis, 58),
    ):
        fit_ids = [str(row.get("fit_id")) for row in rows]
        if len(rows) != expected or len(set(fit_ids)) != expected:
            raise RuntimeError(
                f"STATE_SPEC_CONFLICT: {name} ledger is not {expected} unique fits"
            )
        if any(row.get("outer_test_record_ids_read") != [] for row in rows):
            raise RuntimeError(f"STATE_SPEC_CONFLICT: {name} outer-test read")
        if any(row.get("calibration_record_ids") != [] for row in rows):
            raise RuntimeError(f"STATE_SPEC_CONFLICT: {name} calibration read")
    return {
        "hashes": observed,
        "admission": {
            "rows": 639,
            "unique_fit_ids": 639,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        },
        "diagnosis": {
            "rows": 58,
            "unique_fit_ids": 58,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        },
        "admission_ledgers": admission,
        "diagnosis_ledgers": diagnosis,
    }


def projection_matrix() -> tuple[np.ndarray, dict[str, Any]]:
    seed = stable_seed(20260813, "v3.17", "graded_semantic_injection")
    matrix = (
        np.random.default_rng(seed)
        .standard_normal((840, 384))
        .astype("<f4")
    )
    if matrix.shape != (840, 384) or matrix.dtype != np.dtype("<f4"):
        raise AssertionError("projection matrix violated frozen shape/dtype")
    payload = np.ascontiguousarray(matrix).tobytes(order="C")
    return matrix, {
        "generator": "numpy.random.default_rng(seed_W).standard_normal((840,384)).astype('<f4')",
        "seed_rule": "stable_seed(20260813,'v3.17','graded_semantic_injection')",
        "seed_W": seed,
        "shape": [840, 384],
        "dtype": "float32-little-endian",
        "order": "C",
        "c_order_sha256": hashlib.sha256(payload).hexdigest(),
    }


def semantic_code(matrix: np.ndarray, item_embedding: np.ndarray) -> np.ndarray:
    projection = np.asarray(matrix, dtype="<f4")
    embedding = np.asarray(item_embedding, dtype="<f4")
    if projection.shape != (840, 384) or embedding.shape != (384,):
        raise ValueError("semantic injection requires W[840,384] and z[384]")
    if not np.isfinite(projection).all() or not np.isfinite(embedding).all():
        raise ValueError("semantic injection inputs must be finite")
    raw = projection @ embedding
    denominator = max(float(np.linalg.norm(raw)), 1e-12)
    code = (np.float32(math.sqrt(840.0) / denominator) * raw).astype(
        "<f4", copy=False
    )
    if code.shape != (840,) or not np.isfinite(code).all():
        raise ValueError("semantic injection code is invalid")
    return code


def inject_after_normalizer(
    normalized: np.ndarray,
    rows: Sequence[Mapping[str, Any]],
    *,
    alpha: float,
    matrix: np.ndarray,
    item_vectors: Mapping[str, np.ndarray],
) -> np.ndarray:
    values = np.asarray(normalized, dtype="<f4")
    if values.shape != (len(rows), 840) or not np.isfinite(values).all():
        raise ValueError("normalized injection input must be finite [N,840]")
    if alpha not in ALPHAS:
        raise ValueError("alpha is outside the frozen grid")
    codes_by_surface: dict[str, np.ndarray] = {}
    codes: list[np.ndarray] = []
    for row in rows:
        surface = str(row["surface"])
        if surface not in item_vectors:
            raise ValueError(f"missing frozen item embedding for {surface!r}")
        codes_by_surface.setdefault(
            surface, semantic_code(matrix, item_vectors[surface])
        )
        codes.append(codes_by_surface[surface])
    code_matrix = np.stack(codes).astype("<f4") if codes else np.empty((0, 840), "<f4")
    result = (values + np.float32(alpha) * code_matrix).astype("<f4", copy=False)
    if alpha == 0.0 and result.tobytes(order="C") != values.tobytes(order="C"):
        raise AssertionError("alpha=0 is not canonical-byte identical")
    if not np.isfinite(result).all():
        raise ValueError("semantic injection produced nonfinite values")
    return result


def summarize_amendment_fold(
    *,
    task: str,
    fold: str,
    h_logp: Sequence[float],
    oracle_logp: Sequence[float],
    oracle_top1: Sequence[int],
    true_positions: Sequence[int],
    subject_ids: Sequence[str],
    row_contract: Mapping[str, bool],
) -> dict[str, Any]:
    if task not in TASKS or fold not in NEW_FOLDS:
        raise ValueError("D49 permits only the two missing t0 subject folds")
    h_values = np.asarray(h_logp, dtype=np.float64)
    oracle_values = np.asarray(oracle_logp, dtype=np.float64)
    top1 = np.asarray(oracle_top1, dtype=np.int64)
    truth = np.asarray(true_positions, dtype=np.int64)
    subjects = np.asarray(subject_ids)
    if not (
        h_values.shape == oracle_values.shape == top1.shape == truth.shape == subjects.shape
        and h_values.size > 0
    ):
        raise ValueError("D49 scorer rows differ")
    if not np.isfinite(h_values).all() or not np.isfinite(oracle_values).all():
        raise ValueError("D49 scorer values are nonfinite")
    expected = set(SUBJECT_FOLDS[task][fold])
    observed = set(map(str, subjects.tolist()))
    if observed != expected:
        raise ValueError(f"{task}/{fold}: frozen subject coverage mismatch")
    if not all(bool(value) for value in row_contract.values()):
        raise ValueError(f"{task}/{fold}: row/vocabulary contract failed")
    differences = oracle_values - h_values
    return {
        "fold": fold,
        "subjects": sorted(expected),
        "scoring_rows": int(h_values.size),
        "subject_mean_logp_gains": {
            subject: float(differences[subjects == subject].mean())
            for subject in sorted(expected)
        },
        "per_subject_oracle_r_at_1": {
            subject: float(
                np.mean(top1[subjects == subject] == truth[subjects == subject])
            )
            for subject in sorted(expected)
        },
        "row_vocabulary_contract": dict(row_contract),
    }


def combine_amendment_summaries(
    *,
    task: str,
    old_s0: Mapping[str, Any],
    new_folds: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected = SUBJECT_FOLDS[task]
    old_gains = dict(old_s0["paired_oracle_minus_h_logp"]["subject_values"])
    old_r1 = dict(old_s0["per_subject_r_at_1"])
    if set(old_gains) != set(expected["inner_s0_t0"]) or set(old_r1) != set(old_gains):
        raise ValueError(f"{task}: immutable s0 summary coverage mismatch")
    by_fold = {str(row["fold"]): row for row in new_folds}
    if set(by_fold) != set(NEW_FOLDS):
        raise ValueError(f"{task}: D49 needs exactly s1_t0 and s2_t0")
    gains = {str(key): float(value) for key, value in old_gains.items()}
    r1 = {str(key): float(value) for key, value in old_r1.items()}
    coverage = {"inner_s0_t0": sorted(gains)}
    for fold in NEW_FOLDS:
        row = by_fold[fold]
        subjects = set(map(str, row["subjects"]))
        if subjects != set(expected[fold]) or set(gains).intersection(subjects):
            raise ValueError(f"{task}/{fold}: subject coverage is not disjoint/frozen")
        fold_gains = dict(row["subject_mean_logp_gains"])
        fold_r1 = dict(row["per_subject_oracle_r_at_1"])
        if set(fold_gains) != subjects or set(fold_r1) != subjects:
            raise ValueError(f"{task}/{fold}: incomplete subject summaries")
        gains.update({str(key): float(value) for key, value in fold_gains.items()})
        r1.update({str(key): float(value) for key, value in fold_r1.items()})
        coverage[fold] = sorted(subjects)
    union = set().union(*(set(values) for values in expected.values()))
    pairwise_disjoint = sum(len(values) for values in expected.values()) == len(union)
    if not pairwise_disjoint or set(gains) != union or set(r1) != union or len(union) != 15:
        raise ValueError(f"{task}: D49 does not cover exactly 15 disjoint subjects")
    bootstrap = cluster_bootstrap(
        gains,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(20260813, "D42", "A-A1-scorer", task),
    )
    macro_r1 = float(np.mean([r1[subject] for subject in sorted(r1)]))
    passed = scorer_threshold_pass(
        ci_low=float(bootstrap["ci95"][0]), macro_subject_r1=macro_r1
    )
    return {
        "subject_fold_coverage": coverage,
        "pairwise_disjoint": pairwise_disjoint,
        "subject_ids": sorted(union),
        "subject_count": 15,
        "equal_subject_weighting": True,
        "paired_oracle_minus_h_logp": bootstrap,
        "oracle_full_vocabulary_macro_subject_r_at_1": macro_r1,
        "per_subject_oracle_r_at_1": dict(sorted(r1.items())),
        "pass": bool(passed),
    }


def summarize_injection_rows(
    rows: Sequence[Mapping[str, Any]], *, task: str, alpha: float
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if str(row["task"]) == task and float(row["alpha"]) == float(alpha)
    ]
    if not selected:
        raise ValueError(f"no injection rows for {task}/alpha={alpha}")
    by_subject: defaultdict[str, defaultdict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    subject_folds: defaultdict[str, set[str]] = defaultdict(set)
    for row in selected:
        subject = str(row["subject_id"])
        subject_folds[subject].add(str(row["fold"]))
        for metric in METRICS:
            value = float(row[metric])
            if not np.isfinite(value):
                raise ValueError("injection metric is nonfinite")
            by_subject[subject][metric].append(value)
    expected = set().union(*(set(values) for values in SUBJECT_FOLDS[task].values()))
    if set(by_subject) != expected or len(expected) != 15:
        raise ValueError(f"{task}/alpha={alpha}: subject set is not frozen 15")
    if any(len(folds) != 1 for folds in subject_folds.values()):
        raise ValueError(f"{task}/alpha={alpha}: subject crosses injection cells")
    summaries: dict[str, Any] = {}
    for metric in METRICS:
        subject_values = {
            subject: float(np.mean(by_subject[subject][metric]))
            for subject in sorted(by_subject)
        }
        summaries[metric] = cluster_bootstrap(
            subject_values,
            n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
            seed=stable_seed(20260813, "v3.17", task, alpha, metric),
        )
    family = (
        summaries["u_oof"]["ci95"][0] > 0.0
        and summaries["u_oof"]["positive_subject_count"] >= 12
        and summaries["real_minus_trial_shuffle"]["estimate"] > 0.0
        and summaries["real_minus_within_trial_unit_assignment_shuffle"]["estimate"]
        > 0.0
        and summaries["real_minus_channel_block_permutation"]["estimate"] > 0.0
    )
    legacy = (
        family
        and summaries["u_min"]["ci95"][0] > 0.0
        and summaries["u_min"]["positive_subject_count"] >= 12
    )
    return {
        "alpha": float(alpha),
        "subject_ids": sorted(expected),
        "subject_count": 15,
        "equal_subject_weighting": True,
        "observation_count": len(selected),
        "metrics": summaries,
        "family_mean_detected": bool(family),
        "legacy_full_detected": bool(legacy),
        "legacy_label": "legacy_pointwise_max_sensitivity",
    }


def spearman_rho(alpha_values: Sequence[float], estimates: Sequence[float]) -> float:
    alpha_array = np.asarray(alpha_values, dtype=np.float64)
    estimate_array = np.asarray(estimates, dtype=np.float64)
    if alpha_array.shape != estimate_array.shape or alpha_array.size != 8:
        raise ValueError("Spearman curve requires the eight frozen alpha points")
    if not np.isfinite(alpha_array).all() or not np.isfinite(estimate_array).all():
        raise ValueError("Spearman inputs must be finite")
    ranked_alpha = rankdata(alpha_array, method="average")
    ranked_estimate = rankdata(estimate_array, method="average")
    rho = float(np.corrcoef(ranked_alpha, ranked_estimate)[0, 1])
    if not np.isfinite(rho):
        raise ValueError("Spearman rho is undefined")
    return rho


def summarize_curve(alpha_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_alpha = {float(row["alpha"]): row for row in alpha_results}
    if tuple(sorted(by_alpha)) != tuple(sorted(ALPHAS)):
        raise ValueError("curve does not contain the complete frozen alpha grid")
    ordered = [by_alpha[alpha] for alpha in ALPHAS]
    family_floor = next(
        (float(row["alpha"]) for row in ordered if row["family_mean_detected"]),
        None,
    )
    legacy_floor = next(
        (float(row["alpha"]) for row in ordered if row["legacy_full_detected"]),
        None,
    )
    rho = spearman_rho(
        ALPHAS, [row["metrics"]["u_oof"]["estimate"] for row in ordered]
    )
    alpha10 = by_alpha[10.0]
    path_pass = bool(alpha10["family_mean_detected"] and rho >= 0.90)
    diagnostic = (
        "LEGACY_U_MIN_NOT_CONSTRUCT_VALID_ON_FROZEN_GRID"
        if path_pass and legacy_floor is None
        else None
    )
    return {
        "alpha_results": ordered,
        "alpha_family_floor": family_floor,
        "alpha_legacy_floor": legacy_floor,
        "spearman_rho_alpha_vs_u_oof": rho,
        "alpha_10_family_mean_detected": bool(alpha10["family_mean_detected"]),
        "alpha_10_legacy_full_detected": bool(alpha10["legacy_full_detected"]),
        "diagnostic": diagnostic,
        "pass": path_pass,
    }
