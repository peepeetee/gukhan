# SPDX-License-Identifier: Apache-2.0
"""Throughput of the converter on a text of about 1 MB (UTF-8), for CI and for a laptop.

    python scripts/benchmark.py                       # 1 MB, a synthetic 200k-entry lexicon
    python scripts/benchmark.py --lexicon build/lexicon --size-mb 1 --json

The text is made from fixed Korean sentences, repeated with a changing number so no two lines
are equal; the same text is produced on every run. Without ``--lexicon`` a lexicon of
``--synthetic-entries`` made-up headwords is added to the sample one, so dictionary lookup works
on a table of realistic size (the real lexicon has about 700k entries). The figures are for
trend-watching, not a promise: the first call loads the Kiwi model, reported separately.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
import time
from pathlib import Path

SENTENCES = (
    "국군은 작전 계획을 수립하였다.",
    "대한민국의 주권은 국민에게 있고 모든 권력은 국민으로부터 나온다.",
    "전기 공학을 연구하는 학자가 새로운 이론을 발표했다.",
    "이 법은 국민의 권리와 의무를 정함을 목적으로 한다.",
    "그는 어제 도서관에서 오래된 지도를 찾아 한참을 들여다보았다.",
    "정부는 내년도 예산안을 국회에 제출하고 심의를 요청하였다.",
    "법원은 피고인에게 징역 이 년을 선고하고 집행을 유예하였다.",
    "봄이 오면 강가의 버드나무에 연한 새잎이 돋아난다.",
)


def make_text(size_bytes: int, seed: int = 1) -> str:
    rng = random.Random(seed)
    lines: list[str] = []
    size = 0
    n = 0
    while size < size_bytes:
        n += 1
        line = f"{n}. " + " ".join(rng.choice(SENTENCES) for _ in range(rng.randint(1, 4)))
        lines.append(line)
        size += len(line.encode("utf-8")) + 1
    return "\n".join(lines) + "\n"


def synthetic_lexicon(entries: int, seed: int = 1):
    from gukhan.lexicon import Entry, Lexicon

    rng = random.Random(seed)
    lex = Lexicon.sample()
    syllables = [chr(c) for c in range(0xAC00, 0xAC00 + 2000)]
    hanja = [chr(c) for c in range(0x4E00, 0x4E00 + 2000)]
    for _ in range(entries):
        n = rng.choice((2, 2, 2, 3, 3, 4))
        picks = [rng.randrange(2000) for _ in range(n)]
        lex.add(Entry("".join(syllables[i] for i in picks), "".join(hanja[i] for i in picks), "명사", "synthetic"))
    return lex


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size-mb", type=float, default=1.0, help="text size in MB (UTF-8)")
    ap.add_argument("--lexicon", type=Path, help="lexicon.tsv or directory; default: sample plus synthetic entries")
    ap.add_argument("--synthetic-entries", type=int, default=200_000)
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    args = ap.parse_args(argv)

    from gukhan.convert import Converter
    from gukhan.lexicon import Lexicon

    t = time.perf_counter()
    if args.lexicon:
        lex = Lexicon.load(args.lexicon / "lexicon.tsv" if args.lexicon.is_dir() else args.lexicon)
        lexicon_name = str(args.lexicon)
    else:
        lex = synthetic_lexicon(args.synthetic_entries)
        lexicon_name = f"synthetic {args.synthetic_entries}"
    load_s = time.perf_counter() - t

    conv = Converter(lex)
    t = time.perf_counter()
    conv.convert("국군은 작전 계획을 수립하였다.")  # loads the Kiwi model
    model_s = time.perf_counter() - t

    text = make_text(int(args.size_mb * 1_000_000))
    t = time.perf_counter()
    result = conv.convert(text)
    convert_s = time.perf_counter() - t
    nbytes = len(text.encode("utf-8"))
    out = {
        "size_bytes": nbytes,
        "chars": len(text),
        "lexicon": lexicon_name,
        "lexicon_entries": len(lex),
        "lexicon_load_s": round(load_s, 2),
        "model_load_s": round(model_s, 2),
        "convert_s": round(convert_s, 2),
        "mb_per_s": round(nbytes / 1e6 / convert_s, 3),
        "chars_per_s": round(len(text) / convert_s),
        "decisions": len(result.decisions),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(
            f"{nbytes / 1e6:.2f} MB ({out['chars']} chars) in {convert_s:.1f} s = {out['mb_per_s']} MB/s "
            f"({out['chars_per_s']} chars/s); {out['decisions']} decisions; lexicon {lexicon_name} "
            f"({out['lexicon_entries']} entries, load {load_s:.1f} s), model load {model_s:.1f} s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
