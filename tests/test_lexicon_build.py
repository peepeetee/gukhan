# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from gukhan.lexicon_build import kowiki, stdict, unihan, wikidata_lexemes
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
    assert ("가감하다", "加減하다") in forms  # full-dump style: homonym number stripped, -하다 tail kept
    assert ("가", "加") in forms
    assert stats.items == 11 and stats.rejected == 2
    assert "<" not in next(e for e in entries if e.hanja == "加減하다").sense
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
    assert m["counts"]["entries"] == 8 and m["counts"].get("native_homographs", 0) == 0
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
    assert stats.items == 12
    assert any(r.hangul == "오류" and "reads" in r.reason for r in rejects)
    assert stats.native["안"][0] == "명사" and stats.native["안"][1] == "inside, interior"
    assert "배" in stats.native  # native with no Sino entry; the CLI only keeps those with one
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
    assert (
        shorten("yeoksa (service under successive kings)", romanizations={"yeoksa"}) == "service under successive kings"
    )
    assert shorten("operation (of a machine)", romanizations={"gadong"}) == "operation (of a machine)"
    assert shorten("(Chinese character classification) a compound ideograph") == "a compound ideograph"
    assert shorten("(only a label)") == "only a label"


def test_form_of_gloss_keeps_nested_parentheses():
    from gukhan.lexicon_build.wiktextract import _gloss

    raw = "hanja form of 회의 (“(Chinese character classification) compound indicatives, one of six 六書”)"
    g = _gloss({"senses": [{"glosses": [raw], "tags": ["form-of"]}]})
    assert g.startswith("compound indicatives") and g.count("(") == g.count(")")
    g = _gloss({"senses": [{"glosses": ["hanja form of 가동 (“operation (of a machine)”)"], "tags": ["form-of"]}]})
    assert g == "operation (of a machine)"


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
    tsv = (out / "lexicon.tsv").read_text(encoding="utf-8")
    assert "안\t案\t명사\tenwikt:안\tplan, proposal\t12" in tsv
    assert "안\t안\t명사\tenwikt:안\tinside, interior\t12" in tsv  # native homograph, same-sound marker
    assert "배\t배" not in tsv
    assert m["counts"]["native_homographs"] == 1
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
    assert m["licence"] == "CC-BY-SA-4.0" and m["counts"]["stdict_entries"] == 8
    assert main(["-o", str(out)]) == 2


def test_drop_nonstandard_spellings():
    from gukhan.lexicon_build.cli import drop_nonstandard_spellings

    E = stdict.Entry
    kept = drop_nonstandard_spellings(
        [
            E("력사", "歷史", "명사", "t"),
            E("역사", "歷史", "명사", "t"),
            E("녀자", "女子", "명사", "t"),
            E("리론", "理論", "명사", "t"),
        ]
    )
    assert [(e.hangul, e.hanja) for e in kept] == [("역사", "歷史"), ("녀자", "女子"), ("리론", "理論")]


def test_north_korea_senses_skipped_and_label_dropped():
    from gukhan.lexicon_build import wiktextract

    lines = [
        '{"word": "력사", "lang_code": "ko", "pos": "noun", "forms": [{"form": "歷史", "tags": ["hanja"]}],'
        ' "senses": [{"glosses": ["history"], "tags": ["North-Korea"]}]}',
        '{"word": "歷史", "lang_code": "ko", "pos": "noun", "forms": [{"form": "력사", "tags": ["hangeul"]}],'
        ' "senses": [{"glosses": ["hanja form of 력사 (“history”) (North Korea)"], "tags": ["form-of"]}]}',
        '{"word": "歷史", "lang_code": "ko", "pos": "noun", "forms": [{"form": "역사", "tags": ["hangeul"]}],'
        ' "senses": [{"glosses": ["hanja form of 역사 (“history”) (South Korea)"], "tags": ["form-of"]}]}',
    ]
    f = FIX.parent / "_tmp_nk.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        entries, _, _ = wiktextract.parse(f)
    finally:
        f.unlink()
    assert [(e.hangul, e.sense) for e in entries] == [("력사", "history"), ("역사", "history")]


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


def test_opendict_fixture():
    from gukhan.lexicon_build import opendict

    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    entries, rejects, stats = opendict.parse(FIX / "opendict_sample.xml", readings)
    forms = {(e.hangul, e.hanja, e.pos) for e in entries}
    assert ("전기", "電氣", "명사") in forms  # two senses → two entries here, one line after merge
    assert sum(1 for e in entries if e.hanja == "電氣" and e.hangul == "전기") == 2
    assert not any(e.hanja == "傳記" for e in entries)  # 북한어 sense skipped
    assert not any(e.hanja == "前期" for e in entries)  # 방언 sense skipped
    assert ("작전 계획", "作戰 計劃", "품사 없음") in forms  # 구: ^ is a space, pos as 표준국어대사전 writes it
    assert ("책상다리", "冊床다리", "명사") in forms  # native component assembled from the parts
    assert ("전기주스", "電氣주스", "명사") in forms  # foreign component of unknown length
    assert ("전극", "電劇", "명사") in forms and not any(e.hanja == "前劇" for e in entries)  # /(병기): first only
    assert ("이론적", "理論的", "관형사") in forms and ("이론적", "理論的", "명사") in forms  # 관·명 expanded
    assert ("가감", "加減", "어근") in forms  # 품사 없음 + ‘…’의 어근 → 어근
    assert not any(e.hangul == "전끼" for e in entries)  # ⇒규범 표기는: non-standard spelling skipped
    assert not any(e.hangul.startswith("전기가") for e in entries)  # 관용구 skipped
    assert not any(e.hangul == "사과" for e in entries)  # 고유어 skipped
    assert [r.hangul for r in rejects] == ["오류"] and "reads" in rejects[0].reason
    assert stats.items == 14 and stats.rejected == 1
    e = next(e for e in entries if e.source == "opendict:2001")
    assert e.sense == "물질 안의 전자가 흐르는 현상." and e.weight == 0  # markup stripped, examples never read


def test_components_to_hanja():
    from gukhan.lexicon_build.stdict import components_to_hanja as c

    assert c("생과일", [("生", "한자"), ("과일", "고유어")]) == "生--"
    assert c("생과일주스", [("生", "한자"), ("과일", "고유어"), ("juice", "영어")]) == "生----"
    assert c("생크림단팥빵", [("生", "한자"), ("cream", "영어"), ("단팥빵", "고유어")]) == "生-----"
    assert c("가갸시절", [("가갸", "고유어"), ("時節", "한자")]) == "--時節"
    assert c("서어", [("齟齬", "한자"), ("/", "/(병기)"), ("鉏鋙", "한자")]) == "齟齬"
    assert c("생균 백신", [("生菌", "한자"), ("vaccine", "영어")]) == "生菌--"
    # two foreign components cannot be placed
    assert c("생식샘자극호르몬분비호르몬", [("生殖", "한자"), ("샘", "고유어"), ("刺戟", "한자"), ("hormone", "영어"),
                                            ("分泌", "한자"), ("hormone", "영어")]) is None  # fmt: skip
    assert (
        c("생과일", [("生", "한자"), ("배", "고유어")]) == "生--"
    )  # a mismatching native part is still placed by length


def test_cli_opendict_merges_and_ranks_below_stdict(tmp_path):
    out = tmp_path / "od"
    rc = main(
        [
            "--stdict",
            str(FIX / "stdict_sample.xml"),
            "--opendict",
            str(FIX / "opendict_sample.xml"),
            "--unihan",
            str(FIX / "Unihan_Readings.txt"),
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    tsv = (out / "lexicon.tsv").read_text(encoding="utf-8")
    lines = [ln for ln in tsv.splitlines() if ln.startswith("전기\t電氣\t")]
    assert len(lines) == 1 and "\tstdict:1001\t" in lines[0]  # one line per pair; 표준국어대사전 represents it
    assert sum(1 for ln in tsv.splitlines() if ln.startswith("작전 계획\t")) == 1
    assert "전기주스\t電氣주스\t명사\topendict:2007" in tsv  # 우리말샘-only pair kept with its own source
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-2.0-KR"
    assert m["sources"]["opendict"]["licence"] == "CC-BY-SA-2.0-KR" and m["sources"]["opendict"]["sha256"]
    assert m["counts"]["opendict_items"] == 14 and m["counts"]["opendict_entries"] == 9
    assert "우리말샘" in m["notice"] and "標準國語大辭典" in m["notice"]
    rc = main(["--opendict", str(FIX / "opendict_sample.xml"), "-o", str(tmp_path / "only")])
    assert rc == 0
    m = json.loads((tmp_path / "only" / "manifest.json").read_text(encoding="utf-8"))
    assert m["sources"]["stdict"] is None and m["licence"] == "CC-BY-SA-2.0-KR"


def test_stdict_mixed_word_from_components():
    xml = (
        "<channel><item><target_code>9</target_code><word_info><word>생-과일</word><word_type>혼종어</word_type>"
        "<original_language_info><original_language>生</original_language><language_type>한자</language_type>"
        "</original_language_info><original_language_info><original_language>과일</original_language>"
        "<language_type>고유어</language_type></original_language_info><pos_info><pos>명사</pos></pos_info>"
        "</word_info></item></channel>"
    )
    f = FIX.parent / "_tmp_stdict_mixed.xml"
    f.write_text(xml, encoding="utf-8")
    try:
        entries, rejects, _ = stdict.parse(f)
    finally:
        f.unlink()
    assert [(e.hangul, e.hanja) for e in entries] == [("생과일", "生과일")] and not rejects


def test_kowiki_leads_become_name_entries():
    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings_names.txt")
    entries, rejects, stats = kowiki.parse(FIX / "kowiki_sample.xml", readings)
    forms = {(e.hangul, e.hanja) for e in entries}
    assert ("이순신", "李舜臣") in forms  # 頭音法則: 李 reads 리, written 이
    assert ("대한민국 헌법", "大韓民國 憲法") in forms  # {{llang}} dropped; spacing follows the Hangul
    assert ("서울특별시", "서울特別市") in forms  # Hangul inside the parenthesis stays Hangul
    assert ("전기", "電氣") in forms  # {{한자|…}} unwrapped; title disambiguator removed
    assert all(e.pos == "고유 명사" and e.source.startswith("kowiki:") for e in entries)
    assert next(e for e in entries if e.hanja == "電氣").sense == "물리"
    reasons = {r.hangul: r.reason for r in rejects}
    assert "마오쩌둥" in reasons and "도쿄" in reasons  # Chinese/Japanese readings, not Sino-Korean
    assert not any(e.hangul in ("김철수", "동음이의", "분류") for e in entries)  # no Hanja / redirect / other namespace
    assert stats.items == 8 and stats.entries == 4


def test_kowiki_markup_helpers():
    assert kowiki.hanja_of("한자: 大韓民國, 영어: Korea", "대한민국") == "大韓民國"
    assert kowiki.hanja_of("1950년 ~ ", "김철수") is None
    assert kowiki.lead_pair("{{틀|a=b}}\n* 목록\n'''가나'''(街那)는") == ("가나", "街那")


def test_wikidata_lexeme_survey_and_parse():
    report = wikidata_lexemes.survey(FIX / "wikidata_lexemes_sample.json")
    assert report["counts"]["lexemes"] == 5 and report["counts"]["korean"] == 4
    assert report["counts"]["hanja_in_lemma_or_form"] == 2
    assert report["hanja_statement_properties"] == {"P9999": 1}
    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings_names.txt")
    entries, _, stats = wikidata_lexemes.parse(FIX / "wikidata_lexemes_sample.json", readings)
    assert {(e.hangul, e.hanja, e.pos) for e in entries} == {("전기", "電氣", "명사")}
    assert stats.rejected == 1  # 傳記: no fixture reading for 傳
    entries, _, _ = wikidata_lexemes.parse(FIX / "wikidata_lexemes_sample.json", None, ("P9999",))
    assert ("서울", "漢陽", "고유 명사") in {(e.hangul, e.hanja, e.pos) for e in entries}


def test_cli_names_sources_set_licence_and_manifest(tmp_path):
    out = tmp_path / "n"
    rc = main(
        [
            "--kowiki",
            str(FIX / "kowiki_sample.xml"),
            "--wikidata-lexemes",
            str(FIX / "wikidata_lexemes_sample.json"),
            "--unihan",
            str(FIX / "Unihan_Readings_names.txt"),
            "-o",
            str(out),
        ]
    )
    assert rc == 0
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-4.0" and m["sources"]["kowiki"]["licence"].startswith("CC-BY-SA-4.0")
    assert m["sources"]["wikidata_lexemes"]["licence"] == "CC0-1.0"
    assert "위키백과" in m["notice"] and "Wikidata" in m["notice"]
    text = (out / "lexicon.tsv").read_text(encoding="utf-8")
    assert "이순신\t李舜臣\t고유 명사\tkowiki:이순신" in text and "전기\t電氣" in text
    wd_only = tmp_path / "w"
    assert main(["--wikidata-lexemes", str(FIX / "wikidata_lexemes_sample.json"), "-o", str(wd_only)]) == 0
    assert json.loads((wd_only / "manifest.json").read_text(encoding="utf-8"))["licence"] == "CC0-1.0"


def test_sense_domain_is_set_only_when_every_sense_is_specialist():
    from gukhan.lexicon_build.stdict import sense_domain

    assert sense_domain(["불교"]) == "불교"
    assert sense_domain(["불교", "민속"]) == "민속,불교"
    assert sense_domain(["불교", None]) == ""  # one everyday sense: everyday word
    assert sense_domain(["불교", "없음"]) == ""
    assert sense_domain([]) == ""


def test_merge_keeps_domain_only_when_all_entries_have_one():
    from gukhan.lexicon_build.cli import merge_entries
    from gukhan.lexicon_build.stdict import Entry as E

    out = merge_entries([E("보살", "菩薩", "명사", "a", "x", domain="불교"), E("보살", "菩薩", "명사", "b", "y")])
    assert [e.domain for e in out] == [""]
    out = merge_entries(
        [E("보살", "菩薩", "명사", "a", "x", domain="불교"), E("보살", "菩薩", "명사", "b", "y", domain="민속")]
    )
    assert [e.domain for e in out] == ["민속,불교"]


def test_lexicon_reads_the_domain_column():
    from gukhan.lexicon import Lexicon

    lex = Lexicon.from_lines(["보살\t菩薩\t명사\tt\t\t0\t0\t0\t불교", "보살\t補殺\t명사\tt\t\t0\t0\t0\t"])
    assert {e.hanja: e.domain for e in lex.candidates("보살")} == {"菩薩": "불교", "補殺": ""}


def test_tsv_cells_never_contain_tabs_or_line_breaks():
    from gukhan.lexicon_build.stdict import Entry, Reject

    row = Entry("가", "街", "명사", "src", "a\tb\r\nc  ", 3).tsv()
    assert row == "가\t街\t명사\tsrc\ta b c\t3"
    assert len(Reject("가", "X\tY", "s", "bad\nreason").tsv().split("\t")) == 4


def test_wiktextract_skips_lines_that_are_not_objects(tmp_path):
    from gukhan.lexicon_build import wiktextract

    path = tmp_path / "w.jsonl"
    path.write_text('["not", "an", "object"]\n"text"\n{"word": "x", "lang_code": "en"}\n{broken\n', encoding="utf-8")
    entries, _, stats = wiktextract.parse(path)
    assert entries == [] and stats.items == 1 and stats.rejected == 3
