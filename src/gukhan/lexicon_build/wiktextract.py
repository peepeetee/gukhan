# SPDX-License-Identifier: Apache-2.0
"""Parse a wiktextract JSONL file (kaikki.org) into lexicon entries.

Needs no login. The English Wiktionary's Korean entries are published by
kaikki.org as ``kaikki.org-dictionary-Korean.jsonl`` (one JSON object per
line, wiktextract schema). Two shapes carry Hanja:

- a Hangul headword with a form tagged ``hanja``::

    {"word": "핵산", "lang_code": "ko", "pos": "noun",
     "forms": [{"form": "核酸", "tags": ["hanja"]}], "senses": [...]}

- a Hanja headword with a form tagged ``hangeul`` (the "hanja form of"
  pages)::

    {"word": "制定", "lang_code": "ko", "pos": "noun",
     "forms": [{"form": "제정", "tags": ["hangeul"]}], ...}

Both become ``(hangul, hanja)`` entries. Per-character pages (``pos`` of
``character``) are skipped; single-syllable *words* such as 왕 王 are kept.
The data is Wiktionary content under CC BY-SA (4.0 since 2023) + GFDL.
"""

from __future__ import annotations

import gzip
import io
import json
import re
from collections.abc import Iterator
from pathlib import Path

from .hangul import is_cjk, is_syllable
from .stdict import Entry, ParseStats, Reject, align, clean_hanja, validate_readings

POS_MAP = {
    "noun": "명사",
    "name": "고유 명사",
    "proper noun": "고유 명사",
    "adv": "부사",
    "prefix": "접두사",
    "suffix": "접미사",
    "det": "관형사",
    "num": "수사",
    "verb": "동사",
    "adj": "형용사",
    "intj": "감탄사",
    "root": "어근",
    "phrase": "구",
    "counter": "의존 명사",
    "classifier": "의존 명사",
}
SKIP_POS = {"character", "syllable", "romanization", "punct", "symbol"}


def _open(path: Path) -> io.TextIOBase:
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path), encoding="utf-8")
    return path.open(encoding="utf-8")


def _is_hangul_word(s: str) -> bool:
    return bool(s) and all(is_syllable(c) or c == " " for c in s) and not s.isspace()


def _is_hanja_word(s: str) -> bool:
    """At least one Hanja; Hangul syllables allowed for mixed words such as 工夫하다."""
    return bool(s) and all(is_cjk(c) or is_syllable(c) or c == " " for c in s) and any(is_cjk(c) for c in s)


def _pairs(obj: dict) -> Iterator[tuple[str, str, bool]]:
    """Yield (hangul, raw_hanja, from_hangul_page) found in one JSON object."""
    word = obj.get("word", "")
    forms = obj.get("forms") or []
    if _is_hangul_word(word):
        for f in forms:
            if "hanja" in (f.get("tags") or []) and _is_hanja_word(f.get("form", "")):
                yield word, f["form"], True
    elif _is_hanja_word(word):
        for f in forms:
            if "hangeul" in (f.get("tags") or []) and _is_hangul_word(f.get("form", "")):
                yield f["form"], word, False


# Greedy up to the closing quote so nested parentheses inside the gloss survive:
# 「hanja form of 회의 (“(Chinese character classification) compound …”)」.
_FORM_OF = re.compile(r"^hanja form of \S+\s*\((?:[“\"]|&quot;)?(.+?)(?:[”\"]|&quot;)?\)\s*$", re.IGNORECASE)


_ROMAN_THEN_PAREN = re.compile(r"^[A-Za-z' -]+ \((.+)\)$")
_LEADING_LABEL = re.compile(r"^\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*")


def tidy_gloss(text: str, romanizations: frozenset[str] | set[str] = frozenset()) -> str:
    """Make a Wiktionary gloss useful on one line.

    「yeoksa (a practice in the Joseon Dynasty …)」 → the parenthetical, when the
    leading word is the headword's own romanisation and so says nothing;
    「(Chinese character classification) a character …」 → drop the leading
    label unless nothing else is left.
    """
    text = " ".join(text.split())
    m = _ROMAN_THEN_PAREN.match(text)
    if m and text[: m.start(1) - 2].strip() in romanizations:
        text = m.group(1)
    m = _LEADING_LABEL.match(text)
    if m and text[m.end() :].strip():
        text = text[m.end() :].strip()
    elif m:
        text = m.group(1)
    return text


def shorten(text: str, limit: int = 80, romanizations: frozenset[str] | set[str] = frozenset()) -> str:
    """Tidy, then cut at a word boundary without leaving an unbalanced parenthesis."""
    text = tidy_gloss(text, romanizations)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    while cut.count("(") > cut.count(")") and "(" in cut:
        shorter = cut[: cut.rfind("(")].rstrip(" ,;")
        if not shorter:
            break
        cut = shorter
    return cut + "…"


def _gloss(obj: dict) -> str:
    """First gloss; for 「hanja form of 역사 (“history”)」 pages, the quoted gloss."""
    fallback = ""
    roman = {f.get("form", "") for f in obj.get("forms") or [] if "romanization" in (f.get("tags") or [])}
    for sense in obj.get("senses") or []:
        for g in sense.get("glosses") or []:
            if not g:
                continue
            g = g.replace("\t", " ").replace("\n", " ")
            m = _FORM_OF.match(g)
            if m:
                fallback = fallback or shorten(m.group(1), romanizations=roman)
            elif not g.lower().startswith("hanja form of"):
                return shorten(g, romanizations=roman)
    return fallback


def _weight(obj: dict, from_hangul_page: bool) -> int:
    """Crude likelihood, higher = more likely reading.

    10 for a reading listed on the Hangul page, plus one per sense (max 9),
    plus one per derived, related or compound term listed (max 9): common
    words such as 電氣 have derived terms, rare ones such as 轉機 do not.
    """
    senses = [s for s in obj.get("senses") or [] if "form-of" not in (s.get("tags") or [])]
    links = sum(len(obj.get(k) or []) for k in ("derived", "related", "compounds"))
    links += sum(len(s.get("derived") or []) + len(s.get("related") or []) for s in obj.get("senses") or [])
    return (10 if from_hangul_page else 0) + min(len(senses), 9) + min(links, 9)


def parse(
    path: Path,
    readings: dict[str, list[str]] | None = None,
) -> tuple[list[Entry], list[Reject], ParseStats]:
    entries: list[Entry] = []
    rejects: list[Reject] = []
    stats = ParseStats()
    with _open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                stats.rejected += 1
                continue
            stats.items += 1
            if stats.items <= 50:
                stats.tags_seen.update(obj.keys())
            if obj.get("lang_code") != "ko":
                continue
            pos_raw = obj.get("pos", "")
            if pos_raw in SKIP_POS:
                continue
            pos = POS_MAP.get(pos_raw, pos_raw)
            for hangul, raw, from_hangul_page in _pairs(obj):
                stats.sino += 1
                source = f"enwikt:{obj.get('word', '')}"
                mixed = align(hangul, clean_hanja(raw))
                if mixed is not None and pos == "구" and any(is_syllable(c) for c in mixed):
                    continue  # phrases with particles (甲과 乙) can never be matched; skip quietly
                if mixed is None:
                    rejects.append(Reject(hangul, raw, source, "hanja does not align with headword"))
                    stats.rejected += 1
                    continue
                if readings:
                    why = validate_readings(hangul, mixed, readings)
                    if why:
                        rejects.append(Reject(hangul, raw, source, why))
                        stats.rejected += 1
                        continue
                entries.append(Entry(hangul, mixed, pos, source, _gloss(obj), _weight(obj, from_hangul_page)))
                stats.entries += 1
    return entries, rejects, stats
