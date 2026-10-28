# SPDX-License-Identifier: Apache-2.0
"""Morphological analyser interface. The default is Kiwi (kiwipiepy)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

# Sejong-style tags whose tokens may carry a Sino-Korean lexicon entry.
CANDIDATE_TAGS = frozenset({"NNG", "NNP", "NNB", "NR", "XR", "XPN", "XSN", "MAG", "MM"})

# Lexicon part-of-speech labels compatible with each analyser tag. An entry
# whose pos is not listed for the token's tag is not a candidate at all, so a
# native numeral 세 (MM) is never flagged with 世/歲 and the counter 시 (NNB)
# only matches an explicit 의존 명사 entry. Empty pos (override files, hand
# lists) is accepted for the open noun classes only.
TAG_TO_POS: dict[str, frozenset[str]] = {
    "NNG": frozenset({"명사", "의존 명사", "어근", ""}),
    "NNP": frozenset({"명사", "고유 명사", ""}),
    "NNB": frozenset({"의존 명사"}),
    "NR": frozenset({"수사", "명사", ""}),
    "XR": frozenset({"어근", "명사", ""}),
    "XPN": frozenset({"접두사", "접사"}),
    "XSN": frozenset({"접미사", "접사"}),
    "MAG": frozenset({"부사"}),
    "MM": frozenset({"관형사"}),
}


@dataclass(frozen=True)
class Token:
    form: str
    tag: str
    start: int  # character offset in the analysed string
    end: int


class Analyser(Protocol):
    def tokenize(self, text: str) -> list[Token]: ...


class KiwiAnalyser:
    """Wraps kiwipiepy. The model (about 2 s) loads on first use."""

    def __init__(self) -> None:
        self._kiwi = None

    def _load(self):
        if self._kiwi is None:
            try:
                from kiwipiepy import Kiwi
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "kiwipiepy가 設置되어 있지 않습니다 / kiwipiepy is not installed: pip install kiwipiepy"
                ) from e
            self._kiwi = Kiwi()
        return self._kiwi

    def tokenize(self, text: str) -> list[Token]:
        kiwi = self._load()
        return [Token(t.form, t.tag, t.start, t.end) for t in kiwi.tokenize(text)]


class ListAnalyser:
    """Test double: (form, tag) pairs matched left to right; pairs absent from the text are skipped."""

    def __init__(self, tokens: Iterable[tuple[str, str]]) -> None:
        self._tokens = list(tokens)

    def tokenize(self, text: str) -> list[Token]:
        out, pos = [], 0
        for form, tag in self._tokens:
            idx = text.find(form, pos)
            if idx < 0:
                continue  # token belongs to another span of the same text
            out.append(Token(form, tag, idx, idx + len(form)))
            pos = idx + len(form)
        return out
