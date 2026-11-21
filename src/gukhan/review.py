# SPDX-License-Identifier: Apache-2.0
"""``gukhan review``: a human picks the Hanja for each flagged word, in context.

The decisions are written to the ordinary override file (see ``overrides.py``), one
line each and at once, so a quit or a crash loses nothing and the next run reuses them.
Nothing is preselected and Enter does nothing: the tool never guesses. With ``--llm-url`` a local
model may suggest one candidate per word, shown as an unconfirmed hint from the first context;
it is used only if you answer ``y``.

Answers at the prompt (a number is the candidate's number in the list)::

    3      use candidate 3 for this word everywhere
    n3     use candidate 3 only where this word is followed by the same next word
    p3     use candidate 3 only where this word follows the same previous word
    y      accept the model's suggestion (only when one is shown; see below)
    k      keep Hangul everywhere          s  skip for now        u  undo the last answer
    q      save and quit                   漢字  (typed)  use exactly this Hanja
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .convert import Converter, Decision, Kind, Result
from .lexicon import Entry, _strip_spaces
from .overrides import KEEP, Overrides
from .report import one_line
from .suggest import Backend, SuggestError, Suggestion, sentence_around, suggest_one

SHOW_CONTEXTS = 3
CONTEXT = 20
ANSWER = re.compile(r"^([np]?)(\d+)$")


@dataclass
class Group:
    """All decisions for one unresolved spelling, with the candidates they share."""

    hangul: str
    decisions: list[Decision]
    candidates: list[Entry] = field(default_factory=list)


def collect(result: Result, include_review: bool = False) -> list[Group]:
    """Unresolved words grouped by spelling, most frequent first (ties: first appearance)."""
    kinds = {Kind.FLAGGED} | ({Kind.REVIEW} if include_review else set())
    groups: dict[str, Group] = {}
    for d in result.decisions:
        if d.kind not in kinds:
            continue
        g = groups.setdefault(_strip_spaces(d.hangul), Group(d.hangul, []))
        g.decisions.append(d)
        for c in d.candidates:
            if all(c.hanja != o.hanja for o in g.candidates):
                g.candidates.append(c)
    return sorted(groups.values(), key=lambda g: -len(g.decisions))


def _context(text: str, d: Decision) -> str:
    left = one_line(text[max(0, d.start - CONTEXT) : d.start])
    right = one_line(text[d.end : d.end + CONTEXT])
    return f"…{left}[{d.hangul}]{right}…"


def _neighbour(result: Result, d: Decision, side: str) -> Decision | None:
    """The decision directly before or after ``d`` (only whitespace between), if any."""
    ds = result.decisions
    i = ds.index(d)
    j = i + 1 if side == "n" else i - 1
    if not 0 <= j < len(ds):
        return None
    o = ds[j]
    gap = result.text[d.end : o.start] if side == "n" else result.text[o.end : d.start]
    return o if gap.strip() == "" and len(gap) <= 1 else None


def _written(d: Decision) -> str:
    return d.hanja if d.kind == Kind.CONVERTED and d.hanja else d.hangul


def phrase_pair(result: Result, d: Decision, side: str, hanja: str) -> tuple[str, str] | None:
    """``(hangul phrase, hanja phrase)`` joining ``d`` to its neighbour, or None."""
    o = _neighbour(result, d, side)
    if o is None:
        return None
    if side == "n":
        return f"{d.hangul} {o.hangul}", f"{hanja} {_written(o)}"
    return f"{o.hangul} {d.hangul}", f"{_written(o)} {hanja}"


class Reviewer:
    """The interactive ``gukhan review`` session: asks about each flagged word and appends answers to the override file.

    ``input_fn`` and ``output_fn`` replace ``input`` and ``print`` (for tests and other front ends).
    """

    def __init__(
        self,
        conv: Converter,
        text: str,
        path: Path,
        *,
        input_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], None] = print,
        include_review: bool = False,
        backend: Backend | None = None,
    ) -> None:
        self.conv, self.text, self.path = conv, text, path
        self.backend = backend
        self._sugg: dict[str, Suggestion | None] = {}
        self.ask = input_fn if input_fn is not None else (lambda prompt: input(prompt))
        self.say = output_fn
        self.include_review = include_review
        if conv.overrides is None:
            conv.overrides = Overrides()
        self.ov = conv.overrides
        self.result = conv.convert(text)
        self.history: list[tuple[str, str, Entry | None | bool, int]] = []  # (line, key, previous, group index)
        self.saved = 0
        self._cur = 0
        self._undone_at = 0

    # -- file ------------------------------------------------------------
    def _append(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # a hand-edited file may lack its final newline; without one the new line would join the last
        lead = ""
        if self.path.is_file() and self.path.stat().st_size:
            with self.path.open("rb") as fh:
                fh.seek(-1, 2)
                lead = "" if fh.read(1) == b"\n" else "\n"
        with self.path.open("a", encoding="utf-8", newline="") as fh:
            fh.write(lead + line + "\n")

    def _remove_last(self, line: str) -> None:
        lines = self.path.read_text(encoding="utf-8-sig").splitlines()
        for i in range(len(lines) - 1, -1, -1):
            if lines[i] == line:
                del lines[i]
                break
        self.path.write_text("".join(x + "\n" for x in lines), encoding="utf-8")

    def _record(self, hangul: str, hanja: str, note: str) -> None:
        key = _strip_spaces(hangul)
        prev: Entry | None | bool = self.ov.decisions[key] if key in self.ov.decisions else False
        self.ov.add(hangul, hanja, "override:review")
        line = f"{hangul} = {hanja}  # review: {note}"
        self._append(line)
        self.history.append((line, key, prev, self._cur))
        self.saved += 1

    def undo(self) -> bool:
        if not self.history:
            return False
        line, key, prev, at = self.history.pop()
        self._remove_last(line)
        if prev is False:
            self.ov.decisions.pop(key, None)
        else:
            self.ov.decisions[key] = prev  # type: ignore[assignment]
        self.saved -= 1
        self._undone_at = at
        return True

    # -- loop ------------------------------------------------------------
    def show(self, g: Group, n: int, total: int) -> None:
        self.say(f"\n[{n}/{total}] {g.hangul}  ×{len(g.decisions)}")
        for d in g.decisions[:SHOW_CONTEXTS]:
            self.say("  " + _context(self.text, d))
        if g.candidates:
            for i, c in enumerate(g.candidates, 1):
                self.say(f"  {i}) {c.hanja}" + (f"  {c.sense}" if c.sense else ""))
            s = self._suggestion(g)
            if s is not None:
                self.say(f"  提案 suggestion (unconfirmed, {s.backend}): {s.hanja}  — y to accept / y 로 受容")
        else:
            self.say("  (no candidates / 後補 없음: type the Hanja)")

    def _suggestion(self, g: Group) -> Suggestion | None:
        """The backend's hint for the first context of ``g``, asked once; a failure turns the backend off."""
        if self.backend is None or len(g.candidates) < 2:
            return None
        key = _strip_spaces(g.hangul)
        if key not in self._sugg:
            d = g.decisions[0]
            try:
                self._sugg[key] = suggest_one(
                    self.backend, sentence_around(self.text, d.start, d.end), g.hangul, g.candidates
                )
            except SuggestError as e:
                self.say(f"提案 없이 繼續합니다 / continuing without suggestions: {e}")
                self.backend = None
                return None
        return self._sugg[key]

    def apply(self, g: Group, answer: str) -> str | None:
        """Handle one answer. Returns an error message, or None when it was accepted."""
        if answer == "y":
            s = self._sugg.get(_strip_spaces(g.hangul))
            if s is None:
                return "受容할 提案이 없습니다 / no suggestion to accept"
            if s.hanja.replace(" ", "") == _strip_spaces(g.hangul):  # the native-word candidate: keep Hangul
                self._record(g.hangul, KEEP, f"accepted suggestion, {s.backend}")
            else:
                self._record(g.hangul, s.hanja, f"accepted suggestion, {s.backend}")
            return None
        m = ANSWER.match(answer)
        if m:
            side, num = m.group(1), int(m.group(2))
            if not 1 <= num <= len(g.candidates):
                return f"1–{len(g.candidates)} 中에서 고르세요 / pick 1–{len(g.candidates)}"
            hanja = g.candidates[num - 1].hanja
            if not side:
                self._record(g.hangul, hanja, "word")
                return None
            return self._phrase(g, side, hanja)
        if answer == "k":
            self._record(g.hangul, KEEP, "keep Hangul")
            return None
        if answer and all("一" <= c <= "鿿" or "㐀" <= c <= "䶿" or c == " " for c in answer):
            if len(_strip_spaces(answer)) != len(_strip_spaces(g.hangul)):
                return f"{g.hangul} 와 길이가 다릅니다 / length differs from {g.hangul}"
            self._record(g.hangul, answer, "typed")
            return None
        return "알 수 없는 答 / unknown answer (番號, n番號, p番號, k, s, u, q, or Hanja)"

    def _phrase(self, g: Group, side: str, hanja: str) -> str | None:
        d = g.decisions[0]
        pair = phrase_pair(self.result, d, side, hanja)
        if pair is None:
            return "이웃 낱말이 없습니다 / no adjacent word on that side"
        hangul_phrase, hanja_phrase = pair
        key = _strip_spaces(hangul_phrase)
        if key in self.ov.decisions:
            return "이미 決定된 句입니다 / that phrase already has a decision"
        self._record(hangul_phrase, hanja_phrase, f"phrase, {side}")
        after = self.conv.convert(self.text)
        ok = any(
            x.kind == Kind.CONVERTED and x.start <= d.start < x.end and hanja in (x.hanja or "")
            for x in after.decisions
        )
        if not ok:
            self.undo()
            return "그 句로는 適用되지 않습니다 / the phrase did not apply here; use the whole word"
        self.result = after
        return None

    def run(self) -> int:
        groups = collect(self.result, self.include_review)
        if not groups:
            self.say("檢討할 낱말이 없습니다 / nothing to review")
            return 0
        i, total = 0, len(groups)
        while i < total:
            self._cur = i
            self.show(groups[i], i + 1, total)
            i = self._prompt(groups, i)
            if i < 0:
                break
        self.say(f"\n{self.saved} 件 저장 / saved → {self.path}")
        return 0

    def _prompt(self, groups: list[Group], i: int) -> int:
        """Ask until the word is settled. Returns the next index, or -1 to quit."""
        g = groups[i]
        self._cur = i
        while True:
            try:
                answer = self.ask("> ").strip()
            except (EOFError, KeyboardInterrupt):
                return -1
            if answer == "q":
                return -1
            if answer == "s":
                return i + 1
            if answer == "u":
                if not self.undo():
                    self.say("取消할 것이 없습니다 / nothing to undo")
                    continue
                self.say("취소했습니다 / undone")
                return self._undone_at
            err = self.apply(g, answer)
            if err:
                self.say(err)
                continue
            return i + 1


__all__ = ["Group", "Reviewer", "collect"]
