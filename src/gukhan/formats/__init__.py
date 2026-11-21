# SPDX-License-Identifier: Apache-2.0
"""Input formats beyond plain text and Markdown: HTML, Word (.docx), EPUB and subtitles (SRT, WebVTT).

Every format is read into *flows*: runs of text that read as one piece of prose (a paragraph, a subtitle cue).
A flow is a list of editable text pieces and :class:`Gap` placeholders for what sits between them (an
entity, a line break, a code span). The converter sees a flow joined into one string, so a word split by
inline markup (``전<b>기</b>``) or a sentence split over several Word runs is still analysed whole, and the
converted characters are then written back piece by piece. Everything outside the editable pieces (tags,
attributes, XML, timing lines, images, styles) is copied byte for byte.

HTML, Word, EPUB 및 字幕 file을 읽어 文章 單位(flow)로 變換하고, 標識·屬性·시간 정보는 그대로 둡니다.

Public: :func:`load`, :func:`convert_document`, :func:`detect_format`, :class:`Document`, :class:`Gap`,
:class:`Converted`, :class:`FormatError`, :data:`FORMATS`.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from gukhan.convert import Converter, Decision, Result

FORMATS = ("text", "html", "docx", "epub", "srt", "vtt")
BINARY = frozenset({"docx", "epub"})
_BY_SUFFIX = {
    ".html": "html",
    ".htm": "html",
    ".xhtml": "html",
    ".docx": "docx",
    ".epub": "epub",
    ".srt": "srt",
    ".vtt": "vtt",
}


class FormatError(ValueError):
    """The file is not a valid document of the chosen format (the message is Korean and English)."""


@dataclass(frozen=True)
class Gap:
    """One fixed character standing in for something between editable pieces: an entity, a tab, a line break."""

    char: str


Flow = list["str | Gap"]

_ENTITY = re.compile(r"&(?:#[0-9]{1,8}|#[xX][0-9A-Fa-f]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
_OBJECT = "￼"


def detect_format(path: Path) -> str:
    """The format a file name implies; ``text`` (plain text or Markdown) for anything else."""
    return _BY_SUFFIX.get(path.suffix.lower(), "text")


def is_binary(fmt: str) -> bool:
    """Whether the format is a binary container (.docx, .epub) rather than UTF-8 text."""
    return fmt in BINARY


def entity_char(entity: str) -> str:
    """A single non-Hangul character that stands for an entity while the converter reads the flow."""
    if entity.lower() in ("&nbsp;", "&#160;", "&#xa0;"):
        return " "
    s = html.unescape(entity)
    if len(s) != 1 or s == entity or "가" <= s <= "힣" or "一" <= s <= "鿿" or s.isalnum():
        return _OBJECT
    return s


def scan_text(src: str, start: int, end: int, flow: Flow, slots: list[tuple[int, int]]) -> None:
    """Add ``src[start:end]`` to a flow: text between entities is editable, each entity is a :class:`Gap`."""
    pos = start
    for m in _ENTITY.finditer(src, start, end):
        if m.start() > pos:
            flow.append(src[pos : m.start()])
            slots.append((pos, m.start()))
        flow.append(Gap(entity_char(m.group())))
        pos = m.end()
    if pos < end:
        flow.append(src[pos:end])
        slots.append((pos, end))


class Document:
    """A parsed file: ``flows`` in document order, and :meth:`rebuild` to write converted text back."""

    flows: list[Flow]

    def __init__(self, flows: list[Flow]) -> None:
        self.flows = flows

    def rebuild(self, edited: list[str]) -> str | bytes:
        """The file with its editable pieces (all flows, in order) replaced by ``edited``."""
        raise NotImplementedError

    def markup_flags(self) -> list[bool]:
        """For each flow, whether markup (``<ruby>``) may be written into it: HTML text, not Word, subtitles or NCX."""
        return [False] * len(self.flows)

    @property
    def slots(self) -> int:
        """How many editable pieces the document has."""
        return sum(1 for flow in self.flows for item in flow if isinstance(item, str))


class SpanDocument(Document):
    """A text file whose editable pieces are character ranges of the source; the rest is copied untouched."""

    def __init__(self, src: str, spans: list[tuple[int, int]], flows: list[Flow], *, markup: bool = False) -> None:
        super().__init__([f for f in flows if any(isinstance(i, str) for i in f)])
        self.src, self.spans, self.markup = src, spans, markup

    def markup_flags(self) -> list[bool]:
        return [self.markup] * len(self.flows)

    def rebuild(self, edited: list[str]) -> str:
        if len(edited) != len(self.spans):
            raise FormatError("내부 誤謬: 조각 數가 다릅니다 / internal error: piece count differs")
        out: list[str] = []
        pos = 0
        for (a, b), new in zip(self.spans, edited, strict=True):
            out.append(self.src[pos:a])
            out.append(new)
            pos = b
        out.append(self.src[pos:])
        return "".join(out)


@dataclass
class Converted:
    """The converted file (``text`` for text formats, ``bytes`` for binary ones), the extracted prose it was
    made from, and a :class:`~gukhan.convert.Result` whose offsets refer to that extracted prose."""

    output: str | bytes
    source_text: str
    result: Result


def _join(flow: Flow) -> str:
    return "".join(item.char if isinstance(item, Gap) else item for item in flow)


def _pieces(conv: Converter, flow: Flow, text: str, decisions: list[Decision], mark: bool) -> list[str] | None:
    """Cut the conversion of one flow back into its editable pieces, character by character.

    A converted word's Hanja replace its Hangul one for one, wherever the piece boundaries fall; a flagged
    word's ``{…}`` mark (``mark=True``) goes after its last character. None when that cannot be done exactly
    (a changed placeholder).
    """
    out = list(text)
    for d in decisions:
        if d.hangul != text[d.start : d.end]:
            return None
        out[d.start : d.end] = conv.decision_chars(d, text, mark)
    pieces: list[str] = []
    pos = 0
    for item in flow:
        if isinstance(item, Gap):
            if out[pos] != text[pos]:
                return None
            pos += 1
        else:
            pieces.append("".join(out[pos : pos + len(item)]))
            pos += len(item)
    return pieces


def convert_document(doc: Document, conv: Converter, *, mark: bool = False) -> Converted:
    """Convert every flow of ``doc`` and rebuild the file; only the converted words differ from the input."""
    joined = [_join(flow) for flow in doc.flows]
    flags = doc.markup_flags()
    ruby = conv.style == "ruby"
    if ruby and not any(flags):
        raise FormatError(
            "ruby 形式은 HTML 계열 出力에서만 쓸 수 있습니다 / the ruby style writes HTML <ruby> tags, so it works "
            "with HTML, EPUB, Markdown and text, not with Word or subtitle files"
        )
    own_evidence = "field" in conv.rules
    if own_evidence:
        conv.set_document(joined, markdown=False)
    edited: list[str] = []
    decisions: list[Decision] = []
    converted_text: list[str] = []
    base = 0
    style = conv.style
    try:
        for flow, text, markup in zip(doc.flows, joined, flags, strict=True):
            conv.style = "hanja-gloss" if ruby and not markup else style  # an EPUB's table of contents is plain text
            res = conv.convert(text, mark=mark, markdown=False)
            pieces = _pieces(conv, flow, text, res.decisions, mark)
            if pieces is None:  # cannot be cut exactly: convert piece by piece
                pieces = [conv.convert(item, mark=mark, markdown=False).text for item in flow if isinstance(item, str)]
            edited.extend(pieces)
            converted_text.append(res.text)
            decisions.extend(
                Decision(d.start + base, d.end + base, d.hangul, d.kind, d.hanja, d.candidates, d.reason, d.tag)
                for d in res.decisions
            )
            base += len(text) + 1
    finally:
        conv.style = style
        if own_evidence:
            conv.field_evidence = None
    return Converted(doc.rebuild(edited), "\n".join(joined), Result("\n".join(converted_text), decisions))


def load(fmt: str, data: str | bytes) -> Document:
    """Parse ``data`` (``str`` for html, srt and vtt; ``bytes`` for docx and epub) as format ``fmt``."""
    if fmt == "html":
        from .htmldoc import parse_html

        return parse_html(_text(data))
    if fmt in ("srt", "vtt"):
        from .subtitles import parse_subtitles

        return parse_subtitles(_text(data))
    if fmt == "docx":
        from .ooxml import parse_docx

        return parse_docx(_bytes(data))
    if fmt == "epub":
        from .epub import parse_epub

        return parse_epub(_bytes(data))
    raise FormatError(f"알 수 없는 形式입니다 / unknown format: {fmt}")


def _text(data: str | bytes) -> str:
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise FormatError("UTF-8이 아닙니다 / not UTF-8 text") from e
    return data


def _bytes(data: str | bytes) -> bytes:
    if isinstance(data, str):
        raise FormatError("이 形式은 binary입니다 / this format is binary, not text")
    return data


__all__ = [
    "FORMATS",
    "Converted",
    "Document",
    "FormatError",
    "Gap",
    "convert_document",
    "detect_format",
    "is_binary",
    "load",
]
