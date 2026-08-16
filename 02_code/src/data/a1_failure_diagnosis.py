"""Pure contracts for the SPEC v3.15 A1 failure diagnosis.

The diagnosis is deliberately separate from the admitted v3.14 runner.  It
validates the immutable failure evidence and implements only the two explicit
oracle positive controls from D42.  No helper in this module accepts EEG as an
oracle input or changes the frozen A1 admission outcome.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from data.a1_admission import (
    DEFAULT_ADMISSION_CONFIG,
    balanced_recall,
    canonical_artifact,
    cluster_bootstrap,
    permutation_null_fixed_predictions,
    stable_seed,
    validate_v5_or_raise,
)


ALGORITHM_VERSION = "a1-failure-diagnosis-v315-d42-v1"
RUN_ID = "2026-08-16_029_v315_a1_failure_diagnosis"
TASKS = ("task1_nr", "task2_tsr")
BASES = ("raw", "token_local_frozen_initial_latent")
SEEDS = (20260813, 20260814, 20260815)
EXPECTED_FIT_COUNTS = {"logistic": 54, "ridge": 4, "total": 58}

OLD_ARTIFACT_HASHES = {
    "artifacts/a1_admission_contract.yaml": "c9c5a94b8227b6e43ecfc6d61b9b10b33f9340f7c845ca7dbaa0e0a3e65d9f4b",
    "04_results/audits/a1_admission.json": "b3d2b47ee21b2e777470004dbca862cb9495b59f3c68513e9001f3800b4e151e",
    "04_results/audits/a1_admission.md": "e187f2314ca3ee8a9d8f973c7898276ecaccd64245ce1480243c916c5c729a8e",
    "04_results/audits/a1_admission_run_ledger.jsonl.gz": "fe22b691795709508386d72d662cbf2feeafb3dd74d5012b46b12e5ae1d963fd",
}

OLD_IMPLEMENTATION_HASHES = {
    "02_code/src/data/a1_admission.py": "14e45bc194cdfcbb03ef01a3862dfb331b916a7e425e7a74a8adffecb5ab96b4",
    "02_code/scripts/run_a1_admission.py": "a671a65dd4fb533cb92b820d9e723e3963c99168c96a3cf77bf9bfcd8f9fb099",
    "02_code/tests/test_a1_admission.py": "3866756f6d4b56f1f33ea81b6eccaed5ffc3fe385a319795a8e425afd75aa238",
}

FORBIDDEN_FORMAL_KEYS = {
    "features",
    "feature_array",
    "eeg_array",
    "embeddings",
    "observation_embeddings",
    "logits",
    "weights",
    "model_parameters",
    "trial_assignment",
    "trial_exclusions",
    "unit_exclusions",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_old_evidence(root: Path) -> dict[str, Any]:
    """Byte-verify admitted artifacts/implementation and inspect the old gzip."""

    observed_artifacts = {
        relative: sha256_file(root / relative) for relative in OLD_ARTIFACT_HASHES
    }
    observed_implementation = {
        relative: sha256_file(root / relative) for relative in OLD_IMPLEMENTATION_HASHES
    }
    if observed_artifacts != OLD_ARTIFACT_HASHES:
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: old A1 artifact hashes changed: {observed_artifacts}"
        )
    if observed_implementation != OLD_IMPLEMENTATION_HASHES:
        raise RuntimeError(
            "STATE_SPEC_CONFLICT: admitted A1 implementation bytes changed: "
            f"{observed_implementation}"
        )
    ledger_path = root / "04_results/audits/a1_admission_run_ledger.jsonl.gz"
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    fit_ids = [str(row["fit_id"]) for row in rows]
    if len(rows) != 639 or len(set(fit_ids)) != 639:
        raise RuntimeError("STATE_SPEC_CONFLICT: old A1 ledger is not 639 unique fits")
    if any(row.get("outer_test_record_ids_read") != [] for row in rows):
        raise RuntimeError("STATE_SPEC_CONFLICT: old A1 ledger has outer-test reads")
    if any(row.get("calibration_record_ids") != [] for row in rows):
        raise RuntimeError("STATE_SPEC_CONFLICT: old A1 ledger has calibration reads")
    return {
        "artifact_hashes": observed_artifacts,
        "implementation_hashes": observed_implementation,
        "ledger_rows": len(rows),
        "unique_fit_ids": len(set(fit_ids)),
        "outer_test_read_count": 0,
        "calibration_read_count": 0,
        "ledgers": rows,
    }


def validate_diagnosis_v5_or_raise(
    ledger: Mapping[str, Any],
    scope_index: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> None:
    """Apply admitted V5 plus explicit run/stage zero-read invariants."""

    validate_v5_or_raise(ledger, scope_index, input_hashes)
    if ledger.get("outer_test_record_ids_read") != []:
        raise ValueError("V5 diagnosis ledger has outer-test reads")
    if ledger.get("calibration_record_ids") != []:
        raise ValueError("V5 diagnosis ledger has calibration reads")
    for stage in ledger.get("stages", []):
        if stage.get("outer_test_record_ids_read") != []:
            raise ValueError("V5 diagnosis stage has outer-test reads")
        if stage.get("calibration_record_ids") != []:
            raise ValueError("V5 diagnosis stage has calibration reads")


def oracle_input(
    h_values: np.ndarray,
    item_values: np.ndarray,
    *,
    role: str,
) -> np.ndarray:
    """Construct only the explicitly registered positive-control inputs."""

    h = np.asarray(h_values, dtype=np.float32)
    items = np.asarray(item_values, dtype=np.float32)
    if h.ndim != 2 or items.ndim != 2 or h.shape[0] != items.shape[0]:
        raise ValueError("positive-control H/item rows must be aligned rank-2 matrices")
    if h.shape[1] != 384 or items.shape[1] != 384:
        raise ValueError("positive-control H and item embeddings must each be 384D")
    if not np.isfinite(h).all() or not np.isfinite(items).all():
        raise ValueError("positive-control inputs must be finite")
    if role == "a_a3_construct_validity_oracle_item":
        return items.copy()
    if role == "a_a1_scorer_h_only":
        return h.copy()
    if role == "a_a1_scorer_oracle_item":
        return np.concatenate([h, items], axis=1).astype(np.float32, copy=False)
    raise ValueError(f"oracle item embedding is forbidden for unregistered role: {role}")


def validate_fold_roles(
    *,
    inner_train_record_ids: Sequence[str],
    inner_validation_record_ids: Sequence[str],
    cluster_fit_record_ids: Sequence[str],
    scoring_record_ids: Sequence[str],
) -> dict[str, bool]:
    train = set(map(str, inner_train_record_ids))
    validation = set(map(str, inner_validation_record_ids))
    cluster_fit = set(map(str, cluster_fit_record_ids))
    scoring = set(map(str, scoring_record_ids))
    result = {
        "inner_train_validation_disjoint": train.isdisjoint(validation),
        "cluster_fit_train_only": cluster_fit <= train and cluster_fit.isdisjoint(validation),
        "validation_scoring_only": scoring <= validation and scoring.isdisjoint(train),
    }
    if not all(result.values()):
        raise ValueError(f"fold role violation: {result}")
    return result


def class_support_summary(
    train_labels: Sequence[int], scoring_labels: Sequence[int], *, class_count: int = 8
) -> dict[str, Any]:
    train = np.asarray(train_labels, dtype=np.int64)
    scoring = np.asarray(scoring_labels, dtype=np.int64)
    if np.any(train < 0) or np.any(train >= class_count):
        raise ValueError("train cluster label is outside frozen K=8")
    if np.any(scoring < 0) or np.any(scoring >= class_count):
        raise ValueError("scoring cluster label is outside frozen K=8")
    train_counts = np.bincount(train, minlength=class_count)
    scoring_counts = np.bincount(scoring, minlength=class_count)
    return {
        "train_class_counts": train_counts.tolist(),
        "scoring_class_counts": scoring_counts.tolist(),
        "train_empty_classes": np.flatnonzero(train_counts == 0).tolist(),
        "scoring_empty_classes": np.flatnonzero(scoring_counts == 0).tolist(),
        "train_min_class_support": int(train_counts.min()),
        "scoring_min_class_support": int(scoring_counts.min()),
        "train_rows": int(train.size),
        "scoring_rows": int(scoring.size),
    }


def a3_threshold_pass(*, ci_low: float, observed: float, null_q95: float) -> bool:
    return bool(ci_low > 1.0 / 8.0 and observed > null_q95)


def scorer_threshold_pass(*, ci_low: float, macro_subject_r1: float) -> bool:
    return bool(ci_low > 0.0 and macro_subject_r1 >= 0.80)


def summarize_a_a3_positive_control(
    *,
    task: str,
    truth: Sequence[int],
    predictions: Sequence[int],
    subject_ids: Sequence[str],
) -> dict[str, Any]:
    y_true = np.asarray(truth, dtype=np.int64)
    y_pred = np.asarray(predictions, dtype=np.int64)
    subjects = np.asarray(subject_ids)
    if y_true.shape != y_pred.shape or y_true.shape != subjects.shape or y_true.size == 0:
        raise ValueError("A-A3 positive-control OOF rows are not aligned")
    subject_values = {
        subject: balanced_recall(y_true[subjects == subject], y_pred[subjects == subject])
        for subject in sorted(set(subjects.tolist()))
    }
    bootstrap = cluster_bootstrap(
        subject_values,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(SEEDS[0], "D42", "A-A3", task),
    )
    null = permutation_null_fixed_predictions(
        y_true,
        y_pred,
        subjects,
        n_resamples=DEFAULT_ADMISSION_CONFIG.permutation_resamples,
        seed=SEEDS[0],
    )
    observed = balanced_recall(y_true, y_pred)
    passed = a3_threshold_pass(
        ci_low=bootstrap["ci95"][0], observed=observed, null_q95=null["q95"]
    )
    return {
        "role": "oracle_construct_validity_positive_control_not_eeg_evidence",
        "joint_oof_rows": int(y_true.size),
        "balanced_accuracy": observed,
        "chance": 1.0 / 8.0,
        "subject_cluster_bootstrap": bootstrap,
        "within_subject_permutation_null": null,
        "per_subject_recall": subject_values,
        "pass": bool(passed),
    }


def ridge_top1_positions(
    model: Mapping[str, np.ndarray],
    x: np.ndarray,
    vocabulary: np.ndarray,
    *,
    device: str,
    batch_size: int = 8192,
) -> np.ndarray:
    values = np.asarray(x, dtype=np.float32)
    vocab = np.asarray(vocabulary, dtype=np.float32)
    if values.ndim != 2 or vocab.ndim != 2 or vocab.shape[1] != 384:
        raise ValueError("ridge top1 inputs violate scorer shape contract")
    weights = torch.as_tensor(model["weights"], dtype=torch.float32, device=device)
    intercept = torch.as_tensor(model["intercept"], dtype=torch.float32, device=device)
    vocab_tensor = torch.as_tensor(vocab, dtype=torch.float32, device=device)
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(values), batch_size):
            batch = torch.as_tensor(values[start : start + batch_size], dtype=torch.float32, device=device)
            query = torch.nn.functional.normalize(batch @ weights + intercept, p=2, dim=1)
            outputs.append((query @ vocab_tensor.T).argmax(dim=1).cpu().numpy())
    return np.concatenate(outputs).astype(np.int64) if outputs else np.empty(0, np.int64)


def summarize_scorer_positive_control(
    *,
    task: str,
    h_logp: Sequence[float],
    oracle_logp: Sequence[float],
    oracle_top1: Sequence[int],
    true_positions: Sequence[int],
    subject_ids: Sequence[str],
    row_vocabulary_contract: Mapping[str, bool],
) -> dict[str, Any]:
    h_values = np.asarray(h_logp, dtype=np.float64)
    oracle_values = np.asarray(oracle_logp, dtype=np.float64)
    top1 = np.asarray(oracle_top1, dtype=np.int64)
    truth = np.asarray(true_positions, dtype=np.int64)
    subjects = np.asarray(subject_ids)
    if not (
        h_values.shape == oracle_values.shape == top1.shape == truth.shape == subjects.shape
        and h_values.size > 0
    ):
        raise ValueError("scorer positive-control rows differ")
    if not np.isfinite(h_values).all() or not np.isfinite(oracle_values).all():
        raise ValueError("scorer positive-control log probabilities are nonfinite")
    differences = oracle_values - h_values
    subject_differences = {
        subject: float(differences[subjects == subject].mean())
        for subject in sorted(set(subjects.tolist()))
    }
    bootstrap = cluster_bootstrap(
        subject_differences,
        n_resamples=DEFAULT_ADMISSION_CONFIG.bootstrap_resamples,
        seed=stable_seed(SEEDS[0], "D42", "A-A1-scorer", task),
    )
    per_subject_r1 = {
        subject: float(np.mean(top1[subjects == subject] == truth[subjects == subject]))
        for subject in sorted(set(subjects.tolist()))
    }
    macro_subject_r1 = float(np.mean(list(per_subject_r1.values())))
    contract_pass = all(bool(value) for value in row_vocabulary_contract.values())
    passed = scorer_threshold_pass(
        ci_low=bootstrap["ci95"][0], macro_subject_r1=macro_subject_r1
    ) and contract_pass
    return {
        "role": "oracle_scorer_positive_control_not_eeg_evidence",
        "scoring_rows": int(h_values.size),
        "paired_oracle_minus_h_logp": bootstrap,
        "oracle_full_vocabulary_macro_subject_r_at_1": macro_subject_r1,
        "per_subject_r_at_1": per_subject_r1,
        "r_at_1_threshold": 0.80,
        "row_vocabulary_contract": dict(row_vocabulary_contract),
        "pass": bool(passed),
    }


def derive_existing_failure_summary(admitted_audit: Mapping[str, Any]) -> dict[str, Any]:
    """Copy/derive only admitted aggregate and subject-level failure evidence."""

    result: dict[str, Any] = {}
    for task in TASKS:
        task_result = admitted_audit["results"][task]
        result[task] = {}
        for basis in BASES:
            metrics = task_result["A-A1"][basis]["metrics"]
            u_oof = metrics["u_oof"]
            u_min = metrics["u_min"]
            u_oof_subjects = u_oof["subject_values"]
            u_min_subjects = u_min["subject_values"]
            subjects = sorted(set(u_oof_subjects).intersection(u_min_subjects))
            gap_subjects = {
                subject: float(u_oof_subjects[subject]) - float(u_min_subjects[subject])
                for subject in subjects
            }
            result[task][basis] = {
                "u_oof": dict(u_oof),
                "u_min": dict(u_min),
                "max_selection_gap": {
                    "definition": "u_oof_minus_u_min_equals_max_sham_minus_mean_shams",
                    "estimate": float(u_oof["estimate"]) - float(u_min["estimate"]),
                    "subject_values": gap_subjects,
                    "positive_subject_count": sum(value > 0.0 for value in gap_subjects.values()),
                },
                "single_sham_contrasts": {
                    name: dict(metrics[name])
                    for name in (
                        "real_minus_trial_shuffle",
                        "real_minus_within_trial_unit_assignment_shuffle",
                        "real_minus_channel_block_permutation",
                    )
                },
                "A-A2": dict(task_result["A-A2"][basis]),
                "A-A3": dict(task_result["A-A3"][basis]),
            }
    return {
        "source_outcome_unchanged": admitted_audit["completion_outcome"],
        "mechanism_claim": "forbidden_channel_sham_pattern_is_descriptive_only",
        "task_basis": result,
    }


def evaluate_completion(
    *,
    a3_results: Mapping[str, Mapping[str, Any]],
    scorer_results: Mapping[str, Mapping[str, Any]],
    fit_summaries: Sequence[Mapping[str, Any]],
    ledger_count: int,
    old_evidence_pass: bool,
    old_v5_revalidated: int,
    formal_output_pass: bool,
    outer_test_read_count: int,
    calibration_read_count: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    logistic = sum(row.get("fit_type") == "multinomial_logistic" for row in fit_summaries)
    ridge = sum(row.get("fit_type") == "ridge" for row in fit_summaries)
    if (logistic, ridge, len(fit_summaries), ledger_count) != (54, 4, 58, 58):
        reasons.append(
            f"FIT_OR_V5_COUNT_MISMATCH:logistic={logistic},ridge={ridge},fits={len(fit_summaries)},ledgers={ledger_count}"
        )
    if not old_evidence_pass or old_v5_revalidated != 639:
        reasons.append("OLD_A1_EVIDENCE_REVALIDATION_FAILED")
    for task in TASKS:
        if not a3_results[task]["pass"]:
            reasons.append(f"{task}:A-A3_POSITIVE_CONTROL_FAIL")
        if not scorer_results[task]["pass"]:
            scorer = scorer_results[task]
            subject_count = int(
                scorer.get("paired_oracle_minus_h_logp", {}).get("n_subjects", 0)
            )
            subject_contract = scorer.get("row_vocabulary_contract", {}).get(
                "subject_count_15", True
            )
            if not subject_contract:
                reasons.append(
                    f"{task}:A-A1_SCORER_SUBJECT_COUNT_{subject_count}_NOT_FROZEN_15"
                )
            else:
                reasons.append(f"{task}:A-A1_SCORER_POSITIVE_CONTROL_FAIL")
    if not formal_output_pass:
        reasons.append("FORMAL_OUTPUT_CONTRACT_FAILED")
    if outer_test_read_count != 0:
        reasons.append(f"OUTER_TEST_READ_COUNT={outer_test_read_count}")
    if calibration_read_count != 0:
        reasons.append(f"CALIBRATION_READ_COUNT={calibration_read_count}")
    return (
        ("PASS_A1_FAILURE_DIAGNOSIS", [])
        if not reasons
        else ("INVALID_A1_FAILURE_DIAGNOSIS", sorted(set(reasons)))
    )


def planned_state_transition(outcome: str) -> dict[str, Any]:
    if outcome == "PASS_A1_FAILURE_DIAGNOSIS":
        return {
            "diagnosis_status": "DONE",
            "route_primary": "NEGATIVE-DIAGNOSTIC",
            "route_backup": None,
            "route_locked": None,
            "recommended_next_task": "S0_A1_NEGATIVE_CONFIRMATION_FREEZE",
            "negative_confirmation_freeze_status": "READY",
            "negative_confirmation_run_status": "BLOCKED",
        }
    if outcome == "INVALID_A1_FAILURE_DIAGNOSIS":
        return {
            "diagnosis_status": "BLOCKED",
            "route_unchanged": True,
            "recommended_next_task": None,
            "author_review_blocker_required": True,
        }
    raise ValueError(f"unknown diagnosis outcome: {outcome}")


def formal_key_inventory(value: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    if isinstance(value, Mapping):
        for key, item in value.items():
            counts[str(key)] += 1
            counts.update(formal_key_inventory(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            counts.update(formal_key_inventory(item))
    return counts


def validate_aggregate_formal_output(value: Mapping[str, Any]) -> dict[str, Any]:
    inventory = formal_key_inventory(value)
    present = sorted(FORBIDDEN_FORMAL_KEYS.intersection(inventory))
    canonical = canonical_artifact(value)
    json.loads(canonical)
    return {
        "forbidden_keys_present": present,
        "canonical_json": True,
        "pass": not present,
    }
