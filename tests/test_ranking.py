# SPDX-License-Identifier: Apache-2.0
from gukhan.convert import rank
from gukhan.lexicon import Entry, Lexicon
from gukhan.lexicon_build.ranking import krdict_levels, learner_ranks


def test_exact_forms_only(tmp_path):
    xml = tmp_path / "levels.xml"
    xml.write_text(
        """<Lexicon><LexicalEntry>
      <Lemma><feat att="writtenForm" val="전기"/></Lemma>
      <feat att="origin" val="電氣"/><feat att="vocabularyLevel" val="초급"/>
      <Sense><feat att="origin" val="傳記"/><feat att="definition" val="bad\x08control"/></Sense>
    </LexicalEntry></Lexicon>""",
        encoding="utf-8",
    )
    assert krdict_levels(xml) == {("전기", "電氣"): 3}
    learner = tmp_path / "learner.txt"
    learner.write_bytes("10\t전기01\t명\t電氣\tA\n20\t전기02\t명\t책의 ~\tB\n".encode("cp949"))
    assert learner_ranks(learner) == {("전기", "電氣"): 10}


def test_ranking_preserves_primary_weight_and_roundtrips():
    entries = [Entry("전기", "傳記", weight=11), Entry("전기", "電氣", weight=10, level=3, learner_rank=10)]
    assert rank(entries)[0].hanja == "傳記"
    entries[0] = Entry("전기", "傳記", weight=10)
    assert rank(entries)[0].hanja == "電氣"
    lex = Lexicon.from_lines(["전기\t電氣\t명사\ttest\t\t10\t3\t10"])
    assert lex.candidates("전기")[0].level == 3
    assert Lexicon.from_lines(["전기\t電氣"]).candidates("전기")[0].level == 0
