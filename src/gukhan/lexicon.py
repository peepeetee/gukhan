# SPDX-License-Identifier: Apache-2.0
"""Sino-Korean lexicon: TSV loading and lookup keyed by Hangul headword."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

COLUMNS = ("hangul", "hanja", "pos", "source", "sense", "weight", "level", "learner_rank")


@dataclass(frozen=True)
class Entry:
    hangul: str  # as written, may contain spaces for phrases
    hanja: str  # same length as hangul; Hangul kept where no Hanja exists
    pos: str = ""
    source: str = ""
    sense: str = ""
    weight: int = 0  # higher = more likely reading; from the builder, see docs/PLAN.md §4
    level: int = 0
    learner_rank: int = 0


def _strip_spaces(s: str) -> str:
    return s.replace(" ", "")


class Lexicon:
    """Entries indexed by space-free Hangul so 작전계획 and 작전 계획 both match."""

    def __init__(self, entries: Iterable[Entry] = ()) -> None:
        self._by_key: dict[str, list[Entry]] = {}
        self.max_key_len = 0
        self.weighted = False  # any entry carries a weight (Wiktionary-built lexicons do)
        self.path: Path | None = None
        for e in entries:
            self.add(e)

    def add(self, entry: Entry) -> None:
        key = _strip_spaces(entry.hangul)
        bucket = self._by_key.setdefault(key, [])
        if entry not in bucket:
            bucket.append(entry)
        self.max_key_len = max(self.max_key_len, len(key))
        if entry.weight:
            self.weighted = True

    def candidates(self, hangul: str) -> list[Entry]:
        return list(self._by_key.get(_strip_spaces(hangul), ()))

    def __contains__(self, hangul: str) -> bool:
        return _strip_spaces(hangul) in self._by_key

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_key.values())

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> Lexicon:
        lex = cls()
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise ValueError(
                    f"line {n}: expected at least 2 tab-separated columns / 탭 區分 열이 2個 以上이어야 합니다"
                )
            parts += [""] * (len(COLUMNS) - len(parts))
            hangul, hanja, pos, source, sense, weight = (p.strip() for p in parts[:6])
            if len(_strip_spaces(hangul)) != len(_strip_spaces(hanja)):
                raise ValueError(f"line {n}: {hangul!r} and {hanja!r} differ in length / 길이가 다릅니다")
            try:
                w = int(weight) if weight else 0
            except ValueError:
                raise ValueError(
                    f"line {n}: weight must be an integer / weight는 整數여야 합니다: {weight!r}"
                ) from None
            level, rank = (int(p.strip()) if p.strip() else 0 for p in parts[6:8])
            lex.add(Entry(hangul, hanja, pos, source, sense, w, level, rank))
        return lex

    @classmethod
    def load(cls, path: Path) -> Lexicon:
        """Load ``path`` (a TSV file, or a directory containing lexicon.tsv)."""
        if path.is_dir():
            path = path / "lexicon.tsv"
        with path.open(encoding="utf-8") as fh:
            lex = cls.from_lines(fh)
        lex.path = path
        return lex

    @classmethod
    def sample(cls) -> Lexicon:
        """The small hand-written lexicon bundled for development and tests."""
        text = resources.files("gukhan").joinpath("data/sample_lexicon.tsv").read_text(encoding="utf-8")
        return cls.from_lines(text.splitlines())
