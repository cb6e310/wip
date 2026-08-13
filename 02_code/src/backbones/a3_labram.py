"""A3 LaBraM preparation wrapper.

This module contains only the frozen engineering contract needed for a later
T6 extraction.  It deliberately refuses to run on an unverified channel map.
The map is kept separate from the model because EGI labels are not LaBraM
semantic channel names.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch


@dataclass(frozen=True)
class A3Config:
    source_sampling_rate_hz: int = 500
    sampling_rate_hz: int = 200
    window_seconds: float = 5.0
    stride_seconds: float = 2.5
    patch_samples: int = 200
    n_channels: int = 128
    embedding_dim: int = 200
    expected_model_pos_slots: int = 128
    expected_time_pos_slots: int = 16
    bandpass_hz: tuple[float, float] = (0.1, 75.0)
    notch_hz: float = 50.0
    notch_q: float | None = None
    filter_order: int | None = None
    release_scale_divisor: float = 100.0

    @property
    def window_samples(self) -> int:
        return int(self.sampling_rate_hz * self.window_seconds)

    @property
    def stride_samples(self) -> int:
        return int(self.sampling_rate_hz * self.stride_seconds)

    @property
    def n_patches(self) -> int:
        return self.window_samples // self.patch_samples

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update(
            window_samples=self.window_samples,
            stride_samples=self.stride_samples,
            n_patches=self.n_patches,
        )
        return result


@dataclass(frozen=True)
class A3ChannelMap:
    """Explicit source-to-model order.

    ``source_indices`` is ordered by model channel, so the values are used to
    reorder a raw source tensor before it is passed to LaBraM.  ``verified``
    must stay false until an approved montage/interpolation decision is frozen.
    """

    source_labels: tuple[str, ...]
    model_channel_names: tuple[str, ...]
    source_indices: tuple[int, ...]
    model_input_chans: tuple[int, ...]
    provenance: str
    coverage: float
    verified: bool = False
    mixing_matrix: np.ndarray | None = None

    def __post_init__(self) -> None:
        if len(self.source_labels) != 128:
            raise ValueError("A3 requires 128 source labels")
        if len(self.model_channel_names) != 128:
            raise ValueError("A3 requires 128 model channel names")
        if len(self.source_indices) != 128:
            raise ValueError("source_indices must contain 128 entries")
        if len(self.model_input_chans) != 129 or self.model_input_chans[0] != 0:
            raise ValueError("model_input_chans must be [CLS=0] + 128 positions")
        if len(set(self.source_labels)) != 128:
            raise ValueError("source labels must be unique")
        if len(set(self.model_channel_names)) != 128:
            raise ValueError("model channel names must be unique")
        if self.mixing_matrix is None and sorted(self.source_indices) != list(range(128)):
            raise ValueError("source_indices must be a complete 128-channel permutation")
        if sorted(self.model_input_chans[1:]) != list(range(1, 129)):
            raise ValueError("model_input_chans must contain each checkpoint position 1..128")
        if any(i < 0 or i >= 128 for i in self.source_indices):
            raise ValueError("source index outside 128-channel input")
        if any(i < 0 or i > 128 for i in self.model_input_chans):
            raise ValueError("model positional index outside checkpoint capacity")
        if not self.provenance.strip():
            raise ValueError("channel-map provenance is required")
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("coverage must be in [0, 1]")
        if self.verified and self.coverage != 1.0:
            raise ValueError("verified map must have complete coverage")
        if self.mixing_matrix is not None:
            matrix = np.asarray(self.mixing_matrix, dtype=np.float64)
            if matrix.shape != (128, 128) or not np.isfinite(matrix).all():
                raise ValueError("mixing_matrix must be finite with shape [128,128]")

    def reorder(self, windows: np.ndarray) -> np.ndarray:
        if windows.ndim != 3 or windows.shape[1] != 128:
            raise ValueError("expected windows with shape [N,128,T]")
        if self.mixing_matrix is None:
            return windows[:, list(self.source_indices), :]
        matrix = np.asarray(self.mixing_matrix, dtype=windows.dtype)
        return np.einsum("ij,njt->nit", matrix, windows, optimize=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_labels": list(self.source_labels),
            "model_channel_names": list(self.model_channel_names),
            "source_indices": list(self.source_indices),
            "model_input_chans": list(self.model_input_chans),
            "provenance": self.provenance,
            "coverage": self.coverage,
            "verified": self.verified,
            "mixing_matrix": None if self.mixing_matrix is None else np.asarray(self.mixing_matrix).tolist(),
        }


def synthetic_contract_map() -> A3ChannelMap:
    """Return an identity map for shape-only smoke tests.

    It is intentionally marked unverified and cannot be used by the default
    extraction path.
    """

    labels = tuple(f"E{i}" for i in range(1, 129))
    return A3ChannelMap(
        source_labels=labels,
        model_channel_names=labels,
        source_indices=tuple(range(128)),
        model_input_chans=tuple(range(129)),
        provenance="synthetic identity map; shape smoke only",
        coverage=0.0,
        verified=False,
    )


def window_signal(signal: np.ndarray, config: A3Config = A3Config()) -> np.ndarray:
    """Slice a [128,T] signal into non-padded 5 s windows at 2.5 s stride."""

    signal = np.asarray(signal)
    if signal.ndim != 2 or signal.shape[0] != config.n_channels:
        raise ValueError(f"expected signal shape [128,T], got {signal.shape}")
    if signal.shape[1] < config.window_samples:
        return np.empty((0, config.n_channels, config.window_samples), dtype=signal.dtype)
    starts = range(0, signal.shape[1] - config.window_samples + 1, config.stride_samples)
    return np.stack([signal[:, start : start + config.window_samples] for start in starts])


def preprocess_raw_signal(signal: np.ndarray, config: A3Config = A3Config()) -> np.ndarray:
    """Apply the explicit LaBraM release preprocessing candidate.

    Filtering occurs before polyphase resampling; the official finetuning
    engine divides its input by 100 before patching. The source-unit decision
    remains a project blocker until the data-card convention is approved.
    """

    from scipy.signal import butter, filtfilt, iirnotch, resample_poly, sosfiltfilt

    signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim != 2 or signal.shape[0] != config.n_channels:
        raise ValueError(f"expected raw signal shape [128,T], got {signal.shape}")
    if not np.isfinite(signal).all():
        raise ValueError("raw signal contains non-finite values")
    if signal.shape[1] < 4 * config.source_sampling_rate_hz:
        raise ValueError("raw signal is too short for zero-phase filtering")
    if config.filter_order is None or config.notch_q is None:
        raise RuntimeError("A3 filter order and notch Q are not frozen; provide an approved candidate explicitly")
    low, high = config.bandpass_hz
    if not 0 < low < high < config.source_sampling_rate_hz / 2:
        raise ValueError("invalid A3 bandpass contract")
    sos = butter(config.filter_order, (low, high), btype="bandpass", fs=config.source_sampling_rate_hz, output="sos")
    filtered = sosfiltfilt(sos, signal, axis=1)
    notch_b, notch_a = iirnotch(config.notch_hz, config.notch_q, fs=config.source_sampling_rate_hz)
    filtered = filtfilt(notch_b, notch_a, filtered, axis=1)
    resampled = resample_poly(filtered, up=2, down=5, axis=1)
    return (resampled / config.release_scale_divisor).astype(np.float32, copy=False)


def checkpoint_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_hash(config: A3Config = A3Config()) -> str:
    payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _load_vendor_modeling(vendor_root: Path):
    vendor_root = vendor_root.resolve()
    if str(vendor_root) not in sys.path:
        sys.path.insert(0, str(vendor_root))
    return importlib.import_module("modeling_finetune")


def load_labram_base(
    checkpoint_path: Path,
    vendor_root: Path,
    config: A3Config = A3Config(),
) -> torch.nn.Module:
    """Build the official Base constructor and load its student weights."""

    modeling = _load_vendor_modeling(vendor_root)
    model = modeling.labram_base_patch200_200(
        num_classes=0,
        EEG_size=config.window_samples,
        init_values=0.1,
        use_mean_pooling=True,
        qkv_bias=False,
        use_abs_pos_emb=True,
        use_rel_pos_bias=False,
        drop_path_rate=0.0,
    )
    if tuple(model.pos_embed.shape) != (1, config.expected_model_pos_slots + 1, config.embedding_dim):
        raise RuntimeError(f"unexpected LaBraM spatial position shape: {tuple(model.pos_embed.shape)}")
    if tuple(model.time_embed.shape) != (1, config.expected_time_pos_slots, config.embedding_dim):
        raise RuntimeError(f"unexpected LaBraM temporal position shape: {tuple(model.time_embed.shape)}")
    if config.n_patches > config.expected_time_pos_slots:
        raise ValueError("A3 window exceeds the checkpoint temporal-position capacity")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state = checkpoint.get("model", checkpoint)
    student = {key.removeprefix("student."): value for key, value in state.items() if key.startswith("student.")}
    if not student:
        student = state
    missing, unexpected = model.load_state_dict(student, strict=False)
    allowed_missing = {"fc_norm.weight", "fc_norm.bias"}
    allowed_unexpected = {
        "norm.weight",
        "norm.bias",
        "mask_token",
        "lm_head.weight",
        "lm_head.bias",
    }
    missing_set = set(missing)
    if missing_set - allowed_missing:
        raise RuntimeError(f"unexpected missing LaBraM checkpoint keys: {sorted(missing_set)}")
    unexpected_set = set(unexpected)
    if unexpected_set - allowed_unexpected:
        raise RuntimeError(f"unexpected LaBraM checkpoint keys: {sorted(unexpected_set)}")
    model._a3_load_diagnostics = {
        "missing_expected": sorted(missing_set),
        "unexpected_expected": sorted(unexpected_set),
        "init_values": 0.1,
        "use_mean_pooling": True,
        "qkv_bias": False,
        "use_abs_pos_emb": True,
        "use_rel_pos_bias": False,
        "drop_path_rate": 0.0,
        "pooling_order": "fc_norm(mean(non_cls_patch_tokens))",
    }
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.eval()
    return model


@torch.no_grad()
def extract_pooled_embeddings(
    model: torch.nn.Module,
    windows: np.ndarray,
    channel_map: A3ChannelMap,
    config: A3Config = A3Config(),
) -> np.ndarray:
    """Extract release-pooled 200D embeddings from already-resampled windows."""

    if not channel_map.verified:
        raise RuntimeError("A3 channel map is not verified; extraction is blocked")
    if windows.ndim != 3 or windows.shape[1:] != (config.n_channels, config.window_samples):
        raise ValueError(f"expected windows [{config.n_channels},{config.window_samples}], got {windows.shape}")
    ordered = channel_map.reorder(windows)
    tensor = torch.as_tensor(ordered, dtype=torch.float32).reshape(
        ordered.shape[0], config.n_channels, config.n_patches, config.patch_samples
    )
    pooled = model(
        tensor,
        input_chans=list(channel_map.model_input_chans),
        return_patch_tokens=False,
    )
    if tuple(pooled.shape) != (ordered.shape[0], config.embedding_dim):
        raise RuntimeError(f"unexpected LaBraM pooled shape: {tuple(pooled.shape)}")
    return pooled.detach().cpu().numpy().astype(np.float32, copy=False)


def run_metadata(seed: int, fold: str, method: str, config: A3Config = A3Config()) -> dict[str, Any]:
    return {
        "seed": int(seed),
        "fold": str(fold),
        "method": str(method),
        "config_hash": config_hash(config),
        "config": config.to_dict(),
    }
