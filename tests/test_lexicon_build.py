# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from gukhan.lexicon_build import stdict, unihan
from gukhan.lexicon_build.cli import main
from gukhan.lexicon_build.hangul import initial_sound_variants

FIX = Path(__file__).parent / "fixtures"


def test_initial_sound_variants():
    assert "이" in initial_sound_variants("리")
    assert "노" in initial_sound_variants("로")
    assert "여" in initial_sound_variants("녀")
    assert initial_sound_variants("가") == {"가"}


def test_align_mixed_and_phrase():
    assert stdict.align("책상다리", "冊床--") == "冊床다리"
    assert stdict.align("작전 계획", "作戰計劃") == "作戰 計劃"
    assert stdict.align("전기", "電氣氣") is None
    assert stdict.align("전기", "電") is None


def test_unihan_fixture():
    readings, version = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    assert version == "16.0.0"
    assert readings["理"] == ["리"]


def test_parse_with_validation():
    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    entries, rejects, stats = stdict.parse(FIX / "stdict_sample.xml", readings)
    forms = {(e.hangul, e.hanja) for e in entries}
    assert ("전기", "電氣") in forms and ("전기", "傳記") in forms and ("전기", "前期") in forms
    assert ("책상다리", "冊床다리") in forms
    assert ("작전 계획", "作戰 計劃") in forms
    assert ("이론", "理論") in forms  # 頭音法則: 理 reads 리, written 이
    assert not any(e.hangul == "사과" for e in entries)  # 고유어 skipped
    reasons = {r.hangul: r.reason for r in rejects}
    assert "nawn" not in reasons
    assert "align" in reasons["나쁜"]
    assert "reads" in reasons["오류"]
    assert stats.items == 9 and stats.rejected == 2
    assert next(e for e in entries if e.hanja == "電氣").sense.startswith("물질")


def test_cli_builds_deterministic_outputs(tmp_path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    for out in (out1, out2):
        rc = main(
            ["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(FIX / "Unihan_Readings.txt"), "-o", str(out)]
        )
        assert rc == 0
    assert (out1 / "lexicon.tsv").read_bytes() == (out2 / "lexicon.tsv").read_bytes()
    m = json.loads((out1 / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-2.0-KR"
    assert m["sources"]["stdict"]["sha256"] == m["sources"]["stdict"]["sha256"]
    assert m["sources"]["unihan"]["version"] == "16.0.0"
    assert m["counts"]["entries"] == 6
    assert m["outputs"]["lexicon"]["sha256"]
    text = (out1 / "lexicon.tsv").read_text(encoding="utf-8")
    assert text.startswith("# gukhan lexicon")
    assert "전기\t電氣\t명사\tstdict:1001" in text
    assert (out1 / "chars.tsv").exists()


def test_cli_rejects_wrong_schema(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<root><thing>x</thing></root>", encoding="utf-8")
    assert main(["--stdict", str(bad), "-o", str(tmp_path / "o")]) == 2


def test_wiktextract_fixture():
    from gukhan.lexicon_build import wiktextract

    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    entries, rejects, stats = wiktextract.parse(FIX / "wiktextract_sample.jsonl", readings)
    forms = {(e.hangul, e.hanja, e.pos) for e in entries}
    assert ("핵산", "核酸", "명사") not in forms  # 核/酸 not in the tiny Unihan fixture → rejected, not guessed
    assert ("제정", "制定", "명사") not in forms  # same
    assert ("전기", "電氣", "명사") in forms and ("전기", "傳記", "명사") in forms
    assert ("공부하다", "工夫하다", "동사") not in forms  # 工/夫 not in fixture
    assert not any(e.hangul == "전" for e in entries)  # character pages skipped
    assert not any(e.hangul == "사과" for e in entries)  # no hanja form
    assert stats.items == 9
    assert any(r.hangul == "오류" and "reads" in r.reason for r in rejects)
    # without Unihan validation everything aligned is kept
    entries2, _, _ = wiktextract.parse(FIX / "wiktextract_sample.jsonl")
    forms2 = {(e.hangul, e.hanja) for e in entries2}
    assert {("핵산", "核酸"), ("제정", "制定"), ("공부하다", "工夫하다"), ("오류", "電氣")} <= forms2
    assert next(e for e in entries2 if e.hanja == "制定").sense == "enactment"  # quoted gloss of "hanja form of"
    assert next(e for e in entries2 if e.hanja == "制定").weight == 0  # Hanja page, no own senses
    assert next(e for e in entries2 if e.hanja == "核酸").weight == 11  # Hangul page + 1 sense


def test_shorten_gloss_keeps_parentheses_balanced():
    from gukhan.lexicon_build.wiktextract import shorten

    g = "yeoksa (a practice in the Joseon Dynasty whereby a newly appointed official was made to wait for a long time)"
    out = shorten(g, 60)
    assert out.count("(") == out.count(")") and out.endswith("…") and len(out) <= 61
    assert shorten("short", 60) == "short"
    assert shorten("yeoksa (service under successive kings)") == "service under successive kings"
    assert shorten("(Chinese character classification) a compound ideograph") == "a compound ideograph"
    assert shorten("(only a label)") == "only a label"


def test_weight_counts_derived_terms():
    from gukhan.lexicon_build import wiktextract

    lines = [
        '{"word": "전기", "lang_code": "ko", "pos": "noun", "forms": [{"form": "電氣", "tags": ["hanja"]}],'
        ' "senses": [{"glosses": ["electricity"]}], "derived": [{"word": "전기 공학"}, {"word": "전기차"}]}',
        '{"word": "전기", "lang_code": "ko", "pos": "noun", "forms": [{"form": "轉機", "tags": ["hanja"]}],'
        ' "senses": [{"glosses": ["turning point"]}]}',
    ]
    f = FIX.parent / "_tmp_weight.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        entries, _, _ = wiktextract.parse(f)
    finally:
        f.unlink()
    w = {e.hanja: e.weight for e in entries}
    assert w == {"電氣": 13, "轉機": 11}


def test_cli_wiktextract_only_sets_licence(tmp_path):
    out = tmp_path / "w"
    rc = main(["--wiktextract", str(FIX / "wiktextract_sample.jsonl"), "-o", str(out)])
    assert rc == 0
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-4.0"
    assert m["sources"]["stdict"] is None and len(m["sources"]["wiktextract"]) == 1
    assert "Wiktionary" in m["notice"] and "標準國語大辭典" not in m["notice"]
    assert (out / "lexicon.tsv").read_text(encoding="utf-8").startswith("# gukhan lexicon\tlicence=CC-BY-SA-4.0")
    rc = main(
        [
            "--stdict",
            str(FIX / "stdict_sample.xml"),
            "--wiktextract",
            str(FIX / "wiktextract_sample.jsonl"),
            "--unihan",
            str(FIX / "Unihan_Readings.txt"),
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-4.0" and m["counts"]["stdict_entries"] == 6
    assert main(["-o", str(out)]) == 2


def test_merge_entries_prefers_gloss_and_common_noun():
    from gukhan.lexicon_build.cli import merge_entries

    E = stdict.Entry
    merged = merge_entries(
        [
            E("역사", "繹史", "고유 명사", "enwikt:역사", "a book"),
            E("역사", "繹史", "명사", "enwikt:繹史", ""),
            E("역사", "歷史", "명사", "enwikt:繹史", ""),
            E("역사", "歷史", "명사", "enwikt:역사", "history"),
        ]
    )
    assert [(e.hanja, e.pos, e.sense) for e in merged] == [("歷史", "명사", "history"), ("繹史", "고유 명사", "a book")]


def test_unihan_version_from_date_or_header(tmp_path):
    f = tmp_path / "Unihan_Readings.txt"
    f.write_text("#\n#\tUnihan_Readings.txt\n#\tDate: 2025-09-01 [MS]\nU+4E00\tkHangul\t일:0E\n", encoding="utf-8")
    assert unihan.read_khangul(f)[1] == "dated 2025-09-01"
    f.write_text(
        "# Unihan_Readings.txt\n# Date: 2026-07-31 00:00:00 GMT [KL]\n# Unicode Version 18.0.0\n#\n"
        "U+4E00\tkHangul\t일:0E\n",
        encoding="utf-8",
    )
    assert unihan.read_khangul(f)[1] == "18.0.0"
    f.write_text("# Unihan_Readings-17.0.0.txt\nU+4E00\tkHangul\t일:0E\n", encoding="utf-8")
    assert unihan.read_khangul(f)[1] == "17.0.0"
