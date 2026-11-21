# SPDX-License-Identifier: Apache-2.0
"""Evidence rules: each narrows a flag's candidates only on evidence, never by how common a word is."""

import pytest

from gukhan import rules
from gukhan.analyser import ListAnalyser
from gukhan.cli import main as cli_main
from gukhan.convert import Converter, Kind
from gukhan.lexicon import Entry, Lexicon
from gukhan.lexicon_build.cli import merge_entries
from gukhan.lexicon_build.stdict import Entry as BuildEntry


def conv(lex, tokens, **kw):
    return Converter(lex, None, ListAnalyser(tokens), **kw)


def test_parse_rules():
    assert rules.parse_rules("default") == rules.DEFAULT
    assert rules.parse_rules("none") == frozenset()
    assert rules.parse_rules("default,verb") == rules.DEFAULT | {"verb"}
    assert rules.parse_rules("all") == rules.ALL
    with pytest.raises(ValueError):
        rules.parse_rules("guess")


WIWON = Lexicon(
    [
        Entry("위원", "委員", "명사", "t", "어떤 일을 위임받아 처리하는 사람"),
        Entry("위원", "渭原", "명사", "t", "평안북도 위원군에 있는 면. 압록강 중류의 굴곡 지대에 있다."),
        Entry("위원", "魏源", "명사", "t", "중국 청나라 말기의 학자(1794~1857). 춘추 공양학을 근간으로 하였다."),
    ]
)


def test_name_filter_drops_person_and_place_for_a_common_noun():
    r = conv(WIWON, [("위원", "NNG")]).convert("위원")
    assert r.text == "委員" and "common noun" in r.decisions[0].reason
    # a proper-noun token keeps all readings, and the rule can be switched off
    assert conv(WIWON, [("위원", "NNP")]).convert("위원").decisions[0].kind == Kind.FLAGGED
    assert conv(WIWON, [("위원", "NNG")], use_rules=frozenset()).convert("위원").decisions[0].kind == Kind.FLAGGED


def test_name_filter_never_empties_the_list():
    lex = Lexicon(
        [
            Entry("위원", "渭原", "명사", "t", "평안북도 위원군에 있는 면."),
            Entry("위원", "魏源", "명사", "t", "학자(1794~1857)."),
        ]
    )
    r = conv(lex, [("위원", "NNG")]).convert("위원")
    assert r.decisions[0].kind == Kind.FLAGGED and len(r.decisions[0].candidates) == 2


LAW = Lexicon(
    [
        Entry("제", "第", "접사", "t", "‘그 숫자에 해당되는 차례’의 뜻을 더하는 접두사."),
        Entry("제", "諸", "접사", "t", "‘여러’의 뜻을 나타내는 접두사."),
        Entry("조", "條", "의존 명사", "t", "내용을 체계적으로 나누어 구분하는 단위의 하나."),
        Entry("조", "組", "의존 명사", "t", "한 벌의 물건을 세는 단위."),
    ]
)


def test_ordinal_prefix_and_numbered_division():
    toks = [("제", "XPN"), ("1", "SN"), ("조", "NNB")]
    r = conv(LAW, toks).convert("제 1 조")
    assert r.text == "第 1 條"
    assert "ordinal prefix" in r.decisions[0].reason and "numbered division" in r.decisions[1].reason
    # outside the 「제 N」 frame a counter stays ambiguous: 2조 may be 組
    r = conv(LAW, [("1", "SN"), ("조", "NNB")]).convert("1 조")
    assert r.decisions[0].kind == Kind.FLAGGED
    # switched off, the prefix is ambiguous too
    assert conv(LAW, toks, use_rules=frozenset()).convert("제 1 조").text == "제 1 조"


VERB = Lexicon(
    [
        Entry("중요", "重要", "명사", "t"),
        Entry("중요", "中夭", "명사", "t"),
        Entry("중요하다", "重要하다", "형용사", "t"),
        Entry("명", "命", "명사", "t"),
        Entry("명", "名", "명사", "t"),
        Entry("명하다", "命하다", "동사", "t"),
        Entry("부", "富", "명사", "t"),
        Entry("부", "附", "명사", "t"),
        Entry("부하다", "富하다", "형용사", "t"),
    ]
)


def test_verb_rule_is_opt_in_and_checks_part_of_speech_and_length():
    toks = [("중요", "NNG"), ("하", "XSA"), ("다", "EF")]
    assert conv(VERB, toks).convert("중요하다").decisions[0].kind == Kind.FLAGGED  # default: no verb rule
    r = conv(VERB, toks, use_rules=rules.parse_rules("verb")).convert("중요하다")
    assert r.text == "重要하다" and "attested as 중요하다" in r.decisions[0].reason
    # 하/XSV wants a 동사 entry; 중요하다 is a 형용사
    r = conv(VERB, [("중요", "NNG"), ("하", "XSV")], use_rules=rules.parse_rules("verb")).convert("중요하")
    assert r.decisions[0].kind == Kind.FLAGGED
    # one syllable stays flagged even when a single verb survives: 附하다 may simply be missing
    r = conv(VERB, [("명", "NNG"), ("하", "XSV")], use_rules=rules.parse_rules("verb")).convert("명하")
    assert r.decisions[0].kind == Kind.FLAGGED and [c.hanja for c in r.decisions[0].candidates] == ["命"]
    r = conv(VERB, [("부", "NNG"), ("하", "XSV")], use_rules=rules.parse_rules("verb")).convert("부하")
    assert r.decisions[0].kind == Kind.FLAGGED and len(r.decisions[0].candidates) == 2  # 富하다 is an adjective


COMPOUND = Lexicon(
    [
        Entry("국무", "國務", "명사", "t"),
        Entry("국무", "國巫", "명사", "t"),
        Entry("위원", "委員", "명사", "t"),
        Entry("위원", "魏源", "명사", "t"),
        Entry("국무위원회", "國務委員會", "명사", "t"),
        Entry("국무위원장", "國務委員長", "명사", "t"),
        Entry("삼일운동", "三一運動", "명사", "t"),
        Entry("삼", "三", "수사", "t"),
        Entry("일", "日", "의존 명사", "t"),
        Entry("운동", "運動", "명사", "t"),
    ]
)


def test_attested_compound_resolves_a_run_inside_longer_headwords():
    toks = [("국무", "NNG"), ("위원", "NNG"), ("과", "JC")]
    r = conv(COMPOUND, toks).convert("국무위원과")
    assert r.text == "國務委員과" and "attested inside 2 longer headword" in r.decisions[0].reason
    # spaced text is not a compact run; the rule is switchable
    assert conv(COMPOUND, toks).convert("국무 위원과").decisions[0].kind == Kind.FLAGGED
    assert conv(COMPOUND, toks, use_rules=frozenset()).convert("국무위원과").decisions[0].kind == Kind.FLAGGED


def test_attested_compound_needs_one_form_and_four_syllables():
    lex = Lexicon(
        [
            Entry("국무위원회", "國務委員會", "명사", "t"),
            Entry("국무위원장", "國務委員長", "명사", "t"),
            Entry("국무위원단", "國巫委員團", "명사", "t"),
        ]
    )
    forms, heads = lex.attested("국무위원")
    assert forms == {"國務委員", "國巫委員"} and heads == 3
    assert lex.attested("국무위") == (set(), 0)
    assert lex.attested("국무위원회") == (set(), 0)  # the headword itself is a lookup, not an attestation


def test_compact_run_may_cross_numeral_and_counter_when_a_headword_matches():
    toks = [("삼", "NR"), ("일", "NNB"), ("운동", "NNG")]
    r = conv(COMPOUND, toks).convert("삼일운동")
    assert r.text == "三一運動"
    # with a space the headword 삼일운동 does not match 「삼 일 운동」
    assert conv(COMPOUND, toks).convert("삼 일 운동").text != "三一運動"


def test_builder_keeps_one_line_per_part_of_speech_group():
    a = [
        BuildEntry("일절", "一切", "명사", "enwikt:일절", "all"),
        BuildEntry("일절", "一切", "부사", "stdict:1", "조금도"),
        BuildEntry("대한민국", "大韓民國", "고유 명사", "enwikt:x", "Korea"),
        BuildEntry("대한민국", "大韓民國", "명사", "stdict:2", "나라"),
        BuildEntry("작전 계획", "作戰 計劃", "품사 없음", "opendict:3", "구"),
        BuildEntry("작전 계획", "作戰 計劃", "명사", "stdict:4", "구"),
    ]
    out = {(e.hangul, e.hanja, e.pos) for e in merge_entries(a)}
    assert ("일절", "一切", "명사") in out and ("일절", "一切", "부사") in out
    assert sum(1 for e in out if e[0] == "대한민국") == 1 and sum(1 for e in out if e[0] == "작전 계획") == 1


def test_builder_keeps_bound_forms_that_the_initial_sound_rule_would_drop():
    a = [
        BuildEntry("연", "年", "명사", "stdict:1"),
        BuildEntry("년", "年", "의존 명사", "stdict:2"),
        BuildEntry("여자", "女子", "명사", "stdict:3"),
        BuildEntry("녀자", "女子", "명사", "stdict:4"),
    ]
    out = {(e.hangul, e.hanja) for e in merge_entries(a)}
    assert ("년", "年") in out and ("녀자", "女子") not in out


def test_cli_rejects_unknown_rule(tmp_path, capsys):
    f = tmp_path / "a.txt"
    f.write_text("국군", encoding="utf-8")
    assert cli_main([str(f), "--rules", "guess"]) == 2


def test_counter_needs_a_number_when_every_reading_is_a_unit():
    lex = Lexicon(
        [
            Entry("일", "日", "의존 명사", "t", "날을 세는 단위."),
            Entry("일", "一", "수사", "t"),
            Entry("항", "項", "의존 명사", "t"),
        ]
    )
    assert conv(lex, [("일", "NNB")]).convert("그 일").decisions == []  # native word 일
    r = conv(lex, [("3", "SN"), ("일", "NNB")]).convert("3일")
    assert r.text == "3日"
    r = conv(lex, [("일", "NNB")], use_rules=frozenset()).convert("일")
    assert r.text == "日"  # switched off
    # a counter whose definition does not call it a unit (前項) keeps converting without a number
    assert conv(lex, [("항", "NNB")]).convert("항").text == "項"


def test_field_rule_drops_specialist_readings_without_evidence():
    lex = Lexicon(
        [
            Entry("보살", "菩薩", "명사", "t", "", domain="불교"),
            Entry("보살", "補殺", "명사", "t", ""),
            Entry("임자", "壬子", "명사", "t", "", domain="민속"),
            Entry("임자", "任者", "명사", "t", ""),
        ]
    )
    # no sign of Buddhism in the text: the reading whose every sense is Buddhist terminology goes
    c = conv(lex, [("임자", "NNG")])
    assert c.convert("임자").text == "任者"
    assert "specialist" in c.convert("임자").decisions[0].reason
    # two settled Buddhist words in the document make 불교 readings believable again
    c.field_evidence = {"민속": 2}
    r = c.convert("임자")
    assert r.decisions[0].kind == Kind.FLAGGED
    # switched off, both readings remain
    assert conv(lex, [("임자", "NNG")], use_rules=frozenset()).convert("임자").decisions[0].kind == Kind.FLAGGED


def test_field_rule_ignores_broad_fields_and_everyday_senses():
    lex = Lexicon(
        [
            Entry("음악", "音樂", "명사", "t", "", domain="음악"),
            Entry("음악", "淫樂", "명사", "t", ""),
            Entry("의원", "議員", "명사", "t", ""),
            Entry("의원", "醫院", "명사", "t", "", domain="한의"),
        ]
    )
    # 음악 labels everyday words too (音樂), so it never counts as a specialist field
    assert conv(lex, [("음악", "NNG")]).convert("음악").decisions[0].kind == Kind.FLAGGED
    assert conv(lex, [("의원", "NNG")]).convert("의원").text == "議員"


def test_field_rule_skips_a_token_glued_to_the_one_before():
    lex = Lexicon(
        [
            Entry("임자", "壬子", "명사", "t", "", domain="민속"),
            Entry("임자", "任者", "명사", "t", ""),
        ]
    )
    # 수임자 split as 수 + 임자: a fragment of a longer word is no evidence of anything
    r = conv(lex, [("수", "NR"), ("임자", "NNG")]).convert("수임자")
    assert r.decisions[-1].kind == Kind.FLAGGED


def test_measured_evidence_comes_from_settled_words_only():
    lex = Lexicon(
        [
            Entry("보살", "菩薩", "명사", "t", "", domain="불교"),
            Entry("염불", "念佛", "명사", "t", "", domain="불교"),
            Entry("임자", "壬子", "명사", "t", "", domain="불교"),
            Entry("임자", "任者", "명사", "t", ""),
        ]
    )
    c = conv(lex, [("보살", "NNG"), ("염불", "NNG"), ("임자", "NNG")])
    c.set_document(["보살 염불 임자"])
    assert c.field_evidence["불교"] == 2
    assert c.convert("보살 염불 임자").decisions[-1].kind == Kind.FLAGGED


SENSE_LEX = Lexicon(
    [
        Entry("의결", "議決", "명사", "t", "의논하여 결정함. 의안이나 안건을 토의하여 결정함"),
        Entry("의결", "疑結", "명사", "t", "인과를 의심하는 마음에서 일어나는 번뇌."),
    ]
)


def test_sense_rule_needs_two_shared_nouns_and_a_margin():
    toks = [("의안", "NNG"), ("안건", "NNG"), ("의결", "NNG"), (".", "SF")]
    r = conv(SENSE_LEX, toks).convert("의안 안건 의결.")
    assert "議決" in r.text and "definition shares" in r.decisions[-1].reason
    # one shared noun is not enough
    r = conv(SENSE_LEX, [("의안", "NNG"), ("의결", "NNG")]).convert("의안 의결")
    assert r.decisions[-1].kind == Kind.FLAGGED
    # the noun must be in the same sentence
    r = conv(SENSE_LEX, [("의안", "NNG"), ("안건", "NNG"), (".", "SF"), ("의결", "NNG")]).convert("의안 안건. 의결")
    assert r.decisions[-1].kind == Kind.FLAGGED
    # switched off
    r = conv(SENSE_LEX, toks, use_rules=frozenset()).convert("의안 안건 의결.")
    assert r.decisions[-1].kind == Kind.FLAGGED
