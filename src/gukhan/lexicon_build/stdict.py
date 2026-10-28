# SPDX-License-Identifier: Apache-2.0
"""Parse the 표준국어대사전 XML dump into lexicon entries.

The dump is obtained by the user from <https://stdict.korean.go.kr> (login,
「사전 내려받기」). Its schema nests the headword under ``item/word_info``;
the open API uses flat ``item/word``. Both shapes are accepted: for every
``<item>`` the parser looks up the first element with each wanted local tag
name anywhere under the item, so a renamed wrapper does not break it. Usage
examples (용례) are never read.

Headword and Hanja conventions handled:

- ``^`` in a headword marks a space in a multi-word entry; ``-`` marks a
  morpheme boundary. Both are dropped (``^`` becomes a space).
- In the original-language field, ``▽``/``▼`` mark variant characters and are
  dropped; ``-`` stands for a Hangul syllable that has no Hanja (mixed
  entries such as 冊床-- for 책상다리). Spaces are ignored.
- After cleaning, Hanja characters must align one-to-one with the headword
  syllables; otherwise the entry is rejected with a reason.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .hangul import initial_sound_variants, is_cjk, is_syllable

WANTED_TAGS = ("word", "original_language", "origin", "pos", "word_type", "target_code", "definition", "sup_no")
SINO_WORD_TYPES = {"한자어", "혼종어"}


@dataclass
class Entry:
    hangul: str
    hanja: str
    pos: str
    source: str
    sense: str = ""

    def tsv(self) -> str:
        return "\t".join((self.hangul, self.hanja, self.pos, self.source, self.sense))


@dataclass
class Reject:
    hangul: str
    raw_hanja: str
    source: str
    reason: str

    def tsv(self) -> str:
        return "\t".join((self.hangul, self.raw_hanja, self.source, self.reason))


@dataclass
class ParseStats:
    items: int = 0
    sino: int = 0
    entries: int = 0
    rejected: int = 0
    tags_seen: set[str] = field(default_factory=set)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(item: ET.Element, name: str) -> str | None:
    for el in item.iter():
        if _local(el.tag) == name and el.text and el.text.strip():
            return el.text.strip()
    return None


def clean_headword(word: str) -> str:
    return word.replace("^", " ").replace("-", "").strip()


def clean_hanja(raw: str) -> str:
    return re.sub(r"[▽▼\s()（）]", "", raw)


def align(hangul: str, hanja: str) -> str | None:
    """Map cleaned Hanja onto the headword, keeping ``-`` syllables as Hangul.

    Returns the mixed-script form (same length as ``hangul``) or ``None``
    when the two do not line up.
    """
    syllables = hangul.replace(" ", "")
    if len(hanja) != len(syllables):
        return None
    out = []
    i = 0
    for ch in hangul:
        if ch == " ":
            out.append(" ")
            continue
        h = hanja[i]
        i += 1
        if h == "-":
            out.append(ch)
        elif is_cjk(h):
            out.append(h)
        else:
            return None
    mixed = "".join(out)
    if not any(is_cjk(c) for c in mixed):
        return None
    return mixed


def validate_readings(hangul: str, mixed: str, readings: dict[str, list[str]]) -> str | None:
    """Return a reason string if a Hanja character cannot read as its syllable."""
    for syl, h in zip(hangul, mixed, strict=True):
        if not is_cjk(h) or not is_syllable(syl):
            continue
        known = readings.get(h)
        if known is None:
            return f"no kHangul reading for {h}"
        if not any(r in initial_sound_variants(syl) or syl in initial_sound_variants(r) for r in known):
            return f"{h} reads {'/'.join(known)}, not {syl}"
    return None


def iter_items(path: Path) -> Iterator[ET.Element]:
    """Yield every ``<item>`` element from a zip, a directory of XML, or one file."""
    for name, fh in _open_all(path):
        for _, el in ET.iterparse(fh, events=("end",)):
            if _local(el.tag) == "item":
                yield el
                el.clear()


def _open_all(path: Path) -> Iterable[tuple[str, object]]:
    if path.is_dir():
        for p in sorted(path.rglob("*.xml")):
            with p.open("rb") as fh:
                yield str(p), fh
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for name in sorted(n for n in zf.namelist() if n.lower().endswith(".xml")):
                with zf.open(name) as fh:
                    yield name, fh
    else:
        with path.open("rb") as fh:
            yield str(path), fh


def parse(
    path: Path,
    readings: dict[str, list[str]] | None = None,
) -> tuple[list[Entry], list[Reject], ParseStats]:
    entries: list[Entry] = []
    rejects: list[Reject] = []
    stats = ParseStats()
    for item in iter_items(path):
        stats.items += 1
        if stats.items <= 50:
            stats.tags_seen.update(_local(e.tag) for e in item.iter())
        word = _find_text(item, "word")
        if not word:
            continue
        raw_hanja = _find_text(item, "original_language") or _find_text(item, "origin") or ""
        word_type = _find_text(item, "word_type") or ""
        if word_type and word_type not in SINO_WORD_TYPES:
            continue
        if not any(is_cjk(c) for c in raw_hanja):
            continue
        stats.sino += 1
        code = _find_text(item, "target_code") or ""
        sup = _find_text(item, "sup_no") or ""
        source = f"stdict:{code}" if code else f"stdict:{word}{sup}"
        hangul = clean_headword(word)
        mixed = align(hangul, clean_hanja(raw_hanja))
        if mixed is None:
            rejects.append(Reject(hangul, raw_hanja, source, "hanja does not align with headword"))
            stats.rejected += 1
            continue
        if readings:
            why = validate_readings(hangul, mixed, readings)
            if why:
                rejects.append(Reject(hangul, raw_hanja, source, why))
                stats.rejected += 1
                continue
        pos = _find_text(item, "pos") or ""
        sense = (_find_text(item, "definition") or "").replace("\t", " ").replace("\n", " ")[:80]
        entries.append(Entry(hangul, mixed, pos, source, sense))
        stats.entries += 1
    return entries, rejects, stats
