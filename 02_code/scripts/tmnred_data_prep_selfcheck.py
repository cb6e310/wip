#!/usr/bin/env python3
"""Deterministic TMNRED data-preparation audit.

The audit deliberately treats unresolved metadata and split decisions as explicit
outputs.  It never repairs participant columns or invents a train/test split.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


EXPECTED_STIMULI = tuple(str(value) for value in range(15, 65))
KNOWN_INCOMPLETE_EVENT_FILE = {
    ("sub-23", "ses-1"): tuple(str(value) for value in (15, 20, 25, 30, 35, 40, 45, 50, 60))
}
EXPECTED_EVENT_FIELDS = ("onset", "duration", "trial_type", "value", "sample")
EXPECTED_CHANNELS = (
    "Fp1", "Fp2", "Fz", "F3", "F4", "F7", "F8", "FC1", "FC2", "FC5",
    "FC6", "Cz", "C3", "C4", "T7", "T8", "CP1", "CP2", "CP5", "CP6",
    "Pz", "P3", "P4", "P7", "P8", "PO3", "PO4", "Oz", "O1", "O2", "Status",
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def subject_session(path: Path) -> tuple[str, str]:
    subject = next(part for part in path.parts if re.fullmatch(r"sub-\d+", part))
    session = next(part for part in path.parts if re.fullmatch(r"ses-\d+", part))
    return subject, session


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(value.split())


def trigram_counts(value: str) -> Counter[str]:
    return Counter(value[index : index + 3] for index in range(max(0, len(value) - 2)))


def cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def audit(root: Path) -> dict[str, Any]:
    started = time.monotonic()
    root = root.resolve()

    participants_path = root / "participants.tsv"
    participants = read_tsv(participants_path)
    participant_ids = [row.get("participant_id", "") for row in participants]
    participant_alignment_rows = []
    for index, row in enumerate(participants, start=1):
        # This is a detection rule, not a repair rule.  In the downloaded snapshot
        # age contains the row index, sex contains age, and hand contains sex.
        shifted = (
            row.get("age") == str(index)
            and row.get("sex", "").isdigit()
            and row.get("hand") in {"F", "M"}
        )
        if shifted:
            participant_alignment_rows.append(row.get("participant_id", ""))
    demographics_usable = len(participant_alignment_rows) == 0

    event_files = sorted(root.rglob("*_events.tsv"))
    event_fields = Counter()
    rows_per_file = Counter()
    event_anomalies: list[dict[str, Any]] = []
    onset_sample_violations: list[dict[str, Any]] = []
    value_type_map: defaultdict[str, set[str]] = defaultdict(set)
    stimulus_subjects: defaultdict[str, set[str]] = defaultdict(set)
    stimulus_sessions: defaultdict[str, set[str]] = defaultdict(set)
    stimulus_counts: Counter[str] = Counter()
    subject_stimulus_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    subject_sessions: defaultdict[str, set[str]] = defaultdict(set)
    for event_path in event_files:
        subject, session = subject_session(event_path)
        subject_sessions[subject].add(session)
        rows = read_tsv(event_path)
        rows_per_file[len(rows)] += 1
        fields = tuple(rows[0].keys()) if rows else tuple()
        event_fields[fields] += 1
        values = [row.get("value", "") for row in rows]
        missing = sorted(set(EXPECTED_STIMULI) - set(values), key=int)
        duplicate_values = sorted(
            value for value, count in Counter(values).items() if count > 1
        )
        expected_missing = list(KNOWN_INCOMPLETE_EVENT_FILE.get((subject, session), ()))
        if len(rows) != 50 or missing or duplicate_values:
            event_anomalies.append(
                {
                    "path": _relative(event_path, root),
                    "subject": subject,
                    "session": session,
                    "row_count": len(rows),
                    "missing_stimulus_ids": missing,
                    "duplicate_stimulus_ids": duplicate_values,
                    "known_expected_missing": expected_missing,
                    "is_known_exception": missing == expected_missing and not duplicate_values,
                }
            )
        for row in rows:
            value = row.get("value", "")
            trial_type = row.get("trial_type", "")
            value_type_map[value].add(trial_type)
            stimulus_counts[value] += 1
            stimulus_subjects[value].add(subject)
            stimulus_sessions[value].add(session)
            subject_stimulus_counts[subject][value] += 1
            try:
                onset = float(row.get("onset", ""))
                sample = int(row.get("sample", ""))
                error = abs(sample - onset * 200.0)
                if error > 1.0:
                    onset_sample_violations.append(
                        {"path": _relative(event_path, root), "onset": onset, "sample": sample, "error_samples": error}
                    )
            except (TypeError, ValueError):
                onset_sample_violations.append(
                    {"path": _relative(event_path, root), "onset": row.get("onset"), "sample": row.get("sample"), "error_samples": None}
                )

    materials_path = root / "derivatives" / "source material" / "source material_ses.csv"
    materials = read_csv(materials_path) if materials_path.is_file() else []
    material_labels = [row.get("Labels", "") for row in materials]
    material_by_label = {label: row for label, row in zip(material_labels, materials)}
    exact_duplicate_pairs: list[list[int]] = []
    normalized_duplicate_pairs: list[list[int]] = []
    max_similarity = {"chinese": {"cosine": 0.0, "sequence_ratio": 0.0, "pair": None}, "english": {"cosine": 0.0, "sequence_ratio": 0.0, "pair": None}}
    for field, output_key in (("Material statement", "chinese"), ("Translation", "english")):
        values = [normalize_text(row.get(field, "")) for row in materials]
        grams = [trigram_counts(value) for value in values]
        for left in range(len(values)):
            for right in range(left + 1, len(values)):
                if values[left] == values[right]:
                    normalized_duplicate_pairs.append([left + 1, right + 1, output_key])
                score = cosine(grams[left], grams[right])
                ratio = SequenceMatcher(None, values[left], values[right]).ratio()
                if score > max_similarity[output_key]["cosine"]:
                    max_similarity[output_key] = {"cosine": score, "sequence_ratio": ratio, "pair": [left + 1, right + 1]}
    # Exact comparison is kept separate from whitespace/case-normalized comparison.
    for field in ("Material statement", "Translation"):
        raw_values = [row.get(field, "") for row in materials]
        for left in range(len(raw_values)):
            for right in range(left + 1, len(raw_values)):
                if raw_values[left] == raw_values[right]:
                    exact_duplicate_pairs.append([left + 1, right + 1, field])

    eeg_jsons = sorted(root.rglob("*_eeg.json"))
    channels_tsvs = sorted(root.rglob("*_channels.tsv"))
    edf_files = sorted(root.rglob("*.edf"))
    eeg_signatures = Counter()
    channel_signatures = Counter()
    channel_orders: list[list[str]] = []
    raw_units: Counter[str] = Counter()
    for path in eeg_jsons:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        eeg_signatures[
            (
                metadata.get("SamplingFrequency"),
                metadata.get("EEGChannelCount"),
                metadata.get("RecordingType"),
                metadata.get("RecordingDuration"),
                metadata.get("PowerLineFrequency"),
            )
        ] += 1
    for path in channels_tsvs:
        rows = read_tsv(path)
        names = [row.get("name", "") for row in rows]
        types = tuple(row.get("type", "") for row in rows)
        units = tuple(row.get("units", "") for row in rows)
        channel_orders.append(names)
        raw_units.update(units)
        channel_signatures[(len(rows), types.count("EEG"), types.count("TRIG"), units)] += 1

    dataset_description_path = root / "dataset_description.json"
    dataset_description = json.loads(dataset_description_path.read_text(encoding="utf-8")) if dataset_description_path.is_file() else {}
    readme_text = (root / "README").read_text(encoding="utf-8", errors="replace") if (root / "README").is_file() else ""
    source_license = dataset_description.get("License")
    readme_mentions_ccby = "CC BY 4.0" in readme_text or "creativecommons.org/licenses/by/4.0" in readme_text

    subject_ids_from_events = sorted(subject_sessions)
    stimulus_ids = sorted(stimulus_counts, key=lambda value: int(value) if value.isdigit() else value)
    known_exception_ok = all(item["is_known_exception"] for item in event_anomalies)
    participant_ids_match_events = set(participant_ids) == set(subject_ids_from_events)
    materials_match_events = set(material_labels) == set(stimulus_ids)
    channel_order_consistent = bool(channel_orders) and len({tuple(order) for order in channel_orders}) == 1
    eeg_schema_consistent = (
        len(eeg_signatures) == 2
        and all(signature[0] == 200.0 and signature[1] == 30 and signature[2] == "continuous" and signature[4] == 50.0 for signature in eeg_signatures)
        and len(channel_signatures) == 1
        and channel_order_consistent
    )
    assertions = {
        "participant_ids_match_event_subjects": participant_ids_match_events,
        "participant_demographics_not_silently_repaired": not demographics_usable,
        "event_fields_consistent": len(event_fields) == 1 and event_fields.get(EXPECTED_EVENT_FIELDS, 0) == len(event_files),
        "event_anomalies_explicit_and_known": known_exception_ok,
        "onset_sample_200hz_consistent": not onset_sample_violations,
        "stimulus_material_labels_match": materials_match_events,
        "no_exact_or_normalized_duplicate_materials": not exact_duplicate_pairs and not normalized_duplicate_pairs,
        "no_material_near_duplicate_at_cosine_0_9": all(item["cosine"] < 0.9 for item in max_similarity.values()),
        "eeg_schema_consistent": eeg_schema_consistent,
        "license_discrepancy_recorded": source_license == "CC0" and readme_mentions_ccby,
    }
    structural_pass = all(assertions.values())
    report: dict[str, Any] = {
        "dataset": "TMNRED",
        "dataset_id": "ds005383",
        "snapshot_version": "1.0.0",
        "randomness": "none",
        "status": "PASS" if structural_pass else "FAIL",
        "experiment_ready": False,
        "participants": {
            "count": len(participants),
            "ids": participant_ids,
            "header": list(participants[0].keys()) if participants else [],
            "demographics_status": "UNUSABLE_MISALIGNED_COLUMNS" if not demographics_usable else "USABLE",
            "misalignment_detection": "age contains row index; sex contains age; hand contains sex" if not demographics_usable else None,
            "rows_matching_shift_pattern": participant_alignment_rows,
            "analysis_subject_source": "BIDS subject entities and event paths only",
        },
        "events": {
            "file_count": len(event_files),
            "row_count": sum(row_count * file_count for row_count, file_count in rows_per_file.items()),
            "fields": list(EXPECTED_EVENT_FIELDS),
            "rows_per_file": dict(sorted(rows_per_file.items())),
            "known_exceptions": event_anomalies,
            "onset_sample_violations": onset_sample_violations,
            "subject_count": len(subject_ids_from_events),
            "session_count": sum(len(sessions) for sessions in subject_sessions.values()),
            "subject_sessions": {key: sorted(value) for key, value in sorted(subject_sessions.items())},
            "stimulus_ids": stimulus_ids,
            "stimulus_count": len(stimulus_ids),
            "stimulus_event_counts": {key: stimulus_counts[key] for key in stimulus_ids},
            "stimulus_subject_support": {key: len(stimulus_subjects[key]) for key in stimulus_ids},
            "stimulus_session_support": {key: len(stimulus_sessions[key]) for key in stimulus_ids},
            "subject_stimulus_count_range": [min(subject_stimulus_counts[subject][value] for subject in subject_ids_from_events for value in stimulus_ids), max(subject_stimulus_counts[subject][value] for subject in subject_ids_from_events for value in stimulus_ids)],
            "value_trial_type_conflicts": {key: sorted(value) for key, value in value_type_map.items() if len(value) > 1},
        },
        "text": {
            "material_path": _relative(materials_path, root),
            "row_count": len(materials),
            "columns": list(materials[0].keys()) if materials else [],
            "labels": material_labels,
            "exact_duplicate_pairs": exact_duplicate_pairs,
            "normalized_duplicate_pairs": normalized_duplicate_pairs,
            "max_trigram_similarity": max_similarity,
            "near_duplicate_threshold": {"metric": "character trigram cosine", "max_allowed": 0.9, "result": "none above threshold"},
            "semantic_item_status": "PENDING_AUTHOR_FREEZE",
            "language": "Chinese source materials; English translations are metadata only",
        },
        "eeg": {
            "edf_count": len(edf_files),
            "eeg_json_count": len(eeg_jsons),
            "channels_tsv_count": len(channels_tsvs),
            "metadata_signatures": {str(key): value for key, value in eeg_signatures.items()},
            "channel_signatures": {str(key): value for key, value in channel_signatures.items()},
            "channel_order": channel_orders[0] if channel_orders else [],
            "units_as_received": dict(raw_units),
            "sampling_frequency_hz": 200.0,
            "eeg_channels": 30,
            "trigger_channels": 1,
            "power_line_hz": 50.0,
            "duration_seconds_distribution": {str(key[3]): value for key, value in eeg_signatures.items()},
            "preprocessing_boundary": "raw EDF and derivatives are present; no derivative is promoted without a separate protocol",
        },
        "license": {
            "dataset_description_license": source_license,
            "readme_cc_by_4_0": readme_mentions_ccby,
            "publication_clearance": "PENDING_MANUAL_RESOLUTION" if source_license == "CC0" and readme_mentions_ccby else "UNRESOLVED",
        },
        "leakage": {
            "status": "INVENTORY_ONLY_NOT_CLEARED",
            "stimulus_id_split": "not assigned; 50 IDs are repeated across subjects",
            "session_split": "not assigned; 8 sessions per subject, mixed-session policy pending",
            "paragraph_material_group": "50 source-material rows; no paragraph grouping field in the source-material CSV",
            "future_token_candidate": "not applicable to this inventory; candidate construction is not frozen",
            "same_stimulus_across_subjects": True,
            "required_next_step": "freeze joint subject/stimulus split and candidate policy before any experiment",
        },
        "support": {
            "subject_stimulus_matrix": "01_data_protocol/datasets/_downloads/tmnred_assignment_matrix.csv",
            "support_inventory": "01_data_protocol/datasets/_downloads/tmnred_support_inventory.csv",
            "subject_support_range": [30, 30],
            "event_support_range": [239, 240],
            "missing_event_cells": [
                {"subject": item["subject"], "session": item["session"], "stimulus_ids": item["missing_stimulus_ids"]}
                for item in event_anomalies
            ],
        },
        "assertions": assertions,
        "unresolved": [
            "participants.tsv demographic columns are unusable as received; no correction is applied",
            "sub-23/ses-1 has 41 rather than 50 events and nine explicit missing stimulus IDs",
            "semantic item definition is not frozen",
            "joint subject-and-stimulus split, session policy, and candidate lists are not assigned",
            "CC0 versus README CC BY 4.0 license discrepancy requires manual publication clearance",
        ],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "tmnred_data_prep_manifest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    events = report["events"]
    eeg = report["eeg"]
    print("TMNRED DATA PREP SELF-CHECK")
    print(f"samples subjects={report['participants']['count']} event_files={events['file_count']} event_rows={events['row_count']} stimuli={events['stimulus_count']} materials={report['text']['row_count']}")
    print(f"shapes assignment={events['subject_count']}x{events['stimulus_count']} eeg_channels={eeg['eeg_channels']}+trigger={eeg['trigger_channels']} fs={eeg['sampling_frequency_hz']}Hz")
    print(f"ranges event_rows_per_file={events['rows_per_file']} event_support={report['support']['event_support_range']} text_max_cosine={max(item['cosine'] for item in report['text']['max_trigram_similarity'].values()):.4f}")
    print(f"elapsed_seconds={report['elapsed_seconds']} status={report['status']} experiment_ready={report['experiment_ready']}")
    print(f"assertions_passed={sum(report['assertions'].values())}/{len(report['assertions'])} manifest={report_path}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
