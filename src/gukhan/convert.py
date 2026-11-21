# SPDX-License-Identifier: Apache-2.0
"""The conversion pipeline: analyse → longest match → override → rule → flag → splice."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, replace
from enum import Enum

from . import rules
from .analyser import CANDIDATE_TAGS, NATIVE_STOP, TAG_TO_POS, VERB_SUFFIXES, Analyser, KiwiAnalyser, Token
from .lexicon import Entry, Lexicon
from .overrides import Overrides
from .segments import segment

MAX_PHRASE_TOKENS = 6
# Measured on the 1948 constitution: a cutoff of 12 cut wrong from 1.4% to 0.5% but right
# from 48.7% to 21.7%, so the default is off; pass --min-weight to trade coverage for caution.
DEFAULT_MIN_WEIGHT = 0
# Tags that may take part in a multi-token phrase match. Determiners, adverbs
# and dependent nouns are excluded so that 「세 시」 never becomes 세시.
PHRASE_TAGS = frozenset({"NNG", "NNP", "NR", "XR", "XPN", "XSN"})
# Kiwi's running time grows faster than linearly with the length of one call (about 75 times slower
# for a 16 times longer text), so long spans are analysed in pieces of about this many characters.
# Pieces end at a line break, else after a sentence, else at a space; a phrase never spans one.
CHUNK_CHARS = 2000
_SENTENCE_END = re.compile(r"[.!?。…][\"'”’)\]]*\s")


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


_JAMO_SYLLABLE = re.compile("[\u1100-\u1112][\u1161-\u1175][\u11a8-\u11c2]?")
_IGNORABLE = "\u200b\u200c\u200d\u2060\ufeff\u00ad"
_NEEDS_NORMALISING = re.compile("[\u1100-\u11ff" + _IGNORABLE + "]")


def _normalise(text: str) -> tuple[str, list[int], list[int]] | None:
    """``text`` with jamo composed and zero-width characters dropped, plus each kept character's
    original start and end offsets; None when there is nothing to change."""
    if not _NEEDS_NORMALISING.search(text):
        return None
    plain: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _IGNORABLE:
            i += 1
            continue
        m = _JAMO_SYLLABLE.match(text, i)
        if m:
            plain.append(unicodedata.normalize("NFC", m.group()))
            starts.append(i)
            ends.append(m.end())
            i = m.end()
        else:
            plain.append(ch)
            starts.append(i)
            ends.append(i + 1)
            i += 1
    return "".join(plain), starts, ends


def chunk_bounds(s: str, limit: int | None = None) -> list[tuple[int, int]]:
    """Split ``s`` into consecutive ``(start, end)`` pieces of at most ``limit`` characters.

    The cut falls after the last line break inside the limit, else after the last sentence end,
    else after the last space, else at the limit itself.
    """
    limit = limit or CHUNK_CHARS
    out, pos = [], 0
    while pos < len(s):
        end = min(pos + limit, len(s))
        if end < len(s):
            cut = s.rfind("\n", pos, end) + 1
            if cut <= pos:
                ends = [m.end() for m in _SENTENCE_END.finditer(s, pos, end)]
                cut = ends[-1] if ends else s.rfind(" ", pos, end) + 1
            if cut > pos:
                end = cut
        out.append((pos, end))
        pos = end
    return out


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


def is_native_entry(e: Entry) -> bool:
    """An entry whose Hanja column repeats the Hangul marks a native word of the same sound (안 = inside)."""
    return e.hanja.replace(" ", "") == e.hangul.replace(" ", "")


def decide(
    hangul: str,
    tag: str,
    candidates: list[Entry],
    override: tuple[bool, Entry | None] = (False, None),
    *,
    min_weight: int = 0,
    attested: str = "",
) -> Decision:
    """Override → rule → flag, for one matched span. Offsets are filled by the caller.

    ``min_weight`` > 0 means a lone candidate is written only when its weight
    reaches it; a rarer single entry is flagged instead, because one entry in
    a crowd-sourced lexicon is no proof that no other reading exists.

    ``attested`` is the note of a rule that already narrowed the candidates
    (「attested as 중요하다」, 「ordinal prefix before a number」). A lone survivor of
    two or more syllables then rests on that evidence, so the weight caution does
    not apply. One syllable stays flagged: the dictionary lists 부하다 (富) but not
    附하다, so a lone verb is a gap, not proof.
    """
    has, entry = override
    if has:
        if entry is None:
            return Decision(0, 0, hangul, Kind.KEPT, reason="override: keep Hangul", tag=tag)
        return Decision(0, 0, hangul, Kind.CONVERTED, entry.hanja.replace(" ", ""), (entry,), "override", tag)
    allowed = TAG_TO_POS.get(tag)
    pool = [c for c in candidates if allowed is None or c.pos in allowed]
    if not pool or all(is_native_entry(c) for c in pool):
        return Decision(0, 0, hangul, Kind.NONE, reason=f"no entry fits tag {tag}", tag=tag)
    forms = sorted({c.hanja.replace(" ", "") for c in pool})
    if len(forms) == 1:
        why = "single entry" if len(pool) == 1 else "all candidates agree"
        if len(pool) < len(candidates):
            why += f" after POS filter ({tag})"
        if attested and len(hangul.replace(" ", "")) > 1:
            return Decision(0, 0, hangul, Kind.CONVERTED, forms[0], tuple(pool), f"{why}, {attested}", tag)
        if len(hangul.replace(" ", "")) == 1 and tag in ("NNG", "NNP", "NR", "XR"):
            # one syllable, one entry: almost every Sino-Korean syllable has many Hanja, so a
            # lone entry is a lexicon gap, not evidence (前項 → 全항 came from this)
            return Decision(0, 0, hangul, Kind.FLAGGED, None, tuple(pool), f"{why}, single syllable", tag)
        if min_weight and max(c.weight for c in pool) < min_weight:
            return Decision(0, 0, hangul, Kind.FLAGGED, None, tuple(pool), f"{why}, weight below {min_weight}", tag)
        return Decision(0, 0, hangul, Kind.CONVERTED, forms[0], tuple(pool), why, tag)
    return Decision(0, 0, hangul, Kind.FLAGGED, None, tuple(rank(pool)), f"{len(forms)} readings", tag)


_POS_RANK = {"명사": 0, "의존 명사": 1, "부사": 1, "어근": 1, "접두사": 1, "접미사": 1, "고유 명사": 2}


def rank(entries: list[Entry]) -> list[Entry]:
    """Likely readings first: builder weight, then glossed entries, common nouns before proper nouns."""
    return sorted(
        entries,
        key=lambda e: (
            -e.weight,
            -e.level,
            e.learner_rank or float("inf"),
            not e.sense,
            _POS_RANK.get(e.pos, 1),
            e.hanja,
        ),
    )


def _forms_of(cands: list[Entry]) -> set[str]:
    return {c.hanja.replace(" ", "") for c in cands}


class Converter:
    def __init__(
        self,
        lexicon: Lexicon | None = None,
        overrides: Overrides | None = None,
        analyser: Analyser | None = None,
        *,
        review_all: bool = False,
        min_weight: int | None = None,
        use_rules: bool | frozenset[str] = True,
        field_evidence: Counter[str] | None = None,
    ) -> None:
        self.lexicon = lexicon if lexicon is not None else Lexicon.sample()
        self.overrides = overrides
        self.analyser = analyser if analyser is not None else KiwiAnalyser()
        self.review_all = review_all
        self.rules = rules.DEFAULT if use_rules is True else frozenset(use_rules or ())
        if min_weight is None:
            min_weight = DEFAULT_MIN_WEIGHT if self.lexicon.weighted else 0
        self.min_weight = min_weight
        # Words per dictionary field that the text settled without the ``field`` rule; None = not computed yet.
        self.field_evidence = field_evidence

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
        out: list[Token] = []
        for i, t in enumerate(tokens):
            if (
                t.tag not in CANDIDATE_TAGS
                or text[t.start : t.end] != t.form
                or not _is_hangul(t.form)
                or (t.tag == "NNB" and t.form in NATIVE_STOP)
            ):
                continue
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if t.tag in ("NNG", "XR") and nxt is not None and nxt.start == t.end:
                tail = VERB_SUFFIXES.get((nxt.form, nxt.tag))
                if tail:
                    t = replace(t, suffix=tail[0], suffix_pos=tail[1])
            out.append(t)
        return out

    def _after_number(self, toks: list[Token], tok: Token) -> bool:
        """The token before ``tok`` is a number (digits, Sino-Korean numeral, or a 몇/각-type determiner)."""
        if tok.idx <= 0:
            return False
        prev = toks[tok.idx - 1]
        return prev.tag in ("SN", "NR", "MM") and tok.start - prev.end <= 1

    def _narrow_by_context(self, toks: list[Token], tok: Token, cands: list[Entry]) -> tuple[list[Entry], str]:
        """Apply the evidence rules of ``rules`` that depend on the neighbouring tokens."""
        note = ""
        active = self.rules
        before = toks[tok.idx - 1] if tok.idx > 0 else None
        after = toks[tok.idx + 1] if 0 <= tok.idx + 1 < len(toks) else None
        if "counter" in active and tok.tag == "NNB" and not self._after_number(toks, tok):
            # 일 (日, 「날을 세는 단위」) and 시 (時) are counters only after a count; alone they are native words
            pool = [c for c in cands if c.pos in TAG_TO_POS["NNB"]]
            if pool and all(rules.UNIT_SENSE in c.sense for c in pool):
                return [], "counter without a number"
        if tok.tag == "NNG" and "name" in active:
            kept = rules.drop_proper_names(cands)
            if len(kept) < len(cands):
                cands, note = kept, "common noun, not a name"
        glued = before is not None and before.end == tok.start and before.tag in ("NNG", "NNB", "NR", "XPN", "MM")
        if "field" in active and tok.tag in ("NNG", "XR") and self.field_evidence is not None and not glued:
            kept = rules.drop_unevidenced_fields(cands, self.field_evidence)
            if len(kept) < len(cands):
                cands, note = kept, note or "everyday word, no sign of a specialist field"
        if "sense" in active and tok.tag == "NNG" and len(_forms_of(cands)) > 1:
            lo = max((t.idx for t in toks[: tok.idx] if t.tag == "SF"), default=-1) + 1
            hi = min((t.idx for t in toks[tok.idx :] if t.tag == "SF"), default=len(toks))
            nouns = {t.form for t in toks[lo:hi] if t.tag == "NNG" and len(t.form) >= 2 and t.idx != tok.idx}
            nouns.discard(tok.form)
            kept = rules.by_context_words(cands, nouns)
            if len(kept) < len(cands):
                cands, note = kept, "definition shares words with the sentence"
        if "ordinal" in active and tok.tag == "XPN" and after is not None and after.tag == "SN":
            kept = rules.by_sense(cands, rules.ORDINAL_SENSE)
            if kept and len(kept) < len(cands):
                cands, note = kept, "ordinal prefix before a number"
        if "division" in active and tok.tag in ("NNB", "NNG") and before is not None and before.tag == "SN":
            earlier = toks[tok.idx - 2] if tok.idx > 1 else None
            if earlier is not None and earlier.tag == "XPN" and earlier.form == "제":
                kept = rules.by_sense(cands, rules.DIVISION_SENSE)
                if kept and len(kept) < len(cands):
                    cands, note = kept, "numbered division (제 N …)"
        return cands, note

    def _narrow_by_verb(self, tok: Token, cands: list[Entry]) -> tuple[list[Entry], str]:
        """Keep the readings of a noun that also exist as the dictionary verb it is about to become.

        ``명`` before ``하/XSV`` is the verb 명하다 (命하다, 동사); readings with no such
        verb of the same part of speech (名, 銘; 富하다 is an adjective) are not what the
        text says. Applied only when at least one reading survives; otherwise nothing changes.
        """
        n = len(tok.suffix)
        verbs = {
            e.hanja.replace(" ", "")[:-n]
            for e in self.lexicon.candidates(tok.form + tok.suffix)
            if e.hanja.endswith(tok.suffix) and len(e.hanja) > n and e.pos == tok.suffix_pos
        }
        kept = [c for c in cands if c.hanja.replace(" ", "") in verbs]
        if kept and len(kept) < len(cands):
            return kept, f"attested as {tok.form}{tok.suffix}"
        return cands, ""

    # -- main pipeline --------------------------------------------------
    def convert_span(self, text: str, base: int = 0) -> list[Decision]:
        """Decisions for one convertible span; offsets are relative to ``base`` and point into ``text``.

        Decomposed (NFD) Hangul is read as the syllables it composes to and zero-width characters
        inside a word are ignored for matching; the decisions still cover the original characters.
        """
        norm = _normalise(text)
        if norm is None:
            return self._convert_span(text, base)
        plain, starts, ends = norm
        out = []
        for d in self._convert_span(plain, 0):
            out.append(replace(d, start=base + starts[d.start], end=base + ends[d.end - 1]))
        return out

    def _convert_span(self, text: str, base: int = 0) -> list[Decision]:
        toks = self.analyser.tokenize(text)
        toks = [replace(t, idx=i) for i, t in enumerate(toks)]
        cands = self._candidate_tokens(text, toks)
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
                compact = " " not in span
                if n > 1 and (
                    (first.tag not in PHRASE_TAGS and not compact)
                    or not all(
                        text[cands[k].end : cands[k + 1].start] in ("", " ")
                        and (cands[k + 1].tag in PHRASE_TAGS or compact)
                        for k in range(i, i + n - 1)
                    )
                ):
                    continue
                attested = ""
                has_ov, ov, lex_cands = self._lookup(span)
                if n > 1 and not has_ov and not lex_cands and compact and "compound" in self.rules:
                    forms, heads = self.lexicon.attested(span)
                    if len(forms) == 1 and first.tag in PHRASE_TAGS:
                        (form,) = forms
                        decisions.append(
                            Decision(
                                base + first.start,
                                base + last.end,
                                span,
                                Kind.CONVERTED,
                                form,
                                (Entry(span, form, "", "attested", ""),),
                                f"attested inside {heads} longer headword(s)",
                                first.tag,
                            )
                        )
                        i += n
                        matched = True
                        break
                if n == 1 and not has_ov and self.rules:
                    if first.suffix and "verb" in self.rules:
                        lex_cands, attested = self._narrow_by_verb(first, lex_cands)
                    lex_cands, note = self._narrow_by_context(toks, first, lex_cands)
                    attested = attested or note
                if not has_ov and not lex_cands:
                    continue
                d = decide(
                    span,
                    first.tag,
                    lex_cands,
                    (has_ov, ov),
                    min_weight=self.min_weight,
                    attested=attested,
                )
                if d.kind == Kind.NONE:
                    continue
                hanja = _apply_spacing(span, d.hanja) if d.hanja else None
                reason = d.reason if not attested or attested in d.reason else f"{d.reason}; {attested}"
                decisions.append(
                    Decision(base + first.start, base + last.end, span, d.kind, hanja, d.candidates, reason, d.tag)
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

    def measure_fields(self, texts: list[str]) -> Counter[str]:
        """Count, per dictionary field, the words of ``texts`` that settle on one reading of that field.

        This is the evidence of the ``field`` rule; it runs the converter with that rule off, so a
        reading chosen *because* of the rule never counts as evidence for itself.
        """
        saved = self.field_evidence
        self.field_evidence = None
        counts: Counter[str] = Counter()
        try:
            for text in texts:
                for seg in segment(text):
                    if seg.protected:
                        continue
                    for d in self.convert_span(text[seg.start : seg.end], seg.start):
                        if d.kind == Kind.CONVERTED and d.candidates and d.reason != "override":
                            fields = rules.entry_fields(list(d.candidates), d.hanja.replace(" ", ""))
                            counts.update(fields)
        finally:
            self.field_evidence = saved
        return counts

    def set_document(self, texts: list[str]) -> None:
        """Take the ``field`` rule's evidence from all of ``texts`` (one document), not from each call."""
        self.field_evidence = self.measure_fields(texts) if "field" in self.rules else None

    def convert(self, text: str, *, mark: bool = False) -> Result:
        if "field" in self.rules and self.field_evidence is None:
            self.field_evidence = self.measure_fields([text])
            try:
                return self.convert(text, mark=mark)
            finally:
                self.field_evidence = None
        decisions: list[Decision] = []
        for seg in segment(text):
            if seg.protected:
                continue
            for a, b in chunk_bounds(text[seg.start : seg.end]):
                decisions.extend(self.convert_span(text[seg.start + a : seg.start + b], seg.start + a))
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
