# SPDX-License-Identifier: Apache-2.0
"""The conversion pipeline: analyse → longest match → override → rule → flag → splice."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .analyser import CANDIDATE_TAGS, TAG_TO_POS, Analyser, KiwiAnalyser, Token
from .lexicon import Entry, Lexicon
from .overrides import Overrides
from .segments import segment

MAX_PHRASE_TOKENS = 6
# Tags that may take part in a multi-token phrase match. Determiners, adverbs
# and dependent nouns are excluded so that 「세 시」 never becomes 세시.
PHRASE_TAGS = frozenset({"NNG", "NNP", "NR", "XR", "XPN", "XSN"})


def spacing_compatible(span: str, entry_hangul: str) -> bool:
    """A span written with spaces matches only an entry written with the same spaces.

    A span without spaces matches any entry (「작전계획」 finds 「작전 계획」),
    but 「세 시」 must not find 「세시」.
    """
    return " " not in span or span == entry_hangul


class Kind(str, Enum):
    CONVERTED = "converted"  # Hanja written
    FLAGGED = "flagged"  # several candidates, left in Hangul, needs a human
    REVIEW = "review"  # proper noun or unknown word with no entry
    KEPT = "kept"  # override said keep Hangul
    NONE = "none"  # internal: entries exist but none fits the token's tag; not recorded


@dataclass(frozen=True)
class Decision:
    start: int
    end: int
    hangul: str
    kind: Kind
    hanja: str | None = None
    candidates: tuple[Entry, ...] = ()
    reason: str = ""
    tag: str = ""


@dataclass
class Result:
    text: str
    decisions: list[Decision] = field(default_factory=list)

    def of(self, kind: Kind) -> list[Decision]:
        return [d for d in self.decisions if d.kind == kind]


def _is_hangul(s: str) -> bool:
    return all("가" <= c <= "힣" for c in s)


def _apply_spacing(original: str, hanja_compact: str) -> str:
    out, i = [], 0
    for ch in original:
        if ch == " ":
            out.append(" ")
        else:
            out.append(hanja_compact[i])
            i += 1
    return "".join(out)


def decide(
    hangul: str,
    tag: str,
    candidates: list[Entry],
    override: tuple[bool, Entry | None] = (False, None),
) -> Decision:
    """Override → rule → flag, for one matched span. Offsets are filled by the caller."""
    has, entry = override
    if has:
        if entry is None:
            return Decision(0, 0, hangul, Kind.KEPT, reason="override: keep Hangul", tag=tag)
        return Decision(0, 0, hangul, Kind.CONVERTED, entry.hanja, (entry,), "override", tag)
    allowed = TAG_TO_POS.get(tag)
    pool = [c for c in candidates if allowed is None or c.pos in allowed]
    if not pool:
        return Decision(0, 0, hangul, Kind.NONE, reason=f"no entry fits tag {tag}", tag=tag)
    forms = sorted({c.hanja.replace(" ", "") for c in pool})
    if len(forms) == 1:
        why = "single entry" if len(pool) == 1 else "all candidates agree"
        if len(pool) < len(candidates):
            why += f" after POS filter ({tag})"
        return Decision(0, 0, hangul, Kind.CONVERTED, forms[0], tuple(pool), why, tag)
    return Decision(0, 0, hangul, Kind.FLAGGED, None, tuple(rank(pool)), f"{len(forms)} readings", tag)


_POS_RANK = {"명사": 0, "의존 명사": 1, "부사": 1, "어근": 1, "접두사": 1, "접미사": 1, "고유 명사": 2}


def rank(entries: list[Entry]) -> list[Entry]:
    """Likely readings first: builder weight, then glossed entries, common nouns before proper nouns."""
    return sorted(entries, key=lambda e: (-e.weight, not e.sense, _POS_RANK.get(e.pos, 1), e.hanja))


class Converter:
    def __init__(
        self,
        lexicon: Lexicon | None = None,
        overrides: Overrides | None = None,
        analyser: Analyser | None = None,
        *,
        review_all: bool = False,
    ) -> None:
        self.lexicon = lexicon if lexicon is not None else Lexicon.sample()
        self.overrides = overrides
        self.analyser = analyser if analyser is not None else KiwiAnalyser()
        self.review_all = review_all

    # -- lookup helpers -------------------------------------------------
    def _max_key_len(self) -> int:
        return max(self.lexicon.max_key_len, self.overrides.max_key_len if self.overrides else 0)

    def _lookup(self, span: str) -> tuple[bool, Entry | None, list[Entry]]:
        """(has_override, override_entry, lexicon_candidates) for a text span."""
        has_ov, ov = False, None
        if self.overrides:
            has_ov, ov = self.overrides.get(span)
            if has_ov and ov is not None and not spacing_compatible(span, ov.hangul):
                has_ov, ov = False, None
        cands = [c for c in self.lexicon.candidates(span) if spacing_compatible(span, c.hangul)]
        return has_ov, ov, cands

    def _candidate_tokens(self, text: str, tokens: list[Token]) -> list[Token]:
        return [t for t in tokens if t.tag in CANDIDATE_TAGS and text[t.start : t.end] == t.form and _is_hangul(t.form)]

    # -- main pipeline --------------------------------------------------
    def convert_span(self, text: str, base: int = 0) -> list[Decision]:
        """Decisions for one convertible span; offsets are relative to ``base``."""
        cands = self._candidate_tokens(text, self.analyser.tokenize(text))
        decisions: list[Decision] = []
        max_len = self._max_key_len()
        i = 0
        while i < len(cands):
            matched = False
            for n in range(min(MAX_PHRASE_TOKENS, len(cands) - i), 0, -1):
                first, last = cands[i], cands[i + n - 1]
                span = text[first.start : last.end]
                if len(span.replace(" ", "")) > max_len:
                    continue
                if n > 1 and (
                    first.tag not in PHRASE_TAGS
                    or not all(
                        text[cands[k].end : cands[k + 1].start] in ("", " ") and cands[k + 1].tag in PHRASE_TAGS
                        for k in range(i, i + n - 1)
                    )
                ):
                    continue
                has_ov, ov, lex_cands = self._lookup(span)
                if not has_ov and not lex_cands:
                    continue
                d = decide(span, first.tag, lex_cands, (has_ov, ov))
                if d.kind == Kind.NONE:
                    continue
                hanja = _apply_spacing(span, d.hanja) if d.hanja else None
                decisions.append(
                    Decision(base + first.start, base + last.end, span, d.kind, hanja, d.candidates, d.reason, d.tag)
                )
                i += n
                matched = True
                break
            if not matched:
                t = cands[i]
                if t.tag == "NNP" or (self.review_all and t.tag in ("NNG", "XR")):
                    decisions.append(
                        Decision(
                            base + t.start, base + t.end, t.form, Kind.REVIEW, reason=f"no entry ({t.tag})", tag=t.tag
                        )
                    )
                i += 1
        return decisions

    def convert(self, text: str, *, mark: bool = False) -> Result:
        decisions: list[Decision] = []
        for seg in segment(text):
            if not seg.protected:
                decisions.extend(self.convert_span(text[seg.start : seg.end], seg.start))
        out, pos = [], 0
        for d in decisions:
            out.append(text[pos : d.start])
            if d.kind == Kind.CONVERTED:
                out.append(d.hanja)
            elif d.kind == Kind.FLAGGED and mark:
                out.append(d.hangul + "{" + "|".join(c.hanja for c in d.candidates) + "}")
            else:
                out.append(d.hangul)
            pos = d.end
        out.append(text[pos:])
        return Result("".join(out), decisions)


def convert(text: str, **kwargs) -> Result:
    """One-shot helper: ``convert("국군은 작전 계획을 수립하였다.").text``."""
    mark = kwargs.pop("mark", False)
    return Converter(**kwargs).convert(text, mark=mark)
