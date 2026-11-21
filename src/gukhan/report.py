# SPDX-License-Identifier: Apache-2.0
"""Flagged-word report and review list."""

from __future__ import annotations

import bisect
import re
from collections.abc import Mapping

from .convert import Decision, Kind, Result
from .suggest import Suggestion, describe

CONTEXT = 12


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_col(starts: list[int], offset: int) -> tuple[int, int]:
    line = bisect.bisect_right(starts, offset) - 1
    return line + 1, offset - starts[line] + 1


_WHITESPACE = re.compile(r"\s")
# C0/C1 controls (ESC starts a terminal escape sequence), line/paragraph separators and the bidirectional
# overrides that can reorder what a terminal shows
_UNSAFE = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029\u202a-\u202e\u2066-\u2069]")


def one_line(s: str) -> str:
    """Every line break and tab becomes a space, so a context never breaks a TSV row or a terminal line.

    Other control characters become ``�``: a text that is only being shown (``gukhan review``, reports) must
    not be able to send escape sequences to the reader's terminal.
    """
    return _UNSAFE.sub("\ufffd", _WHITESPACE.sub(" ", s))


def _context(text: str, d: Decision) -> str:
    left = one_line(text[max(0, d.start - CONTEXT) : d.start])
    right = one_line(text[d.end : d.end + CONTEXT])
    return f"{left}[{d.hangul}]{right}"


def _candidates(d: Decision) -> str:
    return " | ".join(f"{c.hanja}" + (f" ({one_line(c.sense)})" if c.sense else "") for c in d.candidates)


Suggestions = Mapping[tuple[int, int], Suggestion]


def rows(source_text: str, result: Result, suggestions: Suggestions | None = None) -> list[dict[str, str]]:
    starts = _line_starts(source_text)
    out = []
    for d in result.decisions:
        if d.kind not in (Kind.FLAGGED, Kind.REVIEW):
            continue
        line, col = _line_col(starts, d.start)
        row = {
            "kind": d.kind.value,
            "line": str(line),
            "col": str(col),
            "hangul": d.hangul,
            "candidates": _candidates(d),
            "context": _context(source_text, d),
        }
        if suggestions is not None:
            # a model's hint, not a decision: the column says so and is empty when it abstained
            row["suggestion"] = describe(suggestions.get((d.start, d.end)))
        out.append(row)
    return out


def summary(result: Result) -> dict[str, int]:
    return {k.value: len(result.of(k)) for k in Kind}


def to_tsv(source_text: str, result: Result, suggestions: Suggestions | None = None) -> str:
    header = "# kind\tline\tcol\thangul\tcandidates\tcontext" + ("\tsuggestion" if suggestions is not None else "")
    header += "\n"
    body = "".join("\t".join(r.values()) + "\n" for r in rows(source_text, result, suggestions))
    s = summary(result)
    foot = "# " + " ".join(f"{k}={v}" for k, v in s.items()) + "\n"
    return header + body + foot


def to_markdown(source_text: str, result: Result, suggestions: Suggestions | None = None) -> str:
    s = summary(result)
    lines = [
        "# gukhan 報告 / report",
        "",
        f"變換 converted: {s['converted']} · flag된 同音異義語 flagged: {s['flagged']} · "
        f"檢討 review: {s['review']} · 維持 kept: {s['kept']}",
        "",
        "| kind | line:col | 한글 | 候補 candidates | 文脈 context |"
        + (" 提案 suggestion (unconfirmed) |" if suggestions is not None else ""),
        "| --- | --- | --- | --- | --- |" + (" --- |" if suggestions is not None else ""),
    ]
    for r in rows(source_text, result, suggestions):
        cands = r["candidates"].replace(" | ", " · ").replace("|", "\\|")
        ctx = r["context"].replace("|", "\\|")
        extra = f" {r['suggestion'].replace('|', chr(92) + '|')} |" if "suggestion" in r else ""
        lines.append(f"| {r['kind']} | {r['line']}:{r['col']} | {r['hangul']} | {cands} | {ctx} |{extra}")
    return "\n".join(lines) + "\n"
