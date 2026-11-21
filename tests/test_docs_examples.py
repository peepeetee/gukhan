# SPDX-License-Identifier: Apache-2.0
"""The commands and outputs in docs/overrides-and-review.md are run here, so the guide cannot go stale."""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from gukhan import cli

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "overrides-and-review.md").read_text(encoding="utf-8")
INPUT = ROOT / "docs" / "examples" / "input.txt"
LEXICON = ROOT / "docs" / "examples" / "lexicon.tsv"


def run(capsys, *argv: str) -> str:
    assert cli.main([str(a) for a in argv]) == 0
    captured = capsys.readouterr()
    return (captured.out + captured.err).rstrip("\n")


def assert_in_doc(text: str) -> None:
    for line in text.splitlines():
        if line.strip() and not line.startswith("> "):
            assert line.strip() in DOC, f"not in the guide: {line!r}"


def test_the_example_input_is_the_one_shown():
    assert INPUT.read_text(encoding="utf-8").strip() in DOC


def test_mark_output(capsys):
    assert_in_doc(run(capsys, INPUT, "--lexicon", LEXICON, "--mark"))


def test_hand_written_override_file(capsys, tmp_path):
    by_hand = tmp_path / "by-hand.txt"
    by_hand.write_text("의사 = 醫師\n전기 공학 = 電氣 工學\n이순신 = 李舜臣\n", encoding="utf-8")
    assert by_hand.read_text(encoding="utf-8").strip() in DOC
    assert_in_doc(run(capsys, INPUT, "--lexicon", LEXICON, "--overrides", by_hand, "--mark"))


def test_too_short_hanja_is_refused(capsys, tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("의사 = 醫\n", encoding="utf-8")
    assert cli.main([str(INPUT), "--lexicon", str(LEXICON), "--overrides", str(bad)]) == 2
    assert "line 1" in capsys.readouterr().err


def answer(monkeypatch, *typed: str) -> None:
    it = iter(typed)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(it))


def test_review_session_and_follow_up(capsys, monkeypatch, tmp_path):
    mine = tmp_path / "my.txt"
    answer(monkeypatch, "n2", "2", "李舜臣")
    rc = cli.main(["review", str(INPUT), "--lexicon", str(LEXICON), "--overrides", str(mine), "--include-review"])
    assert rc == 0
    out = capsys.readouterr().out
    assert_in_doc(out.replace(str(mine), "my.txt"))
    assert mine.read_text(encoding="utf-8").splitlines() == [
        "전기 공학 = 電氣 工學  # review: phrase, n",
        "의사 = 醫師  # review: word",
        "이순신 = 李舜臣  # review: typed",
    ]
    assert_in_doc(mine.read_text(encoding="utf-8"))

    answer(monkeypatch, "k")
    assert cli.main(["review", str(INPUT), "--lexicon", str(LEXICON), "--overrides", str(mine)]) == 0
    assert_in_doc(capsys.readouterr().out.replace(str(mine), "my.txt"))
    assert_in_doc(run(capsys, INPUT, "--lexicon", LEXICON, "--overrides", mine))

    mine.write_text(mine.read_text(encoding="utf-8") + "전기 연구 = 電氣 研究\n", encoding="utf-8")
    assert "醫師의 電氣 研究." in run(capsys, INPUT, "--lexicon", LEXICON, "--overrides", mine)
    assert "醫師의 電氣 研究." in DOC


@pytest.mark.parametrize("name", ["input.txt", "lexicon.tsv"])
def test_example_files_exist(name):
    assert (ROOT / "docs" / "examples" / name).is_file()
