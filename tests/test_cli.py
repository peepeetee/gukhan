# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from gukhan.cli import main

FIX = Path(__file__).parent / "fixtures"


def test_usage_errors(tmp_path, capsys):
    assert main([]) == 2
    assert main([str(tmp_path / "missing.md")]) == 2
    assert "file not found" in capsys.readouterr().err


@pytest.mark.kiwi
def test_cli_converts_and_reports(tmp_path, capsys):
    src = tmp_path / "in.md"
    src.write_text("# 제목\n\n대한민국 헌법 제1조. 전기를 읽었다.\n", encoding="utf-8")
    ov = tmp_path / "ov.txt"
    ov.write_text("전기 = 傳記\n", encoding="utf-8")
    out, rep = tmp_path / "out.md", tmp_path / "rep.md"
    rc = main([str(src), "-o", str(out), "--report", str(rep), "--lexicon", str(FIX / "mini_lexicon.tsv")])
    assert rc == 0
    assert out.read_text(encoding="utf-8") == "# 제목\n\n大韓民國 憲法 第1條. 전기를 읽었다.\n"
    assert "| flagged | 3:14 | 전기 |" in rep.read_text(encoding="utf-8")
    rc = main([str(src), "-o", str(out), "--overrides", str(ov), "--lexicon", str(FIX / "mini_lexicon.tsv")])
    assert rc == 0
    assert "傳記를" in out.read_text(encoding="utf-8")
    assert "sample" not in capsys.readouterr().err
