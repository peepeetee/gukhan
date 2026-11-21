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

## Modern statutes / 現行 法律 (2026-11-21)

`modern-law.tsv` (1218 items) tests homograph choice on current statutes. Current
法律 are written in Hangul, but the plain-language rewrites of the 2000s–2020s put
the Hanja after a legal term on first use: `분사무소(分事務所)`, `의사(意思)`. That
annotation is the lawmaker's own Hanja for the word, so it is gold.

- Source: `legalize-kr/legalize-kr` on GitHub, a mirror of law.go.kr; 40 statutes,
  listed with 公布日 / 施行日 / 法令MST in `modern-law-laws.tsv`. Statutes are free
  of copyright (저작권법 제7조); the mirror's own structure and metadata are MIT.
- Only annotated words are Hanja in the gold text; every other word stays Hangul.
  So read `right`, `flagged` and `wrong`; `over` counts every un-annotated word
  the converter writes in Hanja and means nothing here.
- At most two sentences per distinct (word, Hanja) pair, so `자(子)` does not
  dominate. Readings were checked by eye, not against Unihan.
- Rebuild: `python scripts/collect_law_glosses.py --out build/laws` then
  `--from build/laws --items tests/regression/modern-law.tsv`.

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

## `field` rule / 分野 規則 (2026-11-21)

Lexicon built in the cloud container from 標準國語大辭典 (88 chunks) + 우리말샘 (25 chunks), no
Wiktionary, 韓國語基礎辭典 or learner list: 705,758 entries, 484,686 of them with a `domain`.
Kiwi 0.24.1 `cong`. Columns: words, right, partial, flagged, wrong, over. The scorer folds 祕/秘
since this run (秘密 was counted wrong for a variant glyph).

| id | default rules without `field` | default rules (with `field`) |
| --- | --- | --- |
| constitution-1948 | 1897 · 896 · 106 · 888 · 7 · 3 | 1897 · **938** · 101 · 851 · 7 · 3 |
| constitution-1952 | 2149 · 973 · 131 · 1037 · 8 · 5 | 2149 · **1019** · 126 · 996 · 8 · 5 |
| constitution-1954 | 2244 · 1016 · 136 · 1085 · 7 · 7 | 2244 · **1073** · 129 · 1035 · 7 · 7 |
| declaration-1919 | 497 · 148 · 25 · 314 · 10 · 4 | 497 · **151** · 25 · 311 · 10 · 4 |
| provisional-charter-1919 | 133 · 49 · 5 · 77 · 2 · 0 | 133 · **51** · 6 · 74 · 2 · 0 |
| nim-1926 (b1–b8) | 573 · 147 · 5 · 412 · 9 · 140 | 573 · **176** · 5 · 382 · 10 · 140 |
| nim-preface-1926 | 12 · 2 · 0 · 10 · 0 · 3 | 12 · 2 · 0 · 10 · 0 · 3 |

Over all sets: right 3231 → 3410 (+179), flagged 3823 → 3659, wrong 43 → 44. The one new wrong
word is 菩薩 → 補殺 in 님의 沈黙 (one Buddhist word in the text is not evidence of the field).
The gain is mostly 불교, 민속 and 역사 words that the dictionary lists next to an everyday reading,
e.g. 임자 (壬子 「민속」, 妊子 「한의」, 荏子 vs 任者). Which fields count was settled on these same
sets, by measuring each label alone (without 음악, 동물, 의학, 법률, 경제, 공업: they added wrong), so the
figure is tuned to the sets and not an independent estimate.

## `sense` rule / 뜻풀이 規則 (2026-11-21)

Same lexicon and settings as the `field` table above, regression sets as of main at #46 (more
님의 沈黙 batches). Columns: words, right, partial, flagged, wrong, over.

| id | default without `sense` | default (with `sense`) |
| --- | --- | --- |
| constitution-1948 | 1897 · 938 · 101 · 851 · 7 · 3 | 1897 · **957** · 104 · 829 · 7 · 3 |
| constitution-1952 | 2149 · 1019 · 126 · 996 · 8 · 5 | 2149 · **1040** · 133 · 968 · 8 · 5 |
| constitution-1954 | 2244 · 1073 · 129 · 1035 · 7 · 7 | 2244 · **1095** · 137 · 1005 · 7 · 7 |
| declaration-1919, provisional-charter-1919, nim-1926 | unchanged | unchanged |

All sets: right 3448 → 3510 (+62), wrong 48 → 48. Every gain is in the three constitutions, which
repeat each other, so the distinct-word gain is about a third of that. The thresholds (two nouns,
margin two, same sentence) were chosen on these sets: with a threshold of one noun the rule picked
442 right and 74 wrong words. Nothing has been measured on modern prose.

## Native homographs from 標準國語大辭典 / 고유어 同音語 (2026-11-21)

`gukhan-lexicon-build --stdict` now also records the dictionary's native (고유어) headwords
that have the same sound as a Sino-Korean entry, as candidates whose Hanja column repeats the
Hangul (the mechanism Wiktionary natives already used). 사랑 had one Sino-Korean entry (舍廊
「바깥채」) and was written 舍廊 in 77 places in 님의 沈黙; now it is flagged between 舍廊 and
the native 사랑. 2,337 native headwords. Same lexicon otherwise (標準國語大辭典 + 우리말샘), same
rules; columns: words, right, partial, flagged, wrong, over.

| id | before | after |
| --- | --- | --- |
| constitution-1948 | 1897 · 957 · 104 · 829 · 7 · 3 | 1897 · 949 · 104 · 837 · 7 · 3 |
| constitution-1952 | 2149 · 1040 · 133 · 968 · 8 · 5 | 2149 · 1027 · 132 · 982 · 8 · 5 |
| constitution-1954 | 2244 · 1095 · 137 · 1005 · 7 · 7 | 2244 · 1078 · 137 · 1022 · 7 · 7 |
| declaration-1919 | 497 · 151 · 25 · 311 · 10 · 4 | 497 · 149 · 24 · 314 · 10 · 4 |
| provisional-charter-1919 | 133 · 51 · 6 · 74 · 2 · 0 | 133 · 50 · 6 · 75 · 2 · 0 |
| nim-1926 (b1–b14) | 931 · 290 · 15 · 610 · 16 · 201 | 931 · 286 · 13 · 616 · 16 · 103 |
| nim-preface-1926 | 12 · 2 · 0 · 10 · 0 · 3 | 12 · 2 · 0 · 10 · 0 · 1 |

All sets: `over` 223 → 123, wrong 50 → 50, right 3586 → 3541 (−45). The tool now abstains on
words that have a native twin (e.g. 시내, 생각, 도막) instead of writing the Sino-Korean one;
that costs 45 right words and removes 100 words written in Hanja where the author kept Hangul.

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
