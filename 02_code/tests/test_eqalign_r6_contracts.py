"""T-01 through T-09 synthetic/adversarial R6 contract checks."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile

import torch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code" / "src"))

from eqalign_r6.arms import (
    ARM_IDS,
    base_arm,
    direct_arm,
    direct_matched_arm,
    eq_anma_arm,
    eq_shuffle_arm,
    r6_direct_variant_ids,
)
from eqalign_r6.contracts import PRIMARY_METRIC, R6ProtocolConfig
from eqalign_r6.controller import (
    bounded_weights,
    fit_sentence_score_stats,
    sentence_fisher_score,
    shuffle_h_within_subject_trial,
    standardize_and_clip,
)
from eqalign_r6.ledger import (
    ComputeCounters,
    ReadCounters,
    assert_compute_matched,
    batch_index_sequence_hash,
    canonical_artifact_sha256,
    independent_rng_stream_id,
    physical_sha256,
    validate_ledger_budget,
    validate_ledger_row,
)
from eqalign_r6.scope import (
    ScopeLedger,
    assert_controller_fit_ids,
    assert_feature_role,
    primary_metric_from_freeze,
)


def _raises(exception_type, function, *args, **kwargs) -> None:
    try:
        function(*args, **kwargs)
    except exception_type:
        return
    raise AssertionError(f"expected {exception_type.__name__}")


def _counters() -> ComputeCounters:
    return ComputeCounters(
        C_step="steps=4|forward=4|backward=4|epochs=1",
        C_data="batch=2|examples=4|seeds=3|order=frozen",
        C_model="encoder=17|text=frozen:abc|pool=frozen:def",
        C_lr="mean_weight=1.000000",
    )


def _arms() -> dict[str, object]:
    counters = _counters()
    h = torch.tensor([-3.0, -0.5, 0.5, 3.0], dtype=torch.float64)
    fit_ids = ("fit-a", "fit-b")
    groups = [("cell", "task", "s1")] * 2 + [("cell", "task", "s2")] * 2
    scores = torch.tensor([[0.2, 0.0], [0.8, 0.1], [0.4, 0.0], [1.2, 0.2]], dtype=torch.float64)
    mask = torch.ones_like(scores, dtype=torch.bool)
    direct_score = torch.tensor([0.2, 0.8, 0.4, 1.2], dtype=torch.float64)
    fit_mask = torch.tensor([True, True, False, False])
    results = [
        base_arm(4, counters),
        direct_arm(scores, mask, gamma=1.0, score_version="u_oof", warmup="none", fit_ids=fit_ids, counters=counters),
        eq_anma_arm(h, 0.5, fit_ids, counters),
        eq_shuffle_arm(h, 0.5, groups, 17, fit_ids, counters),
        direct_matched_arm(direct_score, fit_mask, 0.5, fit_ids, counters),
    ]
    return {result.arm_id: result for result in results}


def test_t01_gamma_zero_exact_base_nesting() -> None:
    h = torch.tensor([-3.0, -0.1, 0.0, 2.5, 3.0], dtype=torch.float64, requires_grad=True)
    counters = _counters()
    base = base_arm(h.numel(), counters)
    eq = eq_anma_arm(h, 0.0, ("fit",), counters)
    assert torch.equal(eq.raw_weight, base.raw_weight)
    assert torch.equal(eq.normalized_weight, base.normalized_weight)
    assert not eq.raw_weight.requires_grad and not eq.normalized_weight.requires_grad


def test_t02_controller_rng_is_independent() -> None:
    h = torch.arange(8, dtype=torch.float64)
    groups = [("c", "t", "s")] * 8
    torch.manual_seed(991)
    before = torch.random.get_rng_state().clone()
    first = shuffle_h_within_subject_trial(h, groups, 41)
    after = torch.random.get_rng_state().clone()
    second = shuffle_h_within_subject_trial(h, groups, 41)
    assert torch.equal(before, after)
    assert torch.equal(first, second)
    assert independent_rng_stream_id("shuffle", 41) != independent_rng_stream_id("training", 41)


def test_t03_fit_ids_are_the_only_allowed_controller_set_adversarial() -> None:
    fit_ids = {"fit-1", "fit-2"}
    assert_controller_fit_ids(["fit-1"], fit_ids)
    _raises(ValueError, assert_controller_fit_ids, ["fit-1", "held-out-injection"], fit_ids)
    ledger = ScopeLedger(fit_record_ids=frozenset(fit_ids))
    _raises(ValueError, ledger.assert_controller_fit, ["outer-subject-record"])


def test_t04_shuffle_marginal_axis_and_three_seeds_adversarial() -> None:
    config = R6ProtocolConfig()
    assert config.shuffle_realizations == 3
    assert config.shuffle_axis == "within_outer_cell_task_subject_across_trials"
    h = torch.tensor([-3.0, -1.0, 0.0, 2.0, -2.0, 1.0, 2.5, 3.0])
    groups = [("c1", "t1", "s1")] * 4 + [("c1", "t1", "s2")] * 4
    for seed in (11, 23, 37):
        shuffled = shuffle_h_within_subject_trial(h, groups, seed)
        assert torch.equal(torch.sort(shuffled).values, torch.sort(h).values)
        assert torch.equal(torch.sort(shuffled[:4]).values, torch.sort(h[:4]).values)
        assert torch.equal(torch.sort(shuffled[4:]).values, torch.sort(h[4:]).values)
        assert torch.equal(shuffled.mean(), h.mean())
        assert torch.equal(shuffled.var(unbiased=False), h.var(unbiased=False))
        assert float(shuffled.min()) >= -3.0 and float(shuffled.max()) <= 3.0
    _raises(ValueError, shuffle_h_within_subject_trial, h, ["subject-only"] * 8, 11)


def test_t05_five_arm_compute_and_batch_equality() -> None:
    arms = _arms()
    assert set(arms) == set(ARM_IDS)
    batch_hash = batch_index_sequence_hash([[0, 1], [2, 3]])
    assert_compute_matched(
        {name: arm.compute_counters for name, arm in arms.items()},
        {name: arm.data_examples_seen for name, arm in arms.items()},
        {name: batch_hash for name in arms},
    )
    mismatched = {name: arm.compute_counters for name, arm in arms.items()}
    mismatched["DIRECT"] = ComputeCounters("different", "same", "same", "same")
    _raises(
        ValueError,
        assert_compute_matched,
        mismatched,
        {name: arm.data_examples_seen for name, arm in arms.items()},
        {name: batch_hash for name in arms},
    )


def test_t06_zero_reads_and_frozen_primary_metric() -> None:
    reads = ReadCounters()
    reads.validate()
    scope = ScopeLedger(fit_record_ids=frozenset({"fit"}))
    scope.assert_pre_outer()
    _raises(ValueError, scope.record_outer_read, "cell", "task", purpose="selection")
    assert primary_metric_from_freeze(R6ProtocolConfig()) == PRIMARY_METRIC
    _raises(ValueError, primary_metric_from_freeze, R6ProtocolConfig(primary_metric="mrr_at_10"))


def test_t07_behavior_and_identifier_injection_are_rejected() -> None:
    assert_feature_role("behavior", "controller_input")
    for role in ("eeg_encoder", "text_encoder", "candidate", "split", "eligibility"):
        _raises(ValueError, assert_feature_role, "behavior", role)
        _raises(ValueError, assert_feature_role, "subject_id", role)
        _raises(ValueError, assert_feature_role, "item_id", role)


def test_t08_bounds_normalization_stop_gradient_and_examples() -> None:
    h = torch.tensor([-3.0, -2.0, 0.0, 2.0, 3.0], requires_grad=True)
    result = bounded_weights(h, 1.0)
    assert float(result.raw_weight.min()) >= 0.2
    assert float(result.raw_weight.max()) <= 3.0
    assert torch.isclose(result.normalized_weight.mean(), torch.tensor(1.0), atol=1e-6)
    assert not result.raw_weight.requires_grad and not result.normalized_weight.requires_grad
    arms = _arms()
    assert {arm.data_examples_seen for arm in arms.values()} == {4}
    for arm in arms.values():
        assert torch.isclose(arm.normalized_weight.mean(), torch.tensor(1.0, dtype=arm.normalized_weight.dtype), atol=1e-6)
    information = torch.tensor([[1.0, 3.0], [9.0, 9.0]])
    mask = torch.tensor([[True, True], [False, False]])
    assert torch.equal(sentence_fisher_score(information, mask), torch.tensor([2.0, 0.0]))


def test_t09_hash_schema_read_counters_and_budget() -> None:
    payload = {"b": 2, "a": [1, 3]}
    assert canonical_artifact_sha256(payload) == canonical_artifact_sha256({"a": [1, 3], "b": 2})
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "artifact.bin"
        path.write_bytes(b"r6-synthetic-artifact")
        assert physical_sha256(path) == hashlib.sha256(b"r6-synthetic-artifact").hexdigest()
    token = hashlib.sha256(b"fit-record").hexdigest()
    artifact_hash = hashlib.sha256(b"weights").hexdigest()
    config_hash = R6ProtocolConfig().canonical_sha256()
    row = {
        "arm_id": "EQ_ANMA",
        "variant_id": "eq|gamma=0.5",
        "controller_fit_record_ids": [token],
        "weight_artifact_sha256": artifact_hash,
        "config_hash": config_hash,
    }
    validate_ledger_row(row)
    validate_ledger_budget([row], maximum_rows=1)
    _raises(ValueError, validate_ledger_row, {**row, "subject_id": "injected"})
    _raises(ValueError, validate_ledger_budget, [row, row], maximum_rows=1)
    bad_reads = ReadCounters(controller_reads_outer=True)
    _raises(ValueError, bad_reads.validate)
    assert len(r6_direct_variant_ids()) == 8
    assert len(set(r6_direct_variant_ids())) == 8
    assert all("gated" not in variant for variant in r6_direct_variant_ids())


CORE_TESTS = (
    test_t01_gamma_zero_exact_base_nesting,
    test_t02_controller_rng_is_independent,
    test_t03_fit_ids_are_the_only_allowed_controller_set_adversarial,
    test_t04_shuffle_marginal_axis_and_three_seeds_adversarial,
    test_t05_five_arm_compute_and_batch_equality,
    test_t06_zero_reads_and_frozen_primary_metric,
    test_t07_behavior_and_identifier_injection_are_rejected,
    test_t08_bounds_normalization_stop_gradient_and_examples,
    test_t09_hash_schema_read_counters_and_budget,
)


def run_all_contract_checks() -> None:
    for test in CORE_TESTS:
        test()
