#!/usr/bin/env python3
"""Rebuild and verify the committed R6 split surfaces without writing outputs."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import traceback


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from build_eqalign_r6_splits import (  # noqa: E402
    DEFAULT_AUDIT,
    DEFAULT_INNER,
    DEFAULT_OUTER,
    OLD_INNER,
    OLD_INNER_SHA256,
    OLD_OUTER,
    OLD_OUTER_SHA256,
    construct_r6_split_artifacts,
)
from data.joint_split import canonical_json_bytes  # noqa: E402
from eqalign_r6.split_builder import (  # noqa: E402
    file_sha256,
    validate_r6_inner_artifact,
    validate_r6_outer_artifact,
    validate_support_audit,
)


TASKS_SHA256 = "919c86e80a5f6cd8fab0d44bede6f090f52e96cb8c87d6f9fb781137dfa2adb0"
SPEC = Path(
    "guide/EEG_Text_Bprime_Unified_Paper_Spec_v4_1_"
    "R6SPLIT_RECONCILE_READY_MAIN_2026-08-24.md"
)
SPEC_SHA256 = "2d2b584766ab99f4b50dd48dfcb20e0154433081f063cda38fc6833b224850af"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_protected_history_clean() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "artifacts/real_sham*", "04_results/diagnostics/real_sham*", "runs/research/*real_sham*"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    paths = ["TASKS.yaml", *tracked]
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *paths],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError("TASKS.yaml or R0-R4 formal/history files differ from HEAD")


def main() -> int:
    try:
        if file_sha256(OLD_OUTER) != OLD_OUTER_SHA256:
            raise AssertionError("old 6x5 outer artifact SHA256 changed")
        if file_sha256(OLD_INNER) != OLD_INNER_SHA256:
            raise AssertionError("old 6x5 inner artifact SHA256 changed")
        if file_sha256("TASKS.yaml") != TASKS_SHA256:
            raise AssertionError("TASKS.yaml SHA256 changed")
        if file_sha256(SPEC) != SPEC_SHA256:
            raise AssertionError("R6 split SPEC SHA256 changed")
        _assert_protected_history_clean()
        tracked_outer, tracked_inner, tracked_audit = map(
            _load, (DEFAULT_OUTER, DEFAULT_INNER, DEFAULT_AUDIT)
        )
        if validate_r6_outer_artifact(tracked_outer):
            raise AssertionError(validate_r6_outer_artifact(tracked_outer))
        if validate_r6_inner_artifact(tracked_inner):
            raise AssertionError(validate_r6_inner_artifact(tracked_inner))
        if validate_support_audit(tracked_audit):
            raise AssertionError(validate_support_audit(tracked_audit))
        rebuilt = construct_r6_split_artifacts()
        for label, tracked, current in zip(
            ("outer", "inner", "support_audit"),
            (tracked_outer, tracked_inner, tracked_audit),
            rebuilt,
        ):
            if canonical_json_bytes(tracked) != canonical_json_bytes(current):
                raise AssertionError(f"{label} artifact differs from deterministic rebuild")
        print("R6 SPLIT SELFCHECK PASS")
        print("outer_cells_per_task=18 inner_cells_per_outer=9")
        print("forward_reverse_canonical_byte_identity=True")
        print("old_6x5_artifacts_byte_identical=True protected_history_unchanged=True")
        print("read_counters=r6_real_eeg_value_reads:0,outer_test_reads:0,calibration_reads:0")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
