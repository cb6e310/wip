"""Auditable compute and artifact ledger contracts for R6."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from .contracts import canonical_json_sha256


LEDGER_FIELDS = frozenset(
    {
        "arm_id",
        "variant_id",
        "controller_fit_record_ids",
        "weight_artifact_sha256",
        "config_hash",
    }
)
SENSITIVE_KEY_FRAGMENTS = ("eeg", "subject", "heldout_text", "raw_text", "embedding", "array")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ComputeCounters:
    C_step: str
    C_data: str
    C_model: str
    C_lr: str

    def canonical_hash(self) -> str:
        return canonical_json_sha256(asdict(self))


@dataclass(frozen=True)
class ReadCounters:
    controller_reads_outer: bool = False
    test_calibration_count: int = 0
    real_outer_reads_in_stage_C: int = 0

    def validate(self) -> None:
        if self.controller_reads_outer:
            raise ValueError("controller outer reads are forbidden")
        if self.test_calibration_count != 0:
            raise ValueError("test calibration count is frozen to zero")
        if self.real_outer_reads_in_stage_C != 0:
            raise ValueError("Stage C real outer reads are forbidden")


def batch_index_sequence_hash(batches: Sequence[Sequence[int]]) -> str:
    canonical = [[int(index) for index in batch] for batch in batches]
    return canonical_json_sha256(canonical)


def independent_rng_stream_id(namespace: str, seed: int) -> str:
    if not namespace:
        raise ValueError("RNG namespace must not be empty")
    return hashlib.sha256(f"r6|controller|{namespace}|{int(seed)}".encode("ascii")).hexdigest()


def physical_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_artifact_sha256(value: Any) -> str:
    return canonical_json_sha256(value)


def assert_compute_matched(
    counters: Mapping[str, ComputeCounters],
    examples_seen: Mapping[str, int],
    batch_hashes: Mapping[str, str],
) -> None:
    if not counters or set(counters) != set(examples_seen) or set(counters) != set(batch_hashes):
        raise ValueError("all arms must provide counters, examples, and batch hashes")
    if len(set(counters.values())) != 1:
        raise ValueError("R6 compute counters differ across arms")
    if len(set(int(value) for value in examples_seen.values())) != 1:
        raise ValueError("R6 data examples differ across arms")
    if len(set(batch_hashes.values())) != 1:
        raise ValueError("R6 batch-index sequence hashes differ across arms")


def validate_ledger_budget(rows: Iterable[Mapping[str, Any]], *, maximum_rows: int) -> None:
    materialized = list(rows)
    if maximum_rows < 0 or len(materialized) > maximum_rows:
        raise ValueError("ledger row budget exceeded")
    for row in materialized:
        validate_ledger_row(row)


def _reject_sensitive(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise ValueError(f"sensitive ledger content at {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def validate_ledger_row(row: Mapping[str, Any]) -> None:
    if set(row) != LEDGER_FIELDS:
        raise ValueError("ledger row must use the exact five-field whitelist")
    _reject_sensitive(row)
    for key in ("weight_artifact_sha256", "config_hash"):
        if not isinstance(row[key], str) or not SHA256_RE.fullmatch(row[key]):
            raise ValueError(f"{key} must be a lowercase SHA256")
    record_ids = row["controller_fit_record_ids"]
    if not isinstance(record_ids, (list, tuple)) or not all(
        isinstance(value, str) and SHA256_RE.fullmatch(value) for value in record_ids
    ):
        raise ValueError("controller fit record IDs must be irreversible SHA256 tokens")
