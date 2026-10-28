# 回歸 test set / Regression set

Public, hand-checked sentences in 國漢文混用體 with their Hangul-only form.
Every accuracy figure gukhan ever quotes comes from `gukhan-regress score`
on these files, nothing else.

## Where the sentences come from

Pre-1970 texts that were written in mixed script when first published, so the
Hanja choice is the author's, not ours:

- Statutes, constitutions, official notices: no copyright at all (저작권법
  제7조). The 1948 大韓民國憲法 is the first set.
- Literature by authors who died before 1962 (public domain in the Republic
  of Korea), and anonymous flyers or advertisements published before 1956.

`sources.tsv` lists each text with its URL, the markers that delimit it and
the legal basis. Add a row there before adding items.

## Files

- `sources.tsv`: provenance.
- `<id>.tsv`: items, tab separated: `id  source  hangul  mixed`. The `mixed`
  column is the gold answer exactly as published. A trailing ` # CHECK …`
  note marks readings `gukhan-regress prepare` had to guess; remove the note
  once a person has confirmed or corrected the Hangul.

## How to add a text

```
python scripts/fetch_corpus.py --out build/corpus --only constitution-1948
gukhan-regress prepare build/corpus/constitution-1948.txt \
    --chars build/lexicon/chars.tsv --source constitution-1948 \
    -o tests/regression/constitution-1948.tsv
# read the CHECK notes, fix the Hangul where needed, delete the notes
gukhan-regress score tests/regression/*.tsv --lexicon build/lexicon
```

`chars.tsv` comes from `gukhan-lexicon-build --unihan`; pass `--lexicon
build/lexicon` to `prepare` so that runs of Hanja are first cut into words the
lexicon knows, which settles multi-reading characters and the 頭音法則 inside
compounds (强制勞役 → 강제노역). Uncovered characters take their education-set
reading, with the initial-sound rule at the start of each segment and not
after a numeral (4281年 → 4281년). The original's spacing and spelling are
kept as published.

## What the score means

| Column | Meaning |
| --- | --- |
| words | runs of Hanja in the gold text |
| right | converter wrote exactly that Hanja |
| partial | part of the run is right, the rest stayed Hangul (compound known in part) |
| flagged | converter left the word in Hangul (abstained or flagged) |
| wrong | converter wrote different Hanja somewhere in the run |
| over | converter wrote Hanja where the gold text has Hangul |
| chars_* | the same, counted per Hanja character |

Glyph variants such as 强/強 are folded before comparison. The score line
also depends on `--min-weight` (default 12 on a Wiktionary-built lexicon): a
lone lexicon entry below that weight is flagged rather than written, because
one entry in a crowd-sourced lexicon is no proof that no other reading exists.

`wrong` and `over` are the numbers that matter most: the tool promises never
to guess, so they should stay near zero while `flagged` shrinks.
