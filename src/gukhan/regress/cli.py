# SPDX-License-Identifier: Apache-2.0
"""``gukhan-regress``: prepare regression items from gold text, and score the converter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gukhan import rules
from gukhan.cli import _utf8_streams
from gukhan.convert import Converter
from gukhan.lexicon import Lexicon
from gukhan.overrides import Overrides

from . import prepare as prep
from . import score as sc


def cmd_prepare(args: argparse.Namespace) -> int:
    chars = prep.load_chars(args.chars)
    words = prep.load_lexicon_hanja(args.lexicon) if args.lexicon else None
    text = args.text.read_text(encoding="utf-8-sig")
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
        print(
            f"chars.tsv에 讀音이 없는 漢字 (그대로 둠) / characters without a reading in chars.tsv (left as is): "
            f"{''.join(sorted(unknown))}",
            file=sys.stderr,
        )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    for pth in [*args.items, *([args.lexicon] if args.lexicon else []), *args.overrides]:
        if not pth.exists():
            print(f"gukhan-regress: file을 찾을 수 없습니다 / file not found: {pth}", file=sys.stderr)
            return 2
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
    p = sub.add_parser(
        "prepare",
        help="金標準 國漢文混用 글 → 한글을 뽑은 項目 TSV / gold mixed-script text → items TSV with derived Hangul",
    )
    p.add_argument("text", type=Path, help="國漢文混用으로 쓴 UTF-8 글 file / UTF-8 text file in mixed script")
    p.add_argument(
        "--chars",
        type=Path,
        required=True,
        help="gukhan-lexicon-build --unihan이 만든 chars.tsv / chars.tsv from gukhan-lexicon-build --unihan",
    )
    p.add_argument("--source", required=True, help="짧은 出處 이름 / short source id, e.g. constitution-1948")
    p.add_argument(
        "--lexicon",
        type=Path,
        help="lexicon.tsv: 漢字 連續을 아는 낱말로 먼저 나눔 / lexicon.tsv: segments Hanja runs into known words first",
    )
    p.add_argument("-o", "--out", type=Path, required=True, help="出力 file / output file")
    p.set_defaults(func=cmd_prepare)
    s = sub.add_parser("score", help="項目에 變換器를 돌려 報告 / run the converter on items and report")
    s.add_argument("items", type=Path, nargs="+", help="項目 TSV / items TSV file(s)")
    s.add_argument("--lexicon", type=Path, help="lexicon.tsv 또는 그 directory / lexicon.tsv or its directory")
    s.add_argument(
        "--overrides",
        type=Path,
        action="append",
        default=[],
        help="사용자 지정 file, 여러 번 가능 / override file; repeatable",
    )
    s.add_argument("--json", action="store_true", help="JSON으로 출력 / print JSON")
    s.add_argument(
        "--min-weight",
        type=int,
        default=None,
        help="變換器에 넘김 (加重 辭典 기본 12) / passed to the converter (default 12 on a weighted lexicon)",
    )
    s.add_argument(
        "--rules",
        default="default",
        help="`gukhan --rules`와 같음: default, all, none 또는 規則 이름 / "
        "default, all, none or rule names, as for `gukhan --rules`",
    )
    s.set_defaults(func=cmd_score)
    args = ap.parse_args(argv)
    _utf8_streams()
    for attr in ("text", "chars"):
        pth = getattr(args, attr, None)
        if pth is not None and not pth.exists():
            print(f"gukhan-regress: file을 찾을 수 없습니다 / file not found: {pth}", file=sys.stderr)
            return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
