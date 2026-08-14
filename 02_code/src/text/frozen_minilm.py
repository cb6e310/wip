"""Exact-revision frozen MiniLM text encoder required by SPEC v3.8 D10/D15/D16.

All sentence targets, item surfaces, legal language histories and candidate
near-duplicate checks must call this module's one ``encode`` interface.  The
module contains no learned pooling or projection and never fine-tunes the
underlying transformer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor
from torch.nn import functional as F


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
OUTPUT_DIM = 384
POOLING = "attention_mask_mean"
NORMALIZATION = "l2"
MAX_SEQ_LENGTH = 256


def _canonical_sha256(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Hash one provenance file without copying it into the repository."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def aggregate_file_hash(file_hashes: Mapping[str, str]) -> str:
    """Hash a filename-to-SHA256 manifest deterministically."""

    if not file_hashes:
        raise ValueError("at least one provenance file hash is required")
    return _canonical_sha256(dict(sorted(file_hashes.items())))


@dataclass(frozen=True)
class FrozenTextEncoderConfig:
    """Every frozen value that changes the public text representation."""

    model_id: str = MODEL_ID
    revision: str = REVISION
    output_dim: int = OUTPUT_DIM
    pooling: str = POOLING
    normalization: str = NORMALIZATION
    max_seq_length: int = MAX_SEQ_LENGTH

    def __post_init__(self) -> None:
        if self.model_id != MODEL_ID:
            raise ValueError(f"model_id is frozen to {MODEL_ID}")
        if self.revision != REVISION:
            raise ValueError(f"revision is frozen to {REVISION}")
        if self.output_dim != OUTPUT_DIM:
            raise ValueError(f"output_dim is frozen to {OUTPUT_DIM}")
        if self.pooling != POOLING:
            raise ValueError(f"pooling is frozen to {POOLING}")
        if self.normalization != NORMALIZATION:
            raise ValueError(f"normalization is frozen to {NORMALIZATION}")
        if self.max_seq_length != MAX_SEQ_LENGTH:
            raise ValueError(f"max_seq_length is frozen to {MAX_SEQ_LENGTH}")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def scientific_config_hash(self) -> str:
        """Hash scientific fields; this is not a released-file manifest hash."""

        return _canonical_sha256(self.to_dict())


DEFAULT_CONFIG = FrozenTextEncoderConfig()


def mean_pooling(token_embeddings: Tensor, attention_mask: Tensor) -> Tensor:
    """Apply the sole permitted mask-mean pooling and L2 normalization."""

    if token_embeddings.ndim != 3:
        raise ValueError("token_embeddings must have shape [batch,tokens,hidden]")
    if attention_mask.ndim != 2 or tuple(attention_mask.shape) != tuple(token_embeddings.shape[:2]):
        raise ValueError("attention_mask must match [batch,tokens]")
    mask = attention_mask.unsqueeze(-1).to(token_embeddings.dtype)
    pooled = (token_embeddings * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1e-9)
    embedding = F.normalize(pooled, p=2, dim=1)
    embedding = embedding.to(torch.float32)
    if not torch.isfinite(embedding).all():
        raise ValueError("pooling produced non-finite output")
    return embedding


def exact_utf8_text_sha256(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_sha256(name: str, value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a 64-character SHA256 hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{name} must be a 64-character SHA256 hex digest") from error
    return value.lower()


def build_cache_key(
    text: str,
    *,
    tokenizer_manifest_hash: str,
    encoder_config_manifest_hash: str,
    scientific_config_hash: str,
    config: FrozenTextEncoderConfig = DEFAULT_CONFIG,
    model_id: str | None = None,
    revision: str | None = None,
    pooling: str | None = None,
    normalization: str | None = None,
) -> str:
    """Build a stable cache key bound to exact text and the frozen contract."""

    tokenizer_manifest_hash = _validate_sha256(
        "tokenizer_manifest_hash", tokenizer_manifest_hash
    )
    encoder_config_manifest_hash = _validate_sha256(
        "encoder_config_manifest_hash", encoder_config_manifest_hash
    )
    scientific_config_hash = _validate_sha256(
        "scientific_config_hash", scientific_config_hash
    )
    payload = {
        "exact_utf8_text_sha256": exact_utf8_text_sha256(text),
        "model_id": config.model_id if model_id is None else model_id,
        "revision": config.revision if revision is None else revision,
        "tokenizer_manifest_hash": tokenizer_manifest_hash,
        "encoder_config_manifest_hash": encoder_config_manifest_hash,
        "scientific_config_hash": scientific_config_hash,
        "pooling": config.pooling if pooling is None else pooling,
        "normalization": config.normalization if normalization is None else normalization,
    }
    return _canonical_sha256(payload)


@dataclass(frozen=True)
class TokenizationRecord:
    exact_utf8_text_sha256: str
    token_count_before_truncation: int
    token_count_after_truncation: int
    truncated: bool
    cache_key: str


@dataclass(frozen=True)
class EncodingResult:
    embeddings: Tensor
    records: tuple[TokenizationRecord, ...]
    model_max_length: int


def _flat_token_count(encoded: Any) -> int:
    ids = encoded["input_ids"]
    if isinstance(ids, Tensor):
        if ids.ndim == 2:
            if ids.shape[0] != 1:
                raise ValueError("single-text tokenization returned multiple rows")
            return int(ids.shape[1])
        return int(ids.numel())
    if ids and isinstance(ids[0], (list, tuple)):
        if len(ids) != 1:
            raise ValueError("single-text tokenization returned multiple rows")
        ids = ids[0]
    return len(ids)


class FrozenMiniLMEncoder:
    """One frozen encoder instance with injectable offline test doubles."""

    def __init__(
        self,
        *,
        tokenizer: Any | None = None,
        model: Any | None = None,
        tokenizer_manifest_hash: str,
        encoder_config_manifest_hash: str,
        config: FrozenTextEncoderConfig = DEFAULT_CONFIG,
        device: str | torch.device = "cpu",
        local_files_only: bool = False,
    ) -> None:
        if (tokenizer is None) != (model is None):
            raise ValueError("tokenizer and model must be supplied together")
        self.config = config
        self.device = torch.device(device)
        self.tokenizer_manifest_hash = _validate_sha256(
            "tokenizer_manifest_hash", tokenizer_manifest_hash
        )
        self.encoder_config_manifest_hash = _validate_sha256(
            "encoder_config_manifest_hash", encoder_config_manifest_hash
        )
        self.scientific_config_hash = _validate_sha256(
            "scientific_config_hash", config.scientific_config_hash
        )
        if tokenizer is None:
            from transformers import AutoModel, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                config.model_id,
                revision=config.revision,
                trust_remote_code=False,
                local_files_only=local_files_only,
            )
            model = AutoModel.from_pretrained(
                config.model_id,
                revision=config.revision,
                trust_remote_code=False,
                local_files_only=local_files_only,
                use_safetensors=True,
            )
        self.tokenizer = tokenizer
        self.model = model.to(self.device)
        self.model.eval()
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)
        hidden_size = int(getattr(self.model.config, "hidden_size", -1))
        if hidden_size != config.output_dim:
            raise ValueError(
                f"model hidden size {hidden_size} does not match frozen output_dim {config.output_dim}"
            )
        self.model_max_length = self._resolve_model_max_length()

    def _resolve_model_max_length(self) -> int:
        tokenizer_limit = int(getattr(self.tokenizer, "model_max_length", 0))
        config_limit = int(getattr(self.model.config, "max_position_embeddings", 0))
        required = self.config.max_seq_length
        if tokenizer_limit < required:
            raise ValueError(
                "tokenizer.model_max_length is below the frozen sentence-transformers "
                f"max_seq_length: {tokenizer_limit} < {required}"
            )
        if config_limit < required:
            raise ValueError(
                "model.config.max_position_embeddings is below the frozen "
                f"sentence-transformers max_seq_length: {config_limit} < {required}"
            )
        return required

    @property
    def total_parameter_count(self) -> int:
        return sum(int(parameter.numel()) for parameter in self.model.parameters())

    @property
    def trainable_parameter_count(self) -> int:
        return sum(
            int(parameter.numel())
            for parameter in self.model.parameters()
            if parameter.requires_grad
        )

    def encode(self, texts: str | Sequence[str]) -> EncodingResult:
        """Encode one string or a non-empty batch through the shared contract."""

        normalized_texts = [texts] if isinstance(texts, str) else list(texts)
        if not normalized_texts:
            raise ValueError("texts batch must be non-empty")
        if any(not isinstance(text, str) for text in normalized_texts):
            raise TypeError("every text must be str")

        before_counts = []
        for text in normalized_texts:
            untruncated = self.tokenizer(
                text,
                add_special_tokens=True,
                truncation=False,
                padding=False,
                return_attention_mask=False,
            )
            before_counts.append(_flat_token_count(untruncated))

        batch = self.tokenizer(
            normalized_texts,
            add_special_tokens=True,
            padding=True,
            truncation=True,
            max_length=self.model_max_length,
            return_attention_mask=True,
            return_tensors="pt",
        )
        if "input_ids" not in batch or "attention_mask" not in batch:
            raise ValueError("tokenizer must return input_ids and attention_mask")
        model_inputs = {
            key: value.to(self.device) if isinstance(value, Tensor) else value
            for key, value in batch.items()
        }
        attention_mask = model_inputs["attention_mask"]
        if not isinstance(attention_mask, Tensor):
            raise TypeError("attention_mask must be a tensor")
        after_counts = [int(value) for value in attention_mask.sum(dim=1).tolist()]

        with torch.no_grad():
            outputs = self.model(**model_inputs)
            embeddings = mean_pooling(outputs.last_hidden_state, attention_mask)
        embeddings = embeddings.detach().to(torch.float32)
        expected_shape = (len(normalized_texts), self.config.output_dim)
        if tuple(embeddings.shape) != expected_shape:
            raise ValueError(f"unexpected encoder output shape: {tuple(embeddings.shape)}")
        if embeddings.requires_grad or not torch.isfinite(embeddings).all():
            raise ValueError("encoder output violates no-grad/finite contract")

        records = tuple(
            TokenizationRecord(
                exact_utf8_text_sha256=exact_utf8_text_sha256(text),
                token_count_before_truncation=before,
                token_count_after_truncation=after,
                truncated=before > after,
                cache_key=build_cache_key(
                    text,
                    tokenizer_manifest_hash=self.tokenizer_manifest_hash,
                    encoder_config_manifest_hash=self.encoder_config_manifest_hash,
                    scientific_config_hash=self.scientific_config_hash,
                    config=self.config,
                ),
            )
            for text, before, after in zip(
                normalized_texts, before_counts, after_counts, strict=True
            )
        )
        return EncodingResult(
            embeddings=embeddings,
            records=records,
            model_max_length=self.model_max_length,
        )


def encode(
    texts: str | Sequence[str],
    *,
    encoder: FrozenMiniLMEncoder,
) -> EncodingResult:
    """Public shared interface for sentence, item, H and candidate callers."""

    return encoder.encode(texts)
