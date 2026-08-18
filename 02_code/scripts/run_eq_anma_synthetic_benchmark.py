#!/usr/bin/env python3
"""Run only the frozen SPEC v3.20 EQ-ANMA synthetic benchmark."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import yaml
from torch import Tensor, nn
from torch.nn import functional as F


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from data.a1_admission import (  # noqa: E402
    canonical_artifact,
    deterministic_gzip_jsonl,
    fit_fold_normalizer,
    sattolo_cycle,
    stable_seed,
    transform_fold_normalizer,
    u_statistics,
)
from data.eq_anma_synthetic_benchmark import (  # noqa: E402
    ALPHAS,
    CANDIDATE_N,
    FEATURE_DIM,
    ITEM_SPLITS,
    ITEMS_PER_SENTENCE,
    REGIMES,
    REPLICATE_SEEDS,
    SENTENCES_PER_SUBJECT,
    SUBJECT_SPLITS,
    TEXT_DIM,
    alpha_zero_byte_equality,
    assert_split_isolation,
    build_replicate,
    build_synthetic_v5_ledger,
    candidate_sets,
    canonical_json_hash,
    flatten_partition,
    generate_scenario,
    sha256_bytes,
)
from methods.anma_orig import partial_spearman, rankfit_plateau_step, spearman  # noqa: E402
from methods.direct_u_plus import (  # noqa: E402
    GAMMA_GRID,
    SCORE_VERSIONS,
    WARMUP_VERSIONS,
    direct_u_plus_weights,
    weight_diagnostics,
)
from methods.eq_anma import EQANMAModel, LAMBDA_M_GRID, contribution_soft_response  # noqa: E402


RUN_ID = "2026-08-16_037_v320_eq_anma_synthetic_benchmark"
CONTRACT_PATH = Path("artifacts/eq_anma_synthetic_benchmark_contract.yaml")
RESULT_JSON_PATH = Path("04_results/synthetic_method/eq_anma_synthetic_benchmark.json")
RESULT_MD_PATH = Path("04_results/synthetic_method/eq_anma_synthetic_benchmark.md")
LEDGER_PATH = Path("04_results/synthetic_method/eq_anma_synthetic_benchmark_run_ledger.jsonl.gz")
CACHE_PATH = Path(".codex_eq_anma_synthetic_v320")
ARM_NAMES = ("real", "trial_shuffle", "within_trial_unit_assignment_shuffle", "channel_block_permutation")
ALL_ARMS = ("H_only", *ARM_NAMES)
EXPECTED_RIDGE_FITS = 4800
EXPECTED_ALIGNMENT_FITS = 7104
EXPECTED_TOTAL_FITS = 11904
BOOTSTRAP_RESAMPLES = 10_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument("--worker-count", type=int, default=1)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--max-scenarios", type=int, default=None, help="debug only; forbidden with --formal")
    return parser.parse_args()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contract(root: Path) -> dict[str, Any]:
    value = yaml.safe_load((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    if value.get("contract_status") != "FROZEN_BEFORE_FORMAL_FINAL_TEST":
        raise RuntimeError("STATE_SPEC_CONFLICT: synthetic contract is not frozen")
    if value["accounting"] != {
        "scenarios": 192,
        "ridge_fits": 4800,
        "alignment_fits": 7104,
        "total_fits": 11904,
        "unique_passing_synthetic_v5_ledgers": 11904,
    }:
        raise RuntimeError("STATE_SPEC_CONFLICT: synthetic accounting contract changed")
    spec_path = root / value["governing_spec"]["path"]
    freeze_path = root / value["freeze_artifact"]["path"]
    if _sha256_file(spec_path) != value["governing_spec"]["sha256"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: governing SPEC hash mismatch")
    if _sha256_file(freeze_path) != value["freeze_artifact"]["sha256"]:
        raise RuntimeError("STATE_SPEC_CONFLICT: freeze artifact hash mismatch")
    return value


def _metadata(partition: Mapping[str, Any], selected: np.ndarray) -> list[dict[str, Any]]:
    subjects = np.asarray(partition["item_subjects"])[selected]
    sentences = np.asarray(partition["item_sentences"])[selected]
    item_indices = np.asarray(partition["item_indices"])[selected]
    slots = selected % ITEMS_PER_SENTENCE
    return [
        {
            "record_id": f"synthetic|subject={int(subject)}|sentence={int(sentence)}",
            "observation_id": f"synthetic|subject={int(subject)}|sentence={int(sentence)}|slot={int(slot)}|item={int(item)}",
            "subject_id": str(int(subject)),
            "session_id": str(int(sentence) % 2),
            "group_key": f"sentence={int(sentence)}",
        }
        for subject, sentence, slot, item in zip(subjects, sentences, slots, item_indices, strict=True)
    ]


def _synthetic_shams(
    normalized: np.ndarray,
    metadata: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    partition: str,
) -> dict[str, np.ndarray]:
    values = np.asarray(normalized, dtype=np.float32)
    groups: dict[str, list[int]] = {}
    group_subject_session: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(metadata):
        record_id = str(row["record_id"])
        groups.setdefault(record_id, []).append(index)
        group_subject_session[record_id] = (str(row["subject_id"]), str(row["session_id"]))
    sizes = {len(indices) for indices in groups.values()}
    if sizes not in ({2}, {4}):
        raise AssertionError(f"frozen two-by-two sentence balance failed: {sizes}")

    trial = np.empty_like(values)
    buckets: dict[tuple[str, str], list[str]] = {}
    for record_id, key in group_subject_session.items():
        buckets.setdefault(key, []).append(record_id)
    for key in sorted(buckets):
        records = sorted(buckets[key])
        if len(records) < 2:
            raise AssertionError("trial sham bucket has fewer than two sentences")
        permutation = sattolo_cycle(len(records), seed_parts=(seed, "trial_shuffle", partition, *key))
        for target_position, target_id in enumerate(records):
            donor_id = records[int(permutation[target_position])]
            target_indices, donor_indices = groups[target_id], groups[donor_id]
            if len(target_indices) != len(donor_indices):
                raise AssertionError("trial sham unit counts changed")
            trial[target_indices] = values[donor_indices]

    unit = np.empty_like(values)
    channel = np.empty_like(values)
    for record_id in sorted(groups):
        indices = groups[record_id]
        unit_perm = sattolo_cycle(len(indices), seed_parts=(seed, "within_trial_unit_assignment_shuffle", partition, record_id))
        unit[indices] = values[np.asarray(indices)[unit_perm]]
        channel_perm = sattolo_cycle(105, seed_parts=(seed, "channel_block_permutation", partition, record_id))
        blocks = values[indices].reshape(len(indices), 105, 8)
        channel[indices] = blocks[:, channel_perm, :].reshape(len(indices), FEATURE_DIM)
    result = {
        "real": values,
        "trial_shuffle": trial,
        "within_trial_unit_assignment_shuffle": unit,
        "channel_block_permutation": channel,
    }
    if len({array.shape for array in result.values()}) != 1 or any(not np.isfinite(array).all() for array in result.values()):
        raise AssertionError("synthetic sham capacity/finite contract failed")
    return result


@dataclass
class RidgeModel:
    weights: Tensor
    intercept: Tensor


def _fit_ridge_models(x_by_arm: Mapping[str, np.ndarray], y: np.ndarray, *, device: str) -> dict[str, RidgeModel]:
    names = ARM_NAMES
    stack = torch.as_tensor(np.stack([x_by_arm[name] for name in names]), dtype=torch.float32, device=device)
    target = torch.as_tensor(np.asarray(y, dtype=np.float32), dtype=torch.float32, device=device)
    x_mean = stack.mean(dim=1)
    y_mean = target.mean(dim=0)
    centered_x = stack - x_mean[:, None, :]
    centered_y = target - y_mean
    gram = torch.matmul(centered_x.transpose(1, 2), centered_x)
    identity = torch.eye(gram.shape[-1], dtype=gram.dtype, device=gram.device)
    gram = gram + identity[None, :, :]
    rhs = torch.matmul(centered_x.transpose(1, 2), centered_y[None, :, :].expand(len(names), -1, -1))
    cholesky, info = torch.linalg.cholesky_ex(gram)
    if bool((info != 0).any()):
        raise RuntimeError("synthetic ridge Cholesky failed")
    weights = torch.cholesky_solve(rhs, cholesky)
    intercept = y_mean[None, :] - torch.einsum("ad,ado->ao", x_mean, weights)
    residual = torch.matmul(gram, weights) - rhs
    relative = residual.norm(dim=(1, 2)) / rhs.norm(dim=(1, 2)).clamp_min(1e-8)
    if not bool(torch.isfinite(relative).all()) or float(relative.max()) > 2e-3:
        raise RuntimeError(f"synthetic ridge residual failed: {relative.tolist()}")
    models = {name: RidgeModel(weights[index].detach(), intercept[index].detach()) for index, name in enumerate(names)}
    h_intercept = target.mean(dim=0)
    models["H_only"] = RidgeModel(torch.zeros((FEATURE_DIM, TEXT_DIM), device=device), h_intercept.detach())
    return models


def _ridge_logp(
    model: RidgeModel,
    x: np.ndarray,
    vocabulary: np.ndarray,
    true_positions: np.ndarray,
    *,
    device: str,
    batch_size: int = 4096,
) -> np.ndarray:
    values = np.asarray(x, dtype=np.float32)
    vocab = torch.as_tensor(np.asarray(vocabulary, dtype=np.float32), device=device)
    positions = np.asarray(true_positions, dtype=np.int64)
    output: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(values), batch_size):
            batch = torch.as_tensor(values[start : start + batch_size], device=device)
            query = F.normalize(batch @ model.weights + model.intercept, dim=1)
            logits = query @ vocab.T / 0.07
            pos = torch.as_tensor(positions[start : start + batch_size], dtype=torch.long, device=device)
            row = torch.arange(len(pos), device=device)
            logp = logits[row, pos] - torch.logsumexp(logits, dim=1)
            output.append(logp.cpu().numpy().astype(np.float64))
    result = np.concatenate(output)
    if not np.isfinite(result).all():
        raise RuntimeError("synthetic ridge logp is nonfinite")
    return result


@dataclass
class ProbeBundle:
    models: Mapping[str, RidgeModel]
    normalizer: Mapping[str, np.ndarray]
    vocabulary: np.ndarray
    train_items: np.ndarray


def _score_probe_bundle(
    bundle: ProbeBundle,
    partition: Mapping[str, Any],
    *,
    seed: int,
    partition_name: str,
    device: str,
) -> dict[str, np.ndarray]:
    selected = np.arange(len(partition["item_indices"]), dtype=np.int64)
    normalized = transform_fold_normalizer(partition["item_features"], bundle.normalizer)
    arms = _synthetic_shams(normalized, _metadata(partition, selected), seed=seed, partition=partition_name)
    positions = np.asarray(partition["item_indices"], dtype=np.int64)
    result = {
        name: _ridge_logp(bundle.models[name], normalized if name == "H_only" else arms[name], bundle.vocabulary, positions, device=device)
        for name in ALL_ARMS
    }
    result.update(u_statistics(result["real"], {name: result[name] for name in ARM_NAMES[1:]}))
    return result


def measurement_path(
    scenario: Any, *, device: str, include_final_test: bool
) -> tuple[dict[str, Any], ProbeBundle, list[dict[str, Any]], int]:
    train = flatten_partition(scenario, "train")
    selection = flatten_partition(scenario, "selection")
    test = flatten_partition(scenario, "final_test") if include_final_test else None
    count = len(train["item_indices"])
    cross_logp = {name: np.full(count, np.nan, dtype=np.float64) for name in ALL_ARMS}
    ledgers: list[dict[str, Any]] = []
    ridge_fit_count = 0
    train_items = np.asarray(ITEM_SPLITS["train"], dtype=np.int64)
    train_vocabulary = scenario.item_text_embeddings[train_items]
    train_position = np.full(120, -1, dtype=np.int64)
    train_position[train_items] = np.arange(len(train_items))

    item_subjects = np.asarray(train["item_subjects"], dtype=np.int64)
    item_indices = np.asarray(train["item_indices"], dtype=np.int64)
    subject_fold = scenario.subject_folds[item_subjects]
    item_fold = scenario.item_folds[item_indices]
    for held_subject_fold in (0, 1):
        for held_item_fold in (0, 1):
            fit_mask = (subject_fold != held_subject_fold) & (item_fold != held_item_fold)
            score_mask = (subject_fold == held_subject_fold) & (item_fold == held_item_fold)
            fit_index, score_index = np.flatnonzero(fit_mask), np.flatnonzero(score_mask)
            normalizer, _ = fit_fold_normalizer(train["item_features"][fit_index])
            fit_normalized = transform_fold_normalizer(train["item_features"][fit_index], normalizer)
            score_normalized = transform_fold_normalizer(train["item_features"][score_index], normalizer)
            scope = f"crossfit_s{held_subject_fold}_i{held_item_fold}"
            fit_arms = _synthetic_shams(fit_normalized, _metadata(train, fit_index), seed=scenario.replicate_seed, partition=f"{scope}|fit")
            score_arms = _synthetic_shams(score_normalized, _metadata(train, score_index), seed=scenario.replicate_seed, partition=f"{scope}|score")
            y_fit = scenario.item_text_embeddings[item_indices[fit_index]]
            models = _fit_ridge_models(fit_arms, y_fit, device=device)
            ridge_fit_count += 5
            true_positions = train_position[item_indices[score_index]]
            for arm in ALL_ARMS:
                x_score = score_normalized if arm == "H_only" else score_arms[arm]
                cross_logp[arm][score_index] = _ridge_logp(models[arm], x_score, train_vocabulary, true_positions, device=device)
                fit_id = f"{scenario.scenario_id}|measurement|{scope}|arm={arm}"
                ledgers.append(build_synthetic_v5_ledger(
                    fit_id=fit_id,
                    scenario_id=scenario.scenario_id,
                    fit_ids=[train["observation_ids"][index] for index in fit_index],
                    selection_ids=[train["observation_ids"][index] for index in score_index],
                    generator_hash=scenario.feature_sha256,
                    scope=f"measurement|{scope}|{arm}",
                ))
    if any(not np.isfinite(values).all() for values in cross_logp.values()):
        raise RuntimeError("cross-fitting did not score every train observation exactly once")
    cross_logp.update(u_statistics(cross_logp["real"], {name: cross_logp[name] for name in ARM_NAMES[1:]}))

    all_index = np.arange(count, dtype=np.int64)
    normalizer, normalizer_summary = fit_fold_normalizer(train["item_features"])
    train_normalized = transform_fold_normalizer(train["item_features"], normalizer)
    train_arms = _synthetic_shams(train_normalized, _metadata(train, all_index), seed=scenario.replicate_seed, partition="train_final_fit")
    models = _fit_ridge_models(train_arms, scenario.item_text_embeddings[item_indices], device=device)
    ridge_fit_count += 5
    bundle = ProbeBundle(models=models, normalizer=normalizer, vocabulary=scenario.item_text_embeddings, train_items=train_items)
    selection_scores = _score_probe_bundle(bundle, selection, seed=scenario.replicate_seed, partition_name="selection", device=device)
    test_scores = None
    if include_final_test:
        assert test is not None
        test_scores = _score_probe_bundle(bundle, test, seed=scenario.replicate_seed, partition_name="final_test", device=device)
    for arm in ALL_ARMS:
        ledgers.append(build_synthetic_v5_ledger(
            fit_id=f"{scenario.scenario_id}|measurement|train_final|arm={arm}",
            scenario_id=scenario.scenario_id,
            fit_ids=train["observation_ids"],
            selection_ids=selection["observation_ids"],
            final_test_ids=test["observation_ids"] if include_final_test and test is not None else (),
            generator_hash=scenario.feature_sha256,
            scope=f"measurement|train_final|{arm}",
        ))
    if ridge_fit_count != 25 or len(ledgers) != 25:
        raise AssertionError("per-scenario ridge/V5 accounting is not 25")

    null = np.concatenate([
        cross_logp["trial_shuffle"] - cross_logp["within_trial_unit_assignment_shuffle"],
        cross_logp["trial_shuffle"] - cross_logp["channel_block_permutation"],
        cross_logp["within_trial_unit_assignment_shuffle"] - cross_logp["channel_block_permutation"],
    ])
    delta = float(np.quantile(null, 0.95))
    u_min = cross_logp["u_min"]
    per_item_subject: dict[int, dict[int, float]] = {}
    for item in ITEM_SPLITS["train"]:
        per_item_subject[item] = {}
        for subject in SUBJECT_SPLITS["train"]:
            mask = (item_indices == item) & (item_subjects == subject)
            per_item_subject[item][subject] = float(u_min[mask].mean()) if bool(mask.any()) else float("nan")
    gate = np.zeros(120, dtype=np.float32)
    for item in ITEM_SPLITS["train"]:
        values = np.asarray([value for value in per_item_subject[item].values() if np.isfinite(value)])
        gate[item] = max(float(np.median(values)) - delta, 0.0) if values.size else 0.0

    measurement = {
        "train_crossfit": cross_logp,
        "selection": selection_scores,
        "test": test_scores,
        "delta_sham_sham_q95": delta,
        "gate": gate,
        "normalizer_summary": normalizer_summary,
        "final_test_read_events": 1 if include_final_test else 0,
    }
    return measurement, bundle, ledgers, ridge_fit_count


class AlignmentProjection(nn.Module):
    def __init__(self, initial: Tensor) -> None:
        super().__init__()
        self.weight = nn.Parameter(initial.clone())

    def forward(self, features: Tensor) -> Tensor:
        return F.normalize(features @ self.weight, dim=1)


def _batch_schedule(seed: int, count: int, steps: int, batch_size: int) -> list[np.ndarray]:
    rng = np.random.default_rng(stable_seed(seed, "v3.20", "alignment_batch_order", count))
    schedule: list[np.ndarray] = []
    pool = np.empty(0, dtype=np.int64)
    while len(schedule) < steps:
        if len(pool) < batch_size:
            pool = np.concatenate([pool, rng.permutation(count)])
        schedule.append(pool[:batch_size].copy())
        pool = pool[batch_size:]
    return schedule


def _infonce_per_row(query: Tensor, target: Tensor) -> Tensor:
    logits = query @ target.T / 0.07
    labels = torch.arange(len(query), device=query.device)
    return F.cross_entropy(logits, labels, reduction="none")


def _retrieval_metrics(
    projection: Tensor,
    partition: Mapping[str, Any],
    candidates: np.ndarray,
    *,
    device: str,
) -> dict[str, Any]:
    x = torch.as_tensor(np.asarray(partition["sentence_features"], dtype=np.float32), device=device)
    targets = torch.as_tensor(np.asarray(partition["sentence_text"], dtype=np.float32), device=device)
    candidate_tensor = torch.as_tensor(candidates, dtype=torch.long, device=device)
    with torch.no_grad():
        query = F.normalize(x @ projection, dim=1)
        candidate_targets = targets[candidate_tensor]
        scores = torch.einsum("nd,nkd->nk", query, candidate_targets)
        target_position = (candidate_tensor == torch.arange(len(x), device=device)[:, None]).nonzero(as_tuple=False)[:, 1]
        order = scores.argsort(dim=1, descending=True)
        rank = (order == target_position[:, None]).nonzero(as_tuple=False)[:, 1] + 1
        r1 = (rank == 1).float().cpu().numpy()
        mrr = (1.0 / rank.float()).cpu().numpy()
    subjects = np.asarray(partition["sentence_subjects"], dtype=np.int64)
    subject_r1 = {str(subject): float(r1[subjects == subject].mean()) for subject in sorted(set(subjects.tolist()))}
    subject_mrr = {str(subject): float(mrr[subjects == subject].mean()) for subject in sorted(set(subjects.tolist()))}
    return {
        "R_at_1_N10": float(np.mean(list(subject_r1.values()))),
        "MRR_at_10": float(np.mean(list(subject_mrr.values()))),
        "subject_R_at_1_N10": subject_r1,
        "subject_MRR_at_10": subject_mrr,
    }


@dataclass
class AlignmentFit:
    fit_id: str
    method: str
    variant: str
    complexity: tuple[Any, ...]
    projection: Tensor
    selection: Mapping[str, Any]
    warmup_steps: int
    eq_model: EQANMAModel | None = None


def _fit_direct(
    *,
    fit_id: str,
    initial: Tensor,
    train_x: Tensor,
    train_y: Tensor,
    sentence_scores: Tensor,
    item_mask: Tensor,
    gate_items: Tensor | None,
    gamma: float,
    warmup_steps: int,
    schedule: Sequence[np.ndarray],
    selection: Mapping[str, Any],
    selection_candidates: np.ndarray,
    device: str,
) -> AlignmentFit:
    model = AlignmentProjection(initial).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    for step, index in enumerate(schedule):
        batch = torch.as_tensor(index, dtype=torch.long, device=device)
        gate = None if gate_items is None else gate_items[batch]
        weights = direct_u_plus_weights(
            sentence_scores[batch], item_mask[batch], gamma=gamma, gate=gate, step=step, warmup_steps=warmup_steps
        ).weights
        loss = (weights * _infonce_per_row(model(train_x[batch]), train_y[batch])).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    projection = model.weight.detach().clone()
    metrics = _retrieval_metrics(projection, selection, selection_candidates, device=device)
    return AlignmentFit(
        fit_id=fit_id,
        method="gated_direct" if gate_items is not None else "direct",
        variant=fit_id.split("|alignment|")[-1],
        complexity=(),
        projection=projection,
        selection=metrics,
        warmup_steps=warmup_steps,
    )


def _fit_uniform(
    *, initial: Tensor, train_x: Tensor, train_y: Tensor, schedule: Sequence[np.ndarray], selection: Mapping[str, Any], selection_candidates: np.ndarray, scenario_id: str, device: str
) -> AlignmentFit:
    model = AlignmentProjection(initial).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    for index in schedule:
        batch = torch.as_tensor(index, dtype=torch.long, device=device)
        loss = _infonce_per_row(model(train_x[batch]), train_y[batch]).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    projection = model.weight.detach().clone()
    return AlignmentFit(
        fit_id=f"{scenario_id}|alignment|uniform",
        method="uniform",
        variant="uniform",
        complexity=(0,),
        projection=projection,
        selection=_retrieval_metrics(projection, selection, selection_candidates, device=device),
        warmup_steps=0,
    )


def _fit_eq(
    *,
    scenario: Any,
    variant: str,
    lambda_m: float,
    initial: Tensor,
    train_x: Tensor,
    train_y: Tensor,
    sentence_items: Tensor,
    observations: Tensor,
    u_oof: Tensor,
    gate: Tensor,
    text_embeddings: Tensor,
    schedule: Sequence[np.ndarray],
    selection: Mapping[str, Any],
    selection_candidates: np.ndarray,
    device: str,
) -> AlignmentFit:
    measurement_seed = stable_seed(scenario.replicate_seed, "v3.20", "measurement_initialization", scenario.regime, scenario.alpha)
    eq = EQANMAModel(variant=variant, lambda_m=lambda_m, seed=measurement_seed).to(device)
    projection_model = AlignmentProjection(initial).to(device)
    optimizer = torch.optim.Adam(list(projection_model.parameters()) + list(eq.parameters()), lr=0.003)
    rankfit: list[tuple[int, float]] = []
    plateau: int | None = None
    mask_all = torch.ones_like(sentence_items, dtype=torch.bool)
    for step, index in enumerate(schedule):
        batch = torch.as_tensor(index, dtype=torch.long, device=device)
        warmup = len(schedule) if plateau is None else plateau
        output = eq(
            train_x[batch], text_embeddings, sentence_items[batch], mask_all[batch], observations[batch], u_oof[batch], gate,
            reference_features=train_x, step=step, warmup_steps=warmup,
        )
        align = _infonce_per_row(projection_model(train_x[batch]), train_y[batch])
        loss = (output.weights * align).mean() + float(lambda_m) * output.measurement_loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if (step + 1) % 4 == 0:
            rankfit.append((step + 1, spearman(output.p.detach(), observations[batch].detach())))
            plateau = rankfit_plateau_step(rankfit)
    warmup_steps = len(schedule) if plateau is None else int(plateau)
    projection = projection_model.weight.detach().clone()
    fit_id = f"{scenario.scenario_id}|alignment|{variant}|lambda_m={lambda_m:g}"
    return AlignmentFit(
        fit_id=fit_id,
        method=variant,
        variant=f"{variant}|lambda_m={lambda_m:g}",
        complexity=(float(lambda_m), fit_id),
        projection=projection,
        selection=_retrieval_metrics(projection, selection, selection_candidates, device=device),
        warmup_steps=warmup_steps,
        eq_model=eq,
    )


def _select(fits: Sequence[AlignmentFit]) -> AlignmentFit:
    if not fits:
        raise ValueError("selection requires candidates")
    return sorted(
        fits,
        key=lambda fit: (-float(fit.selection["R_at_1_N10"]), fit.complexity, fit.fit_id),
    )[0]


def _recovery(values: np.ndarray, oracle: np.ndarray) -> dict[str, float]:
    x = np.asarray(values, dtype=np.float64).reshape(-1)
    y = np.asarray(oracle, dtype=np.float64).reshape(-1)
    x_norm = x / max(float(x.mean()), 1e-8)
    y_norm = y / max(float(y.mean()), 1e-8)
    threshold_x = np.quantile(x, 0.75)
    threshold_y = np.quantile(y, 0.75)
    top_x, top_y = x >= threshold_x, y >= threshold_y
    union = int(np.count_nonzero(top_x | top_y))
    return {
        "spearman": spearman(x, y),
        "normalized_absolute_error": float(np.mean(np.abs(x_norm - y_norm))),
        "top_quartile_overlap": float(np.count_nonzero(top_x & top_y) / union) if union else 1.0,
    }


def alignment_path(
    scenario: Any,
    measurement: Mapping[str, Any],
    *,
    device: str,
    include_final_test: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    train = flatten_partition(scenario, "train")
    selection = flatten_partition(scenario, "selection")
    test = flatten_partition(scenario, "final_test") if include_final_test else None
    train_x = torch.as_tensor(train["sentence_features"], dtype=torch.float32, device=device)
    train_y = torch.as_tensor(train["sentence_text"], dtype=torch.float32, device=device)
    sentence_items = torch.as_tensor(train["sentence_items"], dtype=torch.long, device=device)
    train_u = np.asarray(measurement["train_crossfit"]["u_oof"], dtype=np.float32).reshape(-1, ITEMS_PER_SENTENCE)
    train_u_min = np.asarray(measurement["train_crossfit"]["u_min"], dtype=np.float32).reshape(-1, ITEMS_PER_SENTENCE)
    u_tensor = torch.as_tensor(train_u, device=device)
    u_min_tensor = torch.as_tensor(train_u_min, device=device)
    tau = max(float(np.std(train_u, ddof=0)), 1e-8)
    observations = contribution_soft_response(u_tensor, tau=tau)
    gate = torch.as_tensor(np.asarray(measurement["gate"], dtype=np.float32), device=device)
    gate_items = gate[sentence_items]
    text = torch.as_tensor(scenario.item_text_embeddings, dtype=torch.float32, device=device)
    initial_rng = np.random.default_rng(stable_seed(scenario.replicate_seed, "v3.20", "alignment_initialization", scenario.regime, scenario.alpha))
    initial = torch.as_tensor(initial_rng.normal(0.0, 0.02, (FEATURE_DIM, TEXT_DIM)).astype(np.float32), device=device)
    schedule = _batch_schedule(stable_seed(scenario.replicate_seed, scenario.regime, scenario.alpha), len(train_x), 32, 64)
    selection_candidates = candidate_sets(scenario.replicate_seed, "selection")
    all_fits: list[AlignmentFit] = []

    eq_by_variant: dict[str, list[AlignmentFit]] = {variant: [] for variant in ("V0", "V1", "V2")}
    for variant in ("V0", "V1", "V2"):
        for lambda_m in LAMBDA_M_GRID:
            fit = _fit_eq(
                scenario=scenario, variant=variant, lambda_m=lambda_m, initial=initial, train_x=train_x, train_y=train_y,
                sentence_items=sentence_items, observations=observations, u_oof=u_tensor, gate=gate,
                text_embeddings=text, schedule=schedule, selection=selection, selection_candidates=selection_candidates, device=device,
            )
            eq_by_variant[variant].append(fit)
            all_fits.append(fit)
    matched_warmup = max(fit.warmup_steps for fit in eq_by_variant["V1"])

    uniform = _fit_uniform(
        initial=initial, train_x=train_x, train_y=train_y, schedule=schedule, selection=selection,
        selection_candidates=selection_candidates, scenario_id=scenario.scenario_id, device=device,
    )
    all_fits.append(uniform)
    direct_fits: list[AlignmentFit] = []
    gated_fits: list[AlignmentFit] = []
    for gamma in GAMMA_GRID:
        for score_name, score_tensor in (("u_oof", u_tensor), ("u_min", u_min_tensor)):
            for warmup_name in WARMUP_VERSIONS:
                warmup = 0 if warmup_name == "none" else matched_warmup
                suffix = f"gamma={gamma:g}|score={score_name}|warmup={warmup_name}"
                for gated, collection in ((False, direct_fits), (True, gated_fits)):
                    prefix = "gated_direct" if gated else "direct"
                    fit = _fit_direct(
                        fit_id=f"{scenario.scenario_id}|alignment|{prefix}|{suffix}", initial=initial, train_x=train_x, train_y=train_y,
                        sentence_scores=score_tensor, item_mask=torch.ones_like(sentence_items, dtype=torch.bool),
                        gate_items=gate_items if gated else None, gamma=gamma, warmup_steps=warmup, schedule=schedule,
                        selection=selection, selection_candidates=selection_candidates, device=device,
                    )
                    fit.complexity = (
                        0 if warmup_name == "none" else 1,
                        0 if score_name == "u_oof" else 1,
                        abs(math.log2(gamma)),
                        fit.fit_id,
                    )
                    collection.append(fit)
                    all_fits.append(fit)
    if len(all_fits) != 37:
        raise AssertionError("per-scenario alignment fit accounting is not 37")

    selected = {
        "uniform": uniform,
        "direct": _select(direct_fits),
        "gated_direct": _select(gated_fits),
        "V0": _select(eq_by_variant["V0"]),
        "V1": _select(eq_by_variant["V1"]),
        "V2": _select(eq_by_variant["V2"]),
    }
    choices = {name: fit.fit_id for name, fit in selected.items()}
    final_metrics: dict[str, Any] = {}
    if include_final_test:
        assert test is not None
        final_candidates = candidate_sets(scenario.replicate_seed, "final_test")
        # This is the single batched final-test read event, after choices freeze.
        for name, fit in selected.items():
            final_metrics[name] = _retrieval_metrics(fit.projection, test, final_candidates, device=device)

    ledgers = [
        build_synthetic_v5_ledger(
            fit_id=fit.fit_id,
            scenario_id=scenario.scenario_id,
            fit_ids=train["sentence_ids"],
            selection_ids=selection["sentence_ids"],
            final_test_ids=test["sentence_ids"] if include_final_test and test is not None and fit.fit_id in set(choices.values()) else (),
            generator_hash=scenario.feature_sha256,
            scope=f"alignment|{fit.method}|{fit.variant}",
        )
        for fit in all_fits
    ]

    diagnostics: dict[str, Any] = {}
    if include_final_test:
        v1 = selected["V1"]
        assert v1.eq_model is not None and test is not None
        with torch.no_grad():
            alpha_hat, b_hat, a_hat = v1.eq_model.item_parameters(text)
            test_x = torch.as_tensor(test["sentence_features"], dtype=torch.float32, device=device)
            q_hat = v1.eq_model.trial_q(test_x, reference_features=train_x).cpu().numpy()
        test_items = np.asarray(ITEM_SPLITS["final_test"], dtype=np.int64)
        q_true = np.repeat(scenario.truth.q[np.asarray(SUBJECT_SPLITS["final_test"])], SENTENCES_PER_SUBJECT)
        rho_a = spearman(a_hat[test_items].cpu(), scenario.truth.a[test_items])
        rho_b = spearman(b_hat[test_items].cpu(), scenario.truth.b[test_items])
        rho_q = spearman(q_hat, q_true)

        v1.eq_model.eval()
        with torch.no_grad():
            v1_weights_out = v1.eq_model(
                train_x, text, sentence_items, torch.ones_like(sentence_items, dtype=torch.bool), observations, u_tensor, gate,
                reference_features=train_x, step=32, warmup_steps=v1.warmup_steps,
            )
        v1_weights = v1_weights_out.weights.cpu().numpy()
        direct_fit = selected["direct"]
        gated_fit = selected["gated_direct"]
        def parse_direct(fit: AlignmentFit, gated: bool) -> tuple[np.ndarray, Any]:
            parts = {piece.split("=", 1)[0]: piece.split("=", 1)[1] for piece in fit.fit_id.split("|") if "=" in piece and piece.split("=", 1)[0] in {"gamma", "score", "warmup"}}
            source = u_tensor if parts["score"] == "u_oof" else u_min_tensor
            output = direct_u_plus_weights(
                source, torch.ones_like(sentence_items, dtype=torch.bool), gamma=float(parts["gamma"]),
                gate=gate_items if gated else None, step=32, warmup_steps=matched_warmup if parts["warmup"] == "EQ_matched" else 0,
            )
            return output.weights.cpu().numpy(), output
        direct_weights, direct_output = parse_direct(direct_fit, False)
        gated_weights, gated_output = parse_direct(gated_fit, True)
        oracle = scenario.truth.oracle_sentence_budget[np.asarray(SUBJECT_SPLITS["train"])].reshape(-1)
        stable = scenario.truth.stable_mask[np.asarray(ITEM_SPLITS["train"])]
        predicted_stable = np.asarray(measurement["gate"])[np.asarray(ITEM_SPLITS["train"])] > 0
        tp = int(np.count_nonzero(stable & predicted_stable))
        fp = int(np.count_nonzero(~stable & predicted_stable))
        fn = int(np.count_nonzero(stable & ~predicted_stable))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        item_counts = np.bincount(np.asarray(train["item_indices"]), minlength=120)
        frequency = item_counts[np.asarray(train["sentence_items"])].mean(axis=1)
        length = np.full(len(frequency), 4.0)
        surprisal = -np.log(np.maximum(frequency, 1.0))
        diagnostics = {
            "parameter_recovery": {"rho_a": rho_a, "rho_b": rho_b, "rho_q": rho_q, "scope": "joint_heldout_subjects_items"},
            "oracle_weight_recovery": {
                "V1": _recovery(v1_weights, oracle),
                "direct": _recovery(direct_weights, oracle),
                "gated_direct": _recovery(gated_weights, oracle),
                "scope": "train_crossfit_steady_state_final_diagnostic",
            },
            "gate_recovery": {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "scope": "train_items_final_diagnostic"},
            "dispersion": {
                "V1": weight_diagnostics(torch.as_tensor(v1_weights)),
                "direct": weight_diagnostics(torch.as_tensor(direct_weights)),
                "gated_direct": weight_diagnostics(torch.as_tensor(gated_weights)),
            },
            "floor_all_zero": {
                "V1_floor_rate": float(v1_weights_out.floor_hit.float().mean().cpu()),
                "V1_all_zero": bool(v1_weights_out.all_zero_batch),
                "direct_floor_rate": float(direct_output.floor_hit.float().mean().cpu()),
                "direct_all_zero": bool(direct_output.all_zero_batch),
                "gated_direct_floor_rate": float(gated_output.floor_hit.float().mean().cpu()),
                "gated_direct_all_zero": bool(gated_output.all_zero_batch),
            },
            "partial_correlations": {
                "length_constant_by_contract": True,
                "V1_frequency_given_surprisal": partial_spearman(v1_weights, frequency, [surprisal]),
                "direct_frequency_given_surprisal": partial_spearman(direct_weights, frequency, [surprisal]),
                "gated_direct_frequency_given_surprisal": partial_spearman(gated_weights, frequency, [surprisal]),
                "length": 0.0,
            },
        }
    return {
        "selection_choices": choices,
        "selection_metrics": {fit.fit_id: dict(fit.selection) for fit in all_fits},
        "selected_final_test": final_metrics,
        "matched_warmup_steps": matched_warmup,
        "diagnostics": diagnostics,
        "final_test_read_events": 1 if include_final_test else 0,
    }, ledgers, len(all_fits)


def _test_measurement_summary(test_scores: Mapping[str, np.ndarray], test_partition: Mapping[str, Any]) -> dict[str, Any]:
    subjects = np.asarray(test_partition["item_subjects"], dtype=np.int64)
    metrics = ("u_oof", "u_min", "real_minus_trial_shuffle", "real_minus_within_trial_unit_assignment_shuffle", "real_minus_channel_block_permutation")
    return {
        metric: {str(subject): float(np.asarray(test_scores[metric])[subjects == subject].mean()) for subject in SUBJECT_SPLITS["final_test"]}
        for metric in metrics
    }


def run_scenario(scenario: Any, *, device: str, include_final_test: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started = time.perf_counter()
    measurement, _, measurement_ledgers, ridge_count = measurement_path(scenario, device=device, include_final_test=include_final_test)
    alignment, alignment_ledgers, alignment_count = alignment_path(scenario, measurement, device=device, include_final_test=include_final_test)
    if ridge_count != 25 or alignment_count != 37:
        raise AssertionError("scenario accounting failed")
    result: dict[str, Any] = {
        "scenario_id": scenario.scenario_id,
        "replicate_seed": scenario.replicate_seed,
        "regime": scenario.regime,
        "alpha": scenario.alpha,
        "feature_sha256": scenario.feature_sha256,
        "ridge_fits": ridge_count,
        "alignment_fits": alignment_count,
        "total_fits": ridge_count + alignment_count,
        "v5_ledgers": len(measurement_ledgers) + len(alignment_ledgers),
        "selection_final_isolation": {
            "selection_subject_item_disjoint": True,
            "final_subject_item_disjoint": True,
            "final_test_read_events": 1 if include_final_test else 0,
            "all_choices_frozen_before_final_read": include_final_test,
        },
        "alignment": alignment,
        "elapsed_seconds": time.perf_counter() - started,
    }
    if include_final_test:
        test = flatten_partition(scenario, "final_test")
        result["measurement_final_test_subjects"] = _test_measurement_summary(measurement["test"], test)
        result["delta_sham_sham_q95"] = measurement["delta_sham_sham_q95"]
    ledgers = measurement_ledgers + alignment_ledgers
    if len(ledgers) != 62 or len({row["fit_id"] for row in ledgers}) != 62:
        raise AssertionError("scenario synthetic V5 IDs are not 62 unique fits")
    return result, ledgers


def _bootstrap(values: Sequence[float], *, seed_parts: Sequence[object]) -> dict[str, Any]:
    vector = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(stable_seed(*seed_parts))
    index = rng.integers(0, len(vector), size=(BOOTSTRAP_RESAMPLES, len(vector)))
    draws = vector[index].mean(axis=1)
    return {
        "estimate": float(vector.mean()),
        "ci95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
        "positive_replicates": int(np.count_nonzero(vector > 0)),
        "replicate_values": [float(value) for value in vector],
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
    }


def summarize(scenarios: Sequence[Mapping[str, Any]], *, contract_hash: str, ledger_hash: str) -> dict[str, Any]:
    curves: dict[str, dict[str, Any]] = {regime: {} for regime in REGIMES}
    by_key = {(row["regime"], float(row["alpha"]), int(row["replicate_seed"])): row for row in scenarios}
    for regime in REGIMES:
        for alpha in ALPHAS:
            rows = [by_key[(regime, alpha, seed)] for seed in REPLICATE_SEEDS]
            measurement: dict[str, Any] = {}
            for metric in ("u_oof", "u_min", "real_minus_trial_shuffle", "real_minus_within_trial_unit_assignment_shuffle", "real_minus_channel_block_permutation"):
                replicate = [float(np.mean(list(row["measurement_final_test_subjects"][metric].values()))) for row in rows]
                measurement[metric] = _bootstrap(replicate, seed_parts=(20260813, "v3.20", regime, alpha, metric))
            family = (
                measurement["u_oof"]["ci95"][0] > 0
                and measurement["u_oof"]["positive_replicates"] >= 10
                and all(measurement[name]["estimate"] > 0 for name in measurement if name.startswith("real_minus_"))
            )
            methods: dict[str, Any] = {}
            for method in ("uniform", "direct", "gated_direct", "V0", "V1", "V2"):
                r1 = [float(row["alignment"]["selected_final_test"][method]["R_at_1_N10"]) for row in rows]
                mrr = [float(row["alignment"]["selected_final_test"][method]["MRR_at_10"]) for row in rows]
                methods[method] = {
                    "R_at_1_N10": _bootstrap(r1, seed_parts=(20260813, "v3.20", regime, alpha, method, "R1")),
                    "MRR_at_10": _bootstrap(mrr, seed_parts=(20260813, "v3.20", regime, alpha, method, "MRR")),
                }
            contrasts: dict[str, Any] = {}
            for right in ("direct", "gated_direct"):
                values = [
                    float(row["alignment"]["selected_final_test"]["V1"]["R_at_1_N10"])
                    - float(row["alignment"]["selected_final_test"][right]["R_at_1_N10"])
                    for row in rows
                ]
                contrasts[f"V1_minus_{right}"] = _bootstrap(values, seed_parts=(20260813, "v3.20", regime, alpha, "V1", right))
            v2_values = [
                float(row["alignment"]["selected_final_test"]["V2"]["R_at_1_N10"])
                - float(row["alignment"]["selected_final_test"]["direct"]["R_at_1_N10"])
                for row in rows
            ]
            contrasts["V2_minus_direct"] = _bootstrap(v2_values, seed_parts=(20260813, "v3.20", regime, alpha, "V2", "direct"))
            recovery: dict[str, Any] = {}
            for parameter in ("rho_a", "rho_b", "rho_q"):
                values = [float(row["alignment"]["diagnostics"]["parameter_recovery"][parameter]) for row in rows]
                recovery[parameter] = {"median": float(np.median(values)), "replicate_values": values}
            oracle: dict[str, Any] = {}
            for method in ("V1", "direct", "gated_direct"):
                values = [float(row["alignment"]["diagnostics"]["oracle_weight_recovery"][method]["spearman"]) for row in rows]
                oracle[method] = _bootstrap(values, seed_parts=(20260813, "v3.20", regime, alpha, "oracle", method))
            oracle_diff: dict[str, Any] = {}
            for right in ("direct", "gated_direct"):
                values = [
                    float(row["alignment"]["diagnostics"]["oracle_weight_recovery"]["V1"]["spearman"])
                    - float(row["alignment"]["diagnostics"]["oracle_weight_recovery"][right]["spearman"])
                    for row in rows
                ]
                oracle_diff[f"V1_minus_{right}"] = _bootstrap(values, seed_parts=(20260813, "v3.20", regime, alpha, "oracle", right))
            gate_values = [float(row["alignment"]["diagnostics"]["gate_recovery"]["f1"]) for row in rows]
            structured_advantage = bool(
                regime == "STRUCTURED_FISHER"
                and family
                and contrasts["V1_minus_direct"]["estimate"] >= 0.01
                and contrasts["V1_minus_direct"]["ci95"][0] > 0
                and contrasts["V1_minus_direct"]["positive_replicates"] >= 10
                and contrasts["V1_minus_gated_direct"]["ci95"][0] > 0
                and contrasts["V1_minus_gated_direct"]["positive_replicates"] >= 10
                and oracle_diff["V1_minus_direct"]["ci95"][0] > 0
                and oracle_diff["V1_minus_gated_direct"]["ci95"][0] > 0
                and all(recovery[name]["median"] >= 0.70 for name in recovery)
                and np.sign(contrasts["V1_minus_direct"]["estimate"]) == np.sign(contrasts["V2_minus_direct"]["estimate"])
            )
            curves[regime][f"{alpha:g}"] = {
                "measurement": measurement,
                "family_detected": bool(family),
                "methods": methods,
                "contrasts": contrasts,
                "parameter_recovery": recovery,
                "oracle_weight_recovery": oracle,
                "oracle_weight_contrasts": oracle_diff,
                "gate_recovery_f1": {"median": float(np.median(gate_values)), "replicate_values": gate_values},
                "structured_advantage": structured_advantage,
            }

    alpha_star: float | None = None
    for index, alpha in enumerate(ALPHAS[1:-1], start=1):
        current = curves["STRUCTURED_FISHER"][f"{alpha:g}"]["structured_advantage"]
        next_value = curves["STRUCTURED_FISHER"][f"{ALPHAS[index + 1]:g}"]["structured_advantage"]
        if current and next_value:
            alpha_star = float(alpha)
            break
    alpha0 = curves["STRUCTURED_FISHER"]["0"]["contrasts"]["V1_minus_direct"]
    alpha0_pass = alpha0["ci95"][0] <= 0 <= alpha0["ci95"][1] and abs(alpha0["estimate"]) < 0.01
    monotone_positive = [curves["MONOTONE_DIRECT"][f"{alpha:g}"]["contrasts"]["V1_minus_direct"]["ci95"][0] > 0 for alpha in ALPHAS]
    monotone_consecutive = any(monotone_positive[index] and monotone_positive[index + 1] for index in range(len(ALPHAS) - 1))
    detected_monotone = [curves["MONOTONE_DIRECT"][f"{alpha:g}"] for alpha in ALPHAS if curves["MONOTONE_DIRECT"][f"{alpha:g}"]["family_detected"]]
    direct_systematically_lower = bool(detected_monotone) and all(
        row["oracle_weight_recovery"]["direct"]["estimate"] < row["oracle_weight_recovery"]["V1"]["estimate"]
        for row in detected_monotone
    )
    controls_pass = alpha0_pass and not monotone_consecutive and not direct_systematically_lower
    contract_pass = (
        len(scenarios) == 192
        and sum(int(row["ridge_fits"]) for row in scenarios) == EXPECTED_RIDGE_FITS
        and sum(int(row["alignment_fits"]) for row in scenarios) == EXPECTED_ALIGNMENT_FITS
        and sum(int(row["v5_ledgers"]) for row in scenarios) == EXPECTED_TOTAL_FITS
        and all(row["selection_final_isolation"]["final_test_read_events"] == 1 for row in scenarios)
    )
    if not contract_pass or not controls_pass:
        outcome = "INVALID_EQ_ANMA_SYNTHETIC_BENCHMARK"
    elif alpha_star is not None:
        outcome = "PASS_EQ_ANMA_SYNTHETIC_METHOD_ADVANTAGE"
    else:
        structured_rows = [curves["STRUCTURED_FISHER"][f"{alpha:g}"] for alpha in ALPHAS[1:]]
        mechanism_only = any(
            row["family_detected"]
            and all(row["parameter_recovery"][name]["median"] >= 0.70 for name in ("rho_a", "rho_b", "rho_q"))
            and row["oracle_weight_contrasts"]["V1_minus_direct"]["ci95"][0] > 0
            and row["oracle_weight_contrasts"]["V1_minus_gated_direct"]["ci95"][0] > 0
            and row["gate_recovery_f1"]["median"] >= 0.70
            for row in structured_rows
        )
        outcome = "PASS_EQ_ANMA_SYNTHETIC_MECHANISM_ONLY" if mechanism_only else "FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE"
    return {
        "schema_version": 1,
        "task": "S1_EQ_ANMA_SYNTHETIC_BENCHMARK",
        "evidence_scope": "SYNTHETIC_METHOD_VALIDITY",
        "outcome": outcome,
        "alpha_star": alpha_star,
        "curves": curves,
        "controls": {
            "alpha_zero": {"pass": alpha0_pass, "contrast": alpha0},
            "monotone_no_two_consecutive_EQ_positive_CIs": not monotone_consecutive,
            "monotone_direct_oracle_not_systematically_lower": not direct_systematically_lower,
            "pass": controls_pass,
        },
        "contract": {
            "pass": contract_pass,
            "scenarios": len(scenarios),
            "ridge_fits": sum(int(row["ridge_fits"]) for row in scenarios),
            "alignment_fits": sum(int(row["alignment_fits"]) for row in scenarios),
            "total_fits": sum(int(row["total_fits"]) for row in scenarios),
            "unique_passing_synthetic_v5_ledgers": sum(int(row["v5_ledgers"]) for row in scenarios),
            "final_test_read_events": sum(int(row["selection_final_isolation"]["final_test_read_events"]) for row in scenarios),
            "contract_sha256": contract_hash,
            "ledger_sha256": ledger_hash,
        },
        "alpha_zero_byte_equality": {
            str(seed): {
                "equal": by_key[("STRUCTURED_FISHER", 0.0, seed)]["feature_sha256"] == by_key[("MONOTONE_DIRECT", 0.0, seed)]["feature_sha256"],
                "sha256": by_key[("STRUCTURED_FISHER", 0.0, seed)]["feature_sha256"],
            }
            for seed in REPLICATE_SEEDS
        },
        "claim_boundary": {
            "real_EEG_superiority": False,
            "real_Gate_B_released": False,
            "real_EEG_alpha_threshold": False,
            "real_outer_test_reads": 0,
            "next_task": "S1_A1_NEGATIVE_CONFIRMATION",
        },
        "replicate_summaries": list(scenarios),
    }


def _markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# EQ-ANMA synthetic benchmark (SPEC v3.20)",
        "",
        f"Declarative outcome: `{result['outcome']}`",
        f"Synthetic alpha_star: `{result['alpha_star']}`. This is not a real EEG threshold.",
        "",
        "This artifact is synthetic-method evidence only. It does not establish real EEG superiority, release Gate B, or alter the frozen A1 failures.",
        "",
        "## Exact accounting",
        "",
        f"- ridge fits: {result['contract']['ridge_fits']}",
        f"- alignment fits: {result['contract']['alignment_fits']}",
        f"- total fits / unique passing V5 ledgers: {result['contract']['total_fits']} / {result['contract']['unique_passing_synthetic_v5_ledgers']}",
        f"- final-test batch read events: {result['contract']['final_test_read_events']} (one per scenario, after choice freeze)",
        "",
    ]
    for regime in REGIMES:
        lines.extend([f"## {regime}", "", "| alpha | family | V1 R@1 | direct R@1 | gated R@1 | V1-direct | V1-gated |", "|---:|:---:|---:|---:|---:|---:|---:|"])
        for alpha in ALPHAS:
            row = result["curves"][regime][f"{alpha:g}"]
            lines.append(
                f"| {alpha:g} | {row['family_detected']} | {row['methods']['V1']['R_at_1_N10']['estimate']:.6f} | "
                f"{row['methods']['direct']['R_at_1_N10']['estimate']:.6f} | {row['methods']['gated_direct']['R_at_1_N10']['estimate']:.6f} | "
                f"{row['contrasts']['V1_minus_direct']['estimate']:.6f} | {row['contrasts']['V1_minus_gated_direct']['estimate']:.6f} |"
            )
        lines.append("")
    lines.extend([
        "## Controls and boundary",
        "",
        f"- alpha-zero control: {result['controls']['alpha_zero']['pass']}",
        f"- MONOTONE_DIRECT no consecutive EQ-positive CI: {result['controls']['monotone_no_two_consecutive_EQ_positive_CIs']}",
        f"- MONOTONE_DIRECT oracle discriminativeness: {result['controls']['monotone_direct_oracle_not_systematically_lower']}",
        "- true a/b/q/I/stable mask were restricted to generation and final diagnostics.",
        "- selection and final-test subjects/items are jointly disjoint; final test was evaluated only after all choices froze.",
        "- required next task: `S1_A1_NEGATIVE_CONFIRMATION`.",
        "",
    ])
    return "\n".join(lines)


def preflight(root: Path, *, device: str) -> None:
    _contract(root)
    assert_split_isolation()
    first = build_replicate(REPLICATE_SEEDS[0])
    second = build_replicate(REPLICATE_SEEDS[0])
    if first.base_noise.tobytes() != second.base_noise.tobytes():
        raise RuntimeError("generator determinism preflight failed")
    equal, structured_hash, monotone_hash = alpha_zero_byte_equality(first)
    if not equal or structured_hash != monotone_hash:
        raise RuntimeError("alpha-zero canonical-byte equality preflight failed")
    # Adversarial V5 overlap must reject.
    try:
        build_synthetic_v5_ledger(
            fit_id="adversarial", scenario_id="preflight", fit_ids=["same"], selection_ids=["same"],
            generator_hash=structured_hash, scope="adversarial",
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("V5 adversarial overlap was not rejected")
    scenario = generate_scenario(first, "STRUCTURED_FISHER", 0.3)
    started = time.perf_counter()
    result, ledgers = run_scenario(scenario, device=device, include_final_test=False)
    elapsed = time.perf_counter() - started
    if elapsed > 300:
        raise RuntimeError(f"BLOCKER_RUNTIME: single scenario took {elapsed:.3f}s > 300s")
    if result["ridge_fits"] != 25 or result["alignment_fits"] != 37 or len(ledgers) != 62:
        raise RuntimeError("preflight scenario accounting failed")
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "generator_deterministic": True,
        "alpha_zero_byte_equal": True,
        "split_isolation": True,
        "v5_adversarial": True,
        "single_scenario_seconds": elapsed,
        "single_scenario_fits": {"ridge": 25, "alignment": 37, "total": 62},
        "formal_final_test_curves_read": False,
    }, sort_keys=True))


def formal(
    root: Path,
    *,
    device: str,
    resume: bool,
    worker_index: int,
    worker_count: int,
    aggregate_only: bool,
) -> None:
    contract = _contract(root)
    if worker_count < 1 or worker_index < 0 or worker_index >= worker_count:
        raise ValueError("worker-index must be in [0, worker-count)")
    cache_root = root / CACHE_PATH
    cache_root.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []
    all_ledgers: list[dict[str, Any]] = []
    completed = 0
    selected_seeds = REPLICATE_SEEDS if aggregate_only else tuple(
        seed for index, seed in enumerate(REPLICATE_SEEDS) if index % worker_count == worker_index
    )
    for seed in selected_seeds:
        base = build_replicate(seed)
        for regime in REGIMES:
            for alpha in ALPHAS:
                cache_file = cache_root / f"seed_{seed}_{regime}_alpha_{alpha:g}.json.gz"
                if (resume or aggregate_only) and cache_file.is_file():
                    with gzip.open(cache_file, "rt", encoding="utf-8") as handle:
                        cached = json.load(handle)
                    result, ledgers = cached["result"], cached["ledgers"]
                elif aggregate_only:
                    raise RuntimeError(f"aggregate-only missing scenario cache: {cache_file.name}")
                else:
                    scenario = generate_scenario(base, regime, alpha)
                    result, ledgers = run_scenario(scenario, device=device, include_final_test=True)
                    payload = json.dumps({"result": result, "ledgers": ledgers}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
                    cache_file.write_bytes(gzip.compress(payload, compresslevel=6, mtime=0))
                all_results.append(result)
                all_ledgers.extend(ledgers)
                completed += 1
                print(f"SCENARIO_COMPLETE {completed}/192 {result['scenario_id']} seconds={result['elapsed_seconds']:.3f}", flush=True)
    if worker_count > 1 and not aggregate_only:
        expected = len(selected_seeds) * len(REGIMES) * len(ALPHAS)
        if completed != expected:
            raise RuntimeError("formal worker scenario accounting failed")
        print(json.dumps({
            "status": "FORMAL_WORKER_COMPLETE",
            "worker_index": worker_index,
            "worker_count": worker_count,
            "scenarios": completed,
            "formal_final_test_read_events": completed,
        }, sort_keys=True), flush=True)
        return
    fit_ids = [row["fit_id"] for row in all_ledgers]
    if len(all_results) != 192 or len(all_ledgers) != EXPECTED_TOTAL_FITS or len(set(fit_ids)) != EXPECTED_TOTAL_FITS:
        raise RuntimeError("INVALID_EQ_ANMA_SYNTHETIC_BENCHMARK: exact scenario/V5 accounting failed")
    if any(row.get("v5_pass") is not True for row in all_ledgers):
        raise RuntimeError("INVALID_EQ_ANMA_SYNTHETIC_BENCHMARK: a V5 ledger failed")
    ledger_bytes = deterministic_gzip_jsonl(all_ledgers)
    ledger_path = root / LEDGER_PATH
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_bytes(ledger_bytes)
    ledger_hash = sha256_bytes(ledger_bytes)
    contract_hash = _sha256_file(root / CONTRACT_PATH)
    result = summarize(all_results, contract_hash=contract_hash, ledger_hash=ledger_hash)
    json_path = root / RESULT_JSON_PATH
    md_path = root / RESULT_MD_PATH
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes(canonical_artifact(result))
    md_path.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": "FORMAL_COMPLETE",
        "outcome": result["outcome"],
        "alpha_star": result["alpha_star"],
        "ridge_fits": result["contract"]["ridge_fits"],
        "alignment_fits": result["contract"]["alignment_fits"],
        "total_fits": result["contract"]["total_fits"],
        "v5": result["contract"]["unique_passing_synthetic_v5_ledgers"],
        "ledger_sha256": ledger_hash,
        "result_sha256": _sha256_file(json_path),
    }, sort_keys=True), flush=True)


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    if args.max_scenarios is not None and args.formal:
        raise SystemExit("--max-scenarios is forbidden with --formal")
    if args.preflight == args.formal:
        raise SystemExit("choose exactly one of --preflight or --formal")
    if not torch.cuda.is_available() and str(args.device).startswith("cuda"):
        raise RuntimeError("BLOCKER_OOM_OR_DEVICE: CUDA requested but unavailable")
    if args.preflight:
        preflight(root, device=args.device)
    else:
        formal(
            root,
            device=args.device,
            resume=args.resume,
            worker_index=args.worker_index,
            worker_count=args.worker_count,
            aggregate_only=args.aggregate_only,
        )


if __name__ == "__main__":
    main()
