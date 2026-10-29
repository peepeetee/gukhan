# Third-party notices

This file lists every third-party component and data source that gukhan
depends on or redistributes, with its licence as stated on the source's own
page. CI fails if a Python dependency under GPL or AGPL is installed; see
`.github/workflows/licence-check.yml`.

Keep this list in sync with `pyproject.toml` and with the lexicon build
manifest. Add a row when you add a dependency or a data source; never remove
a row for data that is still shipped.

## Code dependencies

Runtime: `kiwipiepy>=0.24` (Apache-2.0) with its model package
`kiwipiepy_model` (Apache-2.0; contains the pretrained CoNg language model
`cong.mdl` and dictionaries, selected as `model_type="cong"`). Earlier
versions are not covered by this Apache-2.0 selection. Dev only: pytest, ruff, pip-licenses.

한국어: Apache-2.0 적용 버전인 `kiwipiepy>=0.24`만 사용합니다.

Browser tests only: Playwright (Apache-2.0; 1.64.1 pinned in
`.github/workflows/extension.yml`, 1.63.0 used for the first passing run),
installed by CI or the developer; not bundled in the extension. Source: <https://github.com/microsoft/playwright/blob/main/LICENSE>.
Optional font: Noto Serif CJK KR (SIL OFL 1.1), not bundled; see `docs/fonts.md`.

Analysers considered (Kiwi chosen; see docs/PLAN.md §2):

| Component | Licence | Notes | Source |
| --- | --- | --- | --- |
| Kiwi / kiwipiepy (runtime dependency) | Apache-2.0 (code and trained model files) | Bundles Eigen under MPL-2.0 (file-level copyleft, acceptable) and MIT/BSD parts | <https://github.com/bab2min/Kiwi/blob/main/LICENSE>, <https://github.com/bab2min/Kiwi/blob/main/NOTICE> |
| mecab-ko | GPL, LGPL or BSD at the user's choice | Use under the BSD option only | <https://bitbucket.org/eunjeon/mecab-ko/raw/master/COPYING> |
| mecab-ko-dic | Apache-2.0 | Trained on the 21세기 세종계획 corpus; the corpus itself is not redistributed | <https://bitbucket.org/eunjeon/mecab-ko-dic/raw/master/README.md> |

## Data sources

Data is never mixed into the Apache-2.0 code. It ships only in the separate
`gukhan-lexicon` package, under the licence of its sources.

| Source | Licence | Share-alike | Used for | Licence statement |
| --- | --- | --- | --- | --- |
| Unicode Unihan database (`kHangul` readings) | Unicode License v3 | No | Per-character Hanja readings | <https://www.unicode.org/terms_of_use.html>, <https://unicode.org/license.html> |
| 표준국어대사전 (National Institute of Korean Language) | CC BY-SA 2.0 KR | Yes | Sino-Korean word lexicon (headword, Hanja form). Usage examples (용례) that cite an external source are excluded, as the policy requires. The dump requires a 국립국어원 account with Korean identity verification (본인인증), so it is optional | <https://stdict.korean.go.kr/join/copyrightPolicy.do> |
| 우리말샘 (National Institute of Korean Language, open contributor-edited dictionary) | CC BY-SA 2.0 KR for all material not marked otherwise, including contributor-written entries; media files and source-cited 용례 excluded | Yes | Sino-Korean word lexicon (headword, Hanja form, part of speech, definition excerpt) via `--opendict`; only 일반어 senses of 어휘/구 entries, no examples. 표준국어대사전 takes precedence for a pair both have. Same NIKL licence, so the build licence does not change. Policy page verified from a browser capture on 2026-10-28 | <https://opendict.korean.go.kr/service/copyrightPolicy> |
| Wiktionary, English edition, Korean entries (Wikimedia contributors), read through the wiktextract JSONL published by kaikki.org | CC BY-SA 4.0 (Wikimedia Terms of Use since 2023; earlier contributions CC BY-SA 3.0, upgradeable) + GFDL 1.3 | Yes | Sino-Korean word lexicon (headword, Hanja form, gloss). Login-free alternative to 표준국어대사전. kaikki.org itself states no licence of its own and asks for citation of Ylonen, *Wiktextract* (LREC 2022); the data remains Wiktionary content | <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>, <https://kaikki.org/dictionary/Korean/>, <https://kaikki.org/dictionary/rawdata.html> |
| Korean Wikipedia (Wikimedia contributors), article lead sentences in the pages-articles dump | CC BY-SA 4.0 + GFDL (Wikimedia Terms of Use; en.wikipedia states CC BY-SA 4.0 with most text also under GFDL) | Yes | Names only (`--kowiki`): the bold title and the first parenthesised Hanja form of main-namespace articles, as proper-noun entries; every Hanja is checked against Unihan readings. Written against the documented export format and hand-made fixtures; not yet run on a real dump. Licence not read from ko.wikipedia.org itself, which does not load from the cloud container | <https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>, <https://dumps.wikimedia.org/kowiki/latest/> |
| Wikidata lexemes (Wikidata contributors), lexeme JSON dump | CC0 1.0 for structured data in the main, property and lexeme namespaces (Wikidata:Licensing, quoted 2026-10-28) | No | Optional Hanja forms of Korean lexemes (`--wikidata-lexemes`). Coverage unknown: run `python -m gukhan.lexicon_build.wikidata_lexemes <dump>` first. Not yet run on a real dump | <https://www.wikidata.org/wiki/Wikidata:Licensing>, <https://dumps.wikimedia.org/wikidatawiki/entities/> |

Not used at present, recorded for the audit trail:

| Source | Licence | Reason not used |
| --- | --- | --- |
| Wiktionary, Korean edition | CC BY-SA 4.0 + GFDL | Not parsed yet; the English edition's Korean entries carry explicit Hanja forms and are used instead |
| UTagger | Research-only terms, no open licence | Excluded entirely; no code, dictionaries or outputs are used or compared against |

## Attribution text for the lexicon package

### Ranking sources / 후보 순서 자료

| Source | Licence | Use |
| --- | --- | --- |
| 國立國語院 한국어기초사전 | CC BY-SA 2.0 KR | 초급/중급/고급 vocabulary levels, matched by headword and Hanja; [mirror](https://github.com/spellcheck-ko/korean-dict-nikl), [policy](https://krdict.korean.go.kr/kor/copyRightPolicy) |
| 國立國語院 한국어 학습용 어휘 목록 (2003) | KOGL Type 1 | Frequency rank for exact headword/Hanja matches; attribution: National Institute of Korean Language, 2003 learner vocabulary list, adapted for candidate ordering; [source and licence](https://www.korean.go.kr/front_eng/down/down_02V.do?etc_seq=70) |

한국어: 國立國語院 자료를 후보 정렬용으로 가공했습니다. 용례·음성·번역은 배포하지 않습니다.
English: only ranking metadata is extracted; examples, audio and translations are not distributed.
The stdict (88 XML chunks, dump date 2026-06-05), krdict (11 XML chunks,
creation date 2026-06-19) and opendict (25 XML chunks, 우리말샘, build date
2026-06-02) downloads use mirror commit
`42c0d01889f34536e9cf94fe57f62bd2055b1bde`. Input hashes are in the build manifest.

The `gukhan-lexicon` package and the Chrome extension must display:

> 이 사전 데이터는 國立國語院 《標準國語大辭典》(stdict.korean.go.kr)을 바탕으로 만들어졌으며,
> 크리에이티브 커먼즈 저작자표시-동일조건변경허락 2.0 대한민국 라이선스(CC BY-SA 2.0 KR)에 따라 配布됩니다.
> 漢字 讀音은 Unicode Unihan database(Unicode License v3)를 사용하였습니다.

When 우리말샘 is included the first sentence also names it:
國立國語院 《우리말샘》(opendict.korean.go.kr, CC BY-SA 2.0 KR). The builder
writes the exact text to `manifest.json` (`notice`).

When the lexicon is built from Wiktionary (alone or together with
표준국어대사전) the package licence is CC BY-SA 4.0 and the notice reads:

> 이 사전 데이터는 Wiktionary 寄與者들의 Korean 項目(en.wiktionary.org, kaikki.org의 wiktextract 抽出本)을
> 바탕으로 만들어졌으며, 크리에이티브 커먼즈 저작자표시-동일조건변경허락 4.0 國際 라이선스(CC BY-SA 4.0)에 따라 配布됩니다.
> 漢字 讀音은 Unicode Unihan database(Unicode License v3)를 사용하였습니다.

The builder writes the exact notice for each build into `manifest.json`.
