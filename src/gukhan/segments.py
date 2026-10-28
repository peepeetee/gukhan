# SPDX-License-Identifier: Apache-2.0
"""Split text into convertible and protected spans.

Protected: fenced code blocks, inline code, URLs, e-mail addresses, and HTML
tags. Everything else is converted, including Markdown headings and links'
visible text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PROTECTED = re.compile(
    r"(?ms)"
    r"^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$"  # fenced code block
    r"|`[^`\n]+`"  # inline code
    r"|https?://\S+|www\.\S+"  # URLs
    r"|[\w.+-]+@[\w-]+\.[\w.-]+"  # e-mail
    r"|<[A-Za-z/!][^>\n]*>"  # HTML tag
)


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    protected: bool


def segment(text: str) -> list[Segment]:
    out: list[Segment] = []
    pos = 0
    for m in _PROTECTED.finditer(text):
        if m.start() > pos:
            out.append(Segment(pos, m.start(), False))
        out.append(Segment(m.start(), m.end(), True))
        pos = m.end()
    if pos < len(text):
        out.append(Segment(pos, len(text), False))
    return out
