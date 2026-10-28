# SPDX-License-Identifier: Apache-2.0
"""Score the converter against regression items.

For every item the converter runs on the Hangul form and the output is
compared with the gold mixed-script text position by position. Each maximal
run of Hanja in the gold text is one *word*; it counts as

- ``right``   the output has exactly the same Hanja there,
- ``partial`` part of the run is the right Hanja and the rest stayed Hangul
  (a compound the lexicon knows only in part: 大韓國民 → 대한國民),
- ``flagged`` the output left it all in Hangul (the converter abstained),
- ``wrong``   the output has different Hanja somewhere in the run,

and a run of Hanja in the output where the gold has Hangul is ``over``.
Glyph variants (强/強, 眞/真 …) are folded before comparison. Character
counts (``chars_right`` …) are reported alongside. Accuracy figures in the
README come only from this script.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from gukhan.convert import Converter
from gukhan.lexicon_build.hangul import is_cjk


@dataclass(frozen=True)
class Item:
    id: str
    source: str
    hangul: str
    mixed: str


# Glyph variants folded before comparison: the 1948 texts write 强, Wiktionary 強.
VARIANTS = str.maketrans(
    {
        "强": "強", "眞": "真", "爲": "為", "靑": "青", "淸": "清", "內": "内", "卽": "即", "旣": "既",
        "敎": "教", "鎭": "鎮", "衆": "眾", "値": "值", "戶": "戸", "氷": "冰", "裏": "裡", "冊": "册",
        "槪": "概", "戾": "戻", "黃": "黄", "溫": "温", "說": "説", "勳": "勲", "歲": "歳", "者": "者",
    }
)  # fmt: skip


def fold_variants(s: str) -> str:
    return s.translate(VARIANTS)


@dataclass
class Tally:
    right: int = 0
    partial: int = 0
    flagged: int = 0
    wrong: int = 0
    over: int = 0
    chars_right: int = 0
    chars_flagged: int = 0
    chars_wrong: int = 0
    misaligned: int = 0  # output length differs from gold; item skipped
    examples_wrong: list[tuple[str, str, str]] = field(default_factory=list)
    examples_over: list[tuple[str, str, str]] = field(default_factory=list)
    examples_partial: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def words(self) -> int:
        return self.right + self.partial + self.flagged + self.wrong

    def as_dict(self) -> dict[str, int | float]:
        w = self.words
        c = self.chars_right + self.chars_flagged + self.chars_wrong
        return {
            "words": w,
            "right": self.right,
            "partial": self.partial,
            "flagged": self.flagged,
            "wrong": self.wrong,
            "over": self.over,
            "chars": c,
            "chars_right": self.chars_right,
            "chars_flagged": self.chars_flagged,
            "chars_wrong": self.chars_wrong,
            "misaligned_items": self.misaligned,
            "right_pct": round(100 * self.right / w, 1) if w else 0.0,
            "wrong_pct": round(100 * self.wrong / w, 1) if w else 0.0,
            "chars_right_pct": round(100 * self.chars_right / c, 1) if c else 0.0,
            "chars_wrong_pct": round(100 * self.chars_wrong / c, 1) if c else 0.0,
        }


def read_items(path: Path) -> list[Item]:
    items = []
    with path.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                raise ValueError(f"{path}:{n}: expected id, source, hangul, mixed / 열이 4個 必要합니다")
            items.append(Item(*(p.strip() for p in parts[:4])))
    return items


def _runs(text: str) -> list[tuple[int, int]]:
    runs, start = [], None
    for i, ch in enumerate(text + " "):
        if is_cjk(ch):
            if start is None:
                start = i
        elif start is not None:
            runs.append((start, i))
            start = None
    return runs


def score_item(item: Item, output: str, tally: Tally) -> None:
    if len(output) != len(item.mixed):
        tally.misaligned += 1
        return
    gold, out = fold_variants(item.mixed), fold_variants(output)
    covered: set[int] = set()
    for a, b in _runs(gold):
        covered.update(range(a, b))
        g, o = gold[a:b], out[a:b]
        wrong_chars = sum(1 for x, y in zip(g, o, strict=True) if is_cjk(y) and x != y)
        right_chars = sum(1 for x, y in zip(g, o, strict=True) if x == y)
        tally.chars_right += right_chars
        tally.chars_wrong += wrong_chars
        tally.chars_flagged += len(g) - right_chars - wrong_chars
        if o == g:
            tally.right += 1
        elif wrong_chars:
            tally.wrong += 1
            if len(tally.examples_wrong) < 20:
                tally.examples_wrong.append((item.id, g, o))
        elif right_chars:
            tally.partial += 1
            if len(tally.examples_partial) < 20:
                tally.examples_partial.append((item.id, g, o))
        else:
            tally.flagged += 1
    for a, b in _runs(out):
        if not any(i in covered for i in range(a, b)):
            tally.over += 1
            if len(tally.examples_over) < 20:
                tally.examples_over.append((item.id, gold[a:b], out[a:b]))


def score(items: Iterable[Item], converter: Converter) -> Tally:
    tally = Tally()
    for item in items:
        score_item(item, converter.convert(item.hangul).text, tally)
    return tally
