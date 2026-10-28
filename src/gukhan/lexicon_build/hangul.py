# SPDX-License-Identifier: Apache-2.0
"""Hangul syllable helpers: decomposition and 頭音法則 (initial-sound rule)."""

from __future__ import annotations

_BASE = 0xAC00
_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_Y_OR_I_VOWELS = set("ㅣㅑㅒㅕㅖㅛㅠㅖ")


def is_syllable(ch: str) -> bool:
    return len(ch) == 1 and _BASE <= ord(ch) <= 0xD7A3


def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x3134F


def decompose(ch: str) -> tuple[int, int, int]:
    code = ord(ch) - _BASE
    return code // 588, (code % 588) // 28, code % 28


def compose(initial: int, vowel: int, final: int) -> str:
    return chr(_BASE + initial * 588 + vowel * 28 + final)


def initial_sound_variants(syllable: str) -> set[str]:
    """Return the syllable plus its 頭音法則 forms (리→이, 로→노, 녀→여 …).

    Used when a Hanja character's dictionary reading differs from the way it
    is written at the start of a word.
    """
    if not is_syllable(syllable):
        return {syllable}
    ini, vow, fin = decompose(syllable)
    out = {syllable}
    r, n, ieung = _INITIALS.index("ㄹ"), _INITIALS.index("ㄴ"), _INITIALS.index("ㅇ")
    vowel_ch = _VOWELS[vow]
    if ini == r:
        if vowel_ch in _Y_OR_I_VOWELS:
            out.add(compose(ieung, vow, fin))
        else:
            out.add(compose(n, vow, fin))
            out.add(compose(ieung, vow, fin))  # 례→예, 료→요 handled above; 라→나
    elif ini == n and vowel_ch in _Y_OR_I_VOWELS:
        out.add(compose(ieung, vow, fin))
    return out
