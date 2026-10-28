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
gukhan-lexicon-build --stdict stdict_dump.zip --unihan Unihan.zip -o build/lexicon
```

## How it works

text → morphological analysis (Kiwi) → longest-match lookup in a Sino-Korean
lexicon → choose Hanja (user override list, then rule, then flag) → splice
Hanja into the original text, endings untouched. Unresolved homographs are
flagged, never guessed. Runs on a laptop CPU with no neural model. The Chrome extension processes text locally and sends
nothing anywhere.

## Licence

- Code: [Apache-2.0](LICENSE). Keep the [NOTICE](NOTICE) file with any copy.
- Lexicon data: distributed separately as `gukhan-lexicon` under
  CC BY-SA 2.0 KR, built from 國立國語院 《標準國語大辭典》 and the Unicode
  Unihan database.

See [docs/licensing.md](docs/licensing.md) for the reasoning and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for every source.
