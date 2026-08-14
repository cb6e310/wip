#!/usr/bin/env python3
"""Validate the small, file-based project memory system.

The validator is deliberately conservative: missing evidence is an error only when a
task claims DONE, while unresolved scientific facts remain explicit blockers.
"""

from __future__ import annotations

import argparse
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


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    state_path = root / "PROJECT_STATE.yaml"
    tasks_path = root / "TASKS.yaml"
    state = _load_yaml(state_path, errors)
    tasks = _load_yaml(tasks_path, errors)
    if not isinstance(state, dict) or not isinstance(tasks, dict):
        return errors

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
