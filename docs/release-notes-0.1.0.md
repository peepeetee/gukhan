# gukhan 0.1.0 — release notes (draft) / 0.1.0 版 公開 노트 (草案)

Draft prepared 2026-11-21; the owner reads it before the release PR copies it. Figures are not repeated here:
the README's regression table is the only source, and the release PR checks it against the lexicon in the release.
草案이며 수치는 README 표만을 出處로 합니다.

## What it is / 이것은

gukhan 國漢混用 turns Hangul text into mixed Hangul-Hanja script: a command line tool and Python library
(Apache-2.0), a separate dictionary package `gukhan-lexicon` (CC BY-SA 4.0, built from 標準國語大辭典, 우리말샘,
Wiktionary, 韓國語基礎辭典 and Unihan), and a browser extension for Chrome and Firefox.
한글 글을 國漢混用으로 바꾸는 命令行 道具·라이브러리, 別途 사전 패키지, 브라우저 확장입니다.

Install: `pip install gukhan[lexicon]`; then `gukhan file.md`. The extension is listed separately in each store.

## What is in 0.1.0 / 들어 있는 것

- Morphology by Kiwi; whole-word, phrase and domain-aware lookup; ambiguous words are **flagged and left in Hangul,
  never guessed**; override file (`전기 = 電氣`, `의사 = -`), `gukhan review`.
- Input formats: Markdown and plain text, HTML, .docx, EPUB, SRT and VTT; typed library API with a stability policy.
- Output styles for Hanja learners: `mixed`, `gloss` 한글(漢字), `hanja-gloss` 漢字(한글), `ruby`; in the extension
  too, with each Hanja's 音 and meaning (the Korean 訓 where Wiktionary has one, else the English meaning) on the candidate card.
- Extension: per-site permission, all local, no network, no remote code (`docs/privacy.md`).

## Known problems, stated plainly / 알려진 문제

- **It converts about half of the words in historical texts and flags the rest.** That is the intended trade; see the
  README's table for the current rates of right, wrong, flagged and over-converted words.
- **Over-conversion of native words**: Hanja can be written where an author wrote Hangul (별→別, 거→炬). 사랑 → 舍廊 was
  fixed by keeping native headwords per part of speech; others remain. A line like `별 = -` keeps a word in Hangul.
- **Pre-1970 and modern texts are harder**: Kiwi was not trained on the older register; the modern check covers statutes only.
- **The browser extension has no morphological analysis**, so it is less accurate than the command line.
- **Korean 訓 only for some Hanja**: the NIKL dumps and Unihan carry none; the card takes it from Wiktionary's `ko-hanja` entries (about 3,000 characters) and shows the English meaning for the rest (`docs/styles.md`).
- **Regression excerpts are test data, not verified gold**: original-edition checks for 李光洙, 玄鎭健 and 蔡萬植 are pending.
- Start-up loads the whole dictionary (about 23 s in the cloud container, including Kiwi); a cache may follow.
- One person builds this and the names are not trademark-cleared.

## Licences and credits / 라이선스

Code Apache-2.0. The dictionary package is CC BY-SA 4.0 because it includes Wiktionary data; credits are in its
`NOTICE.txt` and `THIRD-PARTY-NOTICES.md`. Unihan is under the Unicode License v3. No UTagger data or code was used.
