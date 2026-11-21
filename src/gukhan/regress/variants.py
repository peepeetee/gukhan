# SPDX-License-Identifier: Apache-2.0
"""Variant-glyph equivalence from Unihan (``variants.tsv``), for scoring and for matching input that has Hanja.

A 1924 print writes 絕對 and 痛歎 where the lexicon (標準國語大辭典) has 絶對 and 痛嘆. Both are the same word in a
different glyph or a different standard form, so a comparison should not call one of them wrong. The table comes from
Unihan's ``kZVariant`` (glyph forms of one character: 絕 絶) and ``kSemanticVariant`` (characters interchangeable in
some uses: 歎 嘆), written by ``gukhan-lexicon-build --unihan`` as ``variants.tsv``: ``char<TAB>variant<TAB>kind``.
The semantic list is looser, so it can hide a real error; choose ``kinds=("z",)`` to fold glyph forms only.
Unihan 變體 표로 字形이 달라도 같은 낱말은 틀린 것으로 세지 않습니다. 意味 變體는 더 느슨해 ``z``만 고를 수 있습니다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from gukhan.regress.score import fold_variants

KINDS = ("z", "semantic")


class Variants:
    """Groups of equivalent characters; every group folds to its smallest code point."""

    def __init__(self, pairs: Iterable[tuple[str, str]] = ()) -> None:
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in pairs:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
        self._canon = {c: find(c) for c in list(parent)}
        self._members: dict[str, list[str]] = {}
        for c, root in sorted(self._canon.items()):
            self._members.setdefault(root, []).append(c)
        self._table = str.maketrans({c: r for c, r in self._canon.items() if c != r})

    def __len__(self) -> int:
        return len(self._canon)

    def fold(self, s: str) -> str:
        """``s`` with every variant replaced by its group's canonical character (and the built-in folds applied)."""
        return fold_variants(s.translate(self._table))

    def group(self, ch: str) -> list[str]:
        """``ch`` and its variants, ``ch`` first."""
        root = self._canon.get(ch)
        if root is None:
            return [ch]
        return [ch, *(c for c in self._members[root] if c != ch)]


def load_variants(path: Path, kinds: Iterable[str] = KINDS) -> Variants:
    """Read ``variants.tsv`` (or a directory holding it), keeping the pairs of the given kinds."""
    wanted = set(kinds)
    unknown = wanted - set(KINDS)
    if unknown:
        raise ValueError(f"unknown variant kind(s) / 알 수 없는 變體 種類: {', '.join(sorted(unknown))}")
    if path.is_dir():
        path = path / "variants.tsv"
    pairs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[2] in wanted and len(parts[0]) == 1 and len(parts[1]) == 1:
                pairs.append((parts[0], parts[1]))
    return Variants(pairs)


Fold = Callable[[str], str]
