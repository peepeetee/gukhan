# gukhan 計劃 / Plan

Current implementation and remaining release gates / 현재 구현과 남은 검증:
see [STATUS.md](STATUS.md). The sections below retain the original design rationale.

Written 2026-10-28. Covers milestones 2 and 3 of the project brief
and what is deferred to the Chrome extension. Short by design; the code and
tests are the detailed record.

要約 (國漢文): 本 文書는 gukhan의 構造, 形態素 分析器 選擇, 辭典 構築 pipeline,
資料 形式, CLI 設計, test 戰略을 定한다. 漢字 變換은 「override → 規則 → flag」
順序로 하며 同音異義語는 推測하지 않고 flag한다.

## 1. Architecture

```
text ──▶ segment (protect code/URLs) ──▶ Kiwi morphological analysis
     ──▶ longest-match lexicon lookup over noun-like tokens
     ──▶ decide: override file → rule → flag
     ──▶ splice Hanja into the original string (endings stay in Hangul)
     ──▶ output text + flagged-word report + review list
```

Only the characters of a matched lexicon headword are replaced. Everything
else in the input, including particles, endings, spacing and punctuation, is
copied through unchanged, so the converter can never damage grammar. Pure
CPU; gukhan trains nothing and has no Hanja-selection network. Kiwi's own
pretrained language model (CoNg, see §2) is the only learned component, and
it only decides segmentation and part of speech.

Module layout (`src/gukhan/`):

| Module | Role |
| --- | --- |
| `analyser.py` | Thin wrapper over `kiwipiepy`; yields `Token(form, tag, start, end)`. Swappable (tests use a fake). |
| `lexicon.py` | Load the TSV lexicon, index by Hangul headword, longest-match search. |
| `overrides.py` | Parse the user override file. |
| `convert.py` | The pipeline above; produces `Decision` records (converted, flagged, review, kept). |
| `segments.py` | Split Markdown/plain text into convertible and protected spans (fenced code, inline code, URLs). |
| `report.py` | Flagged-word report and review list (TSV and Markdown). |
| `cli.py` | `gukhan` command. |
| `lexicon_build/` | Milestone 2: `stdict.py` (표준국어대사전 XML dump parser), `unihan.py` (kHangul readings), `manifest.py`, `cli.py` (`gukhan-lexicon-build`). |

## 2. Morphological analyser: Kiwi (kiwipiepy)

Chosen over mecab-ko / mecab-ko-dic because:

- Licence: Apache-2.0 for code *and* model files. mecab-ko is a GPL/LGPL/BSD
  triple that must be used under BSD only, with a separately installed
  dictionary; the licence check in CI is simpler with one Apache component.
- Install: `pip install kiwipiepy` gives prebuilt wheels on Linux, macOS and
  Windows with the model included. mecab-ko needs a native build or system
  package plus `mecab-ko-dic`, which is the main source of user install
  failures for Korean NLP tools.
- Output: character offsets per token, Sejong-style tags (NNG/NNP/NR/XR…),
  irregular conjugation handled, and a user-dictionary API for later tuning.
- Measured here: model load about 2 s, then thousands of sentences per second
  on one CPU core.

Language model. Kiwi scores candidate morpheme paths with a pretrained
language model. kiwipiepy 0.24.1 ships (package `kiwipiepy_model` 0.24.0)
the CoNg (Contextual N-gram embedding) model, `cong.mdl`, about 76 MB on
disk, plus the `cong-global` variant; the older KnLM and SkipBigram models
were dropped from the default model files in 0.22. Kiwi's default
`model_type="none"` means "fastest available", so `analyser.py` passes
`model_type="cong"` explicitly and `KiwiAnalyser.describe()` reports the
version and model actually loaded. CoNg is a neural model; its layer sizes
and parameter count have not been verified here and are not claimed. gukhan
trains nothing, fine-tunes nothing, and the regression texts and collected
literature are evaluation material, never training data.

言語 model (國漢文): gukhan은 自體 model을 訓練하지 않는다. Kiwi가 싣고 오는
CoNg 事前學習 言語 model은 形態素 分析에만 쓰이며 漢字 選擇에는 關與하지 않는다.

What Kiwi does *not* do: it never outputs Hanja. All Hanja comes from the
lexicon, so analyser errors can only cause a missed or wrong *segmentation*,
not an invented Hanja form.

Only tokens tagged NNG, NNP, NR, XR, XPN, XSN, MAG (Sino-Korean adverbs such as
卽, 約), MM (관형사 such as 各, 每) and NNB (dependent nouns such as 條, 項)
are candidates for lookup, and each tag accepts only matching lexicon parts of
speech: an MM token matches 관형사 entries only, an NNB token 의존 명사 only,
so native numerals and counters (세 시) are never flagged with noun readings.
Verb/adjective stems are reached through their noun root (`研究하다` is
`연구/NNG + 하/XSV`), so `-하다`, `-되다`, `-적` words convert naturally.

## 3. Lexicon build pipeline (milestone 2)

Sources, either or both:

1. 國立國語院 《標準國語大辭典》 full XML dump, CC BY-SA 2.0 KR. Not on a
   public URL: the user creates an account on <https://stdict.korean.go.kr>,
   requests 「사전 내려받기」 and downloads the XML zip. As of 2026-10-28 the
   account needs Korean identity verification (본인인증), which rules it out
   for many users. 우리말샘 sign-up goes through the same verification page.
2. Wiktionary (English edition) Korean entries, CC BY-SA 4.0, read through
   the wiktextract JSONL that kaikki.org publishes with no login:
   <https://kaikki.org/dictionary/Korean/kaikki.org-dictionary-Korean.jsonl>
   (about 200 MB; roughly 58 000 Korean headwords, Hanja forms tagged
   `hanja`). A build that includes it is CC BY-SA 4.0; see docs/licensing.md.

The builder takes file paths; nothing is fetched automatically, and nothing
from either source is committed to this repository.

Unihan: `Unihan.zip` from <https://www.unicode.org/Public/UCD/latest/ucd/>.
Used for `kHangul` per-character readings, which the builder uses to
*validate* each entry (every Hanja character must have the headword's
syllable as one of its readings, allowing 頭音法則) and to populate a
character-level fallback table. Entries that fail validation are written to a
rejects file, not into the lexicon.

Builder: `gukhan-lexicon-build [--stdict <zip|dir>] [--wiktextract <jsonl>]
[--unihan Unihan.zip] -o out/` produces:

- `lexicon.tsv`: one line per (headword, Hanja) pair. Columns:
  `hangul  hanja  pos  source  sense`. Homographs are simply repeated
  headwords. The file is sorted and deterministic, so two builds of the same
  input give the same bytes.
- `chars.tsv` (if Unihan given): `hanja  readings`.
- `manifest.json`: builder version, source file names, sizes and SHA-256,
  Unihan version, entry counts, build time, the resulting licence and the
  attribution notice to display.
- `rejects.tsv`: entries dropped and why.

Entry selection from the dump: `word_type` is 한자어 or 혼종어 and the
original-language field contains CJK characters. Mixed entries keep the
Hangul part as Hangul (`한자어+고유어` such as 木手일 → only the Sino part is
Hanja). Entries whose Hanja field contains `▽` (variant marks), `-`, or
parentheses are normalised by stripping those marks. Usage examples are never
read, which keeps the source-cited 용례 exclusion trivially satisfied.

Sample data for development and tests: `src/gukhan/data/sample_lexicon.tsv` is a small
hand-written list (about 80 common words including homograph traps such as
전기, 사과, 의사, 부정). It is not derived from any dictionary and exists
only so the converter and tests run without the dump. The real lexicon ships
separately as `gukhan-lexicon`.

Status of this environment: stdict.korean.go.kr and unicode.org are both
unreachable from the build container, so the parser is written from the
dump's documented schema and tested only on a hand-written fixture in the same
shape. The first run on a real dump will need a schema check; the builder
prints which fields it found and fails loudly if the expected ones are absent.

## 4. Data formats

Lexicon TSV (UTF-8, `#` comments, tab separated):

```
# gukhan lexicon  licence=CC-BY-SA-2.0-KR  manifest=manifest.json
전기	電氣	명사	stdict:12345	electricity	12
전기	傳記	명사	stdict:12346	biography	11
대한민국	大韓民國	명사	stdict:...		10
```

The optional sixth column `weight` orders candidates in flag lists (higher
first). It is a crude likelihood, not a frequency: the Wiktionary builder
gives 10 to readings listed on the Hangul page, plus one per sense and one
per derived or related term (each capped at 9). A real frequency signal is
future work and would need a licence-clean corpus.

Override file (plain text, one decision per line, shareable):

```
# 「hangul = hanja」. Left side may be a word or a phrase.
전기 = 電氣          # always this reading
전기 공학 = 電氣 工學  # phrase override, matched before single words
의사 = -            # keep this word in Hangul
이순신 = 李舜臣      # add a word the lexicon lacks
```

Decision order for each matched span: override (longest phrase first) → rule
→ flag. Rules: exactly one lexicon candidate → use it, unless the lexicon is
weighted and the entry's weight is below `--min-weight` (default 0, off:
on the 1948 constitution a cutoff of 12 cut wrong from 1.4% to 0.5% but
right from 48.7% to 21.7%), in which case it is flagged; several candidates with identical Hanja → use it;
otherwise flag. A one-syllable common noun with a lone entry is flagged too,
because almost every Sino-Korean syllable has many Hanja and one entry means
a lexicon gap (前項 → 全항 came from that); closed classes (counters,
prefixes, suffixes, adverbs, determiners) are exempt, and an override such as
`약 = 藥` settles the frequent ones. An entry whose Hanja column repeats the Hangul marks a native
word of the same sound (안 = inside), so 안 is flagged between 案 and the
native word rather than written. Native bound nouns (할 수 있다, 그럴 리가)
are never looked up. Proper nouns (NNP) with no lexicon entry go to the
review list; nothing is guessed.

## 5. CLI (milestone 3)

```
gukhan input.md                      # converted text to stdout
gukhan input.md -o out.md            # write converted file
gukhan input.md --overrides my.txt   # apply an override file (repeatable)
gukhan input.md --report flagged.tsv # flagged words and review list
gukhan input.md --mark               # flagged words shown as 전기{電氣|傳記}
gukhan input.md --lexicon path/      # use a built lexicon instead of the sample
gukhan --stdin                       # read from stdin
```

Exit status 0 on success, 2 on a usage or file error. Messages in Korean and
English on one line each. Markdown handling in this milestone: fenced code,
inline code and URLs are left alone; everything else is treated as text.

Flagged-word report columns: `line  col  hangul  candidates  context`. The
review list (names and unknown words) follows with the same columns and
`candidates` empty.

## 6. Test strategy

- Unit tests with a fake analyser: lexicon loading, longest match, override
  parsing and precedence, rule/flag decisions, splice correctness (output
  length and non-matched text identical to input), Markdown protection.
- One integration test with the real Kiwi on a handful of sentences, so the
  tag set assumptions are checked on every CI run.
- Builder tests on a hand-written XML fixture in the dump's schema plus a
  tiny Unihan-format fixture: deterministic output, manifest hashes, rejects.
- Accuracy is reported only from the public regression set (milestone 4),
  never from these unit tests.
- CI: `pytest`, `ruff`, and the existing licence check, on pull requests and
  main.

## 6a. Regression set (milestone 4)

Sentences come from pre-1970 texts first published in 國漢文混用, so the
Hanja choice is the author's: statutes and constitutions (no copyright,
저작권법 제7조), literature by authors who died before 1962, anonymous
ephemera before 1956. First set: 大韓民國憲法 1948 from the Constitutional
Court's history pages. `scripts/fetch_corpus.py` downloads the texts listed
in `tests/regression/sources.tsv`; `gukhan-regress prepare` derives the
Hangul input from the gold text with Unihan readings (頭音法則 at the start of
each Hanja run, a preference table for 不/金/樂…, everything else guessed is
marked CHECK for a person); `gukhan-regress score` reports right / flagged /
wrong / over per Hanja run. See tests/regression/README.md.

## 7. Deferred to the Chrome extension (milestone 5)

- A JavaScript runtime: Kiwi is C++. Options to evaluate then: WebAssembly
  build of Kiwi, or a lighter longest-match-only mode without morphology for
  the extension. Nothing in the Python pipeline assumes either.
- Per-site toggle, click-a-word to see candidates, saving an override from
  the popup. The override file format above is already what the popup would
  write, so files stay shareable between CLI and extension.
- Privacy policy text (all processing local).

## 8. Out of scope

Hanja → Hangul, other languages, hosted service, training models, anything
from UTagger.
