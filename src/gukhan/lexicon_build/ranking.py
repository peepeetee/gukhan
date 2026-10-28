# SPDX-License-Identifier: Apache-2.0
"""Exact headword/Hanja ranking signals; never infer a homograph from Hangul alone."""

import io
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .stdict import align_with_suffix, clean_hanja, clean_headword


def krdict_levels(path: Path) -> dict[tuple[str, str], int]:
    result = {}
    for file in sorted(path.glob("*.xml")) if path.is_dir() else [path]:
        # The mirror contains U+0008 in some translations. Remove only XML 1.0
        # forbidden control bytes; keep the original input intact for hashing.
        xml = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", file.read_bytes())
        for _, entry in ET.iterparse(io.BytesIO(xml), events=("end",)):
            if entry.tag != "LexicalEntry":
                continue
            features = {e.get("att"): e.get("val", "") for e in entry.findall("feat")}
            lemma = entry.find("Lemma/feat[@att='writtenForm']")
            level = {"초급": 3, "중급": 2, "고급": 1}.get(features.get("vocabularyLevel"), 0)
            if lemma is not None and level:
                word = clean_headword(lemma.get("val", ""))
                form = align_with_suffix(word, clean_hanja(features.get("origin", "")))
                if form:
                    result[word, form] = max(result.get((word, form), 0), level)
            entry.clear()
    return result


def learner_ranks(path: Path) -> dict[tuple[str, str], int]:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp949")
    result = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 5 or not fields[0].isdigit():
            continue
        rank, word, _, origin, _ = fields
        word = clean_headword(word)
        # Explanatory prose and examples are not dictionary forms.
        form = align_with_suffix(word, clean_hanja(origin))
        if form:
            key = word, form
            result[key] = min(result.get(key, int(rank)), int(rank))
    return result
