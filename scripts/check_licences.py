# SPDX-License-Identifier: Apache-2.0
"""Licence policy check, run by CI.

1. Every tracked Python and JavaScript/TypeScript source file carries an
   ``SPDX-License-Identifier: Apache-2.0`` header.
2. No installed Python dependency is under GPL or AGPL (LGPL is allowed).
   Uses ``pip-licenses`` output in JSON form.

Exit status is non-zero on any violation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SPDX_LINE = "SPDX-License-Identifier: Apache-2.0"
SOURCE_SUFFIXES = {".py", ".js", ".ts", ".mjs"}
# Substrings matched case-insensitively against pip-licenses' licence names.
FORBIDDEN = ("gpl",)
ALLOWED_EXCEPTIONS = ("lgpl", "lesser general public")
# Packages whose metadata is known to be wrong or absent can be listed here
# with a reason, after their licence has been verified by hand.
VERIFIED_OVERRIDES: dict[str, str] = {}


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout
    return [Path(p) for p in out.splitlines()]


def check_spdx_headers() -> list[str]:
    problems = []
    for path in tracked_files():
        if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
            continue
        head = path.read_text(encoding="utf-8", errors="replace")[:400]
        if SPDX_LINE not in head:
            problems.append(f"missing SPDX header: {path}")
    return problems


def check_dependency_licences() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json", "--with-system"],
        check=True,
        capture_output=True,
        text=True,
    )
    problems = []
    for pkg in json.loads(result.stdout):
        name, licence = pkg["Name"], pkg["License"]
        if name.lower() in VERIFIED_OVERRIDES:
            continue
        lowered = licence.lower()
        if any(f in lowered for f in FORBIDDEN) and not any(a in lowered for a in ALLOWED_EXCEPTIONS):
            problems.append(f"forbidden licence: {name} ({licence})")
        if lowered in ("unknown", ""):
            problems.append(f"unknown licence, verify and record: {name}")
    return problems


def main() -> int:
    problems = check_spdx_headers() + check_dependency_licences()
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"{len(problems)} licence problem(s)", file=sys.stderr)
        return 1
    print("licence check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
