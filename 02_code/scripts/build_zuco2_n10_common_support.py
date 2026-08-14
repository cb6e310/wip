#!/usr/bin/env python3
"""Build the admitted ZuCo2 N=10 common-support scoring artifacts."""

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

from data.candidate_common_support import (  # noqa: E402
    BASE_FILE_SHA256,
    DEFAULT_RUN_ID,
    canonical_triplet_bytes,
    derive_common_support,
    load_verified_base_triplet,
    reverse_scope_target_order,
    write_common_support_triplet,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-input",
        type=Path,
        default=ROOT / "01_data_protocol/candidates/candidate_lists.json",
    )
    parser.add_argument(
        "--pair-input",
        type=Path,
        default=ROOT / "01_data_protocol/candidates/paired_verification_pairs.json",
    )
    parser.add_argument(
        "--audit-input",
        type=Path,
        default=ROOT / "04_results/audits/zuco2_candidate_feasibility.json",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=ROOT / "01_data_protocol/candidates/candidate_lists_n10_common_support.json",
    )
    parser.add_argument(
        "--pair-output",
        type=Path,
        default=ROOT / "01_data_protocol/candidates/paired_verification_pairs_n10.json",
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=ROOT / "04_results/audits/zuco2_n10_common_support_audit.json",
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    try:
        candidates, pairs, audit, physical_hashes = load_verified_base_triplet(
            args.candidate_input, args.pair_input, args.audit_input
        )
        first = derive_common_support(
            candidates, pairs, audit, base_file_hashes=physical_hashes, run_id=args.run_id
        )
        second = derive_common_support(
            candidates, pairs, audit, base_file_hashes=physical_hashes, run_id=args.run_id
        )
        reversed_build = derive_common_support(
            reverse_scope_target_order(candidates),
            reverse_scope_target_order(pairs),
            reverse_scope_target_order(audit),
            base_file_hashes=physical_hashes,
            run_id=args.run_id,
        )
        first_bytes = canonical_triplet_bytes(first)
        if first_bytes != canonical_triplet_bytes(second):
            raise AssertionError("two same-order builds are not canonical-byte identical")
        if first_bytes != canonical_triplet_bytes(reversed_build):
            raise AssertionError("forward/reverse builds are not canonical-byte identical")
        written = write_common_support_triplet(
            first, (args.candidate_output, args.pair_output, args.audit_output)
        )
        summary = first[2]["count_summary"]
        result = {
            "status": "PASS",
            "run_id": args.run_id,
            "base_file_sha256": physical_hashes,
            "base_hashes_match_frozen": physical_hashes == BASE_FILE_SHA256,
            "same_order_build_byte_identical": True,
            "reverse_order_build_byte_identical": True,
            "overall": summary["overall"],
            "outer": summary["outer"],
            "inner": summary["inner"],
            "failure_stage_counts": first[2]["failure_stage_counts"],
            "written": written,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "assertions": {
                "scoring_only": True,
                "training_records_removed": 0,
                "eeg_read": False,
                "encoder_rerun": False,
                "roamm_read": False,
            },
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:  # explicit self-check FAIL contract
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
