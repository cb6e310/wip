import unittest

import numpy as np

try:
    from backbones.a3_labram import (
        A3ChannelMap,
        A3Config,
        extract_pooled_embeddings,
        preprocess_raw_signal,
        synthetic_contract_map,
        window_signal,
    )
except ModuleNotFoundError:
    from a3_labram import (
        A3ChannelMap,
        A3Config,
        extract_pooled_embeddings,
        preprocess_raw_signal,
        synthetic_contract_map,
        window_signal,
    )


class A3ContractTest(unittest.TestCase):
    def test_frozen_window_contract(self):
        config = A3Config()
        self.assertEqual(config.window_samples, 1000)
        self.assertEqual(config.stride_samples, 500)
        self.assertEqual(config.n_patches, 5)
        signal = np.zeros((128, 1500), dtype=np.float32)
        windows = window_signal(signal, config)
        self.assertEqual(windows.shape, (2, 128, 1000))

    def test_short_signal_is_empty_without_padding(self):
        windows = window_signal(np.zeros((128, 999), dtype=np.float32))
        self.assertEqual(windows.shape, (0, 128, 1000))

    def test_unverified_map_blocks_extraction(self):
        class NeverCalled:
            def __call__(self, *_args, **_kwargs):
                raise AssertionError("model must not run with an unverified map")

        windows = np.zeros((1, 128, 1000), dtype=np.float32)
        with self.assertRaisesRegex(RuntimeError, "not verified"):
            extract_pooled_embeddings(NeverCalled(), windows, synthetic_contract_map())

    def test_raw_preprocessing_contract(self):
        with self.assertRaisesRegex(RuntimeError, "not frozen"):
            preprocess_raw_signal(np.zeros((128, 5000), dtype=np.float32))
        config = A3Config(filter_order=4, notch_q=30.0)
        raw = np.zeros((128, 5000), dtype=np.float32)
        processed = preprocess_raw_signal(raw, config)
        self.assertEqual(processed.shape, (128, 2000))
        self.assertTrue(np.isfinite(processed).all())

    def test_channel_map_requires_permutations(self):
        labels = tuple(f"E{i}" for i in range(1, 129))
        with self.assertRaisesRegex(ValueError, "permutation"):
            A3ChannelMap(labels, labels, (0,) * 128, tuple(range(129)), "test", 1.0, True)

    def test_verified_map_uses_release_pooling_call(self):
        labels = tuple(f"E{i}" for i in range(1, 129))
        channel_map = A3ChannelMap(
            labels,
            labels,
            tuple(reversed(range(128))),
            tuple(range(129)),
            "approved test permutation",
            1.0,
            True,
        )

        class FakeModel:
            def __init__(self):
                self.seen = None

            def __call__(self, tensor, **kwargs):
                self.seen = (tensor.detach().numpy().copy(), kwargs)
                return __import__("torch").zeros((tensor.shape[0], 200))

        model = FakeModel()
        windows = np.zeros((1, 128, 1000), dtype=np.float32)
        windows[:, 0, :] = 1.0
        output = extract_pooled_embeddings(model, windows, channel_map)
        self.assertEqual(output.shape, (1, 200))
        self.assertFalse(model.seen[1]["return_patch_tokens"])
        self.assertEqual(float(model.seen[0][0, -1, 0, 0]), 1.0)


if __name__ == "__main__":
    unittest.main()
