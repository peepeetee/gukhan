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
from typing import IO
from xml.etree import ElementTree as ET

from .hangul import initial_sound_variants, is_cjk, is_syllable

WANTED_TAGS = ("word", "original_language", "origin", "pos", "word_type", "target_code", "definition", "sup_no")
SINO_WORD_TYPES = {"한자어", "혼종어"}


class InputError(ValueError):
    """An input file that cannot be read as what it claims to be (truncated, corrupt)."""


@dataclass
class Entry:
    hangul: str
    hanja: str
    pos: str
    source: str
    sense: str = ""
    weight: int = 0
    domain: str = ""  # field label(s) (법률, 의학 …) when every sense of the entry carries one; "" = general or unknown

    def tsv(self) -> str:
        cells = (self.hangul, self.hanja, self.pos, self.source, self.sense)
        return "\t".join((*(_cell(c) for c in cells), str(self.weight)))


_CELL_BREAKS = re.compile(r"[\t\r\n]+")


def _cell(value: str) -> str:
    """A tab or line break inside a field would shift the columns or split the row of a TSV."""
    return _CELL_BREAKS.sub(" ", value).strip()


@dataclass
class Reject:
    hangul: str
    raw_hanja: str
    source: str
    reason: str

    def tsv(self) -> str:
        return "\t".join(_cell(c) for c in (self.hangul, self.raw_hanja, self.source, self.reason))


@dataclass
class ParseStats:
    items: int = 0
    sino: int = 0
    entries: int = 0
    rejected: int = 0
    tags_seen: set[str] = field(default_factory=set)
    # Hangul headwords that also exist as native words (no Hanja form): word → (pos, gloss, weight)
    native: dict[str, tuple[str, str, int]] = field(default_factory=dict)
    # (headword, part of speech) → (gloss, source id) of 標準國語大辭典 native words; 조 is noun and determiner
    native_pos: dict[tuple[str, str], tuple[str, str]] = field(default_factory=dict)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(item: ET.Element, name: str) -> str | None:
    for el in item.iter():
        if _local(el.tag) == name and el.text and el.text.strip():
            return el.text.strip()
    return None


def _components(item: ET.Element) -> list[tuple[str, str]]:
    """``[(original_language, language_type), …]``; a bare ``original_language`` counts as 한자."""
    out = []
    for el in item.iter():
        if _local(el.tag) != "original_language_info":
            continue
        text = kind = ""
        for child in el:
            if _local(child.tag) == "original_language":
                text = (child.text or "").strip()
            elif _local(child.tag) == "language_type":
                kind = (child.text or "").strip()
        out.append((text, kind or "한자"))
    if not out:
        raw = _find_text(item, "original_language")
        if raw:
            out.append((raw, "한자"))
    return out


HOMONYM_SUFFIX = re.compile(r"(\d{2})$")


def split_homonym(word: str) -> tuple[str, str]:
    """Split the two-digit homonym number the full dump appends to headwords.

    The 2026 dump writes ``가03``, ``가계-하다01``; the open API writes ``가``
    with a separate ``sup_no``. Returns ``(word, number)``; number is ``""``
    when absent.
    """
    m = HOMONYM_SUFFIX.search(word)
    if m:
        return word[: m.start()], m.group(1)
    return word, ""


def clean_headword(word: str) -> str:
    word, _ = split_homonym(word)
    return word.replace("^", " ").replace("-", "").strip()


def clean_hanja(raw: str) -> str:
    return re.sub(r"[▽▼\s()（）]", "", raw).replace("ː", "")


def components_to_hanja(hangul: str, comps: list[tuple[str, str]]) -> str | None:
    """Assemble the raw Hanja string of a mixed word from its ``original_language_info`` components.

    ``comps`` is ``[(text, language_type), …]`` in order. A 한자 component
    contributes its characters; any other component covers the matching
    Hangul syllables and is written as ``-`` so ``align`` keeps them in
    Hangul. A native component normally spells those syllables itself
    (生 + 과일 → 生과일); a foreign one (juice) does not, and its length is
    taken as whatever the other components leave over. Two such components
    cannot be placed and give ``None``. ``/(병기)`` separators introduce an
    alternative spelling; only the first alternative is kept.
    """
    if any(kind == "/(병기)" or text == "/" for text, kind in comps):
        first = []
        for text, kind in comps:
            if kind == "/(병기)" or text == "/":
                break
            first.append((text, kind))
        comps = first
    syllables = hangul.replace(" ", "")
    pieces: list[str] = []
    pending: int | None = None  # index in pieces of a component whose length is not known yet
    pos = 0
    for text, kind in comps:
        if kind == "한자":
            h = clean_hanja(text)
            pieces.append(h)
            pos += len(h)
            continue
        literal = re.sub(r"[\s^-]", "", text)
        idx = syllables.find(literal, pos) if literal else -1
        if idx == pos or (idx > pos and pending is not None):
            if pending is not None:
                pieces[pending] = "-" * (idx - pos)
                pending = None
            pieces.append("-" * len(literal))
            pos = idx + len(literal)
        elif pending is None:
            pending = len(pieces)
            pieces.append("")
        else:
            return None  # two components of unknown length cannot be placed
    if pending is not None:
        gap = len(syllables) - sum(len(p) for p in pieces)
        if gap < 1:
            return None
        pieces[pending] = "-" * gap
    return "".join(pieces)


# Hangul tails the full dump leaves out of the original-language field:
# 가감-하다 → 加減, 가각-히 → 苛刻. Longest first so 스럽다 wins over 다.
HANGUL_SUFFIXES = ("스럽다", "시키다", "하다", "되다", "롭다", "답다", "히", "이", "적", "들", "껏", "째")


def align_with_suffix(hangul: str, hanja: str) -> str | None:
    """``align`` that also accepts a headword ending in a derivational tail.

    The tail stays Hangul in the mixed form (加減하다, 苛刻히), which is what
    the converter must output. Only the suffixes in ``HANGUL_SUFFIXES`` are
    tried, so arbitrary misalignments are still rejected.
    """
    mixed = align(hangul, hanja)
    if mixed is not None:
        return mixed
    for suf in HANGUL_SUFFIXES:
        stem = hangul[: -len(suf)]
        if hangul.endswith(suf) and stem and stem.replace(" ", ""):
            head = align(stem, hanja)
            if head is not None:
                return head + suf
    return None


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
        if h == "-" or h == ch:  # no Hanja for this syllable (mixed word)
            out.append(ch)
        elif is_cjk(h):
            out.append(h)
        else:
            return None
    mixed = "".join(out)
    if not any(is_cjk(c) for c in mixed):
        return None
    return mixed


# Parts of speech of native words that can collide with a Sino-Korean headword (사랑 vs 舍廊).
NATIVE_POS = frozenset({"명사", "부사", "관형사", "의존 명사", "수사"})


def note_native(item: ET.Element, word: str, stats: ParseStats) -> None:
    """Record a native (고유어) headword so that the same sound as a Sino-Korean entry is flagged, not converted."""
    pos = _find_text(item, "pos") or ""
    hangul = clean_headword(word)
    if pos not in NATIVE_POS or not hangul or not all("가" <= c <= "힣" for c in hangul):
        return
    sense = re.sub(r"<[^>]+>", "", _find_text(item, "definition") or "").replace("\t", " ").replace("\n", " ")[:80]
    stats.native_pos.setdefault((hangul, pos), (sense, f"stdict:{_find_text(item, 'target_code') or hangul}"))


GENERAL_CAT = "없음"


def sense_domain(cats: Iterable[str | None]) -> str:
    """Field label(s) of the senses of one entry, or "" when any sense is general (no label, or 없음).

    An entry is a specialist word only if every sense says so; a reading with one everyday sense
    is everyday vocabulary, whatever else it also means.
    """
    seen: set[str] = set()
    for cat in cats:
        cat = (cat or "").strip()
        if not cat or cat == GENERAL_CAT:
            return ""
        seen.add(cat)
    return ",".join(sorted(seen))


def item_domain(item: ET.Element) -> str:
    cats = []
    for sense in item.iter():
        if _local(sense.tag) == "sense_info":
            cats.append(_find_text(sense, "cat"))
    return sense_domain(cats)


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
        try:
            for _, el in ET.iterparse(fh, events=("end",)):
                if _local(el.tag) == "item":
                    yield el
                    el.clear()
        except ET.ParseError as e:  # a truncated or corrupt chunk: say which one
            raise InputError(f"{name}: XML이 온전하지 않습니다 / not well-formed XML ({e})") from e


def _open_all(path: Path) -> Iterable[tuple[str, IO[bytes]]]:
    if path.is_dir():
        for p in sorted(q for q in path.rglob("*") if q.suffix.lower() == ".xml"):
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
        comps = _components(item)
        raw_hanja = "".join(raw for raw, _ in comps) or _find_text(item, "origin") or ""
        word_type = _find_text(item, "word_type") or ""
        if word_type and word_type not in SINO_WORD_TYPES:
            if word_type == "고유어" and _find_text(item, "word_unit") == "단어":
                note_native(item, word, stats)
            continue
        if not any(is_cjk(c) for c in raw_hanja):
            continue
        stats.sino += 1
        code = _find_text(item, "target_code") or ""
        sup = _find_text(item, "sup_no") or split_homonym(word)[1]
        source = f"stdict:{code}" if code else f"stdict:{word}{sup}"
        hangul = clean_headword(word)
        assembled = components_to_hanja(hangul, comps) if len(comps) > 1 else clean_hanja(raw_hanja)
        mixed = align_with_suffix(hangul, assembled) if assembled else None
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
        sense = re.sub(r"<[^>]+>", "", _find_text(item, "definition") or "")
        sense = sense.replace("\t", " ").replace("\n", " ")[:80]
        entries.append(Entry(hangul, mixed, pos, source, sense, domain=item_domain(item)))
        stats.entries += 1
    return entries, rejects, stats
