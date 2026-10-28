# SPDX-License-Identifier: Apache-2.0
"""``gukhan-lexicon-build``: build lexicon.tsv + manifest.json from the sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import stdict as stdict_mod
from . import unihan as unihan_mod
from . import wiktextract as wikt_mod
from .manifest import write_manifest

HEADER = "# gukhan lexicon\tlicence={licence}\tmanifest=manifest.json\n# hangul\thanja\tpos\tsource\tsense\tweight\n"


POS_PREFERENCE = {"명사": 0, "의존 명사": 1, "부사": 1, "어근": 1, "접두사": 1, "접미사": 1, "고유 명사": 3}


def merge_entries(entries: list[stdict_mod.Entry]) -> list[stdict_mod.Entry]:
    """One line per (hangul, hanja): prefer the entry with a gloss, then a common noun over a proper noun.

    The same pair often comes from a Hangul page and a Hanja page, or as 명사 and
    고유 명사; keeping both would make every flag list twice as long.
    """
    best: dict[tuple[str, str], stdict_mod.Entry] = {}
    weight: dict[tuple[str, str], int] = {}
    for e in entries:
        key = (e.hangul, e.hanja)
        weight[key] = max(weight.get(key, 0), e.weight)
        rank = (not e.sense, POS_PREFERENCE.get(e.pos, 2), e.source)
        cur = best.get(key)
        if cur is None or rank < (not cur.sense, POS_PREFERENCE.get(cur.pos, 2), cur.source):
            best[key] = e
    out = [stdict_mod.Entry(e.hangul, e.hanja, e.pos, e.source, e.sense, weight[k]) for k, e in best.items()]
    return sorted(out, key=lambda e: (e.hangul, e.hanja))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="gukhan-lexicon-build",
        description="辭典 構築 / build lexicon.tsv from 표준국어대사전 and/or Wiktionary (kaikki.org). No downloads.",
    )
    ap.add_argument(
        "--stdict",
        type=Path,
        help="표준국어대사전 XML dump: zip, directory or single file (needs a 국립국어원 account)",
    )
    ap.add_argument(
        "--wiktextract",
        type=Path,
        action="append",
        default=[],
        help="kaikki.org wiktextract JSONL (.jsonl or .jsonl.gz), e.g. kaikki.org-dictionary-Korean.jsonl; repeatable",
    )
    ap.add_argument("--unihan", type=Path, help="Unihan.zip or directory with Unihan_Readings.txt (validates readings)")
    ap.add_argument("-o", "--out", required=True, type=Path, help="output directory")
    args = ap.parse_args(argv)

    if not args.stdict and not args.wiktextract:
        print("辭典 source가 없습니다 / give --stdict and/or --wiktextract", file=sys.stderr)
        return 2
    for p in ([args.stdict] if args.stdict else []) + args.wiktextract:
        if not p.exists():
            print(f"入力 file을 찾을 수 없습니다 / input not found: {p}", file=sys.stderr)
            return 2
    readings: dict[str, list[str]] | None = None
    unihan_version = None
    if args.unihan:
        if not args.unihan.exists():
            print(f"Unihan 파일을 찾을 수 없습니다 / Unihan input not found: {args.unihan}", file=sys.stderr)
            return 2
        readings, unihan_version = unihan_mod.read_khangul(args.unihan)
        print(f"Unihan kHangul: {len(readings)} characters, version {unihan_version or 'unknown'}")

    entries, rejects = [], []
    counts: dict[str, int] = {}
    if args.stdict:
        e, r, stats = stdict_mod.parse(args.stdict, readings)
        print(f"stdict: items={stats.items} sino={stats.sino} entries={stats.entries} rejected={stats.rejected}")
        print("stdict tags seen in first items: " + ", ".join(sorted(stats.tags_seen)))
        if stats.items == 0 or "word" not in stats.tags_seen:
            print(
                "XML에서 <item>/<word>를 찾지 못했습니다. 덤프 形式을 確認하세요 / "
                "No <item>/<word> found; check the dump schema (see docs/PLAN.md §3).",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        counts["stdict_items"], counts["stdict_entries"] = stats.items, stats.entries
    for p in args.wiktextract:
        e, r, stats = wikt_mod.parse(p, readings)
        print(
            f"wiktextract {p.name}: lines={stats.items} pairs={stats.sino} "
            f"entries={stats.entries} rejected={stats.rejected}"
        )
        if stats.items == 0 or "word" not in stats.tags_seen:
            print(
                f"JSONL에서 word 項目을 찾지 못했습니다 / no wiktextract objects with 'word' found in {p}",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        counts["wiktextract_lines"] = counts.get("wiktextract_lines", 0) + stats.items
        counts["wiktextract_entries"] = counts.get("wiktextract_entries", 0) + stats.entries
    licence = "CC-BY-SA-2.0-KR" if not args.wiktextract else "CC-BY-SA-4.0"

    args.out.mkdir(parents=True, exist_ok=True)
    merged = merge_entries(entries)
    lex_path = args.out / "lexicon.tsv"
    with lex_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER.format(licence=licence))
        for e in merged:
            fh.write(e.tsv() + "\n")
    outputs = {"lexicon": lex_path}
    seen = merged

    rejects = sorted(
        {(r.hangul, r.raw_hanja, r.reason): r for r in rejects}.values(), key=lambda r: (r.hangul, r.source)
    )
    rej_path = args.out / "rejects.tsv"
    with rej_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# hangul\traw_hanja\tsource\treason\n")
        for r in rejects:
            fh.write(r.tsv() + "\n")
    outputs["rejects"] = rej_path

    if readings:
        chars_path = args.out / "chars.tsv"
        with chars_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("# hanja\treadings\n")
            for ch in sorted(readings):
                fh.write(f"{ch}\t{' '.join(readings[ch])}\n")
        outputs["chars"] = chars_path

    write_manifest(
        args.out,
        stdict=args.stdict,
        wiktextract=args.wiktextract,
        unihan=args.unihan,
        unihan_version=unihan_version,
        licence=licence,
        counts={**counts, "entries": len(seen), "rejected": len(rejects)},
        outputs=outputs,
    )
    print(f"wrote {args.out / 'lexicon.tsv'} ({len(seen)} entries) and manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
