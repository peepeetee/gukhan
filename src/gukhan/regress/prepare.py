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


@dataclass
class Chars:
    """Per-character readings in Unihan order with education-set readings first, and how many
    readings carried the E tag (0 when chars.tsv has no tags)."""

    readings: dict[str, list[str]] = field(default_factory=dict)
    edu: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, list[str]]) -> Chars:
        return cls(dict(d), {})

    def get(self, ch: str, default: list[str] | None = None) -> list[str] | None:
        return self.readings.get(ch, default)


def load_chars(path: Path) -> Chars:
    """Read chars.tsv: ``hanja<TAB>reading:tag …`` (tags optional, Unihan order)."""
    out = Chars()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            ch, _, field_ = line.rstrip("\n").partition("\t")
            items = [v.split(":", 1) for v in field_.split()]
            edu = [r for r, *t in items if t and "E" in t[0]]
            rest = [r for r, *t in items if not (t and "E" in t[0])]
            out.readings[ch] = list(dict.fromkeys(edu + rest))
            out.edu[ch] = len(dict.fromkeys(edu))
    return out


def load_lexicon_hanja(path: Path) -> dict[str, str]:
    """``{compact hanja: compact hangul}`` from a lexicon.tsv, for word segmentation."""
    from gukhan.lexicon import Lexicon

    lex = Lexicon.load(path)
    best: dict[str, tuple[int, int, str]] = {}  # hanja → (weight, standard_rank, hangul)
    for entries in lex._by_key.values():
        for e in entries:
            hj, hg = e.hanja.replace(" ", ""), e.hangul.replace(" ", "")
            if not (all(is_cjk(c) for c in hj) and len(hj) == len(hg)):
                continue
            # several Hangul spellings for one Hanja word: keep the heaviest, ties → the one
            # that obeys the 頭音法則 (역사 over 력사), then the alphabetically first
            cand = (e.weight, _standard_rank(hg), hg)
            cur = best.get(hj)
            if (
                cur is None
                or (cand[0], cand[1]) > (cur[0], cur[1])
                or ((cand[0], cand[1]) == (cur[0], cur[1]) and hg < cur[2])
            ):
                best[hj] = cand
    return {hj: hg for hj, (_, _, hg) in best.items()}


def _standard_rank(hangul: str) -> int:
    """1 when the first syllable could not be a 頭音法則 violation, 0 when it starts with ㄹ or ㄴ+y."""
    ini, vow, _ = decompose(hangul[0]) if is_syllable(hangul[0]) else (0, 0, 0)
    initial, vowel = _INITIALS[ini], _VOWELS[vow]
    return 0 if initial == "ㄹ" or (initial == "ㄴ" and vowel in _Y_OR_I) else 1


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


def _pick(char: str, readings: list[str], next_char: str | None, chars: Chars) -> tuple[str, bool]:
    """Choose a reading; second value says whether it was a guess worth checking."""
    if len(readings) == 1:
        return readings[0], False
    pref = PREFER.get(char)
    if pref is None and chars.edu.get(char) == 1:
        return readings[0], False  # exactly one education-set reading: the usual one
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


MAX_WORD = 8


def prepare(mixed: str, chars: Chars | dict[str, list[str]], words: dict[str, str] | None = None) -> Prepared:
    """Hangul for ``mixed``.

    Each run of Hanja is first segmented by longest match against ``words``
    (Hanja → Hangul from a lexicon), which settles multi-reading characters
    and the 頭音法則 inside compounds (强制勞役 → 강제노역). Characters not
    covered by a word get their per-character reading, with the initial-sound
    rule at the start of each segment.
    """
    out: list[str] = []
    flags: list[Flag] = []
    unknown: list[str] = []
    if isinstance(chars, dict):
        chars = Chars.from_dict(chars)
    words = words or {}
    i = 0
    seg_start = True
    while i < len(mixed):
        ch = mixed[i]
        if not is_cjk(ch):
            out.append(ch)
            # a counter after a numeral keeps its dictionary reading: 4281年 → 4281년, 3里 → 3리
            seg_start = not ch.isdigit()
            i += 1
            continue
        matched = False
        for n in range(MAX_WORD, 1, -1):
            cand = mixed[i : i + n]
            if len(cand) == n and all(is_cjk(c) for c in cand) and cand in words:
                out.append(words[cand])
                i += n
                seg_start = True
                matched = True
                break
        if matched:
            continue
        readings = chars.get(ch)
        if not readings:
            unknown.append(ch)
            out.append(ch)
            seg_start = True
            i += 1
            continue
        nxt = mixed[i + 1] if i + 1 < len(mixed) else None
        chosen, guessed = _pick(ch, readings, nxt if nxt and is_cjk(nxt) else None, chars)
        if seg_start:
            chosen = _apply_initial_rule(chosen)
        if guessed:
            flags.append(Flag(i, ch, chosen, readings))
        out.append(chosen)
        seg_start = False
        i += 1
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
