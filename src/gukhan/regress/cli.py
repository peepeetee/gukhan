# SPDX-License-Identifier: Apache-2.0
"""``gukhan-regress``: prepare regression items from gold text, and score the converter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gukhan import rules
from gukhan.convert import Converter
from gukhan.lexicon import Lexicon
from gukhan.overrides import Overrides

from . import prepare as prep
from . import score as sc


def cmd_prepare(args: argparse.Namespace) -> int:
    chars = prep.load_chars(args.chars)
    words = prep.load_lexicon_hanja(args.lexicon) if args.lexicon else None
    text = args.text.read_text(encoding="utf-8")
    sentences = prep.split_sentences(text)
    flagged_total = 0
    unknown: set[str] = set()
    with args.out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# gukhan regression items from {args.source}\n# id\tsource\thangul\tmixed\n")
        for n, sent in enumerate(sentences, 1):
            if not any(prep.is_cjk(c) for c in sent):
                continue
            p = prep.prepare(sent, chars, words)
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
    try:
        use_rules = rules.parse_rules(args.rules)
    except ValueError as e:
        print(f"gukhan-regress: {e}", file=sys.stderr)
        return 2
    conv = Converter(lexicon, overrides, min_weight=args.min_weight, use_rules=use_rules)
    items = []
    for p in args.items:
        for it in sc.read_items(p):
            items.append(sc.Item(it.id, it.source, it.hangul, it.mixed.split(" # CHECK ")[0]))
    tally = sc.score(items, conv)
    result = {
        "items": len(items),
        "lexicon": str(args.lexicon or "sample"),
        "rules": ",".join(sorted(use_rules)) or "none",
        **tally.as_dict(),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"items={result['items']} words={result['words']} right={result['right']} ({result['right_pct']}%) "
            f"partial={result['partial']} flagged={result['flagged']} wrong={result['wrong']} "
            f"({result['wrong_pct']}%) over={result['over']} misaligned={result['misaligned_items']}"
        )
        print(f"in_candidates={result['in_candidates']} ({result['in_candidates_pct']}%): right or offered")
        print(
            f"chars={result['chars']} right={result['chars_right']} ({result['chars_right_pct']}%) "
            f"flagged={result['chars_flagged']} wrong={result['chars_wrong']} ({result['chars_wrong_pct']}%)"
        )
        for kind, ex in (
            ("wrong", tally.examples_wrong),
            ("over", tally.examples_over),
            ("partial", tally.examples_partial),
        ):
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
    p.add_argument("--lexicon", type=Path, help="lexicon.tsv: segments Hanja runs into known words first")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.set_defaults(func=cmd_prepare)
    s = sub.add_parser("score", help="run the converter on items and report")
    s.add_argument("items", type=Path, nargs="+")
    s.add_argument("--lexicon", type=Path)
    s.add_argument("--overrides", type=Path, action="append", default=[])
    s.add_argument("--json", action="store_true")
    s.add_argument(
        "--min-weight", type=int, default=None, help="passed to the converter (default 12 on a weighted lexicon)"
    )
    s.add_argument("--rules", default="default", help="default, all, none or rule names, as for `gukhan --rules`")
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
