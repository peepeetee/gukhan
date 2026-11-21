# API reference / API 參照

Everything on this page is the public API of the `gukhan` package; names not listed here are internal and
may change without notice (see the [API policy](api-policy.md)). 이 面에 있는 것이 公開 API이며, 나머지는 內部用입니다.

A minimal use / 最小 例:

```python
from pathlib import Path

from gukhan import Converter, Lexicon, Overrides

conv = Converter(Lexicon.load(Path("build/lexicon")), Overrides.load(Path("my.txt")))
result = conv.convert("국군은 작전 계획을 수립하였다.", mark=True)
print(result.text)
for d in result.decisions:  # one Decision per word: CONVERTED, FLAGGED, REVIEW or KEPT
    print(d.kind.value, d.hangul, d.hanja)
```

## Converting / 變換

The one-shot helper `gukhan.convert.convert(text, **converter_options)` returns a `Result` too; it is not
re-exported at package level so that the name `gukhan.convert` stays the module.

::: gukhan.Converter
::: gukhan.Result
::: gukhan.Decision
::: gukhan.Kind

## Lexicon and overrides / 辭典과 사용자 지정

::: gukhan.Lexicon
::: gukhan.Entry
::: gukhan.Overrides

## Analysers / 形態素 分析器

::: gukhan.Analyser
::: gukhan.KiwiAnalyser
::: gukhan.ListAnalyser
::: gukhan.Token

## Reports / 報告

::: gukhan.report
    options:
      members: [rows, summary, to_tsv, to_markdown]

## Review / 檢討

::: gukhan.review
    options:
      members: [Group, Reviewer, collect]

## Local-model suggestions / 局所 모델 提案

::: gukhan.suggest
    options:
      members: [Backend, Suggestion, SuggestError, OpenAIChatBackend, MockBackend, collect_suggestions, apply_suggestions]
