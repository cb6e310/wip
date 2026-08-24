"""Pure contracts for the v3.24 R3 subject-balanced inner diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from data.a1_failure_diagnosis import sha256_file
from data.real_sham_r1_inner import (
    ARMS,
    FOLDS,
    METRICS,
    REGIMES,
    TASKS,
    paired_cross_recovery,
    summarize_subject_first,
)
from data.real_sham_r2_geometry import verify_immutable_parent_r0_r1


ALGORITHM_VERSION = "real-sham-r3-subject-balanced-v324-d110-d113-v1"
RUN_ID = "2026-08-24_005_v324_real_sham_r3_subject_balanced_inner"
TARGET = "Y0_RAW_MINILM"
BASIS = "B0_RAW_A1"
ALIGNMENT = "M0_STRICT_INDUCTIVE"
METHODS = ("P0_OBSERVATION_WEIGHTED", "P1_SUBJECT_ITEM_BALANCED")
BASELINE_METHOD = METHODS[0]
CANDIDATE_METHOD = METHODS[1]

EXPECTED_H_ONLY_FITS = 12
EXPECTED_EEG_PROBES = 48
EXPECTED_RIDGE_OPERATIONS = 60
EXPECTED_V5_LEDGERS = 60
EXPECTED_GROUP_SCOPES = 6

IMMUTABLE_R2_HASHES = {
    "artifacts/real_sham_r2_freeze.yaml": "2d8b8746ad68c9d5cb48566ec6f769d4ffa07f147ca8d4e108259a0974400bf0",
    "artifacts/real_sham_r2_geometry_contract.yaml": "cb28e85029ec01dff3961e101a42d00672155ac7258641a077bf4bd6cf6eee78",
    "04_results/diagnostics/real_sham_r2_geometry_inner.json": "6aca8e2be1e062092a3ca7a4133cacd179e0fd73926240bd48739aedaa51426b",
    "04_results/diagnostics/real_sham_r2_geometry_inner.md": "931091510f32059e6b199028eab6e8023960d74a093b8a09546925b709a60d55",
    "04_results/diagnostics/real_sham_r2_geometry_inner_run_ledger.jsonl.gz": "8e9ee515cfef330eba7d6f2d6caaa91ec4d4b140678c191e21f11597253fecd3",
    "04_results/diagnostics/real_sham_r2_geometry_inner_transform_ledger.jsonl.gz": "21d257d3002a4e3aff8198317bd2e25293eab3b2d8ec585b85acad42b951021b",
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_23_2026-08-23.md": "e8ce2b93f3cd3bc27232c0f98193c74528f3eb46ca56dc6f705f6a461fd92d63",
    "runs/research/2026-08-23_004_v323_real_sham_r2_geometry_freeze.md": "5750f3e26fe8105f127d84a50e5282a52afc2a53dfbe09dfc3fa18e71eab41b3",
    "02_code/src/data/real_sham_r2_geometry.py": "289ea36c28400c9e7c321e48fd0f02a9ef5a233f4e1e0f861235d2c6c229fac6",
    "02_code/scripts/run_real_sham_r2_geometry_inner.py": "99d392cff4b4320bb13ca0d6792215e62f55b1e413b84aea3c5d46841ed7f155",
    "02_code/tests/test_real_sham_r2_geometry.py": "61fcf2a5062c37345d704d333996fe66884d34b256cd2eacb8e8753e0c04bfa6",
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def verify_immutable_parent_r0_r1_r2(root: Path) -> dict[str, str]:
    observed = verify_immutable_parent_r0_r1(root)
    observed_r2 = {
        relative: sha256_file(root / relative) for relative in IMMUTABLE_R2_HASHES
    }
    if observed_r2 != IMMUTABLE_R2_HASHES:
        changed = {
            relative: {
                "expected": IMMUTABLE_R2_HASHES[relative],
                "observed": observed_r2[relative],
            }
            for relative in IMMUTABLE_R2_HASHES
            if observed_r2[relative] != IMMUTABLE_R2_HASHES[relative]
        }
        raise RuntimeError(
            f"STATE_SPEC_CONFLICT: immutable R2 artifacts changed: {changed}"
        )
    return {**observed, **observed_r2}


def subject_item_group_means(
    arms: Mapping[str, np.ndarray],
    fit_metadata: Sequence[Mapping[str, Any]],
    *,
    task: str,
    fold: str,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], dict[str, Any]]:
    """Average fit EEG within each subject/item group, with equal group rows."""

    if set(arms) != set(ARMS):
        raise ValueError("R3 grouping requires exactly the frozen four arms")
    matrices = {arm: np.asarray(arms[arm], dtype=np.float32) for arm in ARMS}
    shapes = {matrix.shape for matrix in matrices.values()}
    if len(shapes) != 1:
        raise ValueError("R3 four-arm fit capacities differ")
    shape = next(iter(shapes))
    if len(shape) != 2 or shape[0] != len(fit_metadata) or shape[1] != 840:
        raise ValueError("R3 grouping requires aligned 840D fit rows")
    if any(not np.isfinite(matrix).all() for matrix in matrices.values()):
        raise ValueError("R3 fit EEG must be finite; no grouping fallback is allowed")

    keyed: dict[tuple[str, str], list[int]] = {}
    observation_ids: list[str] = []
    for index, row in enumerate(fit_metadata):
        subject = str(row.get("subject_id", ""))
        item = str(row.get("item_id", ""))
        observation = str(row.get("observation_id", ""))
        if not subject or not item or not observation:
            raise ValueError("R3 fit grouping key or observation identity is empty")
        keyed.setdefault((subject, item), []).append(index)
        observation_ids.append(observation)
    keys = sorted(keyed)
    if not keys:
        raise ValueError("R3 fit grouping produced no groups")

    grouped: dict[str, np.ndarray] = {}
    for arm in ARMS:
        grouped[arm] = np.stack(
            [matrices[arm][keyed[key]].astype(np.float64).mean(axis=0) for key in keys]
        ).astype(np.float32)
        if not np.isfinite(grouped[arm]).all():
            raise ValueError("R3 grouped EEG is nonfinite")

    group_metadata = [dict(fit_metadata[keyed[key][0]]) for key in keys]
    sizes = np.asarray([len(keyed[key]) for key in keys], dtype=np.int64)
    memberships = [
        {
            "subject_id": key[0],
            "item_id": key[1],
            "observation_ids": sorted(
                str(fit_metadata[index]["observation_id"]) for index in keyed[key]
            ),
        }
        for key in keys
    ]
    summary = {
        "task": task,
        "fold": fold,
        "source_scope": "fit_rows_only",
        "grouping_key": ["subject_id", "item_id"],
        "aggregate": "arithmetic_mean_of_finite_EEG_rows_per_group",
        "equal_group_weight": True,
        "seen_cross_rows_used_for_grouping_weight_vocabulary_or_threshold": False,
        "subject_id_input_to_probe": False,
        "fit_observation_count": int(shape[0]),
        "group_count": int(len(keys)),
        "group_size": {
            "minimum": int(sizes.min()),
            "maximum": int(sizes.max()),
            "mean": float(sizes.mean()),
            "median": float(np.median(sizes)),
            "q25": float(np.quantile(sizes, 0.25)),
            "q75": float(np.quantile(sizes, 0.75)),
            "singleton_count": int(np.sum(sizes == 1)),
        },
        "fit_observation_ids_sha256": _canonical_hash(sorted(observation_ids)),
        "subject_item_group_keys_sha256": _canonical_hash(keys),
        "group_membership_sha256": _canonical_hash(memberships),
        "grouped_eeg_sha256": {arm: _array_hash(grouped[arm]) for arm in ARMS},
        "same_groups_all_four_arms": True,
    }
    return grouped, group_metadata, summary


def validate_group_summaries(
    rows: Sequence[Mapping[str, Any]], *, expected_count: int = EXPECTED_GROUP_SCOPES
) -> None:
    if len(rows) != expected_count:
        raise ValueError(f"R3 group scope count {len(rows)} != {expected_count}")
    scopes = {(row.get("task"), row.get("fold")) for row in rows}
    if len(scopes) != expected_count:
        raise ValueError("R3 group scopes are not unique")
    for row in rows:
        if row.get("source_scope") != "fit_rows_only":
            raise ValueError("R3 group source escaped fit rows")
        if row.get("grouping_key") != ["subject_id", "item_id"]:
            raise ValueError("R3 grouping key changed")
        required_true = ("equal_group_weight", "same_groups_all_four_arms")
        if any(row.get(key) is not True for key in required_true):
            raise ValueError("R3 equal-weight/four-arm grouping contract failed")
        required_false = (
            "seen_cross_rows_used_for_grouping_weight_vocabulary_or_threshold",
            "subject_id_input_to_probe",
        )
        if any(row.get(key) is not False for key in required_false):
            raise ValueError("R3 forbidden scoring-row or subject input use detected")
        if int(row.get("group_count", 0)) < 1:
            raise ValueError("R3 group count is empty")
        if int(row.get("fit_observation_count", 0)) < int(row["group_count"]):
            raise ValueError("R3 group count exceeds fit observations")
        hashes = (
            row.get("fit_observation_ids_sha256"),
            row.get("subject_item_group_keys_sha256"),
            row.get("group_membership_sha256"),
        )
        if any(not isinstance(value, str) or len(value) != 64 for value in hashes):
            raise ValueError("R3 group identity hash missing")
        eeg_hashes = row.get("grouped_eeg_sha256", {})
        if set(eeg_hashes) != set(ARMS) or any(len(value) != 64 for value in eeg_hashes.values()):
            raise ValueError("R3 grouped EEG hashes are incomplete")


def evaluate_r3_outcome(
    results: Mapping[str, Any], *, contract_pass: bool
) -> tuple[str, list[str], list[str]]:
    if not contract_pass:
        return (
            "INVALID_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC",
            [],
            ["SCOPE_GROUP_LEDGER_READ_COUNT_TEST_OR_HASH_CONTRACT_FAILED"],
        )
    passing_tasks: list[str] = []
    for task in TASKS:
        baseline = results[task][BASELINE_METHOD]["cross"]
        candidate = results[task][CANDIDATE_METHOD]
        recovery = paired_cross_recovery(
            candidate["cross"], baseline, task=task, candidate_id=CANDIDATE_METHOD
        )
        passed = (
            candidate["cross"]["family_detected"]
            and recovery["ci95"][0] > 0.0
            and recovery["positive_subject_count"] >= 10
        )
        candidate["cross_recovery"] = recovery
        candidate["recovery_pass"] = bool(passed)
        results[task][BASELINE_METHOD]["cross_recovery"] = None
        results[task][BASELINE_METHOD]["recovery_pass"] = False
        if passed:
            passing_tasks.append(task)
    if passing_tasks:
        return "PASS_R3_SUBJECT_BALANCED_INNER", passing_tasks, []
    return "FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC", [], []


__all__ = [
    "ALIGNMENT",
    "ALGORITHM_VERSION",
    "ARMS",
    "BASELINE_METHOD",
    "BASIS",
    "CANDIDATE_METHOD",
    "EXPECTED_EEG_PROBES",
    "EXPECTED_GROUP_SCOPES",
    "EXPECTED_H_ONLY_FITS",
    "EXPECTED_RIDGE_OPERATIONS",
    "EXPECTED_V5_LEDGERS",
    "FOLDS",
    "METRICS",
    "METHODS",
    "REGIMES",
    "RUN_ID",
    "TARGET",
    "TASKS",
    "evaluate_r3_outcome",
    "subject_item_group_means",
    "summarize_subject_first",
    "validate_group_summaries",
    "verify_immutable_parent_r0_r1_r2",
]
