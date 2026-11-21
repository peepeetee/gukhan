# SPDX-License-Identifier: Apache-2.0
"""Hanja the lawmaker wrote next to a legal term: ``분사무소(分事務所)``, ``개의(開議)``.

Current Korean statutes are written in Hangul, but the plain-language rewrites since the 2000s
annotate a term with its Hanja where it first appears. Each annotation is an attested pair chosen
by the drafters of a statute, which makes it a source of legal vocabulary that dictionaries miss
(將星級, 解囑, 除斥) and of evidence for which reading a legal text uses.

Input is a checkout (or a folder of copies) of the legalize-kr/legalize-kr repository, which
mirrors law.go.kr as one Markdown file per statute under ``kr/<법령명>/<법령구분>.md``. The statute
text is a public work (저작권법 제7조); the mirror's own structure and metadata are MIT. A file whose
front matter says ``상태: 폐지`` is skipped.

The Hangul word is the run of Hangul syllables right before the parenthesis; when it is longer
than the Hanja, the last syllables carry the gloss (``소속기관(機關)`` → 기관 機關). Glosses of one
syllable are not used: 과(科) and 업(業) say too little. Hanja must be possible readings of the
syllables when Unihan readings are given.

``parse`` returns lexicon entries (source ``law:<statute>``, domain ``법률``, weight 0 so a lexicon
built with it does not start to count as weighted) and, in ``stats.pairs``, how often and in how many
statutes each pair is glossed. The builder adds an entry only for a Hangul word no other source knows;
the counts go to ``law-glosses.tsv`` and the dominant readings to an opt-in override list.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .hangul import is_cjk
from .stdict import Entry, Reject, align, validate_readings

SOURCE_PREFIX = "law"
DOMAIN = "법률"
GLOSS = re.compile(r"([가-힣]+)\(([一-鿿]+)\)")
_ESCAPED = re.compile(r"\\([()])")
_STATUS_REPEALED = re.compile(r"^상태:\s*[\"']?폐지", re.M)
MIN_SYLLABLES = 2


@dataclass
class LawStats:
    items: int = 0  # statute files read
    repealed: int = 0
    glossed: int = 0  # statutes with at least one usable gloss
    tokens: int = 0  # gloss occurrences seen
    single: int = 0  # occurrences of a one-syllable gloss, not used
    entries: int = 0
    rejected: int = 0
    excluded: int = 0  # occurrences dropped because the pair is in an excluded gold set
    pairs: dict[tuple[str, str], tuple[int, int]] = field(default_factory=dict)  # (hangul, hanja) → (count, statutes)


def iter_statutes(root: Path) -> Iterator[tuple[str, str]]:
    """Yield ``(statute id, text)`` for every Markdown file under ``root`` (or ``root/kr``)."""
    base = root / "kr" if (root / "kr").is_dir() else root
    for p in sorted(base.rglob("*.md")):
        if p.name.lower() in {"readme.md", "license.md"} and p.parent == base:
            continue
        yield f"{p.parent.name}/{p.stem}", p.read_text(encoding="utf-8-sig")


def gloss_pairs(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield ``(word, tail, hanja)``: the Hangul run, its last len(hanja) syllables, the Hanja."""
    text = _ESCAPED.sub(r"\1", unicodedata.normalize("NFC", text))  # compatibility ideographs → unified
    for m in GLOSS.finditer(text):
        word, hanja = m.groups()
        if len(word) >= len(hanja):
            yield word, word[len(word) - len(hanja) :], hanja
        else:
            yield word, "", hanja


def pairs_in_items(path: Path) -> set[tuple[str, str]]:
    """The ``(hangul, hanja)`` pairs a regression items file holds: each maximal Hanja run of the gold text."""
    out: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8-sig") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4 or len(parts[2]) != len(parts[3]):
                continue
            hangul, mixed = parts[2], parts[3]
            start = None
            for i, ch in enumerate(mixed + " "):
                if is_cjk(ch):
                    if start is None:
                        start = i
                elif start is not None:
                    out.add((hangul[start:i], mixed[start:i]))
                    start = None
    return out


def parse(
    root: Path,
    readings: dict[str, list[str]] | None = None,
    exclude: Iterable[tuple[str, str]] = (),
) -> tuple[list[Entry], list[Reject], LawStats]:
    excluded = set(exclude)
    stats = LawStats()
    counts: Counter[tuple[str, str]] = Counter()
    statutes: dict[tuple[str, str], set[str]] = {}
    first: dict[tuple[str, str], str] = {}
    rejects: list[Reject] = []
    rejected_seen: set[tuple[str, str, str]] = set()
    glossed: set[str] = set()
    for sid, text in iter_statutes(root):
        stats.items += 1
        if _STATUS_REPEALED.search(text[:600]):
            stats.repealed += 1
            continue
        for word, tail, hanja in gloss_pairs(text):
            stats.tokens += 1
            if len(tail) < MIN_SYLLABLES:
                if tail:
                    stats.single += 1
                elif (word, hanja, "hanja longer than word") not in rejected_seen:
                    rejected_seen.add((word, hanja, "hanja longer than word"))
                    rejects.append(Reject(word, hanja, f"{SOURCE_PREFIX}:{sid}", "hanja longer than the Hangul word"))
                    stats.rejected += 1
                continue
            key = (tail, hanja)
            if key in excluded:
                stats.excluded += 1
                continue
            mixed = align(tail, hanja)
            why = None if mixed else "hanja does not align with headword"
            if mixed and readings:
                why = validate_readings(tail, mixed, readings)
            if why:
                if (tail, hanja, why) not in rejected_seen:
                    rejected_seen.add((tail, hanja, why))
                    rejects.append(Reject(tail, hanja, f"{SOURCE_PREFIX}:{sid}", why))
                    stats.rejected += 1
                continue
            counts[key] += 1
            statutes.setdefault(key, set()).add(sid)
            first.setdefault(key, sid)
            glossed.add(sid)
    stats.glossed = len(glossed)
    entries = []
    for key in sorted(counts):
        stats.pairs[key] = (counts[key], len(statutes[key]))
        entries.append(Entry(key[0], key[1], "명사", f"{SOURCE_PREFIX}:{first[key]}", "", 0, DOMAIN))
    stats.entries = len(entries)
    return entries, rejects, stats


def pairs_tsv(stats: LawStats) -> str:
    """``hangul hanja count statutes share``: share is this Hanja's part of the word's glosses, in statutes."""
    by_word: dict[str, int] = {}
    for (hangul, _), (_, n) in stats.pairs.items():
        by_word[hangul] = by_word.get(hangul, 0) + n
    rows = sorted(stats.pairs.items(), key=lambda kv: (-kv[1][1], -kv[1][0], kv[0]))
    lines = ["# hangul\thanja\tcount\tstatutes\tshare\n"]
    for (hangul, hanja), (count, n) in rows:
        lines.append(f"{hangul}\t{hanja}\t{count}\t{n}\t{n / by_word[hangul]:.2f}\n")
    return "".join(lines)


def override_lines(stats: LawStats, min_statutes: int = 3, min_share: float = 0.9) -> list[str]:
    """``hangul = hanja`` for words the statutes gloss one way in at least ``min_statutes`` statutes.

    Opt-in: a statute reading is not the everyday reading (의사 as 意思 in a civil code), so this
    file is for processing legal text, never loaded by default.
    """
    by_word: dict[str, int] = {}
    for (hangul, _), (_, n) in stats.pairs.items():
        by_word[hangul] = by_word.get(hangul, 0) + n
    out = []
    for (hangul, hanja), (_, n) in sorted(stats.pairs.items(), key=lambda kv: (-kv[1][1], kv[0])):
        if n >= min_statutes and n / by_word[hangul] >= min_share:
            out.append(f"{hangul} = {hanja}")
    return out
