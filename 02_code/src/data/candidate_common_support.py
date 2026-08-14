"""Derive the SPEC v3.11 N=10 common-support scoring view.

This module is deliberately JSON-only.  It consumes the three admitted v3.10
candidate artifacts and never imports or invokes text encoders, EEG readers,
or candidate construction code paths that recompute scientific quantities.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from data.candidates import validate_candidate_artifacts
from data.joint_split import canonical_json_bytes, sha256_bytes


ALGORITHM_VERSION = "zuco2-n10-common-support-v311-o3-v1"
DEFAULT_RUN_ID = "2026-08-14_021_v311_n10_common_support"
DEFAULT_SEED = 20260813
REPEATS = 5
NEGATIVE_COUNT = 9
EXCLUSION_REASON = "LEGAL_NEGATIVES_LT_9"
BASE_FILE_SHA256 = {
    "candidate_lists": "51130ffc216a1f0bf50a9eeec42136555ab98ee110f3aaa265de54c3a004115a",
    "paired_verification_pairs": "bc37630ea3c6c870d4388ac0c16582f742e6751d533e3656a284304d09e3ec5c",
    "candidate_feasibility": "8f478fddc78ccb46df2c1a75945a3f90ec89f7c58ca456172a4874bef75f7960",
}
EXPECTED_COUNTS = {
    ("outer_test", "task1_nr"): (306, 349),
    ("outer_test", "task2_tsr"): (359, 390),
    ("inner_validation", "task1_nr"): (7553, 8376),
    ("inner_validation", "task2_tsr"): (8843, 9360),
}
EXPECTED_FAILURE_STAGES = {"length": 1402, "cosine": 0, "H": 12}


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _without_integrity(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("integrity", None)
    return result


def _verify_integrity(value: Mapping[str, Any], label: str) -> None:
    block = value.get("integrity")
    if not isinstance(block, Mapping):
        raise ValueError(f"{label}: missing integrity block")
    payload = canonical_json_bytes(_without_integrity(value))
    if block.get("canonical_payload_sha256") != sha256_bytes(payload):
        raise ValueError(f"{label}: canonical SHA256 mismatch")
    if block.get("canonical_payload_bytes") != len(payload):
        raise ValueError(f"{label}: canonical byte count mismatch")


def _add_integrity(value: dict[str, Any], scope: str) -> None:
    payload = canonical_json_bytes(value)
    value["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": scope,
    }


def _json_file(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    return value


def load_verified_base_triplet(
    candidate_path: str | Path,
    pair_path: str | Path,
    audit_path: str | Path,
    *,
    expected_file_sha256: Mapping[str, str] = BASE_FILE_SHA256,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    """Load and fully admit the immutable v3.10 triplet."""

    paths = {
        "candidate_lists": Path(candidate_path),
        "paired_verification_pairs": Path(pair_path),
        "candidate_feasibility": Path(audit_path),
    }
    actual = {name: file_sha256(path) for name, path in paths.items()}
    for name, expected in expected_file_sha256.items():
        if actual.get(name) != expected:
            raise ValueError(
                f"STATE_SPEC_CONFLICT: {name} physical SHA256 mismatch: "
                f"expected={expected} actual={actual.get(name)}"
            )
    candidates = _json_file(paths["candidate_lists"])
    pairs = _json_file(paths["paired_verification_pairs"])
    audit = _json_file(paths["candidate_feasibility"])
    for label, value in (("candidate_lists", candidates), ("paired_pairs", pairs), ("feasibility", audit)):
        _verify_integrity(value, label)
    errors = validate_candidate_artifacts(candidates, pairs, audit)
    if errors:
        raise ValueError(f"STATE_SPEC_CONFLICT: invalid base triplet: {errors}")
    if pairs.get("candidate_lists_file_sha256") != actual["candidate_lists"]:
        raise ValueError("STATE_SPEC_CONFLICT: base pair file binding mismatch")
    if pairs.get("candidate_lists_canonical_payload_sha256") != candidates["integrity"][
        "canonical_payload_sha256"
    ]:
        raise ValueError("STATE_SPEC_CONFLICT: base pair canonical binding mismatch")
    if not (candidates.get("provenance") == pairs.get("provenance") == audit.get("provenance")):
        raise ValueError("STATE_SPEC_CONFLICT: base provenance differs across triplet")
    return candidates, pairs, audit, actual


def _distribution(values: Sequence[int]) -> dict[str, float | int]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"count": 0, "min": 0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0}
    n = len(ordered)
    median = float(ordered[n // 2]) if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0
    return {
        "count": n,
        "min": ordered[0],
        "q1": float(ordered[(n - 1) // 4]),
        "median": median,
        "q3": float(ordered[(3 * (n - 1)) // 4]),
        "max": ordered[-1],
    }


def _document_id(stimulus_id: str) -> str:
    parts = stimulus_id.split("|")
    if len(parts) < 4:
        raise ValueError(f"malformed source-slot identity: {stimulus_id}")
    return "|".join(parts[:3])


def _population_stats(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    material = list(rows)
    documents = Counter(str(row["document_id"]) for row in material)
    folds = Counter(str(row["text_fold_id"]) for row in material)
    return {
        "target_occurrence_count": len(material),
        "token_length_distribution": _distribution([int(row["token_length"]) for row in material]),
        "unique_document_count": len(documents),
        "document_target_counts": dict(sorted(documents.items())),
        "text_fold_target_counts": dict(sorted(folds.items())),
    }


def _scope_identity(scope: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "task",
        "scope_type",
        "scope_id",
        "outer_cell_id",
        "outer_subject_fold",
        "outer_text_fold",
        "inner_text_fold",
        "reuse_outer_subject_folds",
        "reuse_inner_subject_folds",
    )
    return {key: copy.deepcopy(scope[key]) for key in keys if key in scope}


def _text_fold_id(scope: Mapping[str, Any]) -> str:
    if scope["scope_type"] == "outer_test":
        return f"outer_t{scope['outer_text_fold']}"
    return f"outer_{scope['outer_cell_id']}|inner_t{scope['inner_text_fold']}"


def _failure_stage(counts: Mapping[str, Any]) -> str:
    if int(counts["length_pass"]) < NEGATIVE_COUNT:
        return "length"
    if int(counts["cosine_pass"]) < NEGATIVE_COUNT:
        return "cosine"
    if int(counts["h_full_pass"]) < NEGATIVE_COUNT:
        return "H"
    raise ValueError("ineligible target does not transition below nine at a frozen filter stage")


def _shared(
    method: str,
    config: Mapping[str, Any],
    provenance: Mapping[str, Any],
    run_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "dataset": "zuco_2_0",
        "seed": DEFAULT_SEED,
        "method": method,
        "algorithm_version": ALGORITHM_VERSION,
        "config": dict(config),
        "config_hash": sha256_bytes(canonical_json_bytes(config)),
        "provenance": copy.deepcopy(provenance),
        "status": "PASS",
        "completion_outcome": "PASS_N10_COMMON_SUPPORT",
    }


def _minimal_base_checks(
    candidates: Mapping[str, Any], pairs: Mapping[str, Any], audit: Mapping[str, Any]
) -> None:
    if candidates.get("dataset") != "zuco_2_0" or candidates.get("seed") != DEFAULT_SEED:
        raise ValueError("base candidate dataset/seed mismatch")
    if not (candidates.get("provenance") == pairs.get("provenance") == audit.get("provenance")):
        raise ValueError("base provenance differs")
    if len(candidates.get("stimuli", [])) == 0:
        raise ValueError("base stimuli are empty")
    pair_keys = {(s["task"], s["scope_type"], s["scope_id"]) for s in pairs.get("scopes", [])}
    audit_keys = {(s["task"], s["scope_type"], s["scope_id"]) for s in audit.get("scopes", [])}
    candidate_keys = {(s["task"], s["scope_type"], s["scope_id"]) for s in candidates.get("scopes", [])}
    if not candidate_keys or candidate_keys != pair_keys or candidate_keys != audit_keys:
        raise ValueError("base scope identities differ")


def derive_common_support(
    candidates: Mapping[str, Any],
    pairs: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    base_file_hashes: Mapping[str, str],
    run_id: str = DEFAULT_RUN_ID,
    enforce_frozen_counts: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Purely derive the N=10 scoring view from existing JSON ledgers."""

    _minimal_base_checks(candidates, pairs, audit)
    config = {
        "algorithm_version": ALGORITHM_VERSION,
        "eligibility": "legal_count >= 9 within each frozen task-local scope",
        "n": 10,
        "negative_count": NEGATIVE_COUNT,
        "repeats": REPEATS,
        "auroc": "one positive plus first negative from the same N10 prefix",
        "auprc": "one positive plus the same nine negatives from the N10 prefix",
        "sampling": "no resampling; first nine of admitted maximal ordering",
        "spec": "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_11_2026-08-14.md#O.3",
    }
    provenance = {
        "base_run_id": candidates.get("run_id"),
        "base_file_sha256": dict(sorted(base_file_hashes.items())),
        "base_canonical_payload_sha256": {
            "candidate_lists": candidates["integrity"]["canonical_payload_sha256"],
            "paired_verification_pairs": pairs["integrity"]["canonical_payload_sha256"],
            "candidate_feasibility": audit["integrity"]["canonical_payload_sha256"],
        },
        "base_scientific_provenance": copy.deepcopy(candidates["provenance"]),
        "source_quantities_recomputed": [],
        "roamm_paths_read": [],
    }
    # Base target/negative identities are positional indices into this immutable
    # table, so its admitted order is itself part of the frozen identity.
    stimulus_rows = copy.deepcopy(candidates["stimuli"])
    by_index = dict(enumerate(stimulus_rows))
    audit_scopes = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in audit["scopes"]
    }
    output_scopes: list[dict[str, Any]] = []
    pair_scopes: list[dict[str, Any]] = []
    audit_scope_rows: list[dict[str, Any]] = []
    population_rows: list[dict[str, Any]] = []
    failure_counts: Counter[str] = Counter()
    totals: Counter[tuple[str, str, str]] = Counter()

    ordered_scopes = sorted(
        candidates["scopes"], key=lambda row: (row["task"], row["scope_type"], row["scope_id"])
    )
    for scope in ordered_scopes:
        key = (scope["task"], scope["scope_type"], scope["scope_id"])
        base_audit_scope = audit_scopes[key]
        audit_targets = {int(row["target_index"]): row for row in base_audit_scope["targets"]}
        candidate_targets: list[dict[str, Any]] = []
        paired_targets: list[dict[str, Any]] = []
        target_audits: list[dict[str, Any]] = []
        eligible_count = 0
        text_fold_id = _text_fold_id(scope)
        for target in sorted(scope["targets"], key=lambda row: int(row["target_index"])):
            target_index = int(target["target_index"])
            stimulus = by_index[target_index]
            source_audit = audit_targets[target_index]
            legal_count = int(target["legal_count"])
            if legal_count != int(source_audit["counts"]["legal_count"]):
                raise ValueError(f"{key}/{target_index}: legal_count differs from base audit")
            eligible = legal_count >= NEGATIVE_COUNT
            reason = None if eligible else EXCLUSION_REASON
            repeats: list[dict[str, Any]] = []
            pair_repeats: list[dict[str, Any]] = []
            ordered_repeats = sorted(target["repeats"], key=lambda row: int(row["repeat"]))
            if len(ordered_repeats) != REPEATS:
                raise ValueError(f"{key}/{target_index}: expected five repeats")
            for repeat in ordered_repeats:
                ordering = list(repeat["maximal_legal_negative_indices"])
                n10 = repeat["n_lists"]["10"]
                if len(ordering) != legal_count or len(ordering) != len(set(ordering)):
                    raise ValueError(f"{key}/{target_index}: malformed maximal ordering")
                if eligible:
                    negative_indices = ordering[:NEGATIVE_COUNT]
                    target_position = n10["target_position"]
                    if not n10["available"] or n10["negative_prefix_length"] != NEGATIVE_COUNT:
                        raise ValueError(f"{key}/{target_index}: base N10 availability mismatch")
                    if not isinstance(target_position, int) or not 0 <= target_position < 10:
                        raise ValueError(f"{key}/{target_index}: base target position mismatch")
                    if target_index in negative_indices or len(set(negative_indices)) != NEGATIVE_COUNT:
                        raise ValueError(f"{key}/{target_index}: invalid N10 prefix")
                else:
                    negative_indices = []
                    target_position = None
                    if n10["available"] or n10["target_position"] is not None:
                        raise ValueError(f"{key}/{target_index}: base ineligible N10 mismatch")
                repeat_id = int(repeat["repeat"])
                repeats.append(
                    {
                        "repeat": repeat_id,
                        "available": eligible,
                        "target_position": target_position,
                        "negative_indices": negative_indices,
                        "derived_from": "base_maximal_legal_negative_indices_prefix_9",
                    }
                )
                pair_repeats.append(
                    {
                        "repeat": repeat_id,
                        "available": eligible,
                        "auroc_1_to_1": {
                            "positive_index": target_index if eligible else None,
                            "negative_index": negative_indices[0] if eligible else None,
                            "derived_from": "n10_common_support_prefix_1",
                        },
                        "auprc_1_to_9": {
                            "positive_index": target_index if eligible else None,
                            "negative_indices": negative_indices,
                            "positive_prevalence": 0.1 if eligible else None,
                            "derived_from": "same_n10_common_support_prefix_9",
                        },
                    }
                )
            counts = copy.deepcopy(source_audit["counts"])
            exclusions = copy.deepcopy(source_audit["sequential_exclusions"])
            candidate_targets.append(
                {
                    "target_index": target_index,
                    "legal_count": legal_count,
                    "eligible": eligible,
                    "exclusion_reason": reason,
                    "sequential_counts": counts,
                    "repeats": repeats,
                }
            )
            paired_targets.append(
                {
                    "target_index": target_index,
                    "eligible": eligible,
                    "exclusion_reason": reason,
                    "repeats": pair_repeats,
                }
            )
            stage = None if eligible else _failure_stage(counts)
            if stage is not None:
                failure_counts[stage] += 1
            if eligible:
                eligible_count += 1
            totals[(scope["scope_type"], scope["task"], "eligible")] += int(eligible)
            totals[(scope["scope_type"], scope["task"], "total")] += 1
            row = {
                "target_index": target_index,
                "stimulus_id": stimulus["stimulus_id"],
                "exact_text_sha256": stimulus["exact_text_sha256"],
                "token_length": int(stimulus["token_length"]),
                "document_id": _document_id(stimulus["stimulus_id"]),
                "text_fold_id": text_fold_id,
                "eligible": eligible,
                "exclusion_reason": reason,
                "failure_stage": stage,
                "counts": counts,
                "sequential_exclusions": exclusions,
            }
            population_rows.append(row)
            target_audits.append(row)
        identity = _scope_identity(scope)
        output_scopes.append(
            {
                **identity,
                "pool_stimulus_indices": sorted(int(value) for value in scope["pool_stimulus_indices"]),
                "target_count": len(candidate_targets),
                "eligible_target_count": eligible_count,
                "excluded_target_count": len(candidate_targets) - eligible_count,
                "targets": candidate_targets,
            }
        )
        pair_scopes.append(
            {
                **identity,
                "target_count": len(paired_targets),
                "eligible_target_count": eligible_count,
                "targets": paired_targets,
            }
        )
        total = len(target_audits)
        audit_scope_rows.append(
            {
                **identity,
                "eligible_target_count": eligible_count,
                "total_target_count": total,
                "excluded_target_count": total - eligible_count,
                "coverage": eligible_count / total,
                "targets": target_audits,
            }
        )

    def summary(scope_type: str | None = None, task: str | None = None) -> dict[str, Any]:
        selected = [
            row for row in audit_scope_rows
            if (scope_type is None or row["scope_type"] == scope_type)
            and (task is None or row["task"] == task)
        ]
        eligible = sum(int(row["eligible_target_count"]) for row in selected)
        total = sum(int(row["total_target_count"]) for row in selected)
        return {
            "eligible": eligible,
            "total": total,
            "excluded": total - eligible,
            "coverage": eligible / total if total else 0.0,
            "scope_count": len(selected),
            "minimum_scope_coverage": min((float(row["coverage"]) for row in selected), default=0.0),
        }

    count_summary = {
        "outer": {
            "task1_nr": summary("outer_test", "task1_nr"),
            "task2_tsr": summary("outer_test", "task2_tsr"),
            "total": summary("outer_test"),
        },
        "inner": {
            "task1_nr": summary("inner_validation", "task1_nr"),
            "task2_tsr": summary("inner_validation", "task2_tsr"),
            "total": summary("inner_validation"),
        },
        "tasks": {"task1_nr": summary(task="task1_nr"), "task2_tsr": summary(task="task2_tsr")},
        "overall": summary(),
    }
    if enforce_frozen_counts:
        for (scope_type, task), expected in EXPECTED_COUNTS.items():
            observed = summary(scope_type, task)
            if (observed["eligible"], observed["total"]) != expected:
                raise ValueError(
                    f"STATE_SPEC_CONFLICT: frozen count mismatch {scope_type}/{task}: "
                    f"expected={expected} observed={(observed['eligible'], observed['total'])}"
                )
        observed_failure_stages = {
            key: int(failure_counts.get(key, 0)) for key in ("length", "cosine", "H")
        }
        if observed_failure_stages != EXPECTED_FAILURE_STAGES:
            raise ValueError(
                f"STATE_SPEC_CONFLICT: failure-stage mismatch expected={EXPECTED_FAILURE_STAGES} "
                f"observed={observed_failure_stages}"
            )
        if count_summary["outer"]["total"]["minimum_scope_coverage"] < (6 / 7):
            raise ValueError("STATE_SPEC_CONFLICT: outer per-scope coverage below 85.71%")
        # Frozen display minimum 82.80% is the exact observed ratio 77/93;
        # compare ratios, never the rounded display percentage.
        if count_summary["inner"]["total"]["minimum_scope_coverage"] < (77 / 93):
            raise ValueError("STATE_SPEC_CONFLICT: inner per-scope coverage below 82.80%")

    common = _shared(
        "ZuCo2-N10-common-support-scoring-view", config, provenance, run_id
    )
    candidate_output = {
        **common,
        "identity_encoding": copy.deepcopy(candidates.get("identity_encoding")),
        "stimuli": stimulus_rows,
        "scopes": output_scopes,
        "assertions": {
            "scoring_only": True,
            "training_records_removed": 0,
            "all_excluded_targets_retained": True,
            "source_quantities_recomputed": [],
            "contains_no_eeg_or_model_outputs": True,
        },
    }
    _add_integrity(candidate_output, "canonical JSON N10 common-support candidate view without integrity")
    candidate_file_payload = canonical_json_bytes(candidate_output) + b"\n"

    pair_output = {
        **_shared("ZuCo2-N10-common-support-paired-scoring-view", config, provenance, run_id),
        "candidate_lists_canonical_payload_sha256": candidate_output["integrity"][
            "canonical_payload_sha256"
        ],
        "candidate_lists_file_sha256": sha256_bytes(candidate_file_payload),
        "scopes": pair_scopes,
        "assertions": {
            "auroc_uses_first_negative": True,
            "auprc_uses_same_nine_negatives": True,
            "auprc_positive_prevalence": 0.1,
            "scoring_only": True,
            "training_records_removed": 0,
        },
    }
    _add_integrity(pair_output, "canonical JSON N10 paired scoring view without integrity")
    pair_file_payload = canonical_json_bytes(pair_output) + b"\n"

    eligible_rows = [row for row in population_rows if row["eligible"]]
    excluded_rows = [row for row in population_rows if not row["eligible"]]
    audit_output = {
        **_shared("ZuCo2-N10-common-support-audit", config, provenance, run_id),
        "claim_population": "candidate-common-support sentences",
        "count_summary": count_summary,
        "failure_stage_counts": {key: int(failure_counts.get(key, 0)) for key in ("length", "cosine", "H")},
        "population_diagnostics": {
            "included": _population_stats(eligible_rows),
            "excluded": _population_stats(excluded_rows),
        },
        "scopes": audit_scope_rows,
        "new_artifact_bindings": {
            "candidate_lists_n10_common_support": {
                "canonical_payload_sha256": candidate_output["integrity"]["canonical_payload_sha256"],
                "file_sha256": sha256_bytes(candidate_file_payload),
            },
            "paired_verification_pairs_n10": {
                "canonical_payload_sha256": pair_output["integrity"]["canonical_payload_sha256"],
                "file_sha256": sha256_bytes(pair_file_payload),
            },
            "self_hash_location": "integrity.canonical_payload_sha256; physical file SHA256 is reported by writer",
        },
        "assertions": {
            "scoring_only": True,
            "training_records_removed": 0,
            "all_excluded_targets_retained": True,
            "excluded_reason": EXCLUSION_REASON,
            "base_candidate_ordering_unchanged": True,
            "tokenizer_or_encoder_rerun": False,
            "eeg_read": False,
            "roamm_read": False,
        },
    }
    _add_integrity(audit_output, "canonical JSON N10 common-support audit without integrity")
    errors = validate_common_support(candidate_output, pair_output, audit_output, enforce_frozen_counts=enforce_frozen_counts)
    if errors:
        raise AssertionError(f"derived common-support self-validation failed: {errors}")
    return candidate_output, pair_output, audit_output


def validate_common_support(
    candidates: Mapping[str, Any],
    pairs: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    enforce_frozen_counts: bool = True,
) -> list[str]:
    errors: list[str] = []
    try:
        for label, value in (("candidates", candidates), ("pairs", pairs), ("audit", audit)):
            _verify_integrity(value, label)
            if value.get("status") != "PASS" or value.get("completion_outcome") != "PASS_N10_COMMON_SUPPORT":
                raise ValueError(f"{label}: status/outcome mismatch")
            if value.get("config_hash") != sha256_bytes(canonical_json_bytes(value["config"])):
                raise ValueError(f"{label}: config hash mismatch")
        if not (candidates["config"] == pairs["config"] == audit["config"]):
            raise ValueError("derived config differs across triplet")
        if not (candidates["provenance"] == pairs["provenance"] == audit["provenance"]):
            raise ValueError("derived provenance differs across triplet")
        pair_scope_map = {(s["task"], s["scope_type"], s["scope_id"]): s for s in pairs["scopes"]}
        audit_scope_map = {(s["task"], s["scope_type"], s["scope_id"]): s for s in audit["scopes"]}
        excluded = 0
        total = 0
        for scope in candidates["scopes"]:
            key = (scope["task"], scope["scope_type"], scope["scope_id"])
            paired_targets = {int(t["target_index"]): t for t in pair_scope_map[key]["targets"]}
            audit_targets = {int(t["target_index"]): t for t in audit_scope_map[key]["targets"]}
            if len(scope["targets"]) != scope["target_count"]:
                raise ValueError(f"{key}: target count mismatch")
            for target in scope["targets"]:
                total += 1
                target_index = int(target["target_index"])
                eligible = bool(target["eligible"])
                if eligible != (int(target["legal_count"]) >= NEGATIVE_COUNT):
                    raise ValueError(f"{key}/{target_index}: eligibility mismatch")
                if not eligible:
                    excluded += 1
                    if target["exclusion_reason"] != EXCLUSION_REASON:
                        raise ValueError(f"{key}/{target_index}: exclusion reason mismatch")
                if len(target["repeats"]) != REPEATS:
                    raise ValueError(f"{key}/{target_index}: repeat count mismatch")
                pair_target = paired_targets[target_index]
                if audit_targets[target_index]["eligible"] != eligible or pair_target["eligible"] != eligible:
                    raise ValueError(f"{key}/{target_index}: ledger eligibility differs")
                for row, paired in zip(target["repeats"], pair_target["repeats"], strict=True):
                    negatives = row["negative_indices"]
                    if eligible:
                        if len(negatives) != NEGATIVE_COUNT or len(set(negatives)) != NEGATIVE_COUNT:
                            raise ValueError(f"{key}/{target_index}: N10 negative count mismatch")
                        if paired["auroc_1_to_1"]["negative_index"] != negatives[0]:
                            raise ValueError(f"{key}/{target_index}: AUROC mismatch")
                        if paired["auprc_1_to_9"]["negative_indices"] != negatives:
                            raise ValueError(f"{key}/{target_index}: AUPRC mismatch")
                        if not math.isclose(paired["auprc_1_to_9"]["positive_prevalence"], 0.1):
                            raise ValueError(f"{key}/{target_index}: prevalence mismatch")
                    elif negatives or row["target_position"] is not None:
                        raise ValueError(f"{key}/{target_index}: excluded scoring material present")
        summary = audit["count_summary"]["overall"]
        if total != int(summary["total"]) or excluded != int(summary["excluded"]):
            raise ValueError("overall ledger count mismatch")
        if enforce_frozen_counts and (summary["eligible"], summary["total"], summary["excluded"]) != (17061, 18475, 1414):
            raise ValueError("frozen overall count mismatch")
        if candidates["assertions"]["training_records_removed"] != 0 or audit["assertions"]["training_records_removed"] != 0:
            raise ValueError("training records removed must be zero")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def canonical_triplet_bytes(values: Sequence[Mapping[str, Any]]) -> tuple[bytes, bytes, bytes]:
    if len(values) != 3:
        raise ValueError("triplet must contain exactly three artifacts")
    return tuple(canonical_json_bytes(value) + b"\n" for value in values)  # type: ignore[return-value]


def atomic_write_json(value: Mapping[str, Any], path: str | Path) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def write_common_support_triplet(
    values: Sequence[Mapping[str, Any]],
    paths: Sequence[str | Path],
) -> dict[str, dict[str, Any]]:
    if len(values) != 3 or len(paths) != 3:
        raise ValueError("expected exactly three artifacts and paths")
    names = ("candidate_lists_n10_common_support", "paired_verification_pairs_n10", "audit")
    return {name: atomic_write_json(value, path) for name, value, path in zip(names, values, paths, strict=True)}


def reverse_scope_target_order(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a test-only order perturbation without changing index identities."""

    result = copy.deepcopy(value)
    result["scopes"] = list(reversed(result["scopes"]))
    for scope in result["scopes"]:
        scope["targets"] = list(reversed(scope["targets"]))
    return result
