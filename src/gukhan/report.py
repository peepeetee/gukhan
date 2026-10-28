# SPDX-License-Identifier: Apache-2.0
"""Flagged-word report and review list."""

from __future__ import annotations

import bisect

from .convert import Decision, Kind, Result

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


def _context(text: str, d: Decision) -> str:
    left = text[max(0, d.start - CONTEXT) : d.start].replace("\n", " ")
    right = text[d.end : d.end + CONTEXT].replace("\n", " ")
    return f"{left}[{d.hangul}]{right}"


def _candidates(d: Decision) -> str:
    return " | ".join(f"{c.hanja}" + (f" ({c.sense})" if c.sense else "") for c in d.candidates)


def rows(source_text: str, result: Result) -> list[dict[str, str]]:
    starts = _line_starts(source_text)
    out = []
    for d in result.decisions:
        if d.kind not in (Kind.FLAGGED, Kind.REVIEW):
            continue
        line, col = _line_col(starts, d.start)
        out.append(
            {
                "kind": d.kind.value,
                "line": str(line),
                "col": str(col),
                "hangul": d.hangul,
                "candidates": _candidates(d),
                "context": _context(source_text, d),
            }
        )
    return out


def summary(result: Result) -> dict[str, int]:
    return {k.value: len(result.of(k)) for k in Kind}


def to_tsv(source_text: str, result: Result) -> str:
    header = "# kind\tline\tcol\thangul\tcandidates\tcontext\n"
    body = "".join("\t".join(r.values()) + "\n" for r in rows(source_text, result))
    s = summary(result)
    foot = "# " + " ".join(f"{k}={v}" for k, v in s.items()) + "\n"
    return header + body + foot


def to_markdown(source_text: str, result: Result) -> str:
    s = summary(result)
    lines = [
        "# gukhan 報告 / report",
        "",
        f"變換 converted: {s['converted']} · flag된 同音異義語 flagged: {s['flagged']} · "
        f"檢討 review: {s['review']} · 維持 kept: {s['kept']}",
        "",
        "| kind | line:col | 한글 | 候補 candidates | 文脈 context |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows(source_text, result):
        cands = r["candidates"].replace(" | ", " · ")
        ctx = r["context"].replace("|", "\\|")
        lines.append(f"| {r['kind']} | {r['line']}:{r['col']} | {r['hangul']} | {cands} | {ctx} |")
    return "\n".join(lines) + "\n"
