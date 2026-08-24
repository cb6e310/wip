"""Frozen protocol constants for the R6 controller-only implementation surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


PRIMARY_METRIC = "candidate_common_support_macro_subject_recall_at_1_n10"


def canonical_json_bytes(value: Any) -> bytes:
    """Encode JSON deterministically for protocol and artifact hashes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class R6ProtocolConfig:
    gamma_grid: tuple[float, ...] = (0.0, 0.25, 0.5, 1.0)
    w_min: float = 0.2
    w_max: float = 3.0
    h_clip: float = 3.0
    direct_grid_size: int = 8
    shuffle_realizations: int = 3
    shuffle_axis: str = "within_outer_cell_task_subject_across_trials"
    outer_read_limit_per_cell_task: int = 1
    test_calibration_count: int = 0
    primary_metric: str = PRIMARY_METRIC

    def canonical_payload(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.canonical_payload())
