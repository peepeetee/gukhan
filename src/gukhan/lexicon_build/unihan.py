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
_DEFINITION = re.compile(r"^U\+([0-9A-F]{4,6})\tkDefinition\t(.+)$")
_VERSION = re.compile(r"Unihan(?:_Readings)?[-_ ](\d+\.\d+\.\d+)|Unicode (?:version )?(\d+\.\d+\.\d+)", re.IGNORECASE)
_DATE = re.compile(r"Date:\s*(\d{4}-\d{2}-\d{2})")


def _open_readings(path: Path) -> tuple[io.TextIOBase, str | None]:
    if path.is_dir():
        candidates = sorted(path.glob("Unihan_Readings*.txt"))
        if not candidates:
            raise FileNotFoundError(f"Unihan_Readings.txt를 찾을 수 없습니다 / Unihan_Readings.txt not found in {path}")
        return candidates[0].open(encoding="utf-8"), None
    if zipfile.is_zipfile(path):
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if n.startswith("Unihan_Readings")]
        if not names:
            raise FileNotFoundError(f"Unihan_Readings.txt를 찾을 수 없습니다 / Unihan_Readings.txt not found in {path}")
        return io.TextIOWrapper(zf.open(names[0]), encoding="utf-8"), None
    return path.open(encoding="utf-8"), None


def read_khangul(path: Path, *, with_tags: bool = False) -> tuple[dict[str, list[str]], str | None]:
    """Return ``{hanja_char: [readings...]}`` in Unihan order, and the Unihan version if stated.

    With ``with_tags`` each reading keeps its source tag (``책:0E``): ``0``/``1``
    say which KS X standard lists it, ``E`` marks the reading taught in the
    standard education set, which is the usual one.
    """
    readings: dict[str, list[str]] = {}
    version: str | None = None
    fh, _ = _open_readings(path)
    with fh:
        for line in fh:
            if line.startswith("#"):
                if version is None or version.startswith("dated "):
                    m = _VERSION.search(line)
                    if m:
                        version = m.group(1) or m.group(2)
                    elif version is None:
                        d = _DATE.search(line)
                        if d:
                            version = "dated " + d.group(1)
                continue
            m = _LINE.match(line.rstrip("\n"))
            if not m:
                continue
            ch = chr(int(m.group(1), 16))
            values = [v if with_tags else v.split(":", 1)[0] for v in m.group(2).split()]
            readings[ch] = list(dict.fromkeys(values))
    return readings, version


def read_definitions(path: Path) -> dict[str, str]:
    """Return ``{hanja_char: English meaning}`` from ``kDefinition``: the first two senses, at most 60 characters.

    Unihan separates senses with ``;`` and synonyms with ``,``: ``country, nation; state`` keeps both senses.
    Unihan에는 한국어 訓이 없어 英語 뜻을 씁니다.
    """
    out: dict[str, str] = {}
    fh, _ = _open_readings(path)
    with fh:
        for line in fh:
            m = _DEFINITION.match(line.rstrip("\n"))
            if m:
                senses = [x.strip() for x in m.group(2).split(";") if x.strip()]
                out[chr(int(m.group(1), 16))] = "; ".join(senses[:2])[:60].rstrip(" ,;")
    return out
