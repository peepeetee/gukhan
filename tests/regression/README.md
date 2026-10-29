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
kept as published, archaic jamo (ᄲᅮᆫ, ᄯᅩ) and the particle ㅣ of 1919
prose included; only the amendment notes a law site inserts (<개정 1954.11.29>,
[전문개정 …]) are stripped, since they were never in the text. Items from
pre-1945 prose are a hard set: the analyser was trained on modern Korean, so
their score says how far the tool is from that register, not how the tool
does on today's text.

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
also depends on `--min-weight` (default 0): with a cutoff, a lone lexicon
entry below that weight is flagged rather than written. On the 1948 text a
cutoff of 12 cut wrong from 1.4% to 0.5% and right from 48.7% to 21.7%, so it
is off by default and the single-syllable rule carries the caution instead.

`wrong` and `over` are the numbers that matter most: the tool promises never
to guess, so they should stay near zero while `flagged` shrinks.

## 우리말샘 and evidence rules / 우리말샘과 근거 규칙 (2026-10-29)

Lexicon: 標準國語大辭典 (88 chunks) + 우리말샘 (25 chunks) + Wiktionary + 韓國語基礎辭典
+ learner list + Unihan 18.0.0, mirror commit `42c0d01889f34536e9cf94fe57f62bd2055b1bde`,
Kiwi 0.24.1 `cong`. Rows are `gukhan-regress score <set> --lexicon <build> [--rules …]`.
Columns: words, right, partial, flagged, wrong, over.

| id | PR #12 baseline (old merge, no rules) | new lexicon, `--rules none` | new lexicon, default rules | `--rules all` (adds `verb`) |
| --- | --- | --- | --- | --- |
| constitution-1948 | 1897 · 845 · 80 · 967 · **5** · 1 | 659 · 89 · 1144 · **5** · 1 | **892** · 93 · 907 · **5** · 3 | 990 · 94 · 806 · **7** · 3 |
| constitution-1952 | 2149 · 907 · 97 · 1139 · **6** · 2 | 719 · 113 · 1311 · **6** · 1 | **967** · 119 · 1057 · **6** · 5 | 1084 · 119 · 938 · **8** · 5 |
| constitution-1954 | 2244 · 950 · 91 · 1198 · **5** · 3 | 745 · 105 · 1389 · **5** · 1 | **1020** · 114 · 1105 · **5** · 7 | 1145 · 115 · 977 · **7** · 7 |
| declaration-1919 | 497 · 138 · 17 · 332 · **10** · 2 | 144 · 26 · 317 · **10** · 5 | **150** · 26 · 312 · **9** · 4 | 161 · 23 · 302 · **11** · 4 |
| provisional-charter-1919 | 133 · 44 · 8 · 79 · **2** · 0 | 44 · 9 · 79 · **1** · 0 | **47** · 5 · 79 · **2** · 0 | 50 · 5 · 76 · **2** · 0 |
| nim-preface-1926 | 12 · 2 · 0 · 10 · **0** · 3 | 2 · 0 · 10 · **0** · 2 | 2 · 0 · 10 · **0** · 2 | 2 · 0 · 10 · **0** · 2 |

Reading the table:

- The builder change alone (one lexicon line per part-of-speech group) lowers *right*
  from 845 to 659 on 1948 and leaves wrong unchanged. It stops hiding alternative
  readings that the old merge dropped by accident (제 was 第 only because other readings such as 諸 were
  merged away); the evidence rules then recover that and more.
- Default rules: right +47, +60, +70 on the three constitutions (+5.6% to +7.4%), wrong
  unchanged; flagged-or-partial falls from 1047 to 1000 on 1948. In the 1948 set the largest
  recovered groups are 제N조 (`ordinal`, `division`), compact compounds such as 國務委員
  (`compound`) and a common-noun reading over a place or surname (`name`).
- `verb` adds 98, 117 and 125 right words on the three constitutions and 2 wrong words each: 妨害 for 防害
  (the dictionary has 妨害하다 only), 回附 for 廻付 and 竝進 for 幷進 (variant forms of the
  same words). It is therefore off by default.
- `over` rises on the constitutions because a bracketed amendment note, `<제1호,1948.7.17>`,
  is kept in Hangul in the gold and the tool writes 第1號 there, and because 即 for 즉 and
  安易 for 안이 are written where the 1919 author kept Hangul. These are not wrong readings
  but they are conversions the gold did not make.
- Chars: wrong characters 7 → 7, 9 → 9, 7 → 7, 10 → 11, 2 → 2 (declaration-1919 gains one
  wrong character in a word that was a plain flag before).

## Combined dictionary measurement / 통합 사전 측정

2026-10-28, Kiwi 0.24.1, stdict + Wiktionary + Unihan 18.0.0, `--min-weight 0`.
Each row comes from `gukhan-regress score tests/regression/<id>.tsv --lexicon build/lexicon`.

| id | words | right | partial | flagged | wrong | over |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| constitution-1948 | 1897 | 848 | 79 | 957 | 13 | 1 |
| constitution-1952 | 2149 | 913 | 97 | 1125 | 14 | 2 |
| constitution-1954 | 2244 | 957 | 90 | 1182 | 15 | 3 |
| provisional-charter-1919 | 133 | 43 | 9 | 77 | 4 | 0 |
| declaration-1919 | 497 | 136 | 19 | 329 | 13 | 2 |
| nim-preface-1926 | 12 | 2 | 0 | 10 | 0 | 3 |

The three Han Yong-un items preserve the 1926 scan transcription, including old jamo.
한국어: 韓龍雲의 1926년 원문 3개 항목은 옛 자모와 띄어쓰기를 보존했습니다.
Other requested authors (李光洙, 玄鎭健, 蔡萬植) still need original-edition verification:
the inspected default pages use modernized spelling or parenthetical Hanja and were not
admitted as historical gold. 해당 작가의 현대화된 전사는 원문 정답 자료에 넣지 않았습니다.

한국어: `--min-weight`는 기본값 0입니다. 표준국어대사전 단독 항목은 가중치 0이므로
양수 기준을 적용하면 많은 정상 후보도 보류됩니다. 옛말과 옛 자모는 자동 교정하지 않습니다.
English: stdict-only entries have weight zero; a positive cutoff abstains on many valid
entries. Vocabulary levels and learner ranks only break candidate-order ties and do
not affect this cutoff. Archaic spelling is preserved and requires review.

`gukhan-regress score` also prints `in_candidates`: words that are right, or whose decision lists the
gold Hanja among its candidates (what a reviewer or the browser card can offer). It does not change
what the converter writes. `node scripts/measure_extension.mjs lexicon.tsv items.tsv…` gives the same
figure for the browser engine.
