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
    assert c.convert("전기를", mark=True).text == "전기{傳記|電氣}를"


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
    # the adverb converts via the POS filter; the one-syllable noun on a lone entry is flagged, not written
    assert r.text == "約 약을"
    assert "POS filter" in r.decisions[0].reason
    assert r.decisions[1].kind == Kind.FLAGGED and [e.hanja for e in r.decisions[1].candidates] == ["藥"]


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


def test_no_phrase_match_across_space_for_determiner():
    lex = Lexicon(
        [Entry("세시", "歲時", "명사", "t"), Entry("세시", "細視", "명사", "t"), Entry("시", "時", "의존 명사", "t")]
    )
    c = Converter(lex, None, ListAnalyser([("오후", "NNG"), ("세", "MM"), ("시", "NNB")]))
    r = c.convert("오후 세 시")
    assert r.text == "오후 세 時"
    assert [d.hangul for d in r.decisions] == ["시"]


def test_spaced_span_needs_spaced_entry():
    lex = Lexicon([Entry("세시", "歲時", "명사", "t"), Entry("작전 계획", "作戰 計劃", "명사", "t")])
    c = Converter(lex, None, ListAnalyser([("세", "NNG"), ("시", "NNG"), ("작전", "NNG"), ("계획", "NNG")]))
    assert c.convert("세 시 작전 계획").text == "세 시 作戰 計劃"
    assert c.convert("세시 작전계획").text == "歲時 作戰計劃"


def test_flag_candidates_are_ranked():
    lex = Lexicon(
        [
            Entry("역사", "繹史", "고유 명사", "t", "a Qing history book"),
            Entry("역사", "歷史", "명사", "t", "history"),
            Entry("역사", "役事", "명사", "t"),
        ]
    )
    r = Converter(lex, None, ListAnalyser([("역사", "NNG")])).convert("역사")
    # the proper noun is dropped by the POS filter for an NNG token; glossed entry first
    assert [e.hanja for e in r.decisions[0].candidates] == ["歷史", "役事"]
    r = Converter(lex, None, ListAnalyser([("역사", "NNP")])).convert("역사")
    assert [e.hanja for e in r.decisions[0].candidates] == ["歷史", "繹史", "役事"]


def test_native_numeral_and_counter_not_flagged():
    lex = Lexicon(
        [
            Entry("세", "世", "명사", "t"),
            Entry("세", "歲", "명사", "t"),
            Entry("시", "市", "명사", "t"),
            Entry("시", "時", "명사", "t"),
            Entry("각", "各", "관형사", "t"),
        ]
    )
    c = Converter(lex, None, ListAnalyser([("오후", "NNG"), ("세", "MM"), ("시", "NNB"), ("각", "MM"), ("시", "NNG")]))
    r = c.convert("오후 세 시 각 시")
    # noun readings do not fit MM/NNB, so the numeral and counter are left alone, not flagged
    assert r.text == "오후 세 시 各 시"
    assert [(d.hangul, d.kind) for d in r.decisions] == [("각", Kind.CONVERTED), ("시", Kind.FLAGGED)]


def test_weight_orders_candidates():
    lex = Lexicon([Entry("역사", "役事", "명사", "t", "work", 1), Entry("역사", "歷史", "명사", "t", "history", 12)])
    r = Converter(lex, None, ListAnalyser([("역사", "NNG")])).convert("역사")
    assert [e.hanja for e in r.decisions[0].candidates] == ["歷史", "役事"]


def test_native_bound_noun_never_converted():
    lex = Lexicon([Entry("수", "首", "의존 명사", "t"), Entry("수", "數", "명사", "t")])
    c = Converter(lex, None, ListAnalyser([("할", "VV"), ("수", "NNB"), ("있", "VA"), ("수", "NNG")]))
    r = c.convert("할 수 있다 수")
    # the bound noun is skipped outright; the NNG 수 is a real 首/數 homograph and is flagged
    assert r.text == "할 수 있다 수"
    assert [(d.start, d.kind) for d in r.decisions] == [(7, Kind.FLAGGED)]


def test_native_homograph_entry_flags():
    lex = Lexicon([Entry("안", "案", "명사", "t", "plan", 12), Entry("안", "안", "명사", "t", "inside", 13)])
    c = Converter(lex, None, ListAnalyser([("안", "NNG")]))
    r = c.convert("안")
    assert r.decisions[0].kind == Kind.FLAGGED
    assert c.convert("안", mark=True).text == "안{안|案}"
    only_native = Lexicon([Entry("안", "안", "명사", "t", "inside", 13)])
    assert Converter(only_native, None, ListAnalyser([("안", "NNG")])).convert("안").decisions == []


def test_min_weight_flags_rare_single_entry():
    lex = Lexicon(
        [Entry("계승", "階乘", "명사", "t", "factorial", 11), Entry("국민", "國民", "명사", "t", "people", 14)]
    )
    assert lex.weighted
    c = Converter(lex, None, ListAnalyser([("계승", "NNG"), ("국민", "NNG")]), min_weight=12)
    r = c.convert("계승 국민")
    assert r.text == "계승 國民"
    assert r.decisions[0].kind == Kind.FLAGGED and "weight below 12" in r.decisions[0].reason
    c0 = Converter(lex, None, ListAnalyser([("계승", "NNG"), ("국민", "NNG")]))  # default: cutoff off
    assert c0.convert("계승 국민").text == "階乘 國民"
    unweighted = Lexicon([Entry("계승", "階乘", "명사", "t")])
    assert Converter(unweighted, None, ListAnalyser([("계승", "NNG")])).convert("계승").text == "階乘"


def test_single_syllable_lone_entry_is_flagged():
    lex = Lexicon(
        [Entry("전", "全", "명사", "t"), Entry("항", "項", "의존 명사", "t"), Entry("제", "第", "접두사", "t")]
    )
    c = Converter(lex, None, ListAnalyser([("전", "NNG"), ("항", "NNB"), ("제", "XPN"), ("1", "SN"), ("항", "NNB")]))
    r = c.convert("전항 제1항")
    assert r.text == "전項 第1項"
    assert r.decisions[0].kind == Kind.FLAGGED and "single syllable" in r.decisions[0].reason


def test_kiwi_analyser_selects_cong_explicitly(monkeypatch):
    """Reproducibility: the Kiwi language model is named, never Kiwi's "fastest available" default."""
    import sys
    import types

    from gukhan.analyser import KIWI_MODEL_TYPE, KiwiAnalyser

    calls = {}

    class FakeKiwi:
        def __init__(self, model_type=None):
            calls["model_type"] = model_type
            self.model_type = model_type

        def tokenize(self, text):
            return []

    monkeypatch.setitem(sys.modules, "kiwipiepy", types.SimpleNamespace(Kiwi=FakeKiwi, __version__="0.0.0-test"))
    analyser = KiwiAnalyser()
    assert analyser.tokenize("연구") == []
    assert calls["model_type"] == KIWI_MODEL_TYPE == "cong"
    assert analyser.describe() == "kiwipiepy 0.0.0-test, model cong"


@pytest.mark.parametrize(
    "text, protected",
    [
        ("- 항목\n  ```\n  국군\n  ```\n국군", ["  ```\n  국군\n  ```"]),  # fence inside a list item
        ("````\n국군\n`````\n국군", ["````\n국군\n`````"]),  # closing fence longer than the opening one
        ("```\n국군\n``` x\n국군", ["```\n국군\n``` x\n국군"]),  # a closing fence carries no info string: still open
        ("~~~\n국군\n~~~\n국군", ["~~~\n국군\n~~~"]),
        ("국군\n```\n국군\n국군", ["```\n국군\n국군"]),  # unclosed fence protects to the end
        ("``a`국군`` 국군", ["``a`국군``"]),  # double-backtick inline code containing a backtick
        ("```국군``` 국군", ["```국군```"]),  # inline, not a fence
        ("국군 [국군](문서/국군.md) ![국군](국군.png)", ["(문서/국군.md)", "(국군.png)"]),
        ("연락처는국군@example.com 국군", []),  # non-ASCII before @ is not an address
        ("연락처 a.b@example.co.kr 국군", ["a.b@example.co.kr"]),
    ],
)
def test_segment_protection(text, protected):
    got = [text[s.start : s.end] for s in segment(text) if s.protected]
    assert got == protected


def test_indented_fence_is_not_converted():
    c = Converter(LEX, None, ListAnalyser([("국군", "NNG")] * 3))
    text = "국군\n  ```\n  국군\n  ```\n국군"
    assert c.convert(text).text == "國軍\n  ```\n  국군\n  ```\n國軍"
