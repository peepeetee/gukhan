# gukhan · 國漢混用

Hangul → Hanja mixed-script converter. 한글 文章을 國漢文混用體로 바꿔 주는 道具입니다.
將韓文諺文轉為國漢混用文的工具。

Status: pre-alpha. The CLI converts text with a small bundled sample lexicon;
the real lexicon is built by `gukhan-lexicon-build` from a 표준국어대사전 dump
you obtain yourself. Accuracy numbers will come only from the public regression
set (milestone 4), never from marketing. Plan: [docs/PLAN.md](docs/PLAN.md).

## Install and use

```
pip install -e .            # pulls kiwipiepy (Apache-2.0) with its model
gukhan input.md             # converted text to stdout (sample lexicon)
gukhan input.md -o out.md --report flagged.tsv --overrides my.txt --mark
gukhan input.md --lexicon build/lexicon/     # a lexicon you built
```

`--report` writes flagged homographs and the review list (names and unknown
words) with line and column; `--mark` shows flagged words inline as
`전기{電氣|傳記}`. An override file is plain text, one decision per line:

```
전기 = 電氣          # always this reading
전기 공학 = 電氣 工學  # phrase, matched before single words
의사 = -            # keep in Hangul
이순신 = 李舜臣      # add a word
```

Build the lexicon (nothing is downloaded; see docs/PLAN.md §3 for where the
inputs come from):

```
# login-free: Wiktionary Korean entries via kaikki.org (CC BY-SA 4.0)
gukhan-lexicon-build --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip -o build/lexicon
# with a 표준국어대사전 dump too, or instead (needs a verified 국립국어원 account)
gukhan-lexicon-build --stdict stdict_dump.zip --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip -o build/lexicon
```

## How it works

text → morphological analysis (Kiwi) → longest-match lookup in a Sino-Korean
lexicon → choose Hanja (user override list, then rule, then flag) → splice
Hanja into the original text, endings untouched. Unresolved homographs are
flagged, never guessed. Runs on a laptop CPU with no neural model. The Chrome extension processes text locally and sends
nothing anywhere.

## Regression set and accuracy

`tests/regression/` holds public sentences from pre-1970 mixed-script texts
(first: 大韓民國憲法 1948) with their Hangul form. `gukhan-regress score
tests/regression/*.tsv --lexicon build/lexicon` is the only source of any
accuracy figure.

First scores, 2026-10-28 (民國115年), lexicon built from Wiktionary
(kaikki.org) + Unihan 18.0.0, default settings:

| source | items | words | right | wrong | over |
| --- | --- | --- | --- | --- | --- |
| 大韓民國憲法 1948 | 321 | 1897 | 48.4% | 22 (1.2%) | 0 |
| 憲法 1952 amendment | 352 | 2149 | 46.2% | 28 (1.3%) | 0 |
| 憲法 1954 amendment | 360 | 2244 | 46.2% | 32 (1.4%) | 0 |
| 大韓民國臨時憲章 1919 | 22 | 133 | 48.1% | 3 (2.3%) | 0 |
| 3·1獨立宣言書 1919 (hard set) | 35 | 497 | 22.9% | 31 (6.2%) | 9 |

Per Hanja character on the 1948 text: 60.7% right, 0.8% wrong. Nearly every
wrong word on the constitutions is a homograph the Wiktionary lexicon lacks
(繼承 written as 階乘, 移轉 as 以前, 前項 as 全항); a 표준국어대사전 build
is expected to close most of them. The 1919 declaration is pre-modern prose
(吾人 → 誤認, archaic 하야 → 下野) that the analyser was never trained on.
The large `flagged` share is by design: the tool abstains where it cannot be
sure, and a user override file turns repeated flags into conversions.

## Licence

- Code: [Apache-2.0](LICENSE). Keep the [NOTICE](NOTICE) file with any copy.
- Lexicon data: distributed separately as `gukhan-lexicon` under CC BY-SA,
  built from Wiktionary's Korean entries (CC BY-SA 4.0) and/or 國立國語院
  《標準國語大辭典》 (CC BY-SA 2.0 KR), validated with the Unicode Unihan
  database. The build manifest states which.

See [docs/licensing.md](docs/licensing.md) for the reasoning and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for every source.
