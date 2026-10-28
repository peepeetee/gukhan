# SPDX-License-Identifier: Apache-2.0
"""Read ``kHangul`` readings from the Unicode Unihan database.

Accepts ``Unihan.zip`` or a directory/file containing ``Unihan_Readings.txt``.
Lines look like ``U+4E00<TAB>kHangul<TAB>일:0E`` where each reading carries a
source code after the colon.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

_LINE = re.compile(r"^U\+([0-9A-F]{4,6})\tkHangul\t(.+)$")
_VERSION = re.compile(r"Unihan_Readings-(\d+\.\d+\.\d+)\.txt")


def _open_readings(path: Path) -> tuple[io.TextIOBase, str | None]:
    if path.is_dir():
        candidates = sorted(path.glob("Unihan_Readings*.txt"))
        if not candidates:
            raise FileNotFoundError(f"Unihan_Readings.txt not found in {path}")
        return candidates[0].open(encoding="utf-8"), None
    if zipfile.is_zipfile(path):
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if n.startswith("Unihan_Readings")]
        if not names:
            raise FileNotFoundError(f"Unihan_Readings.txt not found in {path}")
        return io.TextIOWrapper(zf.open(names[0]), encoding="utf-8"), None
    return path.open(encoding="utf-8"), None


def read_khangul(path: Path) -> tuple[dict[str, list[str]], str | None]:
    """Return ``{hanja_char: [readings...]}`` and the Unihan version if stated."""
    readings: dict[str, list[str]] = {}
    version: str | None = None
    fh, _ = _open_readings(path)
    with fh:
        for line in fh:
            if version is None and line.startswith("#"):
                m = _VERSION.search(line)
                if m:
                    version = m.group(1)
                continue
            m = _LINE.match(line.rstrip("\n"))
            if not m:
                continue
            ch = chr(int(m.group(1), 16))
            values = [v.split(":", 1)[0] for v in m.group(2).split()]
            readings[ch] = sorted(set(values))
    return readings, version
