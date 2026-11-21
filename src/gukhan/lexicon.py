# SPDX-License-Identifier: Apache-2.0
"""Sino-Korean lexicon: TSV loading and lookup keyed by Hangul headword."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

COLUMNS = ("hangul", "hanja", "pos", "source", "sense", "weight", "level", "learner_rank", "domain")


@dataclass(frozen=True)
class Entry:
    """One lexicon line: a Hangul headword, its Hanja reading and the facts the converter ranks by."""

    hangul: str  # as written, may contain spaces for phrases
    hanja: str  # same length as hangul; Hangul kept where no Hanja exists
    pos: str = ""
    source: str = ""
    sense: str = ""
    weight: int = 0  # higher = more likely reading; from the builder, see docs/PLAN.md §4
    level: int = 0
    learner_rank: int = 0
    domain: str = ""  # field label(s) (법률, 의학 …) when every sense of the entry has one; "" = general or unknown


def _strip_spaces(s: str) -> str:
    return s.replace(" ", "")


def _is_han(ch: str) -> bool:
    return not ("가" <= ch <= "힣")


def is_native_entry_text(hangul: str, hanja: str) -> bool:
    return hangul == hanja


class Lexicon:
    """Entries indexed by space-free Hangul so 작전계획 and 작전 계획 both match."""

    def __init__(self, entries: Iterable[Entry] = ()) -> None:
        self._by_key: dict[str, list[Entry]] = {}
        self.max_key_len = 0
        self.weighted = False  # any entry carries a weight (Wiktionary-built lexicons do)
        self.path: Path | None = None
        self._grams: dict[str, list[tuple[str, str]]] | None = None  # 4-syllable index for attested(), built lazily
        for e in entries:
            self.add(e)

    def add(self, entry: Entry) -> None:
        self._add(_strip_spaces(entry.hangul), entry)

    def _add(self, key: str, entry: Entry) -> None:
        bucket = self._by_key.get(key)
        if bucket is None:
            self._by_key[key] = [entry]
        elif entry not in bucket:
            bucket.append(entry)
        if len(key) > self.max_key_len:
            self.max_key_len = len(key)
        if entry.weight:
            self.weighted = True

    def candidates(self, hangul: str) -> list[Entry]:
        return list(self._by_key.get(_strip_spaces(hangul), ()))

    GRAM = 4

    def attested(self, run: str) -> tuple[set[str], int]:
        """Hanja forms that the lexicon itself writes for ``run`` inside longer headwords, and how many headwords do.

        ``국무위원`` is not a headword, but 국무위원회 (國務委員會) and 국무위원장 (國務委員長)
        contain it with one Hanja form. Only Hanja-only stretches count (a Hangul-kept
        syllable in the entry means the entry does not settle the Hanja there), and only runs
        of at least four syllables, so a short stretch is never read out of an unrelated word.
        Returns ``(forms, headword count)``.
        """
        run = _strip_spaces(run)
        n = len(run)
        if n < self.GRAM:
            return set(), 0
        if self._grams is None:
            grams: dict[str, list[tuple[str, str]]] = {}
            for key, bucket in self._by_key.items():
                if len(key) <= self.GRAM:
                    continue
                for e in bucket:
                    hanja = _strip_spaces(e.hanja)
                    if len(hanja) != len(key) or is_native_entry_text(key, hanja):
                        continue
                    for i in range(len(key) - self.GRAM + 1):
                        grams.setdefault(key[i : i + self.GRAM], []).append((key, hanja))
            self._grams = grams
        forms: set[str] = set()
        heads: set[str] = set()
        for key, hanja in self._grams.get(run[: self.GRAM], ()):
            if len(key) <= n:
                continue
            at = key.find(run)
            while at >= 0:
                piece = hanja[at : at + n]
                if all(_is_han(c) for c in piece):
                    forms.add(piece)
                    heads.add(key)
                at = key.find(run, at + 1)
        return forms, len(heads)

    def __contains__(self, hangul: str) -> bool:
        return _strip_spaces(hangul) in self._by_key

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_key.values())

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> Lexicon:
        # Hot path: a real lexicon has 700,000 lines, so each is split and converted once, with no generators.
        lex = cls()
        width = len(COLUMNS)
        for n, raw in enumerate(lines, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise ValueError(
                    f"line {n}: expected at least 2 tab-separated columns / 탭 區分 열이 2個 以上이어야 합니다"
                )
            if len(parts) < width:
                parts += [""] * (width - len(parts))
            hangul, hanja, weight = parts[0].strip(), parts[1].strip(), parts[5].strip()
            key = hangul.replace(" ", "")
            if len(key) != len(hanja.replace(" ", "")):
                raise ValueError(f"line {n}: {hangul!r} and {hanja!r} differ in length / 길이가 다릅니다")
            try:
                w = int(weight) if weight else 0
            except ValueError:
                raise ValueError(
                    f"line {n}: weight must be an integer / weight는 整數여야 합니다: {weight!r}"
                ) from None
            level_text, rank_text = parts[6].strip(), parts[7].strip()
            try:
                level = int(level_text) if level_text else 0
                rank = int(rank_text) if rank_text else 0
            except ValueError:
                raise ValueError(
                    f"line {n}: level and learner_rank must be integers / 整數여야 합니다: {parts[6:8]!r}"
                ) from None
            lex._add(
                key,
                Entry(
                    hangul,
                    hanja,
                    parts[2].strip(),
                    parts[3].strip(),
                    parts[4].strip(),
                    w,
                    level,
                    rank,
                    parts[8].strip(),
                ),
            )
        return lex

    @classmethod
    def load(cls, path: Path) -> Lexicon:
        """Load ``path`` (a TSV file, or a directory containing lexicon.tsv)."""
        if path.is_dir():
            path = path / "lexicon.tsv"
        with path.open(encoding="utf-8-sig") as fh:
            lex = cls.from_lines(fh)
        lex.path = path
        return lex

    @classmethod
    def installed(cls) -> Lexicon | None:
        """The lexicon of an installed ``gukhan-lexicon`` package, or None when it is not installed."""
        try:
            import gukhan_lexicon
        except ImportError:
            return None
        return cls.load(gukhan_lexicon.lexicon_path())

    @classmethod
    def sample(cls) -> Lexicon:
        """The small hand-written lexicon bundled for development and tests."""
        text = resources.files("gukhan").joinpath("data/sample_lexicon.tsv").read_text(encoding="utf-8")
        return cls.from_lines(text.splitlines())


__all__ = ["Entry", "Lexicon"]
