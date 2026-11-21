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

The browser extension has the same four styles in its popup; see `extension/README.md`.
