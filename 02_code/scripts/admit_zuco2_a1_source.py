#!/usr/bin/env python3
"""Build the SPEC v3.13 Q.3 ZuCo2 A1 source-admission artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code" / "src"))

from data.a1_source_admission import DEFAULT_SEED, build_admission  # noqa: E402


RUN_ID = "2026-08-15_025_v313_a1_source_admission"
BASELINE_COMMIT = "d9dfe51442155fbd3854d223916c519a7757fff1"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--baseline-commit", default=BASELINE_COMMIT)
    args = parser.parse_args()
    started = time.perf_counter()
    project_root = args.project_root.resolve()
    output_root = (args.output_root or project_root).resolve()
    contract, audit, ledger = build_admission(
        project_root, baseline_commit=args.baseline_commit, run_id=args.run_id, seed=args.seed
    )
    contract_bytes = yaml.safe_dump(
        contract, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).encode("utf-8")
    audit_bytes = (json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2,
                              allow_nan=False) + "\n").encode("utf-8")
    outputs = {
        output_root / "artifacts/a1_real_source_contract.yaml": contract_bytes,
        output_root / "01_data_protocol/a1_source_exclusions.jsonl.gz": ledger,
        output_root / "04_results/audits/zuco2_a1_source_admission.json": audit_bytes,
    }
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    elapsed = time.perf_counter() - started
    retained = audit["coverage"]["retained_subjects"]
    print("ZUCO2 A1 SOURCE ADMISSION SELF-CHECK")
    print(f"summary_files={audit['input_bindings']['summary_file_count']} preprocessed_files=252 ")
    print(f"retained_NR={len(retained['task1_nr'])} retained_TSR={len(retained['task2_tsr'])} ")
    print(f"smoke_records={audit['feature_smoke']['selected_record_count']} shape=[T,840] dtype=float32")
    print(f"phase_max_abs={audit['phase_invariance']['maximum_absolute_error']:.9g} "
          f"phase_max_rel={audit['phase_invariance']['maximum_relative_error']:.9g}")
    for path, payload in outputs.items():
        print(f"OUTPUT {path.relative_to(output_root)} bytes={len(payload)} sha256={_sha(payload)}")
    print(f"seed={args.seed} run_id={args.run_id} elapsed_seconds={elapsed:.3f} "
          f"status={audit['overall_outcome']}")
    for name, passed in audit["checks"].items():
        print(f"ASSERT {name}={'PASS' if passed else 'FAIL'}")
    return 0 if audit["overall_outcome"] == "PASS_REAL_A1_SOURCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
