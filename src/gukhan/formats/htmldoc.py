# SPDX-License-Identifier: Apache-2.0
"""HTML and XHTML: the text nodes are converted, every tag, attribute, comment and script stays as written."""

from __future__ import annotations

from html.parser import HTMLParser

from . import Flow, FormatError, Gap, SpanDocument, entity_char, scan_text

# Their contents are code or data, not prose; each stands for a break in the text around it.
_BLOCK_SKIP = frozenset({"script", "style", "pre", "textarea", "noscript", "template"})
# Inline code and ruby readings: left alone, and a placeholder keeps the words around them apart.
_INLINE_SKIP = frozenset({"code", "kbd", "samp", "rt", "rp"})
# A tag that ends the running prose (a different paragraph, cell, item or heading starts).
_BREAKS = frozenset(
    "html head body title p div section article aside nav header footer main blockquote figure figcaption address "
    "ul ol li dl dt dd table caption thead tbody tfoot tr td th form fieldset legend select option optgroup "
    "h1 h2 h3 h4 h5 h6 hr br details summary button label iframe object video audio canvas".split()
)
_OBJECT = "￼"


class _Collector(HTMLParser):
    def __init__(self, src: str) -> None:
        super().__init__(convert_charrefs=False)
        self.src = src
        self.starts = [0]
        for i, ch in enumerate(src):
            if ch == "\n":
                self.starts.append(i + 1)
        self.flows: list[Flow] = []
        self.spans: list[tuple[int, int]] = []
        self.flow: Flow = []
        self.skip: list[str] = []

    def _break(self) -> None:
        if any(isinstance(i, str) for i in self.flow):
            self.flows.append(self.flow)
        self.flow = []

    def _offset(self) -> int:
        line, col = self.getpos()
        return self.starts[line - 1] + col

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.append(tag)  # nested element of the same name: keep the count
            return
        if tag in _BLOCK_SKIP:
            self._break()
            self.skip.append(tag)
        elif tag in _INLINE_SKIP:
            self.flow.append(Gap(_OBJECT))
            self.skip.append(tag)
        elif tag in _BREAKS:
            self._break()

    def handle_endtag(self, tag: str) -> None:
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
                if not self.skip and tag in _BLOCK_SKIP:
                    self._break()
            return
        if tag in _BREAKS:
            self._break()

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        start = self._offset()
        if self.src[start : start + len(data)] != data:
            raise FormatError("HTML 위치를 찾지 못했습니다 / cannot locate text in the HTML")
        scan_text(self.src, start, start + len(data), self.flow, self.spans)

    def handle_entityref(self, name: str) -> None:
        if not self.skip:
            self.flow.append(Gap(entity_char(f"&{name};")))

    def handle_charref(self, name: str) -> None:
        if not self.skip:
            self.flow.append(Gap(entity_char(f"&#{name};")))


def parse_html(src: str) -> SpanDocument:
    """Read HTML or XHTML text; entities, comments, doctype, scripts, styles and code stay untouched."""
    parser = _Collector(src)
    parser.feed(src)
    parser.close()
    parser._break()
    return SpanDocument(src, parser.spans, parser.flows)
