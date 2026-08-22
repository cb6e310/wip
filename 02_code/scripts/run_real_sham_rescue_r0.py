#!/usr/bin/env python3
"""Run only the v3.21 existing-artifact real-vs-sham R0 diagnosis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from data.a1_admission import canonical_artifact, deterministic_gzip_jsonl  # noqa: E402
from data.a1_failure_diagnosis import sha256_file  # noqa: E402
from data.real_sham_rescue import (  # noqa: E402
    ADMISSION_JSON,
    ADMISSION_LEDGER,
    BASES,
    PARENT_FORMAL_HASHES,
    RECOVERY_JSON,
    RUN_ID,
    SHAMS,
    TASKS,
    build_r0_diagnosis,
)


FREEZE_PATH = Path("artifacts/real_sham_rescue_freeze.yaml")
SPEC_PATH = Path("guide/EEG_Text_Bprime_Unified_Paper_Spec_v3_21_2026-08-22.md")
CONTRACT_PATH = Path("artifacts/real_sham_rescue_contract.yaml")
RESULT_JSON_PATH = Path("04_results/diagnostics/real_sham_rescue_r0.json")
RESULT_MD_PATH = Path("04_results/diagnostics/real_sham_rescue_r0.md")
LEDGER_PATH = Path("04_results/diagnostics/real_sham_rescue_r0_run_ledger.jsonl.gz")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--contract-output", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--json-output", type=Path, default=RESULT_JSON_PATH)
    parser.add_argument("--markdown-output", type=Path, default=RESULT_MD_PATH)
    parser.add_argument("--ledger-output", type=Path, default=LEDGER_PATH)
    return parser.parse_args()


def _markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Real-vs-sham rescue R0 diagnostic",
        "",
        f"- Outcome: `{payload['outcome']}`",
        "- Evidence grade: `RESEARCH_DIAGNOSTIC_ONLY`",
        "- Parent outcomes: immutable",
        "- New EEG fits: `0`",
        "- Outer-test/calibration reads: `0/0`",
        "- Channel-block permutation: retained as topology sentinel",
        "",
        "## Existing-artifact contrasts",
        "",
        "| Task | Basis | delta_semantic | delta_legacy | delta_channel | old u_min |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for task in TASKS:
        for basis in BASES:
            cell = payload["diagnostics"][task][basis]
            lines.append(
                "| {task} | {basis} | {semantic:.10f} | {legacy:.10f} | "
                "{channel:.10f} | {u_min:.10f} |".format(
                    task=task,
                    basis=basis,
                    semantic=cell["delta_semantic"]["estimate"],
                    legacy=cell["delta_legacy"]["estimate"],
                    channel=cell["delta_channel"]["estimate"],
                    u_min=cell["legacy_sensitivity"]["u_min"]["estimate"],
                )
            )
    lines.extend(
        [
            "",
            "The old `u_oof`, `u_min`, and all three single-sham contrasts are retained "
            "in the JSON with explicit reproduction checks. These are diagnostic "
            "recalculations, not real EEG incremental evidence.",
            "",
            "## Claim boundary",
            "",
            "R0 releases no alignment, direct u+, EQ-ANMA, Gate A, Gate B, A3, or "
            "ROAMM result. The parent admission, recovery, run-032, synthetic-method, "
            "and outer-confirmation states remain unchanged.",
            "",
            "The only next step is author review followed, if separately authorized, by "
            "`R1_REAL_SHAM_INNER_DIAGNOSTIC`. R1 was not executed here.",
            "",
        ]
    )
    return "\n".join(lines)


def _contract(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    freeze = yaml.safe_load((root / FREEZE_PATH).read_text(encoding="utf-8"))
    if not isinstance(freeze, dict) or freeze.get("outcome") != "PASS_REAL_SHAM_RESCUE_FREEZE":
        raise RuntimeError("STATE_SPEC_CONFLICT: R0 author freeze is not admitted")
    if freeze.get("base_commit") != "86e4f370bab650ff73831627be102fc9a7ffe6a4":
        raise RuntimeError("STATE_SPEC_CONFLICT: R0 base commit changed")
    return {
        "schema_version": 1,
        "task": "R0_REAL_SHAM_RESCUE_FREEZE",
        "run_id": RUN_ID,
        "branch": "research/real-sham-rescue",
        "base_commit": freeze["base_commit"],
        "governing_spec": {
            "path": str(SPEC_PATH),
            "sha256": sha256_file(root / SPEC_PATH),
            "status": "BRANCH_LOCAL_AUTHOR_OVERLAY",
        },
        "author_freeze": {
            "path": str(FREEZE_PATH),
            "sha256": sha256_file(root / FREEZE_PATH),
        },
        "evidence_grade": "RESEARCH_DIAGNOSTIC_ONLY",
        "scope": {
            "tasks": list(TASKS),
            "bases": list(BASES),
            "shams": list(SHAMS),
            "source_artifacts": [str(ADMISSION_JSON), str(ADMISSION_LEDGER), str(RECOVERY_JSON)],
            "existing_artifact_reanalysis_only": True,
            "new_eeg_fits": 0,
            "outer_test_eeg_label_metric_reads": 0,
            "calibration_reads": 0,
        },
        "estimands": payload["diagnostic_estimands"],
        "old_value_reproduction_required": [
            "u_oof",
            "u_min",
            "real_minus_trial_shuffle",
            "real_minus_within_trial_unit_assignment_shuffle",
            "real_minus_channel_block_permutation",
        ],
        "parent_formal_hashes": dict(PARENT_FORMAL_HASHES),
        "outcome_rule": {
            "valid": "PASS_REAL_SHAM_RESCUE_FREEZE",
            "invalid": "INVALID_REAL_SHAM_RESCUE_R0",
            "observed": payload["outcome"],
        },
        "claim_boundary": payload["claim_boundary"],
        "next_task": "R1_REAL_SHAM_INNER_DIAGNOSTIC_AFTER_AUTHOR_REVIEW_ONLY",
    }


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    payload, ledger_rows = build_r0_diagnosis(root)
    contract = _contract(root, payload)
    outputs = {
        args.contract_output: yaml.safe_dump(contract, sort_keys=False, allow_unicode=False).encode("utf-8"),
        args.json_output: canonical_artifact(payload),
        args.markdown_output: _markdown(payload).encode("utf-8"),
        args.ledger_output: deterministic_gzip_jsonl(ledger_rows),
    }
    for relative, contents in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    print(
        json.dumps(
            {
                "outcome": payload["outcome"],
                "new_eeg_fits": 0,
                "outer_test_reads": 0,
                "calibration_reads": 0,
                "parent_v5_ledgers_validated": payload["execution"]["source_v5_ledgers_validated"],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["outcome"] == "PASS_REAL_SHAM_RESCUE_FREEZE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
