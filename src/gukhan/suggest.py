# SPDX-License-Identifier: Apache-2.0
"""Optional suggestions for flagged words from a local language model.

Off by default and never networked unless asked: nothing here runs unless the caller builds a
backend and passes it in (``gukhan --llm-url …``). A backend sees one sentence, the flagged word
and the dictionary's candidates for it, nothing else, and must answer with the number of one
candidate or abstain. It cannot add a reading the dictionary does not list.

A suggestion is a hint, never a decision. Reports and ``gukhan review`` show it marked as a
suggestion. It reaches the converted text only when the caller asks for that explicitly
(``--llm-apply``), and then the report says which words it changed.

``OpenAIChatBackend`` speaks the OpenAI-compatible chat-completions protocol that llama.cpp's
``llama-server`` and Ollama expose on localhost. It uses only the standard library, refuses a host
that is not loopback unless ``allow_remote`` is set, and ignores proxy settings so that a
localhost address is never sent through one. ``MockBackend`` is for tests.
"""

from __future__ import annotations

import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from .convert import Kind, Result, _apply_spacing
from .lexicon import Entry

SENTENCE_END = re.compile(r"[.!?。！？\n]")
MAX_SENTENCE = 300
LOOPBACK_NAMES = {"localhost", "localhost.localdomain"}

SYSTEM_PROMPT = (
    "You choose the Hanja (Sino-Korean written form) of one Korean word in its sentence. "
    "The word is marked [like this]. Candidates are numbered. "
    "Reply with only the number of the one candidate that fits this sentence, "
    "or 0 if the sentence does not settle it. No other text."
)


class SuggestError(RuntimeError):
    """The backend could not be reached or answered something unusable."""


@dataclass(frozen=True)
class Suggestion:
    index: int  # 1-based number in the candidate list; always within it
    hanja: str  # that candidate's Hanja (the Hangul itself for a native-word candidate)
    backend: str
    applied: bool = False  # written into the output by --llm-apply


class Backend(Protocol):
    name: str

    def suggest(self, sentence: str, word: str, candidates: Sequence[Entry]) -> int | None:
        """The 1-based number of the chosen candidate, or None to abstain."""
        ...


def sentence_around(text: str, start: int, end: int, limit: int = MAX_SENTENCE) -> str:
    """The sentence of ``text`` containing ``text[start:end]``, the word marked with brackets.

    Cut at sentence-ending punctuation and line breaks, and at ``limit`` characters in all, so a
    backend never receives more of the document than one sentence.
    """
    left = start
    while left > 0 and not SENTENCE_END.match(text[left - 1]) and start - left < limit:
        left -= 1
    right = end
    while right < len(text) and not SENTENCE_END.match(text[right]) and right - end < limit:
        right += 1
    if right < len(text) and SENTENCE_END.match(text[right]) and text[right] != "\n":
        right += 1
    word = text[start:end]
    return (text[left:start] + "[" + word + "]" + text[end:right]).strip()


def _clean(candidates: Sequence[Entry]) -> list[Entry]:
    """Candidates a backend may choose from: one per Hanja form, in the converter's order."""
    seen: set[str] = set()
    out = []
    for c in candidates:
        key = c.hanja.replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def suggest_one(backend: Backend, sentence: str, word: str, candidates: Sequence[Entry]) -> Suggestion | None:
    cands = _clean(candidates)
    if len(cands) < 2:
        return None
    n = backend.suggest(sentence, word, cands)
    if n is None or not 1 <= n <= len(cands):
        return None  # an out-of-range answer is an abstention, never an invented reading
    return Suggestion(n, cands[n - 1].hanja, backend.name)


def collect_suggestions(
    backend: Backend,
    text: str,
    result: Result,
    *,
    on_error: Callable[[str], None] | None = None,
) -> dict[tuple[int, int], Suggestion]:
    """Ask ``backend`` about every flagged word of ``result``; keys are (start, end) of the decision.

    The first backend failure stops the run (the words after it get no suggestion) and is reported
    once through ``on_error``; conversion itself is never affected.
    """
    out: dict[tuple[int, int], Suggestion] = {}
    cache: dict[tuple[str, str], Suggestion | None] = {}
    for d in result.decisions:
        if d.kind != Kind.FLAGGED or len(d.candidates) < 2:
            continue
        sentence = sentence_around(text, d.start, d.end)
        key = (sentence, d.hangul)
        if key not in cache:
            try:
                cache[key] = suggest_one(backend, sentence, d.hangul, d.candidates)
            except SuggestError as e:
                if on_error:
                    on_error(str(e))
                break
        s = cache[key]
        if s is not None:
            out[(d.start, d.end)] = s
    return out


def apply_suggestions(text: str, result: Result, suggestions: Mapping[tuple[int, int], Suggestion]) -> str:
    """The converted text with each suggested flagged word written in the suggested Hanja.

    Only for the explicit ``--llm-apply``; a suggestion for a native-word candidate keeps the Hangul.
    """
    out, pos = [], 0
    for d in result.decisions:
        out.append(text[pos : d.start])
        s = suggestions.get((d.start, d.end))
        if d.kind == Kind.CONVERTED and d.hanja:
            out.append(d.hanja)
        elif (
            d.kind == Kind.FLAGGED and s is not None and len(s.hanja.replace(" ", "")) == len(d.hangul.replace(" ", ""))
        ):
            out.append(_apply_spacing(d.hangul, s.hanja.replace(" ", "")))
        else:
            out.append(d.hangul)
        pos = d.end
    out.append(text[pos:])
    return "".join(out)


def describe(s: Suggestion | None) -> str:
    if s is None:
        return ""
    return f"{s.hanja} ({s.backend}" + (", applied)" if s.applied else ", unconfirmed)")


# -- backends -------------------------------------------------------------------------------------


class MockBackend:
    """A fixed answer table for tests: ``{"의원": "議員"}`` picks that candidate; anything else abstains."""

    name = "mock"

    def __init__(self, answers: Mapping[str, str] | None = None, *, fail: str | None = None) -> None:
        self.answers = dict(answers or {})
        self.fail = fail
        self.calls: list[tuple[str, str, list[str]]] = []

    def suggest(self, sentence: str, word: str, candidates: Sequence[Entry]) -> int | None:
        self.calls.append((sentence, word, [c.hanja for c in candidates]))
        if self.fail:
            raise SuggestError(self.fail)
        want = self.answers.get(word)
        for i, c in enumerate(candidates, 1):
            if c.hanja.replace(" ", "") == want:
                return i
        return None


def prompt_for(sentence: str, candidates: Sequence[Entry]) -> str:
    lines = [f"Sentence: {sentence}", "Candidates:"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c.hanja}" + (f" — {c.sense}" if c.sense else ""))
    lines.append("Answer (a number, 0 if unsure):")
    return "\n".join(lines)


_NUMBER = re.compile(r"^\s*(\d+)\b")


def parse_choice(content: str) -> int | None:
    """The number a model answered with, or None for 0, an abstention or anything that is not a number first."""
    m = _NUMBER.match(content or "")
    if not m:
        return None
    n = int(m.group(1))
    return n or None


def is_loopback(url: str) -> bool:
    host = urllib.parse.urlsplit(url).hostname or ""
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OpenAIChatBackend:
    """A local model behind an OpenAI-compatible ``/v1/chat/completions`` endpoint (llama.cpp, Ollama …)."""

    def __init__(
        self,
        base_url: str,
        model: str = "",
        *,
        timeout: float = 60.0,
        allow_remote: bool = False,
        api_key: str = "",
    ) -> None:
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"주소가 올바르지 않습니다 / not an http(s) address: {base_url!r}")
        if not allow_remote and not is_loopback(base_url):
            raise ValueError(
                f"localhost 가 아닌 주소입니다: {parts.hostname}. 文章을 보내려면 --llm-allow-remote 를 주세요 / "
                f"not a localhost address: {parts.hostname}; pass --llm-allow-remote to send sentences there"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = api_key
        self.name = f"llm:{model or 'default'}"
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def endpoint(self) -> str:
        root = self.base_url
        return (
            root
            if root.endswith("/chat/completions")
            else root + ("/chat/completions" if root.endswith("/v1") else "/v1/chat/completions")
        )

    def suggest(self, sentence: str, word: str, candidates: Sequence[Entry]) -> int | None:
        body = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_for(sentence, candidates)},
            ],
            "temperature": 0,
            "max_tokens": 8,
            "stream": False,
        }
        if self.model:
            body["model"] = self.model
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.endpoint, json.dumps(body).encode("utf-8"), headers, method="POST")
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError) as e:
            raise SuggestError(
                f"모델에 連結할 수 없거나 答이 올바르지 않습니다 / the model at {self.endpoint} is unreachable "
                f"or answered something unusable: {e}"
            ) from e
        return parse_choice(content if isinstance(content, str) else "")


__all__ = [
    "Backend",
    "MockBackend",
    "OpenAIChatBackend",
    "Suggestion",
    "SuggestError",
    "apply_suggestions",
    "collect_suggestions",
    "sentence_around",
    "suggest_one",
]
