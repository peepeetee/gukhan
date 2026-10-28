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
    assert (t.right, t.flagged, t.wrong, t.over, t.misaligned) == (3, 1, 0, 1, 0)
    # 民主共和國 is one gold run but two lexicon words: still counted as one right word
    d = t.as_dict()
    assert d["words"] == 4 and d["right_pct"] == 75.0


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
