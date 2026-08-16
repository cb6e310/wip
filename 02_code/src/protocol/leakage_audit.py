"""SPEC v3.12 Appendix P pre-run leakage audit for admitted ZuCo2 artifacts.

The audit is intentionally model-independent and EEG-free.  V1--V4 inspect
only frozen protocol JSON/YAML artifacts.  V5 defines and tests the ledger
that every future training/evaluation run must pass; it does not admit a run.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from data.candidate_common_support import validate_common_support
from data.candidates import validate_candidate_artifacts
from data.inner_split import validate_inner_artifact, validate_outer_artifact
from data.joint_split import canonical_json_bytes, sha256_bytes
from protocol.h_definition import (
    DEFAULT_CONFIG,
    audit_h_context,
    build_h_empty,
    build_h_full,
    config_hash as h_config_hash,
)


SCHEMA_VERSION = 1
DEFAULT_RUN_ID = "2026-08-15_023_v312_pre_run_leakage_audit"
EXPECTED_INPUTS = {
    "outer_split": (
        "01_data_protocol/splits/zuco_2_0_outer_folds.json",
        "20aedfd56c7c5ee41a491e5b5531ef77728344808d42ba45d72d7e30250cffa6",
    ),
    "inner_split": (
        "01_data_protocol/splits/zuco_2_0_inner_folds.json",
        "0271aba0ae9627f35e281029a8a95390513c1e92c8010e8a2795171f837575d7",
    ),
    "inner_support": (
        "04_results/audits/zuco2_inner_split_support.json",
        "536ed93758baf1e4d7c8796bc164b39f7ec86a97ac8ac6b4e65bb8e782644564",
    ),
    "source_slot_join": (
        "artifacts/zuco2_source_slot_join.yaml",
        "eb960cd0bf2cb5016f33793813cb61fa2c77c9ce07e2037cff69b29c14c104c8",
    ),
    "h_definition": (
        "artifacts/h_definition.yaml",
        "226f92e299633997fdb9469592f6f8a36fa6c728aa24d9a7d6cb9ded8fb2ae6b",
    ),
    "text_encoder_freeze": (
        "artifacts/text_encoder_freeze.yaml",
        "35e18392a285c8d09ba84a934e31dd327a18fa1a0c10a3bd8550f090cd496494",
    ),
    "base_candidate_lists": (
        "01_data_protocol/candidates/candidate_lists.json",
        "51130ffc216a1f0bf50a9eeec42136555ab98ee110f3aaa265de54c3a004115a",
    ),
    "base_paired_pairs": (
        "01_data_protocol/candidates/paired_verification_pairs.json",
        "bc37630ea3c6c870d4388ac0c16582f742e6751d533e3656a284304d09e3ec5c",
    ),
    "base_feasibility": (
        "04_results/audits/zuco2_candidate_feasibility.json",
        "8f478fddc78ccb46df2c1a75945a3f90ec89f7c58ca456172a4874bef75f7960",
    ),
    "n10_candidate_lists": (
        "01_data_protocol/candidates/candidate_lists_n10_common_support.json",
        "b3eda1c09542344e108ce162a0f414beb54a426644db18126ee1e87e36ddf097",
    ),
    "n10_paired_pairs": (
        "01_data_protocol/candidates/paired_verification_pairs_n10.json",
        "71b6b53e5686e125d067240fd6414b833ef74b46159b130d5c6097152d722771",
    ),
    "n10_audit": (
        "04_results/audits/zuco2_n10_common_support_audit.json",
        "6dfba054d8242501808e267f91efdf080f6cbd479b617819edb4baf47554c0fc",
    ),
}
EXPECTED_SOURCE_JOIN_CONFIG_HASH = (
    "637757e54f47c9c2a73a039887f469f4997463d19ccb878e6a9adf88a2d1cb2d"
)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return value


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return value


def _without_integrity(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    payload.pop("integrity", None)
    return payload


def verify_json_integrity(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    block = value.get("integrity")
    if not isinstance(block, Mapping):
        raise ValueError(f"{label}: missing integrity block")
    payload = canonical_json_bytes(_without_integrity(value))
    actual = sha256_bytes(payload)
    if block.get("canonical_payload_sha256") != actual:
        raise ValueError(f"{label}: canonical payload SHA256 mismatch")
    if block.get("canonical_payload_bytes") != len(payload):
        raise ValueError(f"{label}: canonical payload byte count mismatch")
    return {"canonical_payload_sha256": actual, "canonical_payload_bytes": len(payload)}


def verify_config_hash(value: Mapping[str, Any], label: str) -> None:
    config = value.get("config")
    if not isinstance(config, Mapping):
        raise ValueError(f"{label}: missing config")
    if value.get("config_hash") != sha256_bytes(canonical_json_bytes(config)):
        raise ValueError(f"{label}: config hash mismatch")


def admit_physical_inputs(root: str | Path) -> dict[str, dict[str, Any]]:
    project = Path(root)
    bindings: dict[str, dict[str, Any]] = {}
    for name, (relative_path, expected) in EXPECTED_INPUTS.items():
        path = project / relative_path
        if not path.is_file():
            raise ValueError(f"STATE_SPEC_CONFLICT: missing immutable input {relative_path}")
        actual = file_sha256(path)
        if actual != expected:
            raise ValueError(
                f"STATE_SPEC_CONFLICT: {name} physical SHA256 mismatch; "
                f"expected={expected} actual={actual}"
            )
        bindings[name] = {"path": relative_path, "file_sha256": actual}
    return bindings


def _decode(indices: Iterable[Any], outer_train: Sequence[str], label: str) -> list[str]:
    result: list[str] = []
    for raw in indices:
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0 or raw >= len(outer_train):
            raise ValueError(f"{label}: invalid outer-train record index {raw}")
        result.append(outer_train[raw])
    if len(result) != len(set(result)):
        raise ValueError(f"{label}: duplicate decoded record IDs")
    return result


def _record_groups(record_ids: Iterable[str], records: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return sorted({str(records[record_id]["group_key"]) for record_id in record_ids})


def build_protocol_view(
    outer: Mapping[str, Any], inner: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Project large admitted splits into the fields needed by V1/V2."""

    outer_cells: list[dict[str, Any]] = []
    inner_cells: list[dict[str, Any]] = []
    for task in ("task1_nr", "task2_tsr"):
        panel = outer["panels"][task]
        records = {str(row["record_id"]): row for row in panel["records"]}
        all_record_ids = set(records)
        outer_by_id: dict[str, Mapping[str, Any]] = {}
        for cell in panel["cells"]:
            cell_id = f"{task}|outer_s{cell['subject_fold']}_t{cell['text_fold']}"
            outer_by_id[cell_id] = cell
            train = [str(value) for value in cell["train_record_ids"]]
            test = [str(value) for value in cell["test_record_ids"]]
            held = [str(value) for value in cell["held_out_only_record_ids"]]
            outer_cells.append(
                {
                    "task": task,
                    "outer_cell_id": cell_id,
                    "all_record_ids": sorted(all_record_ids),
                    "train_record_ids": train,
                    "test_record_ids": test,
                    "held_out_only_record_ids": held,
                    "train_subject_ids": sorted(str(value) for value in cell["train_subject_ids"]),
                    "test_subject_ids": sorted(str(value) for value in cell["test_subject_ids"]),
                    "train_stimulus_ids": sorted(str(value) for value in cell["train_stimulus_ids"]),
                    "test_stimulus_ids": sorted(str(value) for value in cell["test_stimulus_ids"]),
                    "train_group_ids": _record_groups(train, records),
                    "test_group_ids": _record_groups(test, records),
                    "held_out_only_group_ids": _record_groups(held, records),
                    "record_subject": {record_id: str(records[record_id]["subject_id"]) for record_id in all_record_ids},
                    "record_stimulus": {record_id: str(records[record_id]["stimulus_id"]) for record_id in all_record_ids},
                    "record_group": {record_id: str(records[record_id]["group_key"]) for record_id in all_record_ids},
                    "record_subject_fold": {record_id: str(records[record_id]["subject_fold"]) for record_id in all_record_ids},
                    "record_text_fold": {record_id: str(records[record_id]["text_fold"]) for record_id in all_record_ids},
                    "subject_fold": str(cell["subject_fold"]),
                    "text_fold": str(cell["text_fold"]),
                }
            )
        for outer_cell in inner["panels"][task]["outer_cells"]:
            outer_cell_id = str(outer_cell["outer_cell_id"])
            admitted_outer = outer_by_id.get(outer_cell_id)
            if admitted_outer is None:
                raise ValueError(f"{task}: unknown inner outer_cell_id {outer_cell_id}")
            outer_train = [str(value) for value in outer_cell["outer_train_record_ids"]]
            outer_test = [str(value) for value in outer_cell["outer_test_record_ids"]]
            for cell in outer_cell["inner_cells"]:
                inner_id = f"{outer_cell_id}|inner_s{cell['inner_subject_fold']}_t{cell['inner_text_fold']}"
                train = _decode(cell["train_record_id_indices"], outer_train, f"{inner_id}/train")
                validation = _decode(
                    cell["validation_record_id_indices"], outer_train, f"{inner_id}/validation"
                )
                held = _decode(
                    cell["held_out_only_record_id_indices"], outer_train, f"{inner_id}/held_out_only"
                )
                inner_cells.append(
                    {
                        "task": task,
                        "outer_cell_id": outer_cell_id,
                        "inner_cell_id": inner_id,
                        "outer_train_record_ids": outer_train,
                        "outer_test_record_ids": outer_test,
                        "outer_test_subject_ids": sorted(str(value) for value in outer_cell["outer_test_subject_ids"]),
                        "outer_test_stimulus_ids": sorted(str(value) for value in outer_cell["outer_test_stimulus_ids"]),
                        "outer_test_group_ids": _record_groups(outer_test, records),
                        "train_record_ids": train,
                        "validation_record_ids": validation,
                        "held_out_only_record_ids": held,
                        "train_subject_ids": sorted(str(value) for value in cell["train_subject_ids"]),
                        "validation_subject_ids": sorted(str(value) for value in cell["validation_subject_ids"]),
                        "train_stimulus_ids": sorted(str(value) for value in cell["train_stimulus_ids"]),
                        "validation_stimulus_ids": sorted(str(value) for value in cell["validation_stimulus_ids"]),
                        "train_group_ids": _record_groups(train, records),
                        "validation_group_ids": _record_groups(validation, records),
                        "held_out_only_group_ids": _record_groups(held, records),
                        "record_subject": {record_id: str(records[record_id]["subject_id"]) for record_id in set(outer_train) | set(outer_test)},
                        "record_stimulus": {record_id: str(records[record_id]["stimulus_id"]) for record_id in set(outer_train) | set(outer_test)},
                        "record_group": {record_id: str(records[record_id]["group_key"]) for record_id in set(outer_train) | set(outer_test)},
                    }
                )
    return {"outer_cells": outer_cells, "inner_cells": inner_cells}


def _duplicates(values: Sequence[str]) -> bool:
    return len(values) != len(set(values))


def _intersects(left: Iterable[str], right: Iterable[str]) -> bool:
    return not set(left).isdisjoint(right)


def validate_protocol_view(view: Mapping[str, Any]) -> dict[str, list[str]]:
    """Validate V1/V2 on either a real projection or adversarial fixture."""

    v1: list[str] = []
    v2: list[str] = []
    outer_map: dict[str, Mapping[str, Any]] = {}
    for cell in view.get("outer_cells", []):
        cell_id = str(cell.get("outer_cell_id"))
        if cell_id in outer_map:
            v1.append(f"{cell_id}: duplicate outer cell")
            continue
        outer_map[cell_id] = cell
        train = [str(value) for value in cell.get("train_record_ids", [])]
        test = [str(value) for value in cell.get("test_record_ids", [])]
        held = [str(value) for value in cell.get("held_out_only_record_ids", [])]
        if any(_duplicates(values) for values in (train, test, held)):
            v1.append(f"{cell_id}: duplicate record within partition")
        if _intersects(train, test) or _intersects(train, held) or _intersects(test, held):
            v1.append(f"{cell_id}: outer record partitions overlap")
        if set(train) | set(test) | set(held) != set(cell.get("all_record_ids", [])):
            v1.append(f"{cell_id}: outer record partitions do not cover admitted records")
        if _intersects(cell.get("train_subject_ids", []), cell.get("test_subject_ids", [])):
            v1.append(f"{cell_id}: outer test subject enters train")
        record_subject = cell.get("record_subject", {})
        record_stimulus = cell.get("record_stimulus", {})
        for label, record_ids, subjects, stimuli in (
            ("train", train, set(cell.get("train_subject_ids", [])), set(cell.get("train_stimulus_ids", []))),
            ("test", test, set(cell.get("test_subject_ids", [])), set(cell.get("test_stimulus_ids", []))),
        ):
            if any(record_subject.get(record_id) not in subjects for record_id in record_ids):
                v1.append(f"{cell_id}: {label} record/subject identity mismatch")
            if any(record_stimulus.get(record_id) not in stimuli for record_id in record_ids):
                v2.append(f"{cell_id}: {label} record/source-slot identity mismatch")
        if _intersects(cell.get("train_stimulus_ids", []), cell.get("test_stimulus_ids", [])):
            v2.append(f"{cell_id}: outer test stimulus enters train")
        if _intersects(cell.get("train_group_ids", []), cell.get("test_group_ids", [])):
            v2.append(f"{cell_id}: outer material group crosses train/test")
        record_group = cell.get("record_group", {})
        train_groups = set(cell.get("train_group_ids", []))
        test_groups = set(cell.get("test_group_ids", []))
        if any(record_group.get(record_id) not in train_groups for record_id in train):
            v2.append(f"{cell_id}: train material-group identity mismatch")
        if any(record_group.get(record_id) not in test_groups for record_id in test):
            v2.append(f"{cell_id}: test material-group identity mismatch")
        sfold = str(cell.get("subject_fold"))
        tfold = str(cell.get("text_fold"))
        if any(
            cell.get("record_subject_fold", {}).get(record_id) != sfold
            or cell.get("record_text_fold", {}).get(record_id) != tfold
            for record_id in test
        ):
            v1.append(f"{cell_id}: test record is not the subject/text-fold intersection")
        if any(
            cell.get("record_subject_fold", {}).get(record_id) == sfold
            or cell.get("record_text_fold", {}).get(record_id) == tfold
            for record_id in train
        ):
            v1.append(f"{cell_id}: train record uses held-out subject or text fold")

    for cell in view.get("inner_cells", []):
        inner_id = str(cell.get("inner_cell_id"))
        outer_id = str(cell.get("outer_cell_id"))
        outer = outer_map.get(outer_id)
        if outer is None:
            v1.append(f"{inner_id}: unknown corresponding outer cell")
            continue
        outer_train = set(str(value) for value in cell.get("outer_train_record_ids", []))
        outer_test = set(str(value) for value in cell.get("outer_test_record_ids", []))
        if outer_train != set(outer.get("train_record_ids", [])):
            v1.append(f"{inner_id}: embedded outer train differs from admitted outer cell")
        if outer_test != set(outer.get("test_record_ids", [])):
            v1.append(f"{inner_id}: embedded outer test differs from admitted outer cell")
        train = set(str(value) for value in cell.get("train_record_ids", []))
        validation = set(str(value) for value in cell.get("validation_record_ids", []))
        held = set(str(value) for value in cell.get("held_out_only_record_ids", []))
        if not train.isdisjoint(validation) or not train.isdisjoint(held) or not validation.isdisjoint(held):
            v1.append(f"{inner_id}: inner record partitions overlap")
        if train | validation | held != outer_train:
            v1.append(f"{inner_id}: inner records are not an exact outer-train partition")
        if not (train | validation | held).isdisjoint(outer_test):
            v1.append(f"{inner_id}: outer-test record enters inner split")
        if _intersects(cell.get("train_subject_ids", []), cell.get("validation_subject_ids", [])):
            v1.append(f"{inner_id}: inner validation subject enters fit train")
        if _intersects(cell.get("train_subject_ids", []), cell.get("outer_test_subject_ids", [])) or _intersects(
            cell.get("validation_subject_ids", []), cell.get("outer_test_subject_ids", [])
        ):
            v1.append(f"{inner_id}: outer-test subject enters inner train/validation")
        if _intersects(cell.get("train_stimulus_ids", []), cell.get("validation_stimulus_ids", [])):
            v2.append(f"{inner_id}: inner validation stimulus enters train")
        if _intersects(cell.get("train_group_ids", []), cell.get("validation_group_ids", [])):
            v2.append(f"{inner_id}: atomic material group crosses inner train/validation")
        if _intersects(cell.get("outer_test_stimulus_ids", []), cell.get("train_stimulus_ids", [])) or _intersects(
            cell.get("outer_test_stimulus_ids", []), cell.get("validation_stimulus_ids", [])
        ):
            v2.append(f"{inner_id}: outer-test stimulus enters inner split")
        if _intersects(cell.get("outer_test_group_ids", []), cell.get("train_group_ids", [])) or _intersects(
            cell.get("outer_test_group_ids", []), cell.get("validation_group_ids", [])
        ):
            v2.append(f"{inner_id}: outer-test material group enters inner split")
        record_subject = cell.get("record_subject", {})
        record_stimulus = cell.get("record_stimulus", {})
        record_group = cell.get("record_group", {})
        for label, ids, subjects, stimuli, groups in (
            ("train", train, set(cell.get("train_subject_ids", [])), set(cell.get("train_stimulus_ids", [])), set(cell.get("train_group_ids", []))),
            ("validation", validation, set(cell.get("validation_subject_ids", [])), set(cell.get("validation_stimulus_ids", [])), set(cell.get("validation_group_ids", []))),
        ):
            if any(record_subject.get(record_id) not in subjects for record_id in ids):
                v1.append(f"{inner_id}: {label} record/subject mismatch")
            if any(record_stimulus.get(record_id) not in stimuli for record_id in ids):
                v2.append(f"{inner_id}: {label} record/source-slot mismatch")
            if any(record_group.get(record_id) not in groups for record_id in ids):
                v2.append(f"{inner_id}: {label} record/material-group mismatch")
    return {"V1": v1, "V2": v2}


def audit_h_payload(
    context: Any,
    *,
    target_tokens: Sequence[object] = (),
    future_sentence_indices: Sequence[int] = (),
    payload: object | None = None,
) -> list[str]:
    checks = audit_h_context(
        context,
        target_tokens=target_tokens,
        future_sentence_indices=future_sentence_indices,
        payload=payload,
    )
    return sorted(name for name, passed in checks.items() if not passed)


def audit_v3(h_artifact: Mapping[str, Any]) -> dict[str, Any]:
    if h_artifact.get("status") != "ENGINEERING_CONTRACT_PASS":
        raise ValueError("H definition is not admitted")
    if h_artifact.get("config_hash") != h_config_hash(DEFAULT_CONFIG):
        raise ValueError("H definition config hash mismatch")
    if h_artifact.get("config") != DEFAULT_CONFIG.to_dict():
        raise ValueError("H definition config differs from frozen HConfig")
    sentences = [["prior", "safe"], ["near", "target"], ["target", "words"]]
    full = build_h_full(
        sentences, target_sentence_index=2, target_tokens=sentences[2], position_index=2
    )
    empty = build_h_empty(target_sentence_index=2, position_index=2)
    if audit_h_payload(full, target_tokens=sentences[2]) or audit_h_payload(empty):
        raise ValueError("admitted H_full/H_empty construction failed audit")
    forbidden_cases = {
        "current_or_target": {"current_token": "x"},
        "future": {"future_tokens": ["x"]},
        "target_statistics": {"word_count": 3},
        "candidate_payload": {"candidate_ids": ["x"]},
        "eye_tracking": {"et": [1.0]},
    }
    rejected: dict[str, list[str]] = {}
    for name, payload in forbidden_cases.items():
        failures = audit_h_payload(full, target_tokens=sentences[2], payload=payload)
        if not failures:
            raise ValueError(f"H forbidden payload was accepted: {name}")
        rejected[name] = failures
    future_failures = audit_h_payload(full, future_sentence_indices=[2])
    if "future_sentences_absent" not in future_failures:
        raise ValueError("H future-sentence mutation was accepted")
    return {
        "outcome": "PASS_REAL_ARTIFACTS",
        "versions": ["H_full", "H_empty"],
        "scope": "stage1_probe_only",
        "candidate_side_allowed_input": "source_sentence_identity_for_hard_exclusion_only",
        "forbidden_case_count": len(rejected) + 1,
        "forbidden_cases_rejected": {**rejected, "future_sentence_index": future_failures},
    }


def validate_exact_bindings(
    actual: Mapping[str, str], expected: Mapping[str, str], label: str = "bindings"
) -> list[str]:
    errors: list[str] = []
    if set(actual) != set(expected):
        errors.append(f"{label}: key set mismatch")
    for key, value in expected.items():
        if actual.get(key) != value:
            errors.append(f"{label}: {key} hash mismatch")
    return errors


def validate_repeat_projection(
    base_target: Mapping[str, Any],
    derived_target: Mapping[str, Any],
    pair_target: Mapping[str, Any],
    audit_target: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    try:
        target_index = int(base_target["target_index"])
        if any(int(row["target_index"]) != target_index for row in (derived_target, pair_target, audit_target)):
            errors.append("target identity mismatch")
            return errors
        legal_count = int(base_target["legal_count"])
        eligible = legal_count >= 9
        if bool(derived_target["eligible"]) != eligible or bool(pair_target["eligible"]) != eligible:
            errors.append("common-support eligibility mismatch")
        if bool(audit_target["eligible"]) != eligible:
            errors.append("audit eligibility mismatch")
        if int(derived_target["legal_count"]) != legal_count:
            errors.append("legal count mismatch")
        if not eligible and any(
            row.get("exclusion_reason") != "LEGAL_NEGATIVES_LT_9"
            for row in (derived_target, pair_target, audit_target)
        ):
            errors.append("excluded reason mismatch")
        base_repeats = sorted(base_target["repeats"], key=lambda row: int(row["repeat"]))
        derived_repeats = sorted(derived_target["repeats"], key=lambda row: int(row["repeat"]))
        pair_repeats = sorted(pair_target["repeats"], key=lambda row: int(row["repeat"]))
        if not (len(base_repeats) == len(derived_repeats) == len(pair_repeats) == 5):
            errors.append("repeat count is not five")
            return errors
        for base_repeat, derived_repeat, pair_repeat in zip(
            base_repeats, derived_repeats, pair_repeats, strict=True
        ):
            if not (
                int(base_repeat["repeat"])
                == int(derived_repeat["repeat"])
                == int(pair_repeat["repeat"])
            ):
                errors.append("repeat identity mismatch")
                continue
            expected_negatives = list(base_repeat["maximal_legal_negative_indices"][:9]) if eligible else []
            if derived_repeat["negative_indices"] != expected_negatives:
                errors.append("first-nine prefix mismatch")
            expected_position = base_repeat["n_lists"]["10"]["target_position"] if eligible else None
            if derived_repeat["target_position"] != expected_position:
                errors.append("target position mismatch")
            if eligible:
                if pair_repeat["auroc_1_to_1"]["negative_index"] != expected_negatives[0]:
                    errors.append("paired AUROC first-negative mismatch")
                if pair_repeat["auprc_1_to_9"]["negative_indices"] != expected_negatives:
                    errors.append("paired AUPRC nine-negative mismatch")
                if pair_repeat["auprc_1_to_9"]["positive_prevalence"] != 0.1:
                    errors.append("paired AUPRC prevalence mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def validate_scoring_contract(
    candidates: Mapping[str, Any], pairs: Mapping[str, Any], audit: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    for label, value in (("candidates", candidates), ("pairs", pairs), ("audit", audit)):
        assertions = value.get("assertions", {})
        if assertions.get("scoring_only") is not True:
            errors.append(f"{label}: scoring_only is not true")
        if assertions.get("training_records_removed") != 0:
            errors.append(f"{label}: training_records_removed is not zero")
    if audit.get("claim_population") != "candidate-common-support sentences":
        errors.append("audit claim population mismatch")
    return errors


def validate_candidate_h_boundary(candidates: Mapping[str, Any]) -> list[str]:
    """Candidate artifacts may carry H source identities, never H content."""

    errors: list[str] = []
    allowed_stimulus_keys = {
        "task",
        "stimulus_id",
        "exact_text_sha256",
        "token_length",
        "h_full_source_indices",
    }
    for index, stimulus in enumerate(candidates.get("stimuli", [])):
        extras = set(stimulus) - allowed_stimulus_keys
        if extras:
            errors.append(f"stimulus[{index}]: forbidden candidate/H content keys {sorted(extras)}")
            break
    if candidates.get("config", {}).get("h_exclusion") != "all_exact_H_full_source_identities":
        errors.append("candidate H exclusion is not exact source identity")
    if not str(candidates.get("provenance", {}).get("h_artifact_sha256", "")):
        errors.append("candidate H artifact provenance is missing")
    return errors


def validate_scope_projection(
    base_scope: Mapping[str, Any],
    derived_scope: Mapping[str, Any],
    pair_scope: Mapping[str, Any],
    audit_scope: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    identity_keys = ("task", "scope_type", "scope_id")
    identity = tuple(base_scope.get(key) for key in identity_keys)
    if any(tuple(scope.get(key) for key in identity_keys) != identity for scope in (derived_scope, pair_scope, audit_scope)):
        errors.append("scope identity mismatch")
    if list(base_scope.get("pool_stimulus_indices", [])) != list(
        derived_scope.get("pool_stimulus_indices", [])
    ):
        errors.append("scope source pool mismatch")
    target_sets = [
        {int(row["target_index"]) for row in scope.get("targets", [])}
        for scope in (base_scope, derived_scope, pair_scope, audit_scope)
    ]
    if not target_sets or any(values != target_sets[0] for values in target_sets[1:]):
        errors.append("scope target ledger mismatch")
    if target_sets and target_sets[0] != {
        int(value) for value in base_scope.get("pool_stimulus_indices", [])
    }:
        errors.append("base targets do not equal source pool")
    return errors


def audit_v4(
    root: str | Path, bindings: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    project = Path(root)
    base_candidates = _load_json(project / EXPECTED_INPUTS["base_candidate_lists"][0])
    base_pairs = _load_json(project / EXPECTED_INPUTS["base_paired_pairs"][0])
    base_audit = _load_json(project / EXPECTED_INPUTS["base_feasibility"][0])
    for label, value in (
        ("base_candidate_lists", base_candidates),
        ("base_paired_pairs", base_pairs),
        ("base_feasibility", base_audit),
    ):
        verify_json_integrity(value, label)
    base_errors = validate_candidate_artifacts(base_candidates, base_pairs, base_audit)
    if base_errors:
        raise ValueError(f"base candidate validation failed: {base_errors}")
    if base_pairs.get("candidate_lists_file_sha256") != bindings["base_candidate_lists"]["file_sha256"]:
        raise ValueError("base paired artifact physical candidate binding mismatch")
    h_boundary_errors = validate_candidate_h_boundary(base_candidates)
    if h_boundary_errors:
        raise ValueError(f"candidate H boundary failed: {h_boundary_errors}")

    derived_candidates = _load_json(project / EXPECTED_INPUTS["n10_candidate_lists"][0])
    derived_pairs = _load_json(project / EXPECTED_INPUTS["n10_paired_pairs"][0])
    derived_audit = _load_json(project / EXPECTED_INPUTS["n10_audit"][0])
    for label, value in (
        ("n10_candidate_lists", derived_candidates),
        ("n10_paired_pairs", derived_pairs),
        ("n10_audit", derived_audit),
    ):
        verify_json_integrity(value, label)
    derived_errors = validate_common_support(derived_candidates, derived_pairs, derived_audit)
    if derived_errors:
        raise ValueError(f"N10 common-support validation failed: {derived_errors}")
    if derived_pairs.get("candidate_lists_file_sha256") != bindings["n10_candidate_lists"]["file_sha256"]:
        raise ValueError("N10 paired artifact physical candidate binding mismatch")
    if validate_scoring_contract(derived_candidates, derived_pairs, derived_audit):
        raise ValueError(f"N10 scoring boundary failed: {validate_scoring_contract(derived_candidates, derived_pairs, derived_audit)}")

    expected_base_files = {
        "candidate_feasibility": bindings["base_feasibility"]["file_sha256"],
        "candidate_lists": bindings["base_candidate_lists"]["file_sha256"],
        "paired_verification_pairs": bindings["base_paired_pairs"]["file_sha256"],
    }
    provenance_files = derived_candidates["provenance"]["base_file_sha256"]
    binding_errors = validate_exact_bindings(provenance_files, expected_base_files, "derived provenance")
    if binding_errors:
        raise ValueError(str(binding_errors))
    base_provenance = base_candidates["provenance"]
    expected_protocol_refs = {
        "outer_file_sha256": bindings["outer_split"]["file_sha256"],
        "inner_file_sha256": bindings["inner_split"]["file_sha256"],
        "inner_support_file_sha256": bindings["inner_support"]["file_sha256"],
        "source_join_artifact_sha256": bindings["source_slot_join"]["file_sha256"],
        "h_artifact_sha256": bindings["h_definition"]["file_sha256"],
        "encoder_artifact_sha256": bindings["text_encoder_freeze"]["file_sha256"],
    }
    protocol_errors = validate_exact_bindings(
        {key: str(base_provenance.get(key)) for key in expected_protocol_refs},
        expected_protocol_refs,
        "base protocol provenance",
    )
    if protocol_errors:
        raise ValueError(str(protocol_errors))
    if base_provenance.get("read_fields") != ["sentenceData/content", "task_materials"]:
        raise ValueError("candidate provenance read_fields boundary mismatch")
    if base_provenance.get("roamm_paths_read") != []:
        raise ValueError("candidate provenance contains a ROAMM read")

    if base_candidates["stimuli"] != derived_candidates["stimuli"]:
        raise ValueError("base/derived source-slot stimulus table mismatch")
    base_scope_map = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in base_candidates["scopes"]
    }
    base_audit_map = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in base_audit["scopes"]
    }
    derived_scope_map = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in derived_candidates["scopes"]
    }
    pair_scope_map = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in derived_pairs["scopes"]
    }
    derived_audit_map = {
        (row["task"], row["scope_type"], row["scope_id"]): row for row in derived_audit["scopes"]
    }
    if not (
        set(base_scope_map)
        == set(base_audit_map)
        == set(derived_scope_map)
        == set(pair_scope_map)
        == set(derived_audit_map)
    ):
        raise ValueError("base/derived scope identity mismatch")
    target_count = 0
    repeat_count = 0
    eligible_count = 0
    for key, base_scope in base_scope_map.items():
        derived_scope = derived_scope_map[key]
        scope_errors = validate_scope_projection(
            base_scope,
            derived_scope,
            pair_scope_map[key],
            derived_audit_map[key],
        )
        if scope_errors:
            raise ValueError(f"{key}: {scope_errors}")
        base_targets = {int(row["target_index"]): row for row in base_scope["targets"]}
        base_audit_targets = {int(row["target_index"]): row for row in base_audit_map[key]["targets"]}
        derived_targets = {int(row["target_index"]): row for row in derived_scope["targets"]}
        pair_targets = {int(row["target_index"]): row for row in pair_scope_map[key]["targets"]}
        audit_targets = {int(row["target_index"]): row for row in derived_audit_map[key]["targets"]}
        if not (set(base_targets) == set(base_audit_targets) == set(derived_targets) == set(pair_targets) == set(audit_targets)):
            raise ValueError(f"{key}: target ledger identity mismatch")
        for target_index, base_target in base_targets.items():
            errors = validate_repeat_projection(
                base_target,
                derived_targets[target_index],
                pair_targets[target_index],
                audit_targets[target_index],
            )
            if errors:
                raise ValueError(f"{key}/{target_index}: {errors}")
            if derived_targets[target_index]["sequential_counts"] != base_audit_targets[target_index]["counts"]:
                raise ValueError(f"{key}/{target_index}: sequential count mutation")
            if audit_targets[target_index]["sequential_exclusions"] != base_audit_targets[target_index]["sequential_exclusions"]:
                raise ValueError(f"{key}/{target_index}: sequential exclusion mutation")
            target_count += 1
            repeat_count += 5
            eligible_count += int(bool(derived_targets[target_index]["eligible"]))
    if (target_count, repeat_count, eligible_count) != (18475, 92375, 17061):
        raise ValueError("frozen target/repeat/common-support counts mismatch")
    return {
        "outcome": "PASS_REAL_ARTIFACTS",
        "base_artifact_count": 3,
        "derived_artifact_count": 3,
        "source_scope_count": len(base_scope_map),
        "target_count": target_count,
        "repeat_count": repeat_count,
        "eligible_target_count": eligible_count,
        "excluded_target_count": target_count - eligible_count,
        "five_repeats_verified": True,
        "first_nine_prefix_and_target_position_verified": True,
        "paired_1_to_1_and_1_to_9_verified": True,
        "scoring_only": True,
        "training_records_removed": 0,
        "candidate_h_input": "source_sentence_identity_only",
    }


def build_scope_index(view: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "outer": {str(row["outer_cell_id"]): row for row in view.get("outer_cells", [])},
        "inner": {str(row["inner_cell_id"]): row for row in view.get("inner_cells", [])},
    }


def _id_list(stage: Mapping[str, Any], key: str, label: str, errors: list[str]) -> list[str]:
    value = stage.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{label}: {key} must be a list of non-empty strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{label}: {key} contains duplicates")
    return value


def validate_run_ledger(
    ledger: Mapping[str, Any],
    scope_index: Mapping[str, Any],
    *,
    expected_input_hashes: Mapping[str, str],
) -> list[str]:
    """Validate one future model-independent fit/selection/scoring ledger."""

    errors: list[str] = []
    if ledger.get("schema_version") != 1 or ledger.get("dataset") != "zuco_2_0":
        errors.append("ledger schema_version/dataset mismatch")
    if not str(ledger.get("run_id", "")).strip():
        errors.append("ledger run_id is empty")
    actual_hashes = ledger.get("input_artifact_hashes")
    if not isinstance(actual_hashes, Mapping):
        errors.append("ledger input_artifact_hashes missing")
    else:
        errors.extend(validate_exact_bindings(actual_hashes, expected_input_hashes, "ledger inputs"))
    stages = ledger.get("stages")
    if not isinstance(stages, list) or not stages:
        errors.append("ledger stages must be non-empty")
        return errors
    allowed_types = {
        "preprocessing",
        "normalization",
        "probe_fit",
        "sham_fit",
        "model_fit",
        "threshold",
        "tuning",
        "final_scoring",
    }
    outer_index = scope_index.get("outer", {})
    inner_index = scope_index.get("inner", {})
    for position, stage in enumerate(stages):
        label = f"stage[{position}]"
        if not isinstance(stage, Mapping):
            errors.append(f"{label}: stage must be an object")
            continue
        stage_type = str(stage.get("stage_type", ""))
        if stage_type not in allowed_types:
            errors.append(f"{label}: unknown stage_type")
        outer_id = str(stage.get("outer_cell", ""))
        outer = outer_index.get(outer_id)
        if outer is None:
            errors.append(f"{label}: unknown outer_cell")
            continue
        inner_id = stage.get("inner_cell")
        inner = None
        if inner_id is not None:
            inner = inner_index.get(str(inner_id))
            if inner is None or str(inner.get("outer_cell_id")) != outer_id:
                errors.append(f"{label}: unknown or wrong-parent inner_cell")
                inner = None
        fit = _id_list(stage, "fit_record_ids", label, errors)
        selection = _id_list(stage, "selection_record_ids", label, errors)
        outer_reads = _id_list(stage, "outer_test_record_ids_read", label, errors)
        calibration = _id_list(stage, "calibration_record_ids", label, errors)
        stage_hashes = stage.get("input_artifact_hashes")
        if not isinstance(stage_hashes, Mapping):
            errors.append(f"{label}: input_artifact_hashes missing")
        else:
            errors.extend(validate_exact_bindings(stage_hashes, expected_input_hashes, f"{label} inputs"))
        allowed_fit = set(inner["train_record_ids"] if inner is not None else outer["train_record_ids"])
        allowed_selection = set(inner["validation_record_ids"] if inner is not None else [])
        outer_test = set(outer["test_record_ids"])
        if not set(fit).issubset(allowed_fit):
            errors.append(f"{label}: fit IDs are outside the legal train scope")
        if not set(selection).issubset(allowed_selection):
            errors.append(f"{label}: selection IDs are outside inner validation")
        if not set(fit).isdisjoint(selection):
            errors.append(f"{label}: inner validation enters fit")
        if not outer_test.isdisjoint(fit) or not outer_test.isdisjoint(selection):
            errors.append(f"{label}: outer test enters fit/selection/threshold/tuning")
        if calibration:
            errors.append(f"{label}: test-time calibration count must be zero")
        if stage_type == "final_scoring":
            if fit or selection:
                errors.append(f"{label}: final scoring cannot fit or select")
            if not set(outer_reads).issubset(outer_test):
                errors.append(f"{label}: final scoring reads non-outer-test records")
        elif outer_reads:
            errors.append(f"{label}: outer test read before final scoring")
    return errors


def synthetic_valid_run_ledger(
    scope_index: Mapping[str, Any], input_hashes: Mapping[str, str]
) -> dict[str, Any]:
    inner_id = sorted(scope_index["inner"])[0]
    inner = scope_index["inner"][inner_id]
    outer_id = str(inner["outer_cell_id"])
    outer = scope_index["outer"][outer_id]
    common = {
        "outer_cell": outer_id,
        "inner_cell": inner_id,
        "calibration_record_ids": [],
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
    }
    return {
        "schema_version": 1,
        "dataset": "zuco_2_0",
        "run_id": "synthetic-v5-contract-selfcheck",
        "seed": 20260813,
        "input_artifact_hashes": dict(sorted(input_hashes.items())),
        "stages": [
            {
                **common,
                "stage_type": "model_fit",
                "fit_record_ids": [inner["train_record_ids"][0]],
                "selection_record_ids": [],
                "outer_test_record_ids_read": [],
            },
            {
                **common,
                "stage_type": "tuning",
                "fit_record_ids": [],
                "selection_record_ids": [inner["validation_record_ids"][0]],
                "outer_test_record_ids_read": [],
            },
            {
                **common,
                "stage_type": "final_scoring",
                "fit_record_ids": [],
                "selection_record_ids": [],
                "outer_test_record_ids_read": [outer["test_record_ids"][0]],
            },
        ],
    }


def _add_integrity(value: dict[str, Any], scope: str) -> None:
    payload = canonical_json_bytes(value)
    value["integrity"] = {
        "canonical_payload_sha256": sha256_bytes(payload),
        "canonical_payload_bytes": len(payload),
        "hash_scope": scope,
    }


def build_pre_run_audit(root: str | Path, *, run_id: str = DEFAULT_RUN_ID) -> dict[str, Any]:
    project = Path(root)
    bindings = admit_physical_inputs(project)
    outer = _load_json(project / EXPECTED_INPUTS["outer_split"][0])
    inner = _load_json(project / EXPECTED_INPUTS["inner_split"][0])
    support = _load_json(project / EXPECTED_INPUTS["inner_support"][0])
    source_join = _load_yaml(project / EXPECTED_INPUTS["source_slot_join"][0])
    h_artifact = _load_yaml(project / EXPECTED_INPUTS["h_definition"][0])
    encoder = _load_yaml(project / EXPECTED_INPUTS["text_encoder_freeze"][0])

    validate_outer_artifact(
        outer,
        outer_file_sha256=bindings["outer_split"]["file_sha256"],
        expected_outer_file_sha256=EXPECTED_INPUTS["outer_split"][1],
    )
    outer_errors = []
    for task in ("task1_nr", "task2_tsr"):
        outer_errors.extend(validate_candidate_free_outer_panel(outer["panels"][task], task))
    if outer_errors:
        raise ValueError(f"outer panel validation failed: {outer_errors}")
    inner_errors = validate_inner_artifact(inner)
    if inner_errors:
        raise ValueError(f"inner split validation failed: {inner_errors}")
    verify_json_integrity(support, "inner support")
    verify_config_hash(support, "inner support")
    if support.get("status") != "PASS" or support.get("outer_file_sha256") != bindings["outer_split"]["file_sha256"]:
        raise ValueError("inner support admission/binding mismatch")
    if inner.get("outer_file_sha256") != bindings["outer_split"]["file_sha256"]:
        raise ValueError("inner split outer-file binding mismatch")
    if source_join.get("status") != "PASS":
        raise ValueError("source-slot join is not PASS")
    # This early YAML freeze predates the repository canonical-JSON helper;
    # its declared digest is therefore admitted by its frozen exact value and
    # physical file hash, while the semantic config is checked explicitly.
    if source_join.get("config_hash") != EXPECTED_SOURCE_JOIN_CONFIG_HASH:
        raise ValueError("source-slot join declared config hash mismatch")
    expected_join_config = {
        "dataset": "zuco_2_0",
        "identity_key": "dataset|task|source_file|row_number|paragraph_id_raw|sentence_id_raw",
        "text_hash_is_identity": False,
        "matching_rule": "summary_sequence_must_have_one_unique_monotone_embedding_in_material_rows",
    }
    if source_join.get("config") != expected_join_config:
        raise ValueError("source-slot join semantic config mismatch")
    if source_join.get("evidence", {}).get("joint_split_artifact_sha256") != bindings["outer_split"]["file_sha256"]:
        raise ValueError("source-slot join outer split binding mismatch")
    if encoder.get("status") != "PASS":
        raise ValueError("text encoder freeze is not PASS")

    view = build_protocol_view(outer, inner)
    protocol_errors = validate_protocol_view(view)
    if protocol_errors["V1"] or protocol_errors["V2"]:
        raise ValueError(f"real protocol isolation failure: {protocol_errors}")
    v1 = {
        "outcome": "PASS_REAL_ARTIFACTS",
        "outer_cell_count": len(view["outer_cells"]),
        "inner_cell_count": len(view["inner_cells"]),
        "subject_isolation": True,
        "record_isolation": True,
        "inner_records_subset_of_corresponding_outer_train": True,
        "outer_test_absent_from_all_inner_partitions": True,
    }
    v2 = {
        "outcome": "PASS_REAL_ARTIFACTS",
        "outer_cell_count": len(view["outer_cells"]),
        "inner_cell_count": len(view["inner_cells"]),
        "source_slot_isolation": True,
        "text_fold_isolation": True,
        "material_group_atomicity": True,
        "outer_test_material_absent_from_inner_train_and_validation": True,
    }
    if (v1["outer_cell_count"], v1["inner_cell_count"]) != (60, 540):
        raise ValueError("real outer/inner cell count mismatch")
    v3 = audit_v3(h_artifact)
    v4 = audit_v4(project, bindings)
    scope_index = build_scope_index(view)
    input_hashes = {name: str(value["file_sha256"]) for name, value in bindings.items()}
    synthetic_ledger = synthetic_valid_run_ledger(scope_index, input_hashes)
    v5_errors = validate_run_ledger(
        synthetic_ledger, scope_index, expected_input_hashes=input_hashes
    )
    if v5_errors:
        raise ValueError(f"V5 legal synthetic ledger failed: {v5_errors}")
    v5 = {
        "outcome": "PASS_PRE_RUN_CONTRACT",
        "schema_version": 1,
        "synthetic_valid_ledger_stage_count": len(synthetic_ledger["stages"]),
        "fit_scope_rule": "fit_record_ids subset of corresponding train only",
        "selection_scope_rule": "inner validation appears only in selection_record_ids",
        "outer_test_rule": "outer test appears only in final scoring reads",
        "test_time_calibration_count": 0,
        "future_run_admission_required": True,
        "real_training_ledgers_audited": 0,
    }
    for name, value in bindings.items():
        relative = EXPECTED_INPUTS[name][0]
        if relative.endswith(".json"):
            loaded = _load_json(project / relative)
            value.update(verify_json_integrity(loaded, name))
    audit = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "audit_scope": "ZuCo2 NR/TSR pre-run protocol artifacts and future run-ledger contract",
        "dataset": "zuco_2_0",
        "seed": 20260813,
        "method": "SPEC-v3.12-V1-V5-pre-run-leakage-audit",
        "input_bindings": dict(sorted(bindings.items())),
        "checks": {"V1": v1, "V2": v2, "V3": v3, "V4": v4, "V5": v5},
        "overall_outcome": "PASS_PRE_RUN_V1_V5",
        "future_run_admission_required": True,
        "real_training_ledgers_audited": 0,
        "limitations": [
            "V1-V4 admit current real protocol artifacts, not EEG or model outputs.",
            "V5 is a tested pre-run contract; no real training ledger exists or was audited.",
            "Every future run must carry and pass its own fit/selection/scoring/calibration ledger.",
            "This audit does not prove that future training is leakage-free before per-run admission.",
        ],
        "assertions": {
            "input_artifacts_modified": False,
            "eeg_read": False,
            "training_run": False,
            "held_out_metric_read": False,
            "roamm_read": False,
        },
        "status": "PASS",
    }
    _add_integrity(audit, "canonical JSON pre-run leakage audit without integrity field")
    return audit


def validate_candidate_free_outer_panel(panel: Mapping[str, Any], task: str) -> list[str]:
    """Use the admitted split validator semantics without candidate imports."""

    errors: list[str] = []
    try:
        verify_json_integrity(panel, f"outer/{task}")
        verify_config_hash(panel, f"outer/{task}")
        if panel.get("assertions", {}).get("all_checks_pass") is not True:
            raise ValueError("outer panel assertion failed")
        if len(panel.get("cells", [])) != 30:
            raise ValueError("outer panel does not contain 30 cells")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def render_markdown_summary(audit: Mapping[str, Any]) -> str:
    checks = audit["checks"]
    lines = [
        "# ZuCo2 pre-run leakage audit",
        "",
        f"- Overall outcome: `{audit['overall_outcome']}`",
        f"- V1 subject/record isolation: `{checks['V1']['outcome']}`",
        f"- V2 stimulus/source-slot/material isolation: `{checks['V2']['outcome']}`",
        f"- V3 legal H boundary: `{checks['V3']['outcome']}`",
        f"- V4 candidate/provenance/scoring boundary: `{checks['V4']['outcome']}`",
        f"- V5 future run-ledger contract: `{checks['V5']['outcome']}`",
        "",
        "V1-V4 passed on the admitted real protocol artifacts. No EEG, training output,",
        "held-out metric, Gate, route, main-experiment or ROAMM result was read.",
        "",
        "## Future run admission boundary",
        "",
        "`future_run_admission_required=true` and `real_training_ledgers_audited=0`.",
        "Every future run must provide fit, inner-selection, outer-test-read and calibration",
        "record IDs plus exact input hashes, and must pass the executable V5 validator.",
        "This pre-run contract is not evidence that an unrun or future training job is leakage-free.",
        "",
        "The machine-readable audit and exact input bindings are in",
        "`04_results/audits/zuco2_pre_run_leakage_audit.json`.",
        "",
    ]
    return "\n".join(lines)


def atomic_write_bytes(payload: bytes, path: str | Path) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def write_audit_outputs(
    audit: Mapping[str, Any], json_path: str | Path, markdown_path: str | Path
) -> dict[str, dict[str, Any]]:
    return {
        "json": atomic_write_bytes(canonical_json_bytes(audit) + b"\n", json_path),
        "markdown": atomic_write_bytes(
            render_markdown_summary(audit).encode("utf-8"), markdown_path
        ),
    }


def mutate_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Convenience deep copy for adversarial tests."""

    return copy.deepcopy(ledger)
