# SPDX-License-Identifier: Apache-2.0
"""Score the converter against regression items.

For every item the converter runs on the Hangul form and the output is
compared with the gold mixed-script text position by position. Each maximal
run of Hanja in the gold text is one *word*; it counts as

- ``right``   the output has exactly the same Hanja there,
- ``flagged`` the output left it in Hangul (the converter abstained),
- ``wrong``   the output has different Hanja there,

and a run of Hanja in the output where the gold has Hangul is ``over``.
Accuracy figures in the README come only from this script.
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


@dataclass
class Tally:
    right: int = 0
    flagged: int = 0
    wrong: int = 0
    over: int = 0
    misaligned: int = 0  # output length differs from gold; item skipped
    examples_wrong: list[tuple[str, str, str]] = field(default_factory=list)
    examples_over: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def words(self) -> int:
        return self.right + self.flagged + self.wrong

    def as_dict(self) -> dict[str, int | float]:
        w = self.words
        return {
            "words": w,
            "right": self.right,
            "flagged": self.flagged,
            "wrong": self.wrong,
            "over": self.over,
            "misaligned_items": self.misaligned,
            "right_pct": round(100 * self.right / w, 1) if w else 0.0,
            "wrong_pct": round(100 * self.wrong / w, 1) if w else 0.0,
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
    gold, out = item.mixed, output
    covered: set[int] = set()
    for a, b in _runs(gold):
        covered.update(range(a, b))
        if out[a:b] == gold[a:b]:
            tally.right += 1
        elif any(is_cjk(c) for c in out[a:b]):
            tally.wrong += 1
            if len(tally.examples_wrong) < 20:
                tally.examples_wrong.append((item.id, gold[a:b], out[a:b]))
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
