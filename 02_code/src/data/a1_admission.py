"""Frozen v3.14 A1 admission helpers.

The module contains the deterministic sham, fold-local probe, statistics and
V5-ledger machinery used by ``run_a1_admission.py``.  Dataset I/O stays in the
script so the pure contracts can be adversarially unit-tested without EEG.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
from scipy import linalg as scipy_linalg
from sklearn.cluster import KMeans
from sklearn.metrics import balanced_accuracy_score

from backbones.a1_spectral import A1AlignmentEncoder, DEFAULT_CONFIG
from protocol.leakage_audit import validate_run_ledger


SCHEMA_VERSION = 1
ALGORITHM_VERSION = "a1-admission-v314-r3-v2"
TASKS = ("task1_nr", "task2_tsr")
OUTER_CELLS = {
    "task1_nr": "task1_nr|outer_s0_t0",
    "task2_tsr": "task2_tsr|outer_s0_t0",
}
SEEDS = (20260813, 20260814, 20260815)
ARMS = ("real", "trial_shuffle", "within_trial_unit_assignment_shuffle", "channel_block_permutation")
BASES = ("raw", "token_local_frozen_initial_latent")


@dataclass(frozen=True)
class AdmissionConfig:
    ridge_alpha: float = 1.0
    softmax_temperature: float = 0.07
    min_item_observations: int = 20
    min_item_subjects: int = 5
    bootstrap_resamples: int = 10_000
    permutation_resamples: int = 1_000
    semantic_clusters: int = 8
    subject_classes: int = 15
    logistic_c: float = 1.0
    logistic_solver: str = "lbfgs"
    logistic_max_iter: int = 1000
    logistic_tol: float = 1e-6
    trial_length_ratio_low: float = 0.75
    trial_length_ratio_high: float = 1.25
    preflight_min_common_support: float = 0.50
    maximum_fit_seconds: float = 300.0
    feature_dim: int = 840
    latent_dim: int = 384
    h_dim: int = 384
    channel_blocks: int = 105
    bands_per_channel: int = 8

    def __post_init__(self) -> None:
        if self.ridge_alpha != 1.0 or self.softmax_temperature != 0.07:
            raise ValueError("v3.14 freezes ridge alpha=1.0 and temperature=0.07")
        if (self.min_item_observations, self.min_item_subjects) != (20, 5):
            raise ValueError("v3.14 freezes item support at 20 observations/5 subjects")
        if (self.bootstrap_resamples, self.permutation_resamples) != (10_000, 1_000):
            raise ValueError("v3.14 freezes B=10000 and permutation B=1000")
        if (self.semantic_clusters, self.subject_classes) != (8, 15):
            raise ValueError("v3.14 freezes K=8 and the 15-way subject probe")
        if self.feature_dim != self.channel_blocks * self.bands_per_channel:
            raise ValueError("A1 raw feature order must be 105 channel blocks x 8 bands")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_ADMISSION_CONFIG = AdmissionConfig()


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def config_hash(config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG) -> str:
    return sha256_bytes(canonical_json_bytes(config.to_dict()))


def stable_seed(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16) % (2**63 - 1)


def deterministic_gzip_jsonl(rows: Iterable[Mapping[str, Any]]) -> bytes:
    ordered = sorted((dict(row) for row in rows), key=canonical_json_bytes)
    raw = b"".join(canonical_json_bytes(row, newline=True) for row in ordered)
    return gzip.compress(raw, compresslevel=9, mtime=0)


def sattolo_cycle(size: int, *, seed_parts: Sequence[object]) -> np.ndarray:
    """Return one deterministic zero-fixed-point cycle over ``range(size)``."""

    if size < 2:
        raise ValueError("Sattolo requires at least two units")
    rng = np.random.default_rng(stable_seed(*seed_parts))
    values = np.arange(size, dtype=np.int64)
    for index in range(size - 1, 0, -1):
        swap = int(rng.integers(0, index))
        values[index], values[swap] = values[swap], values[index]
    if np.any(values == np.arange(size)) or len(set(values.tolist())) != size:
        raise AssertionError("Sattolo cycle violated the no-fixed-point permutation contract")
    return values


def channel_block_permutation(
    features: np.ndarray,
    *,
    seed: int,
    partition: str,
    record_id: str,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> tuple[np.ndarray, np.ndarray]:
    array = np.asarray(features, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != config.feature_dim:
        raise ValueError("channel permutation requires float32 [T,840]")
    permutation = sattolo_cycle(
        config.channel_blocks,
        seed_parts=(seed, "channel_block_permutation", partition, record_id),
    )
    blocks = array.reshape(array.shape[0], config.channel_blocks, config.bands_per_channel)
    result = blocks[:, permutation, :].reshape(array.shape).astype(np.float32, copy=False)
    return result, permutation


def within_trial_assignment(
    size: int, *, seed: int, partition: str, record_id: str
) -> np.ndarray:
    return sattolo_cycle(
        size,
        seed_parts=(seed, "within_trial_unit_assignment_shuffle", partition, record_id),
    )


def _trial_compatible(
    target: Mapping[str, Any], donor: Mapping[str, Any], config: AdmissionConfig
) -> bool:
    if target["record_id"] == donor["record_id"]:
        return False
    if target["subject_id"] != donor["subject_id"]:
        return False
    if target["session_id"] != donor["session_id"]:
        return False
    if target.get("source_mode", "word_aligned") != donor.get("source_mode", "word_aligned"):
        return False
    if target["group_key"] == donor["group_key"]:
        return False
    ratio = float(donor["unit_count"]) / float(target["unit_count"])
    return config.trial_length_ratio_low <= ratio <= config.trial_length_ratio_high


def trial_shuffle_assignment(
    trials: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    partition: str,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Build a deterministic donor permutation inside legal subject/session buckets.

    Candidate donors are ordered by the exact pair hash required by D37.2.
    A deterministic augmenting-path matching gives a no-self bijection (a set
    of permutation cycles).  Trials that cannot participate are explicitly
    ledgered rather than borrowed from another scope.
    """

    rows = [dict(row) for row in trials]
    if len({str(row["record_id"]) for row in rows}) != len(rows):
        raise ValueError("trial record IDs must be unique")
    escaped = [
        str(row["record_id"])
        for row in rows
        if "partition" in row and str(row["partition"]) != partition
    ]
    if escaped:
        raise ValueError(
            "trial donor candidates crossed the requested partition: "
            + ",".join(sorted(escaped))
        )
    buckets: defaultdict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row["subject_id"]), str(row["session_id"]), str(row.get("source_mode", "word_aligned")))
        buckets[key].append(row)

    assignment: dict[str, str] = {}
    exclusions: list[dict[str, str]] = []
    for key in sorted(buckets):
        bucket = sorted(buckets[key], key=lambda row: str(row["record_id"]))
        candidates: dict[str, list[str]] = {}
        by_id = {str(row["record_id"]): row for row in bucket}
        for target in bucket:
            target_id = str(target["record_id"])
            legal = [
                str(donor["record_id"])
                for donor in bucket
                if _trial_compatible(target, donor, config)
            ]
            legal.sort(
                key=lambda donor_id: hashlib.sha256(
                    f"{seed}|trial_shuffle|{partition}|{target_id}|{donor_id}".encode("utf-8")
                ).hexdigest()
            )
            candidates[target_id] = legal

        active = {target_id for target_id, legal in candidates.items() if legal}
        changed = True
        while changed:
            changed = False
            for target_id in sorted(tuple(active)):
                legal = [donor for donor in candidates[target_id] if donor in active]
                if not legal:
                    active.remove(target_id)
                    changed = True
        for target_id in sorted(set(candidates) - active):
            exclusions.append({"record_id": target_id, "reason": "TRIAL_SHUFFLE_NO_LEGAL_DONOR"})
        if not active:
            continue

        donor_owner: dict[str, str] = {}

        def augment(target_id: str, seen: set[str]) -> bool:
            for donor_id in candidates[target_id]:
                if donor_id not in active or donor_id in seen:
                    continue
                seen.add(donor_id)
                owner = donor_owner.get(donor_id)
                if owner is None or augment(owner, seen):
                    donor_owner[donor_id] = target_id
                    return True
            return False

        ordered_targets = sorted(
            active,
            key=lambda target_id: (
                len([donor for donor in candidates[target_id] if donor in active]),
                hashlib.sha256(f"{seed}|trial_shuffle|{partition}|{target_id}".encode()).hexdigest(),
            ),
        )
        failed: list[str] = []
        for target_id in ordered_targets:
            if not augment(target_id, set()):
                failed.append(target_id)
        if failed:
            # A partial matching is never admitted.  Exclude the whole bucket
            # so no donor is duplicated and every retained row remains matched.
            for target_id in sorted(active):
                exclusions.append({"record_id": target_id, "reason": "TRIAL_SHUFFLE_DERANGEMENT_UNAVAILABLE"})
            continue
        inverse = {target_id: donor_id for donor_id, target_id in donor_owner.items()}
        if set(inverse) != active or set(inverse.values()) != active:
            raise AssertionError("trial donor assignment is not a permutation")
        for target_id, donor_id in inverse.items():
            if not _trial_compatible(by_id[target_id], by_id[donor_id], config):
                raise AssertionError("trial donor escaped the frozen scope")
            assignment[target_id] = donor_id
    return dict(sorted(assignment.items())), exclusions


def apply_trial_shuffle(
    features: np.ndarray,
    trial_rows: Mapping[str, Sequence[int]],
    assignment: Mapping[str, str],
) -> tuple[np.ndarray, np.ndarray]:
    array = np.asarray(features, dtype=np.float32)
    output = np.empty_like(array)
    retained: list[int] = []
    for target_id in sorted(assignment):
        target_indices = list(trial_rows[target_id])
        donor_indices = list(trial_rows[assignment[target_id]])
        if not target_indices or not donor_indices:
            continue
        for position, target_index in enumerate(target_indices):
            if len(target_indices) == 1:
                donor_position = 0
            else:
                donor_position = int(round(position * (len(donor_indices) - 1) / (len(target_indices) - 1)))
            output[target_index] = array[donor_indices[donor_position]]
            retained.append(target_index)
    return output, np.asarray(sorted(retained), dtype=np.int64)


def build_four_arm_features(
    normalized_features: np.ndarray,
    observations: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    partition: str,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, Any]]:
    """Construct all four arms and retain their exact row intersection."""

    features = np.asarray(normalized_features, dtype=np.float32)
    if features.shape != (len(observations), config.feature_dim) or not np.isfinite(features).all():
        raise ValueError("normalized observation matrix must be finite [N,840]")
    trial_rows: defaultdict[str, list[int]] = defaultdict(list)
    trial_meta: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(observations):
        record_id = str(row["record_id"])
        trial_rows[record_id].append(index)
        trial_meta.setdefault(
            record_id,
            {
                "record_id": record_id,
                "subject_id": str(row["subject_id"]),
                "session_id": str(row["session_id"]),
                "source_mode": "word_aligned",
                "group_key": str(row["group_key"]),
            },
        )
    for record_id, indices in trial_rows.items():
        trial_meta[record_id]["unit_count"] = len(indices)

    trial_assignment, trial_exclusions = trial_shuffle_assignment(
        list(trial_meta.values()), seed=seed, partition=partition, config=config
    )
    trial_values, trial_supported = apply_trial_shuffle(features, trial_rows, trial_assignment)

    unit_values = np.empty_like(features)
    unit_supported: list[int] = []
    unit_exclusions: list[dict[str, str]] = []
    unit_permutations: dict[str, list[int]] = {}
    channel_values = np.empty_like(features)
    channel_permutations: dict[str, list[int]] = {}
    for record_id in sorted(trial_rows):
        indices = trial_rows[record_id]
        if len(indices) >= 2:
            permutation = within_trial_assignment(
                len(indices), seed=seed, partition=partition, record_id=record_id
            )
            unit_values[indices] = features[np.asarray(indices)[permutation]]
            unit_supported.extend(indices)
            unit_permutations[record_id] = permutation.tolist()
        else:
            unit_exclusions.append({"record_id": record_id, "reason": "WITHIN_TRIAL_REQUIRES_T_GE_2"})
        permuted, channel_perm = channel_block_permutation(
            features[indices], seed=seed, partition=partition, record_id=record_id, config=config
        )
        channel_values[indices] = permuted
        channel_permutations[record_id] = channel_perm.tolist()

    common = np.asarray(
        sorted(set(trial_supported.tolist()).intersection(unit_supported)), dtype=np.int64
    )
    arms = {
        "real": features[common],
        "trial_shuffle": trial_values[common],
        "within_trial_unit_assignment_shuffle": unit_values[common],
        "channel_block_permutation": channel_values[common],
    }
    shapes = {name: value.shape for name, value in arms.items()}
    if len(set(shapes.values())) != 1 or any(not np.isfinite(value).all() for value in arms.values()):
        raise AssertionError("four-arm row/capacity equality failed")
    audit = {
        "partition": partition,
        "seed": seed,
        "input_rows": len(observations),
        "common_rows": int(common.size),
        "common_support_rate": float(common.size / len(observations)) if observations else 0.0,
        "trial_assignment": trial_assignment,
        "trial_exclusions": trial_exclusions,
        "unit_exclusions": unit_exclusions,
        "trial_no_fixed_points": all(target != donor for target, donor in trial_assignment.items()),
        "unit_no_fixed_points": all(
            all(index != donor for index, donor in enumerate(values))
            for values in unit_permutations.values()
        ),
        "channel_no_fixed_points": all(
            all(index != donor for index, donor in enumerate(values))
            for values in channel_permutations.values()
        ),
        "row_ids_identical": True,
        "capacity_identical": True,
    }
    return arms, common, audit


def fit_fold_normalizer(
    train: np.ndarray, *, config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    array = np.asarray(train, dtype=np.float64)
    if array.ndim != 2 or array.shape[0] < 1 or array.shape[1] != config.feature_dim:
        raise ValueError("normalizer train rows must be [N,840]")
    if not np.isfinite(array).all():
        raise ValueError("normalizer train rows must be finite")
    lower = np.quantile(array, 0.005, axis=0)
    upper = np.quantile(array, 0.995, axis=0)
    clipped = np.clip(array, lower, upper)
    median = np.median(clipped, axis=0)
    q25, q75 = np.quantile(clipped, [0.25, 0.75], axis=0)
    raw_iqr = q75 - q25
    iqr = np.maximum(raw_iqr, 1e-6)
    state = {"lower": lower, "upper": upper, "median": median, "iqr": iqr}
    summary = {
        "fit_rows": int(array.shape[0]),
        "feature_dim": int(array.shape[1]),
        "zero_iqr_dimension_count": int(np.count_nonzero(raw_iqr == 0.0)),
        "epsilon_dimension_count": int(np.count_nonzero(raw_iqr < 1e-6)),
        "iqr_min_after_epsilon": float(iqr.min()),
        "finite": True,
    }
    return state, summary


def transform_fold_normalizer(values: np.ndarray, state: Mapping[str, np.ndarray]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("normalizer transform rows must be finite rank-2")
    clipped = np.clip(array, state["lower"], state["upper"])
    result = ((clipped - state["median"]) / state["iqr"]).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError("normalizer produced nonfinite values")
    return result


def supported_item_ids(
    observations: Sequence[Mapping[str, Any]],
    *,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> tuple[set[str], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    subjects: defaultdict[str, set[str]] = defaultdict(set)
    surfaces: dict[str, str] = {}
    for row in observations:
        item = str(row["item_id"])
        counts[item] += 1
        subjects[item].add(str(row["subject_id"]))
        surfaces[item] = str(row["surface"])
    ledger = [
        {
            "item_id": item,
            "surface": surfaces[item],
            "n_observations": counts[item],
            "n_subjects": len(subjects[item]),
            "supported": counts[item] >= config.min_item_observations
            and len(subjects[item]) >= config.min_item_subjects,
        }
        for item in sorted(counts)
    ]
    return {row["item_id"] for row in ledger if row["supported"]}, ledger


def token_local_frozen_initial_latent(
    values: np.ndarray,
    *,
    seed: int,
    device: str,
    batch_size: int = 4096,
) -> tuple[np.ndarray, dict[str, Any]]:
    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != DEFAULT_CONFIG.feature_dim or not np.isfinite(array).all():
        raise ValueError("latent input must be finite float32 [N,840]")
    encoder = A1AlignmentEncoder(seed=seed).to(device)
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(array), batch_size):
            tensor = torch.as_tensor(array[start : start + batch_size], dtype=torch.float32, device=device).unsqueeze(1)
            mask = torch.ones((tensor.shape[0], 1), dtype=torch.bool, device=device)
            outputs.append(encoder(tensor, mask).cpu().numpy().astype(np.float32, copy=False))
    result = np.concatenate(outputs, axis=0) if outputs else np.empty((0, DEFAULT_CONFIG.d_align), np.float32)
    if result.shape != (len(array), DEFAULT_CONFIG.d_align) or not np.isfinite(result).all():
        raise AssertionError("token-local latent violated [N,384] finite contract")
    return result, {
        "seed": seed,
        "name": "token_local_frozen_initial_latent",
        "input_shape": list(array.shape),
        "output_shape": list(result.shape),
        "mask_all_true": True,
        "sequence_length": 1,
        "model_eval": not encoder.training,
        "trainable_parameter_count": sum(p.numel() for p in encoder.parameters() if p.requires_grad),
        "parameter_count": encoder.parameter_count,
    }


def fit_ridge_to_items(
    x_train: np.ndarray,
    y_train: np.ndarray,
    *,
    alpha: float,
    device: str,
) -> tuple[dict[str, np.ndarray], float]:
    """Fit intercept-unregularized multi-output ridge by stable float64 Cholesky.

    The 1.0 ridge term is small relative to the repeated H columns in these
    real folds.  Forming the Gram matrix in float32 can therefore lose positive
    definiteness through rounding even though the mathematical system is
    strictly positive definite.  Float64 CPU accumulation is an engineering
    solver choice only; it does not change alpha, rows, targets or capacity.
    """

    x = np.asarray(x_train, dtype=np.float32)
    y = np.asarray(y_train, dtype=np.float32)
    if x.ndim != 2 or y.ndim != 2 or x.shape[0] != y.shape[0] or x.shape[0] < 2:
        raise ValueError("ridge X/Y must be aligned rank-2 matrices")
    if alpha != 1.0 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("ridge contract requires alpha=1.0 and finite inputs")
    started = time.perf_counter()
    x64 = x.astype(np.float64, copy=False)
    y64 = y.astype(np.float64, copy=False)
    x_mean = x64.mean(axis=0)
    y_mean = y64.mean(axis=0)
    xc = x64 - x_mean
    yc = y64 - y_mean
    gram = xc.T @ xc
    gram = (gram + gram.T) * 0.5
    gram.flat[:: gram.shape[0] + 1] += float(alpha)
    rhs = xc.T @ yc
    try:
        weights = scipy_linalg.solve(
            gram,
            rhs,
            assume_a="pos",
            overwrite_a=True,
            overwrite_b=True,
            check_finite=False,
        )
    except scipy_linalg.LinAlgError as exc:
        raise RuntimeError("ridge float64 Cholesky factorization failed") from exc
    intercept = y_mean - x_mean @ weights
    elapsed = time.perf_counter() - started
    result = {
        "weights": weights.astype(np.float32, copy=False),
        "intercept": intercept.astype(np.float32, copy=False),
    }
    return result, elapsed


def ridge_log_prob(
    model: Mapping[str, np.ndarray],
    x: np.ndarray,
    item_embeddings: np.ndarray,
    true_positions: np.ndarray,
    *,
    temperature: float,
    device: str,
    batch_size: int = 8192,
) -> np.ndarray:
    if temperature != 0.07:
        raise ValueError("v3.14 freezes temperature=0.07")
    values = np.asarray(x, dtype=np.float32)
    vocabulary = np.asarray(item_embeddings, dtype=np.float32)
    positions = np.asarray(true_positions, dtype=np.int64)
    if values.shape[0] != positions.shape[0] or vocabulary.ndim != 2:
        raise ValueError("ridge scoring rows/vocabulary mismatch")
    weights = torch.as_tensor(model["weights"], dtype=torch.float32, device=device)
    intercept = torch.as_tensor(model["intercept"], dtype=torch.float32, device=device)
    vocab = torch.as_tensor(vocabulary, dtype=torch.float32, device=device)
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(values), batch_size):
            batch = torch.as_tensor(values[start : start + batch_size], dtype=torch.float32, device=device)
            query = batch @ weights + intercept
            query = torch.nn.functional.normalize(query, p=2, dim=1)
            logits = query @ vocab.T / temperature
            pos = torch.as_tensor(positions[start : start + batch_size], dtype=torch.long, device=device)
            row = torch.arange(len(pos), device=device)
            logp = logits[row, pos] - torch.logsumexp(logits, dim=1)
            outputs.append(logp.cpu().numpy().astype(np.float64))
    result = np.concatenate(outputs) if outputs else np.empty(0, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError("ridge scoring produced nonfinite log probability")
    return result


def u_statistics(real: np.ndarray, shams: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    real_values = np.asarray(real, dtype=np.float64)
    names = ("trial_shuffle", "within_trial_unit_assignment_shuffle", "channel_block_permutation")
    values = [np.asarray(shams[name], dtype=np.float64) for name in names]
    if any(value.shape != real_values.shape for value in values):
        raise ValueError("real/sham scoring rows differ")
    stack = np.stack(values, axis=0)
    return {
        "u_oof": real_values - stack.mean(axis=0),
        "u_min": real_values - stack.max(axis=0),
        **{f"real_minus_{name}": real_values - value for name, value in zip(names, values, strict=True)},
    }


def percentile_interval(draws: np.ndarray) -> list[float]:
    values = np.asarray(draws, dtype=np.float64)
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def cluster_bootstrap(
    values: Mapping[str, float], *, n_resamples: int, seed: int
) -> dict[str, Any]:
    subjects = sorted(values)
    if not subjects:
        raise ValueError("cluster bootstrap requires subjects")
    vector = np.asarray([float(values[subject]) for subject in subjects], dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(vector), size=(n_resamples, len(vector)))
    draws = vector[indices].mean(axis=1)
    return {
        "estimate": float(vector.mean()),
        "ci95": percentile_interval(draws),
        "n_subjects": len(subjects),
        "n_resamples": n_resamples,
        "positive_subject_count": int(np.count_nonzero(vector > 0.0)),
        "subject_values": {subject: float(values[subject]) for subject in subjects},
    }


def paired_subject_bootstrap(
    raw: Mapping[str, float],
    latent: Mapping[str, float],
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    subjects = sorted(set(raw).intersection(latent))
    if not subjects:
        raise ValueError("paired bootstrap has no common subjects")
    difference = {subject: float(latent[subject]) - float(raw[subject]) for subject in subjects}
    result = cluster_bootstrap(difference, n_resamples=n_resamples, seed=seed)
    result["direction"] = "latent_minus_raw"
    return result


def summarize_a_a1(
    rows: Sequence[Mapping[str, Any]],
    *,
    task: str,
    basis: str,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> dict[str, Any]:
    selected = [row for row in rows if row["task"] == task and row["basis"] == basis]
    if not selected:
        raise ValueError(f"no A-A1 rows for {task}/{basis}")
    by_observation: defaultdict[str, defaultdict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    subjects: dict[str, str] = {}
    for row in selected:
        oid = str(row["observation_id"])
        subjects[oid] = str(row["subject_id"])
        for metric in ("u_oof", "u_min", "real_minus_trial_shuffle", "real_minus_within_trial_unit_assignment_shuffle", "real_minus_channel_block_permutation"):
            by_observation[oid][metric].append(float(row[metric]))
    subject_metrics: defaultdict[str, defaultdict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for oid in sorted(by_observation):
        for metric, values in by_observation[oid].items():
            subject_metrics[subjects[oid]][metric].append(float(np.mean(values)))
    metric_summaries: dict[str, Any] = {}
    for metric in ("u_oof", "u_min", "real_minus_trial_shuffle", "real_minus_within_trial_unit_assignment_shuffle", "real_minus_channel_block_permutation"):
        subject_values = {
            subject: float(np.mean(subject_metrics[subject][metric]))
            for subject in sorted(subject_metrics)
            if subject_metrics[subject][metric]
        }
        metric_summaries[metric] = cluster_bootstrap(
            subject_values,
            n_resamples=config.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A1", task, basis, metric),
        )
    passed = (
        metric_summaries["u_oof"]["ci95"][0] > 0.0
        and metric_summaries["u_min"]["ci95"][0] > 0.0
        and metric_summaries["u_oof"]["positive_subject_count"] >= 12
        and metric_summaries["u_min"]["positive_subject_count"] >= 12
        and all(metric_summaries[name]["estimate"] > 0.0 for name in metric_summaries if name.startswith("real_minus_"))
        and metric_summaries["u_oof"]["n_subjects"] == 15
    )
    return {
        "task": task,
        "basis": basis,
        "observation_seed_rows": len(selected),
        "unique_observations": len(by_observation),
        "metrics": metric_summaries,
        "pass": bool(passed),
    }


class FrozenLogisticPredictor:
    """Small prediction-only wrapper for a completed full-batch LBFGS fit."""

    def __init__(self, weights: np.ndarray, intercept: np.ndarray, classes: np.ndarray, device: str) -> None:
        self.weights = np.asarray(weights, dtype=np.float32)
        self.intercept = np.asarray(intercept, dtype=np.float32)
        self.classes_ = np.asarray(classes)
        self.device = device

    def predict(self, x: np.ndarray) -> np.ndarray:
        values = torch.as_tensor(np.asarray(x, dtype=np.float32), device=self.device)
        weights = torch.as_tensor(self.weights, device=self.device)
        intercept = torch.as_tensor(self.intercept, device=self.device)
        with torch.no_grad():
            positions = (values @ weights.T + intercept).argmax(dim=1).cpu().numpy()
        return self.classes_[positions]


def fit_fixed_logistic(
    x: np.ndarray, y: Sequence[str | int], *, device: str = "cpu"
) -> tuple[FrozenLogisticPredictor, float]:
    """Fit the frozen multinomial L2/C=1 model with full-batch LBFGS.

    The objective matches sklearn's registered ``lbfgs`` scaling: balanced
    sample-weighted mean cross entropy plus ``0.5/(C*sum_weight)*||W||²``;
    the intercept is not regularized.  CUDA is an implementation backend, not
    a different optimizer or scientific setting.
    """

    values = np.asarray(x, dtype=np.float32)
    labels = np.asarray(y)
    if values.ndim != 2 or values.shape[0] != labels.shape[0] or not np.isfinite(values).all():
        raise ValueError("logistic rows/labels mismatch")
    classes, encoded = np.unique(labels, return_inverse=True)
    if len(classes) < 2:
        raise ValueError("multinomial logistic requires at least two classes")
    counts = np.bincount(encoded, minlength=len(classes)).astype(np.float64)
    class_weights = len(labels) / (len(classes) * counts)
    sample_weights = class_weights[encoded].astype(np.float32)
    started = time.perf_counter()
    tensor = torch.as_tensor(values, dtype=torch.float32, device=device)
    target = torch.as_tensor(encoded, dtype=torch.long, device=device)
    weights_per_row = torch.as_tensor(sample_weights, dtype=torch.float32, device=device)
    coefficients = torch.zeros(
        (len(classes), values.shape[1]), dtype=torch.float32, device=device, requires_grad=True
    )
    intercept = torch.zeros(len(classes), dtype=torch.float32, device=device, requires_grad=True)
    optimizer = torch.optim.LBFGS(
        [coefficients, intercept],
        lr=1.0,
        max_iter=1000,
        max_eval=1250,
        tolerance_grad=1e-6,
        tolerance_change=1e-12,
        history_size=100,
        line_search_fn="strong_wolfe",
    )

    weight_sum = float(sample_weights.sum(dtype=np.float64))

    def closure() -> torch.Tensor:
        optimizer.zero_grad(set_to_none=True)
        logits = tensor @ coefficients.T + intercept
        pointwise = torch.nn.functional.cross_entropy(logits, target, reduction="none")
        loss = (pointwise * weights_per_row).sum() / weight_sum
        loss = loss + 0.5 / weight_sum * coefficients.square().sum()
        loss.backward()
        return loss

    optimizer.step(closure)
    if str(device).startswith("cuda"):
        torch.cuda.synchronize(torch.device(device))
    model = FrozenLogisticPredictor(
        coefficients.detach().cpu().numpy(),
        intercept.detach().cpu().numpy(),
        classes,
        device,
    )
    return model, time.perf_counter() - started


def material_group_bootstrap(
    correct: Sequence[bool], groups: Sequence[str], *, n_resamples: int, seed: int
) -> dict[str, Any]:
    grouped: defaultdict[str, list[float]] = defaultdict(list)
    for value, group in zip(correct, groups, strict=True):
        grouped[str(group)].append(float(value))
    keys = sorted(grouped)
    values = np.asarray([np.mean(grouped[key]) for key in keys], dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(n_resamples, len(values)))
    draws = values[indices].mean(axis=1)
    return {
        "estimate": float(np.mean(correct)),
        "ci95": percentile_interval(draws),
        "n_material_groups": len(keys),
        "n_resamples": n_resamples,
    }


def permutation_null_fixed_predictions(
    true_labels: Sequence[Any],
    predicted_labels: Sequence[Any],
    blocks: Sequence[str],
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    truth = np.asarray(true_labels)
    predictions = np.asarray(predicted_labels)
    block_values = np.asarray(blocks)
    if truth.shape != predictions.shape or truth.shape != block_values.shape:
        raise ValueError("permutation truth/prediction/block shapes differ")
    classes = sorted(set(truth.tolist()), key=str)
    class_index = {value: index for index, value in enumerate(classes)}
    truth_encoded = np.asarray([class_index[value] for value in truth], dtype=np.int32)
    prediction_encoded = np.asarray(
        [class_index.get(value, -1) for value in predictions], dtype=np.int32
    )
    denominator = np.bincount(truth_encoded, minlength=len(classes)).astype(np.float64)
    if np.any(denominator == 0):
        raise ValueError("permutation label class has zero support")
    rng = np.random.default_rng(seed)
    unique_blocks = sorted(set(block_values.tolist()))
    block_indices = [np.flatnonzero(block_values == block) for block in unique_blocks]
    draws = np.empty(n_resamples, dtype=np.float64)
    for iteration in range(n_resamples):
        permuted = truth_encoded.copy()
        for indices in block_indices:
            permuted[indices] = permuted[indices][rng.permutation(len(indices))]
        correct = permuted == prediction_encoded
        numerator = np.bincount(permuted[correct], minlength=len(classes))
        draws[iteration] = float(np.mean(numerator / denominator))
    return {
        "n_resamples": n_resamples,
        "q95": float(np.quantile(draws, 0.95)),
        "mean": float(draws.mean()),
        "block_count": len(unique_blocks),
        "method": "fixed_oof_predictions_label_permutation_within_registered_blocks",
    }


def deterministic_item_clusters(
    item_embeddings: np.ndarray,
    *,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> tuple[np.ndarray, KMeans]:
    values = np.asarray(item_embeddings, dtype=np.float32)
    if values.ndim != 2 or values.shape[0] < config.semantic_clusters:
        raise ValueError("K=8 requires at least eight supported items")
    model = KMeans(
        n_clusters=config.semantic_clusters,
        init="k-means++",
        n_init=10,
        max_iter=300,
        random_state=20260813,
        algorithm="lloyd",
    )
    labels = model.fit_predict(values)
    return labels.astype(np.int64), model


def summarize_classification(
    *,
    true_labels: Sequence[Any],
    predicted_labels: Sequence[Any],
    subject_ids: Sequence[str],
    chance: float,
    bootstrap: Mapping[str, Any],
    permutation: Mapping[str, Any],
) -> dict[str, Any]:
    truth = np.asarray(true_labels)
    prediction = np.asarray(predicted_labels)
    subjects = np.asarray(subject_ids)
    observed = balanced_recall(truth, prediction)
    per_subject = {
        subject: balanced_recall(truth[subjects == subject], prediction[subjects == subject])
        for subject in sorted(set(subjects.tolist()))
    }
    passed = float(bootstrap["ci95"][0]) > chance and observed > float(permutation["q95"])
    return {
        "balanced_accuracy": observed,
        "macro_recall": observed,
        "chance": chance,
        "bootstrap": dict(bootstrap),
        "permutation_null": dict(permutation),
        "per_subject_recall": per_subject,
        "pass": bool(passed),
    }


def balanced_recall(true_labels: Sequence[Any], predicted_labels: Sequence[Any]) -> float:
    truth = np.asarray(true_labels)
    prediction = np.asarray(predicted_labels)
    if truth.shape != prediction.shape or truth.size == 0:
        raise ValueError("balanced recall requires aligned non-empty labels")
    recalls = [
        float(np.mean(prediction[truth == label] == label))
        for label in sorted(set(truth.tolist()), key=str)
    ]
    return float(np.mean(recalls))


def evaluate_a_a4(
    a1_raw: Mapping[str, Any],
    a1_latent: Mapping[str, Any],
    a2_raw: Mapping[str, Any],
    a2_latent: Mapping[str, Any],
    a3_raw: Mapping[str, Any],
    a3_latent: Mapping[str, Any],
    *,
    task: str,
    config: AdmissionConfig = DEFAULT_ADMISSION_CONFIG,
) -> dict[str, Any]:
    comparisons = {
        "a_a1_u_min": paired_subject_bootstrap(
            a1_raw["metrics"]["u_min"]["subject_values"],
            a1_latent["metrics"]["u_min"]["subject_values"],
            n_resamples=config.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A4", task, "A-A1"),
        ),
        "a_a2_recall": paired_subject_bootstrap(
            a2_raw["per_subject_recall"], a2_latent["per_subject_recall"],
            n_resamples=config.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A4", task, "A-A2"),
        ),
        "a_a3_recall": paired_subject_bootstrap(
            a3_raw["per_subject_recall"], a3_latent["per_subject_recall"],
            n_resamples=config.bootstrap_resamples,
            seed=stable_seed(SEEDS[0], "A-A4", task, "A-A3"),
        ),
    }
    uniformly_worse = all(
        row["estimate"] < 0.0 and row["ci95"][1] < 0.0 for row in comparisons.values()
    )
    co_n1 = bool(a1_raw["pass"] and not a1_latent["pass"])
    invalid_basis_order = bool(not a1_raw["pass"] and a1_latent["pass"])
    return {
        "task": task,
        "comparisons": comparisons,
        "uniformly_worse": uniformly_worse,
        "co_n1_latent_loss": co_n1,
        "invalid_basis_order": invalid_basis_order,
        "pass": not uniformly_worse and not co_n1 and not invalid_basis_order,
    }


def _underpowered_positive(a1: Mapping[str, Any]) -> bool:
    for metric in ("u_oof", "u_min"):
        row = a1["metrics"][metric]
        low, high = row["ci95"]
        if not (row["estimate"] > 0.0 and low <= 0.0 <= high and high >= 0.0):
            return False
    return True


def evaluate_completion_outcome(results: Mapping[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    for task in TASKS:
        a4 = results[task]["A-A4"]
        if a4["invalid_basis_order"]:
            return "INVALID_A1_ADMISSION", [f"{task}:INVALID_BASIS_ORDER"]
        if a4["co_n1_latent_loss"]:
            reasons.append(f"{task}:CO_N1_LATENT_LOSS")
    diagnostics_pass = all(
        results[task][name][basis]["pass"]
        for task in TASKS
        for name in ("A-A2", "A-A3")
        for basis in BASES
    ) and all(results[task]["A-A4"]["pass"] for task in TASKS)
    a1_task_pass = {
        task: all(results[task]["A-A1"][basis]["pass"] for basis in BASES) for task in TASKS
    }
    if diagnostics_pass and all(a1_task_pass.values()):
        return "PASS_A1_ADMISSION_BOTH_TASKS", []
    if diagnostics_pass and sum(a1_task_pass.values()) == 1:
        failed_task = next(task for task in TASKS if not a1_task_pass[task])
        if all(_underpowered_positive(results[failed_task]["A-A1"][basis]) for basis in BASES):
            return "PASS_LIMITED_A1_ADMISSION_ONE_TASK", [f"{failed_task}:POSITIVE_UNDERPOWERED"]
    for task in TASKS:
        for basis in BASES:
            a1 = results[task]["A-A1"][basis]
            if not a1["pass"]:
                reasons.append(f"{task}:{basis}:A-A1_FAIL")
                for metric_name in ("u_oof", "u_min"):
                    metric = a1["metrics"][metric_name]
                    estimate = float(metric["estimate"])
                    low, high = (float(value) for value in metric["ci95"])
                    if high < 0.0:
                        detail = "SIGNIFICANT_NEGATIVE"
                    elif estimate <= 0.0:
                        detail = "NONPOSITIVE_NOT_SIGNIFICANT"
                    elif low <= 0.0:
                        detail = "POSITIVE_UNDERPOWERED"
                    else:
                        detail = "POSITIVE_BUT_OTHER_ACCEPTANCE_FAILED"
                    reasons.append(f"{task}:{basis}:A-A1_{metric_name.upper()}_{detail}")
            for diagnostic in ("A-A2", "A-A3"):
                if not results[task][diagnostic][basis]["pass"]:
                    reasons.append(f"{task}:{basis}:{diagnostic}_FAIL")
        a4 = results[task]["A-A4"]
        if not a4["pass"]:
            if a4.get("uniformly_worse"):
                reasons.append(f"{task}:A-A4_UNIFORMLY_WORSE")
            if not a4.get("uniformly_worse") and not a4.get("co_n1_latent_loss"):
                reasons.append(f"{task}:A-A4_FAIL")
    return "FAIL_A1_ADMISSION", sorted(set(reasons))


def build_v5_ledger(
    *,
    run_id: str,
    fit_id: str,
    seed: int,
    outer_cell: str,
    inner_cell: str | None,
    fit_record_ids: Sequence[str],
    validation_record_ids: Sequence[str],
    input_hashes: Mapping[str, str],
    scoring_record_ids: Sequence[str] = (),
) -> dict[str, Any]:
    common = {
        "outer_cell": outer_cell,
        "inner_cell": inner_cell,
        "calibration_record_ids": [],
        "outer_test_record_ids_read": [],
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
    }
    stages = [
        {
            **common,
            "stage_type": "model_fit",
            "fit_record_ids": sorted(set(fit_record_ids)),
            "selection_record_ids": [],
        }
    ]
    if inner_cell is not None:
        stages.append(
            {
                **common,
                "stage_type": "tuning",
                "fit_record_ids": [],
                "selection_record_ids": sorted(set(validation_record_ids)),
            }
        )
    ledger = {
        "schema_version": 1,
        "dataset": "zuco_2_0",
        "run_id": f"{run_id}|{fit_id}",
        "fit_id": fit_id,
        "seed": seed,
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "stages": stages,
        "scoring_record_ids": sorted(set(scoring_record_ids)),
        "outer_test_record_ids_read": [],
        "calibration_record_ids": [],
    }
    return ledger


def validate_v5_or_raise(
    ledger: Mapping[str, Any],
    scope_index: Mapping[str, Any],
    input_hashes: Mapping[str, str],
) -> None:
    errors = validate_run_ledger(ledger, scope_index, expected_input_hashes=input_hashes)
    if errors:
        raise ValueError("V5 ledger failure: " + "; ".join(errors))


def canonical_artifact(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(value, newline=True)
