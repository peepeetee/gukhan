# SPDX-License-Identifier: Apache-2.0
"""Evidence rules that narrow a flag's candidates without guessing.

Each rule removes candidates only on evidence the dictionary or the analyser
supplies, and only when at least one candidate survives. None of them looks at
how common a word is. A rule that narrows the list to one reading lets the
converter write it; a rule that leaves several leaves the flag in place, now
with a shorter list for the person to read.

The evidence used:

- ``proper names``: the dictionary's own definition says the entry is a person,
  place or surname. The analyser tagged the token as a common noun (NNG).
- ``ordinal prefix``: the token is a prefix directly before a number and one
  candidate's definition says it marks the ordinal (「그 숫자에 해당되는 차례」: 第).
- ``counter``: the token is a counter (every reading's definition says 「… 단위」: 日 「날을 세는
  단위」) but no number precedes it, so it is the native word 일 or 시, not 日 or 時.
- ``numbered division``: in the frame 「제 N X」 the word X is an ordinal-numbered
  part, so only a reading whose definition says it divides or orders (條: 「나누어 구분하는
  단위」; 號: 「순서를 매겨」), not one that counts sets (組), qualifies.
- ``verb``: the noun is followed by 하/되 …, and only some of its readings exist
  as that dictionary verb with the matching part of speech (命하다, not 名하다).
- ``attested compound``: the whole stretch occurs inside longer headwords with
  one Hanja form (see ``Lexicon.attested``).
"""

from __future__ import annotations

import re

from .lexicon import Entry

# Definitions that mark an entry as a name, written the way 표준국어대사전 and 우리말샘 write them.
PROPER_SENSE = re.compile(
    r"성\(姓\)의 하나"  # surname
    r"|\(\s*(?:B\.C\.\s*)?\d{3,4}\??\s*[~∼]"  # life dates after a person: (1794~1857), (B.C.506~...)
    r"|에 있는 (?:면|읍|동|리|군|시|마을|산|강|섬|호수|고개|골짜기|들)\b"  # place
    r"|’의 (?:자|호|시호)\.?$"  # courtesy / pen name of a person
)
# Rule names, as used by ``Converter(use_rules=...)`` and ``gukhan --rules``.
#
# DEFAULT rules narrow a list on what an entry says about its meaning, on a fixed construction of
# the text, or on the stretch of text itself occurring inside longer headwords. OPT_IN rules narrow
# it because the other readings are *missing* from a dictionary verb; absence from a dictionary is
# weaker than a statement in it (the dictionary has 妨害하다 but not 防害하다, which the 1948 text
# writes), and measured on the regression sets it adds wrong words, so it is opt-in.
DEFAULT = frozenset({"name", "ordinal", "division", "counter", "compound"})
OPT_IN = frozenset({"verb"})
ALL = DEFAULT | OPT_IN


def parse_rules(spec: str) -> frozenset[str]:
    """``default`` | ``all`` | ``none`` | comma list of rule names (``default,verb``) → set of names."""
    out: set[str] = set()
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        if part == "none":
            continue
        if part == "default":
            out |= DEFAULT
        elif part == "all":
            out |= ALL
        elif part in ALL:
            out.add(part)
        else:
            raise ValueError(
                f"unknown rule {part!r}; choose from default, all, none, {', '.join(sorted(ALL))} / "
                f"알 수 없는 規則입니다: {part!r}"
            )
    return frozenset(out)


ORDINAL_SENSE = ("차례",)
UNIT_SENSE = "단위"
DIVISION_SENSE = ("구분", "순서", "차례")


def _forms(cands: list[Entry]) -> set[str]:
    return {c.hanja.replace(" ", "") for c in cands}


def keep_forms(cands: list[Entry], forms: set[str]) -> list[Entry]:
    return [c for c in cands if c.hanja.replace(" ", "") in forms]


def by_sense(cands: list[Entry], words: tuple[str, ...]) -> list[Entry]:
    """Candidates whose Hanja form has at least one entry with a definition containing one of ``words``."""
    return keep_forms(cands, {c.hanja.replace(" ", "") for c in cands if any(w in c.sense for w in words)})


def drop_proper_names(cands: list[Entry]) -> list[Entry]:
    """Remove readings whose every definition marks a name; keep all if that would remove every reading."""
    names = {
        form
        for form in _forms(cands)
        if all(PROPER_SENSE.search(c.sense or "") for c in cands if c.hanja.replace(" ", "") == form)
    }
    kept = [c for c in cands if c.hanja.replace(" ", "") not in names]
    return kept if kept else cands
