# 글꼴 / Fonts for Hanja

Mixed-script text is only as good as the font that draws it. Two things go wrong: the font
has no glyph for a character (the browser then falls back to some other font, often a
Japanese or Chinese one, or shows an empty box), or it draws the glyph in the Chinese or
Japanese form instead of the Korean one (直, 骨, 海 and many more differ in small strokes).

한국어: 漢字가 빈 칸으로 나오거나 中國·日本式 字形으로 보이면 글꼴 문제입니다.

## Recommendation

Use **Noto Serif CJK KR** (serif, for running text) or **Noto Sans CJK KR** (sans). Both are
SIL Open Font License 1.1 and available from the
[official repository](https://github.com/notofonts/noto-cjk). Install the Korean ("KR")
files, not the combined "CJK" `.ttc` file, whose default forms follow Japanese and need the
`lang` attribute to switch.

```css
body { font-family: "Noto Serif CJK KR", "Noto Serif KR", serif; }
```

```html
<html lang="ko">
```

`lang="ko"` matters: browsers use it to choose Korean glyph forms in fonts that carry
several regional forms, and to choose a Korean fallback font for any character the first font
lacks. The browser extension does not change a page's fonts and downloads none; fonts are a
choice for the reader or the site.

한국어: 本文에는 Noto Serif CJK KR, 고딕體에는 Noto Sans CJK KR을 勸합니다(둘 다 SIL OFL 1.1).
`lang="ko"`를 指定하면 韓國 字形과 韓國語 代替 글꼴이 選擇됩니다.

## What was measured (2026-11-05)

`scripts/check_font_coverage.py` counts how many of the Hanja characters that appear in the
Hanja column of the 2026-11-01 lexicon (6,054 distinct characters, 705,000 lines) have a glyph
in a font's character map. Results for the Korean subset OpenType files in the Noto CJK
repository (`Serif/SubsetOTF/KR/NotoSerifKR-Regular.otf`, `Sans/SubsetOTF/KR/NotoSansKR-Regular.otf`):

| Font file | Characters covered | Share of occurrences in the lexicon |
| --- | --- | --- |
| NotoSerifKR-Regular.otf | 6,047 of 6,054 (99.9%) | 100.00% |
| NotoSansKR-Regular.otf | 6,046 of 6,054 (99.9%) | 99.99% |

Missing from both: 鋧, 貤, 妮, 唻, 蠙, 侾 and one private-use code point, each used by one to
three lexicon entries. The sans file also lacks 隙 (243 entries), which the serif file has.
Anything missing falls back to another font, so a page can still show it, in a different style.

What this does not show: the coverage test reads only the character map. It does not check
that each glyph is the Korean form, and it says nothing about fonts that ship with an operating
system, which were not tested here. The lexicon holds the Hanja gukhan can write, not the
Hanja a given text uses: rare personal-name characters in a text may still fall outside any
font.

## Hanja the gold texts use (2026-11-21)

The same script, on the Hanja that the regression set actually uses (`--items` with its 26 items files, not
`sources.tsv` or `modern-law-laws.tsv`: 1,359 distinct ideographs, 19,694 occurrences, from the 1919 declaration
and provisional charter, three constitutions, 님의 沈黙 and the modern statutes). Fonts were read from their character maps only; the Noto files are the Korean subset OpenType
files from the `main` branch of the Noto CJK repository on that date, the others the Ubuntu packages named.

| Font | Characters covered | Share of occurrences | Missing |
| --- | --- | --- | --- |
| Noto Serif KR (NotoSerifKR-Regular.otf, sha256 5ea012e1…) | 1,358 of 1,359 | 99.99% | 兦 |
| Noto Sans KR (NotoSansKR-Regular.otf, sha256 69975a0a…) | 1,358 of 1,359 | 99.99% | 兦 |
| WenQuanYi Zen Hei 0.9.45 (fonts-wqy-zenhei) | 1,359 of 1,359 | 100.00% | none; Chinese forms (see below) |
| GNU Unifont 15.1 (fonts-unifont), BMP file | 1,359 of 1,359 | 100.00% | none; a bitmap-style face, for fallback only |
| IPAGothic (fonts-ipafont-gothic) | 1,342 of 1,359 | 99.38% | 內 稅 脫 强 說 畵 玆 吳 戶 毁 銳 產 兦 旣 閱 洑 歲 |

IPAGothic, a Japanese font, lacks the traditional forms that Korean text uses (內, 稅, 說, 戶 …): a browser that
picks it for Korean text has to borrow those from another font, which is how a page ends up with mixed
styles or boxes. "Covered" does not mean "Korean form": WenQuanYi Zen Hei covers everything here but draws
Simplified-Chinese-leaning forms of some characters. Of the fonts measured, only the Noto Korean files are
both complete here and Korean in form. Characters outside this set, such as Extension B and later (rare
personal-name characters, 𠀀 U+20000 and beyond), are in almost no ordinary font; the extension checks for them
(next section).

## When a character is missing: what the extension does

When it converts a word, the extension draws each Hanja once on a hidden canvas in the same font as the
page text. If nothing is drawn, or the picture equals what a character that no font has (U+FFFF, U+10FFFF)
looks like, the character is counted as missing. Then:

- the popup says how many Hanja the page's font cannot draw, shows up to eight, and suggests Noto Serif or
  Noto Sans CJK KR;
- the candidate card for a word with such a character carries the same note.

Words are still converted: a missing glyph is a font problem, and the reader may have another font for the
site. Limits, stated plainly: this is a check on pictures. It was tested in headless Chromium on Linux, where a
missing glyph is drawn as nothing. Chrome on Windows and macOS is expected to draw one shared box for every missing
character, which the second condition is meant to catch, but that was not tested here. Firefox draws the code
point inside the box, so the pictures differ and the check stays silent there. If the canvas cannot be read
(a browser privacy setting that blanks it) the check turns itself off instead of reporting everything missing.
It never changes a page's fonts and downloads none.

한국어: 擴張 프로그램은 페이지 글꼴로 漢字를 한 번 그려 보아 아무것도 그려지지 않거나 모든 빠진 글자에 같은
네모가 나오면 "글꼴에 없음"으로 셉니다. 팝업과 後補 카드가 이를 알리고 Noto Serif/Sans CJK KR을 勸합니다.
Firefox는 네모 안에 코드를 그려 이 檢査가 침묵합니다. 글꼴을 바꾸거나 내려받지는 않습니다.

## Other fonts

Not tested for this note; coverage depends on the font version, so run the script on the file
you have. Fonts commonly installed:

- Windows: 맑은 고딕 (Malgun Gothic), 바탕 (Batang), 돋움 (Dotum), 굴림 (Gulim).
- macOS: Apple SD Gothic Neo, AppleMyungjo.
- Open fonts: 나눔명조 (Nanum Myeongjo) and 나눔고딕 (Nanum Gothic), distributed by Naver
  (check the licence on the download page you use); Source Han Serif K / Sans K, the Adobe
  names for the same design as Noto CJK KR.

Check a font before recommending it to readers:

```
pip install fonttools
python scripts/check_font_coverage.py MyFont.ttf --lexicon build/lexicon --list-missing 30
```

## Licence

Noto CJK is SIL OFL 1.1. gukhan bundles and loads no font files, locally or remotely. If a
later release redistributes one, it must carry the font's licence text and respect its
reserved font name conditions.

한국어: 글꼴 파일은 同封하지도, 外部에서 내려받지도 않습니다.
