"""A1: deterministic spectral frontend and shared alignment encoder.

The scientific contract is the v3.7 specification section 4.7.1.  This module
contains no dataset loader and no eye-tracking features.  A caller supplies
either EEG epochs already aligned to words or a continuous EEG sentence for
the ET-free fixed-window sensitivity.  Normalization is deliberately a
separate object so that callers must fit it on an outer-training fold.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Iterable, Sequence

import numpy as np
import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class BandDefinition:
    """A half-open frequency band in Hz."""

    name: str
    low_hz: float
    high_hz: float

    def __post_init__(self) -> None:
        if not self.name or self.low_hz < 0 or self.high_hz <= self.low_hz:
            raise ValueError(f"invalid band definition: {self}")


# SPEC v3.7 D8 freezes these exact eight half-open ZuCo 2.0 frequency bands.
# Their values and ordering remain recorded and hash-bound in every A1 run.
DEFAULT_BANDS: tuple[BandDefinition, ...] = (
    BandDefinition("theta1", 4.0, 6.0),
    BandDefinition("theta2", 6.5, 8.0),
    BandDefinition("alpha1", 8.5, 10.0),
    BandDefinition("alpha2", 10.5, 13.0),
    BandDefinition("beta1", 13.5, 18.0),
    BandDefinition("beta2", 18.5, 30.0),
    BandDefinition("gamma1", 30.5, 40.0),
    BandDefinition("gamma2", 40.0, 49.5),
)


@dataclass(frozen=True)
class A1Config:
    """All A1 values that affect features or the alignment encoder.

    ``sampling_rate_hz=500`` and ``n_channels=105`` are explicit, hash-bound
    parts of the v3.7 D8/D9 contract.  Real-file admission must still verify
    those properties before paper-level use.
    """

    n_channels: int = 105
    sampling_rate_hz: float = 500.0
    bands: tuple[BandDefinition, ...] = field(default_factory=lambda: DEFAULT_BANDS)
    fixed_window_seconds: float = 1.0
    fixed_stride_seconds: float = 0.5
    clip_lower_quantile: float = 0.005
    clip_upper_quantile: float = 0.995
    d_model: int = 256
    encoder_layers: int = 2
    encoder_heads: int = 8
    encoder_feedforward: int = 512
    d_align: int = 384
    max_encoder_layers: int = 6
    max_encoder_d_model: int = 512
    max_encoder_params: int = 20_000_000
    # ``np.stack(..., axis=1).reshape`` emits all eight bands per channel.
    feature_order: str = "channel_major"
    finite_policy: str = "reject_any_nonfinite_no_imputation"

    def __post_init__(self) -> None:
        if self.n_channels < 1:
            raise ValueError("n_channels must be positive")
        if self.sampling_rate_hz <= 2.0 * max(b.high_hz for b in self.bands):
            raise ValueError("sampling_rate_hz must exceed twice the highest band")
        if len(self.bands) != 8:
            raise ValueError("A1 requires exactly eight frequency bands")
        if not 0.0 < self.clip_lower_quantile < self.clip_upper_quantile < 1.0:
            raise ValueError("invalid robust clipping quantiles")
        if self.fixed_window_seconds <= 0 or self.fixed_stride_seconds <= 0:
            raise ValueError("fixed-window durations must be positive")
        if self.d_model < 1 or self.d_model > self.max_encoder_d_model:
            raise ValueError("d_model exceeds the A1 contract")
        if self.encoder_layers < 1 or self.encoder_layers > self.max_encoder_layers:
            raise ValueError("encoder layer count exceeds the A1 contract")
        if self.encoder_heads < 1 or self.d_model % self.encoder_heads:
            raise ValueError("encoder_heads must divide d_model")
        if self.encoder_feedforward < 1 or self.d_align < 1:
            raise ValueError("encoder dimensions must be positive")
        if self.feature_order != "channel_major":
            raise ValueError("A1 feature order is frozen to channel_major")
        if self.finite_policy != "reject_any_nonfinite_no_imputation":
            raise ValueError("A1 finite policy is frozen to strict rejection")

    @property
    def feature_dim(self) -> int:
        return self.n_channels * len(self.bands)

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["bands"] = [asdict(band) for band in self.bands]
        value["feature_dim"] = self.feature_dim
        return value


DEFAULT_CONFIG = A1Config()


@dataclass(frozen=True)
class A1ChannelMap:
    """Explicit source-to-A1 mapping for an optional non-contract raw source.

    The v3.7 fixed-window contract prefers the already 105-channel
    ``sentenceData.rawData`` source and requires no 128-to-105 map.  If a
    separate 128-channel continuous source is ever supplied, this explicit
    verified map is mandatory: positional ``first-105`` fallback is forbidden.
    """

    source_labels: tuple[str, ...]
    target_labels: tuple[str, ...]
    source_indices: tuple[int, ...]
    provenance: str
    coverage: float

    def __post_init__(self) -> None:
        if not self.source_labels or not self.target_labels:
            raise ValueError("source and target channel labels are required")
        if len(set(self.source_labels)) != len(self.source_labels):
            raise ValueError("source channel labels must be unique")
        if len(set(self.target_labels)) != len(self.target_labels):
            raise ValueError("target channel labels must be unique")
        if len(self.target_labels) != len(self.source_indices):
            raise ValueError("each target channel needs exactly one source index")
        if len(self.target_labels) != 105:
            raise ValueError("A1 currently requires exactly 105 target EEG channels")
        if any(index < 0 or index >= len(self.source_labels) for index in self.source_indices):
            raise ValueError("source channel index is outside source_labels")
        if len(set(self.source_indices)) != len(self.source_indices):
            raise ValueError("source channel indices must be unique")
        if not self.provenance.strip():
            raise ValueError("channel-map provenance is required")
        if not 0.0 < self.coverage <= 1.0:
            raise ValueError("channel-map coverage must be in (0, 1]")

    @property
    def source_channels(self) -> int:
        return len(self.source_labels)

    @property
    def target_channels(self) -> int:
        return len(self.target_labels)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_labels": list(self.source_labels),
            "target_labels": list(self.target_labels),
            "source_indices": list(self.source_indices),
            "provenance": self.provenance,
            "coverage": self.coverage,
        }

    def apply(self, continuous_eeg: object) -> np.ndarray:
        """Map ``[C,T]`` or ``[T,C]`` EEG to the 105-channel A1 order."""

        array = np.asarray(continuous_eeg)
        if array.ndim != 2:
            raise ValueError("continuous EEG must be rank-2")
        if array.shape[0] == self.source_channels:
            source_first = array
        elif array.shape[1] == self.source_channels:
            source_first = array.T
        else:
            raise ValueError(
                "continuous EEG does not match the channel-map source count: "
                f"shape={array.shape}, source_channels={self.source_channels}"
            )
        return np.asarray(source_first[list(self.source_indices)], dtype=np.float64)


def config_hash(config: A1Config = DEFAULT_CONFIG) -> str:
    """Return the stable hash recorded with every A1 run."""

    payload = json.dumps(config.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_metadata(
    *, seed: int, fold: str | int, method: str = "A1", config: A1Config = DEFAULT_CONFIG
) -> dict[str, object]:
    """Build the minimum traceability fields required for a run ledger."""

    if seed < 0:
        raise ValueError("seed must be non-negative")
    if str(fold).strip() == "":
        raise ValueError("fold must be non-empty")
    if not method.strip():
        raise ValueError("method must be non-empty")
    return {
        "seed": int(seed),
        "fold": str(fold),
        "method": method,
        "config_hash": config_hash(config),
    }


def _orient_epoch(value: object, n_channels: int) -> np.ndarray:
    """Convert a numeric epoch or a list of fixation matrices to [C, time]."""

    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            try:
                parts.append(_orient_epoch(item, n_channels))
            except ValueError:
                continue
        if parts:
            return np.concatenate(parts, axis=1)
        raise ValueError("epoch contains no numeric matrices")

    array = np.asarray(value)
    if array.dtype == object:
        parts = []
        for item in array.reshape(-1):
            try:
                parts.append(_orient_epoch(item, n_channels))
            except ValueError:
                continue
        if parts:
            return np.concatenate(parts, axis=1)
        raise ValueError("object epoch contains no numeric matrices")
    if array.ndim != 2 or array.size == 0:
        raise ValueError(f"epoch must be a non-empty rank-2 matrix, got {array.shape}")
    if array.shape[0] == n_channels:
        oriented = array
    elif array.shape[1] == n_channels:
        oriented = array.T
    else:
        raise ValueError(
            f"epoch has no axis with n_channels={n_channels}: shape={array.shape}"
        )
    if not np.issubdtype(oriented.dtype, np.number):
        raise ValueError("epoch is not numeric")
    if oriented.shape[1] < 1:
        raise ValueError("epoch has no time samples")
    return np.asarray(oriented, dtype=np.float64)


def bandpower_features(
    epoch: object,
    *,
    config: A1Config = DEFAULT_CONFIG,
    sampling_rate_hz: float | None = None,
) -> np.ndarray:
    """Compute one deterministic ``(C * 8,)`` band-power feature vector.

    The PSD is integrated over half-open bands after channel-wise demeaning and
    a Hann window.  No eye-tracking value, epoch length, or sequence length is
    appended to the result.
    """

    fs = config.sampling_rate_hz if sampling_rate_hz is None else float(sampling_rate_hz)
    if fs <= 2.0 * max(band.high_hz for band in config.bands):
        raise ValueError("sampling rate is too low for the configured bands")
    x = _orient_epoch(epoch, config.n_channels)
    if not np.isfinite(x).all():
        raise ValueError("epoch contains NaN/Inf; A1 forbids imputation")
    x = x - x.mean(axis=1, keepdims=True)
    window = np.hanning(x.shape[1])
    if not np.any(window):
        raise ValueError("epoch window is degenerate")
    n_fft = max(512, 1 << int(math.ceil(math.log2(x.shape[1]))))
    spectrum = np.fft.rfft(x * window[None, :], n=n_fft, axis=1)
    frequencies = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    psd = (np.abs(spectrum) ** 2) / (fs * float(np.sum(window**2)))
    frequency_step = float(frequencies[1] - frequencies[0])
    features: list[np.ndarray] = []
    for band in config.bands:
        selected = (frequencies >= band.low_hz) & (frequencies < band.high_hz)
        if not np.any(selected):
            values = np.zeros(config.n_channels, dtype=np.float64)
        else:
            values = np.sum(psd[:, selected], axis=1) * frequency_step
        features.append(np.asarray(values, dtype=np.float32))
    result = np.stack(features, axis=1).reshape(-1).astype(np.float32)
    if result.shape != (config.feature_dim,) or not np.isfinite(result).all():
        raise ValueError("bandpower feature computation produced an invalid result")
    return result


def analysis_spectrum_phase_rotation_features(
    epoch: object,
    *,
    seed: int,
    config: A1Config = DEFAULT_CONFIG,
    sampling_rate_hz: float | None = None,
) -> np.ndarray:
    """Recompute A1 features after rotating only the analysis-spectrum phase.

    This is the v3.13 D32 implementation diagnostic, not a sham generator.
    It performs the same demean/Hann/rFFT analysis as :func:`bandpower_features`,
    rotates legal complex bins, preserves DC and Nyquist reality, and integrates
    the rotated magnitude squared directly.  It deliberately performs no
    inverse transform and no second Hann window.
    """

    if seed < 0:
        raise ValueError("seed must be non-negative")
    fs = config.sampling_rate_hz if sampling_rate_hz is None else float(sampling_rate_hz)
    if fs <= 2.0 * max(band.high_hz for band in config.bands):
        raise ValueError("sampling rate is too low for the configured bands")
    x = _orient_epoch(epoch, config.n_channels)
    if not np.isfinite(x).all():
        raise ValueError("epoch contains NaN/Inf; A1 forbids imputation")
    x = x - x.mean(axis=1, keepdims=True)
    window = np.hanning(x.shape[1])
    if not np.any(window):
        raise ValueError("epoch window is degenerate")
    n_fft = max(512, 1 << int(math.ceil(math.log2(x.shape[1]))))
    spectrum = np.fft.rfft(x * window[None, :], n=n_fft, axis=1)
    magnitude = np.abs(spectrum)
    phase = np.angle(spectrum)
    rotation = np.random.default_rng(seed).uniform(-math.pi, math.pi, size=spectrum.shape)
    rotation[:, 0] = 0.0
    if n_fft % 2 == 0:
        rotation[:, -1] = 0.0
    rotated = magnitude * np.exp(1j * (phase + rotation))
    rotated[:, 0] = spectrum[:, 0].real
    if n_fft % 2 == 0:
        rotated[:, -1] = spectrum[:, -1].real
    frequencies = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    psd = (np.abs(rotated) ** 2) / (fs * float(np.sum(window**2)))
    frequency_step = float(frequencies[1] - frequencies[0])
    features: list[np.ndarray] = []
    for band in config.bands:
        selected = (frequencies >= band.low_hz) & (frequencies < band.high_hz)
        values = (
            np.sum(psd[:, selected], axis=1) * frequency_step
            if np.any(selected)
            else np.zeros(config.n_channels, dtype=np.float64)
        )
        features.append(np.asarray(values, dtype=np.float32))
    result = np.stack(features, axis=1).reshape(-1).astype(np.float32)
    if result.shape != (config.feature_dim,) or not np.isfinite(result).all():
        raise ValueError("phase diagnostic produced an invalid result")
    return result


def extract_word_level_sequence(
    word_epochs: Iterable[object], *, config: A1Config = DEFAULT_CONFIG
) -> np.ndarray:
    """Extract the ET-aligned word sequence from EEG epochs only.

    Invalid/missing word epochs are skipped, matching the existing ZuCo reader;
    no eye-tracking scalar is consumed.  The caller retains the word order.
    """

    features: list[np.ndarray] = []
    for epoch in word_epochs:
        try:
            features.append(bandpower_features(epoch, config=config))
        except (TypeError, ValueError):
            continue
    if not features:
        raise ValueError("no valid word-level EEG epochs were provided")
    return np.stack(features, axis=0).astype(np.float32, copy=False)


def extract_fixed_window_sequence(
    continuous_eeg: object,
    *,
    config: A1Config = DEFAULT_CONFIG,
    sampling_rate_hz: float | None = None,
    channel_map: A1ChannelMap | None = None,
) -> np.ndarray:
    """Extract the mandatory ET-free 1 s / 0.5 s fixed-window sequence.

    The preferred source is 105-channel ``sentenceData.rawData``, which can
    enter this frontend directly in either ``[C,time]`` or ``[time,C]`` order.
    Only complete windows are retained and no eye data are consumed.  A
    128-channel continuous source is never implicitly truncated to first-105.
    """

    fs = config.sampling_rate_hz if sampling_rate_hz is None else float(sampling_rate_hz)
    if fs <= 0:
        raise ValueError("sampling_rate_hz must be positive")
    raw_array = np.asarray(continuous_eeg)
    if channel_map is not None:
        if channel_map.target_channels != config.n_channels:
            raise ValueError("channel map target count must match A1 n_channels")
        continuous = channel_map.apply(raw_array)
    else:
        # Direct input is the 105-channel sentenceData.rawData contract.  In
        # particular, a 128-channel continuous file cannot silently drop
        # channels or masquerade as this field.
        continuous = _orient_epoch(raw_array, config.n_channels)
    window_samples = int(round(config.fixed_window_seconds * fs))
    stride_samples = int(round(config.fixed_stride_seconds * fs))
    if window_samples < 1 or stride_samples < 1:
        raise ValueError("fixed-window sample counts must be positive")
    if continuous.shape[1] < window_samples:
        raise ValueError(
            f"continuous EEG has {continuous.shape[1]} samples, shorter than one "
            f"{window_samples}-sample window"
        )
    starts = range(0, continuous.shape[1] - window_samples + 1, stride_samples)
    features = [
        bandpower_features(
            continuous[:, start : start + window_samples],
            config=config,
            sampling_rate_hz=fs,
        )
        for start in starts
    ]
    result = np.stack(features, axis=0).astype(np.float32, copy=False)
    if result.ndim != 2 or result.shape[1] != config.feature_dim:
        raise ValueError("fixed-window extraction produced an invalid sequence")
    return result


class RobustFeatureNormalizer:
    """Fold-local median/IQR normalization with 0.5/99.5% clipping."""

    def __init__(self, config: A1Config = DEFAULT_CONFIG) -> None:
        self.config = config
        self.lower: np.ndarray | None = None
        self.upper: np.ndarray | None = None
        self.median: np.ndarray | None = None
        self.iqr: np.ndarray | None = None

    @property
    def fitted(self) -> bool:
        return self.lower is not None

    def fit(self, train_sequences: Sequence[np.ndarray]) -> "RobustFeatureNormalizer":
        """Fit using *only* sequences from one outer-training fold."""

        if not train_sequences:
            raise ValueError("at least one training sequence is required")
        rows: list[np.ndarray] = []
        for sequence in train_sequences:
            array = np.asarray(sequence)
            if array.ndim != 2 or array.shape[1] != self.config.feature_dim:
                raise ValueError(
                    "training sequences must have shape (T, C*8), "
                    f"got {array.shape}"
                )
            if array.shape[0] < 1 or not np.isfinite(array).all():
                raise ValueError("training sequences must be non-empty and finite")
            rows.append(array.astype(np.float64, copy=False))
        train = np.concatenate(rows, axis=0)
        self.lower = np.quantile(train, self.config.clip_lower_quantile, axis=0)
        self.upper = np.quantile(train, self.config.clip_upper_quantile, axis=0)
        clipped = np.clip(train, self.lower, self.upper)
        self.median = np.median(clipped, axis=0)
        q25, q75 = np.quantile(clipped, [0.25, 0.75], axis=0)
        self.iqr = np.maximum(q75 - q25, 1e-6)
        return self

    def transform(self, sequence: np.ndarray) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("normalizer must be fit on an outer-training fold first")
        array = np.asarray(sequence)
        if array.ndim != 2 or array.shape[1] != self.config.feature_dim:
            raise ValueError(f"sequence must have shape (T, {self.config.feature_dim})")
        if not np.isfinite(array).all():
            raise ValueError("sequence contains NaN/Inf")
        assert self.lower is not None
        assert self.upper is not None
        assert self.median is not None
        assert self.iqr is not None
        clipped = np.clip(array.astype(np.float64, copy=False), self.lower, self.upper)
        return ((clipped - self.median) / self.iqr).astype(np.float32)

    def transform_many(self, sequences: Sequence[np.ndarray]) -> list[np.ndarray]:
        return [self.transform(sequence) for sequence in sequences]

    def summary(self) -> dict[str, float | int | str]:
        if not self.fitted:
            raise RuntimeError("normalizer is not fitted")
        assert self.lower is not None and self.upper is not None and self.iqr is not None
        assert self.median is not None
        return {
            "feature_dim": self.config.feature_dim,
            "config_hash": config_hash(self.config),
            "train_median_abs_max": float(np.max(np.abs(self.median))),
            "train_iqr_min": float(np.min(self.iqr)),
            "train_iqr_max": float(np.max(self.iqr)),
            "clip_lower_min": float(np.min(self.lower)),
            "clip_upper_max": float(np.max(self.upper)),
        }


def pad_feature_sequences(
    sequences: Sequence[np.ndarray], *, device: torch.device | str | None = None
) -> tuple[Tensor, Tensor]:
    """Pad normalized sequences into the A1 tensor contract.

    Returns ``(features, mask)`` with shapes ``(B,T_max,D)`` and
    ``(B,T_max)``.  The mask is the only representation of variable sequence
    length; no length scalar is concatenated to the features.
    """

    if not sequences:
        raise ValueError("at least one sequence is required")
    arrays = []
    feature_dim: int | None = None
    for sequence in sequences:
        array = np.asarray(sequence)
        if array.ndim != 2 or array.shape[0] < 1:
            raise ValueError(f"sequence must be non-empty rank-2, got {array.shape}")
        if feature_dim is None:
            feature_dim = int(array.shape[1])
        if array.shape[1] != feature_dim:
            raise ValueError("all sequences must share feature dimension")
        if not np.isfinite(array).all():
            raise ValueError("sequence contains NaN/Inf")
        arrays.append(array.astype(np.float32, copy=False))
    assert feature_dim is not None
    max_length = max(array.shape[0] for array in arrays)
    padded = np.zeros((len(arrays), max_length, feature_dim), dtype=np.float32)
    mask = np.zeros((len(arrays), max_length), dtype=bool)
    for row, array in enumerate(arrays):
        padded[row, : array.shape[0]] = array
        mask[row, : array.shape[0]] = True
    return (
        torch.as_tensor(padded, dtype=torch.float32, device=device),
        torch.as_tensor(mask, dtype=torch.bool, device=device),
    )


def _sinusoidal_positions(length: int, dimension: int, *, device: torch.device, dtype: torch.dtype) -> Tensor:
    position = torch.arange(length, device=device, dtype=dtype).unsqueeze(1)
    div = torch.exp(
        torch.arange(0, dimension, 2, device=device, dtype=dtype)
        * (-math.log(10000.0) / max(dimension, 1))
    )
    encoding = torch.zeros((length, dimension), device=device, dtype=dtype)
    encoding[:, 0::2] = torch.sin(position * div)
    if dimension > 1:
        encoding[:, 1::2] = torch.cos(position * div[: encoding[:, 1::2].shape[1]])
    return encoding


class A1AlignmentEncoder(nn.Module):
    """Small shared Transformer alignment encoder on top of A1 features."""

    def __init__(
        self,
        *,
        config: A1Config = DEFAULT_CONFIG,
        seed: int | None = None,
    ) -> None:
        config.__post_init__()
        if seed is not None and seed < 0:
            raise ValueError("seed must be non-negative")
        # Construction under fork_rng makes a requested initialization seed
        # reproducible without changing the caller's global RNG stream.
        with torch.random.fork_rng(devices=[]):
            if seed is not None:
                torch.manual_seed(seed)
            super().__init__()
            self.config = config
            self.input_projection = nn.Linear(config.feature_dim, config.d_model)
            layer = nn.TransformerEncoderLayer(
                d_model=config.d_model,
                nhead=config.encoder_heads,
                dim_feedforward=config.encoder_feedforward,
                dropout=0.0,
                activation="gelu",
                batch_first=True,
                norm_first=True,
            )
            self.encoder = nn.TransformerEncoder(
                layer,
                num_layers=config.encoder_layers,
                enable_nested_tensor=False,
            )
            self.output_norm = nn.LayerNorm(config.d_model)
            self.output_projection = nn.Linear(config.d_model, config.d_align)
        if self.parameter_count > config.max_encoder_params:
            raise ValueError(
                f"A1 alignment encoder has {self.parameter_count} parameters, "
                f"above the {config.max_encoder_params} limit"
            )

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def forward(self, padded: Tensor, mask: Tensor) -> Tensor:
        if padded.ndim != 3:
            raise ValueError(f"A1 input must be rank-3, got {tuple(padded.shape)}")
        if mask.ndim != 2 or mask.shape[:2] != padded.shape[:2]:
            raise ValueError("A1 mask must have shape (B,T_max)")
        if padded.dtype != torch.float32:
            raise TypeError("A1 input must be float32")
        if mask.dtype != torch.bool:
            raise TypeError("A1 mask must be bool")
        if padded.shape[-1] != self.config.feature_dim:
            raise ValueError(
                f"A1 feature dimension must be {self.config.feature_dim}, "
                f"got {padded.shape[-1]}"
            )
        if padded.shape[0] < 1 or padded.shape[1] < 1 or not bool(mask.any(dim=1).all()):
            raise ValueError("every A1 example must contain at least one valid unit")
        if not torch.isfinite(padded).all():
            raise ValueError("A1 input contains NaN/Inf")
        projected = self.input_projection(padded)
        projected = projected + _sinusoidal_positions(
            projected.shape[1],
            projected.shape[2],
            device=projected.device,
            dtype=projected.dtype,
        ).unsqueeze(0)
        encoded = self.encoder(projected, src_key_padding_mask=~mask)
        weights = mask.unsqueeze(-1).to(encoded.dtype)
        pooled = (encoded * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return self.output_projection(self.output_norm(pooled))


class A1Backbone(nn.Module):
    """Convenience wrapper exposing the frozen frontend and trainable encoder."""

    def __init__(
        self,
        *,
        config: A1Config = DEFAULT_CONFIG,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.encoder = A1AlignmentEncoder(config=config, seed=seed)

    @property
    def parameter_count(self) -> int:
        return self.encoder.parameter_count

    def forward(self, padded: Tensor, mask: Tensor) -> Tensor:
        return self.encoder(padded, mask)
