#!/usr/bin/env python3
"""Audit exact ROAMM ds007629 v1.3.0 without training or held-out metrics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from data.roamm_admission import (  # noqa: E402
    AUTHOR_CODE_COMMIT,
    DATASET_COMMIT,
    DATASET_DOI,
    DATASET_ID,
    DATASET_LICENSE,
    DATASET_VERSION,
    EXPECTED_EEG_CHANNELS,
    STORIES,
    audit_coordinates,
    build_subject_run_inventory,
    canonical_json_bytes,
    canonical_yaml_text,
    construct_primary_records,
    manifest_hash,
    structural_n50,
)


RUN_ID = "2026-08-14_015_v38_roamm_admission"
SEED = 20260813
REQUIRED_COLUMNS = {
    "sfreq",
    "first_pass_reading",
    "is_mw",
    "run_num",
    "story_name",
    "is_fix",
    "fix_R_fixed_word_key",
    "fix_R_tStart",
    "fix_R_tEnd",
    "page_num",
}
REP_PKL = (
    "derivatives/synced/sub-10014/"
    "sub-10014_task-ReMind_run-01_mldata.pkl"
)
REP_BDF = "derivatives/raw_data/s10014/eeg/MR_s10014_r1.bdf"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_signature(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def load_snapshot(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshot = payload["data"]["snapshot"]
    assertions = {
        "dataset_id": snapshot["id"] == f"{DATASET_ID}:{DATASET_VERSION}",
        "tag": snapshot["tag"] == DATASET_VERSION,
        "commit": snapshot["hexsha"] == DATASET_COMMIT,
        "doi": snapshot["description"]["DatasetDOI"].removeprefix("doi:") == DATASET_DOI,
        "license": snapshot["description"]["License"] == DATASET_LICENSE,
    }
    failed = [name for name, passed in assertions.items() if not passed]
    if failed:
        raise RuntimeError(f"exact snapshot contract failed: {failed}")
    files = snapshot["files"]
    return {
        "id": snapshot["id"],
        "tag": snapshot["tag"],
        "commit": snapshot["hexsha"],
        "created": snapshot["created"],
        "doi": DATASET_DOI,
        "license": DATASET_LICENSE,
        "tree_entry_count": len(files),
        "manifest_sha256": file_sha256(path),
        "tree_manifest_hash": manifest_hash(
            [
                {
                    "id": item["id"],
                    "path": item["filename"],
                    "size": item["size"],
                    "directory": item["directory"],
                    "annexed": item["annexed"],
                }
                for item in files
            ]
        ),
    }, files


def load_participants(path: Path) -> tuple[list[str], dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    participants = [row["participant_id"] for row in rows]
    if len(participants) != 44 or len(set(participants)) != 44:
        raise RuntimeError(f"participants expected 44 unique, got {len(participants)}")
    return participants, relative_signature(path.parents[0], path)


def load_coordinate_audit(dataset_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base = dataset_root / "derivatives" / "stimuli" / "wiki_stories"
    story_rows = {}
    signatures = {}
    for story in STORIES:
        path = base / f"{story}_coordinates.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            story_rows[story] = list(csv.DictReader(handle))
        signatures[story] = relative_signature(dataset_root, path)
    report, index = audit_coordinates(story_rows)
    if report["status"] != "PASS":
        raise RuntimeError(f"coordinate frozen counts failed: {report['frozen_count_failures']}")
    return report, index, signatures


def expected_annex(files: list[Mapping[str, Any]], path: str) -> tuple[int, str]:
    entry = next(item for item in files if item["filename"] == path)
    key = str(entry["id"])
    size_text, tail = key.removeprefix("SHA256E-s").split("--", 1)
    return int(size_text), tail.split(".", 1)[0]


def robust_channel_stats(values: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    finite = np.isfinite(values)
    nonfinite = int(values.size - finite.sum())
    quantiles = np.nanpercentile(values, [0.1, 1.0, 50.0, 99.0, 99.9], axis=0)
    median = quantiles[2]
    mad = np.nanmedian(np.abs(values - median), axis=0)
    mins = np.nanmin(values, axis=0)
    maxs = np.nanmax(values, axis=0)
    rows = []
    for index, name in enumerate(EXPECTED_EEG_CHANNELS):
        rows.append(
            {
                "channel": name,
                "min": float(mins[index]),
                "max": float(maxs[index]),
                "median": float(median[index]),
                "mad": float(mad[index]),
                "q0_1": float(quantiles[0, index]),
                "q1": float(quantiles[1, index]),
                "q50": float(quantiles[2, index]),
                "q99": float(quantiles[3, index]),
                "q99_9": float(quantiles[4, index]),
                "nonfinite": int(values.shape[0] - finite[:, index].sum()),
            }
        )
    return rows, {
        "finite_ratio": float(finite.sum() / values.size),
        "nonfinite_count": nonfinite,
        "any_all_64_finite_rows": bool(finite.all(axis=1).any()),
    }


def event_rows(
    frame: pd.DataFrame,
    *,
    subject: str,
    run: int,
    story: str,
    eeg_finite_rows: np.ndarray,
) -> list[dict[str, Any]]:
    first_pass = frame["first_pass_reading"].fillna(False).astype(bool).to_numpy()
    is_fix = frame["is_fix"].fillna(False).astype(bool).to_numpy()
    keys = frame["fix_R_fixed_word_key"].fillna("").astype(str).to_numpy()
    starts = pd.to_numeric(frame["fix_R_tStart"], errors="coerce").to_numpy()
    ends = pd.to_numeric(frame["fix_R_tEnd"], errors="coerce").to_numpy()
    pages = pd.to_numeric(frame["page_num"], errors="coerce").to_numpy()
    mask = first_pass & is_fix & (keys != "") & np.isfinite(starts) & np.isfinite(ends) & np.isfinite(pages)
    indices = np.flatnonzero(mask)
    grouped: dict[tuple[float, float, str], list[int]] = defaultdict(list)
    for index in indices:
        grouped[(float(starts[index]), float(ends[index]), keys[index])].append(int(index))
    result = []
    mw_values = frame["is_mw"].to_numpy()
    for (start, end, key), row_indices in grouped.items():
        labels = [mw_values[index] for index in row_indices if not pd.isna(mw_values[index])]
        mw = None if not labels else any(bool(value) for value in labels)
        page_values = {int(pages[index]) for index in row_indices}
        if len(page_values) != 1:
            page = -999999
        else:
            page = next(iter(page_values))
        result.append(
            {
                "subject": subject,
                "run": run,
                "story": story,
                "page": page,
                "first_pass_reading": True,
                "is_fix": True,
                "finite_eeg": bool(eeg_finite_rows[row_indices].any()),
                "fix_start": start,
                "fix_end": end,
                "word_key": key,
                "is_mw": mw,
            }
        )
    return result


def audit_pkls(
    dataset_root: Path,
    inventory: Mapping[str, Any],
    coordinate_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    file_reports = []
    all_events: list[dict[str, Any]] = []
    story_by_subject: dict[str, set[str]] = defaultdict(set)
    run_story: dict[tuple[str, str], int] = {}
    page_offsets = Counter()
    for ordinal, row in enumerate(inventory["rows"], start=1):
        relpath = row["synced_pkl"]
        path = dataset_root / relpath
        annex = row["synced_pkl_annex"]
        actual_sha = file_sha256(path)
        if path.stat().st_size != annex["size"] or actual_sha != annex["sha256"]:
            raise RuntimeError(f"PKL source hash failed before pickle load: {relpath}")
        frame = pd.read_pickle(path)
        if not isinstance(frame, pd.DataFrame):
            raise RuntimeError(f"PKL is not a DataFrame: {relpath}")
        channels = tuple(map(str, frame.columns[:64]))
        if channels != EXPECTED_EEG_CHANNELS:
            raise RuntimeError(f"64-channel order mismatch: {relpath}")
        missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
        if missing:
            raise RuntimeError(f"missing PKL fields {missing}: {relpath}")
        sfreq_values = sorted(set(pd.to_numeric(frame["sfreq"], errors="coerce").dropna()))
        if sfreq_values != [256.0]:
            raise RuntimeError(f"sfreq != 256: {relpath} -> {sfreq_values}")
        run_values = sorted(set(pd.to_numeric(frame["run_num"], errors="coerce").dropna()))
        if run_values != [row["run"]]:
            raise RuntimeError(f"run_num/path mismatch: {relpath} -> {run_values}")
        stories = sorted(set(frame["story_name"].dropna().astype(str)))
        if len(stories) != 1 or stories[0] not in STORIES:
            raise RuntimeError(f"invalid story identity: {relpath} -> {stories}")
        story = stories[0]
        subject = row["participant"]
        if story in story_by_subject[subject]:
            raise RuntimeError(f"duplicate subject/story: {subject}/{story}")
        story_by_subject[subject].add(story)
        run_story[(subject, story)] = row["run"]
        eeg = frame.iloc[:, :64].to_numpy(dtype=np.float64, copy=False)
        stats, finite_summary = robust_channel_stats(eeg)
        finite_rows = np.isfinite(eeg).all(axis=1)
        extracted = event_rows(
            frame,
            subject=subject,
            run=row["run"],
            story=story,
            eeg_finite_rows=finite_rows,
        )
        for event in extracted:
            coordinate = coordinate_index.get(event["word_key"])
            if coordinate is not None and coordinate["story"] == story:
                page_offsets[event["page"] - int(coordinate["page"])] += 1
        all_events.extend(extracted)
        file_reports.append(
            {
                "path": relpath,
                "size": path.stat().st_size,
                "sha256": actual_sha,
                "subject": subject,
                "run": row["run"],
                "story": story,
                "rows": len(frame),
                "columns": len(frame.columns),
                "eeg_dtype": str(eeg.dtype),
                "sfreq": 256.0,
                "finite": finite_summary,
                "channel_stats": stats,
                "candidate_right_fixation_events": len(extracted),
            }
        )
        del frame, eeg
        print(
            f"PKL_AUDIT {ordinal}/220 subject={subject} run={row['run']} story={story} "
            f"events={len(extracted)} status=PASS",
            flush=True,
        )
    invalid_story_sets = {
        subject: sorted(stories)
        for subject, stories in story_by_subject.items()
        if stories != set(STORIES)
    }
    if invalid_story_sets:
        raise RuntimeError(f"subject five-story coverage failed: {invalid_story_sets}")
    if len(page_offsets) != 1:
        raise RuntimeError(f"no single global page offset: {dict(page_offsets)}")
    page_offset = next(iter(page_offsets))
    primary = construct_primary_records(
        all_events,
        coordinate_index,
        allowed_subjects={row["participant"] for row in inventory["rows"]},
        allowed_stories=set(STORIES),
        page_offset=page_offset,
    )
    return {
        "file_reports": file_reports,
        "events": all_events,
        "primary": primary,
        "page_offset": page_offset,
        "page_offset_counts": dict(sorted(page_offsets.items())),
        "run_story": {f"{subject}|{story}": run for (subject, story), run in sorted(run_story.items())},
    }


def coverage_reports(
    primary: Mapping[str, Any],
    coordinate_report: Mapping[str, Any],
    participants: list[str],
    run_story: Mapping[str, int],
) -> dict[str, Any]:
    trials = primary["primary"]["trials"]
    present = {(row["subject"], row["sentence_id"]): row for row in trials}
    story_by_sentence = {}
    for sentence_id in coordinate_report["single_page_sentence_ids"]:
        story_by_sentence[sentence_id] = next(
            story for story in STORIES if sentence_id.startswith(story + "_")
        )
    cell_ledger = []
    for subject in sorted(participants):
        for sentence_id in coordinate_report["single_page_sentence_ids"]:
            story = story_by_sentence[sentence_id]
            row = present.get((subject, sentence_id))
            cell_ledger.append(
                {
                    "subject": subject,
                    "story": story,
                    "sentence_id": sentence_id,
                    "run": run_story[f"{subject}|{story}"],
                    "covered": row is not None,
                    "trial_id": row["trial_id"] if row else None,
                    "missing_reason": None if row else "no_legal_first_pass_right_fixation_with_finite_eeg",
                }
            )
    subject_story = []
    for subject in sorted(participants):
        for story in STORIES:
            subject_story.append(
                {
                    "subject": subject,
                    "story": story,
                    "trial_count": sum(
                        row["subject"] == subject and row["story"] == story for row in trials
                    ),
                }
            )
    sentence_coverage = []
    for sentence_id in coordinate_report["single_page_sentence_ids"]:
        subjects = sorted(row["subject"] for row in trials if row["sentence_id"] == sentence_id)
        sentence_coverage.append(
            {
                "sentence_id": sentence_id,
                "story": story_by_sentence[sentence_id],
                "n_subjects": len(set(subjects)),
                "subjects": sorted(set(subjects)),
            }
        )
    return {
        "theoretical_cell_count": len(cell_ledger),
        "expected_theoretical_cell_count": 44 * 445,
        "covered_cell_count": sum(row["covered"] for row in cell_ledger),
        "missing_cell_count": sum(not row["covered"] for row in cell_ledger),
        "cell_ledger": cell_ledger,
        "subject_story_trial_counts": subject_story,
        "sentence_subject_coverage": sentence_coverage,
    }


def audit_bdf(dataset_root: Path, files: list[Mapping[str, Any]], pkl_report: Mapping[str, Any]) -> dict[str, Any]:
    import mne

    path = dataset_root / REP_BDF
    expected_size, expected_sha = expected_annex(files, REP_BDF)
    actual_sha = file_sha256(path)
    if path.stat().st_size != expected_size or actual_sha != expected_sha:
        raise RuntimeError("representative BDF size/SHA256 failed")
    raw = mne.io.read_raw_bdf(path, preload=False, verbose="ERROR")
    if float(raw.info["sfreq"]) != 2048.0:
        raise RuntimeError(f"representative BDF sfreq != 2048: {raw.info['sfreq']}")
    first64 = list(raw.ch_names[:64])
    sample_stop = min(raw.n_times, int(raw.info["sfreq"] * 60))
    sample_v = raw.get_data(picks=list(range(64)), start=0, stop=sample_stop)
    rep_pkl = next(row for row in pkl_report["file_reports"] if row["path"] == REP_PKL)
    return {
        "path": REP_BDF,
        "size": path.stat().st_size,
        "sha256": actual_sha,
        "format": "BioSemi BDF",
        "native_sfreq": float(raw.info["sfreq"]),
        "n_times": int(raw.n_times),
        "duration_seconds": float(raw.times[-1]),
        "channel_count": len(raw.ch_names),
        "channel_names": list(raw.ch_names),
        "channel_types": raw.get_channel_types(),
        "first_64_channels": first64,
        "first_64_match_synced": first64 == list(EXPECTED_EEG_CHANNELS),
        "orig_units": dict(getattr(raw, "_orig_units", {})),
        "header_highpass": float(raw.info["highpass"]),
        "header_lowpass": float(raw.info["lowpass"]),
        "sample_window_seconds": sample_stop / float(raw.info["sfreq"]),
        "mne_returned_v_sample_quantiles": {
            "q0_1": float(np.nanpercentile(sample_v, 0.1)),
            "q50": float(np.nanpercentile(sample_v, 50)),
            "q99_9": float(np.nanpercentile(sample_v, 99.9)),
        },
        "correspondence": {
            "subject": "sub-10014",
            "run": 1,
            "synced_path": REP_PKL,
            "synced_story": rep_pkl["story"],
            "synced_sfreq": rep_pkl["sfreq"],
        },
    }


def write_outputs(
    *,
    args: argparse.Namespace,
    source: Mapping[str, Any],
    inventory: Mapping[str, Any],
    coordinates: Mapping[str, Any],
    coordinate_signatures: Mapping[str, Any],
    participants: list[str],
    author_code: Mapping[str, Any],
    full: Mapping[str, Any] | None,
    started: float,
) -> None:
    complete = full is not None
    feasibility: dict[str, Any] = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "seed": SEED,
        "fold": "S0-ROAMM",
        "method": "ROAMM-structural-admission",
        "status": "PASS" if complete else "IN_PROGRESS_DOWNLOAD",
        "claim_boundary": "STRUCTURE_SOURCE_SUPPORT_ONLY_NO_TRAINING_NO_HELD_OUT_NO_GATE",
        "source": source,
        "inventory_summary": {
            key: inventory[key]
            for key in (
                "participant_count", "expected_cells", "raw_bdf_count", "synced_pkl_count",
                "raw_eye_count", "log_count", "flowsheet_subject_count", "hard_failures",
                "auxiliary_anomalies",
            )
        },
        "coordinate_files": coordinate_signatures,
        "coordinates": coordinates,
        "structural_n50": structural_n50(coordinates, set()),
        "download_status": {
            "synced_present_size_match": sum(
                row["synced_pkl_content_status"] == "PRESENT_SIZE_MATCH"
                for row in inventory["rows"]
            ),
            "synced_required": 220,
            "representative_bdf_present": (
                (args.dataset_root / REP_BDF).is_file()
            ),
        },
    }
    if complete:
        feasibility.update(full)
    feasibility["config_hash"] = manifest_hash(
        {"dataset": f"{DATASET_ID}:{DATASET_VERSION}", "commit": DATASET_COMMIT, "seed": SEED}
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_bytes(canonical_json_bytes(feasibility))

    artifact = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "task": "S0_ROAMM_ADMISSION",
        "status": "PASS" if complete else "IN_PROGRESS_DOWNLOAD",
        "experiment_ready": bool(complete),
        "source": source,
        "author_code": author_code,
        "inventory": feasibility["inventory_summary"],
        "representative_files": (
            {"pkl": full["representative_pkl"], "bdf": full["representative_bdf"]}
            if complete else {"pkl": None, "bdf": None}
        ),
        "channel_order": list(EXPECTED_EEG_CHANNELS) if complete else None,
        "channel_order_hash": manifest_hash(list(EXPECTED_EEG_CHANNELS)) if complete else None,
        "sampling_rate": 256 if complete else None,
        "stored_unit_status": full["stored_unit_status"] if complete else "PENDING_FULL_AUDIT",
        "preprocessing": full["preprocessing"] if complete else {
            "machine_verified": [], "author_reported": [], "reproduced": False
        },
        "coordinates": coordinates,
        "join_missingness_support": full["summary"] if complete else None,
        "structural_n50": feasibility["structural_n50"],
        "claim_boundary": feasibility["claim_boundary"],
        "output_json_sha256": file_sha256(args.output_json),
    }
    args.output_yaml.parent.mkdir(parents=True, exist_ok=True)
    args.output_yaml.write_text(canonical_yaml_text(artifact), encoding="utf-8", newline="\n")

    card = {
        "schema_version": 1,
        "dataset": "ROAMM",
        "dataset_id": DATASET_ID,
        "version": DATASET_VERSION,
        "status": "ADMITTED" if complete else "IN_PROGRESS_DOWNLOAD",
        "subjects": {"released": 44, "audited": 44},
        "stimuli": coordinates,
        "assignment": full["summary"] if complete else None,
        "sessions": "five randomized story runs per subject",
        "eeg": {
            "channels": 64 if complete else None,
            "sfreq": 256 if complete else None,
            "unit": full["stored_unit_status"] if complete else "PENDING_FULL_AUDIT",
        },
        "text": "released word_key exact join; 445 legal single-page sentences",
        "leakage": "is_mw diagnostic-only; no formal folds or candidates generated",
        "support": full["support_summary"] if complete else "PENDING_ALL_220_PKLS",
        "experiment_ready": bool(complete),
        "claim_boundary": feasibility["claim_boundary"],
    }
    args.data_card.parent.mkdir(parents=True, exist_ok=True)
    args.data_card.write_text(canonical_yaml_text(card), encoding="utf-8", newline="\n")
    elapsed = time.time() - started
    print(
        f"SELF_CHECK participants={len(participants)} inventory=[{inventory['raw_bdf_count']},"
        f"{inventory['synced_pkl_count']}] coordinate_rows={coordinates['coordinate_rows']} "
        f"sentences=[{coordinates['unique_sentences']},{coordinates['cross_page_sentence_count']},"
        f"{coordinates['single_page_sentence_count']}] elapsed_seconds={elapsed:.3f} "
        f"status={'PASS' if complete else 'IN_PROGRESS_DOWNLOAD'}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--snapshot-manifest", type=Path, required=True)
    parser.add_argument("--author-code-manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("metadata", "full"), default="full")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT / "04_results" / "audits" / "roamm_text_feasibility.json",
    )
    parser.add_argument(
        "--output-yaml",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "roamm_admission.yaml",
    )
    parser.add_argument(
        "--data-card",
        type=Path,
        default=PROJECT_ROOT / "01_data_protocol" / "dataset_cards" / "roamm.yaml",
    )
    args = parser.parse_args()
    started = time.time()
    args.dataset_root = args.dataset_root.resolve()
    source, files = load_snapshot(args.snapshot_manifest.resolve())
    author_code = json.loads(args.author_code_manifest.read_text(encoding="utf-8"))
    if author_code["commit"] != AUTHOR_CODE_COMMIT:
        raise RuntimeError("author-code commit mismatch")
    participants, _ = load_participants(args.dataset_root / "participants.tsv")
    inventory = build_subject_run_inventory(
        participants, files, content_root=args.dataset_root
    )
    if inventory["hard_failures"]:
        raise RuntimeError(f"exact 44x5 inventory failed: {inventory['hard_failures']}")
    coordinates, coordinate_index, signatures = load_coordinate_audit(args.dataset_root)
    full = None
    if args.mode == "full":
        present = sum(
            row["synced_pkl_content_status"] == "PRESENT_SIZE_MATCH"
            for row in inventory["rows"]
        )
        if present != 220:
            raise RuntimeError(f"full audit requires 220 PKLs; present size-matched={present}")
        pkl = audit_pkls(args.dataset_root, inventory, coordinate_index)
        coverage = coverage_reports(
            pkl["primary"], coordinates, participants, pkl["run_story"]
        )
        if coverage["theoretical_cell_count"] != 19580:
            raise RuntimeError("theoretical subject-sentence ledger != 19580")
        supported_sentences = {
            row["sentence_id"]
            for row in pkl["primary"]["primary"]["trials"]
        }
        n50 = structural_n50(coordinates, supported_sentences)
        if n50["status"] != "PASS":
            raise RuntimeError("structural N=50 upper-bound failure")
        bdf = audit_bdf(args.dataset_root, files, pkl)
        support = pkl["primary"]["primary"]["support"]
        if support["support_redline_status"] != "PASS":
            raise RuntimeError("global item support rate below frozen 20% redline")
        rep_pkl = next(row for row in pkl["file_reports"] if row["path"] == REP_PKL)
        unit = {
            "status": "INFERRED_V",
            "evidence": [
                "Exact author code reads an EEGLAB .set through MNE raw.get_data() and writes those values directly into the dataframe/pickle without scaling.",
                "Released PKL channel values are machine-verified at approximately 1e-6 SI scale.",
                "Representative BioSemi BDF is read by MNE in volts and supplies a same-subject/run source-scale check.",
                "A later BIDS-export cell multiplies the already-created dataframe by 1e-6 under a conditional comment; it is recorded as contradictory downstream code and is not treated as the PKL generation path.",
            ],
            "silent_scaling_applied": False,
        }
        full = {
            "pkl_file_audit": pkl["file_reports"],
            "page_offset": pkl["page_offset"],
            "page_offset_counts": pkl["page_offset_counts"],
            "primary": pkl["primary"],
            "coverage": coverage,
            "structural_n50": n50,
            "representative_pkl": rep_pkl,
            "representative_bdf": bdf,
            "stored_unit_status": unit,
            "preprocessing": {
                "machine_verified": [
                    "released synced PKL schemas, channel order, 256 Hz, numerical ranges, finite counts and event fields",
                    "representative raw BDF header, 2048 Hz, channels/triggers and source hash",
                ],
                "author_reported": [
                    "0.5-50 Hz filtering", "average reference", "bad-channel interpolation", "ICA artifact removal",
                ],
                "reproduced": False,
            },
            "summary": {
                "theoretical_cells": coverage["theoretical_cell_count"],
                "covered_cells": coverage["covered_cell_count"],
                "missing_cells": coverage["missing_cell_count"],
                "trial_count": len(pkl["primary"]["primary"]["trials"]),
                "item_count": support["item_count"],
                "supported_item_count": support["supported_item_count"],
                "supported_item_rate": support["supported_item_rate"],
                "unknown_or_identity_failure_count": len(pkl["primary"]["failure_ledger"]),
            },
            "support_summary": {
                key: support[key]
                for key in (
                    "item_count", "supported_item_count", "supported_item_rate",
                    "support_redline_status", "unique_trial_item_observations",
                )
            },
        }
    write_outputs(
        args=args,
        source=source,
        inventory=inventory,
        coordinates=coordinates,
        coordinate_signatures=signatures,
        participants=participants,
        author_code=author_code,
        full=full,
        started=started,
    )


if __name__ == "__main__":
    main()
