# SPDX-License-Identifier: Apache-2.0
"""Korean Hanja forms from Wikidata lexemes (CC0), plus a survey of what the dump holds.

Input is ``latest-lexemes.json.bz2`` from dumps.wikimedia.org/wikidatawiki/entities/
(no login; plain or ``.gz`` accepted): a JSON array with one lexeme per line. Written
from the documented Wikibase lexeme JSON, not yet run on a real dump, so run the
survey first::

    python -m gukhan.lexicon_build.wikidata_lexemes latest-lexemes.json.bz2

It counts Korean lexemes (language Q9176), how many have a Hangul lemma, how many
carry an all-Hanja value in any lemma or form (whatever the language code, e.g.
``ko-hani``), and which string-valued statement properties hold all-Hanja values.
If a property such as P1234 carries the Hanja, build with ``hanja_properties``.
"""

from __future__ import annotations

import bz2
import gzip
import io
import json
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .hangul import is_cjk, is_syllable
from .stdict import Entry, ParseStats, Reject, align, validate_readings

KOREAN = "Q9176"
SOURCE_PREFIX = "wikidata"
# Lexical categories: noun, proper noun, adverb. Others are skipped (counted), not guessed.
POS = {"Q1084": "명사", "Q147276": "고유 명사", "Q380057": "부사"}


def _open(path: Path) -> io.BufferedIOBase:
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def iter_lexemes(path: Path) -> Iterator[dict[str, Any]]:
    with _open(path) as fh:
        for raw in fh:
            line = raw.decode("utf-8").strip().rstrip(",")
            if line in ("", "[", "]"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _hangul(s: str) -> bool:
    return bool(s) and all(is_syllable(c) or c == " " for c in s) and not s.isspace()


def _hanja(s: str) -> bool:
    return bool(s) and all(is_cjk(c) or c == " " for c in s) and any(is_cjk(c) for c in s)


def _values(lex: dict[str, Any]) -> Iterator[str]:
    for rep in (lex.get("lemmas") or {}).values():
        yield rep.get("value", "")
    for form in lex.get("forms") or []:
        for rep in (form.get("representations") or {}).values():
            yield rep.get("value", "")


def _string_claims(lex: dict[str, Any]) -> Iterator[tuple[str, str]]:
    for prop, statements in (lex.get("claims") or {}).items():
        for st in statements:
            value = ((st.get("mainsnak") or {}).get("datavalue") or {}).get("value")
            if isinstance(value, str):
                yield prop, value
            elif isinstance(value, dict) and isinstance(value.get("text"), str):
                yield prop, value["text"]


def _korean(lex: dict[str, Any]) -> bool:
    return lex.get("language") == KOREAN and lex.get("type", "lexeme") == "lexeme"


def survey(path: Path) -> dict[str, Any]:
    """Counts that decide whether the dump is worth building from."""
    c: Counter[str] = Counter()
    props: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    samples: list[str] = []
    for lex in iter_lexemes(path):
        c["lexemes"] += 1
        if not _korean(lex):
            continue
        c["korean"] += 1
        categories[lex.get("lexicalCategory", "?")] += 1
        values = [v for v in _values(lex) if v]
        if any(_hangul(v) for v in values):
            c["hangul_lemma"] += 1
        if any(_hanja(v) for v in values):
            c["hanja_in_lemma_or_form"] += 1
            if len(samples) < 10:
                samples.append(f"{lex.get('id')}: " + " / ".join(values[:4]))
        hits = {p for p, v in _string_claims(lex) if _hanja(v)}
        for p in hits:
            props[p] += 1
        if hits:
            c["hanja_in_statement"] += 1
    return {
        "counts": dict(c),
        "hanja_statement_properties": dict(props.most_common(10)),
        "categories": dict(categories.most_common(10)),
        "samples": samples,
    }


def parse(
    path: Path,
    readings: dict[str, list[str]] | None = None,
    hanja_properties: tuple[str, ...] = (),
) -> tuple[list[Entry], list[Reject], ParseStats]:
    entries: list[Entry] = []
    rejects: list[Reject] = []
    stats = ParseStats()
    for lex in iter_lexemes(path):
        stats.items += 1
        if not _korean(lex):
            continue
        pos = POS.get(lex.get("lexicalCategory", ""))
        if pos is None:
            continue
        values = [v for v in _values(lex) if v]
        hangul_words = sorted({v for v in values if _hangul(v)})
        hanja_words = {v for v in values if _hanja(v)}
        hanja_words |= {v for p, v in _string_claims(lex) if p in hanja_properties and _hanja(v)}
        if not hangul_words or not hanja_words:
            continue
        stats.sino += 1
        source = f"{SOURCE_PREFIX}:{lex.get('id', '?')}"
        for hangul in hangul_words[:1]:
            for raw in sorted(hanja_words):
                raw = raw.replace(" ", "")
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
                entries.append(Entry(hangul, mixed, pos, source, ""))
                stats.entries += 1
    stats.tags_seen.add("lexeme")
    return entries, rejects, stats


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(
            "使用法 / usage: python -m gukhan.lexicon_build.wikidata_lexemes latest-lexemes.json.bz2",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(survey(Path(args[0])), ensure_ascii=False, indent=2))
    return 0


__all__ = ["parse", "survey", "iter_lexemes"]

if __name__ == "__main__":
    sys.exit(main())
