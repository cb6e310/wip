#!/usr/bin/env python3
"""Validate the small, file-based project memory system.

The validator is deliberately conservative: missing evidence is an error only when a
task claims DONE, while unresolved scientific facts remain explicit blockers.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment failure
    raise SystemExit("PyYAML is required to validate project state") from exc


ALLOWED_STATUSES = {
    "TODO",
    "READY",
    "IN_PROGRESS",
    "DONE",
    "BLOCKED",
    "FAILED",
    "SKIPPED",
    "TERMINATED",
}
REQUIRED_TASK_FIELDS = {
    "title",
    "stage",
    "status",
    "prerequisites",
    "produces",
    "acceptance",
}
REQUIRED_TASK_IDS = {
    "S0_DATA_CARD",
    "S0_SEMANTIC_ITEM",
    "S0_H_DEFINITION",
    "S0_JOINT_SPLIT",
    "S0_LEAKAGE_AUDIT",
    "S0_A1_FRONTEND",
    "S0_A1_ADMISSION",
    "S0_A3_CONTAMINATION_CHECK",
    "S0_ANMA_ORIG",
    "S0_GATE_A_POPULATION_E5",
    "S0_ALIGN_UNIT_COST",
    "STAGE1_PROBES",
    "SHAM_VALIDATION",
    "GATE_A",
    "GATE_B",
    "ROUTE_LOCK",
    "MAIN_EXPERIMENT",
}
ALLOWED_GATE_OUTCOMES = {None, "PASS", "FAIL", "INVALID"}
ALLOWED_EVIDENCE_GRADES = {
    None,
    "A_STRONG",
    "A_LIMITED",
    "A_FAIL",
    "B_STRONG",
    "B_LIMITED",
    "B_FAIL",
}
ALLOWED_ROUTES = {
    "EQ-ANMA",
    "CSPE",
    "MATCHED-NULL-EVIDENCE",
    "NEGATIVE-DIAGNOSTIC",
}

BRANCH_LOCAL_STATE_KIND = "branch_local_author_freeze"
BRANCH_LOCAL_TASK_STATUSES = {
    "READY",
    "DONE",
    "BLOCKED_UNTIL_R0_AUTHOR_REVIEW",
}
BRANCH_LOCAL_PARENT_OUTCOMES = {
    "real_a1_admission": "FAIL_A1_ADMISSION",
    "real_a1_recovery": "FAIL_A1R_RECOVERY",
    "run_032": "INVALID_A1_MEASUREMENT_VALIDITY_AUDIT",
    "synthetic_eq_anma": "FAIL_EQ_ANMA_SYNTHETIC_ADVANTAGE",
    "outer_negative_confirmation": "READY_NOT_RUN",
    "a3": "UNFINISHED",
    "roamm": "DEFERRED",
}
R1_BRANCH_SPEC = "v3.22_REAL_SHAM_R1_INNER_DIAGNOSTIC"
R2_BRANCH_SPEC = "v3.23_REAL_SHAM_R2_GEOMETRY_INNER"
R3_BRANCH_SPEC = "v3.24_REAL_SHAM_R3_SUBJECT_BALANCED_INNER"
R1_LEGAL_OUTCOMES = {
    "PASS_R1_BOTH_TASKS",
    "PASS_R1_LIMITED_ONE_TASK",
    "FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC",
    "INVALID_R1_REAL_SHAM_INNER_DIAGNOSTIC",
}
R1_FORMAL_HASHES = {
    "contract_sha256": (
        "artifacts/real_sham_r1_contract.yaml",
        "50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed",
    ),
    "json_sha256": (
        "04_results/diagnostics/real_sham_r1_inner.json",
        "610e40bf09959fb30f2a08f998b42148e9967168263a64c3ba37969194e964ff",
    ),
    "markdown_sha256": (
        "04_results/diagnostics/real_sham_r1_inner.md",
        "a858a7475b486bd874ace44435cc2de074c57391f6cdc9ffc102cb7f78c5beed",
    ),
    "ledger_sha256": (
        "04_results/diagnostics/real_sham_r1_inner_run_ledger.jsonl.gz",
        "28fc32b5103a1ba19b9c2cd2c724da5d7d3aff17f53f5ac72e3993e64db9314a",
    ),
}
R2_LEGAL_OUTCOMES = {
    "PASS_R2_INDUCTIVE_GEOMETRY",
    "PASS_R2_TRANSDUCTIVE_GEOMETRY_ONLY",
    "FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC",
    "INVALID_R2_GEOMETRY_INNER_DIAGNOSTIC",
}
R2_FORMAL_PATHS = {
    "contract_sha256": "artifacts/real_sham_r2_geometry_contract.yaml",
    "json_sha256": "04_results/diagnostics/real_sham_r2_geometry_inner.json",
    "markdown_sha256": "04_results/diagnostics/real_sham_r2_geometry_inner.md",
    "ledger_sha256": "04_results/diagnostics/real_sham_r2_geometry_inner_run_ledger.jsonl.gz",
    "transform_ledger_sha256": "04_results/diagnostics/real_sham_r2_geometry_inner_transform_ledger.jsonl.gz",
}
R3_LEGAL_OUTCOMES = {
    "PASS_R3_SUBJECT_BALANCED_INNER",
    "FAIL_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC",
    "INVALID_R3_SUBJECT_BALANCED_INNER_DIAGNOSTIC",
}
R3_FORMAL_PATHS = {
    "contract_sha256": "artifacts/real_sham_r3_subject_balanced_contract.yaml",
    "json_sha256": "04_results/diagnostics/real_sham_r3_subject_balanced_inner.json",
    "markdown_sha256": "04_results/diagnostics/real_sham_r3_subject_balanced_inner.md",
    "ledger_sha256": "04_results/diagnostics/real_sham_r3_subject_balanced_inner_run_ledger.jsonl.gz",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_yaml(path: Path, errors: list[str]) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle)
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return None
    except yaml.YAMLError as exc:
        errors.append(f"invalid YAML in {path}: {exc}")
        return None
    if value is None:
        errors.append(f"empty YAML file: {path}")
    return value


def _all_prerequisites_done(task_id: str, tasks: dict[str, Any]) -> bool:
    """Return False for incomplete or unknown prerequisites instead of crashing."""

    task = tasks.get(task_id)
    if not isinstance(task, dict):
        return False
    prerequisites = task.get("prerequisites", [])
    if not isinstance(prerequisites, list):
        return False
    return all(
        isinstance(tasks.get(item), dict) and tasks[item].get("status") == "DONE"
        for item in prerequisites
    )


def eligible_tasks(tasks: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    """Return tasks that can be started without ignoring recorded blockers."""

    blocked_ids = {
        task_id
        for blocker in blockers
        for task_id in blocker.get("blocks", [])
    }
    return sorted(
        task_id
        for task_id, task in tasks.items()
        if task.get("status") in {"TODO", "READY"}
        and task_id not in blocked_ids
        and _all_prerequisites_done(task_id, tasks)
    )


def _check_cycles(tasks: dict[str, Any], errors: list[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, chain: list[str]) -> None:
        if task_id in visiting:
            cycle = " -> ".join(chain + [task_id])
            errors.append(f"dependency cycle: {cycle}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for prerequisite in tasks[task_id].get("prerequisites", []):
            if prerequisite in tasks:
                visit(prerequisite, chain + [task_id])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id, [])


def _validate_r0_branch_local_freeze(
    root: Path, state: dict[str, Any], tasks: dict[str, Any]
) -> list[str]:
    """Validate the deliberately small v3.21 research-branch state schema."""

    errors: list[str] = []
    project = state.get("project", {})
    expected_project = {
        "parent_spec": "v3.20",
        "branch_spec": "v3.21_REAL_SHAM_RESCUE_RESEARCH",
        "branch_name": "research/real-sham-rescue",
        "base_commit": "86e4f370bab650ff73831627be102fc9a7ffe6a4",
    }
    for field, expected in expected_project.items():
        if project.get(field) != expected:
            errors.append(f"STATE_SPEC_CONFLICT: project.{field} != {expected!r}")
    spec_path = root / "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_21_2026-08-22.md"
    if not spec_path.is_file():
        errors.append(f"missing branch scientific spec: {spec_path}")
    freeze_path = root / "artifacts/real_sham_rescue_freeze.yaml"
    if not freeze_path.is_file():
        errors.append(f"missing branch author freeze: {freeze_path}")

    if state.get("immutable_parent_outcomes") != BRANCH_LOCAL_PARENT_OUTCOMES:
        errors.append("STATE_SPEC_CONFLICT: immutable parent outcomes changed")
    scope = state.get("scope", {})
    if scope.get("evidence_grade") != "RESEARCH_DIAGNOSTIC_ONLY":
        errors.append("branch evidence grade must be RESEARCH_DIAGNOSTIC_ONLY")
    if scope.get("outer_test_reads_allowed") is not False:
        errors.append("branch state must forbid outer-test reads")
    if scope.get("calibration_reads_allowed") is not False:
        errors.append("branch state must forbid calibration reads")

    expected_tasks = {"R0_REAL_SHAM_RESCUE_FREEZE", "R1_REAL_SHAM_INNER_DIAGNOSTIC"}
    if set(tasks) != expected_tasks:
        errors.append(f"branch TASKS.yaml must contain exactly {sorted(expected_tasks)}")
        return errors
    for task_id, task in tasks.items():
        if not isinstance(task, dict):
            errors.append(f"{task_id}: task entry must be a mapping")
            continue
        for field in ("title", "stage", "status", "prerequisites"):
            if field not in task:
                errors.append(f"{task_id}: missing field {field}")
        if task.get("status") not in BRANCH_LOCAL_TASK_STATUSES:
            errors.append(f"{task_id}: illegal branch-local status {task.get('status')!r}")
        if not isinstance(task.get("prerequisites"), list):
            errors.append(f"{task_id}: prerequisites must be a list")

    r0 = tasks["R0_REAL_SHAM_RESCUE_FREEZE"]
    current = state.get("current_task", {})
    if current.get("id") != "R0_REAL_SHAM_RESCUE_FREEZE":
        errors.append("current_task.id must remain R0_REAL_SHAM_RESCUE_FREEZE")
    if current.get("status") != r0.get("status"):
        errors.append("current_task.status does not match R0 task status")
    if current.get("new_eeg_fits") != 0:
        errors.append("R0 new_eeg_fits must be zero")
    if current.get("recommended_next") != "R1_REAL_SHAM_INNER_DIAGNOSTIC":
        errors.append("R0 recommended_next must be R1_REAL_SHAM_INNER_DIAGNOSTIC")
    if tasks["R1_REAL_SHAM_INNER_DIAGNOSTIC"].get("status") != "BLOCKED_UNTIL_R0_AUTHOR_REVIEW":
        errors.append("R1 must remain blocked until author review")
    if r0.get("status") == "DONE":
        if r0.get("completion_outcome") != "PASS_REAL_SHAM_RESCUE_FREEZE":
            errors.append("DONE R0 requires PASS_REAL_SHAM_RESCUE_FREEZE")
        if not r0.get("completed_by_run"):
            errors.append("DONE R0 requires completed_by_run")
        produced = r0.get("produces", [])
        if not isinstance(produced, list) or not produced:
            errors.append("DONE R0 requires produced artifacts")
        else:
            for artifact in produced:
                if not (root / artifact).is_file():
                    errors.append(f"R0 missing DONE artifact {artifact}")
    return errors


def _validate_r1_branch_local_freeze(
    root: Path, state: dict[str, Any], tasks: dict[str, Any]
) -> list[str]:
    """Validate the v3.22 R1 inner-only diagnostic state schema."""

    errors: list[str] = []
    project = state.get("project", {})
    expected_project = {
        "parent_spec": "v3.20",
        "branch_spec": R1_BRANCH_SPEC,
        "branch_name": "research/real-sham-r1-inner",
        "base_commit": "ec7ced2708fe68ae8614b6b89b03256d88d1b541",
        "parent_branch": "research/real-sham-rescue",
    }
    for field, expected in expected_project.items():
        if project.get(field) != expected:
            errors.append(f"STATE_SPEC_CONFLICT: project.{field} != {expected!r}")
    for required in (
        "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_22_2026-08-22.md",
        "artifacts/real_sham_r1_freeze.yaml",
    ):
        if not (root / required).is_file():
            errors.append(f"missing R1 branch freeze artifact: {required}")

    if state.get("immutable_parent_outcomes") != BRANCH_LOCAL_PARENT_OUTCOMES:
        errors.append("STATE_SPEC_CONFLICT: immutable parent outcomes changed")
    immutable_r0 = state.get("immutable_r0", {})
    expected_r0 = {
        "commit": "ec7ced2708fe68ae8614b6b89b03256d88d1b541",
        "outcome": "PASS_REAL_SHAM_RESCUE_FREEZE",
        "contract_sha256": "89f9bc468f5bea0bafe127baa1e0a96ceb5ff1c9327aba89e3445d86ed683055",
    }
    if immutable_r0 != expected_r0:
        errors.append("STATE_SPEC_CONFLICT: immutable R0 contract changed")

    scope = state.get("scope", {})
    if scope.get("evidence_grade") != "RESEARCH_DIAGNOSTIC_ONLY":
        errors.append("R1 evidence grade must be RESEARCH_DIAGNOSTIC_ONLY")
    if scope.get("outer_test_reads_allowed") is not False:
        errors.append("R1 state must forbid outer-test reads")
    if scope.get("calibration_reads_allowed") is not False:
        errors.append("R1 state must forbid calibration reads")
    if scope.get("alignment_scope") != "M0_STRICT_INDUCTIVE_ONLY":
        errors.append("R1 alignment scope must remain M0_STRICT_INDUCTIVE_ONLY")

    if set(tasks) != {"R1_REAL_SHAM_INNER_DIAGNOSTIC"}:
        errors.append("R1 TASKS.yaml must contain exactly R1_REAL_SHAM_INNER_DIAGNOSTIC")
        return errors
    task = tasks["R1_REAL_SHAM_INNER_DIAGNOSTIC"]
    if not isinstance(task, dict):
        return errors + ["R1 task entry must be a mapping"]
    for field in ("title", "stage", "status", "prerequisites"):
        if field not in task:
            errors.append(f"R1 task missing field {field}")
    if task.get("status") not in {"READY", "DONE"}:
        errors.append(f"R1 task has illegal status {task.get('status')!r}")
    if not isinstance(task.get("prerequisites"), list):
        errors.append("R1 prerequisites must be a list")

    current = state.get("current_task", {})
    if current.get("id") != "R1_REAL_SHAM_INNER_DIAGNOSTIC":
        errors.append("current_task.id must be R1_REAL_SHAM_INNER_DIAGNOSTIC")
    if current.get("status") != task.get("status"):
        errors.append("current_task.status does not match R1 task status")
    if current.get("forbidden_next_until_author_review") is not True:
        errors.append("R2 must remain forbidden until author review")

    if task.get("status") == "DONE":
        outcome = task.get("completion_outcome")
        if outcome not in R1_LEGAL_OUTCOMES:
            errors.append(f"DONE R1 has illegal outcome {outcome!r}")
        if current.get("outcome") != outcome:
            errors.append("current_task.outcome does not match R1 task outcome")
        if not task.get("completed_by_run"):
            errors.append("DONE R1 requires completed_by_run")
        produced = task.get("produces", [])
        if not isinstance(produced, list) or not produced:
            errors.append("DONE R1 requires produced artifacts")
        else:
            for artifact in produced:
                if not (root / artifact).is_file():
                    errors.append(f"R1 missing DONE artifact {artifact}")
        execution = state.get("execution_counts", {})
        expected_counts = {
            "h_only_y0_fits": 6,
            "y1_text_residualizer_fits": 6,
            "eeg_probe_fits": 144,
            "total_ridge_operations": 156,
            "v5_eeg_probe_ledgers": 150,
            "text_residualizer_ledgers": 6,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }
        for field, expected in expected_counts.items():
            if execution.get(field) != expected:
                errors.append(f"R1 execution_counts.{field} must be {expected}")
        if state.get("scope_violations") != [] or task.get("scope_violations") != []:
            errors.append("DONE R1 requires zero scope violations")
        recorded_hashes = state.get("formal_outputs", {})
        for field, (relative, expected) in R1_FORMAL_HASHES.items():
            if recorded_hashes.get(field) != expected:
                errors.append(f"R1 formal_outputs.{field} does not match frozen result")
                continue
            path = root / relative
            if path.is_file() and _sha256_file(path) != expected:
                errors.append(f"R1 formal output hash changed: {relative}")
    return errors


def _validate_r2_branch_local_freeze(
    root: Path, state: dict[str, Any], tasks: dict[str, Any]
) -> list[str]:
    """Validate the v3.23 R2 inner-only geometry diagnostic state."""

    errors: list[str] = []
    project = state.get("project", {})
    expected_project = {
        "parent_spec": "v3.20",
        "branch_spec": R2_BRANCH_SPEC,
        "branch_name": "research/real-sham-r2-geometry-inner",
        "base_commit": "012590ff1bc9c421644168a555511715bb30ec4a",
        "parent_branch": "research/real-sham-r1-inner",
    }
    for field, expected in expected_project.items():
        if project.get(field) != expected:
            errors.append(f"STATE_SPEC_CONFLICT: project.{field} != {expected!r}")
    for required in (
        "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_23_2026-08-23.md",
        "artifacts/real_sham_r2_freeze.yaml",
    ):
        if not (root / required).is_file():
            errors.append(f"missing R2 branch freeze artifact: {required}")
    if state.get("immutable_parent_outcomes") != BRANCH_LOCAL_PARENT_OUTCOMES:
        errors.append("STATE_SPEC_CONFLICT: immutable parent outcomes changed")
    expected_r0_r1 = {
        "r0_commit": "ec7ced2708fe68ae8614b6b89b03256d88d1b541",
        "r0_outcome": "PASS_REAL_SHAM_RESCUE_FREEZE",
        "r0_contract_sha256": "89f9bc468f5bea0bafe127baa1e0a96ceb5ff1c9327aba89e3445d86ed683055",
        "r1_commit": "012590ff1bc9c421644168a555511715bb30ec4a",
        "r1_outcome": "FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "r1_contract_sha256": "50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed",
        "r1_json_sha256": "610e40bf09959fb30f2a08f998b42148e9967168263a64c3ba37969194e964ff",
    }
    if state.get("immutable_r0_r1") != expected_r0_r1:
        errors.append("STATE_SPEC_CONFLICT: immutable R0/R1 contract changed")
    scope = state.get("scope", {})
    expected_scope = {
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "outer_test_reads_allowed": False,
        "calibration_reads_allowed": False,
        "primary_alignment_scope": "M0_STRICT_INDUCTIVE",
        "secondary_alignment_scope": "M1_UNLABELED_TRANSDUCTIVE_EA",
    }
    for field, expected in expected_scope.items():
        if scope.get(field) != expected:
            errors.append(f"R2 scope.{field} must be {expected!r}")
    if set(tasks) != {"R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC"}:
        errors.append("R2 TASKS.yaml must contain exactly its frozen task")
        return errors
    task = tasks["R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC"]
    if not isinstance(task, dict):
        return errors + ["R2 task entry must be a mapping"]
    for field in ("title", "stage", "status", "prerequisites"):
        if field not in task:
            errors.append(f"R2 task missing field {field}")
    if task.get("status") not in {"READY", "DONE"}:
        errors.append(f"R2 task has illegal status {task.get('status')!r}")
    if not isinstance(task.get("prerequisites"), list):
        errors.append("R2 prerequisites must be a list")
    current = state.get("current_task", {})
    if current.get("id") != "R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC":
        errors.append("current_task.id must be R2_REAL_SHAM_GEOMETRY_INNER_DIAGNOSTIC")
    if current.get("status") != task.get("status"):
        errors.append("current_task.status does not match R2 task status")
    if current.get("forbidden_next_until_author_review") is not True:
        errors.append("outer confirmation must remain forbidden until author review")

    if task.get("status") == "DONE":
        outcome = task.get("completion_outcome")
        if outcome not in R2_LEGAL_OUTCOMES:
            errors.append(f"DONE R2 has illegal outcome {outcome!r}")
        if current.get("outcome") != outcome:
            errors.append("current_task.outcome does not match R2 task outcome")
        if not task.get("completed_by_run"):
            errors.append("DONE R2 requires completed_by_run")
        produced = task.get("produces", [])
        if not isinstance(produced, list) or not produced:
            errors.append("DONE R2 requires produced artifacts")
        else:
            for artifact in produced:
                if not (root / artifact).is_file():
                    errors.append(f"R2 missing DONE artifact {artifact}")
        expected_counts = {
            "h_only_y0_fits": 6,
            "geometry_probe_fits": 96,
            "total_ridge_operations": 102,
            "unique_v5_ledgers": 102,
            "transform_ledger_rows": 300,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }
        execution = state.get("execution_counts", {})
        for field, expected in expected_counts.items():
            if execution.get(field) != expected:
                errors.append(f"R2 execution_counts.{field} must be {expected}")
        transform = state.get("transform_audit", {})
        if transform.get("labels_used") is not False:
            errors.append("R2 transform audit must record labels_used=false")
        if transform.get("shared_across_arms") is not True:
            errors.append("R2 transform audit must record shared_across_arms=true")
        if transform.get("fallback_count") != 0:
            errors.append("R2 transform audit must record zero fallback")
        if state.get("scope_violations") != [] or task.get("scope_violations") != []:
            errors.append("DONE R2 requires zero scope violations")
        recorded_hashes = state.get("formal_outputs", {})
        for field, relative in R2_FORMAL_PATHS.items():
            digest = recorded_hashes.get(field)
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"R2 formal_outputs.{field} must be SHA-256")
                continue
            path = root / relative
            if path.is_file() and _sha256_file(path) != digest:
                errors.append(f"R2 formal output hash changed: {relative}")
    return errors


def _validate_r3_branch_local_freeze(
    root: Path, state: dict[str, Any], tasks: dict[str, Any]
) -> list[str]:
    """Validate the v3.24 R3 fit-only subject-balanced diagnostic state."""

    errors: list[str] = []
    project = state.get("project", {})
    expected_project = {
        "parent_spec": "v3.20",
        "branch_spec": R3_BRANCH_SPEC,
        "branch_name": "research/real-sham-r3-subject-balanced",
        "base_commit": "a6fdf258ae89e4032e5e7afba61bba021fca186d",
        "parent_branch": "research/real-sham-r2-geometry-inner",
    }
    for field, expected in expected_project.items():
        if project.get(field) != expected:
            errors.append(f"STATE_SPEC_CONFLICT: project.{field} != {expected!r}")
    for required in (
        "guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_24_2026-08-24.md",
        "artifacts/real_sham_r3_freeze.yaml",
    ):
        if not (root / required).is_file():
            errors.append(f"missing R3 branch freeze artifact: {required}")
    if state.get("immutable_parent_outcomes") != BRANCH_LOCAL_PARENT_OUTCOMES:
        errors.append("STATE_SPEC_CONFLICT: immutable parent outcomes changed")
    expected_r0_r1_r2 = {
        "r0_commit": "ec7ced2708fe68ae8614b6b89b03256d88d1b541",
        "r0_outcome": "PASS_REAL_SHAM_RESCUE_FREEZE",
        "r1_commit": "012590ff1bc9c421644168a555511715bb30ec4a",
        "r1_outcome": "FAIL_R1_REAL_SHAM_INNER_DIAGNOSTIC",
        "r1_contract_sha256": "50a4d1ebf44af415a0de69ec66e4fe56bcaeb21acf70d262cfd80a59454779ed",
        "r2_commit": "a6fdf258ae89e4032e5e7afba61bba021fca186d",
        "r2_outcome": "FAIL_R2_GEOMETRY_INNER_DIAGNOSTIC",
        "r2_contract_sha256": "cb28e85029ec01dff3961e101a42d00672155ac7258641a077bf4bd6cf6eee78",
        "r2_json_sha256": "6aca8e2be1e062092a3ca7a4133cacd179e0fd73926240bd48739aedaa51426b",
    }
    if state.get("immutable_r0_r1_r2") != expected_r0_r1_r2:
        errors.append("STATE_SPEC_CONFLICT: immutable R0/R1/R2 contract changed")
    scope = state.get("scope", {})
    expected_scope = {
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "outer_test_reads_allowed": False,
        "calibration_reads_allowed": False,
        "alignment_scope": "M0_STRICT_INDUCTIVE_ONLY",
    }
    for field, expected in expected_scope.items():
        if scope.get(field) != expected:
            errors.append(f"R3 scope.{field} must be {expected!r}")
    if set(tasks) != {"R3_REAL_SHAM_SUBJECT_BALANCED_INNER_DIAGNOSTIC"}:
        errors.append("R3 TASKS.yaml must contain exactly its frozen task")
        return errors
    task = tasks["R3_REAL_SHAM_SUBJECT_BALANCED_INNER_DIAGNOSTIC"]
    if not isinstance(task, dict):
        return errors + ["R3 task entry must be a mapping"]
    for field in ("title", "stage", "status", "prerequisites"):
        if field not in task:
            errors.append(f"R3 task missing field {field}")
    if task.get("status") not in {"READY", "DONE"}:
        errors.append(f"R3 task has illegal status {task.get('status')!r}")
    if not isinstance(task.get("prerequisites"), list):
        errors.append("R3 prerequisites must be a list")
    current = state.get("current_task", {})
    if current.get("id") != "R3_REAL_SHAM_SUBJECT_BALANCED_INNER_DIAGNOSTIC":
        errors.append("current_task.id must be R3 subject-balanced diagnostic")
    if current.get("status") != task.get("status"):
        errors.append("current_task.status does not match R3 task status")
    if current.get("forbidden_next_until_author_review") is not True:
        errors.append("outer confirmation must remain forbidden until author review")

    if task.get("status") == "DONE":
        outcome = task.get("completion_outcome")
        if outcome not in R3_LEGAL_OUTCOMES:
            errors.append(f"DONE R3 has illegal outcome {outcome!r}")
        if current.get("outcome") != outcome:
            errors.append("current_task.outcome does not match R3 task outcome")
        if not task.get("completed_by_run"):
            errors.append("DONE R3 requires completed_by_run")
        produced = task.get("produces", [])
        if not isinstance(produced, list) or not produced:
            errors.append("DONE R3 requires produced artifacts")
        else:
            for artifact in produced:
                if not (root / artifact).is_file():
                    errors.append(f"R3 missing DONE artifact {artifact}")
        expected_counts = {
            "h_only_p0_fits": 6,
            "h_only_p1_fits": 6,
            "p0_probe_fits": 24,
            "p1_probe_fits": 24,
            "total_ridge_operations": 60,
            "unique_v5_ledgers": 60,
            "group_scope_count": 6,
            "outer_test_reads": 0,
            "calibration_reads": 0,
        }
        execution = state.get("execution_counts", {})
        for field, expected in expected_counts.items():
            if execution.get(field) != expected:
                errors.append(f"R3 execution_counts.{field} must be {expected}")
        group_audit = state.get("group_audit", {})
        if group_audit.get("fit_rows_only") is not True:
            errors.append("R3 group audit must record fit_rows_only=true")
        if group_audit.get("subject_id_input_to_probe") is not False:
            errors.append("R3 group audit must forbid subject ID probe input")
        if group_audit.get("same_individual_scoring_rows_p0_p1") is not True:
            errors.append("R3 P0/P1 scoring row identity must be true")
        if state.get("scope_violations") != [] or task.get("scope_violations") != []:
            errors.append("DONE R3 requires zero scope violations")
        recorded_hashes = state.get("formal_outputs", {})
        for field, relative in R3_FORMAL_PATHS.items():
            digest = recorded_hashes.get(field)
            if not isinstance(digest, str) or len(digest) != 64:
                errors.append(f"R3 formal_outputs.{field} must be SHA-256")
                continue
            path = root / relative
            if path.is_file() and _sha256_file(path) != digest:
                errors.append(f"R3 formal output hash changed: {relative}")
    return errors


def _validate_branch_local_freeze(
    root: Path, state: dict[str, Any], tasks: dict[str, Any]
) -> list[str]:
    branch_spec = state.get("project", {}).get("branch_spec")
    if branch_spec == R3_BRANCH_SPEC:
        return _validate_r3_branch_local_freeze(root, state, tasks)
    if branch_spec == R2_BRANCH_SPEC:
        return _validate_r2_branch_local_freeze(root, state, tasks)
    if branch_spec == R1_BRANCH_SPEC:
        return _validate_r1_branch_local_freeze(root, state, tasks)
    return _validate_r0_branch_local_freeze(root, state, tasks)


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    state_path = root / "PROJECT_STATE.yaml"
    tasks_path = root / "TASKS.yaml"
    state = _load_yaml(state_path, errors)
    tasks = _load_yaml(tasks_path, errors)
    if not isinstance(state, dict) or not isinstance(tasks, dict):
        return errors

    if state.get("state_kind") == BRANCH_LOCAL_STATE_KIND:
        return errors + _validate_branch_local_freeze(root, state, tasks)

    missing = sorted(REQUIRED_TASK_IDS - set(tasks))
    if missing:
        errors.append("TASKS.yaml missing required tasks: " + ", ".join(missing))

    for task_id, task in tasks.items():
        if not isinstance(task, dict):
            errors.append(f"{task_id}: task entry must be a mapping")
            continue
        missing_fields = sorted(REQUIRED_TASK_FIELDS - set(task))
        if missing_fields:
            errors.append(f"{task_id}: missing fields: {', '.join(missing_fields)}")
        status = task.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{task_id}: illegal status {status!r}")
        for field in ("prerequisites", "produces", "acceptance"):
            if field in task and not isinstance(task[field], list):
                errors.append(f"{task_id}: {field} must be a list")
        for prerequisite in task.get("prerequisites", []):
            if prerequisite not in tasks:
                errors.append(f"{task_id}: unknown prerequisite {prerequisite}")
        if status == "BLOCKED" and not task.get("blocked_reason"):
            errors.append(f"{task_id}: BLOCKED requires blocked_reason")
        if status == "DONE":
            if not _all_prerequisites_done(task_id, tasks):
                errors.append(f"{task_id}: DONE has unfinished prerequisites")
            if not task.get("produces"):
                errors.append(f"{task_id}: DONE requires at least one produced artifact")
            if not task.get("completed_by_run"):
                errors.append(f"{task_id}: DONE requires completed_by_run")
            for artifact in task.get("produces", []):
                if not (root / artifact).exists():
                    errors.append(f"{task_id}: missing DONE artifact {artifact}")
        if status == "READY":
            if not _all_prerequisites_done(task_id, tasks):
                errors.append(f"{task_id}: READY has unfinished prerequisites")

    _check_cycles(tasks, errors)

    blockers = state.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("PROJECT_STATE.yaml: blockers must be a list")
        blockers = []
    blocked_ids: set[str] = set()
    for blocker in blockers:
        if not isinstance(blocker, dict):
            errors.append("blocker entry must be a mapping")
            continue
        for field in ("id", "reason", "blocks", "resolution"):
            if not blocker.get(field):
                errors.append(f"blocker missing non-empty {field}")
        for task_id in blocker.get("blocks", []):
            if task_id not in tasks:
                errors.append(f"blocker {blocker.get('id')}: unknown task {task_id}")
            else:
                blocked_ids.add(task_id)

    for task_id, task in tasks.items():
        if isinstance(task, dict) and task.get("status") == "READY" and task_id in blocked_ids:
            errors.append(f"{task_id}: READY task is named by an active blocker")

    project = state.get("project", {})
    spec_path = project.get("spec_path")
    if not spec_path or not (root / spec_path).exists():
        errors.append(f"missing scientific spec: {spec_path!r}")
    for field in ("server_root", "python_path"):
        value = project.get(field)
        if isinstance(value, str) and "trust_algin" in value:
            errors.append(f"{field} contains stale project directory trust_algin")
    backbones = state.get("scope", {}).get("backbones", {})
    spec_backbones = set(backbones.get("spec_defined", []))
    active_backbones = set(backbones.get("active", []))
    if not active_backbones.issubset(spec_backbones):
        errors.append(
            "STATE_SPEC_CONFLICT: active backbones are not a subset of guide-defined backbones"
        )

    execution = state.get("execution", {})
    if execution.get("status") not in ALLOWED_STATUSES:
        errors.append(f"execution.status is illegal: {execution.get('status')!r}")
    for gate_name in ("gate_a", "gate_b"):
        gate = state.get("gates", {}).get(gate_name, {})
        gate_status = gate.get("status")
        outcome = gate.get("outcome")
        grade = gate.get("evidence_grade")
        if gate_status not in ALLOWED_STATUSES:
            errors.append(f"{gate_name}: illegal status {gate_status!r}")
        if outcome not in ALLOWED_GATE_OUTCOMES:
            errors.append(f"{gate_name}: illegal outcome {outcome!r}")
        if grade not in ALLOWED_EVIDENCE_GRADES:
            errors.append(f"{gate_name}: illegal evidence_grade {grade!r}")
        task_id = "GATE_A" if gate_name == "gate_a" else "GATE_B"
        if task_id in tasks and gate_status != tasks[task_id].get("status"):
            errors.append(f"{gate_name}: state status does not match {task_id} task status")
        if gate_status == "DONE" and outcome is None:
            errors.append(f"{gate_name}: DONE requires an outcome")
        if gate_status != "DONE" and outcome is not None:
            errors.append(f"{gate_name}: non-DONE gate must not have an outcome")

    gate_a = state.get("gates", {}).get("gate_a", {})
    gate_b = state.get("gates", {}).get("gate_b", {})
    if gate_b.get("status") in {"IN_PROGRESS", "DONE"}:
        if gate_a.get("status") != "DONE" or gate_a.get("outcome") != "PASS":
            errors.append("GATE_B may start only after Gate A PASS")

    route = state.get("route", {})
    locked = route.get("locked")
    if isinstance(locked, list):
        if len(locked) > 1:
            errors.append("EQ-ANMA and CSPE cannot be simultaneously locked")
        locked_values = set(locked)
        if not locked_values.issubset(ALLOWED_ROUTES):
            errors.append(f"route.locked has illegal values: {sorted(locked_values)}")
    elif locked is not None and locked not in ALLOWED_ROUTES:
        errors.append(f"route.locked has illegal value: {locked!r}")
    if route.get("primary") == route.get("backup"):
        errors.append("route primary and backup must be distinct")
    if locked is not None:
        if tasks.get("ROUTE_LOCK", {}).get("status") != "DONE":
            errors.append("route is locked before ROUTE_LOCK is DONE")
        if not route.get("locked_by_run"):
            errors.append("locked route requires locked_by_run")
        if tasks.get("MAIN_EXPERIMENT", {}).get("status") in {"IN_PROGRESS", "DONE"}:
            if tasks.get("ROUTE_LOCK", {}).get("status") != "DONE":
                errors.append("MAIN_EXPERIMENT started before route lock")
    if tasks.get("MAIN_EXPERIMENT", {}).get("status") in {"IN_PROGRESS", "DONE"}:
        if locked is None or tasks.get("ROUTE_LOCK", {}).get("status") != "DONE":
            errors.append("MAIN_EXPERIMENT requires a completed route lock")

    last_completed = state.get("last_completed_task")
    if last_completed and tasks.get(last_completed, {}).get("status") != "DONE":
        errors.append(f"last_completed_task is not DONE: {last_completed}")
    last_run = state.get("last_run")
    if not last_run or not (root / last_run).exists():
        errors.append(f"missing last_run record: {last_run!r}")

    candidates = eligible_tasks(tasks, blockers)
    recommended = state.get("recommended_next_task")
    if candidates and recommended not in candidates:
        errors.append(
            f"recommended_next_task {recommended!r} is not currently eligible; eligible={candidates}"
        )
    if not candidates and recommended is not None:
        errors.append(
            f"recommended_next_task must be null when no task is eligible; got {recommended!r}"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="project root (defaults to the parent of scripts/)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        print("PROJECT STATE INVALID")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    tasks = _load_yaml(root / "TASKS.yaml", [])
    done_count = sum(task.get("status") == "DONE" for task in tasks.values())
    print(f"PROJECT STATE VALID | tasks={len(tasks)} | done={done_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
