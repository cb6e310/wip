"""Frozen ZuCo2 sentence-candidate construction from SPEC v3.10 D22-D24.

The pure builder consumes verified source-slot metadata, token lengths, frozen
text embeddings, exact H source identities, and explicit outer/inner scopes.
It performs no filesystem reads and accepts no EEG, outcome, or metric fields.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from data.joint_split import canonical_json_bytes, sha256_bytes


DEFAULT_SEED = 20260813
DEFAULT_REPEATS = 5
N_VALUES = (10, 50, 100, 200)
NEGATIVE_COUNTS = {10: 9, 50: 49, 100: 99, 200: 199}
COSINE_THRESHOLD = 0.9
ALGORITHM_VERSION = "zuco2-candidates-v310-d22-d24-v1"
EXPECTED_TASKS = ("task1_nr", "task2_tsr")
FROZEN_PROVENANCE = {
    "outer_file_sha256": "20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6",
    "outer_canonical_payload_sha256": "ee7e29e938fc778f26a15f14ff091fc75f9942181c1ad108bbad7eb4511d2b4f",
    "inner_file_sha256": "0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7",
    "inner_canonical_payload_sha256": "36e5b6c5b99fdf1182a198b65d0cfb00afc7d73414005b083d808f4b3db3db08",
    "inner_support_file_sha256": "536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564",
    "inner_support_canonical_payload_sha256": "d19d18d5d3604a3ed4b1e8551597996a26f3a7d9bf13f747c61006ebf72d62eb",
    "source_join_artifact_sha256": "eb960cd0bf2cb5016f33793813cb61fa2c77c9ce07e2037cff69b29c14c104c8",
    "h_artifact_sha256": "226f92e299633997fdb9469592f6f8a36fa6c728aa24d9a7d6cb9ded8fb2ae6b",
    "h_source_sha256": "e4aa7c8a6b2aabbb581ce9de3564347e69632c39694cbd13488523cb8ad3cfcd",
    "h_config_hash": "fa3accaaaaedeb173b5173d0e29d3f0c661dd876e70b5d6b0a365cace7a3c2fe",
    "encoder_artifact_sha256": "35e18392a285c8d09ba84a934e31dd327a18fa1a0c10a3bd8550f090cd496494",
    "encoder_implementation_sha256": "f7345b81483f77d569cb6147c8cf4eecab0df8caa39d006f04d098bdc786950f",
    "encoder_tokenizer_manifest_hash": "78a3daa92dcec076e80baaa628a6553bcbd0b431a214eb02d72c8b5672e69e09",
    "encoder_config_manifest_hash": "8049791e90383b0f56624a32a14852552e292bcb38ab18da1de533ad79629845",
    "encoder_model_manifest_hash": "c0577b9136351b1c12ba99a16f386d5c4c8c45e744941eaea15803880dd30e61",
    "encoder_scientific_config_hash": "0f2fb795c15c7ad7ee185f44509ec86eb912aaca6abf88b78fa1560179e412af",
}
FROZEN_SOURCE_JOIN_MAPPING = {
    "task1_nr": "97f3a0bd695d482ceff409b85414790c5f9877fcba28049572f354de61366f12",
    "task2_tsr": "7a3bc1cb3f41557b7f13cb76f44833de0f4b72726849024378ec0935e98a5060",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_INPUT_KEY_PARTS = (
    "eeg",
    "rawdata",
    "raw_data",
    "held_out_metric",
    "paper_metric",
    "retrieval_result",
    "gate_result",
    "outcome_value",
    "roamm",
    "ds007629",
)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_text_sha256(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("released text must be str")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _valid_sha(value: object) -> bool:
    return bool(_SHA256_RE.fullmatch(str(value)))


def _add_integrity(value: dict[str, Any], scope: str) -> None:
    payload = canonical_json_bytes(value)
    value["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": scope,
    }


def _verify_integrity(value: Mapping[str, Any], label: str) -> None:
    block = value.get("integrity")
    if not isinstance(block, Mapping):
        raise ValueError(f"{label}: missing integrity")
    payload = dict(value)
    payload.pop("integrity", None)
    encoded = canonical_json_bytes(payload)
    if block.get("canonical_payload_sha256") != sha256_bytes(encoded):
        raise ValueError(f"{label}: canonical payload SHA256 mismatch")
    if block.get("canonical_payload_bytes") != len(encoded):
        raise ValueError(f"{label}: canonical payload byte count mismatch")


def _verify_config_hash(value: Mapping[str, Any], label: str) -> None:
    config = value.get("config")
    if not isinstance(config, Mapping):
        raise ValueError(f"{label}: missing config")
    if value.get("config_hash") != sha256_bytes(canonical_json_bytes(config)):
        raise ValueError(f"{label}: config hash mismatch")


def length_is_legal(target_tokens: int, negative_tokens: int) -> bool:
    """Inclusive, integer-only 0.75-to-1.25 length rule."""

    if isinstance(target_tokens, bool) or isinstance(negative_tokens, bool):
        raise TypeError("token lengths must be positive integers")
    if not isinstance(target_tokens, int) or not isinstance(negative_tokens, int):
        raise TypeError("token lengths must be positive integers")
    if target_tokens <= 0 or negative_tokens <= 0:
        raise ValueError("token lengths must be positive")
    return 3 * target_tokens <= 4 * negative_tokens <= 5 * target_tokens


def cosine_is_legal(cosine: float) -> bool:
    value = float(cosine)
    if not math.isfinite(value):
        raise ValueError("cosine must be finite")
    return value <= COSINE_THRESHOLD


def hash_rank_key(
    *, seed: int, task: str, scope_id: str, target_id: str, repeat: int, negative_id: str
) -> tuple[bytes, str]:
    payload = f"{seed}|{task}|{scope_id}|{target_id}|{repeat}|{negative_id}"
    return hashlib.sha256(payload.encode("utf-8")).digest(), negative_id


def stable_target_position(
    *, seed: int, task: str, scope_id: str, target_id: str, repeat: int, n: int
) -> int:
    if n not in N_VALUES:
        raise ValueError(f"unsupported N: {n}")
    payload = f"{seed}|{task}|{scope_id}|{target_id}|{repeat}|N={n}|target_position"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest(), "big") % n


def _reject_forbidden_keys(value: Any, *, path: str = "input") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            folded = str(key).casefold()
            if folded == "roamm_paths_read" and child == []:
                continue
            if any(part in folded for part in _FORBIDDEN_INPUT_KEY_PARTS):
                raise ValueError(f"forbidden EEG/ROAMM/outcome field at {path}.{key}")
            _reject_forbidden_keys(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, path=f"{path}[{index}]")


def _validate_provenance(provenance: Mapping[str, Any]) -> None:
    required_hashes = (
        "outer_file_sha256",
        "outer_canonical_payload_sha256",
        "inner_file_sha256",
        "inner_canonical_payload_sha256",
        "inner_support_file_sha256",
        "inner_support_canonical_payload_sha256",
        "source_join_artifact_sha256",
        "released_text_manifest_sha256",
        "h_artifact_sha256",
        "h_source_sha256",
        "h_config_hash",
        "h_identity_manifest_sha256",
        "encoder_artifact_sha256",
        "encoder_implementation_sha256",
        "encoder_tokenizer_manifest_hash",
        "encoder_config_manifest_hash",
        "encoder_model_manifest_hash",
        "encoder_scientific_config_hash",
    )
    for key in required_hashes:
        if not _valid_sha(provenance.get(key)):
            raise ValueError(f"candidate provenance missing valid {key}")
    for key, expected in FROZEN_PROVENANCE.items():
        if provenance.get(key) != expected:
            raise ValueError(f"candidate provenance frozen {key} mismatch")
    if provenance.get("encoder_model_id") != "sentence-transformers/all-MiniLM-L6-v2":
        raise ValueError("candidate provenance model ID mismatch")
    if provenance.get("encoder_revision") != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41":
        raise ValueError("candidate provenance revision mismatch")
    mapping = provenance.get("source_join_mapping_sha256")
    if not isinstance(mapping, Mapping) or tuple(sorted(mapping)) != EXPECTED_TASKS:
        raise ValueError("candidate provenance source-join mapping hashes are incomplete")
    if any(not _valid_sha(value) for value in mapping.values()):
        raise ValueError("candidate provenance source-join mapping hash is malformed")
    if dict(mapping) != FROZEN_SOURCE_JOIN_MAPPING:
        raise ValueError("candidate provenance frozen source-join mapping mismatch")
    if provenance.get("read_fields") != ["sentenceData/content", "task_materials"]:
        raise ValueError("candidate provenance read_fields must exclude EEG fields")
    if provenance.get("roamm_paths_read") != []:
        raise ValueError("ROAMM path is forbidden")


def _normalise_stimuli(
    stimuli: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], np.ndarray]:
    raw = list(stimuli)
    _reject_forbidden_keys(raw, path="stimuli")
    rows: list[dict[str, Any]] = []
    embeddings: list[np.ndarray] = []
    for index, value in enumerate(raw):
        task = str(value.get("task", "")).strip()
        stimulus_id = str(value.get("stimulus_id", "")).strip()
        text_hash = str(value.get("exact_text_sha256", "")).strip()
        token_length = value.get("token_length")
        h_ids = [str(item).strip() for item in value.get("h_source_ids", [])]
        if task not in EXPECTED_TASKS:
            raise ValueError(f"stimulus {index}: unknown task")
        if not stimulus_id or not stimulus_id.startswith(f"zuco_2_0|{task}|"):
            raise ValueError(f"stimulus {index}: ID is not a verified ZuCo2 source-slot")
        if not _valid_sha(text_hash):
            raise ValueError(f"stimulus {index}: exact-text SHA256 is malformed")
        if isinstance(token_length, bool) or not isinstance(token_length, int) or token_length <= 0:
            raise ValueError(f"stimulus {index}: token length must be a positive integer")
        if any(not item for item in h_ids) or len(h_ids) != len(set(h_ids)):
            raise ValueError(f"stimulus {index}: H source IDs are empty or duplicated")
        vector = np.asarray(value.get("embedding"), dtype=np.float32)
        if vector.ndim != 1 or vector.size < 2 or not np.isfinite(vector).all():
            raise ValueError(f"stimulus {index}: embedding must be finite rank-1")
        norm = float(np.sqrt(np.sum(vector.astype(np.float64) ** 2, dtype=np.float64)))
        if not math.isclose(norm, 1.0, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(f"stimulus {index}: embedding is not L2-normalized")
        rows.append(
            {
                "task": task,
                "stimulus_id": stimulus_id,
                "exact_text_sha256": text_hash,
                "token_length": token_length,
                "h_source_ids": sorted(h_ids),
            }
        )
        embeddings.append(vector)
    if not rows:
        raise ValueError("stimulus table is empty")
    order = sorted(range(len(rows)), key=lambda item: (rows[item]["task"], rows[item]["stimulus_id"]))
    ordered_rows = [rows[index] for index in order]
    if len({row["stimulus_id"] for row in ordered_rows}) != len(ordered_rows):
        raise ValueError("stimulus IDs must be globally unique")
    matrix = np.stack([embeddings[index] for index in order]).astype(np.float32, copy=False)
    lookup = {row["stimulus_id"]: row for row in ordered_rows}
    all_ids = set(lookup)
    for row in ordered_rows:
        if any(source not in all_ids for source in row["h_source_ids"]):
            raise ValueError(f"H source identity is absent from released stimuli: {row['stimulus_id']}")
    return ordered_rows, lookup, matrix


def _normalise_scopes(
    scopes: Iterable[Mapping[str, Any]], stimulus_lookup: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    raw = list(scopes)
    _reject_forbidden_keys(raw, path="scopes")
    result: list[dict[str, Any]] = []
    for index, value in enumerate(raw):
        task = str(value.get("task", "")).strip()
        scope_type = str(value.get("scope_type", "")).strip()
        scope_id = str(value.get("scope_id", "")).strip()
        pool_ids = sorted(str(item).strip() for item in value.get("pool_ids", []))
        if task not in EXPECTED_TASKS or scope_type not in {"outer_test", "inner_validation"}:
            raise ValueError(f"scope {index}: invalid task/type")
        if not scope_id or not pool_ids or len(pool_ids) != len(set(pool_ids)):
            raise ValueError(f"scope {index}: empty/duplicate scope or pool identity")
        for stimulus_id in pool_ids:
            row = stimulus_lookup.get(stimulus_id)
            if row is None or row["task"] != task:
                raise ValueError(f"scope {index}: pool identity is outside task")
        item: dict[str, Any] = {
            "task": task,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "pool_ids": pool_ids,
        }
        if scope_type == "outer_test":
            reuse = sorted(str(value) for value in value.get("reuse_outer_subject_folds", []))
            if reuse != [str(number) for number in range(6)]:
                raise ValueError("outer candidate scope must be reused across all six subject folds")
            item["outer_text_fold"] = str(value.get("outer_text_fold", ""))
            item["reuse_outer_subject_folds"] = reuse
            if item["outer_text_fold"] not in {str(number) for number in range(5)}:
                raise ValueError("outer text fold is invalid")
        else:
            reuse = sorted(str(value) for value in value.get("reuse_inner_subject_folds", []))
            if reuse != [str(number) for number in range(3)]:
                raise ValueError("inner candidate scope must be reused across all three subject folds")
            item.update(
                {
                    "outer_cell_id": str(value.get("outer_cell_id", "")),
                    "outer_subject_fold": str(value.get("outer_subject_fold", "")),
                    "outer_text_fold": str(value.get("outer_text_fold", "")),
                    "inner_text_fold": str(value.get("inner_text_fold", "")),
                    "reuse_inner_subject_folds": reuse,
                }
            )
            if not item["outer_cell_id"] or item["inner_text_fold"] not in {"0", "1", "2"}:
                raise ValueError("inner scope identity/fold is invalid")
        result.append(item)
    result.sort(key=lambda item: (item["task"], item["scope_type"], item["scope_id"]))
    identities = [(item["task"], item["scope_type"], item["scope_id"]) for item in result]
    if len(identities) != len(set(identities)):
        raise ValueError("candidate scope IDs are duplicated")
    return result


def _cosine_diagnostic(values: Sequence[tuple[str, float]]) -> dict[str, Any]:
    if not values:
        return {
            "evaluated_count": 0,
            "greater_than_threshold_count": 0,
            "equal_to_threshold_count": 0,
            "maximum_cosine_hex": None,
            "closest_to_threshold_cosine_hex": None,
            "minimum_absolute_distance_hex": None,
            "closest_candidate_ids": [],
        }
    maximum = max(value for _, value in values)
    distance = min(abs(value - COSINE_THRESHOLD) for _, value in values)
    closest = sorted(identity for identity, value in values if abs(value - COSINE_THRESHOLD) == distance)
    closest_value = next(value for identity, value in values if identity == closest[0])
    return {
        "evaluated_count": len(values),
        "greater_than_threshold_count": sum(value > COSINE_THRESHOLD for _, value in values),
        "equal_to_threshold_count": sum(value == COSINE_THRESHOLD for _, value in values),
        "maximum_cosine_hex": float(maximum).hex(),
        "closest_to_threshold_cosine_hex": float(closest_value).hex(),
        "minimum_absolute_distance_hex": float(distance).hex(),
        "closest_candidate_ids": closest,
    }


def _distribution(values: Sequence[int]) -> dict[str, float | int]:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return {"count": 0, "min": 0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0}
    middle = len(ordered) // 2
    median = float(ordered[middle]) if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
    return {
        "count": len(ordered),
        "min": ordered[0],
        "q1": float(ordered[(len(ordered) - 1) // 4]),
        "median": median,
        "q3": float(ordered[(3 * (len(ordered) - 1)) // 4]),
        "max": ordered[-1],
    }


def _availability(targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for n in N_VALUES:
        insufficient = [row for row in targets if int(row["counts"]["legal_count"]) < NEGATIVE_COUNTS[n]]
        result[str(n)] = {
            "available": not insufficient,
            "required_negative_count": NEGATIVE_COUNTS[n],
            "target_count": len(targets),
            "infeasible_target_count": len(insufficient),
        }
    return result


def _shared_record(
    *, run_id: str, method: str, config: Mapping[str, Any], provenance: Mapping[str, Any]
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
        "provenance": dict(provenance),
    }


def build_candidate_artifacts(
    stimuli: Iterable[Mapping[str, Any]],
    scopes: Iterable[Mapping[str, Any]],
    *,
    provenance: Mapping[str, Any],
    seed: int = DEFAULT_SEED,
    repeats: int = DEFAULT_REPEATS,
    run_id: str = "2026-08-14_019_v310_zuco2_candidates",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build candidate lists, paired-verification pairs, and feasibility audit."""

    if seed != DEFAULT_SEED or repeats != DEFAULT_REPEATS:
        raise ValueError("SPEC v3.10 freezes seed=20260813 and L=5")
    _reject_forbidden_keys(provenance, path="provenance")
    _validate_provenance(provenance)
    stimulus_rows, stimulus_lookup, embeddings = _normalise_stimuli(stimuli)
    scope_rows = _normalise_scopes(scopes, stimulus_lookup)
    stimulus_index = {row["stimulus_id"]: index for index, row in enumerate(stimulus_rows)}
    cosine = np.einsum("ik,jk->ij", embeddings, embeddings, optimize=False)

    candidate_scopes: list[dict[str, Any]] = []
    feasibility_scopes: list[dict[str, Any]] = []
    pair_scopes: list[dict[str, Any]] = []
    all_feasibility_targets: list[dict[str, Any]] = []
    for scope in scope_rows:
        pool_ids = scope["pool_ids"]
        pool_indices = [stimulus_index[value] for value in pool_ids]
        candidate_targets: list[dict[str, Any]] = []
        feasibility_targets: list[dict[str, Any]] = []
        pair_targets: list[dict[str, Any]] = []
        for target_id in pool_ids:
            target = stimulus_lookup[target_id]
            target_index = stimulus_index[target_id]
            after_target = [value for value in pool_ids if value != target_id]
            after_length = [
                value
                for value in after_target
                if length_is_legal(int(target["token_length"]), int(stimulus_lookup[value]["token_length"]))
            ]
            similarities = [
                (value, float(cosine[target_index, stimulus_index[value]]))
                for value in after_length
            ]
            after_cosine = [value for value, score in similarities if cosine_is_legal(score)]
            h_sources = set(target["h_source_ids"])
            legal = sorted(value for value in after_cosine if value not in h_sources)
            counts = {
                "raw_pool": len(pool_ids),
                "after_target_exclusion": len(after_target),
                "length_pass": len(after_length),
                "cosine_pass": len(after_cosine),
                "h_full_pass": len(legal),
                "legal_count": len(legal),
            }
            exclusions = {
                "target_identity_excluded": len(pool_ids) - len(after_target),
                "length_excluded": len(after_target) - len(after_length),
                "cosine_excluded": len(after_length) - len(after_cosine),
                "h_full_identity_excluded": len(after_cosine) - len(legal),
            }
            feasible_n = [n for n in N_VALUES if len(legal) >= NEGATIVE_COUNTS[n]]
            unavailable = {
                str(n): f"legal_count_{len(legal)}_below_required_{NEGATIVE_COUNTS[n]}"
                for n in N_VALUES
                if n not in feasible_n
            }
            repeat_rows: list[dict[str, Any]] = []
            pair_repeat_rows: list[dict[str, Any]] = []
            for repeat in range(repeats):
                ordering = sorted(
                    legal,
                    key=lambda negative_id: hash_rank_key(
                        seed=seed,
                        task=scope["task"],
                        scope_id=scope["scope_id"],
                        target_id=target_id,
                        repeat=repeat,
                        negative_id=negative_id,
                    ),
                )
                ordering_indices = [stimulus_index[value] for value in ordering]
                n_lists = {
                    str(n): {
                        "available": n in feasible_n,
                        "negative_prefix_length": NEGATIVE_COUNTS[n] if n in feasible_n else 0,
                        "target_position": stable_target_position(
                            seed=seed,
                            task=scope["task"],
                            scope_id=scope["scope_id"],
                            target_id=target_id,
                            repeat=repeat,
                            n=n,
                        )
                        if n in feasible_n
                        else None,
                    }
                    for n in N_VALUES
                }
                repeat_rows.append(
                    {
                        "repeat": repeat,
                        "maximal_legal_negative_indices": ordering_indices,
                        "n_lists": n_lists,
                    }
                )
                pair_repeat_rows.append(
                    {
                        "repeat": repeat,
                        "auroc_1_to_1": {
                            "available": bool(ordering_indices),
                            "positive_index": target_index,
                            "negative_index": ordering_indices[0] if ordering_indices else None,
                            "derived_from": "candidate_maximal_order_prefix_1",
                        },
                        "auprc_1_to_49": {
                            "available": 50 in feasible_n,
                            "positive_index": target_index,
                            "negative_indices": ordering_indices[:49] if 50 in feasible_n else [],
                            "derived_from": "candidate_N50_negative_prefix_49",
                        },
                    }
                )
            candidate_targets.append(
                {
                    "target_index": target_index,
                    "legal_count": len(legal),
                    "repeats": repeat_rows,
                }
            )
            feasibility = {
                "target_index": target_index,
                "counts": counts,
                "sequential_exclusions": exclusions,
                "h_full_source_indices": sorted(stimulus_index[value] for value in h_sources),
                "cosine_boundary_diagnostic": _cosine_diagnostic(similarities),
                "feasible_n": feasible_n,
                "unavailable_n_reasons": unavailable,
            }
            feasibility_targets.append(feasibility)
            all_feasibility_targets.append({**feasibility, "task": scope["task"], "scope_type": scope["scope_type"]})
            pair_targets.append({"target_index": target_index, "repeats": pair_repeat_rows})
        scope_metadata = {key: value for key, value in scope.items() if key != "pool_ids"}
        candidate_scopes.append(
            {
                **scope_metadata,
                "pool_stimulus_indices": pool_indices,
                "target_count": len(candidate_targets),
                "targets": candidate_targets,
            }
        )
        feasibility_scopes.append(
            {
                **scope_metadata,
                "pool_count": len(pool_indices),
                "target_count": len(feasibility_targets),
                "targets": feasibility_targets,
            }
        )
        pair_scopes.append(
            {
                **scope_metadata,
                "target_count": len(pair_targets),
                "targets": pair_targets,
            }
        )

    config = {
        "spec": "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_10_2026-08-14.md#N.3",
        "algorithm_version": ALGORITHM_VERSION,
        "seed": seed,
        "repeats": repeats,
        "n_values": list(N_VALUES),
        "negative_counts": {str(key): value for key, value in NEGATIVE_COUNTS.items()},
        "length_rule": "3*L_target <= 4*L_negative <= 5*L_target",
        "cosine_exclusion": "strictly_greater_than_0.9",
        "h_exclusion": "all_exact_H_full_source_identities",
        "ordering": "SHA256(seed|task|scope_id|target_id|repeat|negative_id), then negative_id",
        "sampling": "without_replacement_prefixes_of_one_maximal_ordering",
    }
    output_stimuli = [
        {
            "stimulus_id": row["stimulus_id"],
            "task": row["task"],
            "exact_text_sha256": row["exact_text_sha256"],
            "token_length": row["token_length"],
            "h_full_source_indices": [stimulus_index[value] for value in row["h_source_ids"]],
        }
        for row in stimulus_rows
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in all_feasibility_targets:
        grouped[(row["task"], row["scope_type"])].append(row)
    summaries: dict[str, Any] = {}
    for task in EXPECTED_TASKS:
        summaries[task] = {}
        for scope_type in ("outer_test", "inner_validation"):
            rows = grouped[(task, scope_type)]
            summaries[task][scope_type] = {
                "target_count": len(rows),
                "stage_count_distributions": {
                    stage: _distribution([int(row["counts"][stage]) for row in rows])
                    for stage in (
                        "raw_pool",
                        "after_target_exclusion",
                        "length_pass",
                        "cosine_pass",
                        "h_full_pass",
                        "legal_count",
                    )
                },
                "n_availability": _availability(rows),
            }
    task_availability = {
        task: _availability([row for row in all_feasibility_targets if row["task"] == task])
        for task in EXPECTED_TASKS
    }
    overall_availability = _availability(all_feasibility_targets)
    n50_pass = bool(overall_availability["50"]["available"])
    completion_outcome = "PASS_N50" if n50_pass else "STRUCTURAL_NO_GO_N50"
    common_assertions = {
        "all_targets_retained": sum(len(scope["pool_ids"]) for scope in scope_rows) == len(all_feasibility_targets),
        "outer_and_inner_scopes_present": {scope["scope_type"] for scope in scope_rows}
        == {"outer_test", "inner_validation"},
        "five_hash_ranked_repeats": repeats == 5,
        "without_replacement": True,
        "prefix_nesting": True,
        "source_slot_identity_only": True,
        "contains_no_sentence_text": True,
        "contains_no_eeg_or_paper_metrics": True,
        "roamm_paths_read": [],
    }

    candidates: dict[str, Any] = {
        **_shared_record(
            run_id=run_id,
            method="ZuCo2-frozen-sentence-candidate-lists",
            config=config,
            provenance=provenance,
        ),
        "identity_encoding": "zero_based_indices_into_exact_source_slot_stimuli",
        "stimuli": output_stimuli,
        "scopes": candidate_scopes,
        "completion_outcome": completion_outcome,
        "assertions": common_assertions,
        "status": "PASS",
    }
    _add_integrity(candidates, "canonical JSON candidate artifact without integrity field")

    pairs: dict[str, Any] = {
        **_shared_record(
            run_id=run_id,
            method="ZuCo2-paired-verification-from-frozen-candidates",
            config=config,
            provenance=provenance,
        ),
        "identity_encoding": "zero_based_indices_into_candidate_lists.stimuli",
        "candidate_lists_file_sha256": None,
        "scopes": pair_scopes,
        "completion_outcome": completion_outcome,
        "assertions": {
            "all_targets_retained": common_assertions["all_targets_retained"],
            "auroc_derived_from_first_frozen_negative": True,
            "auprc_derived_from_same_frozen_n50_prefix": True,
            "no_additional_sampling": True,
            "contains_no_eeg_or_paper_metrics": True,
            "roamm_paths_read": [],
        },
        "status": "PASS",
    }
    # The file SHA is filled by the writer; canonical content instead binds
    # the exact candidate payload hash without creating a circular file hash.
    pairs["candidate_lists_canonical_payload_sha256"] = candidates["integrity"]["canonical_payload_sha256"]
    _add_integrity(pairs, "canonical JSON paired artifact without integrity field")

    audit: dict[str, Any] = {
        **_shared_record(
            run_id=run_id,
            method="ZuCo2-candidate-feasibility-audit",
            config=config,
            provenance=provenance,
        ),
        "identity_encoding": "zero_based_indices_into_candidate_lists.stimuli",
        "scope_count": len(scope_rows),
        "target_count": len(all_feasibility_targets),
        "tasks": summaries,
        "task_n_availability": task_availability,
        "overall_n_availability": overall_availability,
        "n50_outcome": completion_outcome,
        "scopes": feasibility_scopes,
        "assertions": {
            "every_scope_target_audited": common_assertions["all_targets_retained"],
            "all_filter_stages_recorded": True,
            "no_target_silently_deleted": True,
            "n50_requires_every_target": True,
            "n100_n200_never_backfilled": True,
            "contains_no_eeg_or_paper_metrics": True,
            "roamm_paths_read": [],
        },
        "status": "PASS",
    }
    _add_integrity(audit, "canonical JSON feasibility audit without integrity field")
    errors = validate_candidate_artifacts(candidates, pairs, audit)
    if errors:
        raise AssertionError(f"candidate artifact self-validation failed: {errors}")
    return candidates, pairs, audit


def validate_candidate_artifacts(
    candidates: Mapping[str, Any], pairs: Mapping[str, Any], audit: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    try:
        for label, value in (("candidates", candidates), ("pairs", pairs), ("audit", audit)):
            if value.get("status") != "PASS" or value.get("dataset") != "zuco_2_0":
                raise ValueError(f"{label}: status/dataset mismatch")
            _verify_config_hash(value, label)
            _verify_integrity(value, label)
            _validate_provenance(value["provenance"])
        if not (
            candidates["config_hash"] == pairs["config_hash"] == audit["config_hash"]
            and candidates["provenance"] == pairs["provenance"] == audit["provenance"]
            and candidates["run_id"] == pairs["run_id"] == audit["run_id"]
        ):
            raise ValueError("shared config/provenance/run_id differs across artifacts")
        if pairs.get("candidate_lists_canonical_payload_sha256") != candidates["integrity"][
            "canonical_payload_sha256"
        ]:
            raise ValueError("paired artifact does not bind candidate canonical payload")
        stimuli = candidates["stimuli"]
        stimulus_ids = [row["stimulus_id"] for row in stimuli]
        candidate_scopes = {
            (row["task"], row["scope_type"], row["scope_id"]): row
            for row in candidates["scopes"]
        }
        pair_scopes = {
            (row["task"], row["scope_type"], row["scope_id"]): row
            for row in pairs["scopes"]
        }
        audit_scopes = {
            (row["task"], row["scope_type"], row["scope_id"]): row
            for row in audit["scopes"]
        }
        if not candidate_scopes or set(candidate_scopes) != set(pair_scopes) or set(candidate_scopes) != set(audit_scopes):
            raise ValueError("scope coverage differs across artifacts")
        total_targets = 0
        for key, scope in candidate_scopes.items():
            pool = set(scope["pool_stimulus_indices"])
            candidate_targets = {row["target_index"]: row for row in scope["targets"]}
            pair_targets = {row["target_index"]: row for row in pair_scopes[key]["targets"]}
            audit_targets = {row["target_index"]: row for row in audit_scopes[key]["targets"]}
            if set(candidate_targets) != pool or set(candidate_targets) != set(pair_targets) or set(candidate_targets) != set(audit_targets):
                raise ValueError(f"{key}: target coverage differs or a target was dropped")
            total_targets += len(pool)
            for target_index, target in candidate_targets.items():
                legal_count = int(target["legal_count"])
                if legal_count != int(audit_targets[target_index]["counts"]["legal_count"]):
                    raise ValueError(f"{key}: candidate/audit legal count mismatch")
                candidate_repeats = target["repeats"]
                paired_repeats = pair_targets[target_index]["repeats"]
                if len(candidate_repeats) != DEFAULT_REPEATS or len(paired_repeats) != DEFAULT_REPEATS:
                    raise ValueError(f"{key}: repeat count mismatch")
                for candidate_repeat, pair_repeat in zip(candidate_repeats, paired_repeats, strict=True):
                    ordering = candidate_repeat["maximal_legal_negative_indices"]
                    if len(ordering) != legal_count or len(ordering) != len(set(ordering)):
                        raise ValueError(f"{key}: ordering is not maximal/without replacement")
                    if target_index in ordering or not set(ordering).issubset(pool):
                        raise ValueError(f"{key}: target or wrong-scope negative in ordering")
                    repeat = int(candidate_repeat["repeat"])
                    expected_order = sorted(
                        ordering,
                        key=lambda negative_index: hash_rank_key(
                            seed=DEFAULT_SEED,
                            task=key[0],
                            scope_id=key[2],
                            target_id=stimulus_ids[target_index],
                            repeat=repeat,
                            negative_id=stimulus_ids[negative_index],
                        ),
                    )
                    if ordering != expected_order:
                        raise ValueError(f"{key}: hash ordering mismatch")
                    for n in N_VALUES:
                        row = candidate_repeat["n_lists"][str(n)]
                        available = legal_count >= NEGATIVE_COUNTS[n]
                        if bool(row["available"]) != available:
                            raise ValueError(f"{key}: N availability mismatch")
                        if available and ordering[: NEGATIVE_COUNTS[n]] != ordering[: int(row["negative_prefix_length"])]:
                            raise ValueError(f"{key}: prefix nesting mismatch")
                    auroc = pair_repeat["auroc_1_to_1"]
                    if bool(ordering) != bool(auroc["available"]):
                        raise ValueError(f"{key}: AUROC availability mismatch")
                    if ordering and auroc["negative_index"] != ordering[0]:
                        raise ValueError(f"{key}: AUROC was not derived from first negative")
                    auprc = pair_repeat["auprc_1_to_49"]
                    n50 = legal_count >= 49
                    if bool(auprc["available"]) != n50:
                        raise ValueError(f"{key}: AUPRC availability mismatch")
                    if n50 and auprc["negative_indices"] != ordering[:49]:
                        raise ValueError(f"{key}: AUPRC was not derived from N50 prefix")
        if total_targets != int(audit["target_count"]):
            raise ValueError("audit target count mismatch")
        expected_outcome = "PASS_N50" if bool(audit["overall_n_availability"]["50"]["available"]) else "STRUCTURAL_NO_GO_N50"
        if any(value.get("completion_outcome", value.get("n50_outcome")) != expected_outcome for value in (candidates, pairs, audit)):
            raise ValueError("completion outcome mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def write_canonical_json(value: Mapping[str, Any], path: str | Path) -> tuple[int, str]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    output.write_bytes(payload)
    return len(payload), sha256_bytes(payload)


def write_candidate_triplet(
    candidates: Mapping[str, Any],
    pairs: Mapping[str, Any],
    audit: Mapping[str, Any],
    *,
    candidate_path: str | Path,
    pair_path: str | Path,
    audit_path: str | Path,
) -> dict[str, dict[str, Any]]:
    """Write the three canonical artifacts and bind the exact candidate file."""

    errors = validate_candidate_artifacts(candidates, pairs, audit)
    if errors:
        raise ValueError(f"refusing invalid candidate artifacts: {errors}")
    candidate_bytes, candidate_sha = write_canonical_json(candidates, candidate_path)
    bound_pairs = dict(pairs)
    bound_pairs.pop("integrity", None)
    bound_pairs["candidate_lists_file_sha256"] = candidate_sha
    _add_integrity(bound_pairs, "canonical JSON paired artifact without integrity field")
    pair_bytes, pair_sha = write_canonical_json(bound_pairs, pair_path)
    audit_bytes, audit_sha = write_canonical_json(audit, audit_path)
    return {
        "candidate_lists": {"bytes": candidate_bytes, "sha256": candidate_sha},
        "paired_verification_pairs": {"bytes": pair_bytes, "sha256": pair_sha},
        "candidate_feasibility": {"bytes": audit_bytes, "sha256": audit_sha},
    }
