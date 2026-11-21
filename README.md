# gukhan · 國漢混用

Hangul → Hanja mixed-script converter. 한글 文章을 國漢文混用體로 바꿔 주는 道具입니다.
將韓文諺文轉為國漢混用文的工具。

Status: pre-release, not yet published to PyPI. Accuracy numbers come only from the public
regression set (see [Regression set and accuracy](#regression-set-and-accuracy)), never from
marketing. Plan: [docs/PLAN.md](docs/PLAN.md). Release steps: [docs/RELEASE.md](docs/RELEASE.md).

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
Wiktionary (kaikki.org) + 韓國語基礎辭典 + learner list + Unihan 18.0.0; 706,550 entries,
with the domain column and the native-word headwords),
Kiwi 0.24.1, default settings (evidence rules `default`, docs/PLAN.md §5a). A word is one
run of Hanja in the published text. "flagged or partial" counts words the tool left in Hangul
(abstained) or converted only in part; those are not errors. `wrong` is Hanja that differs from
the published text; `over` is Hanja written where the published text has Hangul.

| source | items | words | right | wrong | over | flagged or partial |
| --- | --- | --- | --- | --- | --- | --- |
| 大韓民國憲法 1948 | 321 | 1897 | 49.9% | 4 (0.2%) | 3 | 947 (862 flagged) |
| 憲法 1952 amendment | 352 | 2149 | 48.0% | 5 (0.2%) | 5 | 1113 |
| 憲法 1954 amendment | 360 | 2244 | 48.8% | 4 (0.2%) | 7 | 1144 |
| 大韓民國臨時憲章 1919 | 22 | 133 | 36.1% | 2 (1.5%) | 0 | 83 |
| 3·1獨立宣言書 1919 (hard set) | 35 | 497 | 30.2% | 9 (1.8%) | 4 | 338 |
| 님의 沈黙 1926, batches b1–b19 and preface (poetry) | 418 | 943 | 27.6% | 12 (1.3%) | 97 | 671 |
| 現行 法令 (modern-law, held out; `over` not meaningful, only glossed words are Hanja) | 1218 | 1458 | 23.1% | 21 (1.4%) | n/a | 1100 (990 flagged) |

On the 1948 text, 81.4% of the gold words are among the candidates the tool wrote or offered.
Full tables, `over` lists and per-rule effects are in tests/regression/README.md.

Reading the numbers:

- The tool abstains rather than guesses: about half of the words in the constitutions stay in
  Hangul. That is the intended trade, and a user override file turns repeated flags into
  conversions (`gukhan review`).
- `over` is the weak spot on literary text. In 님의 沈黙 the author wrote many native words in
  Hangul, and the tool sometimes reads them as Sino-Korean: 별→別, 거→炬, 번→番, 조→兆. Since the
  native-word headwords were added, 사랑 is no longer converted to 舍廊 (it was in at least 30 cases
  before), and `over` on the poetry fell from 143 to 97 on a larger set (943 words). An override
  line (`별 = -`) keeps a word in Hangul.
- The constitutions and 님의 沈黙 are pre-1970 texts, written for a register the Kiwi analyser was
  not trained on. The only modern-text check is `modern-law`, current statutes with the Hanja
  glosses the legislature prints in parentheses: 23.1% right, 1.4% wrong, 990 flagged. That set
  covers legal vocabulary only; accuracy on general modern prose has not been measured.

한국어: 憲法 本文에서 誤變換은 0.2~0.3%이나 절반 이상은 變換하지 않고 남깁니다. 詩集에서는
固有語를 漢字語로 읽는 誤變換(사랑→舍廊)이 가장 큰 約點입니다. 現行 法令에서는 正答 23.1%, 誤變換 1.4%이며, 一般 現代 文章의 正確度는 아직 測定하지 않았습니다.

Per Hanja character on the 1948 text: 54.9% right, 0.1% wrong (6 of 4,038). The four wrong words
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
