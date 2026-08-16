"""Strict ZuCo 2.0 source admission for the frozen A1 frontend.

This module audits release identity and source facts only.  It never fits the
fold-local normalizer, constructs a torch model, or computes an outcome metric.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import h5py
import numpy as np

from backbones.a1_spectral import (
    DEFAULT_CONFIG,
    analysis_spectrum_phase_rotation_features,
    bandpower_features,
    config_hash as a1_config_hash,
    extract_fixed_window_sequence,
    extract_word_level_sequence,
)
from data.zuco2_loader import TASKS, dereference, indexed_value, iter_summary_files
from data.zuco2_source_join import prove_task_source_join


SCHEMA_VERSION = 1
ALGORITHM_VERSION = "zuco2-a1-source-admission-v313-q3-v1"
DEFAULT_SEED = 20260813
EXPECTED_CHANNELS = 105
EXPECTED_SAMPLING_HZ = 500.0
PHASE_RTOL = 1e-5
PHASE_ATOL = 1e-7
OFFICIAL_ACQUISITION_EVIDENCE = {
    "title": "ZuCo 2.0: A Dataset of Physiological Recordings During Natural Reading and Annotation",
    "url": "https://www.research-collection.ethz.ch/handle/20.500.11850/353427",
    "statement": "EEG acquired with a 128-channel Geodesic Hydrocel system at 500 Hz",
}


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_gzip_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    ordered = sorted(rows, key=lambda row: canonical_json_bytes(row))
    raw = b"".join(canonical_json_bytes(row, newline=True) for row in ordered)
    return gzip.compress(raw, compresslevel=9, mtime=0)


def stable_selection_key(parts: Sequence[object], *, seed: int = DEFAULT_SEED) -> str:
    return sha256_bytes(canonical_json_bytes({"seed": seed, "identity": list(parts)}))


def select_smoke_records(records: Sequence["ValidRecord"], *, limit: int = 2) -> list["ValidRecord"]:
    if limit < 1:
        raise ValueError("limit must be positive")
    return sorted(records, key=lambda row: (stable_selection_key(row.identity), row.identity))[:limit]


def strict_native_matrix(value: object, *, load: bool = True) -> tuple[np.ndarray | None, str]:
    """Accept only a finite release-native ``[samples,105]`` numeric matrix."""

    if isinstance(value, h5py.Group) or value is None:
        return None, "OBJECT_PLACEHOLDER_OR_DANGLING_REFERENCE"
    shape = getattr(value, "shape", None)
    dtype = getattr(value, "dtype", None)
    if shape is None:
        try:
            array = np.asarray(value)
        except Exception:
            return None, "NON_NUMERIC_LEAF"
        shape, dtype = array.shape, array.dtype
    shape = tuple(int(item) for item in shape)
    if len(shape) != 2:
        return None, "RANK_NOT_2"
    if shape == (1, 1):
        return None, "OBJECT_PLACEHOLDER_1X1"
    if shape[0] < 1 or shape[1] < 1:
        return None, "EMPTY_NUMERIC_LEAF"
    if shape[1] != EXPECTED_CHANNELS:
        if shape[0] == EXPECTED_CHANNELS:
            return None, "SOURCE_TRANSPOSE_FORBIDDEN"
        return None, f"CHANNEL_AXIS_{shape[1]}_NOT_{EXPECTED_CHANNELS}"
    if dtype is None or not np.issubdtype(dtype, np.number):
        return None, "NON_NUMERIC_LEAF"
    if not load:
        return np.empty((0, EXPECTED_CHANNELS), dtype=np.float64), "VALID"
    try:
        array = np.asarray(value[...]) if isinstance(value, h5py.Dataset) else np.asarray(value)
    except Exception:
        return None, "UNREADABLE_NUMERIC_LEAF"
    if array.shape != shape:
        return None, "SHAPE_CHANGED_WHILE_READING"
    if not np.isfinite(array).all():
        return None, "NONFINITE_VALUE"
    return np.asarray(array), "VALID"


def validate_sampling_evidence(
    release_rates: Sequence[float], *, official_rate_hz: float | None
) -> str:
    if official_rate_hz is None or not release_rates:
        return "SOURCE_SAMPLING_UNVERIFIED"
    if float(official_rate_hz) != EXPECTED_SAMPLING_HZ:
        return "SOURCE_SAMPLING_UNVERIFIED"
    if any(float(rate) != EXPECTED_SAMPLING_HZ for rate in release_rates):
        return "SOURCE_SAMPLING_UNVERIFIED"
    return "PASS"


def validate_channel_evidence(
    sequences: Sequence[Sequence[str]], *, summary_exact_links: int, expected_links: int
) -> str:
    if not sequences or expected_links < 1 or summary_exact_links != expected_links:
        return "SOURCE_ORDER_UNVERIFIED"
    first = tuple(sequences[0])
    if len(first) != EXPECTED_CHANNELS or len(set(first)) != EXPECTED_CHANNELS:
        return "SOURCE_ORDER_UNVERIFIED"
    if any(tuple(item) != first for item in sequences):
        return "SOURCE_ORDER_UNVERIFIED"
    return "PASS"


def validate_unit_evidence(
    *, exact_unscaled_links: int, expected_links: int, conversion_requested: bool = False,
    magnitude_inference: bool = False,
) -> str:
    if conversion_requested or magnitude_inference:
        return "SOURCE_SCALE_UNVERIFIED"
    if expected_links < 1 or exact_unscaled_links != expected_links:
        return "SOURCE_SCALE_UNVERIFIED"
    return "release_native_amplitude_unit_unlabelled"


def assert_unique_identities(identities: Sequence[Sequence[object]]) -> None:
    normalized = [tuple(str(item) for item in identity) for identity in identities]
    if len(normalized) != len(set(normalized)):
        raise ValueError("duplicate source identity")
    for identity in normalized:
        if len(identity) < 4 or not all(part.strip() for part in identity[:4]):
            raise ValueError("task/subject/source-slot identity mismatch")


def forbid_out_of_scope_operations(names: Iterable[str]) -> None:
    forbidden = {
        "normalizer.fit", "torch_model", "text_encoder", "candidate_score",
        "outer_test_metric", "probe_training", "sham_training",
    }
    used = set(names)
    overlap = sorted(used & forbidden)
    if overlap:
        raise RuntimeError(f"source admission attempted forbidden operations: {overlap}")


def validate_required_fields(fields: Iterable[str]) -> None:
    required = {"content", "rawData", "word"}
    actual = set(fields)
    if not required.issubset(actual):
        raise ValueError(f"missing required source fields: {sorted(required - actual)}")


def assert_repeat_bytes(first: bytes, second: bytes) -> None:
    if first != second:
        raise ValueError("nondeterministic ledger or feature smoke")


def _ref_target(handle: h5py.File, value: object) -> object | None:
    return dereference(handle, value)


def _vector_length(value: object) -> int:
    shape = tuple(int(item) for item in getattr(value, "shape", ()))
    if not shape:
        return 0
    if len(shape) == 1:
        return shape[0]
    if shape[0] == 1:
        return shape[1]
    if shape[1] == 1:
        return shape[0]
    return int(np.prod(shape))


def _decode_ref_strings(handle: h5py.File, dataset: h5py.Dataset) -> tuple[str, ...]:
    labels: list[str] = []
    for value in np.asarray(dataset[...], dtype=object).reshape(-1):
        target = _ref_target(handle, value)
        if target is None:
            labels.append("")
            continue
        codes = np.asarray(target[...]).reshape(-1)
        labels.append("".join(chr(int(code)) for code in codes).rstrip("\x00"))
    return tuple(labels)


def _scalar(handle: h5py.File, path: str) -> float:
    return float(np.asarray(handle[path][...]).reshape(-1)[0])


def _diagnostic_values(array: np.ndarray, maximum: int = 32) -> list[float]:
    flat = np.asarray(array).reshape(-1)
    if flat.size <= maximum:
        return [float(value) for value in flat]
    indices = np.linspace(0, flat.size - 1, maximum, dtype=np.int64)
    return [float(flat[index]) for index in indices]


@dataclass(frozen=True)
class ValidRecord:
    task: str
    subject: str
    source_kind: str
    source_slot: str
    reference_locator: str
    path: Path
    sentence_index: int
    word_index: int | None
    fixation_index: int | None
    samples: int

    @property
    def identity(self) -> tuple[str, ...]:
        return (self.task, self.subject, self.source_kind, self.source_slot, self.reference_locator)


def _load_record(record: ValidRecord) -> np.ndarray:
    with h5py.File(record.path, "r") as handle:
        if record.source_kind == "sentence":
            target = _ref_target(handle, indexed_value(handle["sentenceData/rawData"], record.sentence_index))
        else:
            word_group = _ref_target(handle, indexed_value(handle["sentenceData/word"], record.sentence_index))
            if not isinstance(word_group, h5py.Group) or record.word_index is None:
                raise RuntimeError("word record lost its release identity")
            container = _ref_target(handle, indexed_value(word_group["rawEEG"], record.word_index))
            if not isinstance(container, h5py.Dataset) or record.fixation_index is None:
                raise RuntimeError("word fixation container lost its release identity")
            values = np.asarray(container[...], dtype=object).reshape(-1)
            target = _ref_target(handle, values[record.fixation_index])
        array, status = strict_native_matrix(target)
        if status != "VALID" or array is None:
            raise RuntimeError(f"selected source became invalid: {status}")
        return array


def _preprocessed_paths(dataset_root: Path) -> list[Path]:
    return sorted([
        *dataset_root.glob("task1 - NR/Preprocessed/*/*_EEG.mat"),
        *dataset_root.glob("task2 - TSR/Preprocessed/*/*_EEG.mat"),
    ])


def inspect_preprocessed_metadata(dataset_root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    sequences: list[tuple[str, ...]] = []
    rates: list[float] = []
    for path in _preprocessed_paths(dataset_root):
        with h5py.File(path, "r") as handle:
            labels = _decode_ref_strings(handle, handle["EEG/chanlocs/labels"])
            srate = _scalar(handle, "EEG/srate")
            automagic_rate = _scalar(handle, "automagic/SamplingFrequency")
            nbchan = int(_scalar(handle, "EEG/nbchan"))
            shape = tuple(int(item) for item in handle["EEG/data"].shape)
            record = {
                "path": str(path.relative_to(dataset_root)), "srate": srate,
                "automagic_sampling_frequency": automagic_rate, "nbchan": nbchan,
                "data_shape": list(shape), "labels_sha256": sha256_bytes(canonical_json_bytes(labels)),
            }
            records.append(record)
            sequences.append(labels)
            rates.extend((srate, automagic_rate))
    labels = sequences[0] if sequences else ()
    return {
        "file_count": len(records), "records": records, "rates": rates,
        "label_sequences": sequences, "ordered_labels": labels,
        "metadata_manifest_sha256": sha256_bytes(canonical_json_bytes(records)),
        "all_data_second_axis_105": bool(records) and all(row["data_shape"][1] == 105 for row in records),
        "all_nbchan_105": bool(records) and all(row["nbchan"] == 105 for row in records),
    }


def _find_preprocessed_path(dataset_root: Path, task: str, subject: str, session: int) -> Path:
    task_dir, short = ("task1 - NR", "NR") if task == "task1_nr" else ("task2 - TSR", "TSR")
    paths = sorted((dataset_root / task_dir / "Preprocessed" / subject).glob(f"*_{subject}_{short}{session}_EEG.mat"))
    if len(paths) != 1:
        raise RuntimeError(f"preprocessed identity mismatch: {task}/{subject}/session{session}")
    return paths[0]


def _unique_exact_slice(path: Path, sample: np.ndarray) -> tuple[bool, int | None]:
    prefix = np.asarray(sample[: min(20, sample.shape[0]), :])
    with h5py.File(path, "r") as handle:
        source = handle["EEG/data"]
        column = np.asarray(source[:, 0])
        candidates = np.flatnonzero(column == prefix[0, 0])
        matches: list[int] = []
        for start in candidates:
            stop = int(start) + prefix.shape[0]
            if stop <= source.shape[0] and np.array_equal(column[start:stop], prefix[:, 0]):
                if np.array_equal(np.asarray(source[start:stop, :]), prefix):
                    matches.append(int(start))
        return len(matches) == 1, matches[0] if len(matches) == 1 else None


def _first_valid(records: Sequence[ValidRecord], kind: str) -> ValidRecord | None:
    return next((record for record in records if record.source_kind == kind), None)


def _source_session(source_file: str) -> int:
    match = re.search(r"_([1-7])\.csv$", source_file)
    if not match:
        raise RuntimeError(f"source slot has no release session: {source_file}")
    return int(match.group(1))


def _exclusion(
    *, task: str, subject: str, source_slot: str, source_kind: str,
    locator: str, reason: str,
) -> dict[str, str]:
    return {
        "task": task, "subject": subject, "source_slot": source_slot,
        "source_kind": source_kind, "reference_locator": locator, "reason": reason,
    }


def scan_summary_sources(dataset_root: Path) -> dict[str, Any]:
    exclusions: list[dict[str, str]] = []
    valid_records: list[ValidRecord] = []
    inventory: list[dict[str, Any]] = []
    diagnostics: list[float] = []
    coverage: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    joins = {task: prove_task_source_join(dataset_root, task) for task in TASKS}
    for task, proof in joins.items():
        if not proof.verified:
            raise RuntimeError(f"source-slot join is not admitted for {task}: {proof.status}")
        slots = proof.slots
        for summary in iter_summary_files(dataset_root, task):
            before = (summary.path.stat().st_size, summary.path.stat().st_mtime_ns)
            physical_sha = sha256_file(summary.path)
            after = (summary.path.stat().st_size, summary.path.stat().st_mtime_ns)
            if before != after:
                raise RuntimeError(f"summary file changed while hashing: {summary.path}")
            inventory.append({
                "path": str(summary.path.relative_to(dataset_root)), "task": task,
                "subject": summary.subject_id, "size_bytes": before[0], "sha256": physical_sha,
            })
            per_file: list[ValidRecord] = []
            with h5py.File(summary.path, "r") as handle:
                sentence = handle.get("sentenceData")
                if not isinstance(sentence, h5py.Group):
                    raise RuntimeError(f"missing required sentenceData field: {summary.path}")
                validate_required_fields(sentence.keys())
                if _vector_length(sentence["content"]) != len(slots):
                    raise RuntimeError(f"source-slot count mismatch: {summary.path}")
                for si, slot in enumerate(slots):
                    source_slot = slot.source_slot_key
                    sentence_locator = f"sentence:{si + 1}"
                    target = _ref_target(handle, indexed_value(sentence["rawData"], si))
                    array, status = strict_native_matrix(target)
                    if status == "VALID" and array is not None:
                        record = ValidRecord(task, summary.subject_id, "sentence", source_slot,
                                             sentence_locator, summary.path, si, None, None, int(array.shape[0]))
                        valid_records.append(record); per_file.append(record)
                        coverage[task][summary.subject_id]["sentence_valid"] += 1
                        if array.shape[0] >= 500:
                            coverage[task][summary.subject_id]["sentence_ge_500"] += 1
                        diagnostics.extend(_diagnostic_values(array))
                    else:
                        exclusions.append(_exclusion(task=task, subject=summary.subject_id,
                            source_slot=source_slot, source_kind="sentence", locator=sentence_locator, reason=status))
                        coverage[task][summary.subject_id]["sentence_excluded"] += 1

                    word_group = _ref_target(handle, indexed_value(sentence["word"], si))
                    if not isinstance(word_group, h5py.Group) or "rawEEG" not in word_group:
                        exclusions.append(_exclusion(task=task, subject=summary.subject_id,
                            source_slot=source_slot, source_kind="word", locator=f"{sentence_locator}/word_container",
                            reason="WORD_GROUP_OR_RAWeeg_MISSING"))
                        coverage[task][summary.subject_id]["word_excluded"] += 1
                        continue
                    raw_eeg = word_group["rawEEG"]
                    for wi in range(_vector_length(raw_eeg)):
                        base = f"{sentence_locator}/word:{wi + 1}"
                        container = _ref_target(handle, indexed_value(raw_eeg, wi))
                        if not isinstance(container, h5py.Dataset):
                            exclusions.append(_exclusion(task=task, subject=summary.subject_id,
                                source_slot=source_slot, source_kind="word", locator=base,
                                reason="FIXATION_CONTAINER_MISSING_OR_PLACEHOLDER"))
                            coverage[task][summary.subject_id]["word_excluded"] += 1
                            continue
                        try:
                            fixation_values = np.asarray(container[...], dtype=object).reshape(-1)
                        except Exception:
                            fixation_values = np.asarray([], dtype=object)
                        if fixation_values.size == 0:
                            exclusions.append(_exclusion(task=task, subject=summary.subject_id,
                                source_slot=source_slot, source_kind="word", locator=base,
                                reason="EMPTY_FIXATION_CONTAINER"))
                            coverage[task][summary.subject_id]["word_excluded"] += 1
                        for fi, fixation_value in enumerate(fixation_values):
                            locator = f"{base}/fixation:{fi + 1}"
                            target = _ref_target(handle, fixation_value)
                            array, status = strict_native_matrix(target)
                            if status == "VALID" and array is not None:
                                record = ValidRecord(task, summary.subject_id, "word", source_slot,
                                    locator, summary.path, si, wi, fi, int(array.shape[0]))
                                valid_records.append(record); per_file.append(record)
                                coverage[task][summary.subject_id]["word_valid"] += 1
                                diagnostics.extend(_diagnostic_values(array))
                            else:
                                exclusions.append(_exclusion(task=task, subject=summary.subject_id,
                                    source_slot=source_slot, source_kind="word", locator=locator, reason=status))
                                coverage[task][summary.subject_id]["word_excluded"] += 1

            # Per summary file, one sentence and one word exact slice bind the
            # summary axis and scale to co-released labelled EEG.data.
            links: list[dict[str, Any]] = []
            for kind in ("sentence", "word"):
                record = _first_valid(per_file, kind)
                if record is None:
                    links.append({"kind": kind, "exact": False, "reason": "NO_VALID_SOURCE"})
                    continue
                slot = slots[record.sentence_index]
                preprocessed = _find_preprocessed_path(dataset_root, task, summary.subject_id,
                                                        _source_session(slot.source_file))
                exact, start = _unique_exact_slice(preprocessed, _load_record(record))
                links.append({"kind": kind, "exact": exact, "start_sample": start,
                              "preprocessed_path": str(preprocessed.relative_to(dataset_root)),
                              "reference_locator": record.reference_locator})
            inventory[-1]["exact_release_slice_links"] = links

    identities = [record.identity for record in valid_records]
    assert_unique_identities(identities)
    quantiles = {}
    if diagnostics:
        values = np.asarray(diagnostics, dtype=np.float64)
        quantiles = {str(q): float(np.quantile(values, q)) for q in (0.0, 0.01, 0.5, 0.99, 1.0)}
    coverage_plain = {task: {subject: dict(counts) for subject, counts in sorted(subjects.items())}
                      for task, subjects in sorted(coverage.items())}
    return {
        "inventory": inventory, "inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "joins": joins, "valid_records": valid_records, "exclusions": exclusions,
        "coverage": coverage_plain, "diagnostic_quantiles_bounded_sample": quantiles,
    }


def run_feature_smoke(records: Sequence[ValidRecord], coverage: dict[str, Any], *, seed: int) -> dict[str, Any]:
    selected: list[ValidRecord] = []
    retained: dict[str, list[str]] = {}
    for task, subjects in sorted(coverage.items()):
        retained[task] = []
        for subject, counts in sorted(subjects.items()):
            if counts.get("word_valid", 0) < 1 or counts.get("sentence_ge_500", 0) < 1:
                continue
            retained[task].append(subject)
            for kind in ("sentence", "word"):
                pool = [record for record in records if record.task == task and record.subject == subject
                        and record.source_kind == kind and (kind != "sentence" or record.samples >= 500)]
                selected.extend(select_smoke_records(pool, limit=2))
    feature_hash = hashlib.sha256()
    selection_rows: list[dict[str, Any]] = []
    maximum_absolute_error = 0.0
    maximum_relative_error = 0.0
    sequence_shapes: Counter[str] = Counter()
    for record in selected:
        array = _load_record(record)
        if record.source_kind == "word":
            first = extract_word_level_sequence([array])
            second = extract_word_level_sequence([array])
            epochs = [array]
        else:
            first = extract_fixed_window_sequence(array)
            second = extract_fixed_window_sequence(array)
            epochs = [array[start:start + 500, :] for start in range(0, array.shape[0] - 500 + 1, 250)]
        if first.dtype != np.float32 or first.ndim != 2 or first.shape[1] != 840:
            raise RuntimeError("A1 feature smoke violated float32 [T,840]")
        if not np.isfinite(first).all() or not np.array_equal(first, second):
            raise RuntimeError("A1 feature smoke is nonfinite or nondeterministic")
        for index, epoch in enumerate(epochs):
            original = first[index] if record.source_kind == "sentence" else bandpower_features(epoch)
            phase_seed = int(stable_selection_key((*record.identity, index), seed=seed)[:16], 16)
            rotated = analysis_spectrum_phase_rotation_features(epoch, seed=phase_seed)
            difference = np.abs(rotated.astype(np.float64) - original.astype(np.float64))
            maximum_absolute_error = max(maximum_absolute_error, float(difference.max(initial=0.0)))
            relative = difference / np.maximum(np.abs(original.astype(np.float64)), PHASE_ATOL)
            maximum_relative_error = max(maximum_relative_error, float(relative.max(initial=0.0)))
            if not np.allclose(rotated, original, rtol=PHASE_RTOL, atol=PHASE_ATOL):
                raise RuntimeError("analysis-spectrum phase invariance failed")
        identity_bytes = canonical_json_bytes(record.identity)
        feature_hash.update(len(identity_bytes).to_bytes(8, "big")); feature_hash.update(identity_bytes)
        feature_hash.update(first.tobytes(order="C"))
        sequence_shapes[str(list(first.shape))] += 1
        selection_rows.append({"identity": list(record.identity), "samples": record.samples,
                               "shape": list(first.shape), "sha256": sha256_bytes(first.tobytes(order="C"))})
    return {
        "seed": seed, "selection_rule": "SHA256(canonical identity plus seed), first two",
        "selected_record_count": len(selected), "retained_subjects": retained,
        "selection_manifest_sha256": sha256_bytes(canonical_json_bytes(selection_rows)),
        "feature_bytes_sha256": feature_hash.hexdigest(), "sequence_shape_counts": dict(sequence_shapes),
        "dtype": "float32", "feature_dim": 840, "finite": True, "two_calls_byte_identical": True,
        "phase": {"method": "analysis-spectrum rotation; no irfft; no second Hann",
                  "rtol": PHASE_RTOL, "atol": PHASE_ATOL,
                  "maximum_absolute_error": maximum_absolute_error,
                  "maximum_relative_error": maximum_relative_error, "pass": True},
    }


def build_admission(
    project_root: Path, *, baseline_commit: str, run_id: str,
    seed: int = DEFAULT_SEED,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    forbid_out_of_scope_operations(())
    dataset_root = project_root / "01_data_protocol" / "datasets" / "zuco_2.0"
    preprocessed = inspect_preprocessed_metadata(dataset_root)
    source = scan_summary_sources(dataset_root)
    exact_links = sum(link["exact"] for row in source["inventory"]
                      for link in row["exact_release_slice_links"])
    expected_links = len(source["inventory"]) * 2
    sampling_status = validate_sampling_evidence(preprocessed["rates"], official_rate_hz=500.0)
    order_status = validate_channel_evidence(preprocessed["label_sequences"],
                                              summary_exact_links=exact_links,
                                              expected_links=expected_links)
    unit_status = validate_unit_evidence(exact_unscaled_links=exact_links, expected_links=expected_links)
    smoke = run_feature_smoke(source["valid_records"], source["coverage"], seed=seed)
    retained = smoke["retained_subjects"]
    g0 = all(len(retained.get(task, [])) >= 12 for task in TASKS)
    exclusion_counts = dict(sorted(Counter(row["reason"] for row in source["exclusions"]).items()))
    labels = tuple(preprocessed["ordered_labels"])
    labels_hash = sha256_bytes(canonical_json_bytes(labels))
    join_hashes = {task: proof.mapping_sha256 for task, proof in source["joins"].items()}
    scripts = [
        dataset_root / "scripts/python_reader/data_loading_helpers.py",
        dataset_root / "scripts/python_reader/read_matlab_files.py",
    ]
    script_hashes = {str(path.relative_to(dataset_root)): sha256_file(path) for path in scripts}
    checks = {
        "summary_files_exactly_36": len(source["inventory"]) == 36,
        "preprocessed_files_exactly_252": preprocessed["file_count"] == 252,
        "sampling_500_hz": sampling_status == "PASS",
        "ordered_105_labels": order_status == "PASS" and preprocessed["all_nbchan_105"]
                              and preprocessed["all_data_second_axis_105"],
        "summary_sentence_word_exact_release_links": exact_links == expected_links,
        "native_scale_provenance": unit_status == "release_native_amplitude_unit_unlabelled",
        "strict_finite_policy": DEFAULT_CONFIG.finite_policy == "reject_any_nonfinite_no_imputation",
        "identity_unique_and_joined": True,
        "coverage_g0": g0,
        "feature_smoke_deterministic_840d": smoke["two_calls_byte_identical"] and smoke["feature_dim"] == 840,
        "analysis_spectrum_phase_invariant": smoke["phase"]["pass"],
    }
    overall = "PASS_REAL_A1_SOURCE" if all(checks.values()) else next((status for status in (
        sampling_status, order_status, unit_status,
        "SOURCE_COVERAGE_G0_FAIL" if not g0 else "",
    ) if status not in ("PASS", "release_native_amplitude_unit_unlabelled", "")), "FAIL")
    common_boundary = {
        "no_normalizer_fit": True, "no_model_or_probe_training": True,
        "no_heldout_metric": True, "no_eeg_array_committed": True,
    }
    input_bindings = {
        "baseline_commit": baseline_commit, "summary_inventory_sha256": source["inventory_sha256"],
        "summary_file_count": len(source["inventory"]), "preprocessed_metadata_manifest_sha256": preprocessed["metadata_manifest_sha256"],
        "release_reader_hashes": script_hashes, "source_join_hashes": join_hashes,
        "a1_config_hash": a1_config_hash(), "official_acquisition_evidence": OFFICIAL_ACQUISITION_EVIDENCE,
    }
    coverage_summary = {
        "by_task_subject": source["coverage"], "retained_subjects": retained,
        "g0_minimum_subjects_per_task": 12, "g0_pass": g0,
        "diagnostic_quantiles_bounded_sample": source["diagnostic_quantiles_bounded_sample"],
    }
    audit = {
        "schema_version": SCHEMA_VERSION, "algorithm_version": ALGORITHM_VERSION,
        "run_id": run_id, "baseline_commit": baseline_commit, "seed": seed,
        "input_bindings": input_bindings, "checks": checks, "coverage": coverage_summary,
        "summary_inventory": source["inventory"], "exclusion_reason_counts": exclusion_counts,
        "exclusion_record_count": len(source["exclusions"]), "feature_smoke": {k: v for k, v in smoke.items() if k != "phase"},
        "phase_invariance": smoke["phase"], "overall_outcome": overall,
        "limitations": [
            "Physical amplitude unit is not labelled; values remain release-native with no conversion.",
            "Source admission is not normalization, signal admission, training, Gate evidence, or a paper result.",
            "Diagnostic quantiles use a fixed bounded sample and never select thresholds.",
        ], **common_boundary,
    }
    contract = {
        "schema_version": SCHEMA_VERSION, "algorithm_version": ALGORITHM_VERSION,
        "run_id": run_id, "spec": "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_13_2026-08-15.md#Q.3",
        "baseline_commit": baseline_commit, "outcome": overall, "seed": seed,
        "source_fields": {"sentence": "sentenceData.rawData [samples,105]",
                          "word": "sentenceData.word.rawEEG fixation [samples,105]"},
        "sampling_rate_hz": EXPECTED_SAMPLING_HZ, "sampling_status": sampling_status,
        "channel_labels": list(labels), "channel_labels_sha256": labels_hash,
        "channel_order_status": order_status, "amplitude_unit_status": unit_status,
        "amplitude_policy": "no V/uV inference or conversion; PSD native-unit^2; future normalization outer-train only",
        "finite_policy": DEFAULT_CONFIG.finite_policy, "input_bindings": input_bindings,
        "coverage": coverage_summary, "exclusions_sha256_uncompressed": sha256_bytes(
            b"".join(canonical_json_bytes(row, newline=True) for row in sorted(source["exclusions"], key=canonical_json_bytes))
        ),
        "feature_smoke": {k: v for k, v in smoke.items() if k != "phase"},
        "phase_invariance": smoke["phase"], "checks": checks, **common_boundary,
    }
    ledger = deterministic_gzip_jsonl(source["exclusions"])
    return contract, audit, ledger
