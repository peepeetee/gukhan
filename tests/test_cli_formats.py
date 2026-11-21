# SPDX-License-Identifier: Apache-2.0
"""The command line with HTML, Word, EPUB and subtitle files."""

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from gukhan.cli import main
from tests.test_formats import HTML, SRT, docx_bytes, epub_bytes, members

pytestmark = pytest.mark.kiwi
FIX = Path(__file__).parent / "fixtures"
MINI = str(FIX / "mini_lexicon.tsv")


def test_by_extension(tmp_path):
    for name, data in (("a.html", HTML), ("a.srt", SRT)):
        src, out = tmp_path / name, tmp_path / ("out_" + name)
        src.write_bytes(data.encode("utf-8"))
        assert main([str(src), "-o", str(out)]) == 0
        before, after = src.read_bytes().decode("utf-8"), out.read_bytes().decode("utf-8")
        assert len(before) == len(after) and before != after
        assert after.count("\r\n") == before.count("\r\n")  # line endings are not rewritten
    for name, data in (("a.docx", docx_bytes()), ("a.epub", epub_bytes())):
        src, out = tmp_path / name, tmp_path / ("out_" + name)
        src.write_bytes(data)
        assert main([str(src), "-o", str(out)]) == 0
        assert [n for n, _, _ in members(out.read_bytes())] == [n for n, _, _ in members(data)]
        assert out.read_bytes() != data


def test_docx_in_place_keeps_a_byte_identical_backup(tmp_path):
    src = tmp_path / "doc.docx"
    src.write_bytes(docx_bytes())
    assert main([str(src), "--in-place"]) == 0
    assert (tmp_path / "doc.docx.bak").read_bytes() == docx_bytes()
    assert src.read_bytes() != docx_bytes()
    with zipfile.ZipFile(src) as z:
        assert z.testzip() is None


def test_stdin_and_stdout_carry_bytes_for_binary_formats(tmp_path):
    done = subprocess.run(
        [sys.executable, "-m", "gukhan.cli", "--stdin", "--format", "epub"],
        input=epub_bytes(),
        capture_output=True,
        check=True,
    )
    assert done.stdout.startswith(b"PK") and done.stdout != epub_bytes()
    assert [n for n, _, _ in members(done.stdout)][0] == "mimetype"


def test_stdin_html(monkeypatch, capsys):
    import io

    class Stdin:
        buffer = io.BytesIO("<p>국군은 작전</p>".encode())

    monkeypatch.setattr(sys, "stdin", Stdin())
    assert main(["--stdin", "--format", "html"]) == 0
    assert capsys.readouterr().out == "<p>國軍은 作戰</p>"


def test_mixed_files_to_out_dir(tmp_path):
    files = {"a.html": HTML.encode(), "b.docx": docx_bytes(), "c.srt": SRT.encode(), "d.md": "국군은 작전\n".encode()}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    out = tmp_path / "out"
    assert main([*[str(tmp_path / n) for n in files], "--out-dir", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == sorted(files)
    assert (out / "d.md").read_text(encoding="utf-8") == "國軍은 作戰\n"
    assert zipfile.is_zipfile(out / "b.docx")


def test_jobs_with_binary_files(tmp_path):
    for name in ("a.docx", "b.epub"):
        (tmp_path / name).write_bytes(docx_bytes() if name.endswith("docx") else epub_bytes())
    out = tmp_path / "out"
    assert main([str(tmp_path / "a.docx"), str(tmp_path / "b.epub"), "--out-dir", str(out), "--jobs", "2"]) == 0
    assert members((out / "a.docx").read_bytes()) != members(docx_bytes())


def test_report_uses_the_extracted_prose(tmp_path, capsys):
    src, rep = tmp_path / "p.html", tmp_path / "rep.tsv"
    src.write_text("<p>국군은</p><p>전기를 읽었다</p>", encoding="utf-8")
    assert main([str(src), "-o", str(tmp_path / "o.html"), "--report", str(rep), "--lexicon", MINI]) == 0
    rows = [line.split("\t") for line in rep.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    assert [(r[0], r[1], r[3]) for r in rows] == [("flagged", "2", "전기")]  # line 2 of the extracted prose
    assert "flag 1" in capsys.readouterr().err


def test_bad_inputs_are_reported_before_anything_is_written(tmp_path, capsys):
    good, bad, out = tmp_path / "a.html", tmp_path / "b.docx", tmp_path / "out"
    good.write_text("<p>국군</p>", encoding="utf-8")
    bad.write_bytes(b"not a zip")
    assert main([str(good), str(bad), "--out-dir", str(out)]) == 2
    err = capsys.readouterr().err
    assert "b.docx" in err and "zip" in err and not out.exists()
    euc = tmp_path / "c.html"
    euc.write_bytes("<p>국군</p>".encode("euc-kr"))
    assert main([str(euc)]) == 2 and "UTF-8" in capsys.readouterr().err


def test_llm_and_review_are_refused_for_structured_formats(tmp_path, capsys):
    src = tmp_path / "p.html"
    src.write_text("<p>국군</p>", encoding="utf-8")
    assert main([str(src), "--llm-url", "http://127.0.0.1:1/v1"]) == 2
    assert "plain text and Markdown only" in capsys.readouterr().err
    assert main(["review", str(src), "--overrides", str(tmp_path / "o.txt")]) == 2
    assert "plain text and Markdown files only" in capsys.readouterr().err


def test_format_option_overrides_the_extension(tmp_path):
    src = tmp_path / "page.txt"
    src.write_text('<p title="국군">국군</p> `국군`', encoding="utf-8")
    out = tmp_path / "o.txt"
    assert main([str(src), "-o", str(out), "--format", "html", "--lexicon", MINI]) == 0
    assert out.read_text(encoding="utf-8").startswith('<p title="국군">')
