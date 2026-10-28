# SPDX-License-Identifier: Apache-2.0
import pytest

from gukhan.analyser import ListAnalyser
from gukhan.convert import Converter, Kind
from gukhan.lexicon import Entry, Lexicon
from gukhan.overrides import Overrides
from gukhan.segments import segment

LEX = Lexicon(
    [
        Entry("전기", "電氣", "명사", "t", "electricity"),
        Entry("전기", "傳記", "명사", "t", "biography"),
        Entry("전기 공학", "電氣 工學", "명사", "t"),
        Entry("공학", "工學", "명사", "t"),
        Entry("국군", "國軍", "명사", "t"),
        Entry("약", "藥", "명사", "t"),
        Entry("약", "約", "부사", "t"),
        Entry("조", "條", "의존 명사", "t"),
        Entry("제", "第", "접두사", "t"),
        Entry("감사", "感謝", "명사", "t"),
        Entry("감사", "感謝", "명사", "t2"),  # same Hanja, two sources
    ]
)


def conv(tokens, overrides=None, **kw):
    return Converter(LEX, overrides, ListAnalyser(tokens), **kw)


def test_single_entry_converts_and_endings_stay():
    c = conv([("국군", "NNG"), ("은", "JX"), ("공학", "NNG"), ("을", "JKO")])
    r = c.convert("국군은 공학을")
    assert r.text == "國軍은 工學을"
    assert [d.kind for d in r.decisions] == [Kind.CONVERTED, Kind.CONVERTED]


def test_homograph_is_flagged_not_guessed():
    c = conv([("전기", "NNG"), ("를", "JKO")])
    r = c.convert("전기를")
    assert r.text == "전기를"
    assert r.decisions[0].kind == Kind.FLAGGED
    assert {e.hanja for e in r.decisions[0].candidates} == {"電氣", "傳記"}
    assert c.convert("전기를", mark=True).text == "전기{電氣|傳記}를"


def test_longest_match_phrase_resolves_homograph():
    c = conv([("전기", "NNG"), ("공학", "NNG"), ("을", "JKO")])
    assert c.convert("전기 공학을").text == "電氣 工學을"
    assert c.convert("전기공학을").text == "電氣工學을"


def test_override_wins_and_keep():
    ov = Overrides.from_lines(["전기 = 傳記", "국군 = -", "장군 = 將軍"])
    c = conv([("전기", "NNG"), ("국군", "NNG"), ("장군", "NNG")], ov)
    r = c.convert("전기 국군 장군")
    assert r.text == "傳記 국군 將軍"
    assert r.decisions[1].kind == Kind.KEPT


def test_pos_filter_disambiguates():
    c = conv([("약", "MAG"), ("약", "NNG"), ("을", "JKO")])
    r = c.convert("약 약을")
    assert r.text == "約 藥을"
    assert "POS filter" in r.decisions[0].reason


def test_identical_candidates_agree():
    c = conv([("감사", "NNG")])
    r = c.convert("감사")
    assert r.text == "感謝" and r.decisions[0].reason == "all candidates agree"


def test_proper_noun_without_entry_goes_to_review():
    c = conv([("홍길동", "NNP"), ("이", "JKS"), ("사람", "NNG")])
    r = c.convert("홍길동이 사람")
    assert r.text == "홍길동이 사람"
    assert [d.kind for d in r.decisions] == [Kind.REVIEW]
    r2 = conv([("홍길동", "NNP"), ("이", "JKS"), ("사람", "NNG")], review_all=True).convert("홍길동이 사람")
    assert [d.hangul for d in r2.decisions] == ["홍길동", "사람"]


def test_protected_segments():
    text = "국군 `국군` http://a.b/국군 <b>국군</b>\n```\n국군\n```\n국군"
    segs = segment(text)
    assert sum(1 for s in segs if s.protected) == 5
    c = Converter(LEX, None, ListAnalyser([("국군", "NNG")] * 2))
    out = c.convert(text).text
    assert out == "國軍 `국군` http://a.b/국군 <b>國軍</b>\n```\n국군\n```\n國軍"


def test_token_form_mismatch_is_skipped():
    # analyser normalised the form; the original text must stay untouched
    c = Converter(LEX, None, ListAnalyser([("국군", "NNG")]))
    assert c.convert("국군").text == "國軍"
    assert c.convert("國軍").decisions == []


def test_override_file_errors():
    with pytest.raises(ValueError):
        Overrides.from_lines(["전기 = 電"])
    with pytest.raises(ValueError):
        Overrides.from_lines(["전기"])


def test_lexicon_tsv_errors():
    with pytest.raises(ValueError):
        Lexicon.from_lines(["전기\t電"])
    assert len(Lexicon.sample()) > 200


@pytest.mark.kiwi
def test_real_kiwi_end_to_end():
    from gukhan.convert import convert

    r = convert("국군은 작전 계획을 수립하였다. 그는 전기를 읽고 전기 공학을 공부했다.")
    assert r.text == "國軍은 作戰 計劃을 樹立하였다. 그는 전기를 읽고 電氣 工學을 工夫했다."
    assert [d.hangul for d in r.of(Kind.FLAGGED)] == ["전기"]
