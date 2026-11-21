# SPDX-License-Identifier: Apache-2.0
"""Split text into convertible and protected spans.

Protected: fenced code blocks (also indented ones), inline code, URLs, e-mail
addresses, HTML tags, comments, script and style blocks, and Markdown link destinations. Everything else is
converted, including Markdown headings and links' visible text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PROTECTED = re.compile(
    r"(?msi)"
    # fenced code block, CommonMark style: may be indented (inside a list item), closes on a
    # fence of the same character at least as long, and runs to the end of the text when unclosed
    r"^[ \t]*(?P<bt>`{3,})[^`\n]*\n(?:.*?^[ \t]*(?P=bt)`*[ \t]*$|.*\Z)"
    r"|^[ \t]*(?P<td>~{3,})[^\n]*\n(?:.*?^[ \t]*(?P=td)~*[ \t]*$|.*\Z)"
    r"|<!--.*?-->"  # HTML comment, possibly over several lines
    r"|<(?P<raw>script|style)\b[^>]*>.*?</(?P=raw)\s*>"  # code and CSS in an HTML file
    r"|(?P<tick>`+)(?!`)[^\n]*?(?<!`)(?P=tick)(?!`)"  # inline code, any run of backticks
    r"|https?://\S+|www\.\S+"  # URLs
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"  # e-mail, ASCII only
    r"|<[A-Za-z/!][^>\n]*>"  # HTML tag
    r"|(?<=\])\([^)\n]*\)"  # Markdown link or image destination: [text](path/문서.md "title")
)


# Prose that came out of a structured file (HTML text nodes, Word runs, subtitle cues): there is no Markdown to
# protect, so a backtick or a bracket is just a character; only addresses stay untouched.
_PROTECTED_PROSE = re.compile(r"(?i)https?://\S+|www\.\S+|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    protected: bool


def segment(text: str, *, markdown: bool = True) -> list[Segment]:
    """Alternate convertible and protected spans; ``markdown=False`` protects only URLs and e-mail addresses."""
    out: list[Segment] = []
    pos = 0
    for m in (_PROTECTED if markdown else _PROTECTED_PROSE).finditer(text):
        if m.start() > pos:
            out.append(Segment(pos, m.start(), False))
        out.append(Segment(m.start(), m.end(), True))
        pos = m.end()
    if pos < len(text):
        out.append(Segment(pos, len(text), False))
    return out
