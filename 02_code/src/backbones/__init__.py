"""Frozen EEG feature frontends and alignment backbones."""

from .a1_spectral import (
    A1AlignmentEncoder,
    A1Backbone,
    A1ChannelMap,
    A1Config,
    BandDefinition,
    RobustFeatureNormalizer,
    bandpower_features,
    config_hash,
    extract_fixed_window_sequence,
    extract_word_level_sequence,
    pad_feature_sequences,
)
from .a3_labram import (
    A3ChannelMap,
    A3Config,
    checkpoint_sha256,
    config_hash as a3_config_hash,
    extract_pooled_embeddings,
    load_labram_base,
    preprocess_raw_signal,
    window_signal,
)

__all__ = [
    "A1AlignmentEncoder",
    "A1Backbone",
    "A1ChannelMap",
    "A1Config",
    "BandDefinition",
    "RobustFeatureNormalizer",
    "bandpower_features",
    "config_hash",
    "extract_fixed_window_sequence",
    "extract_word_level_sequence",
    "pad_feature_sequences",
    "A3ChannelMap",
    "A3Config",
    "a3_config_hash",
    "checkpoint_sha256",
    "extract_pooled_embeddings",
    "load_labram_base",
    "preprocess_raw_signal",
    "window_signal",
]
