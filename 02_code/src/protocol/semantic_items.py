"""Semantic-item rules frozen by the v3.6 project specification.

The module intentionally contains no tokenizer, stemmer, language model, or
sentence-text fallback.  A caller must provide the released reader's
``is_real_word`` predicate.  This keeps the item definition auditable when a
dataset exposes a different release helper.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping


MIN_OBSERVATIONS = 20
MIN_SUBJECTS = 5
SUPPORT_RATE_REDLINE = 0.20

# These values are only placeholders, not a general-purpose stop list.  The
# official predicate is still required before any item can be admitted.
PLACEHOLDER_VALUES = frozenset(
    {"", "nan", "none", "null", "na", "n/a", "<na>", "<null>", "placeholder"}
)
_ASCII_DIGITS = re.compile(r"^[0-9]+(?:[.,][0-9]+)?$")


@dataclass(frozen=True)
class ItemDecision:
    """Decision and normalized identity for one released word-level record."""

    raw_content: str
    normalized_surface: str | None
    item_id: str | None
    accepted: bool
    reason: str


@dataclass
class ItemStats:
    """Aggregated support for one task-local item."""

    item_id: str
    normalized_surface: str
    n_observations: int = 0
    subjects: set[str] = field(default_factory=set)
    trials: set[str] = field(default_factory=set)

    @property
    def n_subjects(self) -> int:
        return len(self.subjects)

    @property
    def n_trials(self) -> int:
        return len(self.trials)

    @property
    def passes_min_support(self) -> bool:
        return self.n_observations >= MIN_OBSERVATIONS and self.n_subjects >= MIN_SUBJECTS


def normalize_surface(value: object) -> str:
    """Apply exactly NFKC, edge whitespace removal, and case-folding."""

    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip().casefold()


def _contains_letter(value: str) -> bool:
    return any(unicodedata.category(char).startswith("L") for char in value)


def decide_item(
    raw_content: object,
    *,
    dataset: str,
    task: str,
    is_real_word: Callable[[str], object],
) -> ItemDecision:
    """Apply the released-content-word rule without inventing tokenization.

    ``is_real_word`` is deliberately a required keyword argument.  A missing
    official reader predicate is a protocol error rather than a reason to
    silently accept every string.
    """

    raw = "" if raw_content is None else str(raw_content)
    normalized = normalize_surface(raw)
    if normalized in PLACEHOLDER_VALUES:
        return ItemDecision(raw, None, None, False, "placeholder_or_empty")
    try:
        official = bool(is_real_word(raw))
    except Exception as exc:  # make a bad release helper visible to the caller
        raise ValueError(f"official is_real_word failed for {raw!r}: {exc}") from exc
    if not official:
        return ItemDecision(raw, None, None, False, "official_is_real_word_false")
    # The ZuCo helper's regex accepts numeric strings.  The v3.5 rule excludes
    # pure numeric material explicitly, while retaining the released surface
    # form verbatim (no punctuation stripping or stemming).
    if _ASCII_DIGITS.fullmatch(normalized) or not _contains_letter(normalized):
        return ItemDecision(raw, None, None, False, "numeric_or_nonlexical")
    item_id = f"{dataset}|{task}|{normalized}"
    return ItemDecision(raw, normalized, item_id, True, "accepted")


def config_dict() -> dict[str, object]:
    return {
        "normalization": "NFKC|strip|casefold",
        "official_predicate": "required_release_reader_is_real_word",
        "no_stemming": True,
        "no_sentence_retokenization": True,
        "min_observations": MIN_OBSERVATIONS,
        "min_subjects": MIN_SUBJECTS,
        "support_rate_redline": SUPPORT_RATE_REDLINE,
        "usable_eeg_rule": "word_rawEEG_container_with_at_least_one_numeric_nonempty_(n,105)_fixation",
        "sentence_rule": "sentence_rawData_numeric_nonplaceholder",
    }


def config_hash() -> str:
    payload = json.dumps(config_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_observation(
    stats: dict[str, ItemStats],
    decision: ItemDecision,
    *,
    subject_id: str,
    trial_id: str,
) -> None:
    """Add one valid word-level EEG observation to an item accumulator."""

    if not decision.accepted or decision.item_id is None or decision.normalized_surface is None:
        raise ValueError("only accepted item decisions may receive observations")
    current = stats.get(decision.item_id)
    if current is None:
        current = ItemStats(decision.item_id, decision.normalized_surface)
        stats[decision.item_id] = current
    current.n_observations += 1
    current.subjects.add(str(subject_id))
    current.trials.add(str(trial_id))


def summarize_stats(stats: Mapping[str, ItemStats], *, subject_ids: Iterable[str]) -> dict[str, object]:
    """Return deterministic T5 support and sparsity diagnostics."""

    ordered = [stats[key] for key in sorted(stats)]
    subjects = sorted({str(value) for value in subject_ids})
    item_count = len(ordered)
    passed = sum(item.passes_min_support for item in ordered)
    n_obs = sum(item.n_observations for item in ordered)
    observed_cells = sum(item.n_subjects for item in ordered)
    total_cells = len(subjects) * item_count
    sparsity = 1.0 - observed_cells / total_cells if total_cells else 1.0
    counts = sorted(item.n_observations for item in ordered)
    if counts:
        mid = len(counts) // 2
        median = float(counts[mid]) if len(counts) % 2 else (counts[mid - 1] + counts[mid]) / 2.0
        q1 = float(counts[(len(counts) - 1) // 4])
        q3 = float(counts[(3 * (len(counts) - 1)) // 4])
    else:
        median = q1 = q3 = 0.0
    coverage = {
        subject: round(
            sum(subject in item.subjects for item in ordered) / item_count if item_count else 0.0,
            8,
        )
        for subject in subjects
    }
    coverage_values = sorted(coverage.values())
    if coverage_values:
        mid = len(coverage_values) // 2
        coverage_median = float(coverage_values[mid]) if len(coverage_values) % 2 else (coverage_values[mid - 1] + coverage_values[mid]) / 2.0
    else:
        coverage_median = 0.0
    support_rate = passed / item_count if item_count else 0.0
    return {
        "item_count": item_count,
        "n_observations": n_obs,
        "support_threshold": {"n_observations": MIN_OBSERVATIONS, "n_subjects": MIN_SUBJECTS},
        "supported_item_count": passed,
        "supported_item_rate": round(support_rate, 8),
        "support_redline": SUPPORT_RATE_REDLINE,
        "support_redline_status": "NO_GO" if support_rate < SUPPORT_RATE_REDLINE else "PASS",
        "observation_count_median": median,
        "observation_count_iqr": [q1, q3],
        "response_matrix": {
            "subject_count": len(subjects),
            "item_count": item_count,
            "observed_subject_item_cells": observed_cells,
            "total_subject_item_cells": total_cells,
            "sparsity": round(sparsity, 8),
        },
        "per_subject_item_coverage": coverage,
        "per_subject_item_coverage_median": round(coverage_median, 8),
    }


def serialize_items(stats: Mapping[str, ItemStats]) -> list[dict[str, object]]:
    """Serialize item rows in byte-deterministic order."""

    return [
        {
            "item_id": item.item_id,
            "normalized_surface": item.normalized_surface,
            "n_observations": item.n_observations,
            "n_subjects": item.n_subjects,
            "n_trials": item.n_trials,
            "subjects": sorted(item.subjects),
            "passes_min_support": item.passes_min_support,
        }
        for item in (stats[key] for key in sorted(stats))
    ]
