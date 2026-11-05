# SPDX-License-Identifier: Apache-2.0
"""How many of the Hanja that gukhan can write does a font draw?

    pip install fonttools          # MIT, needed only for this script
    python scripts/check_font_coverage.py NotoSerifKR-Regular.otf --lexicon build/lexicon
    python scripts/check_font_coverage.py a.otf b.ttf --lexicon build/lexicon --list-missing 30

Reads every Hanja character that occurs in the Hanja column of ``lexicon.tsv`` (the characters gukhan
can output) and reports, per font file, how many the font maps to a glyph. It looks only at the font's
character map: it cannot tell whether the glyph is the Korean form (see docs/fonts.md) or whether
the browser would fall back to another font for a missing character.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path


def lexicon_hanja(path: Path) -> collections.Counter:
    """Count Hanja characters in the hanja column (the second) of a lexicon.tsv or its directory."""
    if path.is_dir():
        path = path / "lexicon.tsv"
    counts: collections.Counter = collections.Counter()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            for ch in cols[1]:
                if ch != " " and not ("가" <= ch <= "힣") and ord(ch) >= 0x2E80:
                    counts[ch] += 1
    return counts


def font_cmap(path: Path) -> set[int]:
    from fontTools.ttLib import TTCollection, TTFont

    if path.suffix.lower() in (".ttc", ".otc"):
        cmap: set[int] = set()
        for f in TTCollection(str(path)).fonts:
            cmap |= set(f.getBestCmap())
        return cmap
    return set(TTFont(str(path), lazy=True).getBestCmap())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="+", type=Path)
    ap.add_argument("--lexicon", type=Path, required=True, help="lexicon.tsv or its directory")
    ap.add_argument("--list-missing", type=int, default=0, metavar="N", help="show the N commonest missing characters")
    args = ap.parse_args(argv)
    try:
        import fontTools  # noqa: F401
    except ImportError:
        print("fontTools is required: pip install fonttools", file=sys.stderr)
        return 2
    counts = lexicon_hanja(args.lexicon)
    total_chars = len(counts)
    total_uses = sum(counts.values())
    print(f"{args.lexicon}: {total_chars} distinct Hanja, {total_uses} occurrences")
    for font in args.fonts:
        cmap = font_cmap(font)
        have = {c for c in counts if ord(c) in cmap}
        uses = sum(counts[c] for c in have)
        print(
            f"{font.name}: {len(have)}/{total_chars} characters ({100 * len(have) / total_chars:.1f}%), "
            f"{100 * uses / total_uses:.2f}% of occurrences"
        )
        if args.list_missing:
            missing = [(c, n) for c, n in counts.most_common() if c not in have][: args.list_missing]
            print("  missing: " + " ".join(f"{c}({n})" for c, n in missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
