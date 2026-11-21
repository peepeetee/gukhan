# Contributing / 基與 方法

Thank you for helping. gukhan converts Hangul text to 國漢混用 (Korean mixed script). 기여를 환영합니다.

## Ground rules / 基本 原則

- **Never guess.** An ambiguous word is flagged and left in Hangul; a choice is made by a rule
  that cites evidence (docs/PLAN.md §5a), by the user's override file, or by a person. A change
  that makes the tool write Hanja it cannot justify will not be merged, even if it raises a score.
- **Clean-room.** Do not use, copy, run against, or compare with UTagger (code, binaries,
  dictionaries or output). Say so in the PR if you are unsure about a source.
- **Licences.** Code is Apache-2.0 and every Python/JavaScript file starts with
  `# SPDX-License-Identifier: Apache-2.0` (or `//`). Dependencies must be permissive or LGPL;
  CI fails on GPL/AGPL. New data sources need their licence checked on the source's own page and
  recorded in `THIRD-PARTY-NOTICES.md`. Raw dictionary dumps are never committed.
- **Privacy.** The extension processes text locally and sends nothing anywhere. A change that
  adds a network request, analytics or remote code will not be accepted.
- **Dates and language.** Docs and error messages are in English and Korean (Korean in mixed
  script where natural); Chinese in 正體中文. Dates in the repository are Korean or CE only.

## Setup / 準備

```
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest -q                                 # about 30 s; tests marked kiwi need kiwipiepy
python -m mypy                                      # strict type check of src/gukhan (CI runs it)
pip install -e ".[docs]" && mkdocs build --strict  # static docs site into build/site (CI builds it, never deploys)
node --test extension/engine.test.mjs               # extension engine (Node 22)
node extension/browser-smoke.cjs                    # optional: needs Playwright + Chromium
python scripts/check_licences.py                    # what CI runs for licences
python scripts/check_bilingual.py                   # every message needs Korean and English
python scripts/benchmark.py                         # throughput on 1 MB (CI runs it, non-blocking)
python scripts/release_dryrun.py                     # build both packages, twine check, clean-venv smoke test (needs build, twine)
```

한국어: 모든 사용자 向 글에는 韓國語(國漢混用)와 英語가 함께 있어야 하며 `check_bilingual.py`가 이를 確認합니다.
`benchmark.py`는 1 MB 글의 處理 速度를 재며, CI에서는 結果가 나빠도 merge를 막지 않습니다.

## Pull requests / 變更 提案

- Small and focused, with a test that fails without the change.
- Run the checks above first. CI runs lint, the tests on Linux and Windows (Python 3.10 and 3.13),
  the licence check and the browser smoke test.
- Describe what changed and how you checked it. Accuracy claims come only from
  `gukhan-regress score` on the regression set, never from impressions.

## Regression set / 回歸 test set

Sources, the copyright rules for them and the item format are in `tests/regression/README.md`.
Only texts that may be reproduced go in: statutes and official notices, literature by authors who
died before 1962, anonymous ephemera before 1956. Cite the edition and page for every item.
Reading a modern reprint is not enough for historical gold text.

## Reporting a wrong conversion / 誤變換 報告

Open an issue with the *Wrong conversion* form: the sentence, what gukhan wrote, what it should
be, and the source. Please do not paste text you may not share.
