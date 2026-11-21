# SPDX-License-Identifier: Apache-2.0
"""User override file: plain text, one decision per line, shareable.

    # comment
    전기 = 電氣            # always this Hanja
    전기 공학 = 電氣 工學   # phrase; matched before shorter words
    의사 = -              # keep this word in Hangul
    이순신 = 李舜臣        # add a word the lexicon lacks

A tab may replace ``=``. Keys are compared with spaces removed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .lexicon import Entry, _strip_spaces

KEEP = "-"


@dataclass
class Overrides:
    """The reader's decisions from an override file (docs/overrides-and-review.md); they beat every rule."""

    decisions: dict[str, Entry | None] = field(default_factory=dict)  # None = keep Hangul
    max_key_len: int = 0

    def get(self, hangul: str) -> tuple[bool, Entry | None]:
        """Return (has_override, entry_or_None)."""
        key = _strip_spaces(hangul)
        if key in self.decisions:
            return True, self.decisions[key]
        return False, None

    def add(self, hangul: str, hanja: str, source: str = "override") -> None:
        key = _strip_spaces(hangul)
        if hanja == KEEP:
            self.decisions[key] = None
        else:
            if len(_strip_spaces(hanja)) != len(key):
                raise ValueError(f"{hangul!r} and {hanja!r} differ in length / 길이가 다릅니다")
            self.decisions[key] = Entry(hangul, hanja, "", source)
        self.max_key_len = max(self.max_key_len, len(key))

    @classmethod
    def from_lines(cls, lines: Iterable[str], source: str = "override") -> Overrides:
        ov = cls()
        for n, raw in enumerate(lines, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            sep = "=" if "=" in line else "\t"
            if sep not in line:
                raise ValueError(f"line {n}: expected 'hangul = hanja' / 「한글 = 漢字」 形式이어야 합니다: {line!r}")
            left, right = (s.strip() for s in line.split(sep, 1))
            if not left or not right:
                raise ValueError(f"line {n}: empty side / 빈 項目: {line!r}")
            try:
                ov.add(left, right, source)
            except ValueError as e:
                raise ValueError(f"line {n}: {e}") from None
        return ov

    @classmethod
    def load(cls, path: Path) -> Overrides:
        with path.open(encoding="utf-8-sig") as fh:
            return cls.from_lines(fh, source=f"override:{path.name}")

    def update(self, other: Overrides) -> None:
        self.decisions.update(other.decisions)
        self.max_key_len = max(self.max_key_len, other.max_key_len)


__all__ = ["Overrides"]
