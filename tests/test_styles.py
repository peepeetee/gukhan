# SPDX-License-Identifier: Apache-2.0
"""Output styles: mixed, gloss, ruby and hanja-gloss."""

import io
import re
import zipfile
from xml.etree import ElementTree as ET

import pytest

from gukhan import formats, styles
from gukhan.cli import main
from gukhan.convert import Converter
from gukhan.suggest import Suggestion, apply_suggestions
from tests.test_formats import HTML, SRT, docx_bytes, epub_bytes, members

SENTENCE = "국군은 작전 계획을 수립하였다."


def test_render_each_style():
    assert styles.render("국군", "國軍") == "國軍"
    assert styles.render("국군", "國軍", "gloss") == "국군(國軍)"
    assert styles.render("국군", "國軍", "hanja-gloss") == "國軍(국군)"
    assert styles.render("국군", "國軍", "ruby") == (
        "<ruby>國<rp>(</rp><rt>국</rt><rp>)</rp></ruby><ruby>軍<rp>(</rp><rt>군</rt><rp>)</rp></ruby>"
    )


def test_phrases_with_a_space_and_characters_without_hanja():
    assert styles.render("작전 계획", "作戰 計劃", "gloss") == "작전 계획(作戰 計劃)"
    assert styles.render("작전 계획", "作戰 計劃", "hanja-gloss") == "作戰 計劃(작전 계획)"
    assert styles.render("작전 계획", "作戰 計劃", "ruby").count("<ruby>") == 4  # the space has no ruby
    # a character that has no Hanja stays plain in ruby (and the reading is not repeated)
    assert styles.render("가나", "家나", "ruby") == "<ruby>家<rp>(</rp><rt>가</rt><rp>)</rp></ruby>나"


def test_char_outputs_has_one_entry_per_hangul_character():
    for style in styles.STYLES:
        assert len(styles.char_outputs("국군", "國軍", style)) == 2
        assert len(styles.char_outputs("국군", "國軍的", style)) == 2  # a reading of another length: whole word
    assert (
        "".join(styles.char_outputs("국군", "國軍的", "ruby")) == "<ruby>國軍的<rp>(</rp><rt>국군</rt><rp>)</rp></ruby>"
    )


def test_unknown_style_is_an_error():
    with pytest.raises(ValueError, match="unknown style"):
        Converter(style="bold")
    with pytest.raises(ValueError):
        styles.char_outputs("국군", "國軍", "bold")


@pytest.mark.kiwi
@pytest.mark.parametrize(
    ("style", "expected"),
    [
        ("mixed", "國軍은 作戰 計劃을 樹立하였다."),
        ("gloss", "국군(國軍)은 작전 계획(作戰 計劃)을 수립(樹立)하였다."),
        ("hanja-gloss", "國軍(국군)은 作戰 計劃(작전 계획)을 樹立(수립)하였다."),
    ],
)
def test_converter_styles(style, expected):
    assert Converter(style=style).convert(SENTENCE).text == expected


@pytest.mark.kiwi
def test_ruby_in_text_and_flagged_words_stay_plain():
    out = Converter(style="ruby").convert("국군은 전기를 읽었다.").text
    assert out.startswith("<ruby>國<rp>(</rp><rt>국</rt><rp>)</rp></ruby><ruby>軍") and "은 전기를 읽었다." in out
    assert Converter(style="gloss").convert("전기를 읽었다.").text == "전기를 읽었다."  # flagged: nothing to gloss
    assert Converter(style="gloss").convert("전기를", mark=True).text.startswith("전기{")


@pytest.mark.kiwi
@pytest.mark.parametrize("style", ["gloss", "hanja-gloss", "ruby"])
def test_running_a_style_twice_does_not_gloss_twice(style):
    conv = Converter(style=style)
    once = conv.convert(SENTENCE).text
    assert conv.convert(once).text == once


def strip(style: str, out: str) -> str:
    """Take the glosses back out of ``out``."""
    if style == "gloss":
        return re.sub(r"\([一-鿿 ]+\)", "", out)
    if style == "hanja-gloss":
        return re.sub(r"\([가-힣 ]+\)", "", out)
    return re.sub(r"</?ruby>|<rp>\(</rp>|<rt>[가-힣]</rt>|<rp>\)</rp>", "", out)


@pytest.mark.kiwi
@pytest.mark.parametrize("style", ["gloss", "hanja-gloss", "ruby"])
def test_styles_add_only_glosses_in_every_text_format(style):
    """Without its glosses the output is the mixed-script output (hanja-gloss, ruby) or the input (gloss)."""
    plain, styled = Converter(), Converter(style=style)
    for fmt, src in (("html", HTML), ("srt", SRT)):
        if fmt == "srt" and style == "ruby":
            continue
        mixed = formats.convert_document(formats.load(fmt, src), plain).output
        out = formats.convert_document(formats.load(fmt, src), styled).output
        assert strip(style, out) == (src if style == "gloss" else mixed), fmt


@pytest.mark.kiwi
def test_word_split_by_markup_keeps_its_gloss_text():
    out = formats.convert_document(formats.load("html", "<p>국<b>군</b>은</p>"), Converter(style="gloss")).output
    assert out == "<p>국<b>군(國軍)</b>은</p>"
    out = formats.convert_document(formats.load("html", "<p>국<b>군</b>은</p>"), Converter(style="ruby")).output
    assert out.startswith("<p><ruby>國<rp>(</rp><rt>국</rt>") and "<b><ruby>軍" in out and out.endswith("</b>은</p>")


@pytest.mark.kiwi
def test_ruby_is_refused_for_word_and_subtitles_and_plain_in_epub_toc():
    for fmt, data in (("docx", docx_bytes()), ("srt", SRT)):
        with pytest.raises(formats.FormatError, match="ruby"):
            formats.convert_document(formats.load(fmt, data), Converter(style="ruby"))
    out = formats.convert_document(formats.load("epub", epub_bytes()), Converter(style="ruby")).output
    parts = {n: d.decode("utf-8") for n, _, d in members(out) if n.endswith((".ncx", ".xhtml"))}
    assert "<text>作戰 計劃(작전 계획)</text>" in parts["OEBPS/toc.ncx"]  # the contents list is plain text
    assert "<ruby>" in parts["OEBPS/c1.xhtml"]
    for body in parts.values():
        ET.fromstring(body)  # still well-formed


@pytest.mark.kiwi
def test_docx_gloss_goes_into_the_run_of_the_last_character():
    out = formats.convert_document(formats.load("docx", docx_bytes()), Converter(style="gloss")).output
    with zipfile.ZipFile(io.BytesIO(out)) as z:
        assert zipfile.ZipFile.testzip(z) is None
        text = z.read("word/document.xml").decode("utf-8")
    assert "군(國軍)" in text and "<w:t " in text


def test_apply_suggestions_uses_the_style():
    from gukhan.convert import Decision, Kind, Result

    text = "전기를"
    d = Decision(0, 2, "전기", Kind.FLAGGED)
    result = Result(text, [d])
    s = {(0, 2): Suggestion(1, "電氣", "mock")}
    assert apply_suggestions(text, result, s) == "電氣를"
    assert apply_suggestions(text, result, s, "gloss") == "전기(電氣)를"
    assert apply_suggestions(text, result, s, "hanja-gloss") == "電氣(전기)를"


@pytest.mark.kiwi
def test_cli_style(tmp_path, capsys):
    src = tmp_path / "a.md"
    src.write_text(SENTENCE + "\n", encoding="utf-8")
    out = tmp_path / "o.md"
    for style, expected in (("gloss", "국군(國軍)은"), ("hanja-gloss", "國軍(국군)은"), ("mixed", "國軍은")):
        assert main([str(src), "-o", str(out), "--style", style]) == 0
        assert out.read_text(encoding="utf-8").startswith(expected)
    assert main([str(src), "-o", str(out), "--style", "ruby"]) == 0
    assert "<ruby>國<rp>(</rp><rt>국</rt>" in out.read_text(encoding="utf-8")
    with pytest.raises(SystemExit):  # argparse rejects an unknown style
        main([str(src), "--style", "bold"])
    capsys.readouterr()


@pytest.mark.kiwi
def test_cli_style_with_formats_and_jobs(tmp_path, capsys):
    word = tmp_path / "a.docx"
    word.write_bytes(docx_bytes())
    assert main([str(word), "-o", str(tmp_path / "o.docx"), "--style", "ruby"]) == 2
    assert "ruby" in capsys.readouterr().err
    assert main([str(word), "-o", str(tmp_path / "o.docx"), "--style", "gloss"]) == 0
    (tmp_path / "b.html").write_text("<p>국군은 작전</p>", encoding="utf-8")
    (tmp_path / "c.md").write_text("국군은 작전\n", encoding="utf-8")
    out = tmp_path / "out"
    assert (
        main(
            [str(tmp_path / "b.html"), str(tmp_path / "c.md"), "--out-dir", str(out), "--style", "gloss", "--jobs", "2"]
        )
        == 0
    )
    assert (out / "b.html").read_text(encoding="utf-8") == "<p>국군(國軍)은 작전(作戰)</p>"
    assert (out / "c.md").read_text(encoding="utf-8") == "국군(國軍)은 작전(作戰)\n"
