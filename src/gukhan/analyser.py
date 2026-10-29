# SPDX-License-Identifier: Apache-2.0
"""Morphological analyser interface. The default is Kiwi (kiwipiepy).

gukhan trains nothing. Kiwi itself loads a pretrained language model to pick
the best morpheme path; since kiwipiepy 0.22 the bundled model is CoNg
(Contextual N-gram embedding), a neural model. Which model Kiwi uses is
fixed here (``KIWI_MODEL_TYPE``) so two runs of the same gukhan version with
the same kiwipiepy version analyse text the same way. Kiwi never outputs
Hanja; every Hanja form still comes from the lexicon.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

# Kiwi language model selected explicitly for reproducibility. Kiwi's default
# ("none") means "the fastest model available", which can change between
# kiwipiepy releases; "cong" names the CoNg model bundled since 0.22.
KIWI_MODEL_TYPE = "cong"

# Sejong-style tags whose tokens may carry a Sino-Korean lexicon entry.
CANDIDATE_TAGS = frozenset({"NNG", "NNP", "NNB", "NR", "XR", "XPN", "XSN", "MAG", "MAJ", "MM"})

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
    "MAJ": frozenset({"부사"}),
    "MM": frozenset({"관형사"}),
}

# Derivational suffix tokens Kiwi splits off a noun: (form, tag) → (dictionary headword tail, dictionary POS).
# 명/NNG + 하/XSV is the verb 명하다 (동사), 중요/NNG + 하/XSA the adjective 중요하다 (형용사).
VERB_SUFFIXES: dict[tuple[str, str], tuple[str, str]] = {
    ("하", "XSV"): ("하다", "동사"),
    ("하", "XSA"): ("하다", "형용사"),
    ("되", "XSV"): ("되다", "동사"),
    ("시키", "XSV"): ("시키다", "동사"),
    ("스럽", "XSA"): ("스럽다", "형용사"),
    ("롭", "XSA"): ("롭다", "형용사"),
}


# Native bound nouns and forms that Kiwi tags NNB/NNG and that must never be
# converted, whatever Sino-Korean counter or noun happens to share the sound:
# 할 수 있다, 그럴 리가, 먹을 것.
NATIVE_STOP = frozenset(
    "수 것 데 바 지 줄 때 뿐 듯 양 척 체 리 터 겸 김 나위 노릇 무렵 따름 따위 적 만 만큼 대로 채 녘 즈음 쯤 들".split()
)


@dataclass(frozen=True)
class Token:
    form: str
    tag: str
    start: int  # character offset in the analysed string
    end: int
    suffix: str = ""  # dictionary tail (하다, 되다 …) of the verb this token begins, "" if none
    suffix_pos: str = ""  # that verb's dictionary part of speech (동사 / 형용사)
    idx: int = -1  # position in the analyser's full token list, -1 if not set


class Analyser(Protocol):
    def tokenize(self, text: str) -> list[Token]: ...


class KiwiAnalyser:
    """Wraps kiwipiepy. The model (about 2 s) loads on first use."""

    def __init__(self, model_type: str = KIWI_MODEL_TYPE) -> None:
        self._kiwi = None
        self.model_type = model_type

    def _load(self):
        if self._kiwi is None:
            try:
                from kiwipiepy import Kiwi
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "kiwipiepy가 設置되어 있지 않습니다 / kiwipiepy is not installed: pip install kiwipiepy"
                ) from e
            self._kiwi = Kiwi(model_type=self.model_type)
        return self._kiwi

    def describe(self) -> str:
        """``kiwipiepy <version>, model <type>`` as actually loaded, for reports and bug reports."""
        import kiwipiepy

        kiwi = self._load()
        return f"kiwipiepy {kiwipiepy.__version__}, model {kiwi.model_type}"

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
