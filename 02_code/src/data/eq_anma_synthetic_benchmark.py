"""Frozen v3.20 EQ-ANMA synthetic benchmark generator and contracts.

This module is synthetic-only.  It contains no path, loader, or API capable of
reading real EEG or real outer-test artifacts.  Generator truth is carried in
a separate ``ScenarioTruth`` object that fitted-method functions do not accept.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from data.a1_admission import stable_seed
from data.a1_measurement_validity import projection_matrix


REPLICATE_SEEDS = tuple(range(20260813, 20260825))
REGIMES = ("STRUCTURED_FISHER", "MONOTONE_DIRECT")
ALPHAS = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)
SUBJECT_SPLITS = {"train": tuple(range(18)), "selection": tuple(range(18, 24)), "final_test": tuple(range(24, 30))}
ITEM_SPLITS = {"train": tuple(range(72)), "selection": tuple(range(72, 96)), "final_test": tuple(range(96, 120))}
FEATURE_DIM = 840
TEXT_DIM = 384
SENTENCES_PER_SUBJECT = 120
ITEMS_PER_SENTENCE = 4
CANDIDATE_N = 10
PROJECTION_SHA256 = "dba2ad5e50eb0379a9d5dec29dc3c1af0138d4a36871012d1ee8ffba9e8dba58"


def _unit_rows(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    norm = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norm <= 0):
        raise ValueError("cannot normalize a zero row")
    return (array / norm).astype("<f4")


def _unit_vector(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    norm = float(np.linalg.norm(array))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("cannot normalize a zero vector")
    return (array / norm).astype("<f4")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def canonical_bytes(values: np.ndarray) -> bytes:
    array = np.ascontiguousarray(np.asarray(values, dtype="<f4"))
    return array.tobytes(order="C")


def sha256_bytes(values: bytes) -> str:
    return hashlib.sha256(values).hexdigest()


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(payload)


def _hash_fold(seed: int, role: str, index: int) -> int:
    return int(stable_seed(seed, "v3.20", role, index) % 2)


@dataclass(frozen=True)
class ReplicateBase:
    seed: int
    text_embeddings: np.ndarray
    semantic_directions: np.ndarray
    d_q: np.ndarray
    a: np.ndarray
    b: np.ndarray
    q: np.ndarray
    p: np.ndarray
    information: np.ndarray
    stable_mask: np.ndarray
    structured_sign: np.ndarray
    sentence_items: np.ndarray
    item_folds: np.ndarray
    subject_folds: np.ndarray
    base_noise: np.ndarray
    projection_metadata: Mapping[str, Any]


@dataclass(frozen=True)
class ScenarioTruth:
    a: np.ndarray
    b: np.ndarray
    q: np.ndarray
    information_by_observation: np.ndarray
    oracle_sentence_budget: np.ndarray
    stable_mask: np.ndarray
    sign_by_observation: np.ndarray


@dataclass(frozen=True)
class SyntheticScenario:
    replicate_seed: int
    regime: str
    alpha: float
    item_features: np.ndarray
    sentence_features: np.ndarray
    sentence_text_targets: np.ndarray
    sentence_items: np.ndarray
    item_text_embeddings: np.ndarray
    subject_folds: np.ndarray
    item_folds: np.ndarray
    feature_sha256: str
    truth: ScenarioTruth

    @property
    def scenario_id(self) -> str:
        return f"seed={self.replicate_seed}|regime={self.regime}|alpha={self.alpha:g}"


def _split_for_subject(subject: int) -> str:
    for name, values in SUBJECT_SPLITS.items():
        if subject in values:
            return name
    raise KeyError(subject)


def build_replicate(seed: int) -> ReplicateBase:
    if seed not in REPLICATE_SEEDS:
        raise ValueError("replicate seed is outside the frozen grid")
    text_rng = np.random.default_rng(stable_seed(seed, "v3.20", "text_embeddings", "all"))
    text = _unit_rows(text_rng.standard_normal((120, TEXT_DIM)))
    projection, projection_metadata = projection_matrix()
    if projection_metadata["c_order_sha256"] != PROJECTION_SHA256:
        raise RuntimeError("frozen v3.17 projection hash mismatch")
    semantic = _unit_rows((projection @ text.T).T)

    va = _unit_vector(np.random.default_rng(stable_seed(seed, "v3.20", "v_a", "all")).standard_normal(TEXT_DIM))
    vb = _unit_vector(np.random.default_rng(stable_seed(seed, "v3.20", "v_b", "all")).standard_normal(TEXT_DIM))
    a = (0.5 + 1.5 * _sigmoid(text.astype(np.float64) @ va.astype(np.float64))).astype("<f4")
    raw_b = text.astype(np.float64) @ vb.astype(np.float64)
    train_b = raw_b[np.asarray(ITEM_SPLITS["train"])]
    b = np.clip((raw_b - train_b.mean()) / train_b.std(ddof=0), -2.0, 2.0).astype("<f4")

    q_raw = np.random.default_rng(stable_seed(seed, "v3.20", "q", "all")).standard_normal(30)
    q_train = q_raw[np.asarray(SUBJECT_SPLITS["train"])]
    q = ((q_raw - q_train.mean()) / q_train.std(ddof=0)).astype("<f4")
    p = _sigmoid(a[None, :] * (q[:, None] - b[None, :])).astype("<f4")
    information = (a[None, :] ** 2 * p * (1.0 - p)).astype("<f4")

    mean_train_direction = semantic[np.asarray(ITEM_SPLITS["train"])].mean(axis=0).astype(np.float64)
    raw_dq = np.random.default_rng(stable_seed(seed, "v3.20", "d_q", "all")).standard_normal(FEATURE_DIM)
    denominator = float(mean_train_direction @ mean_train_direction)
    if denominator > 0:
        raw_dq = raw_dq - (raw_dq @ mean_train_direction) / denominator * mean_train_direction
    d_q = _unit_vector(raw_dq)

    item_folds = np.asarray([_hash_fold(seed, "item_fold", item) for item in range(120)], dtype=np.int8)
    subject_folds = np.asarray([_hash_fold(seed, "subject_fold", subject) for subject in range(30)], dtype=np.int8)
    # Enforce exact fold balance within each frozen split using hash order.
    for values, folds, role in ((SUBJECT_SPLITS, subject_folds, "subject_fold_balance"), (ITEM_SPLITS, item_folds, "item_fold_balance")):
        for split_values in values.values():
            ordered = sorted(split_values, key=lambda index: stable_seed(seed, "v3.20", role, index))
            half = len(ordered) // 2
            for position, index in enumerate(ordered):
                folds[index] = 0 if position < half else 1

    sentence_items = np.empty((30, SENTENCES_PER_SUBJECT, ITEMS_PER_SENTENCE), dtype=np.int16)
    for subject in range(30):
        pool = ITEM_SPLITS[_split_for_subject(subject)]
        pools = {fold: np.asarray([item for item in pool if item_folds[item] == fold], dtype=np.int16) for fold in (0, 1)}
        for sentence in range(SENTENCES_PER_SUBJECT):
            rng = np.random.default_rng(stable_seed(seed, "v3.20", "sentence_items", f"{subject}:{sentence}"))
            chosen = np.concatenate([rng.choice(pools[0], 2, replace=False), rng.choice(pools[1], 2, replace=False)])
            sentence_items[subject, sentence] = chosen[rng.permutation(4)]
    if np.any(np.apply_along_axis(lambda row: len(set(row.tolist())), 2, sentence_items) != 4):
        raise AssertionError("synthetic sentence contains duplicate items")

    stable_order = sorted(range(120), key=lambda item: stable_seed(seed, "v3.20", "stable_item", item))
    stable_mask = np.zeros(120, dtype=bool)
    stable_mask[stable_order[:90]] = True
    structured_sign = np.ones((30, 120), dtype="<f4")
    for item in np.flatnonzero(~stable_mask):
        for split_subjects in SUBJECT_SPLITS.values():
            ordered = sorted(split_subjects, key=lambda subject: stable_seed(seed, "v3.20", "unstable_sign", f"{item}:{subject}"))
            half = len(ordered) // 2
            structured_sign[np.asarray(ordered[:half]), item] = 1.0
            structured_sign[np.asarray(ordered[half:]), item] = -1.0

    shape = (30, SENTENCES_PER_SUBJECT, ITEMS_PER_SENTENCE, FEATURE_DIM)
    epsilon = np.random.default_rng(stable_seed(seed, "v3.20", "epsilon", "all")).standard_normal(shape).astype("<f4")
    subject_vectors = np.stack([
        np.random.default_rng(stable_seed(seed, "v3.20", "subject_vector", subject)).normal(0.0, 0.20, FEATURE_DIM)
        for subject in range(30)
    ]).astype("<f4")
    session_vectors = np.stack([
        np.stack([
            np.random.default_rng(stable_seed(seed, "v3.20", "session_vector", f"{subject}:{session}")).normal(0.0, 0.10, FEATURE_DIM)
            for session in range(2)
        ])
        for subject in range(30)
    ]).astype("<f4")
    block_scalars = np.random.default_rng(stable_seed(seed, "v3.20", "channel_block_scalars", "all")).normal(
        0.0, 0.15, (30, SENTENCES_PER_SUBJECT, ITEMS_PER_SENTENCE, 105)
    ).astype("<f4")
    block_noise = np.repeat(block_scalars, 8, axis=-1)
    session_index = (np.arange(SENTENCES_PER_SUBJECT) % 2).astype(np.int64)
    base_noise = epsilon
    base_noise += subject_vectors[:, None, None, :]
    base_noise += session_vectors[:, session_index, None, :]
    base_noise += block_noise
    if base_noise.shape != shape or not np.isfinite(base_noise).all():
        raise AssertionError("base-noise contract failed")
    return ReplicateBase(
        seed=seed,
        text_embeddings=text,
        semantic_directions=semantic,
        d_q=d_q,
        a=a,
        b=b,
        q=q,
        p=p,
        information=information,
        stable_mask=stable_mask,
        structured_sign=structured_sign,
        sentence_items=sentence_items,
        item_folds=item_folds,
        subject_folds=subject_folds,
        base_noise=np.ascontiguousarray(base_noise, dtype="<f4"),
        projection_metadata=projection_metadata,
    )


def generate_scenario(base: ReplicateBase, regime: str, alpha: float) -> SyntheticScenario:
    if regime not in REGIMES or float(alpha) not in ALPHAS:
        raise ValueError("regime/alpha is outside the frozen grid")
    train_subjects = np.asarray(SUBJECT_SPLITS["train"])
    train_items = np.asarray(ITEM_SPLITS["train"])
    source = base.information if regime == "STRUCTURED_FISHER" else base.p
    median_train = float(np.median(source[np.ix_(train_subjects, train_items)]))
    j = np.clip(source / median_train, 0.25, 4.0).astype("<f4")
    beta = float(alpha) / (1.0 + float(alpha))
    r = np.exp(beta * np.clip(np.log(j.astype(np.float64)), -np.log(4.0), np.log(4.0))).astype("<f4")
    signs = base.structured_sign if regime == "STRUCTURED_FISHER" else np.ones_like(base.structured_sign)

    subjects = np.arange(30)[:, None, None]
    item_index = base.sentence_items.astype(np.int64)
    r_obs = r[subjects, item_index]
    sign_obs = signs[subjects, item_index]
    c_obs = base.semantic_directions[item_index]
    q_signal = (0.25 * base.q[:, None, None, None] * base.d_q[None, None, None, :]).astype("<f4")
    semantic = (float(alpha) * sign_obs[..., None] * np.sqrt(r_obs[..., None]) * c_obs).astype("<f4")
    features = (base.base_noise / np.sqrt(r_obs[..., None]) + q_signal + semantic).astype("<f4")
    features = np.ascontiguousarray(features)
    sentence_features = features.mean(axis=2, dtype=np.float32).astype("<f4")
    text_sum = base.text_embeddings[item_index].mean(axis=2, dtype=np.float32)
    sentence_text = _unit_rows(text_sum.reshape(-1, TEXT_DIM)).reshape(30, SENTENCES_PER_SUBJECT, TEXT_DIM)
    info_obs = base.information[subjects, item_index]
    if regime == "STRUCTURED_FISHER":
        oracle = info_obs.mean(axis=2, dtype=np.float32)
    else:
        amplitude = np.maximum(float(alpha) * sign_obs * np.sqrt(r_obs), 0.0)
        oracle = amplitude.mean(axis=2, dtype=np.float32)
    feature_hash = sha256_bytes(canonical_bytes(features))
    return SyntheticScenario(
        replicate_seed=base.seed,
        regime=regime,
        alpha=float(alpha),
        item_features=features,
        sentence_features=sentence_features,
        sentence_text_targets=np.ascontiguousarray(sentence_text, dtype="<f4"),
        sentence_items=base.sentence_items,
        item_text_embeddings=base.text_embeddings,
        subject_folds=base.subject_folds,
        item_folds=base.item_folds,
        feature_sha256=feature_hash,
        truth=ScenarioTruth(
            a=base.a,
            b=base.b,
            q=base.q,
            information_by_observation=info_obs,
            oracle_sentence_budget=np.ascontiguousarray(oracle, dtype="<f4"),
            stable_mask=base.stable_mask,
            sign_by_observation=sign_obs,
        ),
    )


def partition_sentence_ids(split: str) -> list[str]:
    return [f"synthetic|subject={subject}|sentence={sentence}" for subject in SUBJECT_SPLITS[split] for sentence in range(SENTENCES_PER_SUBJECT)]


def flatten_partition(scenario: SyntheticScenario, split: str) -> dict[str, Any]:
    subjects = np.asarray(SUBJECT_SPLITS[split], dtype=np.int64)
    item_features = scenario.item_features[subjects].reshape(-1, FEATURE_DIM)
    item_indices = scenario.sentence_items[subjects].reshape(-1).astype(np.int64)
    sentence_features = scenario.sentence_features[subjects].reshape(-1, FEATURE_DIM)
    sentence_text = scenario.sentence_text_targets[subjects].reshape(-1, TEXT_DIM)
    sentence_items = scenario.sentence_items[subjects].reshape(-1, ITEMS_PER_SENTENCE).astype(np.int64)
    subject_per_sentence = np.repeat(subjects, SENTENCES_PER_SUBJECT)
    sentence_number = np.tile(np.arange(SENTENCES_PER_SUBJECT), len(subjects))
    subject_per_item = np.repeat(subject_per_sentence, ITEMS_PER_SENTENCE)
    sentence_per_item = np.repeat(sentence_number, ITEMS_PER_SENTENCE)
    observation_ids = [
        f"synthetic|subject={subject}|sentence={sentence}|slot={slot}|item={item}"
        for subject, sentence, item in zip(subject_per_item, sentence_per_item, item_indices, strict=True)
        for slot in [0]
    ]
    # Replace the placeholder slot with the true within-sentence position.
    observation_ids = [value.replace("slot=0", f"slot={index % ITEMS_PER_SENTENCE}") for index, value in enumerate(observation_ids)]
    sentence_ids = [f"synthetic|subject={subject}|sentence={sentence}" for subject, sentence in zip(subject_per_sentence, sentence_number, strict=True)]
    return {
        "item_features": item_features,
        "item_indices": item_indices,
        "sentence_features": sentence_features,
        "sentence_text": sentence_text,
        "sentence_items": sentence_items,
        "sentence_subjects": subject_per_sentence,
        "sentence_numbers": sentence_number,
        "item_subjects": subject_per_item,
        "item_sentences": sentence_per_item,
        "observation_ids": observation_ids,
        "sentence_ids": sentence_ids,
    }


def candidate_sets(seed: int, split: str) -> np.ndarray:
    count = len(SUBJECT_SPLITS[split]) * SENTENCES_PER_SUBJECT
    result = np.empty((count, CANDIDATE_N), dtype=np.int64)
    for local_subject in range(len(SUBJECT_SPLITS[split])):
        offset = local_subject * SENTENCES_PER_SUBJECT
        pool = np.arange(offset, offset + SENTENCES_PER_SUBJECT, dtype=np.int64)
        for sentence in range(SENTENCES_PER_SUBJECT):
            target = offset + sentence
            distractors = pool[pool != target]
            rng = np.random.default_rng(stable_seed(seed, "v3.20", "candidate_N10", f"{split}:{target}"))
            selected = rng.choice(distractors, CANDIDATE_N - 1, replace=False)
            candidates = np.concatenate(([target], selected))
            result[target] = candidates[rng.permutation(CANDIDATE_N)]
    return result


def assert_split_isolation() -> None:
    subject_sets = [set(values) for values in SUBJECT_SPLITS.values()]
    item_sets = [set(values) for values in ITEM_SPLITS.values()]
    if any(subject_sets[left] & subject_sets[right] for left in range(3) for right in range(left + 1, 3)):
        raise AssertionError("subject splits overlap")
    if any(item_sets[left] & item_sets[right] for left in range(3) for right in range(left + 1, 3)):
        raise AssertionError("item splits overlap")
    if set.union(*subject_sets) != set(range(30)) or set.union(*item_sets) != set(range(120)):
        raise AssertionError("split coverage failed")


def scope_digest(ids: Iterable[str]) -> dict[str, Any]:
    ordered = sorted(set(map(str, ids)))
    return {"count": len(ordered), "sha256": canonical_json_hash(ordered)}


def build_synthetic_v5_ledger(
    *,
    fit_id: str,
    scenario_id: str,
    fit_ids: Sequence[str],
    selection_ids: Sequence[str] = (),
    final_test_ids: Sequence[str] = (),
    generator_hash: str,
    scope: str,
) -> dict[str, Any]:
    fit = set(map(str, fit_ids))
    selection = set(map(str, selection_ids))
    final_test = set(map(str, final_test_ids))
    if not fit or fit & selection or fit & final_test or selection & final_test:
        raise ValueError("synthetic V5 scopes are empty or overlap")
    if not fit_id or not scenario_id or not generator_hash or not scope:
        raise ValueError("synthetic V5 identifiers are required")
    row = {
        "schema_version": 1,
        "dataset": "synthetic_v3_20",
        "fit_id": fit_id,
        "scenario_id": scenario_id,
        "method_scope": scope,
        "generator_feature_sha256": generator_hash,
        "fit_scope": scope_digest(fit),
        "selection_scope": scope_digest(selection),
        "final_test_scope": scope_digest(final_test),
        "normalizer_fit_only": True,
        "probe_fit_only": True,
        "gate_fit_only": True,
        "hyperparameters_selection_only": True,
        "final_test_read_after_choice_freeze": bool(final_test),
        "real_outer_test_reads": 0,
        "true_parameter_model_inputs": [],
        "v5_pass": True,
    }
    validate_synthetic_v5_or_raise(row)
    return row


def validate_synthetic_v5_or_raise(row: Mapping[str, Any]) -> None:
    required_scopes = ("fit_scope", "selection_scope", "final_test_scope")
    if row.get("dataset") != "synthetic_v3_20" or row.get("v5_pass") is not True:
        raise ValueError("synthetic V5 dataset/pass marker failed")
    if any(not isinstance(row.get(name), Mapping) for name in required_scopes):
        raise ValueError("synthetic V5 scope digest missing")
    if int(row["fit_scope"].get("count", 0)) <= 0:
        raise ValueError("synthetic V5 fit scope is empty")
    if row.get("real_outer_test_reads") != 0 or row.get("true_parameter_model_inputs") != []:
        raise ValueError("synthetic V5 claim/input boundary failed")
    if not all(row.get(name) is True for name in ("normalizer_fit_only", "probe_fit_only", "gate_fit_only", "hyperparameters_selection_only")):
        raise ValueError("synthetic V5 fit-only discipline failed")


def alpha_zero_byte_equality(base: ReplicateBase) -> tuple[bool, str, str]:
    structured = generate_scenario(base, "STRUCTURED_FISHER", 0.0)
    monotone = generate_scenario(base, "MONOTONE_DIRECT", 0.0)
    equal = canonical_bytes(structured.item_features) == canonical_bytes(monotone.item_features)
    return equal, structured.feature_sha256, monotone.feature_sha256
