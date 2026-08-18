from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data.eq_anma_synthetic_benchmark import (  # noqa: E402
    ITEM_SPLITS,
    SUBJECT_SPLITS,
    alpha_zero_byte_equality,
    assert_split_isolation,
    build_replicate,
    build_synthetic_v5_ledger,
    candidate_sets,
    canonical_bytes,
    flatten_partition,
    generate_scenario,
)


def test_generator_determinism_and_alpha_zero_byte_equality() -> None:
    first = build_replicate(20260813)
    second = build_replicate(20260813)
    assert canonical_bytes(first.base_noise) == canonical_bytes(second.base_noise)
    equal, structured_hash, monotone_hash = alpha_zero_byte_equality(first)
    assert equal
    assert structured_hash == monotone_hash


def test_split_isolation_shape_and_two_by_two_item_balance() -> None:
    assert_split_isolation()
    base = build_replicate(20260814)
    scenario = generate_scenario(base, "STRUCTURED_FISHER", 0.3)
    assert scenario.item_features.shape == (30, 120, 4, 840)
    assert scenario.sentence_features.shape == (30, 120, 840)
    assert scenario.sentence_text_targets.shape == (30, 120, 384)
    for subject in range(30):
        folds = base.item_folds[base.sentence_items[subject]]
        assert np.all(folds.sum(axis=1) == 2)
    train = flatten_partition(scenario, "train")
    assert set(train["item_subjects"]) == set(SUBJECT_SPLITS["train"])
    assert set(train["item_indices"]).issubset(ITEM_SPLITS["train"])


def test_candidates_are_deterministic_target_present_and_n10() -> None:
    first = candidate_sets(20260813, "selection")
    second = candidate_sets(20260813, "selection")
    assert np.array_equal(first, second)
    assert first.shape == (720, 10)
    assert all(index in row for index, row in enumerate(first))
    assert all(len(set(row.tolist())) == 10 for row in first)


def test_synthetic_v5_adversarial_scopes() -> None:
    row = build_synthetic_v5_ledger(
        fit_id="fit-1",
        scenario_id="scenario-1",
        fit_ids=["train-a", "train-b"],
        selection_ids=["selection-a"],
        final_test_ids=[],
        generator_hash="a" * 64,
        scope="ridge|real",
    )
    assert row["v5_pass"]
    with pytest.raises(ValueError, match="overlap"):
        build_synthetic_v5_ledger(
            fit_id="bad",
            scenario_id="scenario-1",
            fit_ids=["same"],
            selection_ids=["same"],
            generator_hash="a" * 64,
            scope="ridge|bad",
        )


def test_truth_is_separate_from_fitted_payload() -> None:
    base = build_replicate(20260815)
    scenario = generate_scenario(base, "MONOTONE_DIRECT", 1.0)
    payload = flatten_partition(scenario, "train")
    forbidden = {"a", "b", "q", "information", "stable_mask", "sign"}
    assert forbidden.isdisjoint(payload)
