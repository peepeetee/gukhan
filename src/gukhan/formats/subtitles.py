# SPDX-License-Identifier: Apache-2.0
"""SubRip (.srt) and WebVTT (.vtt): only the text lines of a cue are converted.

Cue numbers and identifiers, timing lines, ``WEBVTT`` headers, ``NOTE``, ``STYLE`` and ``REGION`` blocks, styling
tags (``<i>``, ``<v Speaker>``, ``<00:00:01.000>``, ``{\\an8}``) and the line endings stay exactly as written.
"""

from __future__ import annotations

import re

from . import Flow, Gap, SpanDocument, scan_text

_LINE = re.compile(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+")
_TIMING = re.compile(r"\s*(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3}\s+-->\s+(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3}")
_TAG = re.compile(r"<[^>\n]*>|\{\\[^}\n]*\}")
_NON_CUE = ("NOTE", "STYLE", "REGION", "WEBVTT")


def parse_subtitles(src: str) -> SpanDocument:
    """Read SRT or WebVTT text into one flow per cue."""
    spans: list[tuple[int, int]] = []
    flows: list[Flow] = []
    block: list[tuple[int, str]] = []  # (offset of the line, the line without its ending)

    def finish() -> None:
        if block:
            first = block[0][1].lstrip("﻿").lstrip()
            at = next((i for i, (_, line) in enumerate(block) if _TIMING.match(line)), None)
            if at is not None and not (first.startswith(_NON_CUE) and at > 0):
                flows.append(_cue(src, block[at + 1 :], spans))
        block.clear()

    for m in _LINE.finditer(src):
        line = m.group().rstrip("\r\n")
        if line.strip() == "":
            finish()
        else:
            block.append((m.start(), line))
    finish()
    return SpanDocument(src, spans, flows)


def _cue(src: str, lines: list[tuple[int, str]], spans: list[tuple[int, int]]) -> Flow:
    flow: Flow = []
    for n, (offset, line) in enumerate(lines):
        if n:
            flow.append(Gap(" "))  # a wrapped line: the words on both sides may belong together
        pos = 0
        for m in _TAG.finditer(line):
            scan_text(src, offset + pos, offset + m.start(), flow, spans)
            pos = m.end()
        scan_text(src, offset + pos, offset + len(line), flow, spans)
    return flow
