#!/usr/bin/env python3
"""Read-only, schema-preserving access to the ZuCo 2.0 release.

This module deliberately does not infer an EEG channel map, band definition,
semantic item unit, or exclusion policy.  It exposes source identifiers and
reference diagnostics so those decisions can be frozen at protocol level.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import h5py
import numpy as np


TASKS = {
    "task1_nr": {
        "label": "task1_NR",
        "summary_dir": "task1 - NR/Matlab files",
        "raw_dir": "task1 - NR/Raw data",
        "summary_glob": "results*_NR.mat",
        "raw_glob": "*_NR_EEG.mat",
        "et_glob": "*_NR_ET.mat",
        "material_glob": "nr_[1-7].csv",
    },
    "task2_tsr": {
        "label": "task2_TSR",
        "summary_dir": "task2 - TSR/Matlab files",
        "raw_dir": "task2 - TSR/Raw data",
        "summary_glob": "results*_TSR.mat",
        "raw_glob": "*_TSR_EEG.mat",
        "et_glob": "*_TSR_ET.mat",
        "material_glob": "tsr_[1-7].csv",
    },
}

SUBJECT_RE = re.compile(r"^(?:results)?([A-Z]{3})_(?:NR|TSR)\.mat$")
RAW_SUBJECT_RE = re.compile(r"^([A-Z]{3})_(?:NR|TSR)([1-7])_(EEG|ET)\.mat$")


@dataclass(frozen=True)
class SummaryFile:
    task: str
    subject_id: str
    path: Path


@dataclass(frozen=True)
class RawFile:
    task: str
    subject_id: str
    session_id: str
    kind: str
    path: Path


@dataclass(frozen=True)
class MaterialRow:
    task: str
    source_file: str
    row_number: int
    source_columns: tuple[str, ...]

    @property
    def paragraph_id_raw(self) -> str:
        return self.source_columns[0] if self.source_columns else ""

    @property
    def sentence_id_raw(self) -> str:
        return self.source_columns[1] if len(self.source_columns) > 1 else ""

    @property
    def text_raw(self) -> str:
        return self.source_columns[2] if len(self.source_columns) > 2 else ""

    @property
    def condition_raw(self) -> str:
        return self.source_columns[3] if len(self.source_columns) > 3 else ""

    @property
    def sentence_slot_raw(self) -> str:
        return self.paragraph_id_raw

    @property
    def material_id_raw(self) -> str:
        return self.sentence_id_raw

    @property
    def text_or_label_raw(self) -> str:
        return self.text_raw


def _task_spec(task: str) -> dict[str, str]:
    try:
        return TASKS[task]
    except KeyError as exc:
        raise ValueError(f"unknown ZuCo 2.0 task: {task}") from exc


def iter_summary_files(dataset_root: Path, task: str) -> Iterator[SummaryFile]:
    spec = _task_spec(task)
    root = dataset_root / spec["summary_dir"]
    for path in sorted(root.glob(spec["summary_glob"])):
        match = SUBJECT_RE.match(path.name)
        if match:
            yield SummaryFile(task, match.group(1), path)


def iter_raw_files(dataset_root: Path, task: str) -> Iterator[RawFile]:
    spec = _task_spec(task)
    root = dataset_root / spec["raw_dir"]
    for subject_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for path in sorted(subject_dir.glob("*.mat")):
            match = RAW_SUBJECT_RE.match(path.name)
            if match:
                yield RawFile(task, match.group(1), match.group(2), match.group(3), path)


def read_material_rows(dataset_root: Path, task: str) -> list[MaterialRow]:
    spec = _task_spec(task)
    material_root = dataset_root / "task_materials"
    rows: list[MaterialRow] = []
    for path in sorted(material_root.glob(spec["material_glob"])):
        # The release files are semicolon-delimited and have no header.  Keep
        # every source column verbatim; interpretation belongs to the data card.
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row_number, columns in enumerate(csv.reader(handle, delimiter=";"), start=1):
                if not columns or not any(value.strip() for value in columns):
                    continue
                rows.append(MaterialRow(task, path.name, row_number, tuple(columns)))
    return rows


def _first_ref(value: object) -> h5py.Reference | None:
    if isinstance(value, h5py.Reference):
        return value if value else None
    array = np.asarray(value, dtype=object).reshape(-1)
    for item in array:
        if isinstance(item, h5py.Reference) and item:
            return item
    return None


def dereference(handle: h5py.File, value: object):
    """Return the first MATLAB object reference, or ``None`` if absent/bad."""
    ref = _first_ref(value)
    if ref is None:
        return None
    try:
        return handle[ref]
    except (KeyError, ValueError, RuntimeError):
        return None


def decode_matlab_string(handle: h5py.File, value: object) -> str | None:
    target = dereference(handle, value)
    if target is None or not hasattr(target, "shape"):
        return None
    try:
        codes = np.asarray(target).reshape(-1)
        return "".join(chr(int(code)) for code in codes).rstrip("\x00")
    except (TypeError, ValueError, OverflowError):
        return None


def dataset_shape(handle: h5py.File, value: object) -> tuple[int, ...] | None:
    target = dereference(handle, value)
    shape = getattr(target, "shape", None)
    return tuple(int(x) for x in shape) if shape is not None else None


def numeric_eeg_reference_status(
    handle: h5py.File,
    value: object,
    *,
    channels: int = 105,
) -> tuple[bool, str]:
    """Validate one released EEG reference without repairing or imputing it.

    The v3.6 data policy admits only a non-empty numeric ``(samples, channels)``
    leaf.  MATLAB ``(1, 1)`` placeholders are reported separately.  Values are
    not loaded or transformed here; this is an identity/schema check used by
    the exclusion ledger and split builder.
    """

    if channels < 1:
        raise ValueError("channels must be positive")
    target = dereference(handle, value)
    shape = getattr(target, "shape", None)
    dtype = getattr(target, "dtype", None)
    if shape is None:
        return False, "missing_or_invalid_reference"
    shape_tuple = tuple(int(item) for item in shape)
    if shape_tuple == (1, 1):
        return False, "placeholder_1x1"
    if not shape_tuple or int(np.prod(shape_tuple, dtype=np.int64)) <= 0:
        return False, "empty_numeric_leaf"
    if dtype is None or not np.issubdtype(dtype, np.number):
        return False, "non_numeric_leaf"
    if len(shape_tuple) != 2 or shape_tuple[1] != channels:
        return False, f"unexpected_shape_{shape_tuple}"
    return True, "valid"


def summary_sentence_count(handle: h5py.File) -> int:
    sentence = handle.get("sentenceData")
    if sentence is None or not isinstance(sentence, h5py.Group):
        return 0
    content = sentence.get("content")
    if content is None or not hasattr(content, "shape"):
        return 0
    return int(max(content.shape)) if content.shape else 0


def iter_sentence_indices(handle: h5py.File) -> range:
    return range(summary_sentence_count(handle))


def source_field_names(handle: h5py.File) -> tuple[str, ...]:
    sentence = handle.get("sentenceData")
    if sentence is None or not isinstance(sentence, h5py.Group):
        return ()
    return tuple(sorted(str(name) for name in sentence.keys()))


def sentence_value(handle: h5py.File, field: str, index: int):
    sentence = handle.get("sentenceData")
    if sentence is None or field not in sentence:
        return None
    dataset = sentence[field]
    return indexed_value(dataset, index)


def indexed_value(dataset: object, index: int):
    """Read one MATLAB cell/reference from either row- or column-vector layout."""
    ndim = getattr(dataset, "ndim", 0)
    shape = getattr(dataset, "shape", ())
    try:
        if ndim == 0:
            return dataset[()]
        if ndim == 1:
            return dataset[index]
        if len(shape) >= 2 and shape[0] == 1 and index < shape[1]:
            return dataset[0, index]
        if len(shape) >= 2 and shape[1] == 1 and index < shape[0]:
            return dataset[index, 0]
        if index < shape[0]:
            return dataset[index, 0]
        if index < shape[1]:
            return dataset[0, index]
    except (IndexError, ValueError, TypeError):
        return None
    return None


def summary_record(handle: h5py.File, index: int) -> dict[str, object]:
    """Return source-level sentence metadata without loading EEG arrays."""
    record: dict[str, object] = {"sentence_index": index + 1}
    for field in ("content", "rawData", "word", "wordbounds", "omissionRate", "allFixations"):
        value = sentence_value(handle, field, index)
        record[f"{field}_shape"] = dataset_shape(handle, value)
        if field == "content":
            record["content"] = decode_matlab_string(handle, value)
    word_value = sentence_value(handle, "word", index)
    record["word_reference"] = word_value
    word_group = dereference(handle, word_value)
    if isinstance(word_group, h5py.Group):
        record["word_fields"] = tuple(sorted(str(name) for name in word_group.keys()))
        lengths: dict[str, int] = {}
        for name in word_group.keys():
            shape = getattr(word_group[name], "shape", ())
            lengths[str(name)] = int(max(shape)) if shape else 0
        record["word_field_lengths"] = lengths
    else:
        record["word_fields"] = ()
        record["word_field_lengths"] = {}
    return record


def validate_config(dataset_root: Path) -> None:
    if not dataset_root.is_dir():
        raise FileNotFoundError(dataset_root)
    missing = [task for task, spec in TASKS.items() if not (dataset_root / spec["summary_dir"]).is_dir()]
    if missing:
        raise FileNotFoundError(f"missing ZuCo task directories: {missing}")
