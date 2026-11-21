# SPDX-License-Identifier: Apache-2.0
"""HTML, Word, EPUB and subtitle input: each is converted and rebuilt, and nothing but the converted words changes."""

import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

from gukhan import formats
from gukhan.convert import Converter, Kind
from gukhan.formats import FormatError, ziputil

HANGUL = "국군은 작전 계획을 수립하였다."  # 國軍은 作戰 計劃을 樹立하였다.
HANJA = "國軍은 作戰 計劃을 樹立하였다."


def is_hangul(ch: str) -> bool:
    return "가" <= ch <= "힣"


def only_words_changed(before: str, after: str) -> None:
    """Same length, and every changed character was a Hangul syllable that became a non-Hangul one."""
    assert len(before) == len(after), "length differs"
    for i, (a, b) in enumerate(zip(before, after, strict=True)):
        if a != b:
            assert is_hangul(a) and not is_hangul(b), f"unexpected change at {i}: {a!r} -> {b!r}"


@pytest.fixture(scope="module")
def conv() -> Converter:
    return Converter()


def run(fmt: str, data: str | bytes, conv: Converter, **kw) -> formats.Converted:
    return formats.convert_document(formats.load(fmt, data), conv, **kw)


def make_zip(parts: list[tuple[str, bytes, int]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data, method in parts:
            info = zipfile.ZipInfo(name, (2026, 11, 21, 12, 0, 0))
            info.compress_type = method
            z.writestr(info, data)
    return buf.getvalue()


def members(data: bytes) -> list[tuple[str, int, bytes]]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return [(i.filename, i.compress_type, z.read(i)) for i in z.infolist()]


def assert_zip_round_trip(before: bytes, after: bytes, changed: set[str]) -> None:
    """Same members, order and compression; untouched parts byte-identical; changed parts differ only in words."""
    a, b = members(before), members(after)
    assert [(n, c) for n, c, _ in a] == [(n, c) for n, c, _ in b]
    for (name, _, old), (_, _, new) in zip(a, b, strict=True):
        if name in changed:
            assert old != new, f"{name} should have changed"
            only_words_changed(old.decode("utf-8"), new.decode("utf-8"))
            ET.fromstring(new)  # still well-formed XML
        else:
            assert old == new, f"{name} must be untouched"


# ---- HTML -----------------------------------------------------------------------------------------------------


HTML = (
    '<!DOCTYPE html>\r\n<html lang="ko"><head><meta charset="utf-8"><title>국군 연구</title>'
    "<style>.국군 { color: red }</style></head><body>\r\n"
    f'<p class="국군" title="국군">{HANGUL} &amp; <b>작전</b> 계획&nbsp;끝 <code>국군</code></p>\r\n'
    '<img alt="국군" src="국군.png"><script>var s = "국군";</script><!-- 국군 -->\r\n'
    "<pre>국군\n작전</pre><P>전<i>기</i>를 <a href='x?q=국군'>연구</a></P><br/>수립<textarea>국군</textarea>\r\n"
    "</body></html>\r\n"
)


@pytest.mark.kiwi
def test_html_converts_text_nodes_only(conv):
    out = run("html", HTML, conv).output
    only_words_changed(HTML, out)
    assert f'<p class="국군" title="국군">{HANJA} &amp; <b>作戰</b> 計劃&nbsp;끝 <code>국군</code></p>' in out
    assert "<title>國軍 硏究</title>" in out
    assert '<img alt="국군" src="국군.png">' in out and 'var s = "국군";' in out and "<!-- 국군 -->" in out
    assert ".국군 { color: red }" in out and "<pre>국군\n작전</pre>" in out and "<textarea>국군</textarea>" in out
    assert "<P>전<i>기</i>를 <a href='x?q=국군'>硏究</a></P><br/>樹立" in out
    assert out.count("\r\n") == HTML.count("\r\n")


@pytest.mark.kiwi
def test_html_word_split_by_inline_tags_is_one_word(conv):
    out = run("html", "<p>국<b>군</b>은 <i>작전</i> <u>계획</u></p>", conv).output
    assert out == "<p>國<b>軍</b>은 <i>作戰</i> <u>計劃</u></p>"


@pytest.mark.kiwi
def test_html_block_tags_separate_text(conv):
    # a heading and the paragraph after it are different sentences; "작전" + "계획" must not join across them
    out = run("html", "<h1>작전</h1><p>계획</p><li>작전</li><li>계획</li>", conv).output
    assert out == "<h1>作戰</h1><p>計劃</p><li>作戰</li><li>計劃</li>"


@pytest.mark.kiwi
def test_html_no_change_is_byte_identical(conv):
    src = '<p class="a">Hello &amp; <b>world</b></p>\n<!-- 국군 --><script>1</script>'
    assert run("html", src, conv).output == src


@pytest.mark.kiwi
def test_html_is_idempotent_and_entities_survive(conv):
    once = run("html", HTML, conv).output
    assert run("html", once, conv).output == once
    assert "&amp;" in once and "&nbsp;" in once


@pytest.mark.kiwi
def test_html_xhtml_and_unusual_markup(conv):
    src = (
        '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
        "<p>국군<br />작전 < 계획 &#54620;글 &unknown; 수립</p></body></html>"
    )
    out = run("html", src, conv).output
    only_words_changed(src, out)
    assert out.startswith('<?xml version="1.0"?>') and "&#54620;" in out and "&unknown;" in out
    assert "國軍<br />作戰 < 計劃" in out


def test_html_mark_mode_changes_length_but_not_markup(conv):
    out = run("html", "<p><b>전기</b>를 연구</p>", Converter(), mark=True).output
    assert out.startswith("<p><b>") and out.endswith("</b>를 硏究</p>") and "{" in out


@pytest.mark.kiwi
def test_html_report_offsets_refer_to_extracted_prose(conv):
    done = run("html", "<p>국군은</p><p>전기를 연구</p>", conv)
    assert done.source_text == "국군은\n전기를 연구"
    flagged = done.result.of(Kind.FLAGGED)
    assert [done.source_text[d.start : d.end] for d in flagged] == ["전기"]


# ---- Subtitles ------------------------------------------------------------------------------------------------


SRT = (
    "﻿1\r\n00:00:01,000 --> 00:00:02,500\r\n<i>국군은</i> 작전\r\n계획을 수립하였다.\r\n\r\n"
    "2\r\n00:00:03,000 --> 00:00:04,000 X1:100\r\n{\\an8}연구 &amp; 국군\r\n\r\n\r\n"
    "3\r\n00:00:05,000 --> 00:00:06,000\r\n국군"
)

VTT = (
    "WEBVTT - 국군 자막\n\nSTYLE\n::cue { color: red } /* 국군 */\n\nNOTE 국군\n작전 계획\n\n"
    "국군-1\n00:00:01.000 --> 00:00:02.000 align:start\n<v 국군>국군은 <c.red>작전</c> 계획</v>\n"
    "<00:00:01.500>수립하였다\n\n"
    "01:00:03.000 --> 01:00:04.000\n연구\n"
)


@pytest.mark.kiwi
def test_srt_converts_cue_text_only(conv):
    out = run("srt", SRT, conv).output
    only_words_changed(SRT, out)
    assert out.startswith("﻿1\r\n00:00:01,000 --> 00:00:02,500\r\n<i>國軍은</i> 作戰\r\n計劃을 樹立하였다.\r\n\r\n")
    assert "00:00:04,000 X1:100\r\n{\\an8}硏究 &amp; 國軍\r\n\r\n\r\n3\r\n" in out
    assert out.endswith("00:00:06,000\r\n國軍")
    assert out.count("\r\n") == SRT.count("\r\n")


@pytest.mark.kiwi
def test_vtt_leaves_header_notes_styles_and_identifiers(conv):
    out = run("vtt", VTT, conv).output
    only_words_changed(VTT, out)
    assert out.startswith(
        "WEBVTT - 국군 자막\n\nSTYLE\n::cue { color: red } /* 국군 */\n\nNOTE 국군\n작전 계획\n\n국군-1\n"
    )
    assert "<v 국군>國軍은 <c.red>作戰</c> 計劃</v>\n<00:00:01.500>樹立하였다\n" in out
    assert "01:00:03.000 --> 01:00:04.000\n硏究\n" in out


@pytest.mark.kiwi
def test_subtitles_without_cues_or_changes_are_identical(conv):
    for src in ("", "WEBVTT\n\nNOTE 국군\n", "1\n00:00:01,000 --> 00:00:02,000\nHello\n", "국군\n작전\n"):
        assert run("srt", src, conv).output == src


@pytest.mark.kiwi
def test_subtitle_phrase_across_a_wrapped_line(conv):
    src = "1\n00:00:01,000 --> 00:00:02,000\n작전\n계획\n"
    assert run("srt", src, conv).output == "1\n00:00:01,000 --> 00:00:02,000\n作戰\n計劃\n"


# ---- Word -----------------------------------------------------------------------------------------------------


NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def run_xml(text: str, bold: bool = False) -> str:
    pr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{pr}<w:t xml:space="preserve">{text}</w:t></w:r>'


DOCUMENT = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>'
    f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>{run_xml("국")}{run_xml("군은 작전 ", True)}'
    f"{run_xml('계획')}{run_xml('을 수립하였다. &amp; ')}<w:r><w:tab/></w:r>{run_xml('연구')}</w:p>"
    '<w:p><w:r><w:instrText> HYPERLINK "국군" </w:instrText></w:r><w:r><w:delText>국군</w:delText></w:r>'
    "<w:r><w:t/></w:r><w:r><w:t >작전</w:t></w:r></w:p>"
    "<w:p><w:ruby><w:rubyPr/><w:rt><w:r><w:t>국군</w:t></w:r></w:rt><w:rubyBase><w:r><w:t>軍</w:t></w:r></w:rubyBase>"
    "</w:ruby></w:p>"
    '<w:sectPr><w:pgSz w:w="11906"/></w:sectPr></w:body></w:document>'
)
HEADER = f"<w:hdr {NS}><w:p>{run_xml('국군 연구')}</w:p></w:hdr>"
FOOTNOTES = f'<w:footnotes {NS}><w:footnote w:id="1"><w:p>{run_xml("수립")}</w:p></w:footnote></w:footnotes>'
CORE = (
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>국군 연구</dc:title></cp:coreProperties>'
)
PNG = bytes(range(256)) * 4


def docx_bytes() -> bytes:
    S, D = zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED
    return make_zip(
        [
            ("[Content_Types].xml", b"<Types/>", D),
            ("_rels/.rels", b"<Relationships/>", D),
            ("word/document.xml", DOCUMENT.encode(), D),
            ("word/header1.xml", HEADER.encode(), D),
            ("word/footnotes.xml", FOOTNOTES.encode(), D),
            ("word/styles.xml", f'<w:styles {NS}><w:style><w:name w:val="국군"/></w:style></w:styles>'.encode(), D),
            ("word/media/image1.png", PNG, S),
            ("docProps/core.xml", CORE.encode(), D),
            ("word/", b"", S),
        ]
    )


@pytest.mark.kiwi
def test_docx_converts_runs_and_keeps_everything_else(conv):
    before = docx_bytes()
    out = run("docx", before, conv).output
    assert isinstance(out, bytes)
    assert_zip_round_trip(before, out, {"word/document.xml", "word/header1.xml", "word/footnotes.xml"})
    doc = dict((n, d.decode("utf-8")) for n, _, d in members(out) if n.endswith(".xml")).get("word/document.xml", "")
    # a word split over runs is converted whole and each character stays in its own run, with its formatting
    assert run_xml("國") in doc and run_xml("軍은 作戰 ", True) in doc and run_xml("計劃") in doc
    assert run_xml("을 樹立하였다. &amp; ") in doc and "<w:tab/>" in doc and run_xml("硏究") in doc
    # field codes, deleted text, empty runs and ruby readings are not touched
    assert '<w:instrText> HYPERLINK "국군" </w:instrText>' in doc and "<w:delText>국군</w:delText>" in doc
    assert "<w:t/>" in doc and "<w:rt><w:r><w:t>국군</w:t></w:r></w:rt>" in doc and "<w:t >作戰</w:t>" in doc


@pytest.mark.kiwi
def test_docx_without_hangul_to_convert_is_returned_as_is(conv):
    before = make_zip(
        [("word/document.xml", f"<w:document {NS}><w:p>{run_xml('Hello')}</w:p></w:document>".encode(), 8)]
    )
    assert run("docx", before, conv).output == before


@pytest.mark.kiwi
def test_docx_mark_mode_puts_the_mark_in_the_run_of_the_last_character(conv):
    body = f"<w:document {NS}><w:p>{run_xml('전')}{run_xml('기를 연구')}</w:p></w:document>"
    src = make_zip([("word/document.xml", body.encode(), 8)])
    out = run("docx", src, conv, mark=True).output
    text = members(out)[0][2].decode("utf-8")
    # the mark goes after the last character of the word, in the run that holds it
    assert run_xml("전") in text and run_xml("기{傳記|前期|電氣}를 硏究") in text
    ET.fromstring(text)


def test_docx_errors():
    with pytest.raises(FormatError):
        formats.load("docx", b"not a zip")
    with pytest.raises(FormatError, match="word/document.xml"):
        formats.load("docx", make_zip([("a.txt", b"x", 8)]))
    with pytest.raises(FormatError):
        formats.load("docx", "text, not bytes")
    bad = make_zip([("word/document.xml", "<w:document>국군</w:document>".encode("utf-16"), 8)])
    with pytest.raises(FormatError, match="UTF-8"):
        formats.load("docx", bad)


def test_zip_limits(monkeypatch):
    monkeypatch.setattr(ziputil, "MAX_TOTAL", 10)
    with pytest.raises(FormatError, match="too large"):
        formats.load("docx", docx_bytes())
    monkeypatch.setattr(ziputil, "MAX_TOTAL", 1 << 30)
    monkeypatch.setattr(ziputil, "MAX_ENTRIES", 2)
    with pytest.raises(FormatError, match="too large"):
        formats.load("docx", docx_bytes())


def test_encrypted_zip_is_refused():
    raw = bytearray(docx_bytes())
    # set the "encrypted" bit in the first local header and in its central directory entry
    raw[6] |= 1
    central = raw.index(b"PK\x01\x02")
    raw[central + 8] |= 1
    with pytest.raises(FormatError, match="encrypted"):
        formats.load("docx", bytes(raw))


# ---- EPUB -----------------------------------------------------------------------------------------------------


CHAPTER = (
    '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko"><head>'
    f"<title>국군</title></head><body><h1>연구</h1><p>{HANGUL}</p>"
    "<p>전<span>기</span>를 <em>수립</em></p></body></html>"
)
NCX = (
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint><navLabel><text>작전 계획</text></navLabel>'
    '<content src="c1.xhtml"/></navPoint></navMap></ncx>'
)
OPF = (
    '<package><metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">국군 연구</dc:title></metadata></package>'
)


def epub_bytes() -> bytes:
    S, D = zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED
    return make_zip(
        [
            ("mimetype", b"application/epub+zip", S),
            ("META-INF/container.xml", b"<container/>", D),
            ("OEBPS/content.opf", OPF.encode(), D),
            ("OEBPS/toc.ncx", NCX.encode(), D),
            ("OEBPS/c1.xhtml", CHAPTER.encode(), D),
            ("OEBPS/style.css", "p::before { content: '국군' }".encode(), D),
            ("OEBPS/cover.jpg", PNG, S),
        ]
    )


@pytest.mark.kiwi
def test_epub_converts_chapters_and_toc_only(conv):
    before = epub_bytes()
    out = run("epub", before, conv).output
    assert isinstance(out, bytes)
    assert_zip_round_trip(before, out, {"OEBPS/toc.ncx", "OEBPS/c1.xhtml"})
    assert members(out)[0][:2] == ("mimetype", zipfile.ZIP_STORED)  # the EPUB rules: first and uncompressed
    parts = {n: d.decode("utf-8") for n, _, d in members(out) if not n.endswith(".jpg")}
    assert "<text>作戰 計劃</text>" in parts["OEBPS/toc.ncx"]
    assert f"<p>{HANJA}</p>" in parts["OEBPS/c1.xhtml"] and "<h1>硏究</h1>" in parts["OEBPS/c1.xhtml"]
    assert parts["OEBPS/c1.xhtml"].startswith('<?xml version="1.0" encoding="utf-8"?>\n')
    assert "<dc:title" in parts["OEBPS/content.opf"] and "국군 연구" in parts["OEBPS/content.opf"]


def test_epub_errors():
    with pytest.raises(FormatError, match="mimetype"):
        formats.load("epub", make_zip([("a.xhtml", b"<p/>", 8)]))
    with pytest.raises(FormatError, match="mimetype"):
        formats.load("epub", make_zip([("mimetype", b"application/zip", 0)]))


# ---- misc -----------------------------------------------------------------------------------------------------


def test_detect_format(tmp_path):
    from pathlib import Path

    cases = {
        "a.HTML": "html",
        "a.htm": "html",
        "a.xhtml": "html",
        "a.docx": "docx",
        "a.epub": "epub",
        "a.srt": "srt",
        "a.VTT": "vtt",
        "a.md": "text",
        "a.txt": "text",
        "a": "text",
    }
    for name, fmt in cases.items():
        assert formats.detect_format(Path(name)) == fmt
    assert formats.is_binary("docx") and formats.is_binary("epub") and not formats.is_binary("html")


def test_unknown_format_and_non_utf8_text():
    with pytest.raises(FormatError):
        formats.load("pdf", "x")
    with pytest.raises(FormatError, match="UTF-8"):
        formats.load("html", "<p>국군</p>".encode("euc-kr"))


@pytest.mark.kiwi
def test_field_rule_evidence_is_not_left_behind(conv):
    run("html", "<p>국군은 작전</p>", conv)
    assert conv.field_evidence is None


# ---- Random documents -----------------------------------------------------------------------------------------


@pytest.mark.kiwi
@pytest.mark.parametrize("seed", range(8))
def test_random_html_and_subtitles_change_only_words(conv, seed):
    import random

    rng = random.Random(seed)
    words = ["국군", "작전", "계획", "수립", "연구", "전기", "hello", "123", "—", "한글", "대한민국"]
    glue = [
        " ",
        " ",
        "&amp;",
        "&nbsp;",
        "&#54620;",
        "\n",
        "\r\n",
        "<b>",
        "</b>",
        "<br>",
        "<!-- 국군 -->",
        "<code>",
        "</code>",
    ]

    def prose(n: int) -> str:
        return "".join(rng.choice(words) + rng.choice(glue) for _ in range(n))

    page = "<body>" + "".join(f"<p>{prose(rng.randint(1, 8))}</p>\n" for _ in range(rng.randint(1, 6)))
    cues = "".join(
        f"{i}\n00:00:0{i},000 --> 00:00:0{i},900\n{prose(rng.randint(1, 5)).replace(chr(10), ' ')}\n\n"
        for i in range(1, 6)
    )
    for fmt, src in (("html", page), ("srt", cues)):
        out = run(fmt, src, conv).output
        only_words_changed(src, out)
        assert run(fmt, out, conv).output == out  # converting twice changes nothing more
        # the markup skeleton (everything that is not a Hangul syllable or a Hanja) is the same
        skeleton = lambda t: "".join(c for c in t if not is_hangul(c) and not ("一" <= c <= "鿿"))  # noqa: E731
        assert skeleton(src) == skeleton(out)
