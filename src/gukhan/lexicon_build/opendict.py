# SPDX-License-Identifier: Apache-2.0
"""Parse the 우리말샘 (opendict.korean.go.kr) XML dump into lexicon entries.

우리말샘 is the 國立國語院's open, contributor-edited dictionary, CC BY-SA 2.0
KR like 표준국어대사전. The dump (``opendict/0050000.xml`` … in the
spellcheck-ko/korean-dict-nikl mirror, about 79 MB per chunk) has one
``<item>`` per *sense*, so the same headword and Hanja recur with different
``target_code``\\s; the builder merges them into one line.

Shape, verified on the 2026-06 dump::

    <item>
      <target_code>449066</target_code>
      <wordInfo>
        <word>생균^수</word>              ^ = space, - = morpheme boundary
        <word_unit>구</word_unit>          어휘 | 구 | 속담 | 관용구
        <word_type>한자어</word_type>      고유어 | 한자어 | 혼종어 | 외래어
        <original_language_info>
          <original_language>生菌數</original_language>
          <language_type>한자</language_type>
        </original_language_info>         repeated once per component
      </wordInfo>
      <senseInfo>
        <sense_no>001</sense_no>
        <pos>명사</pos>                    absent for 구
        <type>일반어</type>                일반어 | 방언 | 북한어 | 옛말
        <definition>…</definition>
        <example_info>…</example_info>    never read
      </senseInfo>
    </item>

What is kept: ``word_unit`` 어휘 or 구, ``type`` 일반어, ``word_type`` 한자어 or
혼종어 (or blank), at least one 한자 component. Dialect, North-Korean and
archaic senses are skipped, as are proverbs, idioms and senses the
dictionary itself marks as non-standard spellings (⇒규범 표기는 …). Usage examples are
never read, so the source-cited 용례 exclusion in the licence is satisfied.

Mixed words assemble their Hanja from the components: 生 + 과일 (고유어)
→ 生과일; a foreign component of unknown syllable count (生 + 과일 + juice)
is allowed once per headword, its length being whatever is left.
``/(병기)`` separators mark alternative Hanja spellings (齟齬/鉏鋙); only the
first alternative is taken, so a spelling variant never becomes a flag.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .hangul import is_cjk
from .stdict import (
    Entry,
    ParseStats,
    Reject,
    _local,
    align_with_suffix,
    clean_hanja,
    clean_headword,
    components_to_hanja,
    iter_items,
    validate_readings,
)

SOURCE_PREFIX = "opendict"
KEEP_UNITS = {"어휘", "구"}
KEEP_TYPES = {"일반어"}
SINO_WORD_TYPES = {"한자어", "혼종어", ""}
# 관·명 = 관형사 and 명사 … ; one entry per part of speech
POS_ABBREVIATIONS = {"관": "관형사", "명": "명사", "부": "부사", "수": "수사", "감": "감탄사", "대": "대명사"}
ROOT_DEFINITION = re.compile(r"^‘.+’의 어근\.?$")
NONSTANDARD_NOTE = "규범 표기는"


def _text(el: ET.Element | None, name: str) -> str:
    if el is None:
        return ""
    found = el.find(name)
    return (found.text or "").strip() if found is not None else ""


def expand_pos(pos: str, definition: str) -> list[str]:
    """``관·명`` → ``["관형사", "명사"]``; ``품사 없음`` with an 어근 definition → ``["어근"]``."""
    if pos == "품사 없음" and ROOT_DEFINITION.match(definition):
        return ["어근"]
    if "·" in pos:
        out = [POS_ABBREVIATIONS.get(p, p) for p in pos.split("·")]
        return out
    return [pos]


def components(word_info: ET.Element) -> list[tuple[str, str]]:
    """``[(original_language, language_type), …]`` in document order."""
    out = []
    for info in word_info.findall("original_language_info"):
        out.append((_text(info, "original_language"), _text(info, "language_type")))
    return out


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
        word_info = item.find("wordInfo")
        sense_info = item.find("senseInfo")
        word = _text(word_info, "word")
        if not word:
            continue
        if _text(word_info, "word_unit") not in KEEP_UNITS:
            continue
        if _text(sense_info, "type") not in KEEP_TYPES:
            continue
        if _text(word_info, "word_type") not in SINO_WORD_TYPES:
            continue
        comps = components(word_info)
        if not any(kind == "한자" and any(is_cjk(c) for c in raw) for raw, kind in comps):
            continue
        definition = re.sub(r"<[^>]+>", "", _text(sense_info, "definition"))
        if NONSTANDARD_NOTE in definition:
            continue  # 생과일쥬스 ⇒규범 표기는 ‘생과일주스’이다: a misspelling, not a word to expect in text
        stats.sino += 1
        code = _text(item, "target_code")
        source = f"{SOURCE_PREFIX}:{code}" if code else f"{SOURCE_PREFIX}:{word}"
        hangul = clean_headword(word)
        raw_hanja = "".join(raw for raw, _ in comps)
        assembled = components_to_hanja(hangul, comps)
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
        sense = definition.replace("\t", " ").replace("\n", " ")[:80]
        pos = _text(sense_info, "pos")
        if not pos and _text(word_info, "word_unit") == "구":
            pos = "품사 없음"  # what 표준국어대사전 writes for phrases; keeps the two sources alike
        for p in expand_pos(pos, definition):
            entries.append(Entry(hangul, mixed, p, source, sense))
            stats.entries += 1
    return entries, rejects, stats


__all__ = ["parse", "expand_pos", "components", "clean_hanja"]
