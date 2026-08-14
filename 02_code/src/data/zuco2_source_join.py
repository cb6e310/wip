"""Source-slot identity proof for ZuCo 2.0 material and summary records.

The v3.6 contract forbids treating equal text or a text hash as stimulus
identity.  The release supplies ordered material rows and ordered summary
slots.  This module proves a join only when the summary sequence has exactly
one monotone embedding in the material-row sequence.  Text is therefore only
an equality constraint; the emitted identity is always the source file, row,
and raw material IDs.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import h5py

from data.zuco2_loader import (
    MaterialRow,
    decode_matlab_string,
    indexed_value,
    iter_summary_files,
    read_material_rows,
)


def normalize_join_text(value: object) -> str:
    """Apply the source-preserving equality normalization used for the join."""

    return unicodedata.normalize("NFKC", "" if value is None else str(value)).strip()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class JoinedSourceSlot:
    summary_index: int
    source_file: str
    row_number: int
    paragraph_id_raw: str
    sentence_id_raw: str
    condition_raw: str
    source_slot_key: str
    group_key: str
    text_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SourceJoinProof:
    dataset: str
    task: str
    status: str
    material_row_count: int
    summary_slot_count: int
    slots: tuple[JoinedSourceSlot, ...]
    skipped_material_rows: tuple[dict[str, object], ...]
    ambiguous_summary_indices: tuple[int, ...]
    material_projection_sha256: str
    summary_sequence_sha256: str
    mapping_sha256: str
    assertions: dict[str, bool]

    @property
    def verified(self) -> bool:
        return self.status == "SOURCE_SLOT_JOIN_VERIFIED" and all(self.assertions.values())

    def to_dict(self, *, include_slots: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "dataset": self.dataset,
            "task": self.task,
            "status": self.status,
            "material_row_count": self.material_row_count,
            "summary_slot_count": self.summary_slot_count,
            "skipped_material_rows": list(self.skipped_material_rows),
            "ambiguous_summary_indices": list(self.ambiguous_summary_indices),
            "material_projection_sha256": self.material_projection_sha256,
            "summary_sequence_sha256": self.summary_sequence_sha256,
            "mapping_sha256": self.mapping_sha256,
            "identity_rule": "ordered source rows; text equality is validation only",
            "text_hash_is_identity": False,
            "assertions": dict(self.assertions),
        }
        if include_slots:
            result["slots"] = [slot.to_dict() for slot in self.slots]
        return result


def _source_slot_key(dataset: str, task: str, row: MaterialRow) -> str:
    return "|".join(
        (
            dataset,
            task,
            row.source_file,
            str(row.row_number),
            row.paragraph_id_raw,
            row.sentence_id_raw,
        )
    )


def _group_key(dataset: str, task: str, row: MaterialRow) -> str:
    # The release's first raw ID is the document/paragraph identity.  Keeping
    # source_file in the key prevents numeric IDs from being merged across
    # separately released material files.
    return "|".join((dataset, task, row.source_file, row.paragraph_id_raw))


def prove_ordered_source_join(
    material_rows: Sequence[MaterialRow],
    summary_contents: Sequence[object],
    *,
    dataset: str,
    task: str,
) -> SourceJoinProof:
    """Prove the unique monotone material-row join or return a blocked proof."""

    if not dataset.strip() or not task.strip():
        raise ValueError("dataset and task are required")
    materials = list(material_rows)
    summary = [normalize_join_text(value) for value in summary_contents]
    material_text = [normalize_join_text(row.text_or_label_raw) for row in materials]
    material_projection = [
        {
            "source_file": row.source_file,
            "row_number": row.row_number,
            "paragraph_id_raw": row.paragraph_id_raw,
            "sentence_id_raw": row.sentence_id_raw,
            "condition_raw": row.condition_raw,
            "text_sha256": sha256_bytes(text.encode("utf-8")),
        }
        for row, text in zip(materials, material_text)
    ]

    earliest: list[int] = []
    cursor = 0
    for value in summary:
        while cursor < len(material_text) and material_text[cursor] != value:
            cursor += 1
        if cursor == len(material_text):
            break
        earliest.append(cursor)
        cursor += 1

    latest: list[int | None] = [None] * len(summary)
    cursor = len(material_text) - 1
    for summary_index in range(len(summary) - 1, -1, -1):
        value = summary[summary_index]
        while cursor >= 0 and material_text[cursor] != value:
            cursor -= 1
        if cursor < 0:
            break
        latest[summary_index] = cursor
        cursor -= 1

    complete = len(earliest) == len(summary) and all(value is not None for value in latest)
    ambiguous = tuple(
        index + 1
        for index, (left, right) in enumerate(zip(earliest, latest))
        if right is None or left != right
    ) if complete else tuple(range(len(earliest) + 1, len(summary) + 1))
    unique = complete and not ambiguous

    slots: list[JoinedSourceSlot] = []
    if unique:
        for summary_index, material_index in enumerate(earliest, start=1):
            row = materials[material_index]
            slots.append(
                JoinedSourceSlot(
                    summary_index=summary_index,
                    source_file=row.source_file,
                    row_number=row.row_number,
                    paragraph_id_raw=row.paragraph_id_raw,
                    sentence_id_raw=row.sentence_id_raw,
                    condition_raw=row.condition_raw,
                    source_slot_key=_source_slot_key(dataset, task, row),
                    group_key=_group_key(dataset, task, row),
                    text_sha256=sha256_bytes(summary[summary_index - 1].encode("utf-8")),
                )
            )

    used = set(earliest) if complete else set()
    skipped = tuple(
        {
            "source_file": row.source_file,
            "row_number": row.row_number,
            "paragraph_id_raw": row.paragraph_id_raw,
            "sentence_id_raw": row.sentence_id_raw,
            "condition_raw": row.condition_raw,
        }
        for index, row in enumerate(materials)
        if index not in used
    )
    source_keys = [slot.source_slot_key for slot in slots]
    mapping_payload = [slot.to_dict() for slot in slots]
    assertions = {
        "all_summary_slots_matched": complete,
        "ordered_mapping_is_unique": unique,
        "source_slot_keys_are_unique": unique and len(source_keys) == len(set(source_keys)),
        "mapping_count_matches_summary": unique and len(slots) == len(summary),
        "text_hash_is_not_identity": True,
    }
    status = "SOURCE_SLOT_JOIN_VERIFIED" if all(assertions.values()) else (
        "BLOCKED_NONUNIQUE_ORDERED_JOIN" if complete else "BLOCKED_UNMATCHED_ORDERED_JOIN"
    )
    return SourceJoinProof(
        dataset=dataset,
        task=task,
        status=status,
        material_row_count=len(materials),
        summary_slot_count=len(summary),
        slots=tuple(slots),
        skipped_material_rows=skipped,
        ambiguous_summary_indices=ambiguous,
        material_projection_sha256=sha256_bytes(canonical_json_bytes(material_projection)),
        summary_sequence_sha256=sha256_bytes(canonical_json_bytes(summary)),
        mapping_sha256=sha256_bytes(canonical_json_bytes(mapping_payload)),
        assertions=assertions,
    )


def read_summary_contents(path: Path) -> list[str]:
    with h5py.File(path, "r") as handle:
        content = handle.get("sentenceData/content")
        shape = getattr(content, "shape", ())
        count = int(max(shape)) if shape else 0
        return [
            decode_matlab_string(handle, indexed_value(content, index)) or ""
            for index in range(count)
        ]


def prove_task_source_join(dataset_root: Path, task: str, *, dataset: str = "zuco_2_0") -> SourceJoinProof:
    summaries = list(iter_summary_files(dataset_root, task))
    if not summaries:
        raise FileNotFoundError(f"no summary files for {task}")
    return prove_ordered_source_join(
        read_material_rows(dataset_root, task),
        read_summary_contents(summaries[0].path),
        dataset=dataset,
        task=task,
    )
