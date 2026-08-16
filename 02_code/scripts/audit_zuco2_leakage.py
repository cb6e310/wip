#!/usr/bin/env python3
"""Run SPEC v3.12 V1--V5 pre-run leakage admission."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "02_code" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from protocol.leakage_audit import (  # noqa: E402
    DEFAULT_RUN_ID,
    build_pre_run_audit,
    file_sha256,
    write_audit_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "04_results/audits/zuco2_pre_run_leakage_audit.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "01_data_protocol/leakage_audit.md",
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    try:
        audit = build_pre_run_audit(args.project_root, run_id=args.run_id)
        before = {
            name: value["file_sha256"] for name, value in audit["input_bindings"].items()
        }
        written = write_audit_outputs(
            audit, json_path=args.json_output, markdown_path=args.markdown_output
        )
        after = {
            name: file_sha256(args.project_root / value["path"])
            for name, value in audit["input_bindings"].items()
        }
        if before != after:
            raise AssertionError("immutable input changed during leakage audit")
        result = {
            "status": "PASS",
            "run_id": args.run_id,
            "overall_outcome": audit["overall_outcome"],
            "V1": audit["checks"]["V1"]["outcome"],
            "V2": audit["checks"]["V2"]["outcome"],
            "V3": audit["checks"]["V3"]["outcome"],
            "V4": audit["checks"]["V4"]["outcome"],
            "V5": audit["checks"]["V5"]["outcome"],
            "future_run_admission_required": audit["future_run_admission_required"],
            "real_training_ledgers_audited": audit["real_training_ledgers_audited"],
            "outer_cells": audit["checks"]["V1"]["outer_cell_count"],
            "inner_cells": audit["checks"]["V1"]["inner_cell_count"],
            "candidate_targets": audit["checks"]["V4"]["target_count"],
            "candidate_repeats": audit["checks"]["V4"]["repeat_count"],
            "immutable_inputs_unchanged": True,
            "written": written,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "assertions": {
                "eeg_read": False,
                "training_run": False,
                "future_training_leakage_claimed": False,
                "roamm_read": False,
            },
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
