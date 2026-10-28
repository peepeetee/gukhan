# Third-party notices

This file lists every third-party component and data source that gukhan
depends on or redistributes, with its licence as stated on the source's own
page. CI fails if a Python dependency under GPL or AGPL is installed; see
`.github/workflows/licence-check.yml`.

Keep this list in sync with `pyproject.toml` and with the lexicon build
manifest. Add a row when you add a dependency or a data source; never remove
a row for data that is still shipped.

## Code dependencies

None yet. The project has no runtime dependencies at this stage.

Candidate analysers under evaluation (not yet depended on):

| Component | Licence | Notes | Source |
| --- | --- | --- | --- |
| Kiwi / kiwipiepy | Apache-2.0 (code and trained model files) | Bundles Eigen under MPL-2.0 (file-level copyleft, acceptable) and MIT/BSD parts | <https://github.com/bab2min/Kiwi/blob/main/LICENSE>, <https://github.com/bab2min/Kiwi/blob/main/NOTICE> |
| mecab-ko | GPL, LGPL or BSD at the user's choice | Use under the BSD option only | <https://bitbucket.org/eunjeon/mecab-ko/raw/master/COPYING> |
| mecab-ko-dic | Apache-2.0 | Trained on the 21세기 세종계획 corpus; the corpus itself is not redistributed | <https://bitbucket.org/eunjeon/mecab-ko-dic/raw/master/README.md> |

## Data sources

Data is never mixed into the Apache-2.0 code. It ships only in the separate
`gukhan-lexicon` package, under the licence of its sources.

| Source | Licence | Share-alike | Used for | Licence statement |
| --- | --- | --- | --- | --- |
| Unicode Unihan database (`kHangul` readings) | Unicode License v3 | No | Per-character Hanja readings | <https://www.unicode.org/terms_of_use.html>, <https://unicode.org/license.html> |
| 표준국어대사전 (National Institute of Korean Language) | CC BY-SA 2.0 KR | Yes | Sino-Korean word lexicon (headword, Hanja form). Usage examples (용례) that cite an external source are excluded, as the policy requires | <https://stdict.korean.go.kr/join/copyrightPolicy.do> |

Not used at present, recorded for the audit trail:

| Source | Licence | Reason not used |
| --- | --- | --- |
| 우리말샘 | CC BY-SA 2.0 KR (per secondary sources; policy page at <https://opendict.korean.go.kr/service/copyrightPolicy> was not machine-readable during the audit) | Deferred; same licence as 표준국어대사전, can be added later |
| Wiktionary (Korean, English) | CC BY-SA 3.0 or later + GFDL | Second licence version would complicate the data package |
| UTagger | Research-only terms, no open licence | Excluded entirely; no code, dictionaries or outputs are used or compared against |

## Attribution text for the lexicon package

The `gukhan-lexicon` package and the Chrome extension must display:

> 이 사전 데이터는 國立國語院 《標準國語大辭典》(stdict.korean.go.kr)을 바탕으로 만들어졌으며,
> 크리에이티브 커먼즈 저작자표시-동일조건변경허락 2.0 대한민국 라이선스(CC BY-SA 2.0 KR)에 따라 配布됩니다.
> 漢字 讀音은 Unicode Unihan database(Unicode License v3)를 사용하였습니다.
