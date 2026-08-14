"""Frozen structural helpers for ROAMM ds007629 v1.3.0 admission.

The functions in this module are deterministic and do not train a model,
construct formal folds, sample candidates, or use ``is_mw`` in primary data
selection.  Real-file loading remains in ``audit_roamm_admission.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DATASET_ID = "ds007629"
DATASET_VERSION = "1.3.0"
DATASET_COMMIT = "15c38fd03740ff60008e0e309bf7b53883e2c36d"
DATASET_DOI = "10.18112/openneuro.ds007629.v1.3.0"
DATASET_LICENSE = "CC0"
AUTHOR_CODE_COMMIT = "77702115a8ff31f659363619b1baf2d9dae1a533"
STORIES = (
    "history_of_film",
    "pluto",
    "prisoners_dilemma",
    "serena_williams",
    "the_voynich_manuscript",
)
EXPECTED_SINGLE_PAGE = {
    "history_of_film": 86,
    "pluto": 88,
    "prisoners_dilemma": 93,
    "serena_williams": 91,
    "the_voynich_manuscript": 87,
}
EXPECTED_EEG_CHANNELS = (
    "Fp1", "AF7", "AF3", "F1", "F3", "F5", "F7", "FT7",
    "FC5", "FC3", "FC1", "C1", "C3", "C5", "T7", "TP7",
    "CP5", "CP3", "CP1", "P1", "P3", "P5", "P7", "P9",
    "PO7", "PO3", "O1", "Iz", "Oz", "POz", "Pz", "CPz",
    "Fpz", "Fp2", "AF8", "AF4", "Afz", "Fz", "F2", "F4",
    "F6", "F8", "FT8", "FC6", "FC4", "FC2", "FCz", "Cz",
    "C2", "C4", "C6", "T8", "TP8", "CP6", "CP4", "CP2",
    "P2", "P4", "P6", "P8", "P10", "PO8", "PO4", "O2",
)

SYNCED_RE = re.compile(
    r"^derivatives/synced/sub-(?P<subject>\d{5})/"
    r"sub-(?P=subject)_task-ReMind_run-0(?P<run>[1-5])_mldata\.pkl$"
)
RAW_RE = re.compile(
    r"^derivatives/raw_data/s(?P<subject>\d{5})/eeg/"
    r"MR_s(?P=subject)_r(?P<run>[1-5])\.bdf$"
)
EYE_RE = re.compile(
    r"^derivatives/raw_data/s(?P<subject>\d{5})/eye/.*_r(?P<run>[1-5])_"
)
LOG_RE = re.compile(
    r"^derivatives/raw_data/s(?P<subject>\d{5})/log/"
    r"(?P=subject)_R(?P<run>[1-5])_"
)
FLOW_RE = re.compile(
    r"^derivatives/raw_data/s(?P<subject>\d{5})/FlowSheet_.*"
)
ANNEX_RE = re.compile(
    r"^SHA256E-s(?P<size>\d+)--(?P<sha256>[0-9a-f]{64})(?:\..+)?$"
)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def manifest_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_yaml_text(value: Any) -> str:
    import yaml

    return yaml.safe_dump(
        value,
        allow_unicode=False,
        default_flow_style=False,
        sort_keys=True,
    )


def parse_synced_path(path: str) -> tuple[str, int]:
    match = SYNCED_RE.fullmatch(path)
    if not match:
        raise ValueError(f"invalid exact synced path: {path}")
    return match.group("subject"), int(match.group("run"))


def parse_raw_bdf_path(path: str) -> tuple[str, int]:
    match = RAW_RE.fullmatch(path)
    if not match:
        raise ValueError(f"invalid exact raw BDF path: {path}")
    return match.group("subject"), int(match.group("run"))


def _annex(entry: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if entry is None:
        return None
    match = ANNEX_RE.fullmatch(str(entry["id"]))
    return {
        "key": entry["id"],
        "size": int(entry["size"]),
        "sha256": match.group("sha256") if match else None,
        "annexed": bool(entry.get("annexed")),
    }


def build_subject_run_inventory(
    participant_ids: Sequence[str],
    file_entries: Sequence[Mapping[str, Any]],
    *,
    content_root: Path | None = None,
) -> dict[str, Any]:
    subjects = []
    for value in participant_ids:
        match = re.fullmatch(r"sub-(\d{5})", value)
        if not match:
            raise ValueError(f"invalid participant_id: {value}")
        subjects.append(match.group(1))
    if len(subjects) != len(set(subjects)):
        raise ValueError("duplicate participant_id")

    by_path = {str(entry["filename"]): entry for entry in file_entries if not entry.get("directory")}
    if len(by_path) != sum(not entry.get("directory") for entry in file_entries):
        raise ValueError("duplicate path in exact tree")

    indexed: dict[str, dict[tuple[str, int], list[str]]] = {
        "raw_bdf": defaultdict(list),
        "synced_pkl": defaultdict(list),
        "raw_eye": defaultdict(list),
        "log": defaultdict(list),
    }
    flows: dict[str, list[str]] = defaultdict(list)
    for path in sorted(by_path):
        for label, pattern in (
            ("raw_bdf", RAW_RE),
            ("synced_pkl", SYNCED_RE),
            ("raw_eye", EYE_RE),
            ("log", LOG_RE),
        ):
            match = pattern.match(path)
            if match:
                indexed[label][(match.group("subject"), int(match.group("run")))].append(path)
        flow = FLOW_RE.match(path)
        if flow:
            flows[flow.group("subject")].append(path)

    rows = []
    hard_failures = []
    auxiliary_anomalies = []
    for subject in sorted(subjects):
        for run in range(1, 6):
            key = (subject, run)
            row: dict[str, Any] = {"participant": f"sub-{subject}", "run": run}
            anomalies = []
            for label in ("raw_bdf", "synced_pkl", "raw_eye", "log"):
                paths = indexed[label].get(key, [])
                row[label] = paths[0] if len(paths) == 1 else None
                row[f"{label}_count"] = len(paths)
                if len(paths) != 1:
                    reason = f"{label}_count={len(paths)}"
                    anomalies.append(reason)
                    if label in {"raw_bdf", "synced_pkl"}:
                        hard_failures.append(f"sub-{subject}/run-{run}: {reason}")
                    else:
                        auxiliary_anomalies.append(f"sub-{subject}/run-{run}: {reason}")
            flow_paths = flows.get(subject, [])
            row["flowsheet"] = flow_paths[0] if len(flow_paths) == 1 else None
            row["flowsheet_count"] = len(flow_paths)
            if len(flow_paths) != 1:
                reason = f"flowsheet_count={len(flow_paths)}"
                anomalies.append(reason)
                auxiliary_anomalies.append(f"sub-{subject}/run-{run}: {reason}")
            for label in ("raw_bdf", "synced_pkl"):
                path = row[label]
                row[f"{label}_annex"] = _annex(by_path[path]) if path else None
                if content_root is None or path is None:
                    row[f"{label}_content_status"] = "NOT_CHECKED"
                else:
                    local = content_root / path
                    row[f"{label}_content_status"] = (
                        "PRESENT_SIZE_MATCH"
                        if local.is_file() and local.stat().st_size == int(by_path[path]["size"])
                        else "ABSENT_OR_SIZE_MISMATCH"
                    )
            row["anomaly_reason"] = ";".join(anomalies) if anomalies else None
            rows.append(row)

    return {
        "participant_count": len(subjects),
        "expected_cells": len(subjects) * 5,
        "rows": rows,
        "hard_failures": sorted(hard_failures),
        "auxiliary_anomalies": sorted(set(auxiliary_anomalies)),
        "raw_bdf_count": sum(row["raw_bdf_count"] for row in rows),
        "synced_pkl_count": sum(row["synced_pkl_count"] for row in rows),
        "raw_eye_count": sum(row["raw_eye_count"] for row in rows),
        "log_count": sum(row["log_count"] for row in rows),
        "flowsheet_subject_count": sum(len(value) == 1 for value in flows.values()),
    }


def audit_coordinates(
    story_rows: Mapping[str, Sequence[Mapping[str, Any]]]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if tuple(sorted(story_rows)) != tuple(sorted(STORIES)):
        raise ValueError("coordinate stories do not match the frozen five-story set")

    key_index: dict[str, dict[str, Any]] = {}
    sentence_text: dict[str, str] = {}
    sentence_story: dict[str, str] = {}
    sentence_pages: dict[str, set[int]] = defaultdict(set)
    pages_by_story: dict[str, set[int]] = defaultdict(set)
    row_counts = {}
    for story in STORIES:
        rows = story_rows[story]
        row_counts[story] = len(rows)
        for raw in rows:
            word_key = str(raw.get("word_key", ""))
            if not word_key:
                raise ValueError(f"empty word_key in {story}")
            if word_key in key_index:
                raise ValueError(f"duplicate word_key: {word_key}")
            sentence_id = str(raw.get("sentence_id", ""))
            sentence = str(raw.get("sentence", ""))
            if not sentence_id or not sentence:
                raise ValueError(f"empty sentence identity in {story}")
            page = int(raw["page"])
            if sentence_id in sentence_text and sentence_text[sentence_id] != sentence:
                raise ValueError(f"sentence_id maps to multiple texts: {sentence_id}")
            if sentence_id in sentence_story and sentence_story[sentence_id] != story:
                raise ValueError(f"sentence_id maps to multiple stories: {sentence_id}")
            sentence_text[sentence_id] = sentence
            sentence_story[sentence_id] = story
            sentence_pages[sentence_id].add(page)
            pages_by_story[story].add(page)
            key_index[word_key] = {
                "story": story,
                "page": page,
                "sentence_id": sentence_id,
                "sentence": sentence,
                "words": str(raw.get("words", "")),
                "word_key": word_key,
            }

    cross_page = sorted(key for key, pages in sentence_pages.items() if len(pages) > 1)
    single_page = sorted(key for key, pages in sentence_pages.items() if len(pages) == 1)
    per_story = {
        story: sum(sentence_story[key] == story for key in single_page) for story in STORIES
    }
    report = {
        "story_count": len(STORIES),
        "pages_per_story": {story: len(pages_by_story[story]) for story in STORIES},
        "coordinate_rows": sum(row_counts.values()),
        "coordinate_rows_per_story": row_counts,
        "unique_word_keys": len(key_index),
        "unique_sentences": len(sentence_text),
        "cross_page_sentence_count": len(cross_page),
        "cross_page_sentence_ids": cross_page,
        "single_page_sentence_count": len(single_page),
        "single_page_per_story": per_story,
        "single_page_sentence_ids": single_page,
    }
    expected = {
        "pages_per_story": {story: 10 for story in STORIES},
        "coordinate_rows": 10839,
        "unique_sentences": 487,
        "cross_page_sentence_count": 42,
        "single_page_sentence_count": 445,
        "single_page_per_story": EXPECTED_SINGLE_PAGE,
    }
    failures = [name for name, value in expected.items() if report[name] != value]
    report["frozen_count_failures"] = failures
    report["status"] = "PASS" if not failures else "FAIL"
    return report, key_index


def normalize_item(words: str) -> tuple[str | None, str | None]:
    normalized = unicodedata.normalize("NFKC", str(words).strip().casefold())
    if not normalized:
        return None, "empty_normalized"
    if not any(unicodedata.category(char).startswith("L") for char in normalized):
        return None, "no_unicode_letter"
    if normalized.isnumeric():
        return None, "pure_numeric"
    return f"roamm|remind|{normalized}", None


def construct_primary_records(
    events: Iterable[Mapping[str, Any]],
    coordinate_index: Mapping[str, Mapping[str, Any]],
    *,
    allowed_subjects: Iterable[str],
    allowed_stories: Iterable[str],
    page_offset: int,
) -> dict[str, Any]:
    allowed_subject_set = frozenset(allowed_subjects)
    allowed_story_set = frozenset(allowed_stories)
    event_seen = set()
    trial_rows: dict[str, dict[str, Any]] = {}
    observation_rows: dict[tuple[str, str], dict[str, Any]] = {}
    failure_rows = []
    item_rejections = []
    mw_counts = {"true": 0, "false": 0, "missing": 0}

    for raw in events:
        subject = str(raw["subject"])
        story = str(raw["story"])
        if subject not in allowed_subject_set or story not in allowed_story_set:
            continue
        if not bool(raw.get("first_pass_reading")):
            continue
        if not bool(raw.get("is_fix")) or not bool(raw.get("finite_eeg")):
            continue
        event_key = (
            subject,
            int(raw["run"]),
            float(raw["fix_start"]),
            float(raw["fix_end"]),
            str(raw.get("word_key", "")),
        )
        if event_key in event_seen:
            continue
        event_seen.add(event_key)
        word_key = event_key[-1]
        coordinate = coordinate_index.get(word_key)
        if coordinate is None:
            failure_rows.append({"event_key": list(event_key), "reason": "unknown_word_key"})
            continue
        if coordinate["story"] != story:
            failure_rows.append({"event_key": list(event_key), "reason": "story_mismatch"})
            continue
        if int(raw["page"]) - int(coordinate["page"]) != page_offset:
            failure_rows.append({"event_key": list(event_key), "reason": "page_mismatch"})
            continue
        item_id, reason = normalize_item(str(coordinate["words"]))
        if item_id is None:
            item_rejections.append({"word_key": word_key, "reason": reason})
            continue
        sentence_id = str(coordinate["sentence_id"])
        trial_id = f"roamm|{subject}|{int(raw['run'])}|{story}|{sentence_id}"
        trial_rows[trial_id] = {
            "trial_id": trial_id,
            "subject": subject,
            "run": int(raw["run"]),
            "story": story,
            "sentence_id": sentence_id,
        }
        observation_rows[(trial_id, item_id)] = {
            "trial_id": trial_id,
            "item_id": item_id,
            "subject": subject,
            "story": story,
            "sentence_id": sentence_id,
        }
        mw = raw.get("is_mw")
        label = "missing" if mw is None else ("true" if bool(mw) else "false")
        mw_counts[label] += 1

    trials = sorted(trial_rows.values(), key=lambda row: row["trial_id"])
    observations = sorted(
        observation_rows.values(), key=lambda row: (row["trial_id"], row["item_id"])
    )
    support = compute_support(
        observations,
        allowed_subjects=allowed_subject_set,
        allowed_stories=allowed_story_set,
    )
    primary = {"trials": trials, "observations": observations, "support": support}
    return {
        "primary": primary,
        "primary_sha256": manifest_hash(primary),
        "failure_ledger": sorted(
            failure_rows, key=lambda row: (row["reason"], row["event_key"])
        ),
        "item_rejections": sorted(
            item_rejections, key=lambda row: (row["reason"], row["word_key"])
        ),
        "mw_diagnostic_counts": mw_counts,
        "deduplicated_event_count": len(event_seen),
    }


def compute_support(
    observations: Iterable[Mapping[str, Any]],
    *,
    allowed_subjects: Iterable[str],
    allowed_stories: Iterable[str],
) -> dict[str, Any]:
    allowed_subject_set = frozenset(allowed_subjects)
    allowed_story_set = frozenset(allowed_stories)
    unique: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in observations:
        if row["subject"] not in allowed_subject_set or row["story"] not in allowed_story_set:
            continue
        unique[(str(row["trial_id"]), str(row["item_id"]))] = row
    item_trials: dict[str, set[str]] = defaultdict(set)
    item_subjects: dict[str, set[str]] = defaultdict(set)
    for (_, item_id), row in unique.items():
        item_trials[item_id].add(str(row["trial_id"]))
        item_subjects[item_id].add(str(row["subject"]))
    rows = []
    for item_id in sorted(item_trials):
        n_obs = len(item_trials[item_id])
        n_subjects = len(item_subjects[item_id])
        rows.append(
            {
                "item_id": item_id,
                "n_obs": n_obs,
                "n_subjects": n_subjects,
                "supported": n_obs >= 20 and n_subjects >= 5,
            }
        )
    supported = sum(row["supported"] for row in rows)
    rate = supported / len(rows) if rows else 0.0
    return {
        "items": rows,
        "item_count": len(rows),
        "supported_item_count": supported,
        "supported_item_rate": rate,
        "support_redline_status": "PASS" if rate >= 0.20 else "NO_GO",
        "unique_trial_item_observations": len(unique),
    }


def structural_n50(
    coordinate_report: Mapping[str, Any], supported_sentence_ids: Iterable[str]
) -> dict[str, Any]:
    supported = frozenset(supported_sentence_ids)
    rows = []
    for story in STORIES:
        count = int(coordinate_report["single_page_per_story"][story])
        legal_ids = [
            sentence_id
            for sentence_id in coordinate_report["single_page_sentence_ids"]
            if sentence_id.startswith(story + "_")
        ]
        rows.append(
            {
                "story": story,
                "legal_single_page_sentences": count,
                "structural_negative_upper_bound": count - 1,
                "supported_sentence_count": sum(value in supported for value in legal_ids),
                "status": "PASS" if count - 1 >= 49 else "BLOCK",
            }
        )
    return {
        "stories": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "BLOCK",
        "scope": "STRUCTURAL_UPPER_BOUND_ONLY",
        "full_n50_feasibility": "DELEGATED_TO_S0_CANDIDATES",
    }
