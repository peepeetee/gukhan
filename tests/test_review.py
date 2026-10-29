# SPDX-License-Identifier: Apache-2.0
"""``gukhan review``: a human picks, the override file records, nothing is guessed."""

from gukhan.analyser import ListAnalyser
from gukhan.cli import main as cli_main
from gukhan.convert import Converter, Kind
from gukhan.lexicon import Entry, Lexicon
from gukhan.overrides import Overrides
from gukhan.review import Reviewer, collect

ENTRIES = [
    Entry("국가", "國家", "명사", "t", "나라"),
    Entry("국가", "國歌", "명사", "t", "나라를 상징하는 노래"),
    Entry("안전", "安全", "명사", "t", "위험이 없음"),
    Entry("보장", "保障", "명사", "t", "보호하여 지킴"),
]
LEX = Lexicon(ENTRIES)
TEXT = "국가 안전 보장. 국가를 부른다."
TOKENS = [("국가", "NNG"), ("안전", "NNG"), ("보장", "NNG"), ("국가", "NNG"), ("를", "JKO")]


def reviewer(tmp_path, answers, text=TEXT, tokens=TOKENS):
    it = iter(answers)
    shown: list[str] = []
    path = tmp_path / "my.overrides"
    conv = Converter(LEX, Overrides.load(path) if path.exists() else None, ListAnalyser(tokens))
    r = Reviewer(conv, text, path, input_fn=lambda _p: next(it), output_fn=shown.append)
    return r, path, shown


def lines(path):
    return [x.split("#")[0].strip() for x in path.read_text(encoding="utf-8").splitlines()]


def test_collect_groups_flagged_words_by_frequency():
    r = Converter(LEX, None, ListAnalyser(TOKENS)).convert(TEXT)
    groups = collect(r)
    assert [g.hangul for g in groups] == ["국가"] and len(groups[0].decisions) == 2
    assert [c.hanja for c in groups[0].candidates] == ["國家", "國歌"]


def test_word_choice_is_written_at_once_and_reused(tmp_path):
    r, path, shown = reviewer(tmp_path, ["2"])
    assert r.run() == 0
    assert lines(path) == ["국가 = 國歌"]
    again = Converter(LEX, Overrides.load(path), ListAnalyser(TOKENS)).convert(TEXT)
    assert not again.of(Kind.FLAGGED) and again.text.count("國歌") == 2
    assert any("1) 國家" in x for x in shown) and any("2) 國歌" in x for x in shown)


def test_enter_and_unknown_answers_choose_nothing(tmp_path):
    r, path, shown = reviewer(tmp_path, ["", "9", "x", "q"])
    r.run()
    assert not path.exists()
    assert sum("pick 1" in x or "unknown answer" in x for x in shown) == 3


def test_keep_skip_and_typed_hanja(tmp_path):
    for name in "abc":
        (tmp_path / name).mkdir()
    r, path, _ = reviewer(tmp_path / "a", ["k"])
    r.run()
    assert lines(path) == ["국가 = -"]
    r, path, shown = reviewer(tmp_path / "b", ["漢字漢", "國家"])
    r.run()
    assert lines(path) == ["국가 = 國家"] and any("length differs" in x for x in shown)
    r, path, _ = reviewer(tmp_path / "c", ["s"])
    r.run()
    assert not path.exists()


def test_undo_goes_back_to_the_word_and_removes_its_line(tmp_path):
    text = "국가 안전. 보장 국가."
    lex = Lexicon(ENTRIES[:2] + [Entry("안전", "安全", "명사", "t", "x"), Entry("안전", "安電", "명사", "t", "y")])
    it = iter(["1", "u", "2", "1"])
    path = tmp_path / "o.txt"
    conv = Converter(lex, None, ListAnalyser([("국가", "NNG"), ("안전", "NNG"), ("보장", "NNG"), ("국가", "NNG")]))
    shown: list[str] = []
    r = Reviewer(conv, text, path, input_fn=lambda _p: next(it), output_fn=shown.append)
    r.run()
    assert lines(path) == ["국가 = 國歌", "안전 = 安全"]
    assert any("undone" in x for x in shown)


def test_phrase_scope_resolves_only_that_place(tmp_path):
    r, path, _ = reviewer(tmp_path, ["n1", "q"])
    r.run()
    assert lines(path) == ["국가 안전 = 國家 安全"]
    after = Converter(LEX, Overrides.load(path), ListAnalyser(TOKENS)).convert(TEXT)
    assert after.text.startswith("國家 安全") and len(after.of(Kind.FLAGGED)) == 1


def test_phrase_scope_without_a_neighbour_is_refused(tmp_path):
    r, path, shown = reviewer(tmp_path, ["p1", "q"])
    r.run()
    assert not path.exists() and any("no adjacent word" in x for x in shown)


def test_eof_quits_and_keeps_what_was_saved(tmp_path):
    r, path, shown = reviewer(tmp_path, ["1"], text="국가 안전", tokens=TOKENS[:2])
    r.run()
    assert lines(path) == ["국가 = 國家"] and any("saved" in x for x in shown)


def test_cli_review_runs_end_to_end(tmp_path, monkeypatch, capsys):
    lex = tmp_path / "lexicon.tsv"
    lex.write_text("국가\t國家\t명사\tt\t나라\n국가\t國歌\t명사\tt\t노래\n", encoding="utf-8")
    src = tmp_path / "a.txt"
    src.write_text("국가를 생각한다.", encoding="utf-8")
    ov = tmp_path / "o.txt"
    answers = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda _p="": next(answers))
    assert cli_main(["review", str(src), "--lexicon", str(lex), "--overrides", str(ov)]) == 0
    assert lines(ov) == ["국가 = 國家"]
    assert "saved" in capsys.readouterr().out


def test_spaced_phrase_override_keeps_the_text_spacing():
    ov = Overrides.from_lines(["전기 공학 = 電氣 工學"])
    c = Converter(Lexicon([]), ov, ListAnalyser([("전기", "NNG"), ("공학", "NNG")]))
    assert c.convert("전기 공학").text == "電氣 工學"
