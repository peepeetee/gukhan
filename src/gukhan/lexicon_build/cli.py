# SPDX-License-Identifier: Apache-2.0
"""``gukhan-lexicon-build``: build lexicon.tsv + manifest.json from the sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import stdict as stdict_mod
from . import unihan as unihan_mod
from .manifest import write_manifest

HEADER = "# gukhan lexicon\tlicence=CC-BY-SA-2.0-KR\tmanifest=manifest.json\n# hangul\thanja\tpos\tsource\tsense\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="gukhan-lexicon-build",
        description="표준국어대사전 dump → lexicon.tsv (辭典 構築). Nothing is downloaded.",
    )
    ap.add_argument("--stdict", required=True, type=Path, help="XML dump: zip, directory or single file")
    ap.add_argument("--unihan", type=Path, help="Unihan.zip or directory with Unihan_Readings.txt (validates readings)")
    ap.add_argument("-o", "--out", required=True, type=Path, help="output directory")
    args = ap.parse_args(argv)

    if not args.stdict.exists():
        print(f"표준국어대사전 파일을 찾을 수 없습니다 / stdict input not found: {args.stdict}", file=sys.stderr)
        return 2
    readings: dict[str, list[str]] | None = None
    unihan_version = None
    if args.unihan:
        if not args.unihan.exists():
            print(f"Unihan 파일을 찾을 수 없습니다 / Unihan input not found: {args.unihan}", file=sys.stderr)
            return 2
        readings, unihan_version = unihan_mod.read_khangul(args.unihan)
        print(f"Unihan kHangul: {len(readings)} characters, version {unihan_version or 'unknown'}")

    entries, rejects, stats = stdict_mod.parse(args.stdict, readings)
    print(f"items={stats.items} sino={stats.sino} entries={stats.entries} rejected={stats.rejected}")
    print("tags seen in first items: " + ", ".join(sorted(stats.tags_seen)))
    if stats.items == 0 or "word" not in stats.tags_seen:
        print(
            "XML에서 <item>/<word>를 찾지 못했습니다. 덤프 형식을 확인하세요 / "
            "No <item>/<word> found; check the dump schema (see docs/PLAN.md §3).",
            file=sys.stderr,
        )
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    entries.sort(key=lambda e: (e.hangul, e.hanja, e.pos, e.source))
    seen = set()
    lex_path = args.out / "lexicon.tsv"
    with lex_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER)
        for e in entries:
            key = (e.hangul, e.hanja, e.pos)
            if key in seen:
                continue
            seen.add(key)
            fh.write(e.tsv() + "\n")
    outputs = {"lexicon": lex_path}

    rej_path = args.out / "rejects.tsv"
    with rej_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# hangul\traw_hanja\tsource\treason\n")
        for r in sorted(rejects, key=lambda r: (r.hangul, r.source)):
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
        unihan=args.unihan,
        unihan_version=unihan_version,
        counts={"items": stats.items, "sino": stats.sino, "entries": len(seen), "rejected": stats.rejected},
        outputs=outputs,
    )
    print(f"wrote {args.out / 'lexicon.tsv'} ({len(seen)} entries) and manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
