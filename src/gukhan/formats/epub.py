# SPDX-License-Identifier: Apache-2.0
"""EPUB: the XHTML chapters and the table of contents (NCX) are converted; the package file, metadata, images,
styles and fonts are copied byte for byte (the archive keeps its member order, so ``mimetype`` stays first)."""

from __future__ import annotations

import re

from . import Flow, FormatError, SpanDocument, scan_text
from .htmldoc import parse_html
from .ooxml import ZipDocument, decode_part
from .ziputil import read_zip

_XHTML = re.compile(r".*\.(?:xhtml|html|htm)", re.IGNORECASE)
_NCX = re.compile(r".*\.ncx", re.IGNORECASE)
_NCX_TEXT = re.compile(r"<(?:\w+:)?text(?:\s[^>]*?)?(?<!/)>(?P<text>[^<]*)</(?:\w+:)?text>")


def parse_ncx(src: str) -> SpanDocument:
    """A table of contents: each ``<text>`` label is its own flow."""
    spans: list[tuple[int, int]] = []
    flows: list[Flow] = []
    for m in _NCX_TEXT.finditer(src):
        flow: Flow = []
        scan_text(src, m.start("text"), m.end("text"), flow, spans)
        flows.append(flow)
    return SpanDocument(src, spans, flows)


def parse_epub(data: bytes) -> ZipDocument:
    """Read an EPUB container."""
    entries = read_zip(data)
    mime = next((e for e in entries if e.info.filename == "mimetype"), None)
    if mime is None or mime.data.strip() != b"application/epub+zip":
        raise FormatError("EPUB이 아닙니다 / not an EPUB (no mimetype entry saying application/epub+zip)")
    parts: dict[int, SpanDocument] = {}
    for i, e in enumerate(entries):
        name = e.info.filename
        if _XHTML.fullmatch(name):
            parts[i] = parse_html(decode_part(e))
        elif _NCX.fullmatch(name):
            parts[i] = parse_ncx(decode_part(e))
    return ZipDocument(entries, parts, data)
