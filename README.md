# gukhan · 國漢混用

Hangul → Hanja mixed-script converter. 한글 文章을 國漢文混用體로 바꿔 주는 道具입니다.
將韓文諺文轉為國漢混用文的工具。

Status: pre-release, not yet published to PyPI. Accuracy numbers come only from the public
regression set (see [Regression set and accuracy](#regression-set-and-accuracy)), never from
marketing. Plan: [docs/PLAN.md](docs/PLAN.md). Release steps: [docs/RELEASE.md](docs/RELEASE.md). Optional local-model suggestions for flagged words: [docs/local-model.md](docs/local-model.md).

## Install and use

```
pip install gukhan                 # code only (Apache-2.0); pulls kiwipiepy with its model
pip install "gukhan[lexicon]"      # plus the prebuilt lexicon, gukhan-lexicon (CC BY-SA 4.0)
gukhan input.md             # converted text to stdout (installed lexicon, else a tiny sample)
gukhan input.md -o out.md --report flagged.tsv --overrides my.txt --mark
gukhan input.md --lexicon build/lexicon/     # a lexicon you built
gukhan chapters/*.md --out-dir converted/      # many files, copies; the model loads once
gukhan notes/*.md --in-place                 # overwrite, keeping each original as FILE.bak
```

Several input files need `--out-dir DIR` (new files, never overwritten) or `--in-place`
(each original is first copied to `FILE.bak`; an existing backup stops the run; `--no-backup`
and `--backup-suffix` change that). Without one of them gukhan refuses, and every input is
checked and read before anything is written. `--report` takes a single input.

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

As a library (the model loads on first use; pass a `Lexicon` for real work):

```python
from gukhan.convert import Converter, Kind
from gukhan.lexicon import Lexicon

conv = Converter(Lexicon.installed() or Lexicon.sample())
result = conv.convert("국군은 작전 계획을 수립하였다.")
print(result.text)  # converted text, endings untouched
for d in result.of(Kind.FLAGGED):  # homographs left in Hangul, with candidates
    print(d.hangul, [c.hanja for c in d.candidates])
```

Other formats / 다른 形式: HTML, Word (`.docx`), EPUB and subtitles (`.srt`, `.vtt`) are chosen by file
extension (`--format` overrides it). Only the text is converted; tags, styles, timing and every other part of the
file are copied unchanged, and the tests check that for each format: `docs/formats.md`.

```
gukhan page.html -o page.hanja.html
gukhan thesis.docx --in-place      # the original is kept as thesis.docx.bak
```

For learners / 學習者用: `--style gloss` writes 국군(國軍), `--style hanja-gloss` 國軍(국군) and `--style ruby`
HTML `<ruby>` with the reading above each Hanja (default `mixed`: 國軍): `docs/styles.md`.

For learners / 學習者用: `--style gloss` writes 국군(國軍), `--style hanja-gloss` 國軍(국군) and `--style ruby`
HTML `<ruby>` with the reading above each Hanja (default `mixed`: 國軍): `docs/styles.md`.

Speed: about 0.36 MB/s on 4 cores (`--workers N` sets Kiwi's threads, `--jobs N` splits several files over
processes; the output never changes); numbers and method in `docs/performance.md` (處理 速度).

A worked example of the override file and of `gukhan review`, with every command run by the tests:
`docs/overrides-and-review.md` (使用者 安內 / user guide).

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

## How it works / 作動 方式

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

한국어: 形態素 分析(Kiwi) → 辭典 最長 一致 檢索 → 漢字 選擇(사용자 지정, 規則, flag 順) → 原文에 漢字만 끼워 넣고
語尾는 그대로 둡니다. 同音異義語가 가려지지 않으면 추측하지 않고 flag합니다. 自體 學習 模型이나 漢字 選擇用
神經網은 없습니다. 확장 프로그램은 글을 기기 안에서만 處理합니다.

## Regression set and accuracy

`tests/regression/` holds public sentences from pre-1970 mixed-script texts
(first: 大韓民國憲法 1948) with their Hangul form. `gukhan-regress score
tests/regression/*.tsv --lexicon build/lexicon` is the only source of any
accuracy figure.

Scores, 2026-11-21, on the lexicon built that day from main (標準國語大辭典 88 chunks + 우리말샘 +
Wiktionary (kaikki.org) + 韓國語基礎辭典 + learner list + Unihan 18.0.0; 706,729 entries,
with the domain column, native headwords kept per part of speech (#58) and no statute glosses),
Kiwi 0.24.1, default settings (evidence rules `default`, docs/PLAN.md §5a). A word is one
run of Hanja in the published text. "flagged or partial" counts words the tool left in Hangul
(abstained) or converted only in part; those are not errors. `wrong` is Hanja that differs from
the published text; `over` is Hanja written where the published text has Hangul.

| source | items | words | right | wrong | over | flagged or partial |
| --- | --- | --- | --- | --- | --- | --- |
| 大韓民國憲法 1948 | 321 | 1897 | 49.4% | 4 (0.2%) | 3 | 955 (870 flagged) |
| 憲法 1952 amendment | 352 | 2149 | 47.4% | 5 (0.2%) | 5 | 1126 |
| 憲法 1954 amendment | 360 | 2244 | 48.1% | 4 (0.2%) | 7 | 1161 |
| 大韓民國臨時憲章 1919 | 22 | 133 | 36.1% | 2 (1.5%) | 0 | 83 |
| 3·1獨立宣言書 1919 (hard set) | 35 | 497 | 30.2% | 9 (1.8%) | 4 | 338 |
| 님의 沈黙 1926, batches b1–b19 and preface (poetry) | 418 | 943 | 27.6% | 11 (1.2%) | 84 | 672 |
| 現行 法令 modern-law-heldout (held out; `over` not meaningful, only glossed words are Hanja) | 649 | 723 | 23.4% | 9 (1.2%) | n/a | 545 |
| 現行 法令 modern-law-tuning (rules were fitted on it; `over` not meaningful) | 547 | 592 | 23.1% | 7 (1.2%) | n/a | 448 |

With statute glosses (`--law-glosses`, the 40 statutes of `modern-law-laws.tsv`, fetched 2026-11-21)
added to the lexicon, and the held-out pairs excluded (`--law-glosses-exclude modern-law-heldout.tsv`):
held-out stays at 23.4% right (169 of 723) with 10 wrong (1.4%), 544 flagged or partial. That is what
the exclusion is for: the pairs under test are not in the lexicon, and the extra words do not help
anything else. The tuning half rises from 23.1% to 40.4% right (7 to 5 wrong) because its own pairs
are now in the lexicon; that number is circular and measures nothing. Excluding both halves gives the
no-gloss figures again (23.1% and 23.4%). The constitutions gain at most 3 words (1948: 49.6%).

On the 1948 text, 81.4% of the gold words are among the candidates the tool wrote or offered.
Full tables, `over` lists and per-rule effects are in tests/regression/README.md.

Reading the numbers:

- The tool abstains rather than guesses: about half of the words in the constitutions stay in
  Hangul. That is the intended trade, and a user override file turns repeated flags into
  conversions (`gukhan review`).
- `over` is the weak spot on literary text. In 님의 沈黙 the author wrote many native words in
  Hangul, and the tool sometimes reads them as Sino-Korean: 별→別, 거→炬, 번→番, 조→兆. Since the
  native-word headwords were added, 사랑 is no longer converted to 舍廊 (it was in at least 30 cases
  before), and `over` on the poetry fell from 143 to 84 on a larger set (943 words); #58 (native homographs kept per part of speech) took off a further 13. An override
  line (`별 = -`) keeps a word in Hangul.
- The constitutions and 님의 沈黙 are pre-1970 texts, written for a register the Kiwi analyser was
  not trained on. The only modern-text check is `modern-law`, current statutes with the Hanja
  glosses the legislature prints in parentheses: on the held-out half 23.4% right, 1.2% wrong, 545 flagged or partial. That set
  covers legal vocabulary only; accuracy on general modern prose has not been measured.

한국어: 憲法 本文에서 誤變換은 0.2~0.3%이나 절반 이상은 變換하지 않고 남깁니다. 詩集에서는
固有語를 漢字語로 읽는 誤變換(사랑→舍廊)이 가장 큰 約點입니다. 現行 法令(保留 標本)에서는 正答 23.4%, 誤變換 1.2%이며, 一般 現代 文章의 正確度는 아직 測定하지 않았습니다.

Per Hanja character on the 1948 text: 54.7% right, 0.1% wrong (6 of 4,038). The four wrong words
there are 總綱→銃腔, 命→名, 總理令→摠理營 and 國防上→國防相.
한국어: 1919년 옛말, 하야·안이·옛 자모와 인명은 현대 형태소 분석기의 한계로 수동 검토가 필요합니다.

## Licence

- Code: [Apache-2.0](LICENSE). Keep the [NOTICE](NOTICE) file with any copy.
- Lexicon data: distributed separately as `gukhan-lexicon` under CC BY-SA 4.0 (the build
  includes Wiktionary's Korean entries, CC BY-SA 4.0), from 國立國語院 《標準國語大辭典》 and
  《우리말샘》 (CC BY-SA 2.0 KR) and the Unicode Unihan database. A build from the 國立國語院
  dictionaries alone would stay CC BY-SA 2.0 KR. The build manifest states which.

See [docs/licensing.md](docs/licensing.md) for the reasoning and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for every source.
