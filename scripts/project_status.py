#!/usr/bin/env python3
"""Print a compact, cold-start project snapshot and critical-path recommendation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from check_project_state import eligible_tasks, validate


def _load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _descendant_count(task_id: str, tasks: dict) -> int:
    reverse = {
        candidate: set()
        for candidate in tasks
    }
    for candidate, task in tasks.items():
        for prerequisite in task.get("prerequisites", []):
            reverse.setdefault(prerequisite, set()).add(candidate)
    seen: set[str] = set()
    stack = list(reverse.get(task_id, set()))
    while stack:
        child = stack.pop()
        if child in seen:
            continue
        seen.add(child)
        stack.extend(reverse.get(child, set()))
    return len(seen)


def _rank(task_id: str, tasks: dict) -> tuple:
    task = tasks[task_id]
    return (
        0 if task.get("critical_path") else 1,
        int(task.get("priority", 1000)),
        -_descendant_count(task_id, tasks),
        task_id,
    )


def _render_branch_local(state: dict, tasks: dict, errors: list[str]) -> str:
    current = state.get("current_task", {})
    parent = state.get("immutable_parent_outcomes", {})
    is_r1 = (
        state.get("project", {}).get("branch_spec")
        == "v3.22_REAL_SHAM_R1_INNER_DIAGNOSTIC"
    )
    if is_r1:
        execution = state.get("execution_counts", {})
        if current.get("status") == "DONE":
            boundary = (
                "R1 inner-only | ridge operations="
                f"{execution.get('total_ridge_operations')} | EEG V5/text ledgers="
                f"{execution.get('v5_eeg_probe_ledgers')}/"
                f"{execution.get('text_residualizer_ledgers')} | outer/calibration reads="
                f"{execution.get('outer_test_reads')}/{execution.get('calibration_reads')}"
            )
        else:
            boundary = (
                "R1 inner-only frozen budget | ridge operations=156 "
                "(6 H-only + 6 text residualizers + 144 EEG probes) | "
                "outer/calibration reads=0/0"
            )
        next_task = (
            "R2_REAL_SHAM_OUTER_CONFIRMATION_FREEZE_IF_R1_PASS is forbidden "
            "until author review; do not start it automatically."
        )
        forbidden = (
            "F3, M1, outer confirmation, calibration, alignment, direct u+, "
            "EQ-ANMA, Gate A/B, A3, and ROAMM"
        )
    else:
        boundary = "existing artifacts only | new EEG fits=0 | outer/calibration reads=0/0"
        next_task = "R1_REAL_SHAM_INNER_DIAGNOSTIC only after author review; currently blocked."
        forbidden = "alignment, direct u+, EQ-ANMA, Gate A/B, A3, and ROAMM"
    lines = [
        "PROJECT SNAPSHOT",
        "",
        "State kind: branch_local_author_freeze",
        f"Branch: {state.get('project', {}).get('branch_name')}",
        f"Base commit: {state.get('project', {}).get('base_commit')}",
        f"Current task: {current.get('id')} ({current.get('status')})",
        f"Outcome: {current.get('outcome', 'not executed')}",
        f"Evidence grade: {state.get('scope', {}).get('evidence_grade')}",
        f"Execution boundary: {boundary}",
        "Immutable parent outcomes:",
    ]
    lines.extend(f"- {key}: {value}" for key, value in parent.items())
    lines.extend(
        [
            "",
            "Next task:",
            next_task,
            "",
            "Forbidden releases:",
            f"- {forbidden}",
            "",
            "Validator:",
            "INVALID" if errors else "VALID",
        ]
    )
    if errors:
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def render(root: Path) -> str:
    errors = validate(root)
    state = _load(root / "PROJECT_STATE.yaml")
    tasks = _load(root / "TASKS.yaml")
    if state.get("state_kind") == "branch_local_author_freeze":
        return _render_branch_local(state, tasks, errors)
    blockers = state.get("blockers", [])
    candidates = sorted(eligible_tasks(tasks, blockers), key=lambda task_id: _rank(task_id, tasks))
    recommended = state.get("recommended_next_task")
    if recommended not in candidates:
        recommended = candidates[0] if candidates else None

    route = state.get("route", {})
    locked = route.get("locked") or "unlocked"
    done_tasks = [task_id for task_id, task in tasks.items() if task.get("status") == "DONE"]
    lines = [
        "PROJECT SNAPSHOT",
        "",
        f"Current stage: {state['execution']['stage']} ({state['execution']['status']})",
        f"Current route: {locked} | primary={route.get('primary')} | backup={route.get('backup')}",
        "Completed prerequisites:",
    ]
    if done_tasks:
        lines.extend(f"- {task_id}: {tasks[task_id]['title']}" for task_id in done_tasks)
    else:
        lines.append("- none")
    lines.append("Active blockers:")
    if blockers:
        lines.extend(f"- {item['id']}: {item['reason']}" for item in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "Ready tasks:"])
    if candidates:
        for index, task_id in enumerate(candidates, 1):
            lines.append(f"{index}. {task_id}: {tasks[task_id]['title']}")
    else:
        lines.append("1. none")
    lines.extend(["", "Recommended next task:"])
    if recommended:
        lines.append(f"{recommended}: {tasks[recommended]['title']}")
        lines.append(f"Why: {tasks[recommended].get('why_ready', tasks[recommended].get('acceptance', [''])[0])}")
    else:
        lines.append("none")
        lines.append("Why: no task currently satisfies its prerequisites without a blocker.")
    lines.extend(["", "Do not do yet:"])
    do_not_do_yet = state.get("do_not_do_yet", [])
    if do_not_do_yet:
        lines.extend(f"- {item}" for item in do_not_do_yet)
    else:
        lines.append("- none")
    lines.extend(["", "Blocked downstream:"])
    blocked_tasks = [
        task_id for task_id, task in tasks.items() if task.get("status") == "BLOCKED"
    ]
    if blocked_tasks:
        for task_id in sorted(blocked_tasks, key=lambda item: _rank(item, tasks)):
            task = tasks[task_id]
            reason = task.get("blocked_reason", "prerequisites incomplete")
            lines.append(f"- {task_id}: {reason}")
    else:
        lines.append("- none")
    if errors:
        lines.extend(["", "Validator:", "INVALID"])
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.extend(["", "Validator:", "VALID"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="project root (defaults to the parent of scripts/)",
    )
    args = parser.parse_args(argv)
    print(render(args.root.resolve()))
    return 0 if not validate(args.root.resolve()) else 1


if __name__ == "__main__":
    sys.exit(main())
