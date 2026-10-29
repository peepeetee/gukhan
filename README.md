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

`--rules default|all|none|<names>` chooses the evidence rules that narrow a flag's
candidates (docs/PLAN.md §5a); `default` is on, `verb` is opt-in.
`--report` writes flagged homographs and the review list (names and unknown
words) with line and column; `--mark` shows flagged words inline as
`전기{電氣|傳記}`. An override file is plain text, one decision per line:

```
전기 = 電氣          # always this reading
전기 공학 = 電氣 工學  # phrase, matched before single words
의사 = -            # keep in Hangul
이순신 = 李舜臣      # add a word
```

Flagged words that no rule can settle (國家 or 國歌?) need a reader. `gukhan review`
shows each one in context with its numbered candidates and appends your choice to the
override file, so the next run reuses it. Nothing is preselected and Enter does nothing:

```
gukhan review input.md --lexicon build/lexicon/ --overrides my.txt
#  3    this Hanja for the word everywhere      k   keep Hangul      s   skip
#  n3   only where the same next word follows   p3  only after the same previous word
#  u    undo the last answer                    q   save and quit (every answer is saved at once)
#  漢字  type the Hanja yourself (also for words with no entry; add --include-review)
```

Build the lexicon (nothing is downloaded; see docs/PLAN.md §3 for where the
inputs come from):

```
# login-free: Wiktionary Korean entries via kaikki.org (CC BY-SA 4.0)
gukhan-lexicon-build --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip -o build/lexicon
# with a 표준국어대사전 dump too, or instead (the full dump is mirrored login-free; see docs/data-distribution.md)
gukhan-lexicon-build --stdict stdict_dump.zip --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip -o build/lexicon
# plus 우리말샘 (opendict.korean.go.kr dump, CC BY-SA 2.0 KR; contributor-edited, so
# 표준국어대사전 represents a pair when both have it)
gukhan-lexicon-build --stdict stdict/ --opendict opendict/ --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip -o build/lexicon
```

`--opendict` keeps only 일반어 senses of 어휘 and 구 entries: dialect (방언),
North-Korean (북한어) and archaic (옛말) senses, proverbs, idioms and spellings
the dictionary marks as non-standard are skipped, and usage examples are never
read.

## How it works

text → morphological analysis (Kiwi) → longest-match lookup in a Sino-Korean
lexicon → choose Hanja (user override list, then rule, then flag) → splice
Hanja into the original text, endings untouched. Unresolved homographs are
flagged, never guessed. Runs on a laptop CPU. gukhan trains no model of its
own and has no Hanja-selection network; Hanja choice is dictionary lookup,
overrides and rules. The morphological analysis step is Kiwi, which loads
its own pretrained language model: in kiwipiepy 0.24.1 that is the CoNg
(Contextual N-gram embedding) neural model, which gukhan selects explicitly
(`model_type="cong"`) so results are reproducible across runs. The Chrome
extension processes text locally and sends nothing anywhere.

## Regression set and accuracy

`tests/regression/` holds public sentences from pre-1970 mixed-script texts
(first: 大韓民國憲法 1948) with their Hangul form. `gukhan-regress score
tests/regression/*.tsv --lexicon build/lexicon` is the only source of any
accuracy figure.

Scores, 2026-10-29, lexicon built from 標準國語大辭典 + 우리말샘 + Wiktionary
(kaikki.org) + 韓國語基礎辭典 + Unihan 18.0.0 (705,000 lines), Kiwi 0.24.1, default settings
(evidence rules `default`, docs/PLAN.md §5a):

| source | items | words | right | wrong | flagged or partial |
| --- | --- | --- | --- | --- | --- |
| 大韓民國憲法 1948 | 321 | 1897 | 47.0% | 5 (0.3%) | 1000 |
| 憲法 1952 amendment | 352 | 2149 | 45.0% | 6 (0.3%) | 1176 |
| 憲法 1954 amendment | 360 | 2244 | 45.5% | 5 (0.2%) | 1219 |
| 大韓民國臨時憲章 1919 | 22 | 133 | 35.3% | 2 (1.5%) | 84 |
| 3·1獨立宣言書 1919 (hard set) | 35 | 497 | 30.2% | 9 (1.8%) | 338 |

The same sets before 우리말샘 and the evidence rules (2026-10-28): right 44.7%,
42.5%, 42.6%, 32.3%, 27.4%; wrong 13, 14, 15, 4, 13 words. Full tables, with
`over` and per-rule effects, are in tests/regression/README.md.

Per Hanja character on the 1948 text: 48.7% right, 0.4% wrong. The larger
dictionary removes the reported 繼承→階乘, 移轉→以前 and 前項→全항 errors,
but increases abstentions. Errors remain, including 大法院→帶법원 and
archaic 안이→安易. These historical texts do not establish modern-text accuracy.
한국어: 사전 확대로 일부 오변환은 줄었지만 보류는 늘었습니다. 1919년 옛말,
하야·안이·옛 자모와 인명은 현대 형태소 분석기의 한계로 수동 검토가 필요합니다.
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
