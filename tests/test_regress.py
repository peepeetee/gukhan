# SPDX-License-Identifier: Apache-2.0

from gukhan.analyser import ListAnalyser
from gukhan.convert import Converter
from gukhan.lexicon import Entry, Lexicon
from gukhan.regress import prepare as prep
from gukhan.regress import score as sc
from gukhan.regress.cli import main

CHARS = {
    "大": ["대"], "韓": ["한"], "民": ["민"], "國": ["국"], "은": ["은"], "主": ["주"], "共": ["공"], "和": ["화"],
    "歷": ["력"], "史": ["사"], "不": ["부", "불"], "動": ["동"], "正": ["정"], "法": ["법"], "律": ["률"],
    "樂": ["락", "악", "요"], "園": ["원"], "女": ["녀"], "子": ["자"],
}  # fmt: skip


def test_prepare_readings_and_initial_rule():
    p = prep.prepare("大韓民國은 民主共和國이다. 歷史와 法律, 女子", CHARS)
    assert p.hangul == "대한민국은 민주공화국이다. 역사와 법률, 여자"
    assert p.flags == [] and p.unknown == []


def test_prepare_multi_reading_preference_and_flags():
    p = prep.prepare("不動 不正 樂園 X", CHARS)
    assert p.hangul == "부동 부정 낙원 X"  # 不 → 부 before ㄷ/ㅈ; 樂 default 락 → 낙 word-initially
    assert p.flags == []
    p = prep.prepare("不法", CHARS)
    assert p.hangul == "불법"
    p = prep.prepare("韓國 龍", CHARS)
    assert p.unknown == ["龍"] and p.hangul == "한국 龍"


def test_prepare_flags_unlisted_multi_reading():
    chars = {"降": ["강", "항"], "雨": ["우"], "X": ["ㄱ"]}
    chars["Z"] = ["자", "차"]
    p = prep.prepare("降雨", chars)
    assert p.hangul == "강우" and not p.flags  # PREFER table
    p = prep.prepare("金", {"金": ["김", "금"]})
    assert p.hangul == "금" and not p.flags
    p = prep.prepare("殺", {"殺": ["쇄", "살"]})
    assert p.hangul == "살"
    p = prep.prepare("Q", {"Q": ["a"]})  # not CJK: passthrough
    assert p.hangul == "Q"


def test_split_sentences():
    assert prep.split_sentences("第1條 大韓民國은 民主共和國이다.\n第2條 大韓民國의 主權은 國民에게 있다.\n\n附則") == [
        "第1條 大韓民國은 民主共和國이다.",
        "第2條 大韓民國의 主權은 國民에게 있다.",
        "附則",
    ]


LEX = Lexicon(
    [
        Entry("대한민국", "大韓民國", "명사", "t"),
        Entry("민주", "民主", "명사", "t"),
        Entry("공화국", "共和國", "명사", "t"),
        Entry("역사", "歷史", "명사", "t"),
        Entry("역사", "役事", "명사", "t"),
        Entry("국민", "國民", "명사", "t"),
        Entry("사과", "沙果", "명사", "t"),
    ]
)


def test_score_counts():
    items = [
        sc.Item("a", "t", "대한민국은 민주공화국이다", "大韓民國은 民主共和國이다"),
        sc.Item("b", "t", "역사와 국민", "歷史와 國民"),
        sc.Item("c", "t", "사과를 먹었다", "사과를 먹었다"),
    ]
    tokens = [
        ("대한민국", "NNP"),
        ("민주", "NNG"),
        ("공화국", "NNG"),
        ("역사", "NNG"),
        ("국민", "NNG"),
        ("사과", "NNG"),
    ]
    conv = Converter(LEX, None, ListAnalyser(tokens))
    t = sc.score(items, conv)
    assert (t.right, t.partial, t.flagged, t.wrong, t.over, t.misaligned) == (3, 0, 1, 0, 1, 0)
    # 民主共和國 is one gold run but two lexicon words: still counted as one right word
    d = t.as_dict()
    assert d["words"] == 4 and d["right_pct"] == 75.0
    assert (d["chars"], d["chars_right"], d["chars_flagged"]) == (13, 11, 2)


def test_score_partial_and_variants():
    t = sc.Tally()
    sc.score_item(sc.Item("a", "t", "대한국민", "大韓國民"), "대한國民", t)
    assert (t.right, t.partial, t.flagged, t.wrong) == (0, 1, 0, 0) and t.chars_right == 2
    sc.score_item(sc.Item("b", "t", "강제", "强制"), "強制", t)
    assert t.right == 1
    sc.score_item(sc.Item("c", "t", "계승", "繼承"), "階乘", t)
    assert t.wrong == 1 and t.chars_wrong == 2


def test_cli_prepare_and_score(tmp_path):
    chars = tmp_path / "chars.tsv"
    chars.write_text(
        "# hanja\treadings\n" + "".join(f"{k}\t{' '.join(v)}\n" for k, v in CHARS.items()), encoding="utf-8"
    )
    text = tmp_path / "gold.txt"
    text.write_text("第1條 大韓民國은 民主共和國이다.\n歷史와 不法.\n", encoding="utf-8")
    out = tmp_path / "items.tsv"
    assert main(["prepare", str(text), "--chars", str(chars), "--source", "t", "-o", str(out)]) == 0
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    assert lines[0].startswith("t-0001\tt\t第1條 대한민국은 민주공화국이다.\t第1條")  # 第/條 unknown → kept as is
    assert "불법" in lines[1]
    assert main(["score", str(out)]) == 0
    assert main(["prepare", str(tmp_path / "nope.txt"), "--chars", str(chars), "--source", "t", "-o", str(out)]) == 2


def test_lexicon_words_prefer_standard_spelling(tmp_path):
    lex = tmp_path / "lexicon.tsv"
    lex.write_text(
        "력사\t歷史\t명사\tt\thistory\t11\n역사\t歷史\t명사\tt\thistory\t18\n"
        "령토\t領土\t명사\tt\t\t11\n영토\t領土\t명사\tt\t\t11\n규률\t規律\t명사\tt\t\t11\n규율\t規律\t명사\tt\t\t12\n",
        encoding="utf-8",
    )
    words = prep.load_lexicon_hanja(lex)
    assert words == {"歷史": "역사", "領土": "영토", "規律": "규율"}


def test_prepare_with_lexicon_words_and_edu_tags(tmp_path):
    chars_file = tmp_path / "chars.tsv"
    chars_file.write_text(
        "# hanja\treadings\n責\t책:0E 채:1N\n任\t임:0E\n年\t년:0E 연:1N\n强\t강:0E\n制\t제:0E\n勞\t로:0E\n役\t역:0E\n"
        "行\t행:0E 항:0N\n歷\t력:0E\n史\t사:0E\n",
        encoding="utf-8",
    )
    chars = prep.load_chars(chars_file)
    assert chars.readings["責"] == ["책", "채"] and chars.edu["責"] == 1
    p = prep.prepare("責任 4281年 行", chars)
    assert p.hangul == "책임 4281년 행" and p.flags == []
    # compound: without words 勞 stays 로 mid-run; with the lexicon word 勞役 it starts a segment
    assert prep.prepare("强制勞役", chars).hangul == "강제로역"
    words = {"强制": "강제", "勞役": "노역", "歷史": "역사"}
    assert prep.prepare("强制勞役 歷史", chars, words).hangul == "강제노역 역사"


def test_strip_annotations_and_split():
    text = "②參議院議員의 任期는 六年으로 한다.<개정 1954.11.29> 다음 條.[전문개정 1962.12.26]"
    assert prep.strip_annotations(text) == "②參議院議員의 任期는 六年으로 한다. 다음 條."
    assert prep.split_sentences(text) == ["②參議院議員의 任期는 六年으로 한다.", "다음 條."]


def test_variant_glyph_takes_standard_reading():
    chars = {"亡": ["망"], "共": ["공"]}
    p = prep.prepare("共兦", chars)
    assert p.hangul == "공망"
    assert p.unknown == []
    assert sc.fold_variants("共兦") == sc.fold_variants("共亡")
    assert sc.fold_variants("萬二千峯") == sc.fold_variants("萬二千峰")


def test_in_candidates_counts_offered_hanja():
    lex = Lexicon(
        [
            Entry("전기", "電氣", "명사", "t"),
            Entry("전기", "傳記", "명사", "t"),
            Entry("사과", "沙果", "명사", "t"),
            Entry("사과", "謝過", "명사", "t"),
        ]
    )
    conv = Converter(lex, None, ListAnalyser([("전기", "NNG"), ("사과", "NNG")]))
    items = [
        sc.Item("a", "t", "전기", "傳記"),  # flagged, but the gold Hanja is offered
        sc.Item("b", "t", "사과", "賜課"),  # flagged, gold not among the candidates
    ]
    t = sc.score(items, conv)
    assert (t.flagged, t.right, t.wrong, t.in_candidates) == (2, 0, 0, 1)
    assert t.as_dict()["in_candidates_pct"] == 50.0


def test_score_reports_missing_files_and_reads_a_bom(tmp_path, capsys):
    assert main(["score", str(tmp_path / "missing.tsv")]) == 2
    assert "file not found" in capsys.readouterr().err
    items = tmp_path / "items.tsv"
    items.write_bytes("﻿a-1\ta\t대한민국\t大韓民國\n".encode())
    assert main(["score", str(items), "--lexicon", str(tmp_path / "missing-lexicon.tsv")]) == 2
    assert main(["score", str(items)]) == 0
    assert "items=1" in capsys.readouterr().out
