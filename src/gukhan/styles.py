# SPDX-License-Identifier: Apache-2.0
"""Output styles for readers who are learning Hanja.

``mixed``       國軍은 作戰 計劃          the default: Hanja replace the Hangul
``gloss``       국군(國軍)은 작전(作戰)    Hangul with the Hanja after it
``hanja-gloss`` 國軍(국군)은 作戰(작전)    Hanja with the Hangul reading after it
``ruby``        HTML ``<ruby>`` with the Hangul reading above each Hanja (one pair per character)

A style only changes how a converted word is written; which words are converted, flagged or kept is the same.
學習者를 위한 出力 形式: 變換되는 낱말은 같고 적는 方式만 다릅니다.
"""

from __future__ import annotations

STYLES = ("mixed", "gloss", "ruby", "hanja-gloss")
DEFAULT_STYLE = "mixed"


def check_style(style: str) -> str:
    """``style`` itself, or a ValueError (Korean and English) when it is not one of :data:`STYLES`."""
    if style not in STYLES:
        raise ValueError(f"알 수 없는 形式입니다 / unknown style {style!r}; choose one of {', '.join(STYLES)}")
    return style


def char_outputs(hangul: str, hanja: str, style: str = DEFAULT_STYLE) -> list[str]:
    """What to write for each character of ``hangul`` once it has been converted to ``hanja``.

    The list has one string per Hangul character, so a caller that edits text character by character (a word split
    over several HTML text nodes or Word runs) can put each piece where it belongs; joined, it is the word as written
    in ``style``. A gloss goes after the word's last character. ``ruby`` is a ruby pair per Hanja, so it stays valid
    wherever the pieces fall; if the Hanja and Hangul differ in length, one ruby covers the whole word.
    """
    n = len(hangul)
    aligned = len(hanja) == n
    base = list(hanja) if aligned else [hanja] + [""] * (n - 1)
    if style == "mixed" or hanja == hangul:
        return base
    if style == "gloss":
        outs = list(hangul)
        outs[-1] += f"({hanja})"
        return outs
    if style == "hanja-gloss":
        base[-1] += f"({hangul})"
        return base
    if style == "ruby":
        if aligned:
            return [c if c in (h, " ") else _ruby(c, h) for h, c in zip(hangul, hanja, strict=True)]
        return [_ruby(hanja, hangul)] + [""] * (n - 1)
    raise ValueError(f"알 수 없는 形式입니다 / unknown style {style!r}")


def _ruby(base: str, reading: str) -> str:
    return f"<ruby>{base}<rp>(</rp><rt>{reading}</rt><rp>)</rp></ruby>"


def render(hangul: str, hanja: str, style: str = DEFAULT_STYLE) -> str:
    """One converted word written in ``style``: ``render("국군", "國軍", "gloss") == "국군(國軍)"``."""
    return "".join(char_outputs(hangul, hanja, style))


__all__ = ["DEFAULT_STYLE", "STYLES", "char_outputs", "check_style", "render"]
