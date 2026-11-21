# SPDX-License-Identifier: Apache-2.0
"""Build the old-statute regression set from the mixed-script passages in legalize-kr's history.

legalize-kr mirrors law.go.kr, whose pre-2000 statute texts are Hangul with the lawmaker's own
Hanja kept inside parentheses: ``(有料道路에 連結되는 通路를 포함한다)``, ``(第251條 및 第252條의 未遂犯을
제외한다)``. Each such passage is a short stretch of real 國漢文混用 written by the drafter. The
mixed form is the passage as published; the Hangul form is derived from it (``gukhan-regress
prepare`` rules, with readings from a lexicon), so the passage is gold for every Hanja word in it.

Statutes are outside copyright (저작권법 제7조 1호). The repository's own metadata is MIT.

    git clone --filter=blob:none https://github.com/legalize-kr/legalize-kr repo
    python scripts/collect_old_law_fragments.py --repo repo --lexicon build/lexicon \\
        --items tests/regression/old-law

Only the lines a commit added are read (``git log -p``), so each passage is taken once, with the
year of the first commit that carries it. Passages that need a Hanja reading the lexicon cannot give
unambiguously are dropped, never guessed. Items are split into ``-tuning`` and ``-heldout`` halves
by a hash of the passage's longest Hanja word, so one word is never in both halves.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HAN = re.compile(r"[一-鿿]")
HAN_RUN = re.compile(r"[一-鿿]+")
HANGUL = re.compile(r"[가-힣]")
PAREN = re.compile(r"\(([^()]{4,120})\)")
MIN_HANJA = 3
MAX_YEAR = 1999


def half(word: str) -> str:
    digest = hashlib.sha256(word.encode()).digest()
    return "heldout" if digest[0] % 2 else "tuning"


def added_lines(repo: Path, until_year: int):
    """Yield (year, added line) for every added line holding Hanja, newest commit first."""
    proc = subprocess.Popen(
        [
            "git",
            "log",
            "-p",
            "--no-renames",
            "--format=@@C %ad",
            "--date=format:%Y",
            f"--until={until_year}-12-31",
        ],
        stdout=subprocess.PIPE,
        text=True,
        errors="replace",
        cwd=repo,
    )
    year = 0
    assert proc.stdout is not None
    for line in proc.stdout:
        if line.startswith("@@C "):
            year = int(line[4:].strip())
        elif line.startswith("+") and not line.startswith("+++") and HAN.search(line):
            yield year, line[1:].rstrip()
    proc.wait()


def passages(text: str) -> list[str]:
    out = []
    for m in PAREN.finditer(text):
        s = m.group(1).strip()
        if len(HAN.findall(s)) >= MIN_HANJA and HANGUL.search(s):
            out.append(s)
    return out


def collect(repo: Path) -> dict[str, int]:
    """``{passage: earliest year}``."""
    found: dict[str, int] = {}
    for year, line in added_lines(repo, MAX_YEAR):
        for s in passages(line):
            if s not in found or year < found[s]:
                found[s] = year
    return found


def lexicon_chars(lexicon: Path):
    """Per-character readings seen in the lexicon's aligned Hanja words (same length as the Hangul)."""
    from gukhan.lexicon import Lexicon
    from gukhan.regress import prepare as prep

    lex = Lexicon.load(lexicon)
    seen: dict[str, Counter] = defaultdict(Counter)
    for entries in lex._by_key.values():
        for e in entries:
            hj, hg = e.hanja.replace(" ", ""), e.hangul.replace(" ", "")
            if len(hj) == len(hg) and all(HAN.match(c) for c in hj):
                for i, (c, r) in enumerate(zip(hj, hg, strict=True)):
                    if i:  # word-initial syllables may be rewritten by the 頭音法則
                        seen[c][r] += 1
    unique = {c: [r for r, _ in n.most_common()] for c, n in seen.items() if len(n) == 1}
    return prep.Chars.from_dict(unique), prep.load_lexicon_hanja(lexicon)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", type=Path, required=True, help="local clone of legalize-kr (full history)")
    ap.add_argument("--lexicon", type=Path, required=True, help="lexicon directory or lexicon.tsv for readings")
    ap.add_argument("--items", type=Path, required=True, help="writes <prefix>-tuning.tsv and <prefix>-heldout.tsv")
    args = ap.parse_args(argv)
    from gukhan.regress import prepare as prep

    lex_path = args.lexicon / "lexicon.tsv" if args.lexicon.is_dir() else args.lexicon
    chars, words = lexicon_chars(lex_path)
    found = collect(args.repo)
    rows: dict[str, list[tuple[int, str, str]]] = {"tuning": [], "heldout": []}
    dropped = 0
    for s, year in sorted(found.items(), key=lambda kv: (kv[1], kv[0])):
        p = prep.prepare(s, chars, words)
        if p.flags or p.unknown:
            dropped += 1
            continue
        longest = max(HAN_RUN.findall(s), key=len)
        rows[half(longest)].append((year, p.hangul, s))
    for name, items in rows.items():
        path = Path(f"{args.items}-{name}.tsv")
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"# gukhan {name} items: mixed-script passages of 1970-1999 statutes (legalize-kr history)\n")
            fh.write("# built by scripts/collect_old_law_fragments.py; see tests/regression/README.md\n")
            fh.write("# id\tsource\thangul\tmixed\n")
            for n, (_year, hangul, mixed) in enumerate(items, 1):
                fh.write(f"old-law-{name}-{n:04d}\told-law-{name}\t{hangul}\t{mixed}\n")
        print(f"{path}: {len(items)} items", file=sys.stderr)
    print(f"{dropped} passages dropped (reading not settled by the lexicon)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
