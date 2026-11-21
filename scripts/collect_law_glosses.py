# SPDX-License-Identifier: Apache-2.0
"""Build the modern-law gloss regression set from current Korean statutes.

Current statutes are written in Hangul, but the 2000s-2020s plain-language rewrites put the
Hanja after the first use of a legal term: ``분사무소(分事務所)``, ``의사(意思)``, ``자(子)``.
Those annotations are the lawmaker's own Hanja for that word in that sentence, so each one is
gold for a homograph decision. Statutes are outside copyright (저작권법 제7조 1호).

Each annotated sentence becomes one item: the Hangul form drops the parentheses; the mixed form
writes only the annotated words in Hanja (the lawmaker's choice) and leaves everything else as
published. Words that are not annotated stay Hangul in the gold text, so ``over`` in
``gukhan-regress score`` counts every other word the converter writes in Hanja and means nothing
for this set; read right / flagged / wrong.

    python scripts/collect_law_glosses.py --out build/laws          # fetch (needs network), cache
    python scripts/collect_law_glosses.py --from build/laws --items tests/regression/modern-law

Source: the legalize-kr/legalize-kr repository, which mirrors law.go.kr (the state's 국가법령정보센터)
as one Markdown file per statute (its own metadata and structure are MIT; the statute text is a
public work).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/legalize-kr/legalize-kr/main/kr/{name}/{kind}.md"
UA = "gukhan-corpus-fetch/0.1 (+https://github.com/peepeetee/gukhan)"
LAWS = (
    "민법 형법 상법 민사소송법 형사소송법 국적법 가족관계의등록등에관한법률 부동산등기법 국세기본법 도로교통법 "
    "건축법 국가공무원법 지방자치법 공직선거법 정당법 군형법 군사법원법 병역법 경찰관직무집행법 공증인법 변호사법 "
    "법원조직법 국회법 정부조직법 소득세법 법인세법 부가가치세법 저작권법 특허법 상표법 약사법 의료법 식품위생법 "
    "주택임대차보호법 상가건물임대차보호법 어음법 수표법 채무자회생및파산에관한법률 소년법 감사원법"
).split()
GLOSS = re.compile(r"([가-힣]+)\(([\u4e00-\u9fff]+)\)")
HAN = re.compile(r"[\u4e00-\u9fff]")
# Glosses whose Hanja does not belong to the Hangul word before it (checked by hand against the
# syllable readings): 상뇌증(狂牛病) glosses a longer name; 한약사(韓藥事) is not 韓藥師.
EXCLUDE = {("뇌증", "狂牛病"), ("상뇌증", "狂牛病"), ("한약사", "韓藥事")}
PER_PAIR = 2  # sentences kept per distinct (word, Hanja): 자(子) alone occurs dozens of times
MAX_CHARS = 240


def half(pair: tuple[str, str]) -> str:
    """``tuning`` or ``heldout``, fixed by the pair alone, so no word is in both halves and the split never moves."""
    digest = hashlib.sha256(f"{pair[0]}\t{pair[1]}".encode()).digest()
    return "heldout" if digest[0] % 2 else "tuning"


def fetch(name: str, kind: str = "법률") -> str:
    url = RAW.format(name=urllib.parse.quote(name), kind=urllib.parse.quote(kind))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out: dict[str, str] = {}
    for line in m.group(1).splitlines() if m else []:
        k, _, v = line.partition(":")
        if v.strip() and not line.startswith(" "):
            out[k.strip()] = v.strip().strip('"')
    return out


def clean(line: str) -> str:
    line = unicodedata.normalize("NFC", line)  # folds Korean compatibility ideographs (U+F98B 曆) to the unified form
    line = re.sub(r"^\s*#+\s*", "", line)
    line = re.sub(r"\\([.\-()\[\]*])", r"\1", line)
    line = line.replace("**", "").replace("\u3000", " ")
    return re.sub(r"\s+", " ", line).strip()


def sentences(line: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", line) if s.strip()]


def to_item(sentence: str) -> tuple[str, str, list[tuple[str, str]]] | None:
    """``(hangul, mixed, [(word, hanja)])`` for one annotated sentence, or None when it is not usable.

    Usable: every Hanja in it belongs to a ``word(漢字)`` gloss whose Hangul word is at least as long
    as the Hanja (the last syllables of a longer run are the glossed word) and nothing is left over.
    """
    hangul, mixed, pairs, pos = [], [], [], 0
    for m in GLOSS.finditer(sentence):
        word, han = m.groups()
        if len(word) < len(han):
            return None
        head = sentence[pos : m.start(1)] + word[: len(word) - len(han)]
        gloss_word = word[len(word) - len(han) :]
        if (gloss_word, han) in EXCLUDE or (word, han) in EXCLUDE:
            return None
        hangul.append(head + gloss_word)
        mixed.append(head + han)
        pairs.append((gloss_word, han))
        pos = m.end()
    if not pairs:
        return None
    rest = sentence[pos:]
    hangul.append(rest)
    mixed.append(rest)
    h, x = "".join(hangul), "".join(mixed)
    # nothing may be left over: no Hanja in the Hangul form, and in the mixed form only the glossed words
    if HAN.search(h) or len(HAN.findall(x)) != sum(len(p[1]) for p in pairs) or len(h) != len(x):
        return None
    return h, x, pairs


def extract(text: str, seen: dict[tuple[str, str], int] | None = None) -> list[tuple[str, str, list[tuple[str, str]]]]:
    seen = {} if seen is None else seen
    out = []
    for raw in text.split("\n"):
        line = clean(raw)
        if not line or not GLOSS.search(line):
            continue
        for s in sentences(line):
            item = to_item(s)
            if item is None or len(item[0]) > MAX_CHARS:
                continue
            new = [p for p in item[2] if seen.get(p, 0) < PER_PAIR]
            if not new:
                continue
            for p in item[2]:
                seen[p] = seen.get(p, 0) + 1
            out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, help="fetch the statutes into this folder")
    ap.add_argument("--from", dest="src", type=Path, help="read cached statutes from this folder")
    ap.add_argument("--items", type=Path, help="items file prefix: writes <prefix>-tuning.tsv, -heldout.tsv, -laws.tsv")
    args = ap.parse_args(argv)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for name in LAWS:
            try:
                (args.out / f"{name}.md").write_text(fetch(name), encoding="utf-8")
            except OSError as e:
                print(f"{name}: {e}", file=sys.stderr)
    if args.src and args.items:
        seen: dict[tuple[str, str], int] = {}
        rows: dict[str, list[tuple[str, str]]] = {"tuning": [], "heldout": []}
        laws, dropped = [], 0
        for name in LAWS:
            path = args.src / f"{name}.md"
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            meta = frontmatter(text)
            count = {"tuning": 0, "heldout": 0}
            for h, x, pairs in extract(text, seen):
                halves = {half(p) for p in pairs}
                if len(halves) != 1:
                    dropped += 1  # its words fall in both halves: keep neither
                    continue
                (which,) = halves
                rows[which].append((h, x))
                count[which] += 1
            laws.append(
                (name, meta.get("공포일자", ""), meta.get("시행일자", ""), meta.get("법령MST", ""), *count.values())
            )
        for which, items in rows.items():
            path = args.items.with_name(f"{args.items.name}-{which}.tsv")
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(f"# gukhan {which} items from modern statutes: the lawmakers' own Hanja glosses\n")
                fh.write("# built by scripts/collect_law_glosses.py; see tests/regression/README.md for the split\n")
                fh.write("# id\tsource\thangul\tmixed\n")
                for n, (h, x) in enumerate(items, 1):
                    fh.write(f"modern-law-{which}-{n:04d}\tmodern-law-{which}\t{h}\t{x}\n")
        laws_path = args.items.with_name(args.items.name + "-laws.tsv")
        with laws_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("# law\t공포일자\t시행일자\t법령MST\ttuning\theldout\n")
            for law in laws:
                fh.write("\t".join(map(str, law)) + "\n")
        print(f"{len(rows['tuning'])} tuning, {len(rows['heldout'])} held-out items, {dropped} straddling dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
