"""Appendix F.1 language-history construction and leakage audit.

The history ``H`` is a probe-only input.  It is deliberately represented as a
small immutable record instead of a free-form dictionary so target tokens,
future sentences, target-derived statistics, candidate lists, and eye
tracking values cannot accidentally enter the alignment model.

The main version keeps the nearest preceding context, bounded by two complete
sentences and 64 tokens.  If the boundary falls inside a sentence, the 64
tokens nearest to the target are retained.  The empty sensitivity version
contains only the within-document position index.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence
import unicodedata


@dataclass(frozen=True)
class HConfig:
    """Frozen values from Appendix F.1."""

    full_version: str = "H_full"
    empty_version: str = "H_empty"
    max_sentences: int = 2
    max_tokens: int = 64
    normalization: str = "NFKC+casefold"
    scope: str = "stage1_probe_only"

    def __post_init__(self) -> None:
        if self.max_sentences != 2 or self.max_tokens != 64:
            raise ValueError("Appendix F.1 freezes H to 2 sentences and 64 tokens")
        if self.normalization != "NFKC+casefold":
            raise ValueError("H token normalization is frozen to NFKC+casefold")
        if self.scope != "stage1_probe_only":
            raise ValueError("H may occur only in Stage-1 probe inputs")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_CONFIG = HConfig()


@dataclass(frozen=True)
class HContext:
    """An auditable, probe-only language-history record."""

    version: str
    tokens: tuple[str, ...]
    position_index: int
    source_sentence_indices: tuple[int, ...]
    target_sentence_index: int
    target_tokens_excluded: bool
    scope: str = "stage1_probe_only"

    def __post_init__(self) -> None:
        if self.version not in {"H_full", "H_empty"}:
            raise ValueError(f"unknown H version: {self.version}")
        if self.position_index < 0:
            raise ValueError("position_index must be non-negative")
        if self.target_sentence_index < 0:
            raise ValueError("target_sentence_index must be non-negative")
        if len(self.source_sentence_indices) > 2:
            raise ValueError("H_full may include at most two preceding sentences")
        if len(self.tokens) > 64:
            raise ValueError("H_full may include at most 64 tokens")
        if self.scope != "stage1_probe_only":
            raise ValueError("H scope is frozen to Stage-1 probe only")
        if not self.target_tokens_excluded:
            raise ValueError("H context cannot be constructed with target tokens")
        if self.version == "H_empty" and self.tokens:
            raise ValueError("H_empty cannot contain language tokens")
        if any(index >= self.target_sentence_index for index in self.source_sentence_indices):
            raise ValueError("H source sentences must precede the target")

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "tokens": list(self.tokens),
            "position_index": self.position_index,
            "source_sentence_indices": list(self.source_sentence_indices),
            "target_sentence_index": self.target_sentence_index,
            "target_tokens_excluded": self.target_tokens_excluded,
            "scope": self.scope,
        }


def _norm(token: object) -> str:
    return unicodedata.normalize("NFKC", str(token)).casefold()


def _clean_tokens(tokens: Iterable[object]) -> list[str]:
    return [str(token) for token in tokens if str(token).strip()]


def config_hash(config: HConfig = DEFAULT_CONFIG) -> str:
    payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_metadata(
    *, seed: int, fold: str | int, method: str = "H-definition", config: HConfig = DEFAULT_CONFIG
) -> dict[str, object]:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if not str(fold).strip() or not method.strip():
        raise ValueError("fold and method must be non-empty")
    return {
        "seed": int(seed),
        "fold": str(fold),
        "method": method,
        "config_hash": config_hash(config),
    }


def _history_tokens(
    sentences: Sequence[Sequence[object]], target_sentence_index: int, config: HConfig
) -> tuple[list[str], tuple[int, ...]]:
    if target_sentence_index < 0 or target_sentence_index >= len(sentences):
        raise IndexError("target_sentence_index is outside sentences")
    first = max(0, target_sentence_index - config.max_sentences)
    source_indices = tuple(range(first, target_sentence_index))
    flattened: list[str] = []
    for index in source_indices:
        flattened.extend(_clean_tokens(sentences[index]))
    # Keep the context nearest to the target when the token boundary cuts a
    # sentence.  This is deterministic and never introduces a future token.
    if len(flattened) > config.max_tokens:
        flattened = flattened[-config.max_tokens :]
    return flattened, source_indices


def _exclude_target_tokens(tokens: Iterable[str], target_tokens: Sequence[object]) -> list[str]:
    target_norm = {_norm(token) for token in target_tokens if str(token).strip()}
    return [token for token in tokens if _norm(token) not in target_norm]


def build_h_full(
    sentences: Sequence[Sequence[object]],
    *,
    target_sentence_index: int,
    target_tokens: Sequence[object],
    position_index: int,
    config: HConfig = DEFAULT_CONFIG,
) -> HContext:
    """Construct ``H_full`` from preceding sentences only.

    Any token whose normalized surface form occurs in the target sentence is
    removed.  This conservative filtering guarantees the F.1 target-token
    prohibition even when a preceding sentence repeats a target word.
    """

    tokens, source_indices = _history_tokens(sentences, target_sentence_index, config)
    tokens = _exclude_target_tokens(tokens, target_tokens)
    if len(tokens) > config.max_tokens:
        tokens = tokens[-config.max_tokens :]
    context = HContext(
        version=config.full_version,
        tokens=tuple(tokens),
        position_index=int(position_index),
        source_sentence_indices=source_indices,
        target_sentence_index=int(target_sentence_index),
        target_tokens_excluded=True,
    )
    assertions = audit_h_context(context, target_tokens=target_tokens)
    if not all(assertions.values()):
        raise AssertionError(f"invalid H_full context: {assertions}")
    return context


def build_h_empty(
    *, target_sentence_index: int, position_index: int, config: HConfig = DEFAULT_CONFIG
) -> HContext:
    """Construct ``H_empty`` (position index only)."""

    return HContext(
        version=config.empty_version,
        tokens=(),
        position_index=int(position_index),
        source_sentence_indices=(),
        target_sentence_index=int(target_sentence_index),
        target_tokens_excluded=True,
    )


def audit_h_context(
    context: HContext,
    *,
    target_tokens: Sequence[object] = (),
    future_sentence_indices: Sequence[int] = (),
    payload: object | None = None,
) -> dict[str, bool]:
    """Return machine-checkable F.0/F.1 assertions for one context record."""

    target_norm = {_norm(token) for token in target_tokens if str(token).strip()}
    context_norm = {_norm(token) for token in context.tokens}
    payload_keys: set[str] = set()
    if isinstance(payload, dict):
        payload_keys = {str(key).casefold() for key in payload}
    return {
        "scope_stage1_probe_only": context.scope == "stage1_probe_only",
        "target_tokens_absent": context_norm.isdisjoint(target_norm),
        "target_flag_true": bool(context.target_tokens_excluded),
        "target_payload_absent": payload_keys.isdisjoint(
            {
                "target",
                "target_id",
                "target_tokens",
                "target_sentence",
                "gold_sentence",
                "answer",
                "current_token",
            }
        ),
        "future_sentences_absent": all(
            index < context.target_sentence_index for index in context.source_sentence_indices
        )
        and not any(index >= context.target_sentence_index for index in future_sentence_indices)
        and payload_keys.isdisjoint({"future", "future_tokens", "future_sentence", "future_sentences"}),
        "target_statistics_absent": payload_keys.isdisjoint(
            {"sentence_length", "word_count", "punctuation_count"}
        ),
        "candidate_inputs_absent": payload_keys.isdisjoint(
            {"candidates", "candidate_ids", "candidate_answers", "candidate_embeddings"}
        ),
        "eye_tracking_inputs_absent": payload_keys.isdisjoint(
            {"eye", "eye_tracking", "et"}
        ),
        "empty_has_no_tokens": context.version != "H_empty" or not context.tokens,
        "token_budget": len(context.tokens) <= 64,
    }
