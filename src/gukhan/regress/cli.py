# SPDX-License-Identifier: Apache-2.0
"""``gukhan-regress``: prepare regression items from gold text, and score the converter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gukhan.convert import Converter
from gukhan.lexicon import Lexicon
from gukhan.overrides import Overrides

from . import prepare as prep
from . import score as sc


def cmd_prepare(args: argparse.Namespace) -> int:
    chars = prep.load_chars(args.chars)
    text = args.text.read_text(encoding="utf-8")
    sentences = prep.split_sentences(text)
    flagged_total = 0
    unknown: set[str] = set()
    with args.out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# gukhan regression items from {args.source}\n# id\tsource\thangul\tmixed\n")
        for n, sent in enumerate(sentences, 1):
            if not any(prep.is_cjk(c) for c in sent):
                continue
            p = prep.prepare(sent, chars)
            unknown.update(p.unknown)
            flagged_total += len(p.flags)
            note = ""
            if p.flags:
                note = " # CHECK " + " ".join(f"{f.char}→{f.chosen}({'/'.join(f.readings)})" for f in p.flags)
            fh.write(f"{args.source}-{n:04d}\t{args.source}\t{p.hangul}\t{sent}{note}\n")
    print(f"{args.out}: {len(sentences)} sentences, {flagged_total} guessed readings marked CHECK")
    if unknown:
        print(f"characters without a reading in chars.tsv (left as is): {''.join(sorted(unknown))}", file=sys.stderr)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    lexicon = Lexicon.load(args.lexicon) if args.lexicon else Lexicon.sample()
    overrides = None
    if args.overrides:
        overrides = Overrides()
        for p in args.overrides:
            overrides.update(Overrides.load(p))
    conv = Converter(lexicon, overrides)
    items = []
    for p in args.items:
        for it in sc.read_items(p):
            items.append(sc.Item(it.id, it.source, it.hangul, it.mixed.split(" # CHECK ")[0]))
    tally = sc.score(items, conv)
    result = {"items": len(items), "lexicon": str(args.lexicon or "sample"), **tally.as_dict()}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"items={result['items']} words={result['words']} right={result['right']} ({result['right_pct']}%) "
            f"flagged={result['flagged']} wrong={result['wrong']} ({result['wrong_pct']}%) over={result['over']} "
            f"misaligned={result['misaligned_items']}"
        )
        for kind, ex in (("wrong", tally.examples_wrong), ("over", tally.examples_over)):
            for item_id, gold, got in ex:
                print(f"  {kind}\t{item_id}\t{gold}\t→\t{got}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gukhan-regress", description="回歸 test set 道具 / regression set tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="gold mixed-script text → items TSV with derived Hangul")
    p.add_argument("text", type=Path, help="UTF-8 text file in 國漢文混用")
    p.add_argument("--chars", type=Path, required=True, help="chars.tsv from gukhan-lexicon-build --unihan")
    p.add_argument("--source", required=True, help="short source id, e.g. constitution-1948")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.set_defaults(func=cmd_prepare)
    s = sub.add_parser("score", help="run the converter on items and report")
    s.add_argument("items", type=Path, nargs="+")
    s.add_argument("--lexicon", type=Path)
    s.add_argument("--overrides", type=Path, action="append", default=[])
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_score)
    args = ap.parse_args(argv)
    for attr in ("text", "chars"):
        pth = getattr(args, attr, None)
        if pth is not None and not pth.exists():
            print(f"gukhan-regress: file을 찾을 수 없습니다 / file not found: {pth}", file=sys.stderr)
            return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
