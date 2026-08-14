#!/usr/bin/env python3
"""Deterministic subject-by-stimulus joint splitting for v3.6.

The splitter implements the scientific contract in section 4.2.1 of the
unified specification.  It deliberately accepts *identity evidence* from an
upstream data-card/join step instead of trying to infer material identity from
text.  Rows whose join is not explicitly verified are excluded and retained in
the audit ledger.

Input rows represent one subject/stimulus observation (multiple rows for the
same pair are allowed when they are distinct source observations):

``subject_id, stimulus_id, group_key, valid_sentence_trials, join_status``

``group_key`` must already encode the non-splittable document/paragraph (and
any paraphrase grouping required by the dataset).  ``join_status`` must be
``VERIFIED`` (or one of the explicitly accepted equivalent labels).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DEFAULT_SEED = 20260813
DEFAULT_SUBJECT_FOLDS = 6
DEFAULT_TEXT_FOLDS = 5
ACCEPTED_JOIN_STATUSES = frozenset({"VERIFIED", "SOURCE_VERIFIED", "APPROVED", "PROVEN"})


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON without implementation-dependent whitespace/order."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().casefold()
    if text in {"1", "true", "yes", "y", "include", "included"}:
        return True
    if text in {"0", "false", "no", "n", "exclude", "excluded"}:
        return False
    return default


def _valid_trial_count(row: Mapping[str, Any]) -> int | None:
    aliases = (
        "valid_sentence_trials",
        "valid_sentence_trial_count",
        "n_valid_sentence_trials",
        "valid_trials",
    )
    value: Any = None
    for key in aliases:
        if key in row:
            value = row[key]
            break
    if value is None and "valid_sentence_trial" in row:
        value = 1 if _as_bool(row["valid_sentence_trial"], default=False) else 0
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or number != math.floor(number):
        return None
    return int(number)


def _stable_key(value: Any) -> str:
    return str(value).strip()


def _record_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep identity/count fields while avoiding text-as-identity semantics."""

    subject_id = _stable_key(row.get("subject_id", row.get("subject")))
    stimulus_id = _stable_key(row.get("stimulus_id", row.get("stimulus")))
    group_key = _stable_key(row.get("group_key", row.get("material_group")))
    status = _stable_key(
        row.get(
            "join_status",
            row.get("material_join_status", row.get("identity_status", "UNVERIFIED")),
        )
    ).upper()
    count = _valid_trial_count(row)
    projected: dict[str, Any] = {
        "subject_id": subject_id,
        "stimulus_id": stimulus_id,
        "group_key": group_key,
        "valid_sentence_trials": count,
        "join_status": status,
        "eligible": _as_bool(row.get("eligible", row.get("include")), default=True),
    }
    # A source-slot key is useful for an exclusion ledger, but is never used
    # as a guessed identity when group_key/stimulus_id are absent.
    if row.get("source_slot") is not None:
        projected["source_slot"] = _stable_key(row["source_slot"])
    if row.get("record_id") is not None and _stable_key(row["record_id"]):
        projected["record_id"] = _stable_key(row["record_id"])
    if row.get("exclusion_reason") is not None and _stable_key(row["exclusion_reason"]):
        projected["exclusion_reason"] = _stable_key(row["exclusion_reason"])
    return projected


def _normalise_records(rows: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Normalize and deterministically identify rows.

    Returns ``(records, raw_rows, input_sha256)``.  ``records`` are sorted and
    have stable IDs; ``raw_rows`` are the selected identity/count projection
    used for the input digest.  Missing IDs/counts are retained for exclusion
    reporting rather than silently repaired.
    """

    raw = [_record_projection(row) for row in rows]
    raw.sort(key=canonical_json_bytes)
    input_digest = sha256_bytes(canonical_json_bytes(raw))

    explicit_ids = [row["record_id"] for row in raw if "record_id" in row]
    if len(explicit_ids) != len(set(explicit_ids)):
        raise ValueError("input contains duplicate explicit record_id values")

    records: list[dict[str, Any]] = []
    generated_counts: Counter[str] = Counter()
    for row in raw:
        record = dict(row)
        if "record_id" not in record:
            base = sha256_bytes(canonical_json_bytes(record))
            generated_counts[base] += 1
            suffix = generated_counts[base]
            record["record_id"] = f"r-{base}" if suffix == 1 else f"r-{base}-{suffix}"
        records.append(record)
    records.sort(key=lambda item: item["record_id"])
    return records, raw, input_digest


def _add_reason(reasons: dict[str, set[str]], record_id: str, reason: str) -> None:
    reasons.setdefault(record_id, set()).add(reason)


def _prepare_records(records: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reasons: dict[str, set[str]] = {}
    by_stimulus: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        rid = str(record["record_id"])
        subject = str(record.get("subject_id", ""))
        stimulus = str(record.get("stimulus_id", ""))
        group = str(record.get("group_key", ""))
        count = record.get("valid_sentence_trials")
        if not subject:
            _add_reason(reasons, rid, "MISSING_SUBJECT_ID")
        if not stimulus:
            _add_reason(reasons, rid, "MISSING_STIMULUS_ID")
        if not group:
            _add_reason(reasons, rid, "MISSING_GROUP_KEY")
        if not isinstance(count, int) or count <= 0:
            _add_reason(reasons, rid, "NONPOSITIVE_OR_INVALID_VALID_SENTENCE_TRIALS")
        if not bool(record.get("eligible", True)):
            _add_reason(reasons, rid, "EXPLICITLY_EXCLUDED")
            if str(record.get("exclusion_reason", "")).strip():
                _add_reason(reasons, rid, f"SOURCE_{record['exclusion_reason']}")
        if str(record.get("join_status", "UNVERIFIED")).upper() not in ACCEPTED_JOIN_STATUSES:
            _add_reason(reasons, rid, "MATERIAL_JOIN_NOT_VERIFIED")
        if stimulus:
            by_stimulus[stimulus].append(record)

    # A stimulus with any unverified occurrence is excluded as a whole.  This
    # prevents a verified row from silently being paired with an ambiguous
    # source slot for the same identity.
    for stimulus, occurrences in by_stimulus.items():
        groups = {str(item.get("group_key", "")) for item in occurrences if item.get("group_key")}
        if len(groups) > 1:
            for item in occurrences:
                _add_reason(reasons, str(item["record_id"]), "STIMULUS_GROUP_IDENTITY_CONFLICT")
        if any(
            str(item.get("join_status", "UNVERIFIED")).upper() not in ACCEPTED_JOIN_STATUSES
            for item in occurrences
        ):
            for item in occurrences:
                _add_reason(reasons, str(item["record_id"]), "STIMULUS_HAS_UNVERIFIED_JOIN")

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in records:
        rid = str(record["record_id"])
        if rid in reasons:
            excluded.append(
                {
                    "record_id": rid,
                    "subject_id": str(record.get("subject_id", "")),
                    "stimulus_id": str(record.get("stimulus_id", "")),
                    "group_key": str(record.get("group_key", "")),
                    "reasons": sorted(reasons[rid]),
                    "source_slot": record.get("source_slot"),
                    "source_exclusion_reason": record.get("exclusion_reason"),
                }
            )
        else:
            eligible.append(record)
    excluded.sort(key=lambda item: item["record_id"])
    return eligible, excluded


def _subject_folds(
    eligible: Sequence[dict[str, Any]], k_subject: int
) -> tuple[dict[str, str], list[dict[str, Any]], list[int]]:
    counts: Counter[str] = Counter()
    for record in eligible:
        counts[str(record["subject_id"])] += int(record["valid_sentence_trials"])
    ordered = sorted(counts, key=lambda subject: (-counts[subject], subject))
    assignment = {subject: str(index % k_subject) for index, subject in enumerate(ordered)}
    fold_counts = [sum(counts[s] for s in ordered if assignment[s] == str(fold)) for fold in range(k_subject)]
    table = [
        {
            "subject_id": subject,
            "valid_sentence_trial_count": int(counts[subject]),
            "subject_fold": assignment[subject],
        }
        for subject in ordered
    ]
    return assignment, table, fold_counts


def _text_folds(
    eligible: Sequence[dict[str, Any]],
    *,
    dataset: str,
    task: str,
    seed: int,
    k_text: int,
) -> tuple[dict[str, str], list[dict[str, Any]], list[int]]:
    group_stimuli: defaultdict[str, set[str]] = defaultdict(set)
    stimulus_groups: defaultdict[str, set[str]] = defaultdict(set)
    for record in eligible:
        stimulus = str(record["stimulus_id"])
        group = str(record["group_key"])
        group_stimuli[group].add(stimulus)
        stimulus_groups[stimulus].add(group)
    conflicts = {stimulus for stimulus, groups in stimulus_groups.items() if len(groups) != 1}
    if conflicts:
        raise ValueError(f"eligible stimulus has multiple group keys: {sorted(conflicts)}")

    group_meta: list[dict[str, Any]] = []
    for group, stimuli in group_stimuli.items():
        group_hash = sha256_text(f"{seed}|{dataset}|{task}|{group}")
        group_meta.append(
            {
                "group_key": group,
                "stimulus_ids": sorted(stimuli),
                "effective_stimulus_count": len(stimuli),
                "group_hash": group_hash,
            }
        )
    group_meta.sort(key=lambda item: (-item["effective_stimulus_count"], item["group_hash"], item["group_key"]))
    totals = [0] * k_text
    groups_by_fold: list[list[str]] = [[] for _ in range(k_text)]
    stimulus_fold: dict[str, str] = {}
    for item in group_meta:
        fold = min(range(k_text), key=lambda index: (totals[index], index))
        item["text_fold"] = str(fold)
        groups_by_fold[fold].append(item["group_key"])
        totals[fold] += int(item["effective_stimulus_count"])
        for stimulus in item["stimulus_ids"]:
            stimulus_fold[stimulus] = str(fold)
    for item in group_meta:
        item["groups_in_fold"] = groups_by_fold[int(item["text_fold"])]
    return stimulus_fold, group_meta, totals


def _assertions(
    eligible: Sequence[dict[str, Any]],
    subjects: Mapping[str, str],
    stimuli: Mapping[str, str],
    groups: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    k_subject: int,
    k_text: int,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["each_subject_has_one_fold"] = len(subjects) == len(set(subjects)) and all(
        fold in {str(i) for i in range(k_subject)} for fold in subjects.values()
    )
    checks["each_stimulus_has_one_fold"] = len(stimuli) == len(set(stimuli)) and all(
        fold in {str(i) for i in range(k_text)} for fold in stimuli.values()
    )
    group_fold_map: defaultdict[str, set[str]] = defaultdict(set)
    for group in groups:
        group_fold_map[str(group["group_key"])].add(str(group["text_fold"]))
    checks["group_does_not_cross_text_folds"] = all(len(folds) == 1 for folds in group_fold_map.values())
    checks["all_subject_folds_populated"] = set(subjects.values()) == {
        str(index) for index in range(k_subject)
    }
    checks["all_text_folds_populated"] = set(stimuli.values()) == {
        str(index) for index in range(k_text)
    }
    checks["every_subject_held_out_at_least_once"] = all(
        any(str(subject_fold) == str(cell["subject_fold"]) and str(subject) in cell["test_subject_ids"] for cell in cells)
        for subject, subject_fold in subjects.items()
    )
    checks["every_stimulus_held_out_at_least_once"] = all(
        any(str(text_fold) == str(cell["text_fold"]) and str(stimulus) in cell["test_stimulus_ids"] for cell in cells)
        for stimulus, text_fold in stimuli.items()
    )
    checks["train_test_disjoint_in_every_cell"] = all(
        not set(cell["test_record_ids"]).intersection(cell["train_record_ids"])
        and not set(cell["test_subject_ids"]).intersection(cell["train_subject_ids"])
        and not set(cell["test_stimulus_ids"]).intersection(cell["train_stimulus_ids"])
        for cell in cells
    )
    eligible_ids = {str(record["record_id"]) for record in eligible}
    checks["cell_partitions_cover_all_records"] = all(
        set(cell["test_record_ids"])
        | set(cell["train_record_ids"])
        | set(cell["held_out_only_record_ids"])
        == eligible_ids
        and not set(cell["test_record_ids"]).intersection(cell["held_out_only_record_ids"])
        and not set(cell["train_record_ids"]).intersection(cell["held_out_only_record_ids"])
        for cell in cells
    )
    checks["all_eligible_records_assigned"] = all(
        "subject_fold" in record and "text_fold" in record for record in eligible
    )
    checks["all_checks_pass"] = all(checks.values())
    return checks


def build_joint_split(
    records: Iterable[Mapping[str, Any]],
    *,
    dataset: str,
    task: str,
    seed: int = DEFAULT_SEED,
    k_subject: int = DEFAULT_SUBJECT_FOLDS,
    k_text: int = DEFAULT_TEXT_FOLDS,
) -> dict[str, Any]:
    """Build one dataset/task panel's deterministic outer split artifact."""

    dataset = _stable_key(dataset)
    task = _stable_key(task)
    if not dataset or not task:
        raise ValueError("dataset and task are required")
    if int(seed) < 0:
        raise ValueError("seed must be non-negative")
    if int(k_subject) <= 0 or int(k_text) <= 0:
        raise ValueError("fold counts must be positive")
    normalized, raw_rows, input_digest = _normalise_records(records)
    eligible, excluded = _prepare_records(normalized)
    if not eligible:
        raise ValueError("no eligible records remain after conservative join/exclusion checks")

    subject_assignment, subject_table, subject_trial_totals = _subject_folds(eligible, int(k_subject))
    stimulus_assignment, group_table, stimulus_totals = _text_folds(
        eligible, dataset=dataset, task=task, seed=int(seed), k_text=int(k_text)
    )

    assigned_records: list[dict[str, Any]] = []
    for record in eligible:
        item = {
            "record_id": str(record["record_id"]),
            "subject_id": str(record["subject_id"]),
            "stimulus_id": str(record["stimulus_id"]),
            "group_key": str(record["group_key"]),
            "valid_sentence_trials": int(record["valid_sentence_trials"]),
            "subject_fold": subject_assignment[str(record["subject_id"])],
            "text_fold": stimulus_assignment[str(record["stimulus_id"])],
        }
        if record.get("source_slot") is not None:
            item["source_slot"] = record["source_slot"]
        assigned_records.append(item)
    assigned_records.sort(key=lambda item: item["record_id"])

    cells: list[dict[str, Any]] = []
    for subject_fold in range(int(k_subject)):
        for text_fold in range(int(k_text)):
            sf = str(subject_fold)
            tf = str(text_fold)
            test = [
                record
                for record in assigned_records
                if record["subject_fold"] == sf and record["text_fold"] == tf
            ]
            train = [
                record
                for record in assigned_records
                if record["subject_fold"] != sf and record["text_fold"] != tf
            ]
            held_out_only = [
                record
                for record in assigned_records
                if (record["subject_fold"] == sf) ^ (record["text_fold"] == tf)
            ]
            cells.append(
                {
                    "subject_fold": sf,
                    "text_fold": tf,
                    "status": "PASS" if test else "MISSING",
                    "test_record_ids": [record["record_id"] for record in test],
                    "train_record_ids": [record["record_id"] for record in train],
                    "held_out_only_record_ids": [record["record_id"] for record in held_out_only],
                    "test_subject_ids": sorted({record["subject_id"] for record in test}),
                    "train_subject_ids": sorted({record["subject_id"] for record in train}),
                    "test_stimulus_ids": sorted({record["stimulus_id"] for record in test}),
                    "train_stimulus_ids": sorted({record["stimulus_id"] for record in train}),
                    "test_record_count": len(test),
                    "train_record_count": len(train),
                    "held_out_only_record_count": len(held_out_only),
                    "test_valid_sentence_trial_count": sum(record["valid_sentence_trials"] for record in test),
                    "train_valid_sentence_trial_count": sum(record["valid_sentence_trials"] for record in train),
                }
            )

    artifact: dict[str, Any] = {
        "schema_version": 1,
        "contract": "EEG_Text_Bprime_Unified_Paper_Spec_v3_6__4.2.1",
        "method": "deterministic_subject_stimulus_joint_split",
        "algorithm": {
            "subject_order": "descending valid sentence-trial count, then subject ID lexicographic",
            "subject_assignment": "round_robin",
            "text_group": "dataset/task/document/paragraph supplied as group_key",
            "text_order": "descending effective stimulus count, then SHA256(seed|dataset|task|group_key), then group_key",
            "text_assignment": "greedy minimum effective-stimulus total, ties by fold number",
            "cell_test": "subject_fold intersection text_fold",
            "cell_train": "subject_fold != target and text_fold != target",
            "unverified_join_policy": "exclude affected stimulus and retain exclusion ledger",
            "text_hash_is_identity": False,
        },
        "dataset": dataset,
        "task": task,
        "seed": int(seed),
        "fold_counts": {"subject": int(k_subject), "text": int(k_text), "cells": int(k_subject) * int(k_text)},
        "input": {
            "record_count": len(raw_rows),
            "record_ids": sorted(str(record["record_id"]) for record in normalized),
            "input_sha256": input_digest,
        },
        "exclusions": excluded,
        "exclusion_summary": {
            "excluded_record_count": len(excluded),
            "excluded_record_ids": [item["record_id"] for item in excluded],
            "excluded_stimulus_ids": sorted({item["stimulus_id"] for item in excluded if item["stimulus_id"]}),
            "reason_counts": dict(
                sorted(
                    Counter(reason for item in excluded for reason in item["reasons"]).items()
                )
            ),
        },
        "subjects": {
            "count": len(subject_table),
            "order": [item["subject_id"] for item in subject_table],
            "records": subject_table,
            "fold_valid_sentence_trial_totals": subject_trial_totals,
        },
        "text": {
            "stimulus_count": len(stimulus_assignment),
            "stimulus_ids": sorted(stimulus_assignment),
            "stimulus_fold": stimulus_assignment,
            "groups": group_table,
            "fold_effective_stimulus_totals": stimulus_totals,
        },
        "records": assigned_records,
        "cells": cells,
    }
    config = {
        "method": artifact["method"],
        "dataset": dataset,
        "task": task,
        "seed": int(seed),
        "subject_folds": int(k_subject),
        "text_folds": int(k_text),
        "algorithm": artifact["algorithm"],
    }
    artifact["config_hash"] = sha256_bytes(canonical_json_bytes(config))
    artifact["config"] = config
    artifact["assertions"] = _assertions(
        assigned_records,
        subject_assignment,
        stimulus_assignment,
        group_table,
        cells,
        int(k_subject),
        int(k_text),
    )
    payload_bytes = canonical_json_bytes(artifact)
    artifact["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload_bytes),
        "canonical_payload_bytes": len(payload_bytes),
        "hash_scope": "canonical JSON artifact without integrity field",
    }
    return artifact


def validate_artifact(artifact: Mapping[str, Any]) -> list[str]:
    """Validate the non-negotiable split assertions and integrity digest."""

    errors: list[str] = []
    assertions = artifact.get("assertions", {})
    for name, value in assertions.items():
        if name != "all_checks_pass" and value is not True:
            errors.append(f"assertion failed: {name}")
    if assertions.get("all_checks_pass") is not True:
        errors.append("assertion failed: all_checks_pass")
    integrity = artifact.get("integrity")
    if isinstance(integrity, Mapping):
        without_integrity = dict(artifact)
        without_integrity.pop("integrity", None)
        expected = sha256_bytes(canonical_json_bytes(without_integrity))
        if integrity.get("canonical_payload_sha256") != expected:
            errors.append("canonical payload SHA256 mismatch")
    else:
        errors.append("missing integrity block")
    return errors


def write_artifact(artifact: Mapping[str, Any], path: str | Path) -> tuple[int, str]:
    """Write canonical JSON and return ``(bytes, file_sha256)``."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(artifact) + b"\n"
    target.write_bytes(payload)
    return len(payload), sha256_bytes(payload)


def synthetic_records() -> list[dict[str, Any]]:
    """Small deterministic fixture used by the CLI self-check."""

    records: list[dict[str, Any]] = []
    for subject_index in range(12):
        subject = f"sub-{subject_index + 1:02d}"
        for stimulus_index in range(15):
            stimulus = f"stim-{stimulus_index + 1:02d}"
            records.append(
                {
                    "record_id": f"{subject}|{stimulus}",
                    "subject_id": subject,
                    "stimulus_id": stimulus,
                    "group_key": f"doc-{stimulus_index // 3:02d}|paragraph-{stimulus_index // 3:02d}",
                    "valid_sentence_trials": 10 + (11 - subject_index),
                    "join_status": "VERIFIED",
                }
            )
    # This row exercises the conservative exclusion ledger without changing
    # the valid fixture population.
    records.append(
        {
            "record_id": "ambiguous|stim-99",
            "subject_id": "sub-01",
            "stimulus_id": "stim-99",
            "group_key": "unknown",
            "valid_sentence_trials": 1,
            "join_status": "AMBIGUOUS_DUPLICATE_TEXT",
            "source_slot": "nr:ambiguous",
        }
    )
    return records
