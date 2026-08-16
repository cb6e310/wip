from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backbones.a1_spectral import (  # noqa: E402
    A1AlignmentEncoder,
    A1ChannelMap,
    A1Config,
    DEFAULT_CONFIG,
    RobustFeatureNormalizer,
    analysis_spectrum_phase_rotation_features,
    bandpower_features,
    config_hash,
    extract_fixed_window_sequence,
    extract_word_level_sequence,
    pad_feature_sequences,
    run_metadata,
)


class A1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rng = np.random.default_rng(20260813)
        cls.epochs = [cls.rng.normal(size=(105, 512)).astype(np.float32) for _ in range(4)]

    def test_eight_band_feature_shape_and_determinism(self) -> None:
        self.assertEqual(DEFAULT_CONFIG.d_align, 384)
        self.assertEqual(
            [(band.low_hz, band.high_hz) for band in DEFAULT_CONFIG.bands],
            [
                (4.0, 6.0),
                (6.5, 8.0),
                (8.5, 10.0),
                (10.5, 13.0),
                (13.5, 18.0),
                (18.5, 30.0),
                (30.5, 40.0),
                (40.0, 49.5),
            ],
        )
        first = bandpower_features(self.epochs[0])
        second = bandpower_features(self.epochs[0].T)
        self.assertEqual(first.shape, (840,))
        self.assertEqual(first.dtype, np.float32)
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.isfinite(first).all())

    def test_feature_order_is_channel_major(self) -> None:
        # A pure 10 Hz tone on channel 1 should occupy channel 1's eight-slot
        # block; this guards the flatten order recorded in A1Config.
        time = np.arange(512, dtype=np.float64) / DEFAULT_CONFIG.sampling_rate_hz
        epoch = np.zeros((DEFAULT_CONFIG.n_channels, time.size), dtype=np.float32)
        epoch[1] = np.sin(2.0 * np.pi * 10.0 * time).astype(np.float32)
        features = bandpower_features(epoch)
        self.assertGreater(float(features[1 * 8 + 2]), float(features[2]))
        self.assertLess(float(features[2]), float(features[1 * 8 + 2]))

    def test_any_nonfinite_is_rejected_without_imputation(self) -> None:
        self.assertEqual(DEFAULT_CONFIG.finite_policy, "reject_any_nonfinite_no_imputation")
        for value in (np.nan, np.inf, -np.inf):
            epoch = self.epochs[0].copy()
            epoch[0, 0] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "forbids imputation"):
                bandpower_features(epoch)

    def test_analysis_spectrum_phase_rotation_is_invariant(self) -> None:
        original = bandpower_features(self.epochs[0])
        rotated = analysis_spectrum_phase_rotation_features(self.epochs[0], seed=20260813)
        np.testing.assert_allclose(rotated, original, rtol=1e-5, atol=1e-7)

    def test_both_segmentation_versions_have_same_feature_contract(self) -> None:
        words = extract_word_level_sequence(self.epochs)
        continuous = np.concatenate(self.epochs, axis=1)
        fixed = extract_fixed_window_sequence(continuous)
        self.assertEqual(words.ndim, 2)
        self.assertEqual(fixed.ndim, 2)
        self.assertEqual(words.shape[1], DEFAULT_CONFIG.feature_dim)
        self.assertEqual(fixed.shape[1], DEFAULT_CONFIG.feature_dim)
        self.assertGreaterEqual(fixed.shape[0], 1)

    def test_fixed_window_requires_explicit_mapping_for_128_channel_input(self) -> None:
        direct_sentence_raw = self.rng.normal(size=(105, 600)).astype(np.float32)
        direct = extract_fixed_window_sequence(direct_sentence_raw)
        self.assertEqual(direct.shape[1], DEFAULT_CONFIG.feature_dim)
        raw = self.rng.normal(size=(128, 600)).astype(np.float32)
        with self.assertRaises(ValueError):
            extract_fixed_window_sequence(raw)
        channel_map = A1ChannelMap(
            source_labels=tuple(f"S{index:03d}" for index in range(128)),
            target_labels=tuple(f"T{index:03d}" for index in range(105)),
            source_indices=tuple(range(105)),
            provenance="synthetic-contract-only; not a ZuCo mapping",
            coverage=1.0,
        )
        mapped = extract_fixed_window_sequence(raw, channel_map=channel_map)
        self.assertEqual(mapped.shape[1], DEFAULT_CONFIG.feature_dim)

    def test_normalizer_is_fold_local_and_transform_is_finite(self) -> None:
        sequences = [
            np.stack([bandpower_features(epoch) for epoch in self.epochs[:2]]),
            np.stack([bandpower_features(epoch) for epoch in self.epochs[2:]]),
        ]
        normalizer = RobustFeatureNormalizer().fit(sequences[:1])
        transformed = normalizer.transform(sequences[1])
        self.assertEqual(transformed.dtype, np.float32)
        self.assertTrue(np.isfinite(transformed).all())
        self.assertGreaterEqual(float(normalizer.iqr.min()), 1e-6)  # type: ignore[union-attr]
        with self.assertRaises(RuntimeError):
            RobustFeatureNormalizer().transform(sequences[1])

    def test_padding_and_encoder_tensor_contract(self) -> None:
        sequences = [
            np.zeros((2, DEFAULT_CONFIG.feature_dim), dtype=np.float32),
            np.ones((4, DEFAULT_CONFIG.feature_dim), dtype=np.float32),
        ]
        padded, mask = pad_feature_sequences(sequences)
        self.assertEqual(tuple(padded.shape), (2, 4, 840))
        self.assertEqual(tuple(mask.shape), (2, 4))
        self.assertEqual(mask.dtype, torch.bool)
        self.assertEqual(padded.dtype, torch.float32)
        encoder = A1AlignmentEncoder(seed=17)
        self.assertLessEqual(encoder.parameter_count, DEFAULT_CONFIG.max_encoder_params)
        output = encoder(padded, mask)
        self.assertEqual(tuple(output.shape), (2, 384))
        self.assertTrue(torch.isfinite(output).all())
        with self.assertRaises(TypeError):
            encoder(padded.double(), mask)
        with self.assertRaises(TypeError):
            encoder(padded, mask.to(torch.int64))

    def test_forbidden_length_is_not_encoded_and_metadata_is_traceable(self) -> None:
        self.assertNotIn("sequence_length", DEFAULT_CONFIG.to_dict())
        self.assertNotIn("unit_count", DEFAULT_CONFIG.to_dict())
        self.assertNotIn("eye", DEFAULT_CONFIG.to_dict())
        self.assertEqual(len(config_hash()), 64)
        metadata = run_metadata(seed=123, fold="S0-T0", method="A1")
        self.assertEqual(metadata["seed"], 123)
        self.assertEqual(metadata["fold"], "S0-T0")
        self.assertEqual(metadata["method"], "A1")
        self.assertEqual(len(metadata["config_hash"]), 64)


if __name__ == "__main__":
    unittest.main()
