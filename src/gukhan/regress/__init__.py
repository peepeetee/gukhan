# SPDX-License-Identifier: Apache-2.0
"""Public regression set tooling (milestone 4).

A regression item is one sentence of historical 國漢文混用 text (the gold
answer) together with its Hangul-only form (the converter's input). Items
come from sources that carry no copyright (statutes, official notices) or
whose copyright has expired; see tests/regression/README.md.

``gukhan-regress prepare`` derives the Hangul form from the gold text with
Unihan readings and flags every character whose reading had to be guessed.
``gukhan-regress score`` runs the converter on the Hangul forms and reports
how many Hanja words came back right, were flagged, or were wrong.
"""
