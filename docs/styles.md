# Output styles for learners / 學習者를 위한 出力 形式

By default gukhan writes the Hanja in place of the Hangul (`mixed`). For readers who are learning Hanja, `--style`
keeps the Hangul beside it. Only the way a converted word is written changes; which words are converted, flagged
or kept in Hangul is the same, and flagged words are never glossed (nothing was decided for them).
`--style`은 變換되는 낱말을 적는 方式만 바꿉니다. 어느 낱말을 바꾸는지는 같고, flag된 낱말은 그대로 둡니다.

| `--style` | Example | Notes |
| --- | --- | --- |
| `mixed` (default) | 國軍은 作戰 計劃 | Hanja replace Hangul |
| `gloss` | 국군(國軍)은 작전 계획(作戰 計劃) | 한글(漢字): Hangul, then the Hanja in parentheses |
| `hanja-gloss` | 國軍(국군)은 作戰 計劃(작전 계획) | 漢字(한글): Hanja, then the Hangul reading in parentheses |
| `ruby` | `<ruby>國<rp>(</rp><rt>국</rt><rp>)</rp></ruby>…` | HTML `<ruby>`: the reading above each Hanja |

```
gukhan essay.md --style gloss -o essay.gloss.md
gukhan page.html --style ruby -o page.ruby.html
gukhan book.epub --style hanja-gloss -o book.learn.epub
```

## Details / 細部

- A phrase (`작전 계획`) is glossed as a whole: `작전 계획(作戰 計劃)`.
- `ruby` writes one `<ruby>` pair per Hanja, so a word split over `<b>…</b>` or over several Word runs stays valid
  HTML. A character with no Hanja stays plain. `<rp>(</rp>` is there for browsers without ruby support.
  漢字마다 `<ruby>` 한 쌍이므로 글자 사이에 標識가 있어도 올바른 HTML입니다.
- `ruby` needs HTML output. It works with HTML, EPUB (the contents list `.ncx` is plain text, so it gets
  `hanja-gloss`), Markdown and plain text (the tags are written into the text as they are). It is refused for Word
  and subtitle files; use `gloss` or `hanja-gloss` there.
- In HTML and Word the gloss goes after the word's last character, inside whatever formatting that character has.
- Running a style twice does not gloss twice: a word already followed by its own `(漢字)`, or already preceded by
  `漢字(` or `<rt>`, is left alone. Still, convert from the original file, not from a glossed copy.
- `--mark` still shows flagged words as `전기{電氣|傳記}`, and `--llm-apply` writes the model's choice in the same
  style.

From Python / 라이브러리:

```python
from gukhan import Converter
from gukhan.styles import render

Converter(style="gloss").convert("국군은 작전 계획을 수립하였다.").text
# '국군(國軍)은 작전 계획(作戰 計劃)을 수립(樹立)하였다.'
render("국군", "國軍", "ruby")  # one word, written in a style
```

## Browser extension / 확장 프로그램

The extension has the same four styles in its popup (*Output style*), applied live to every enabled site. In
`ruby` the reading is a `<ruby>` pair per Hanja, and the word is still the underlined button with the candidate card.
Besides the styles, the card can show each Hanja's reading and English meaning (`電 전 · electricity`) when
`char-info.tsv` is imported. See `extension/README.md`. 확장 프로그램의 팝업에도 같은 네 가지 形式이 있습니다.

Unihan has no Korean 訓 (meaning-reading like 나라 국), so the character list gives the reading (音) and the English
meaning from Unihan. When the dictionary is built with `--wiktextract`, `char-info.tsv` gets a fourth column with the
訓 from Wiktionary's `ko-hanja` entries (물 for 水, 3,000 characters in the 2026-10-01 extract; contributors of
CC BY-SA 4.0, already credited in the build's notice), and the extension card shows `水 물 수` instead of the English
meaning for those characters. Unihan에는 한국어 訓이 없어 Wiktionary의 `ko-hanja` 項目에서 訓을 읽습니다.

### Korean 訓 sources checked (2026-11-21) / 訓 出處 調査

The NIKL dumps (標準國語大辭典, 우리말샘, 韓國語基礎辭典; CC BY-SA 2.0 KR) carry **no 訓音 field**. 標準國語大辭典 has
24 and 우리말샘 about 4,400 single-syllable headwords with a single Hanja, but these are word senses (e.g. 귤 橘 "귤나무의 열매"),
not 訓 (귤 귤). Turning definitions into 訓 would be a guess, so it is not done. Unihan `kHangul` gives 音 only.
標準國語大辭典·우리말샘·韓國語基礎辭典에는 訓音 欄이 없고, 漢字 한 글자 標題語는 낱말 뜻풀이일 뿐 訓이 아닙니다.

Not usable yet: the en.wiktionary Hanja entries (`ko-hanja` template carries 訓 and 音; CC BY-SA 4.0, same licence as the
Wiktionary-including build) are the one candidate with a clear licence, but the kaikki.org extract is not reachable from the
cloud build environment, so its shape could not be checked there. A builder input for it is a follow-up once someone has
inspected a real extract. 國漢混用은 확인하지 못한 資料를 추측으로 넣지 않습니다.

