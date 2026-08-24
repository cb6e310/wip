#!/usr/bin/env python3
"""Run the synthetic R6 contract suite without requiring pytest."""

from __future__ import annotations

from pathlib import Path
import sys
import traceback


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_code" / "src"))
sys.path.insert(0, str(ROOT / "02_code" / "tests"))

from test_eqalign_r6_contracts import CORE_TESTS  # noqa: E402


def main() -> int:
    failures = 0
    for test in CORE_TESTS:
        try:
            test()
        except Exception:
            failures += 1
            print(f"FAIL {test.__name__}", file=sys.stderr)
            traceback.print_exc()
        else:
            print(f"PASS {test.__name__}")
    print(f"R6 contract selfcheck: {len(CORE_TESTS) - failures}/{len(CORE_TESTS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
