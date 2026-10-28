# SPDX-License-Identifier: Apache-2.0
"""Reproducible lexicon builder (milestone 2).

Reads the 표준국어대사전 XML dump the user obtained themselves, optionally the
Unicode Unihan database, and writes a deterministic ``lexicon.tsv`` with a
``manifest.json`` recording versions and SHA-256 hashes of every input.
Nothing is downloaded and nothing from the dump lives in this repository.
"""
