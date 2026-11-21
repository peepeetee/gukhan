# SPDX-License-Identifier: Apache-2.0
"""Accuracy report for CI: score every regression set, compare two runs, gate on the held-out sets.

    python scripts/accuracy.py score LEXICON -o scores.json [--regression tests/regression]
    python scripts/accuracy.py compare base.json head.json [--max-wrong-increase 2] [--summary FILE]

``score`` loads the lexicon once and scores each ``*.tsv`` of the regression folder as its own set, with default
settings. ``compare`` prints a Markdown table of right / wrong / flagged for both runs with the change, and exits
with 1 when the number of wrong words in any held-out set (a file name containing ``heldout``) rose by more than
the threshold. The figures come from whatever lexicon is given (in CI: one built from the NIKL dumps alone), so
they are for comparing two versions of the code, not the published accuracy of the README.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HELD_OUT = "heldout"
FIELDS = ("words", "right", "wrong", "flagged", "partial", "over")


def score_sets(lexicon: Path, regression: Path) -> dict[str, object]:
    """Score each set of ``regression`` with the converter that is importable as ``gukhan``."""
    import gukhan
    from gukhan.convert import Converter
    from gukhan.lexicon import Lexicon
    from gukhan.regress import score as sc

    lex = Lexicon.load(lexicon)
    sets: dict[str, dict[str, int | float]] = {}
    for path in sorted(regression.glob("*.tsv")):
        if path.name in ("sources.tsv", "modern-law-laws.tsv"):
            continue
        items = [sc.Item(i.id, i.source, i.hangul, i.mixed.split(" # CHECK ")[0]) for i in sc.read_items(path)]
        if not items:
            continue
        tally = sc.score(items, Converter(lex))
        sets[path.stem] = {k: v for k, v in tally.as_dict().items() if k in FIELDS}
    return {"gukhan": str(Path(gukhan.__file__).resolve()), "lexicon_entries": len(lex), "sets": sets}


def _delta(base: int | None, head: int) -> str:
    if base is None:
        return f"{head} (new)"
    d = head - base
    return f"{head}" if d == 0 else f"{head} ({d:+d})"


def compare(base: dict[str, object], head: dict[str, object], max_wrong_increase: int) -> tuple[str, list[str]]:
    """The Markdown report and the held-out sets whose wrong count rose by more than the threshold."""
    base_sets = base["sets"]
    head_sets = head["sets"]
    assert isinstance(base_sets, dict) and isinstance(head_sets, dict)
    lines = [
        "| set | words | right | wrong | flagged | partial | over |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    failures: list[str] = []
    for name in sorted(head_sets):
        h = head_sets[name]
        b = base_sets.get(name)
        cells = [name + (" (held out)" if HELD_OUT in name else "")]
        for field in FIELDS:
            cells.append(_delta(None if b is None else int(b[field]), int(h[field])))
        lines.append("| " + " | ".join(cells) + " |")
        if HELD_OUT in name and b is not None and int(h["wrong"]) - int(b["wrong"]) > max_wrong_increase:
            failures.append(
                f"{name}: wrong {b['wrong']} → {h['wrong']} (more than {max_wrong_increase} up) / "
                f"誤變換이 {max_wrong_increase}개보다 많이 늘었습니다"
            )
    for name in sorted(set(base_sets) - set(head_sets)):
        lines.append(f"| {name} | removed | | | | | |")
    return "\n".join(lines), failures


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="정확도 보고 / accuracy report: score every regression set and compare two runs"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="모든 回歸 묶음 採點 / score every regression set")
    s.add_argument("lexicon", type=Path, help="lexicon.tsv 또는 그 directory / lexicon.tsv or its directory")
    s.add_argument("-o", "--out", type=Path, required=True, help="JSON 出力 / JSON output")
    s.add_argument("--regression", type=Path, default=Path("tests/regression"), help="回歸 folder / regression folder")
    c = sub.add_parser("compare", help="두 結果 比較 / compare two score files")
    c.add_argument("base", type=Path, help="기준(main)의 JSON / JSON of the base (main)")
    c.add_argument("head", type=Path, help="이 變更의 JSON / JSON of this change")
    c.add_argument(
        "--max-wrong-increase",
        type=int,
        default=2,
        help="held-out 묶음에서 허용하는 誤變換 增加 / wrong words a held-out set may gain (default 2)",
    )
    c.add_argument(
        "--summary", type=Path, help="Markdown을 덧붙일 file (GITHUB_STEP_SUMMARY) / file to append Markdown to"
    )
    args = ap.parse_args(argv)
    if args.cmd == "score":
        for path in (args.lexicon, args.regression):
            if not path.exists():
                print(f"accuracy.py: 찾을 수 없습니다 / not found: {path}", file=sys.stderr)
                return 2
        result = score_sets(args.lexicon, args.regression)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{args.out}: {len(result['sets'])} sets, {result['lexicon_entries']} lexicon entries")  # type: ignore[arg-type]
        return 0
    for path in (args.base, args.head):
        if not path.is_file():
            print(f"accuracy.py: 찾을 수 없습니다 / not found: {path}", file=sys.stderr)
            return 2
    base = json.loads(args.base.read_text(encoding="utf-8"))
    head = json.loads(args.head.read_text(encoding="utf-8"))
    table, failures = compare(base, head, args.max_wrong_increase)
    text = (
        "### Accuracy against main / main 대비 正確度\n\n"
        f"Lexicon: {head['lexicon_entries']} entries built from the NIKL dumps alone "
        f"(base: {base['lexicon_entries']}). "
        "Figures are for comparing two versions of the code, not the published accuracy. "
        "Words: right / wrong / flagged (left in Hangul) / partial; the change from main is in brackets. "
        "`over` is not meaningful for the modern-law sets (only annotated words are Hanja in their gold).\n\n"
        f"{table}\n"
    )
    if failures:
        text += (
            "\n**Held-out sets got worse / 保留 標本이 나빠졌습니다:**\n\n"
            + "\n".join(f"- {f}" for f in failures)
            + "\n"
        )
    print(text)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(text)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
