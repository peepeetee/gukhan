# SPDX-License-Identifier: Apache-2.0
"""Zip extension/ into an installable .xpi/.zip without tests or the README.

    python scripts/package_extension.py build/gukhan-0.1.0.xpi

The zip has manifest.json at its root, as addons.mozilla.org and Firefox expect.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "extension"
SKIP = ("engine.test.mjs", "browser-smoke.cjs", "firefox-smoke.cjs", "README.md")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = Path(argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path.name not in SKIP:
                z.write(path, path.relative_to(ROOT).as_posix())
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
