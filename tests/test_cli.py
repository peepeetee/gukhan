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


def test_report_rows_stay_on_one_line_with_crlf_and_tabs():
    from gukhan.analyser import ListAnalyser
    from gukhan.convert import Converter
    from gukhan.lexicon import Entry, Lexicon
    from gukhan.report import to_markdown, to_tsv

    lex = Lexicon([Entry("전기", "電氣", "명사", "t", "a|b"), Entry("전기", "傳記", "명사", "t", "line\nbreak")])
    text = "앞\r\n줄\t전기\r\n뒤"
    result = Converter(lex, None, ListAnalyser([("전기", "NNG")])).convert(text)
    tsv = to_tsv(text, result)
    assert "\r" not in tsv and all(len(row.split("\t")) == 6 for row in tsv.splitlines() if not row.startswith("#"))
    assert "a\\|b" in to_markdown(text, result)


@pytest.fixture
def src(tmp_path):
    p = tmp_path / "in.txt"
    p.write_text("대한민국", encoding="utf-8")
    return p


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--rules", "nonsense"], "unknown rule"),
        (["--lexicon", "{tmp}/bad.tsv"], "cannot read lexicon"),
        (["--lexicon", "{tmp}/absent.tsv"], "cannot read lexicon"),
        (["--overrides", "{tmp}/bad.ov"], "override file error"),
        (["--overrides", "{tmp}/absent.ov"], "override file error"),
        (["--stdin"], "one input file or --stdin"),
    ],
)
def test_conversion_errors_exit_2(tmp_path, capsys, src, extra, message):
    (tmp_path / "bad.tsv").write_text("only-one-column\n", encoding="utf-8")
    (tmp_path / "bad.ov").write_text("no separator here\n", encoding="utf-8")
    args = [str(src), *(a.replace("{tmp}", str(tmp_path)) for a in extra)]
    if "--lexicon" not in args:
        args += ["--lexicon", MINI]
    assert main(args) == 2
    assert message in capsys.readouterr().err


def test_review_errors_exit_2(tmp_path, capsys, src):
    ov = tmp_path / "my.ov"
    assert main(["review", str(tmp_path / "missing.txt"), "--overrides", str(ov)]) == 2
    (tmp_path / "bad.tsv").write_text("only-one-column\n", encoding="utf-8")
    assert main(["review", str(src), "--overrides", str(ov), "--lexicon", str(tmp_path / "bad.tsv")]) == 2
    assert main(["review", str(src), "--overrides", str(ov), "--lexicon", MINI, "--rules", "nonsense"]) == 2
    assert capsys.readouterr().err.count("gukhan:") == 3


def _files(tmp_path, n=2):
    out = []
    for i in range(n):
        p = tmp_path / f"f{i}.md"
        p.write_text("대한민국\r\n", encoding="utf-8", newline="")
        out.append(p)
    return out


def test_several_files_need_an_explicit_flag(tmp_path, capsys):
    a, b = _files(tmp_path)
    assert main([str(a), str(b), "--lexicon", MINI]) == 2
    assert "--in-place or --out-dir" in capsys.readouterr().err
    assert a.read_bytes() == b.read_bytes() == "대한민국\r\n".encode()  # nothing touched


def test_in_place_keeps_a_backup_and_line_endings(tmp_path):
    a, b = _files(tmp_path)
    assert main([str(a), str(b), "--in-place", "--lexicon", MINI]) == 0
    for p in (a, b):
        assert p.read_bytes() == "大韓民國\r\n".encode()
        assert p.with_name(p.name + ".bak").read_bytes() == "대한민국\r\n".encode()
        assert not list(tmp_path.glob(".*gukhan-tmp"))


def test_in_place_refuses_to_clobber_an_existing_backup(tmp_path, capsys):
    (a,) = _files(tmp_path, 1)
    a.with_name("f0.md.bak").write_text("older", encoding="utf-8")
    assert main([str(a), "--in-place", "--lexicon", MINI]) == 2
    assert "backup already exists" in capsys.readouterr().err
    assert a.read_bytes() == "대한민국\r\n".encode()
    assert main([str(a), "--in-place", "--no-backup", "--lexicon", MINI]) == 0
    assert a.read_bytes() == "大韓民國\r\n".encode() and a.with_name("f0.md.bak").read_text() == "older"


def test_out_dir_writes_copies_and_never_overwrites(tmp_path, capsys):
    a, b = _files(tmp_path)
    out = tmp_path / "converted"
    assert main([str(a), str(b), "--out-dir", str(out), "--lexicon", MINI]) == 0
    assert (out / "f0.md").read_bytes() == "大韓民國\r\n".encode() and a.read_bytes() == "대한민국\r\n".encode()
    assert main([str(a), "--out-dir", str(out), "--lexicon", MINI]) == 2  # output exists
    assert main([str(a), "--out-dir", str(tmp_path), "--lexicon", MINI]) == 2  # would overwrite its input
    assert "overwrite" in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra",
    [
        ["--in-place", "--out-dir", "{t}/o"],
        ["--in-place", "-o", "{t}/x"],
        ["--no-backup"],
        ["--in-place", "--stdin"],
        ["--out-dir", "{t}/o", "--report", "{t}/r.tsv", "{t}/f1.md"],
    ],
)
def test_conflicting_options_are_rejected(tmp_path, extra):
    a, b = _files(tmp_path)
    args = [str(a), *(x.replace("{t}", str(tmp_path)) for x in extra), "--lexicon", MINI]
    assert main(args) == 2
    assert a.read_bytes() == "대한민국\r\n".encode()


def test_one_bad_file_stops_before_any_write(tmp_path):
    a, _ = _files(tmp_path)
    bad = tmp_path / "bad.md"
    bad.write_bytes("대한민국".encode("cp949"))
    assert main([str(a), str(bad), "--in-place", "--lexicon", MINI]) == 2
    assert a.read_bytes() == "대한민국\r\n".encode() and not a.with_name("f0.md.bak").exists()


def test_version_names_the_analyser_and_lexicon(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("gukhan ") and out[1].startswith("kiwipiepy ") and "model cong" in out[1]
    assert out[2].startswith("gukhan-lexicon ")


def test_jobs_gives_the_same_files_as_one_process(tmp_path, capsys):
    many = []
    for i in range(3):
        p = tmp_path / f"in{i}.md"
        p.write_text("대한민국 헌법 제" + str(i + 1) + "조\n```\n전기\n```\n", encoding="utf-8", newline="")
        many.append(str(p))
    one, two = tmp_path / "one", tmp_path / "two"
    assert main([*many, "--out-dir", str(one), "--lexicon", MINI]) == 0
    capsys.readouterr()
    assert main([*many, "--out-dir", str(two), "--lexicon", MINI, "--jobs", "2", "--workers", "1"]) == 0
    err = capsys.readouterr().err
    for i in range(3):
        assert (one / f"in{i}.md").read_bytes() == (two / f"in{i}.md").read_bytes()
        assert f"in{i}.md: 變換" in err  # the per-file summary line, in input order
    assert err.index("in0.md") < err.index("in1.md") < err.index("in2.md")
    assert "大韓民國 憲法" in (two / "in0.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("extra", [["--workers", "0"], ["--jobs", "-1"]])
def test_bad_worker_counts_are_refused(tmp_path, capsys, extra):
    a, _ = _files(tmp_path)
    assert main([str(a), "--lexicon", MINI, *extra]) == 2
    assert "--workers" in capsys.readouterr().err
