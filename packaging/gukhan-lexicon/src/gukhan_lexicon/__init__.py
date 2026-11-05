# SPDX-License-Identifier: Apache-2.0
"""gukhan-lexicon: the prebuilt Sino-Korean lexicon for gukhan.

The data files under ``data/`` are licensed separately from this module; see NOTICE.txt and
``data/manifest.json`` (key ``licence``) in the installed package.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

DATA_FILES = ("lexicon.tsv", "chars.tsv", "manifest.json")


def data_dir() -> Path:
    """Directory holding lexicon.tsv, chars.tsv and manifest.json (pass it as ``gukhan --lexicon``)."""
    return Path(str(resources.files("gukhan_lexicon").joinpath("data")))


def lexicon_path() -> Path:
    return data_dir() / "lexicon.tsv"


def manifest() -> dict:
    """The build manifest: sources, licence, attribution notice, counts and file hashes."""
    return json.loads((data_dir() / "manifest.json").read_text(encoding="utf-8"))
