# SPDX-License-Identifier: Apache-2.0
"""``gukhan-lexicon-build``: build lexicon.tsv + manifest.json from the sources."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from .. import console
from . import kowiki as kowiki_mod
from . import lawgloss as law_mod
from . import opendict as opendict_mod
from . import stdict as stdict_mod
from . import unihan as unihan_mod
from . import wikidata_lexemes as wikidata_mod
from . import wiktextract as wikt_mod
from .manifest import write_manifest
from .ranking import krdict_levels, learner_ranks

HEADER = (
    "# gukhan lexicon\tlicence={licence}\tmanifest=manifest.json\n"
    "# hangul\thanja\tpos\tsource\tsense\tweight\tlevel\tlearner_rank\tdomain\n"
)


POS_PREFERENCE = {"명사": 0, "의존 명사": 1, "부사": 1, "어근": 1, "접두사": 1, "접미사": 1, "고유 명사": 3}
# Which source's line represents a (hangul, hanja) pair when several have it. 우리말샘 is
# contributor-edited, so its line is used only when no edited source has the pair.
SOURCE_PRIORITY = {"stdict": 0, "enwikt": 0, "opendict": 1, "wikidata": 2, "kowiki": 2}


def source_rank(source: str) -> int:
    return SOURCE_PRIORITY.get(source.split(":", 1)[0], 0)


def pos_group(e: stdict_mod.Entry) -> str:
    """Common and proper nouns (and unlabelled phrases) are one group; other parts of speech keep their own line.

    A pair is often listed as 명사 on a Hangul page and 고유 명사 on a Hanja page, which is
    one reading. But 일절 一切 as 부사 and as 명사 are different facts: the converter's
    part-of-speech filter needs both, so a Kiwi adverb token can find the adverb line.
    """
    if e.pos in ("명사", "고유 명사") or (e.pos == "품사 없음" and " " in e.hangul):
        return "명사"
    return e.pos


def merge_entries(entries: list[stdict_mod.Entry]) -> list[stdict_mod.Entry]:
    """One line per (hangul, hanja, part-of-speech group): prefer a gloss, then a common noun, then source rank."""
    best: dict[tuple[str, str, str], stdict_mod.Entry] = {}
    weight: dict[tuple[str, str, str], int] = {}
    cats: dict[tuple[str, str, str], set[str] | None] = {}  # None = some entry is general or unlabelled
    for e in entries:
        key = (e.hangul, e.hanja, pos_group(e))
        weight[key] = max(weight.get(key, 0), e.weight)
        if key not in cats:
            cats[key] = set()
        if cats[key] is not None:
            if e.domain:
                cats[key].update(e.domain.split(","))
            else:
                cats[key] = None
        rank = (not e.sense, POS_PREFERENCE.get(e.pos, 2), source_rank(e.source), e.source)
        cur = best.get(key)
        if cur is None or rank < (not cur.sense, POS_PREFERENCE.get(cur.pos, 2), source_rank(cur.source), cur.source):
            best[key] = e
    out = [
        stdict_mod.Entry(e.hangul, e.hanja, e.pos, e.source, e.sense, weight[k], ",".join(sorted(cats[k] or ())))
        for k, e in best.items()
    ]
    return sorted(drop_nonstandard_spellings(out), key=lambda e: (e.hangul, e.hanja, e.pos))


BOUND_POS = frozenset({"의존 명사", "접미사", "접사"})


def drop_nonstandard_spellings(entries: list[stdict_mod.Entry]) -> list[stdict_mod.Entry]:
    """Drop 력사/령토/녀자-type spellings when the same Hanja also has the 頭音法則 form (역사)."""
    from .hangul import initial_sound_variants

    by_hanja: dict[str, set[str]] = {}
    for e in entries:
        by_hanja.setdefault(e.hanja, set()).add(e.hangul)
    kept = []
    for e in entries:
        if e.pos in BOUND_POS:
            kept.append(e)  # 2026년, 100리: a bound form is not word-initial, 頭音法則 does not apply to it
            continue
        first = e.hangul[0]
        standard = initial_sound_variants(first) - {first}
        if standard and any(first_alt + e.hangul[1:] in by_hanja[e.hanja] for first_alt in standard):
            continue
        kept.append(e)
    return kept


def main(argv: list[str] | None = None) -> int:
    console.utf8_streams()  # --help carries Korean; a Windows console would fail on it
    try:
        return _build(argv)
    except (
        stdict_mod.InputError,
        EOFError,
        OSError,
        zipfile.BadZipFile,
    ) as e:  # a corrupt or truncated input, a full disk
        print(f"入力 또는 出力 誤謬 / input or output error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def _build(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(
        prog="gukhan-lexicon-build",
        description=(
            "辭典 構築 / build lexicon.tsv from 표준국어대사전, 우리말샘 and/or Wiktionary (kaikki.org). No downloads."
        ),
    )
    ap.add_argument(
        "--stdict",
        type=Path,
        help="표준국어대사전 XML dump: zip, directory or single file (needs a 국립국어원 account)",
    )
    ap.add_argument(
        "--opendict",
        type=Path,
        help="우리말샘 XML dump: directory of chunks (opendict/0050000.xml …), zip or single file",
    )
    ap.add_argument(
        "--wiktextract",
        type=Path,
        action="append",
        default=[],
        help="kaikki.org wiktextract JSONL (.jsonl 또는 .jsonl.gz), 여러 번 가능 / "
        "kaikki.org wiktextract JSONL (.jsonl or .jsonl.gz), e.g. kaikki.org-dictionary-Korean.jsonl; repeatable",
    )
    ap.add_argument(
        "--kowiki",
        type=Path,
        help="한국어 위키백과 dump (kowiki-latest-pages-articles.xml.bz2): 첫 문단의 이름, CC BY-SA 4.0 / "
        "Korean Wikipedia dump (kowiki-latest-pages-articles.xml.bz2): names from article leads, CC BY-SA 4.0",
    )
    ap.add_argument(
        "--wikidata-lexemes",
        type=Path,
        help="Wikidata 語彙素 dump (latest-lexemes.json.bz2, CC0), 먼저 調査 실행 (wikidata_lexemes.py 참조) / "
        "Wikidata lexeme dump (latest-lexemes.json.bz2, CC0); run the survey first (see wikidata_lexemes.py)",
    )
    ap.add_argument(
        "--wikidata-hanja-property",
        action="append",
        default=[],
        metavar="P####",
        help="漢字 形態를 담은 Wikidata 屬性 (調査 결과), 여러 번 가능 / "
        "Wikidata statement property that holds the Hanja form (from the survey); repeatable",
    )
    ap.add_argument(
        "--law-glosses",
        type=Path,
        help=(
            "法令 註釋: legalize-kr checkout (kr/<법령명>/*.md): Hanja the statutes gloss as 분사무소(分事務所). "
            "Optional; adds only words no other source has, and writes law-glosses.tsv and law-overrides.txt. "
            "(選擇 事項: 다른 source에 없는 낱말만 더하고 law-glosses.tsv와 law-overrides.txt를 씀)"
        ),
    )
    ap.add_argument(
        "--law-glosses-exclude",
        type=Path,
        action="append",
        default=[],
        help="金標準 쌍을 法令 註釋에서 뺄 回歸 項目 TSV, 여러 번 가능 / "
        "regression items TSV whose gold pairs are left out of the law glosses (keeps it unseen); repeatable",
    )
    ap.add_argument(
        "--unihan",
        type=Path,
        help="Unihan.zip 또는 Unihan_Readings.txt가 든 directory (讀音 檢證) / "
        "Unihan.zip or directory with Unihan_Readings.txt (validates readings)",
    )
    ap.add_argument("-o", "--out", required=True, type=Path, help="出力 directory / output directory")
    ap.add_argument("--krdict", type=Path, help="한국어기초사전 XML vocabulary levels / candidate tie-breaker")
    ap.add_argument("--learner-list", type=Path, help="국립국어원 learner vocabulary text / candidate tie-breaker")
    args = ap.parse_args(argv)

    if not (args.stdict or args.opendict or args.wiktextract or args.kowiki or args.wikidata_lexemes):
        print(
            "辭典 source가 없습니다 / give --stdict, --opendict, --wiktextract, --kowiki or --wikidata-lexemes",
            file=sys.stderr,
        )
        return 2
    if args.law_glosses and not (args.stdict or args.opendict or args.wiktextract or args.kowiki):
        print(
            "法律 註釋만으로는 辭典을 만들 수 없습니다 / --law-glosses supplements a dictionary source; "
            "give --stdict, --opendict, --wiktextract or --kowiki too",
            file=sys.stderr,
        )
        return 2
    for p in (
        [
            p
            for p in (
                args.stdict,
                args.opendict,
                args.kowiki,
                args.wikidata_lexemes,
                args.krdict,
                args.learner_list,
                args.law_glosses,
            )
            if p
        ]
        + args.wiktextract
        + args.law_glosses_exclude
    ):
        if not p.exists():
            print(f"入力 file을 찾을 수 없습니다 / input not found: {p}", file=sys.stderr)
            return 2
    readings: dict[str, list[str]] | None = None
    unihan_version = None
    if args.unihan:
        if not args.unihan.exists():
            print(f"Unihan 파일을 찾을 수 없습니다 / Unihan input not found: {args.unihan}", file=sys.stderr)
            return 2
        readings, unihan_version = unihan_mod.read_khangul(args.unihan)
        tagged, _ = unihan_mod.read_khangul(args.unihan, with_tags=True)
        print(f"Unihan kHangul: {len(readings)} characters, version {unihan_version or 'unknown'}")

    entries, rejects = [], []
    counts: dict[str, int] = {}
    native: dict[str, tuple[str, str, int]] = {}
    native_pos: dict[tuple[str, str], tuple[str, str]] = {}
    if args.stdict:
        e, r, stats = stdict_mod.parse(args.stdict, readings)
        print(f"stdict: items={stats.items} sino={stats.sino} entries={stats.entries} rejected={stats.rejected}")
        print("stdict tags seen in first items: " + ", ".join(sorted(stats.tags_seen)))
        if stats.items == 0 or "word" not in stats.tags_seen:
            print(
                "XML에서 <item>/<word>를 찾지 못했습니다. 덤프 形式을 確認하세요 / "
                "No <item>/<word> found; check the dump schema (see docs/PLAN.md §3).",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        native_pos.update(stats.native_pos)
        counts["stdict_items"], counts["stdict_entries"] = stats.items, stats.entries
    if args.opendict:
        e, r, stats = opendict_mod.parse(args.opendict, readings)
        print(f"opendict: items={stats.items} sino={stats.sino} entries={stats.entries} rejected={stats.rejected}")
        if stats.items == 0 or "wordInfo" not in stats.tags_seen:
            print(
                "XML에서 <item>/<wordInfo>를 찾지 못했습니다. 우리말샘 덤프 形式을 確認하세요 / "
                "No <item>/<wordInfo> found; check the 우리말샘 dump schema (see lexicon_build/opendict.py).",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        counts["opendict_items"], counts["opendict_entries"] = stats.items, stats.entries
    if args.kowiki:
        e, r, stats = kowiki_mod.parse(args.kowiki, readings)
        print(f"kowiki: pages={stats.items} hanja-leads={stats.sino} entries={stats.entries} rejected={stats.rejected}")
        if stats.items == 0:
            print(
                "위키백과 덤프에서 문서를 찾지 못했습니다 / no main-namespace pages found in the kowiki dump",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        counts["kowiki_pages"], counts["kowiki_entries"] = stats.items, stats.entries
    if args.wikidata_lexemes:
        e, r, stats = wikidata_mod.parse(args.wikidata_lexemes, readings, tuple(args.wikidata_hanja_property))
        print(
            f"wikidata lexemes: lexemes={stats.items} with-hanja={stats.sino} "
            f"entries={stats.entries} rejected={stats.rejected}"
        )
        if stats.items == 0:
            print("lexeme 덤프에서 항목을 찾지 못했습니다 / no lexemes found in the Wikidata dump", file=sys.stderr)
            return 2
        entries += e
        rejects += r
        counts["wikidata_lexemes"], counts["wikidata_entries"] = stats.items, stats.entries
    for p in args.wiktextract:
        e, r, stats = wikt_mod.parse(p, readings)
        print(
            f"wiktextract {p.name}: lines={stats.items} pairs={stats.sino} "
            f"entries={stats.entries} rejected={stats.rejected}"
        )
        if stats.items == 0 or "word" not in stats.tags_seen:
            print(
                f"JSONL에서 word 項目을 찾지 못했습니다 / no wiktextract objects with 'word' found in {p}",
                file=sys.stderr,
            )
            return 2
        entries += e
        rejects += r
        for w, v in stats.native.items():
            if w not in native or v[2] > native[w][2]:
                native[w] = v
        counts["wiktextract_lines"] = counts.get("wiktextract_lines", 0) + stats.items
        counts["wiktextract_entries"] = counts.get("wiktextract_entries", 0) + stats.entries
    licence = "CC-BY-SA-2.0-KR" if not (args.wiktextract or args.kowiki) else "CC-BY-SA-4.0"
    if not (args.stdict or args.opendict or args.wiktextract or args.kowiki):
        licence = "CC0-1.0"  # Wikidata lexemes alone

    args.out.mkdir(parents=True, exist_ok=True)
    merged = merge_entries(entries)
    law_stats = None
    if args.law_glosses:
        excluded: set[tuple[str, str]] = set()
        for path in args.law_glosses_exclude:
            excluded |= law_mod.pairs_in_items(path)
        law_entries, law_rejects, law_stats = law_mod.parse(args.law_glosses, readings, excluded)
        print(
            f"law glosses: statutes={law_stats.items} (repealed {law_stats.repealed}, "
            f"with glosses {law_stats.glossed}) "
            f"gloss-tokens={law_stats.tokens} pairs={len(law_stats.pairs)} rejected={law_stats.rejected} "
            f"excluded={law_stats.excluded}"
        )
        if law_stats.items == 0:
            print("法令 Markdown을 찾지 못했습니다 / no statute .md files found in --law-glosses", file=sys.stderr)
            return 2
        known = {e.hangul for e in merged}
        added = [e for e in law_entries if e.hangul not in known]
        merged = sorted(merged + added, key=lambda e: (e.hangul, e.hanja, e.pos))
        rejects += law_rejects
        counts.update(
            law_statutes=law_stats.items,
            law_pairs=len(law_stats.pairs),
            law_entries_added=len(added),
            law_overrides=len(law_mod.override_lines(law_stats)),
        )
    # A native word with the same sound as a Sino-Korean entry becomes a candidate whose Hanja
    # column repeats the Hangul, so the converter flags 안 (案 or inside?) instead of guessing.
    sino_words = {e.hangul for e in merged}
    natives = [
        stdict_mod.Entry(w, w, pos, f"enwikt:{w}", gloss, weight)
        for w, (pos, gloss, weight) in sorted(native.items())
        if w in sino_words
    ]
    have = {(e.hangul, e.pos) for e in natives}
    natives += [
        stdict_mod.Entry(w, w, pos, source, gloss, 0)
        for (w, pos), (gloss, source) in sorted(native_pos.items())
        if w in sino_words and (w, pos) not in have
    ]
    merged = sorted(merged + natives, key=lambda e: (e.hangul, e.hanja, e.pos))
    counts["native_homographs"] = len(natives)
    lex_path = args.out / "lexicon.tsv"
    levels = krdict_levels(args.krdict) if args.krdict else {}
    ranks = learner_ranks(args.learner_list) if args.learner_list else {}
    counts["level_matches"] = sum((e.hangul, e.hanja) in levels for e in merged)
    counts["learner_matches"] = sum((e.hangul, e.hanja) in ranks for e in merged)
    with lex_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(HEADER.format(licence=licence))
        for e in merged:
            key = e.hangul, e.hanja
            fh.write(e.tsv() + f"\t{levels.get(key, 0)}\t{ranks.get(key, 0)}\t{e.domain}\n")
    outputs = {"lexicon": lex_path}
    seen = merged

    rejects = sorted(
        {(r.hangul, r.raw_hanja, r.reason): r for r in rejects}.values(), key=lambda r: (r.hangul, r.source)
    )
    rej_path = args.out / "rejects.tsv"
    with rej_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# hangul\traw_hanja\tsource\treason\n")
        for r in rejects:
            fh.write(r.tsv() + "\n")
    outputs["rejects"] = rej_path

    if law_stats is not None:
        pairs_path = args.out / "law-glosses.tsv"
        pairs_path.write_text(law_mod.pairs_tsv(law_stats), encoding="utf-8", newline="")
        outputs["law_glosses"] = pairs_path
        ov_path = args.out / "law-overrides.txt"
        ov_path.write_text(
            "# 法律 註釋에서 얻은 우선 規則 / readings the statutes gloss one way\n"
            "# opt-in, for legal text only: gukhan --overrides law-overrides.txt\n"
            + "".join(line + "\n" for line in law_mod.override_lines(law_stats)),
            encoding="utf-8",
            newline="",
        )
        outputs["law_overrides"] = ov_path

    if readings:
        chars_path = args.out / "chars.tsv"
        with chars_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("# hanja\treadings (reading:tag, Unihan order; E = education-set reading)\n")
            for ch in sorted(readings):
                fh.write(f"{ch}\t{' '.join(tagged[ch])}\n")
        outputs["chars"] = chars_path

    write_manifest(
        args.out,
        stdict=args.stdict,
        opendict=args.opendict,
        wiktextract=args.wiktextract,
        kowiki=args.kowiki,
        wikidata_lexemes=args.wikidata_lexemes,
        law_glosses=args.law_glosses,
        unihan=args.unihan,
        unihan_version=unihan_version,
        licence=licence,
        counts={**counts, "entries": len(seen), "rejected": len(rejects)},
        outputs=outputs,
        ranking_sources={k: p for k, p in {"krdict": args.krdict, "learner_list": args.learner_list}.items() if p},
    )
    print(f"wrote {args.out / 'lexicon.tsv'} ({len(seen)} entries) and manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
