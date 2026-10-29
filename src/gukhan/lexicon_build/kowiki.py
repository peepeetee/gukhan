# SPDX-License-Identifier: Apache-2.0
"""Hangul–Hanja pairs for names, from the lead sentence of Korean Wikipedia articles.

Input is the MediaWiki export dump (``kowiki-latest-pages-articles.xml.bz2``
from dumps.wikimedia.org, no login; plain or ``.gz`` XML also accepted). Korean
leads put the Hanja in parentheses after the bold title::

    '''이순신'''(李舜臣, 1545년 4월 28일 ~ 1598년 12월 16일)은 ...
    '''대한민국 헌법'''(大韓民國憲法, {{llang|en|Constitution ...}})은 ...
    '''서울'''({{한자|서울}}) ...

Only the first bold phrase followed by a parenthesis in the first paragraph is
read. The first comma-separated item must contain Hanja; each Hanja must be a
possible reading of its Hangul syllable (via Unihan, 頭音法則 allowed), so a
Chinese-reading name such as 마오쩌둥 (毛澤東) is rejected and logged rather
than turned into a Sino-Korean pair.

Entries are proper nouns (``고유 명사``). The text is CC BY-SA 4.0 (and GFDL).
"""

from __future__ import annotations

import bz2
import gzip
import io
import re
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

from .hangul import is_cjk, is_syllable
from .stdict import Entry, ParseStats, Reject, align, clean_hanja, validate_readings

SOURCE_PREFIX = "kowiki"
# Templates whose last all-Hanja argument is the Hanja form: {{한자|大韓民國}}, {{llang|zh|大韓民國}}.
HANJA_TEMPLATES = frozenset({"한자", "hanja", "漢字", "lang", "llang", "lang-zh", "lang-hani", "zh", "한문", "중국어"})
_LABEL = re.compile(r"^\s*(?:한자|漢字|한문|한자 표기|중국어|한자어)\s*[:：]\s*")
_BOLD = re.compile(r"'''(?P<b>[^'\n]+?)'''\s*[(（](?P<p>[^)）\n]*)[)）]")
_INNERMOST_TEMPLATE = re.compile(r"\{\{([^{}]*)\}\}")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_REF = re.compile(r"<ref[^>/]*/>|<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
_TABLE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
_FILE_LINK = re.compile(r"\[\[(?:파일|File|그림|Image|분류|Category)\s*:[^\]]*\]\]", re.IGNORECASE)
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_TAG = re.compile(r"<[^>]+>")
_DISAMBIG = re.compile(r"\s*\(([^)]*)\)\s*$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _open(path: Path) -> io.BufferedIOBase:
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def _template(match: re.Match) -> str:
    parts = [p.strip() for p in match.group(1).split("|")]
    if parts[0].lower() not in HANJA_TEMPLATES:
        return ""
    for arg in reversed(parts[1:]):
        value = arg.split("=", 1)[-1].strip()
        if value and all(is_cjk(c) for c in value):
            return value
    return ""


def strip_markup(text: str) -> str:
    """Wikitext → plain text with ``'''`` kept, Hanja templates unwrapped, other templates dropped."""
    text = _TABLE.sub("", _REF.sub("", _COMMENT.sub("", text)))
    previous = None
    while previous != text:
        previous, text = text, _INNERMOST_TEMPLATE.sub(_template, text)
    text = _LINK.sub(r"\1", _FILE_LINK.sub("", text))
    text = text.replace("'''", "\x00").replace("''", "").replace("\x00", "'''")
    return _TAG.sub("", text)


def lead_pair(wikitext: str) -> tuple[str, str] | None:
    """``(bold_title, text_in_parentheses)`` of the first paragraph that has one, else ``None``."""
    for line in strip_markup(wikitext).splitlines():
        line = line.strip()
        if "'''" not in line or line[0] in "*:;#|=!{":
            continue
        m = _BOLD.search(line)
        return (m.group("b").strip(), m.group("p")) if m else None
    return None


def hanja_of(parenthetical: str, hangul: str) -> str | None:
    """First item of the parenthesis as a string ``align`` accepts (Hangul syllables become ``-``)."""
    first = re.split(r"[,;，、]", parenthetical, maxsplit=1)[0]
    first = clean_hanja(_LABEL.sub("", first))
    if not any(is_cjk(c) for c in first):
        return None
    if not all(is_cjk(c) or is_syllable(c) for c in first):
        return None  # Latin letters, digits or punctuation: a date or a foreign name, not a Hanja form
    return "".join("-" if is_syllable(c) else c for c in first)


def iter_pages(path: Path) -> Iterator[tuple[str, str]]:
    """Yield ``(title, wikitext)`` for every main-namespace, non-redirect page."""
    with _open(path) as fh:
        root = None
        for event, el in ET.iterparse(fh, events=("start", "end")):
            if event == "start":
                if root is None:
                    root = el
                continue
            if _local(el.tag) != "page":
                continue
            title = ns = text = ""
            redirect = False
            for child in el.iter():
                name = _local(child.tag)
                if name == "title":
                    title = child.text or ""
                elif name == "ns" and not ns:
                    ns = (child.text or "").strip()
                elif name == "redirect":
                    redirect = True
                elif name == "text":
                    text = child.text or ""
            if ns == "0" and not redirect and text:
                yield title, text
            root.clear()


def parse(
    path: Path,
    readings: dict[str, list[str]] | None = None,
) -> tuple[list[Entry], list[Reject], ParseStats]:
    entries: list[Entry] = []
    rejects: list[Reject] = []
    stats = ParseStats()
    for title, text in iter_pages(path):
        stats.items += 1
        lead = lead_pair(text)
        if lead is None:
            continue
        bold, paren = lead
        hangul = _DISAMBIG.sub("", bold).strip()
        if not hangul or not all(is_syllable(c) or c == " " for c in hangul):
            continue
        raw = hanja_of(paren, hangul)
        if raw is None:
            continue
        stats.sino += 1
        source = f"{SOURCE_PREFIX}:{title}"
        mixed = align(hangul, raw)
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
        m = _DISAMBIG.search(title)
        entries.append(Entry(hangul, mixed, "고유 명사", source, m.group(1) if m else ""))
        stats.entries += 1
    stats.tags_seen.add("page")
    return entries, rejects, stats


__all__ = ["parse", "iter_pages", "lead_pair", "hanja_of", "strip_markup"]
