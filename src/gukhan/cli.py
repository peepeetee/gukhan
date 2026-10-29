# SPDX-License-Identifier: Apache-2.0
"""``gukhan``: convert a Hangul text file to 國漢文混用體."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, report, rules
from .convert import Converter
from .lexicon import Lexicon
from .overrides import Overrides


def _err(msg: str) -> int:
    print(f"gukhan: {msg}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gukhan",
        description="한글 文章을 國漢文混用體로 變換합니다 / Convert Hangul text to Hangul-Hanja mixed script.",
    )
    ap.add_argument("input", nargs="?", type=Path, help="input file (Markdown or plain text); omit with --stdin")
    ap.add_argument("--stdin", action="store_true", help="read text from standard input / 標準 入力에서 읽기")
    ap.add_argument("-o", "--output", type=Path, help="write converted text here instead of stdout")
    ap.add_argument("--lexicon", type=Path, help="lexicon.tsv or its directory (default: bundled sample)")
    ap.add_argument("--overrides", type=Path, action="append", default=[], help="override file; repeatable, later wins")
    ap.add_argument("--report", type=Path, help="write flagged words and review list (.tsv or .md by extension)")
    ap.add_argument("--mark", action="store_true", help="show flagged words inline as 전기{電氣|傳記}")
    ap.add_argument("--review-all", action="store_true", help="also list every common noun with no entry")
    ap.add_argument(
        "--min-weight",
        type=int,
        default=None,
        help="flag a lone candidate whose weight is below this (default 12 on a weighted lexicon, 0 otherwise)",
    )
    ap.add_argument(
        "--rules",
        default="default",
        help="evidence rules that narrow a flag's candidates: default, all, none, or names "
        f"({', '.join(sorted(rules.ALL))}), comma separated; see docs/PLAN.md §5",
    )
    ap.add_argument("--version", action="version", version=f"gukhan {__version__}")
    return ap


def review_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="gukhan review",
        description="flag된 낱말의 漢字를 文脈 속에서 직접 고릅니다 / Pick the Hanja for flagged words in context. "
        "Answers are appended to the override file; nothing is guessed.",
    )
    ap.add_argument("input", type=Path, help="the same file you convert")
    ap.add_argument(
        "--overrides", type=Path, required=True, help="override file to read and append to (created if absent)"
    )
    ap.add_argument("--lexicon", type=Path, help="lexicon.tsv or its directory (default: bundled sample)")
    ap.add_argument("--rules", default="default", help="same as for conversion")
    ap.add_argument("--include-review", action="store_true", help="also ask about words with no entry (type the Hanja)")
    args = ap.parse_args(argv)
    from .review import Reviewer

    if not args.input.is_file():
        return _err(f"file을 찾을 수 없습니다 / file not found: {args.input}")
    text = args.input.read_text(encoding="utf-8")
    try:
        lexicon = Lexicon.load(args.lexicon) if args.lexicon else Lexicon.sample()
        overrides = Overrides.load(args.overrides) if args.overrides.exists() else Overrides()
        use_rules = rules.parse_rules(args.rules)
    except (OSError, ValueError) as e:
        return _err(str(e))
    conv = Converter(lexicon, overrides, use_rules=use_rules)
    return Reviewer(conv, text, args.overrides, include_review=args.include_review).run()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "review":
        return review_main(argv[1:])
    args = build_parser().parse_args(argv)
    if args.stdin == (args.input is not None):
        return _err("入力 file 하나 또는 --stdin 을 指定하세요 / give one input file or --stdin")
    if args.stdin:
        text = sys.stdin.read()
    else:
        if not args.input.is_file():
            return _err(f"file을 찾을 수 없습니다 / file not found: {args.input}")
        text = args.input.read_text(encoding="utf-8")

    try:
        lexicon = Lexicon.load(args.lexicon) if args.lexicon else Lexicon.sample()
    except (OSError, ValueError) as e:
        return _err(f"辭典을 읽을 수 없습니다 / cannot read lexicon: {e}")
    overrides = Overrides()
    for p in args.overrides:
        try:
            overrides.update(Overrides.load(p))
        except (OSError, ValueError) as e:
            return _err(f"override file 誤謬 / override file error ({p}): {e}")

    if not args.lexicon:
        print(
            "注意: 內藏 sample 辭典을 使用합니다. 實際 變換에는 --lexicon 을 指定하세요 / "
            "Note: using the bundled sample lexicon; pass --lexicon for real use.",
            file=sys.stderr,
        )
    try:
        use_rules = rules.parse_rules(args.rules)
    except ValueError as e:
        return _err(str(e))
    conv = Converter(
        lexicon,
        overrides if args.overrides else None,
        review_all=args.review_all,
        min_weight=args.min_weight,
        use_rules=use_rules,
    )
    result = conv.convert(text, mark=args.mark)

    if args.output:
        args.output.write_text(result.text, encoding="utf-8")
    else:
        sys.stdout.write(result.text)

    if args.report:
        body = report.to_markdown(text, result) if args.report.suffix.lower() == ".md" else report.to_tsv(text, result)
        args.report.write_text(body, encoding="utf-8")
    s = report.summary(result)
    print(
        f"變換 {s['converted']} · flag {s['flagged']} · 檢討 {s['review']} · 維持 {s['kept']}"
        + (f" → {args.report}" if args.report else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
