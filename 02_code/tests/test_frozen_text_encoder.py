from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from text.frozen_minilm import (  # noqa: E402
    DEFAULT_CONFIG,
    MODEL_ID,
    MAX_SEQ_LENGTH,
    OUTPUT_DIM,
    POOLING,
    REVISION,
    FrozenMiniLMEncoder,
    build_cache_key,
    encode,
    mean_pooling,
)


TOKENIZER_MANIFEST_HASH = "1" * 64
ENCODER_CONFIG_MANIFEST_HASH = "2" * 64
SCIENTIFIC_CONFIG_HASH = DEFAULT_CONFIG.scientific_config_hash


class StubTokenizer:
    def __init__(self, model_max_length: int = 512) -> None:
        self.model_max_length = model_max_length

    @staticmethod
    def _ids(text: str) -> list[int]:
        return [1] + [3 + (ord(character) % 61) for character in text] + [2]

    def __call__(
        self,
        texts: str | list[str],
        *,
        add_special_tokens: bool,
        truncation: bool,
        padding: bool,
        return_attention_mask: bool,
        max_length: int | None = None,
        return_tensors: str | None = None,
    ) -> dict[str, object]:
        del add_special_tokens
        rows = [self._ids(texts)] if isinstance(texts, str) else [self._ids(text) for text in texts]
        if truncation:
            if max_length is None:
                raise AssertionError("max_length is required when truncating")
            rows = [row[:max_length] for row in rows]
        if padding:
            width = max(len(row) for row in rows)
            masks = [[1] * len(row) + [0] * (width - len(row)) for row in rows]
            rows = [row + [0] * (width - len(row)) for row in rows]
        else:
            masks = [[1] * len(row) for row in rows]
        if return_tensors == "pt":
            result: dict[str, object] = {"input_ids": torch.tensor(rows, dtype=torch.long)}
            if return_attention_mask:
                result["attention_mask"] = torch.tensor(masks, dtype=torch.long)
            return result
        result = {"input_ids": rows[0] if isinstance(texts, str) else rows}
        if return_attention_mask:
            result["attention_mask"] = masks[0] if isinstance(texts, str) else masks
        return result


class StubModel(nn.Module):
    def __init__(self, max_position_embeddings: int = 512) -> None:
        super().__init__()
        self.config = SimpleNamespace(
            hidden_size=OUTPUT_DIM,
            max_position_embeddings=max_position_embeddings,
        )
        self.embedding = nn.Embedding(64, OUTPUT_DIM)
        with torch.no_grad():
            values = torch.arange(64 * OUTPUT_DIM, dtype=torch.float32).reshape(64, OUTPUT_DIM)
            self.embedding.weight.copy_((values.remainder(97) - 48.0) / 97.0)

    def forward(self, *, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> SimpleNamespace:
        del attention_mask
        return SimpleNamespace(last_hidden_state=self.embedding(input_ids))


class FrozenTextEncoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tokenizer = StubTokenizer()
        self.model = StubModel()
        self.encoder = FrozenMiniLMEncoder(
            tokenizer=self.tokenizer,
            model=self.model,
            tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
            encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
        )

    def test_attention_mask_mean_pooling_numeric(self) -> None:
        hidden = torch.tensor([[[3.0, 0.0], [0.0, 4.0], [99.0, 99.0]]])
        output = mean_pooling(hidden, torch.tensor([[1, 1, 0]]))
        expected = torch.tensor([[0.6, 0.8]], dtype=torch.float32)
        torch.testing.assert_close(output, expected)

    def test_padding_content_does_not_change_pooling(self) -> None:
        mask = torch.tensor([[1, 1, 0]])
        first = torch.tensor([[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]])
        second = first.clone()
        second[:, 2] = torch.tensor([-1000.0, 1000.0])
        torch.testing.assert_close(mean_pooling(first, mask), mean_pooling(second, mask))

    def test_all_padding_is_finite_not_nan(self) -> None:
        output = mean_pooling(torch.randn(2, 3, 7), torch.zeros(2, 3, dtype=torch.long))
        self.assertTrue(torch.isfinite(output).all())
        torch.testing.assert_close(output, torch.zeros_like(output))

    def test_encode_contract_float32_384_finite_l2(self) -> None:
        result = encode(["alpha", "b"], encoder=self.encoder)
        self.assertEqual(tuple(result.embeddings.shape), (2, 384))
        self.assertEqual(result.embeddings.dtype, torch.float32)
        self.assertTrue(torch.isfinite(result.embeddings).all())
        torch.testing.assert_close(
            torch.linalg.vector_norm(result.embeddings, dim=1),
            torch.ones(2),
            atol=1e-6,
            rtol=1e-6,
        )

    def test_cache_key_is_stable(self) -> None:
        first = build_cache_key(
            "exact text",
            tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
            encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
        )
        second = build_cache_key(
            "exact text",
            tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
            encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_cache_key_changes_with_text_and_tokenizer_hash(self) -> None:
        baseline = self._cache_key("exact text")
        self.assertNotEqual(baseline, self._cache_key("exact text "))
        self.assertNotEqual(
            baseline,
            build_cache_key(
                "exact text",
                tokenizer_manifest_hash="3" * 64,
                encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
                scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
            ),
        )

    def test_cache_key_changes_with_revision_pooling_and_config_hash(self) -> None:
        baseline = self._cache_key("x")
        self.assertNotEqual(
            baseline,
            self._cache_key("x", revision=REVISION + "-changed"),
        )
        self.assertNotEqual(
            baseline,
            self._cache_key("x", pooling=POOLING + "-changed"),
        )
        self.assertNotEqual(
            baseline,
            build_cache_key(
                "x",
                tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
                scientific_config_hash="4" * 64,
            ),
        )

    def test_cache_key_changes_with_encoder_config_manifest_hash(self) -> None:
        baseline = self._cache_key("x")
        changed = build_cache_key(
            "x",
            tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
            encoder_config_manifest_hash="5" * 64,
            scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
        )
        self.assertNotEqual(baseline, changed)

    def test_missing_or_invalid_manifest_hash_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            build_cache_key(  # type: ignore[call-arg]
                "x",
                tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
            )
        for bad_hash in ("", "z" * 64, "1" * 63):
            with self.assertRaises(ValueError):
                FrozenMiniLMEncoder(
                    tokenizer=StubTokenizer(),
                    model=StubModel(),
                    tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                    encoder_config_manifest_hash=bad_hash,
                )

    def test_exact_model_constants_are_frozen(self) -> None:
        self.assertEqual(MODEL_ID, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(REVISION, "1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
        self.assertEqual(OUTPUT_DIM, 384)
        self.assertEqual(MAX_SEQ_LENGTH, 256)
        self.assertEqual(DEFAULT_CONFIG.max_seq_length, 256)
        self.assertEqual(self.encoder.model_max_length, 256)

    def test_model_is_eval_and_all_parameters_are_frozen(self) -> None:
        self.assertFalse(self.encoder.model.training)
        self.assertGreater(self.encoder.total_parameter_count, 0)
        self.assertEqual(self.encoder.trainable_parameter_count, 0)
        self.assertTrue(all(not parameter.requires_grad for parameter in self.encoder.model.parameters()))

    def test_encode_is_no_grad_and_deterministic(self) -> None:
        first = self.encoder.encode("same input").embeddings
        second = self.encoder.encode("same input").embeddings
        self.assertFalse(first.requires_grad)
        self.assertTrue(torch.equal(first, second))

    def test_empty_string_single_and_batch_have_explicit_behavior(self) -> None:
        empty = self.encoder.encode("")
        single = self.encoder.encode("one")
        batch = self.encoder.encode(["one", "two"])
        self.assertEqual(tuple(empty.embeddings.shape), (1, 384))
        self.assertEqual(tuple(single.embeddings.shape), (1, 384))
        self.assertEqual(tuple(batch.embeddings.shape), (2, 384))

    def test_truncation_counts_and_flags(self) -> None:
        result = self.encoder.encode("x" * 300)
        record = result.records[0]
        self.assertTrue(record.truncated)
        self.assertGreater(record.token_count_before_truncation, record.token_count_after_truncation)
        self.assertEqual(record.token_count_after_truncation, 256)
        self.assertEqual(result.model_max_length, 256)

    def test_short_input_is_not_marked_truncated(self) -> None:
        record = self.encoder.encode("a").records[0]
        self.assertFalse(record.truncated)
        self.assertEqual(record.token_count_before_truncation, record.token_count_after_truncation)

    def test_empty_batch_and_non_string_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.encoder.encode([])
        with self.assertRaises(TypeError):
            self.encoder.encode(["ok", 3])  # type: ignore[list-item]

    def test_unit_path_does_not_call_huggingface_network_loaders(self) -> None:
        with patch("transformers.AutoTokenizer.from_pretrained") as tokenizer_loader, patch(
            "transformers.AutoModel.from_pretrained"
        ) as model_loader:
            encoder = FrozenMiniLMEncoder(
                tokenizer=StubTokenizer(),
                model=StubModel(),
                tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            )
            encoder.encode("offline")
            tokenizer_loader.assert_not_called()
            model_loader.assert_not_called()

    def test_tokenizer_capacity_below_256_hard_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "tokenizer.model_max_length"):
            FrozenMiniLMEncoder(
                tokenizer=StubTokenizer(model_max_length=255),
                model=StubModel(),
                tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            )

    def test_model_capacity_below_256_hard_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_position_embeddings"):
            FrozenMiniLMEncoder(
                tokenizer=StubTokenizer(),
                model=StubModel(max_position_embeddings=255),
                tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
                encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            )

    @staticmethod
    def _cache_key(text: str, **overrides: str) -> str:
        return build_cache_key(
            text,
            tokenizer_manifest_hash=TOKENIZER_MANIFEST_HASH,
            encoder_config_manifest_hash=ENCODER_CONFIG_MANIFEST_HASH,
            scientific_config_hash=SCIENTIFIC_CONFIG_HASH,
            **overrides,
        )


if __name__ == "__main__":
    unittest.main()
    DEFAULT_CONFIG,
