# SPDX-License-Identifier: Apache-2.0
"""Derive Hangul input from mixed-script gold text.

Each Hanja character is replaced by its Sino-Korean reading. Readings come
from ``chars.tsv`` (written by ``gukhan-lexicon-build --unihan``). The 頭音法則
is applied to the first character of each Hanja run. Characters with more
than one reading use a small built-in preference table; anything else with
several readings is replaced by the first and flagged so a human checks it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gukhan.lexicon_build.hangul import compose, decompose, is_cjk, is_syllable

# Reading preferences for common multi-reading characters: (default, {next-initial → reading}).
# 不 reads 부 before ㄷ/ㅈ (不動 부동, 不正 부정) and 불 otherwise.
_DT = frozenset("ㄷㄸㅈㅉ")
PREFER: dict[str, tuple[str, dict[frozenset[str], str]]] = {
    "不": ("불", {_DT: "부"}),
    "金": ("금", {}),
    "樂": ("락", {}),
    "率": ("률", {}),
    "說": ("설", {}),
    "省": ("성", {}),
    "殺": ("살", {}),
    "參": ("참", {}),
    "宅": ("택", {}),
    "車": ("차", {}),
    "復": ("복", {}),
    "便": ("편", {}),
    "讀": ("독", {}),
    "惡": ("악", {}),
    "識": ("식", {}),
    "數": ("수", {}),
    "切": ("절", {}),
    "暴": ("폭", {}),
    "布": ("포", {}),
    "拓": ("척", {}),
    "糖": ("당", {}),
    "咽": ("인", {}),
    "辰": ("진", {}),
    "更": ("경", {}),
    "降": ("강", {}),
    "見": ("견", {}),
    "句": ("구", {}),
    "龜": ("귀", {}),
    "洞": ("동", {}),
    "北": ("북", {}),
    "否": ("부", {}),
    "分": ("분", {}),
    "沈": ("침", {}),
    "葉": ("엽", {}),
    "刺": ("자", {}),
    "狀": ("상", {}),
    "則": ("칙", {}),
    "歲": ("세", {}),
    "什": ("십", {}),
    "拾": ("습", {}),
    "滑": ("활", {}),
    "寧": ("녕", {}),
    "諾": ("낙", {}),
    "契": ("계", {}),
    "推": ("추", {}),
    "徵": ("징", {}),
}
_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"


@dataclass
class Flag:
    position: int
    char: str
    chosen: str
    readings: list[str]


@dataclass
class Prepared:
    hangul: str
    flags: list[Flag] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


def load_chars(path: Path) -> dict[str, list[str]]:
    """Read chars.tsv (``hanja<TAB>reading reading …``)."""
    out: dict[str, list[str]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            ch, _, readings = line.rstrip("\n").partition("\t")
            out[ch] = readings.split()
    return out


_Y_OR_I = frozenset("ㅣㅑㅒㅕㅖㅛㅠ")
_VOWELS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"


def _apply_initial_rule(syllable: str) -> str:
    """頭音法則 for a word-initial syllable: 력→역, 락→낙, 로→노, 녀→여, 리→이."""
    ini, vow, fin = decompose(syllable)
    initial, vowel = _INITIALS[ini], _VOWELS[vow]
    if initial == "ㄹ":
        new = "ㅇ" if vowel in _Y_OR_I else "ㄴ"
    elif initial == "ㄴ" and vowel in _Y_OR_I:
        new = "ㅇ"
    else:
        return syllable
    return compose(_INITIALS.index(new), vow, fin)


def _pick(char: str, readings: list[str], next_char: str | None, chars: dict[str, list[str]]) -> tuple[str, bool]:
    """Choose a reading; second value says whether it was a guess worth checking."""
    if len(readings) == 1:
        return readings[0], False
    pref = PREFER.get(char)
    if pref:
        default, by_next = pref
        if next_char and by_next:
            nxt = chars.get(next_char, [next_char])[0]
            if is_syllable(nxt):
                ini = _INITIALS[decompose(nxt)[0]]
                for initials, reading in by_next.items():
                    if ini in initials and reading in readings:
                        return reading, False
        if default in readings:
            return default, False
    return readings[0], True


def prepare(mixed: str, chars: dict[str, list[str]]) -> Prepared:
    out: list[str] = []
    flags: list[Flag] = []
    unknown: list[str] = []
    run_start = True
    for i, ch in enumerate(mixed):
        if not is_cjk(ch):
            out.append(ch)
            run_start = True
            continue
        readings = chars.get(ch)
        if not readings:
            unknown.append(ch)
            out.append(ch)
            run_start = True
            continue
        nxt = mixed[i + 1] if i + 1 < len(mixed) else None
        chosen, guessed = _pick(ch, readings, nxt if nxt and is_cjk(nxt) else None, chars)
        if run_start:
            chosen = _apply_initial_rule(chosen)
        if guessed:
            flags.append(Flag(i, ch, chosen, readings))
        out.append(chosen)
        run_start = False
    return Prepared("".join(out), flags, unknown)


_SENTENCE_END = re.compile(r"(?<=[.。!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split on blank lines and sentence-final punctuation; keeps articles as units."""
    items: list[str] = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        items.extend(s for s in _SENTENCE_END.split(para) if s.strip())
    return items
