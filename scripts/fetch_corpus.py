# SPDX-License-Identifier: Apache-2.0
"""Fetch the public-domain source texts listed in tests/regression/sources.tsv.

Run on a machine with ordinary internet access::

    python scripts/fetch_corpus.py --out build/corpus [--only constitution-1948]

For each row the raw page is saved as ``<id>.raw`` and the text between the
start and end markers, with HTML tags stripped, as ``<id>.txt``. Nothing is
committed by this script; items are produced with ``gukhan-regress prepare``
and reviewed before they enter tests/regression/.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "tests" / "regression" / "sources.tsv"
UA = "gukhan-corpus-fetch/0.1 (+https://github.com/peepeetee/gukhan)"


def read_sources() -> list[dict[str, str]]:
    rows = []
    with SOURCES.open(encoding="utf-8") as fh:
        header = None
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts, strict=False)))
    return rows


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>|</dt>|</dd>|</dl>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(raw)
    # The Constitutional Court pages encode many Hanja as CJK compatibility
    # ideographs (歷 U+F98C for U+6B77); NFC folds them to the unified forms.
    text = unicodedata.normalize("NFC", text)
    return "\n".join(" ".join(line.split()) for line in text.splitlines())


def wikisource_text(raw: bytes) -> str:
    data = json.loads(raw)
    if "error" in data:
        raise ValueError(data["error"].get("info", "wikisource API error"))
    return wikitext_to_text(data["parse"]["wikitext"]["*"])


def wikitext_to_text(wt: str) -> str:
    """Strip the common wiki markup: templates, links, refs, emphasis, headings, tables."""
    for _ in range(3):  # nested templates
        wt = re.sub(r"\{\{[^{}]*\}\}", "", wt)
    wt = re.sub(r"(?is)<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", wt)
    wt = re.sub(r"(?s)\{\|.*?\|\}", "", wt)
    wt = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", wt)
    wt = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", wt)
    wt = re.sub(r"'{2,}", "", wt)
    wt = re.sub(r"(?m)^=+\s*(.*?)\s*=+$", r"\1", wt)
    wt = re.sub(r"(?m)^[*#:;]+\s*", "", wt)
    wt = re.sub(r"<[^>]+>", "", wt)
    wt = html.unescape(wt)
    return "\n".join(" ".join(line.split()) for line in wt.splitlines())


def extract(text: str, start: str, end: str) -> str:
    a = text.find(start) if start else 0
    if a < 0:
        raise ValueError(f"start marker not found: {start!r}")
    b = text.find(end, a) if end else len(text)
    if b < 0:
        raise ValueError(f"end marker not found: {end!r}")
    return text[a : b + len(end)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "corpus")
    ap.add_argument("--only", action="append", default=[])
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for row in read_sources():
        if args.only and row["id"] not in args.only:
            continue
        try:
            raw = fetch(row["url"])
            (args.out / f"{row['id']}.raw").write_bytes(raw)
            if row["kind"] == "wikisource-api":
                text = wikisource_text(raw)
            else:
                text = html_to_text(raw.decode("utf-8", errors="replace"))
            text = extract(text, row.get("start", ""), row.get("end", ""))
            (args.out / f"{row['id']}.txt").write_text(text, encoding="utf-8")
            print(f"{row['id']}: {len(text)} chars → {args.out / (row['id'] + '.txt')}")
        except Exception as e:  # noqa: BLE001 - report every source, keep going
            print(f"{row['id']}: FAILED {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
