"""Pure contracts for the SPEC v3.18 bounded A1-R recovery audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from data.a1_admission import (
    DEFAULT_ADMISSION_CONFIG,
    build_v5_ledger,
    cluster_bootstrap,
    stable_seed,
    validate_v5_or_raise,
)


ALGORITHM_VERSION = "a1-measurement-recovery-v318-d54-d59-v1"
RUN_ID = "2026-08-16_034_v318_a1_measurement_recovery"
TASKS = ("task1_nr", "task2_tsr")
FOLDS = ("inner_s0_t0", "inner_s1_t0", "inner_s2_t0")
FRONTENDS = ("A1_BP_CONCAT", "A1R_LOG_BP_CONCAT", "A1R_T8_FIXATION")
CANDIDATES = ("A1R_LOG_BP_CONCAT", "A1R_T8_FIXATION")
ARMS = (
    "real",
    "trial_shuffle",
    "within_trial_unit_assignment_shuffle",
    "channel_block_permutation",
)
REGIMES = ("seen", "cross")
METRICS = (
    "u_oof",
    "u_min",
    "real_minus_trial_shuffle",
    "real_minus_within_trial_unit_assignment_shuffle",
    "real_minus_channel_block_permutation",
    "max_selection_gap",
)
EXPECTED_H_ONLY_FITS = 6
EXPECTED_FRONTEND_FITS = 72
EXPECTED_TOTAL_FITS = 78

RUN032_IMMUTABLE_HASHES = {
    "artifacts/a1_measurement_validity_contract.yaml": "4c09d484cc1b09d7b1215fbf70c442ba8aaaaea57cd5ef42a66a5b25f99118b6",
    "04_results/audits/a1_measurement_validity.json": "89d4dc7ac9b4925f60db4fdc12a059f426bd453764db685827f5ed83b4fef270",
    "04_results/audits/a1_measurement_validity.md": "f7b84125d56cd0e8816374d0e15ec6228b0fc52d69bc9e812e60e213d2e7ac61",
    "04_results/audits/a1_measurement_validity_run_ledger.jsonl.gz": "4cc1d14acd8c93e834a96146f63460bc8d6d231a61f8fde6549ec319fd6fc638",
    "02_code/src/data/a1_measurement_validity.py": "ea08228a713a03512d807e3f6c890003d558eef9fb4b58a4c69d151e856c64b9",
    "02_code/scripts/run_a1_measurement_validity.py": "9a2b221d30d579758c5d5575b646db1314d09b2ddf2c515cfa42ac3a91eaf4b7",
    "02_code/tests/test_a1_measurement_validity.py": "d349d963902b6b08cf6bd8e99a33a91f62623d7f72a4c9df126c19f5905d5328",
    "runs/2026-08-16_032_v317_a1_measurement_validity.md": "4158a0d4488b6c77dfeb0fb05b0e71503d2ac6595ac008c1a64aa20019c6fb02",
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_17_2026-08-16.md": "e650b85a1f32c4bbccd45214584393f41b38884357bb43b2c091cb5d9924dd9a",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_run032_immutable(root: Path) -> dict[str, str]:
    observed = {
        relative: sha256_file(root / relative)
        for relative in RUN032_IMMUTABLE_HASHES
    }
    if observed != RUN032_IMMUTABLE_HASHES:
        changed = {
            key: {
                "expected": RUN032_IMMUTABLE_HASHES[key],
                "observed": observed[key],
            }
            for key in RUN032_IMMUTABLE_HASHES
            if observed[key] != RUN032_IMMUTABLE_HASHES[key]
        }
        raise RuntimeError(f"STATE_SPEC_CONFLICT: run-032 evidence changed: {changed}")
    return observed


def temporal_fixation_feature(
    fixations: Sequence[np.ndarray],
) -> tuple[np.ndarray | None, dict[str, int]]:
    """Return the exact signed channel-major 105x8 fixation-relative feature."""

    features: list[np.ndarray] = []
    exclusions = {"TEMPORAL_T_LT_8": 0, "TEMPORAL_INVALID": 0}
    for value in fixations:
        matrix = np.asarray(value)
        if matrix.ndim != 2 or matrix.shape[1] != 105 or not np.isfinite(matrix).all():
            exclusions["TEMPORAL_INVALID"] += 1
            continue
        if matrix.shape[0] < 8:
            exclusions["TEMPORAL_T_LT_8"] += 1
            continue
        centered = matrix.astype(np.float64, copy=False) - matrix.mean(
            axis=0, keepdims=True, dtype=np.float64
        )
        bins = np.array_split(np.arange(matrix.shape[0]), 8)
        if len(bins) != 8 or any(len(indices) == 0 for indices in bins):
            raise AssertionError("numpy.array_split did not produce eight nonempty bins")
        channel_by_bin = np.stack(
            [centered[indices].mean(axis=0) for indices in bins], axis=1
        )
        feature = channel_by_bin.reshape(-1).astype(np.float32)
        if feature.shape != (840,) or not np.isfinite(feature).all():
            raise ValueError("temporal fixation feature is not finite float32[840]")
        features.append(feature)
    if not features:
        return None, exclusions
    result = np.mean(np.stack(features).astype(np.float64), axis=0).astype(np.float32)
    if result.shape != (840,) or not np.isfinite(result).all():
        raise ValueError("temporal word feature is not finite float32[840]")
    return result, exclusions


def fit_log_bandpower(
    fit_values: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.asarray(fit_values, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 1 or values.shape[1] != 840:
        raise ValueError("log-bandpower fit rows must be [N,840]")
    if not np.isfinite(values).all() or np.any(values < 0.0):
        raise ValueError("log-bandpower requires finite nonnegative input")
    medians = np.empty(840, dtype=np.float64)
    for dimension in range(840):
        positive = values[:, dimension][values[:, dimension] > 0.0]
        if positive.size == 0:
            raise ValueError(f"log-bandpower dimension {dimension} has no positive fit value")
        medians[dimension] = np.median(positive)
    if not np.isfinite(medians).all() or np.any(medians <= 0.0):
        raise ValueError("log-bandpower fit medians are not strictly positive")
    epsilon = 1e-6 * medians
    return epsilon, {
        "positive_dimension_count": 840,
        "median_min": float(medians.min()),
        "median_max": float(medians.max()),
        "epsilon_min": float(epsilon.min()),
        "epsilon_max": float(epsilon.max()),
        "epsilon_le_f4_sha256": hashlib.sha256(
            epsilon.astype("<f4").tobytes(order="C")
        ).hexdigest(),
    }


def apply_log_bandpower(values: np.ndarray, epsilon: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    eps = np.asarray(epsilon, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 840 or eps.shape != (840,):
        raise ValueError("log-bandpower transform requires [N,840] and epsilon[840]")
    if not np.isfinite(array).all() or np.any(array < 0.0):
        raise ValueError("log-bandpower input must be finite and nonnegative")
    if not np.isfinite(eps).all() or np.any(eps <= 0.0):
        raise ValueError("log-bandpower epsilon must be finite and positive")
    result = np.log(array + eps).astype(np.float32)
    if result.shape != array.shape or not np.isfinite(result).all():
        raise ValueError("log-bandpower produced invalid values")
    return result


def derive_recovery_partitions(
    task_protocol: Mapping[str, Any], cell: Mapping[str, Any]
) -> dict[str, Any]:
    fit = set(map(str, cell["train_record_ids"]))
    cross = set(map(str, cell["validation_record_ids"]))
    records = task_protocol["record_rows"]
    assignments = task_protocol["text_assignment"]
    held_subjects = {str(records[record]["subject_id"]) for record in cross}
    if len(held_subjects) != 5:
        raise ValueError("cross partition does not contain five held-out subjects")
    seen = {
        str(record_id)
        for record_id in task_protocol["outer_train_record_ids"]
        if str(records[str(record_id)]["subject_id"]) not in held_subjects
        and str(assignments[str(records[str(record_id)]["stimulus_id"])]) == "0"
    }
    expected_fit = {
        str(record_id)
        for record_id in task_protocol["outer_train_record_ids"]
        if str(records[str(record_id)]["subject_id"]) not in held_subjects
        and str(assignments[str(records[str(record_id)]["stimulus_id"])]) != "0"
    }
    expected_cross = {
        str(record_id)
        for record_id in task_protocol["outer_train_record_ids"]
        if str(records[str(record_id)]["subject_id"]) in held_subjects
        and str(assignments[str(records[str(record_id)]["stimulus_id"])]) == "0"
    }
    if fit != expected_fit or cross != expected_cross:
        raise ValueError("frozen inner cell does not match v3.18 fit/cross arithmetic")
    if fit & seen or fit & cross or seen & cross:
        raise ValueError("fit/seen/cross record partitions overlap")
    seen_subjects = {str(records[record]["subject_id"]) for record in seen}
    if len(seen_subjects) != 10 or seen_subjects & held_subjects:
        raise ValueError("seen partition does not contain the matched ten subjects")
    all_t0 = {
        str(record_id)
        for record_id in task_protocol["outer_train_record_ids"]
        if str(assignments[str(records[str(record_id)]["stimulus_id"])]) == "0"
    }
    if seen | cross != all_t0:
        raise ValueError("seen/cross do not cover all t0 outer-train records")
    return {
        "fit_record_ids": sorted(fit),
        "seen_record_ids": sorted(seen),
        "cross_record_ids": sorted(cross),
        "fit_subject_ids": sorted(seen_subjects),
        "seen_subject_ids": sorted(seen_subjects),
        "cross_subject_ids": sorted(held_subjects),
        "record_partitions_pairwise_disjoint": True,
        "seen_cross_cover_all_t0": True,
    }


def build_recovery_v5_ledger(
    *,
    run_id: str,
    fit_id: str,
    seed: int,
    outer_cell: str,
    recovery_cell: str,
    fit_record_ids: Sequence[str],
    seen_record_ids: Sequence[str],
    cross_record_ids: Sequence[str],
    input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    scoring = sorted(set(map(str, seen_record_ids)) | set(map(str, cross_record_ids)))
    ledger = build_v5_ledger(
        run_id=run_id,
        fit_id=fit_id,
        seed=seed,
        outer_cell=outer_cell,
        inner_cell=recovery_cell,
        fit_record_ids=fit_record_ids,
        validation_record_ids=scoring,
        scoring_record_ids=scoring,
        input_hashes=input_hashes,
    )
    ledger["recovery_scoring"] = {
        "seen_score_record_ids": sorted(set(map(str, seen_record_ids))),
        "cross_score_record_ids": sorted(set(map(str, cross_record_ids))),
        "same_fit_scores_both_regimes": True,
    }
    return ledger


def validate_recovery_v5_or_raise(
    ledger: Mapping[str, Any],
    scope_index: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> None:
    validate_v5_or_raise(ledger, scope_index, input_hashes)
    scoring = ledger.get("recovery_scoring", {})
    seen = set(map(str, scoring.get("seen_score_record_ids", [])))
    cross = set(map(str, scoring.get("cross_score_record_ids", [])))
    if not seen or not cross or not seen.isdisjoint(cross):
        raise ValueError("recovery V5 seen/cross scopes are missing or overlap")
    if set(map(str, ledger.get("scoring_record_ids", []))) != seen | cross:
        raise ValueError("recovery V5 scoring union mismatch")
    if scoring.get("same_fit_scores_both_regimes") is not True:
        raise ValueError("recovery V5 does not bind both scores to one fit")
    if ledger.get("outer_test_record_ids_read") != []:
        raise ValueError("recovery V5 has outer-test reads")
    if ledger.get("calibration_record_ids") != []:
        raise ValueError("recovery V5 has calibration reads")


def summarize_regime_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    task: str,
    frontend: str,
    regime: str,
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if row["task"] == task
        and row["frontend"] == frontend
        and row["regime"] == regime
    ]
    by_subject: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    for row in selected:
        by_subject.setdefault(str(row["subject_id"]), {}).setdefault(
            str(row["fold"]), []
        ).append(row)
    if len(by_subject) != 15:
        raise ValueError(f"{task}/{frontend}/{regime} does not cover 15 subjects")
    expected_fold_count = 2 if regime == "seen" else 1
    if any(len(folds) != expected_fold_count for folds in by_subject.values()):
        raise ValueError(
            f"{task}/{frontend}/{regime} subject fold multiplicity is not "
            f"{expected_fold_count}"
        )
    summaries: dict[str, Any] = {}
    for metric in METRICS:
        values = {
            subject: float(
                np.mean(
                    [
                        np.mean([float(row[metric]) for row in fold_rows])
                        for fold_rows in folds.values()
                    ]
                )
            )
            for subject, folds in sorted(by_subject.items())
        }
        summaries[metric] = cluster_bootstrap(
            values,
            n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
            seed=stable_seed(20260813, "v3.18", task, frontend, regime, metric),
        )
    absolute: dict[str, Any] = {}
    for arm in ("H_only", *ARMS):
        key = f"logp_{arm}"
        values = {
            subject: float(
                np.mean(
                    [
                        np.mean([float(row[key]) for row in fold_rows])
                        for fold_rows in folds.values()
                    ]
                )
            )
            for subject, folds in sorted(by_subject.items())
        }
        absolute[arm] = cluster_bootstrap(
            values,
            n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
            seed=stable_seed(20260813, "v3.18", task, frontend, regime, key),
        )
    family = (
        summaries["u_oof"]["ci95"][0] > 0.0
        and summaries["u_oof"]["positive_subject_count"] >= 12
        and summaries["real_minus_trial_shuffle"]["estimate"] > 0.0
        and summaries["real_minus_within_trial_unit_assignment_shuffle"]["estimate"]
        > 0.0
        and summaries["real_minus_channel_block_permutation"]["estimate"] > 0.0
    )
    return {
        "subject_ids": sorted(by_subject),
        "subject_count": 15,
        "equal_subject_weighting": True,
        "seen_fold_means_equal_weighted_before_subject_pairing": regime == "seen",
        "observation_count": len(selected),
        "metrics": summaries,
        "absolute_logp": absolute,
        "family_detected": bool(family),
        "legacy_label": "legacy_pointwise_max_sensitivity",
    }


def paired_summary(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    seed_parts: Sequence[object],
) -> dict[str, Any]:
    left_values = left["metrics"]["u_oof"]["subject_values"]
    right_values = right["metrics"]["u_oof"]["subject_values"]
    if set(left_values) != set(right_values) or len(left_values) != 15:
        raise ValueError("paired u_oof summaries do not share frozen 15 subjects")
    differences = {
        subject: float(left_values[subject]) - float(right_values[subject])
        for subject in sorted(left_values)
    }
    return cluster_bootstrap(
        differences,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(*seed_parts),
    )


def bottleneck_label(seen_family: bool, cross_family: bool) -> str:
    if seen_family and not cross_family:
        return "TRANSFER_DOMINANT"
    if not seen_family and not cross_family:
        return "REPRESENTATION_OR_PROBE_DOMINANT"
    if seen_family and cross_family:
        return "BASELINE_REPRODUCTION_DEVIATION"
    return "UNEXPECTED_REGIME_ORDERING"


def evaluate_recovery(
    results: Mapping[str, Any], *, contract_pass: bool
) -> tuple[str, str | None, list[str], list[str]]:
    reasons: list[str] = []
    if not contract_pass:
        reasons.append("FIT_ROW_V5_FORMAL_OR_NO_READ_CONTRACT_FAILED")
        return "INVALID_A1R_RECOVERY", None, [], reasons
    candidate_pass: dict[str, list[str]] = {}
    candidate_score: dict[str, float] = {}
    for candidate in CANDIDATES:
        passing: list[str] = []
        deltas: list[float] = []
        for task in TASKS:
            row = results[task][candidate]
            delta = row["recovery_delta"]
            passed = (
                row["cross"]["family_detected"]
                and delta["ci95"][0] > 0.0
                and delta["positive_subject_count"] >= 10
            )
            row["recovery_pass"] = bool(passed)
            if passed:
                passing.append(task)
                deltas.append(float(delta["estimate"]))
        candidate_pass[candidate] = passing
        if len(passing) == 2:
            candidate_score[candidate] = min(deltas)
        elif len(passing) == 1:
            candidate_score[candidate] = deltas[0]
        else:
            candidate_score[candidate] = float("-inf")
    max_count = max(len(value) for value in candidate_pass.values())
    if max_count == 0:
        return "FAIL_A1R_RECOVERY", None, [], []
    selected = sorted(
        CANDIDATES,
        key=lambda candidate: (
            -len(candidate_pass[candidate]),
            -candidate_score[candidate],
            candidate,
        ),
    )[0]
    outcome = (
        "PASS_A1R_RECOVERY_BOTH_TASKS"
        if max_count == 2
        else "PASS_LIMITED_A1R_RECOVERY_ONE_TASK"
    )
    return outcome, selected, candidate_pass[selected], []
