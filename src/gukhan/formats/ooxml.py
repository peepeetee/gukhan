# SPDX-License-Identifier: Apache-2.0
"""Word (.docx): the text of ``<w:t>`` runs is converted; runs, styles, images and every other part are copied.

A paragraph is one flow, so a word that Word split over several runs (a bold syllable, a spell-check boundary)
is analysed whole, and each converted character goes back into the run it came from, formatting intact.
Only the document body, headers, footers, footnotes, endnotes and comments are read; document properties and
field codes are not touched.
"""

from __future__ import annotations

import re

from . import Document, Flow, FormatError, Gap, SpanDocument, scan_text
from .ziputil import Entry, read_zip, write_zip

_PART = re.compile(r"word/(?:document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml", re.IGNORECASE)
_TOKEN = re.compile(
    r"(?P<run><w:t(?:\s[^>]*?)?(?<!/)>)(?P<text>.*?)</w:t>"
    r"|(?P<para></?w:p(?=[\s>/])[^>]*>)"
    r"|(?P<rt></?w:rt(?=[\s>/])[^>]*>)"
    r"|(?P<gap><w:(?:tab|br|cr|ptab|noBreakHyphen|sym)(?=[\s>/])[^>]*>)",
    re.DOTALL,
)


def parse_part(src: str) -> SpanDocument:
    """One WordprocessingML part: a flow per paragraph, editable pieces from ``<w:t>`` outside ruby readings."""
    spans: list[tuple[int, int]] = []
    flows: list[Flow] = []
    flow: Flow = []
    in_rt = False
    for m in _TOKEN.finditer(src):
        if m.group("run") is not None:
            if in_rt:
                flow.append(Gap("￼"))
            else:
                scan_text(src, m.start("text"), m.end("text"), flow, spans)
        elif m.group("para") is not None:
            flows.append(flow)
            flow = []
        elif m.group("rt") is not None:
            in_rt = not m.group().startswith("</") and not m.group().endswith("/>")
        else:
            tag = m.group()
            flow.append(Gap("-" if "noBreakHyphen" in tag else "￼" if "<w:sym" in tag else " "))
    flows.append(flow)
    return SpanDocument(src, spans, flows)


class ZipDocument(Document):
    """An archive whose XML or XHTML parts are documents; everything else is carried over unchanged."""

    def __init__(self, entries: list[Entry], parts: dict[int, SpanDocument], original: bytes) -> None:
        self.entries, self.parts, self.original = entries, parts, original
        super().__init__([flow for _, part in sorted(parts.items()) for flow in part.flows])

    def rebuild(self, edited: list[str]) -> bytes:
        replaced: dict[int, bytes] = {}
        at = 0
        for index, part in sorted(self.parts.items()):
            n = len(part.spans)
            new = part.rebuild(edited[at : at + n])
            at += n
            if new != part.src:
                replaced[index] = new.encode("utf-8")
        if at != len(edited):
            raise FormatError("내부 誤謬: 조각 數가 다릅니다 / internal error: piece count differs")
        if not replaced:
            return self.original  # nothing was converted: the file is returned as it came
        return write_zip(self.entries, replaced)


def decode_part(entry: Entry) -> str:
    """A part's text; Word writes UTF-8, and anything else is refused rather than guessed."""
    try:
        return entry.data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise FormatError(f"{entry.info.filename}: UTF-8이 아닙니다 / not UTF-8 text") from e


def parse_docx(data: bytes) -> ZipDocument:
    """Read a .docx container."""
    entries = read_zip(data)
    names = {e.info.filename for e in entries}
    if "word/document.xml" not in names:
        raise FormatError(".docx가 아닙니다 / not a Word document (no word/document.xml)")
    parts = {i: parse_part(decode_part(e)) for i, e in enumerate(entries) if _PART.fullmatch(e.info.filename)}
    return ZipDocument(entries, parts, data)
