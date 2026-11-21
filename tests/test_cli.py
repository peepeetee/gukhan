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


MINI = str(FIX / "mini_lexicon.tsv")


def test_crlf_and_bom_survive_a_round_trip(tmp_path):
    src, out = tmp_path / "in.txt", tmp_path / "out.txt"
    src.write_bytes("﻿대한민국\r\n헌법\r\n".encode())
    assert main([str(src), "-o", str(out), "--lexicon", MINI]) == 0
    assert out.read_bytes().decode("utf-8").replace("\r\n", "|") == "﻿大韓民國|憲法|"


def test_not_utf8_input_is_an_error_not_a_traceback(tmp_path, capsys):
    src = tmp_path / "cp949.txt"
    src.write_bytes("대한민국 헌법".encode("cp949"))
    assert main([str(src), "--lexicon", MINI]) == 2
    assert "not UTF-8" in capsys.readouterr().err


def test_unwritable_output_is_an_error(tmp_path, capsys):
    src = tmp_path / "in.txt"
    src.write_text("대한민국", encoding="utf-8")
    assert main([str(src), "-o", str(tmp_path / "no-such-dir" / "out.txt"), "--lexicon", MINI]) == 2
    assert "cannot write" in capsys.readouterr().err


def test_stdin_is_read_as_utf8(monkeypatch, capsysbinary):
    import io

    class Stdin(io.TextIOWrapper):
        pass

    monkeypatch.setattr("sys.stdin", Stdin(io.BytesIO("대한민국\n".encode()), encoding="cp949", errors="replace"))
    assert main(["--stdin", "--lexicon", MINI]) == 0
    assert capsysbinary.readouterr().out.decode("utf-8") == "大韓民國\n"


def test_override_file_with_bom_and_no_final_newline(tmp_path):
    src, ov, out = tmp_path / "in.txt", tmp_path / "ov.txt", tmp_path / "out.txt"
    src.write_text("대한민국", encoding="utf-8")
    ov.write_bytes("﻿대한민국 = 大韓民國".encode())
    assert main([str(src), "-o", str(out), "--overrides", str(ov), "--lexicon", MINI]) == 0
    assert out.read_text(encoding="utf-8") == "大韓民國"
