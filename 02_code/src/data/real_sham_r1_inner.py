"""Pure contracts for the v3.22 R1 inner-only real-vs-sham diagnostic."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from data.a1_admission import (
    DEFAULT_ADMISSION_CONFIG,
    cluster_bootstrap,
    stable_seed,
)
from data.a1_failure_diagnosis import sha256_file


ALGORITHM_VERSION = "real-sham-r1-inner-v322-d90-d95-v1"
RUN_ID = "2026-08-22_003_v322_real_sham_r1_inner"
TASKS = ("task1_nr", "task2_tsr")
FOLDS = ("inner_s0_t0", "inner_s1_t0", "inner_s2_t0")
FRONTENDS = ("F0_A1_BP_CONCAT", "F1_LOGREL_BP", "F2_T8_FIXATION")
TARGETS = ("Y0_RAW_MINILM", "Y1_H_RESIDUAL_MINILM")
ARMS = (
    "real",
    "trial_shuffle",
    "within_trial_unit_assignment_shuffle",
    "channel_block_permutation",
)
REGIMES = ("seen", "cross")
BASELINE_CANDIDATE = "F0_A1_BP_CONCAT/Y0_RAW_MINILM"
CANDIDATES = tuple(
    f"{frontend}/{target}"
    for frontend in FRONTENDS
    for target in TARGETS
    if f"{frontend}/{target}" != BASELINE_CANDIDATE
)
METRICS = (
    "delta_semantic",
    "delta_legacy",
    "delta_channel",
    "u_oof",
    "u_min",
    "real_minus_trial_shuffle",
    "real_minus_within_trial_unit_assignment_shuffle",
    "real_minus_channel_block_permutation",
    "max_selection_gap",
)

EXPECTED_H_ONLY_Y0 = 6
EXPECTED_TEXT_RESIDUALIZERS = 6
EXPECTED_EEG_PROBES = 144
EXPECTED_RIDGE_OPERATIONS = 156
EXPECTED_EEG_V5_LEDGERS = 150
EXPECTED_TEXT_LEDGERS = 6

IMMUTABLE_PARENT_R0_HASHES = {
    "04_results/audits/a1_admission.json": "b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e",
    "04_results/audits/a1_admission.md": "e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e",
    "04_results/audits/a1_admission_run_ledger.jsonl.gz": "fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd",
    "04_results/audits/a1_measurement_recovery.json": "cf68c0ca170152a79f163ed001706df80ea649ea854da85b09fef1f638e8b51a",
    "04_results/audits/a1_measurement_recovery.md": "fc039ae77043619e562eb942898287321882189736bdd8219fc3c6a71cc87004",
    "04_results/audits/a1_measurement_recovery_run_ledger.jsonl.gz": "90326ad6ed2bb981df0c0d8559102dd73c56a16ce7de6923973bad42529debc7",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark.json": "f496f308688df7ff68b82f2a5c38fedc971032801b6060f7ed1e61e64e21d2ea",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark.md": "94e580531f16e8886949b7196c2d47889f360997bda6d467fb044f619c54d9ea",
    "04_results/synthetic_method/eq_anma_synthetic_benchmark_run_ledger.jsonl.gz": "705e9b034794f77eac0f91355f093e7dc70a5d2bb2a13fa2f7da784a0e8b2601",
    "artifacts/real_sham_rescue_freeze.yaml": "a23c06dd9357bfdcc383e34a58d9258e38145244af146653187d18943864afd2",
    "artifacts/real_sham_rescue_contract.yaml": "89f9bc468f5bea0bafe127baa1e0a96ceb5ff1c9327aba89e3445d86ed683055",
    "04_results/diagnostics/real_sham_rescue_r0.json": "70eb78aaa7de232d908d62e610c916a45035c8586f23909879a162c0712a3c5c",
    "04_results/diagnostics/real_sham_rescue_r0.md": "0126550bef4e4220327ed93aa811ade6c7d2170e483dd975d39fa80066037955",
    "04_results/diagnostics/real_sham_rescue_r0_run_ledger.jsonl.gz": "1739ebc0e8b4a9b39887041a3907208a13be98fd4a619acd340e5fc955345ec1",
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_21_2026-08-22.md": "9adf0233ed0a36bac63d731637876513811fa1488ddbaf24f4ce5019a2377c7c",
    "runs/research/2026-08-22_001_v321_real_sham_rescue_freeze.md": "bf42b56b6b321206e9da9f34714bd669e37be33e656635df089da19f80097a9c",
    "runs/research/2026-08-22_002_v321_real_sham_rescue_r0.md": "f58eb1b369e1e6ad8b9c0c7fe269eff94da2d31aafba085394f7955cb92e154b",
    "02_code/src/data/real_sham_rescue.py": "fd923075925a2e6e182ac71340d1ad58d5508b2e1dfb07af30a8fb41c756c237",
    "02_code/scripts/run_real_sham_rescue_r0.py": "7f1327ac5f6ffda3a9700e99d08c44afbc6b9e3c7d34024ffe9d334d2ecda79b",
    "02_code/tests/test_real_sham_rescue.py": "aa13267d0c307f007bd3e6de8a1aa8828bc8caa7a975df0ba5a901c7e553ad2c",
}


def verify_immutable_parent_r0(root: Path) -> dict[str, str]:
    observed = {
        relative: sha256_file(root / relative)
        for relative in IMMUTABLE_PARENT_R0_HASHES
    }
    if observed != IMMUTABLE_PARENT_R0_HASHES:
        changed = {
            relative: {
                "expected": IMMUTABLE_PARENT_R0_HASHES[relative],
                "observed": observed[relative],
            }
            for relative in IMMUTABLE_PARENT_R0_HASHES
            if observed[relative] != IMMUTABLE_PARENT_R0_HASHES[relative]
        }
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: immutable parent/R0 artifacts changed: {changed}"
        )
    return observed


def canonical_fit_row_indices(
    rows: Sequence[Mapping[str, Any]], supported: set[str]
) -> tuple[list[str], np.ndarray, list[str]]:
    """Return one lexically canonical fit observation for every supported item."""

    by_item: dict[str, list[tuple[str, int]]] = {item: [] for item in supported}
    for index, row in enumerate(rows):
        item = str(row["item_id"])
        if item in by_item:
            observation_id = str(row["observation_id"])
            if not observation_id:
                raise ValueError("canonical residual target requires observation_id")
            by_item[item].append((observation_id, index))
    items = sorted(supported)
    missing = [item for item in items if not by_item[item]]
    if missing:
        raise ValueError(f"supported items lack fit rows: {missing[:5]}")
    selected = [min(by_item[item], key=lambda pair: (pair[0], pair[1])) for item in items]
    observation_ids = [pair[0] for pair in selected]
    if len(set(observation_ids)) != len(observation_ids):
        raise ValueError("canonical residual observations are not unique")
    return items, np.asarray([pair[1] for pair in selected], dtype=np.int64), observation_ids


def build_normalized_residual_vocabulary(
    *,
    rows: Sequence[Mapping[str, Any]],
    supported: set[str],
    h_fit: np.ndarray,
    y0_fit: np.ndarray,
    model: Mapping[str, np.ndarray],
) -> tuple[list[str], np.ndarray, dict[str, int], dict[str, Any]]:
    """Build the frozen Y1 vocabulary from canonical fit rows only."""

    h = np.asarray(h_fit, dtype=np.float32)
    y0 = np.asarray(y0_fit, dtype=np.float32)
    weights = np.asarray(model.get("weights"), dtype=np.float32)
    intercept = np.asarray(model.get("intercept"), dtype=np.float32)
    if h.shape != y0.shape or h.ndim != 2 or h.shape[1] != 384:
        raise ValueError("Y1 residualizer requires aligned fit H/Y0 [N,384]")
    if len(rows) != h.shape[0] or weights.shape != (384, 384) or intercept.shape != (384,):
        raise ValueError("Y1 residualizer model or row shape is invalid")
    if not all(np.isfinite(value).all() for value in (h, y0, weights, intercept)):
        raise ValueError("Y1 residualizer inputs/model must be finite")
    items, indices, observation_ids = canonical_fit_row_indices(rows, supported)
    prediction = h[indices].astype(np.float64) @ weights.astype(np.float64)
    prediction += intercept.astype(np.float64)
    residual = y0[indices].astype(np.float64) - prediction
    norms = np.linalg.norm(residual, axis=1)
    if not np.isfinite(residual).all() or not np.isfinite(norms).all():
        raise ValueError("Y1 residuals are not finite")
    if np.any(norms <= 1e-8):
        invalid = [items[index] for index in np.flatnonzero(norms <= 1e-8)[:5]]
        raise ValueError(f"Y1 residual norm <=1e-8 without fallback: {invalid}")
    vocabulary = (residual / norms[:, None]).astype(np.float32)
    renorm = np.linalg.norm(vocabulary.astype(np.float64), axis=1)
    if not np.isfinite(vocabulary).all() or not np.allclose(renorm, 1.0, atol=1e-6):
        raise ValueError("Y1 normalized vocabulary contract failed")
    identity_hash = hashlib.sha256(
        "\n".join(observation_ids).encode("utf-8")
    ).hexdigest()
    return items, vocabulary, {item: index for index, item in enumerate(items)}, {
        "fit_rows": len(rows),
        "supported_item_count": len(items),
        "canonical_fit_row_count": len(observation_ids),
        "canonical_fit_observation_ids_sha256": identity_hash,
        "residual_norm_min": float(norms.min()),
        "residual_norm_max": float(norms.max()),
        "residual_norm_threshold": 1e-8,
        "finite": True,
        "l2_normalized": True,
        "fallback_used": False,
        "seen_cross_refit_count": 0,
    }


def target_rows(
    rows: Sequence[Mapping[str, Any]],
    vocabulary: np.ndarray,
    item_positions: Mapping[str, int],
) -> np.ndarray:
    positions = np.asarray(
        [item_positions[str(row["item_id"])] for row in rows], dtype=np.int64
    )
    result = np.asarray(vocabulary, dtype=np.float32)[positions]
    if result.shape != (len(rows), 384) or not np.isfinite(result).all():
        raise ValueError("fixed residual target rows are invalid")
    return result


def build_text_residualizer_ledger(
    *,
    operation_id: str,
    task: str,
    fold: str,
    fit_record_ids: Sequence[str],
    fit_row_count: int,
    summary: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ledger_type": "TEXT_ONLY_RESIDUALIZER",
        "run_id": RUN_ID,
        "operation_id": operation_id,
        "task": task,
        "fold": fold,
        "fit_type": "ridge",
        "ridge_alpha": 1.0,
        "float64_solve": True,
        "intercept_penalized": False,
        "fit_record_ids": sorted(set(map(str, fit_record_ids))),
        "fit_row_count": int(fit_row_count),
        "supported_item_count": int(summary["supported_item_count"]),
        "canonical_fit_observation_ids_sha256": summary[
            "canonical_fit_observation_ids_sha256"
        ],
        "eeg_loaded": False,
        "outer_test_read": False,
        "calibration_read": False,
        "outer_test_record_ids_read": [],
        "calibration_record_ids": [],
        "seen_cross_refit_count": 0,
        "fallback_used": False,
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
    }


def validate_text_residualizer_ledger(ledger: Mapping[str, Any]) -> None:
    if ledger.get("ledger_type") != "TEXT_ONLY_RESIDUALIZER":
        raise ValueError("text-only ledger type changed")
    if ledger.get("fit_type") != "ridge" or ledger.get("ridge_alpha") != 1.0:
        raise ValueError("text-only ridge contract changed")
    required_false = (
        "eeg_loaded",
        "outer_test_read",
        "calibration_read",
        "fallback_used",
    )
    if any(ledger.get(field) is not False for field in required_false):
        raise ValueError("text-only ledger contains forbidden activity")
    if ledger.get("seen_cross_refit_count") != 0:
        raise ValueError("Y1 residualizer was refit on seen/cross")
    if ledger.get("outer_test_record_ids_read") != []:
        raise ValueError("text-only ledger contains outer-test reads")
    if ledger.get("calibration_record_ids") != []:
        raise ValueError("text-only ledger contains calibration reads")


def summarize_subject_first(
    rows: Sequence[Mapping[str, Any]],
    *,
    task: str,
    candidate: str,
    regime: str,
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if row["task"] == task
        and row["candidate"] == candidate
        and row["regime"] == regime
    ]
    by_subject: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    for row in selected:
        by_subject.setdefault(str(row["subject_id"]), {}).setdefault(
            str(row["fold"]), []
        ).append(row)
    if len(by_subject) != 15:
        raise ValueError(f"{task}/{candidate}/{regime} does not cover 15 subjects")
    expected_fold_count = 2 if regime == "seen" else 1
    if any(len(folds) != expected_fold_count for folds in by_subject.values()):
        raise ValueError(f"{task}/{candidate}/{regime} fold multiplicity changed")
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
            seed=stable_seed(20260813, "v3.22", task, candidate, regime, metric),
        )
    absolute: dict[str, Any] = {}
    for arm in ARMS:
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
            seed=stable_seed(20260813, "v3.22", task, candidate, regime, key),
        )
    semantic = summaries["delta_semantic"]
    family = (
        semantic["ci95"][0] > 0.0
        and semantic["positive_subject_count"] >= 12
        and summaries["real_minus_trial_shuffle"]["estimate"] > 0.0
        and summaries["real_minus_within_trial_unit_assignment_shuffle"][
            "estimate"
        ]
        > 0.0
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
        "family_rule": {
            "delta_semantic_ci_lower_gt_zero": semantic["ci95"][0] > 0.0,
            "delta_semantic_positive_subjects_gte_12": semantic[
                "positive_subject_count"
            ]
            >= 12,
            "both_semantic_single_sham_estimates_gt_zero": (
                summaries["real_minus_trial_shuffle"]["estimate"] > 0.0
                and summaries["real_minus_within_trial_unit_assignment_shuffle"][
                    "estimate"
                ]
                > 0.0
            ),
        },
    }


def paired_cross_recovery(
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    task: str,
    candidate_id: str,
) -> dict[str, Any]:
    left = candidate["metrics"]["delta_semantic"]["subject_values"]
    right = baseline["metrics"]["delta_semantic"]["subject_values"]
    if set(left) != set(right) or len(left) != 15:
        raise ValueError("paired recovery requires the same 15 cross subjects")
    differences = {
        subject: float(left[subject]) - float(right[subject])
        for subject in sorted(left)
    }
    return cluster_bootstrap(
        differences,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(20260813, "v3.22", task, candidate_id, "cross_recovery"),
    )


def evaluate_r1_outcome(
    results: Mapping[str, Any], *, contract_pass: bool
) -> tuple[str, str | None, list[str], list[dict[str, Any]], list[str]]:
    if not contract_pass:
        return (
            "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC",
            None,
            [],
            [],
            ["SCOPE_LEDGER_READ_COUNT_FORMAL_OR_HASH_CONTRACT_FAILED"],
        )
    ranking: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        passing_tasks: list[str] = []
        passing_deltas: list[float] = []
        task_deltas: dict[str, float] = {}
        for task in TASKS:
            row = results[task][candidate]
            recovery = row["cross_recovery"]
            passed = (
                row["cross"]["family_detected"]
                and recovery["ci95"][0] > 0.0
                and recovery["positive_subject_count"] >= 10
            )
            row["recovery_pass"] = bool(passed)
            task_deltas[task] = float(recovery["estimate"])
            if passed:
                passing_tasks.append(task)
                passing_deltas.append(float(recovery["estimate"]))
        ranking.append(
            {
                "candidate": candidate,
                "recovered_task_count": len(passing_tasks),
                "passing_tasks": passing_tasks,
                "task_cross_recovery_delta": task_deltas,
                "two_task_minimum_delta": (
                    min(passing_deltas) if len(passing_tasks) == 2 else None
                ),
                "one_task_passing_delta": (
                    passing_deltas[0] if len(passing_tasks) == 1 else None
                ),
            }
        )
    ranking.sort(
        key=lambda row: (
            -row["recovered_task_count"],
            -(
                row["two_task_minimum_delta"]
                if row["two_task_minimum_delta"] is not None
                else float("-inf")
            ),
            -(
                row["one_task_passing_delta"]
                if row["one_task_passing_delta"] is not None
                else float("-inf")
            ),
            row["candidate"],
        )
    )
    selected = ranking[0]
    recovered_count = int(selected["recovered_task_count"])
    if recovered_count == 2:
        outcome = "PASS_R1_BOTH_TASKS"
    elif recovered_count == 1:
        outcome = "PASS_R1_LIMITED_ONE_TASK"
    else:
        outcome = "FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC"
    return (
        outcome,
        selected["candidate"] if recovered_count else None,
        list(selected["passing_tasks"]),
        ranking,
        [],
    )
