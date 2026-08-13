#!/usr/bin/env python3
"""Download and validate the public TMNRED OpenNeuro snapshot.

The downloader uses only Python's standard library. It records the exact S3
object manifest, resumes partial files, and validates every file by byte size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any


DATASET_ID = "ds005383"
SNAPSHOT_VERSION = "1.0.0"
BUCKET = "openneuro.org"
S3_ROOT = f"https://s3.amazonaws.com/{BUCKET}"
OBJECT_PREFIX = f"{DATASET_ID}/"
USER_AGENT = "trust-align-tmnred-downloader/1.0"
CHUNK_BYTES = 8 * 1024 * 1024
PRINT_LOCK = threading.Lock()


def request(url: str, *, headers: dict[str, str] | None = None, timeout: int = 120):
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=merged_headers), timeout=timeout
    )


def list_objects() -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    continuation_token: str | None = None
    while True:
        query = {"list-type": "2", "prefix": OBJECT_PREFIX, "max-keys": "1000"}
        if continuation_token:
            query["continuation-token"] = continuation_token
        url = f"{S3_ROOT}/?{urllib.parse.urlencode(query)}"
        with request(url) as response:
            root = ET.fromstring(response.read())

        namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s3:Contents", namespace):
            key = item.findtext("s3:Key", default="", namespaces=namespace)
            if not key or key.endswith("/"):
                continue
            objects.append(
                {
                    "key": key,
                    "size": int(
                        item.findtext("s3:Size", default="0", namespaces=namespace)
                    ),
                    "etag": item.findtext(
                        "s3:ETag", default="", namespaces=namespace
                    ).strip('"'),
                    "last_modified": item.findtext(
                        "s3:LastModified", default="", namespaces=namespace
                    ),
                }
            )

        truncated = root.findtext(
            "s3:IsTruncated", default="false", namespaces=namespace
        ).lower() == "true"
        if not truncated:
            break
        continuation_token = root.findtext(
            "s3:NextContinuationToken", default="", namespaces=namespace
        )
        if not continuation_token:
            raise RuntimeError("S3 listing was truncated without a continuation token")

    if not objects:
        raise RuntimeError(f"no objects found under {OBJECT_PREFIX!r}")
    return sorted(objects, key=lambda item: item["key"])


def manifest_payload(objects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dataset": "TMNRED",
        "openneuro_dataset_id": DATASET_ID,
        "openneuro_snapshot_version": SNAPSHOT_VERSION,
        "source": f"s3://{BUCKET}/{OBJECT_PREFIX}",
        "object_count": len(objects),
        "total_bytes": sum(item["size"] for item in objects),
        "objects": objects,
    }


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def object_url(key: str) -> str:
    return f"{S3_ROOT}/{urllib.parse.quote(key, safe='/')}"


def local_path(target: Path, key: str) -> Path:
    relative = PurePosixPath(key).relative_to(OBJECT_PREFIX.rstrip("/"))
    if ".." in relative.parts:
        raise ValueError(f"unsafe S3 key: {key}")
    return target.joinpath(*relative.parts)


def stream_download(item: dict[str, Any], target: Path, retries: int) -> str:
    destination = local_path(target, item["key"])
    expected_size = item["size"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == expected_size:
        return "existing"

    partial = destination.with_name(destination.name + ".part")
    if partial.exists() and partial.stat().st_size > expected_size:
        partial.unlink()

    for attempt in range(1, retries + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with request(object_url(item["key"]), headers=headers) as response:
                status = getattr(response, "status", response.getcode())
                if offset and status != 206:
                    offset = 0
                    partial.unlink(missing_ok=True)
                mode = "ab" if offset and status == 206 else "wb"
                with partial.open(mode) as handle:
                    while True:
                        chunk = response.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        handle.write(chunk)
            actual_size = partial.stat().st_size
            if actual_size != expected_size:
                raise IOError(
                    f"size mismatch for {item['key']}: {actual_size} != {expected_size}"
                )
            os.replace(partial, destination)
            return "downloaded"
        except (OSError, urllib.error.URLError) as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"failed after {retries} attempts: {item['key']}: {exc}"
                ) from exc
            time.sleep(min(2**attempt, 30))
    raise AssertionError("unreachable")


def download_all(
    objects: list[dict[str, Any]], target: Path, workers: int, retries: int
) -> Counter[str]:
    counts: Counter[str] = Counter()
    completed_bytes = 0
    total_bytes = sum(item["size"] for item in objects)
    report_at = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(stream_download, item, target, retries): item
            for item in objects
        }
        for index, future in enumerate(as_completed(futures), start=1):
            item = futures[future]
            result = future.result()
            counts[result] += 1
            completed_bytes += item["size"]
            now = time.monotonic()
            if now >= report_at or index == len(objects):
                with PRINT_LOCK:
                    print(
                        "[progress] "
                        f"files={index}/{len(objects)} "
                        f"accounted={completed_bytes / 1e9:.2f}/{total_bytes / 1e9:.2f} GB",
                        flush=True,
                    )
                report_at = now + 20
    return counts


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_files(objects: list[dict[str, Any]], target: Path) -> dict[str, Any]:
    missing: list[str] = []
    wrong_size: list[str] = []
    md5_mismatch: list[str] = []
    extension_counts: Counter[str] = Counter()
    verified_md5 = 0
    for item in objects:
        path = local_path(target, item["key"])
        if not path.is_file():
            missing.append(item["key"])
            continue
        actual_size = path.stat().st_size
        if actual_size != item["size"]:
            wrong_size.append(item["key"])
            continue
        extension_counts[path.suffix.lower() or "[no extension]"] += 1
        etag = item["etag"]
        if etag and "-" not in etag:
            verified_md5 += 1
            if md5_file(path) != etag.lower():
                md5_mismatch.append(item["key"])

    if missing or wrong_size or md5_mismatch:
        raise RuntimeError(
            "validation failed: "
            f"missing={len(missing)} wrong_size={len(wrong_size)} "
            f"md5_mismatch={len(md5_mismatch)}"
        )

    participants_path = target / "participants.tsv"
    participant_count = None
    if participants_path.is_file():
        lines = [line for line in participants_path.read_text(encoding="utf-8").splitlines() if line]
        participant_count = max(len(lines) - 1, 0)

    description_path = target / "dataset_description.json"
    description = {}
    if description_path.is_file():
        description = json.loads(description_path.read_text(encoding="utf-8"))

    partial_count = sum(1 for path in target.rglob("*.part") if path.is_file())
    return {
        "validated_object_count": len(objects),
        "validated_bytes": sum(item["size"] for item in objects),
        "single_part_etag_md5_verified": verified_md5,
        "participant_rows": participant_count,
        "dataset_name": description.get("Name"),
        "dataset_doi": description.get("DatasetDOI"),
        "license": description.get("License"),
        "extension_counts": dict(sorted(extension_counts.items())),
        "partial_file_count": partial_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.retries < 1:
        parser.error("--workers and --retries must be positive")
    return args


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    print(
        f"[source] dataset={DATASET_ID} snapshot={SNAPSHOT_VERSION} "
        f"url={S3_ROOT}/{OBJECT_PREFIX}",
        flush=True,
    )
    objects = list_objects()
    manifest = manifest_payload(objects)
    write_json_atomic(args.manifest, manifest)
    print(
        "[manifest] "
        f"objects={manifest['object_count']} "
        f"bytes={manifest['total_bytes']} ({manifest['total_bytes'] / 1e9:.2f} GB) "
        f"path={args.manifest}",
        flush=True,
    )
    if args.manifest_only:
        print(
            "[self-check] mode=manifest-only randomness=none "
            f"elapsed_sec={time.monotonic() - started:.1f}",
            flush=True,
        )
        return 0

    args.target.mkdir(parents=True, exist_ok=True)
    counts = download_all(objects, args.target, args.workers, args.retries)
    validation = validate_files(objects, args.target)
    elapsed = time.monotonic() - started
    disk = shutil.disk_usage(args.target)
    report = {
        **manifest_payload(objects),
        "target": str(args.target.resolve()),
        "download_counts": dict(counts),
        "validation": validation,
        "elapsed_seconds": round(elapsed, 3),
        "free_bytes_after_download": disk.free,
        "randomness": "none",
    }
    report.pop("objects")
    write_json_atomic(args.report, report)
    print("[self-check]", flush=True)
    print(
        f"  files={validation['validated_object_count']} "
        f"bytes={validation['validated_bytes']} ({validation['validated_bytes'] / 1e9:.2f} GB)",
        flush=True,
    )
    print(
        f"  participants={validation['participant_rows']} "
        f"dataset_name={validation['dataset_name']!r} "
        f"doi={validation['dataset_doi']!r} license={validation['license']!r}",
        flush=True,
    )
    print(
        f"  md5_verified={validation['single_part_etag_md5_verified']} "
        f"partial_files={validation['partial_file_count']} "
        f"extensions={validation['extension_counts']}",
        flush=True,
    )
    print(
        f"  elapsed_sec={elapsed:.1f} free_after={disk.free / (1024**3):.1f} GiB "
        f"randomness=none report={args.report}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted; .part files retained for resume", file=sys.stderr)
        raise SystemExit(130)
