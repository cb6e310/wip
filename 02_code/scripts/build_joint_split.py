#!/usr/bin/env python3
"""Build or self-check a v3.6 subject-by-stimulus joint split artifact.

The input is a JSON object with ``dataset``, ``task`` and ``records`` (or a
bare records list).  See ``data.joint_split`` for the row contract.  This
script never repairs an unresolved material join.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from data.joint_split import (  # noqa: E402
    DEFAULT_SEED,
    build_joint_split,
    canonical_json_bytes,
    sha256_bytes,
    synthetic_records,
    validate_artifact,
    write_artifact,
)


def _load_input(path: Path) -> tuple[dict, str, str, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return {"records": value}, "unspecified", "unspecified", DEFAULT_SEED
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        raise ValueError("input JSON must be a records list or an object containing records")
    return (
        value,
        str(value.get("dataset", "unspecified")),
        str(value.get("task", "unspecified")),
        int(value.get("seed", DEFAULT_SEED)),
    )


def _summary(artifact: dict, *, elapsed: float, output: Path | None, file_bytes: int | None, file_sha: str | None) -> None:
    errors = validate_artifact(artifact)
    assertions = artifact.get("assertions", {})
    status = "PASS" if not errors else "FAIL"
    print(
        "JOINT SPLIT SELF-CHECK "
        f"records={artifact['input']['record_count']} "
        f"eligible={len(artifact['records'])} "
        f"excluded={len(artifact['exclusions'])} "
        f"subjects={artifact['subjects']['count']} "
        f"stimuli={artifact['text']['stimulus_count']} "
        f"shape=({artifact['fold_counts']['subject']},{artifact['fold_counts']['text']}) "
        f"trial_range=({min(item['valid_sentence_trials'] for item in artifact['records'])},"
        f"{max(item['valid_sentence_trials'] for item in artifact['records'])}) "
        f"elapsed_seconds={elapsed:.3f} "
        f"artifact_bytes={file_bytes if file_bytes is not None else 'NA'} "
        f"artifact_sha256={file_sha if file_sha is not None else artifact['integrity']['canonical_payload_sha256']} "
        f"assertions={sum(bool(value) for key, value in assertions.items() if key != 'all_checks_pass')}/"
        f"{max(0, len(assertions) - 1)} {status}"
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON panel manifest")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("01_data_protocol/splits/zuco_2_0_outer_folds.json"),
    )
    parser.add_argument("--dataset")
    parser.add_argument("--task")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--selfcheck", action="store_true", help="run a synthetic contract check")
    args = parser.parse_args()
    if not args.selfcheck and args.input is None:
        parser.error("--input is required unless --selfcheck is used")

    started = time.monotonic()
    output: Path | None = None
    if args.selfcheck:
        records = synthetic_records()
        dataset, task, seed = "synthetic", "contract", DEFAULT_SEED
        # Keep self-check output ephemeral unless an explicit output was given.
        output = (
            args.output
            if args.output != Path("01_data_protocol/splits/zuco_2_0_outer_folds.json")
            else None
        )
    else:
        panel, dataset, task, seed = _load_input(args.input)
        records = panel["records"]
        output = args.output
    dataset = args.dataset or dataset
    task = args.task or task
    seed = args.seed if args.seed is not None else seed
    artifact = build_joint_split(records, dataset=dataset, task=task, seed=seed)
    if args.selfcheck:
        artifact["evidence_scope"] = "NON_PAPER_SMOKE"
        artifact["real_data_ready"] = False
        artifact["note"] = (
            "Synthetic contract evidence only; real material identity join and "
            "dataset-specific split remain blocked."
        )
        artifact.pop("integrity", None)
        canonical_payload = canonical_json_bytes(artifact)
        artifact["integrity"] = {
            "canonical_payload_sha256": sha256_bytes(canonical_payload),
            "canonical_payload_bytes": len(canonical_payload),
            "hash_scope": "canonical JSON artifact without integrity field",
        }
    if output is not None:
        file_bytes, file_sha = write_artifact(artifact, output)
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_bytes, file_sha = write_artifact(artifact, Path(temp_dir) / "outer_folds.json")
    _summary(
        artifact,
        elapsed=time.monotonic() - started,
        output=output,
        file_bytes=file_bytes,
        file_sha=file_sha,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
