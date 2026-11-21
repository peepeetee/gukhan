# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from gukhan.lexicon import Lexicon
from gukhan.lexicon_build import lawgloss
from gukhan.lexicon_build.cli import main

FIX = Path(__file__).parent / "fixtures"
HEAD = "---\n제목: 시험법\n상태: 시행\n---\n"


def make_repo(tmp_path):
    kr = tmp_path / "repo" / "kr"
    for name, body in {
        "가법": "제1조 이 법은 작전(作戰)과 가감(加減)을 정한다. 전기(電氣)는 \\(그대로\\) 둔다.",
        "나법": "제2조 작전(作戰)을 한다. 책(冊)과 이론(理的)은 쓰지 않는다. 일곱자소속전기(電氣)",
        "다법": "제3조 작전(作戰)과 전기(傳記)와 소속기관(機關)",
    }.items():
        (kr / name).mkdir(parents=True)
        (kr / name / "법률.md").write_text(HEAD + body + "\n", encoding="utf-8")
    old = kr / "폐법"
    old.mkdir()
    (old / "법률.md").write_text("---\n상태: 폐지\n---\n폐지(廢止)된 작전(作戰)\n", encoding="utf-8")
    return tmp_path / "repo"


def test_gloss_pairs_take_the_last_syllables():
    got = list(lawgloss.gloss_pairs("소속기관(機關) 과(科) 분사무소\\(分事務所\\) 개(開議)"))
    assert got == [
        ("소속기관", "기관", "機關"),
        ("과", "과", "科"),
        ("분사무소", "분사무소", "分事務所"),
        ("개", "", "開議"),
    ]


def test_parse_counts_statutes_and_validates_readings(tmp_path):
    from gukhan.lexicon_build import unihan

    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    entries, rejects, stats = lawgloss.parse(make_repo(tmp_path), readings)
    assert stats.items == 4 and stats.repealed == 1
    assert stats.pairs[("작전", "作戰")] == (3, 3)  # the repealed statute is not read
    assert stats.pairs[("전기", "電氣")] == (2, 2)
    assert ("책", "冊") not in stats.pairs and stats.single == 1
    assert ("이론", "理的") not in stats.pairs
    assert any("理的" in r.raw_hanja or r.raw_hanja == "理的" for r in rejects)
    # 機關 has no reading in the tiny fixture: rejected rather than guessed
    assert ("기관", "機關") not in stats.pairs
    e = {(x.hangul, x.hanja): x for x in entries}
    assert e[("작전", "作戰")].domain == "법률" and e[("작전", "作戰")].weight == 0
    assert e[("작전", "作戰")].source.startswith("law:")


def test_pairs_tsv_and_override_lines(tmp_path):
    _, _, stats = lawgloss.parse(make_repo(tmp_path))
    rows = lawgloss.pairs_tsv(stats).splitlines()
    assert rows[1].startswith("작전\t作戰\t3\t3\t1.00")
    assert "전기\t傳記\t1\t1\t0.33" in rows
    assert lawgloss.override_lines(stats) == ["작전 = 作戰"]  # 電氣/傳記 split the votes, 3 statutes needed
    assert lawgloss.override_lines(stats, min_statutes=2, min_share=0.6) == ["작전 = 作戰", "전기 = 電氣"]


def test_pairs_in_items_and_exclusion(tmp_path):
    items = tmp_path / "items.tsv"
    items.write_text("# h\nx-1\tx\t법인이 작전을 한다\t법인이 作戰을 한다\n", encoding="utf-8")
    assert lawgloss.pairs_in_items(items) == {("작전", "作戰")}
    _, _, stats = lawgloss.parse(make_repo(tmp_path), exclude=lawgloss.pairs_in_items(items))
    assert ("작전", "作戰") not in stats.pairs and stats.excluded == 3


def test_builder_adds_only_missing_words_and_writes_side_files(tmp_path):
    repo, out = make_repo(tmp_path), tmp_path / "out"
    args = ["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(FIX / "Unihan_Readings.txt")]
    assert main([*args, "--law-glosses", str(repo), "-o", str(out)]) == 0
    lex = Lexicon.load(out / "lexicon.tsv")
    assert any(c.hanja == "作戰" and c.source.startswith("law:") for c in lex.candidates("작전"))
    assert not any(c.source.startswith("law:") for c in lex.candidates("전기"))  # stdict knows 전기 already
    assert (out / "law-glosses.tsv").read_text(encoding="utf-8").startswith("# hangul")
    assert (out / "law-overrides.txt").read_text(encoding="utf-8").startswith("#")
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "law.go.kr" in m["notice"] and m["sources"]["law_glosses"]["kind"] == "directory"
    assert m["licence"] == "CC-BY-SA-2.0-KR"  # public-work statutes add no share-alike term
    plain = tmp_path / "plain"
    assert main([*args, "-o", str(plain)]) == 0
    assert "law_glosses" not in json.loads((plain / "manifest.json").read_text(encoding="utf-8"))["counts"]


def test_law_glosses_alone_or_missing_are_errors(tmp_path):
    repo = make_repo(tmp_path)
    assert main(["--law-glosses", str(repo), "-o", str(tmp_path / "o")]) == 2
    args = ["--stdict", str(FIX / "stdict_sample.xml")]
    assert main([*args, "--law-glosses", str(tmp_path / "missing"), "-o", str(tmp_path / "o")]) == 2
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main([*args, "--law-glosses", str(empty), "-o", str(tmp_path / "o")]) == 2


def test_compatibility_ideographs_are_folded():
    assert list(lawgloss.gloss_pairs("역(\uf98b)")) == [("역", "역", "曆")]
