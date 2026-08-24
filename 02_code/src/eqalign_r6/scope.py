"""Fail-closed fit/inner/outer and feature-role boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Hashable, Iterable

from .contracts import PRIMARY_METRIC, R6ProtocolConfig


FORBIDDEN_BEHAVIOR_ROLES = frozenset({"eeg_encoder", "text_encoder", "candidate", "split", "eligibility"})
FORBIDDEN_ID_ROLES = frozenset({"eeg_encoder", "text_encoder", "candidate", "split", "eligibility"})


def assert_controller_fit_ids(
    controller_fit_record_ids: Iterable[Hashable], fit_record_ids: Iterable[Hashable]
) -> None:
    fit_ids = set(fit_record_ids)
    requested = set(controller_fit_record_ids)
    leaked = requested - fit_ids
    if leaked:
        raise ValueError("controller fit IDs include records outside the fit scope")


def assert_feature_role(feature_kind: str, role: str) -> None:
    normalized_kind = feature_kind.lower()
    normalized_role = role.lower()
    if normalized_kind == "behavior" and normalized_role != "controller_input":
        raise ValueError("behavior covariates are controller-only")
    if normalized_kind in {"subject_id", "item_id", "record_id"} and normalized_role in FORBIDDEN_ID_ROLES:
        raise ValueError("identifiers may not enter encoder/candidate/split/eligibility features")


@dataclass
class ScopeLedger:
    fit_record_ids: frozenset[Hashable]
    outer_read_limit_per_cell_task: int = 1
    outer_reads: dict[tuple[str, str], int] = field(default_factory=dict)
    selection_outer_reads: int = 0
    calibration_reads: int = 0

    def assert_controller_fit(self, ids: Iterable[Hashable]) -> None:
        assert_controller_fit_ids(ids, self.fit_record_ids)

    def record_outer_read(self, outer_cell: str, task: str, *, purpose: str) -> None:
        if purpose in {"controller", "selection", "calibration"}:
            raise ValueError(f"outer reads for {purpose} are forbidden")
        key = (outer_cell, task)
        next_count = self.outer_reads.get(key, 0) + 1
        if next_count > self.outer_read_limit_per_cell_task:
            raise ValueError("outer read limit exceeded for cell/task")
        self.outer_reads[key] = next_count

    def assert_pre_outer(self) -> None:
        if self.outer_reads or self.selection_outer_reads or self.calibration_reads:
            raise ValueError("pre-outer stage must have zero outer/calibration reads")


def primary_metric_from_freeze(config: R6ProtocolConfig) -> str:
    if config.primary_metric != PRIMARY_METRIC:
        raise ValueError("primary metric differs from the author freeze")
    return config.primary_metric
