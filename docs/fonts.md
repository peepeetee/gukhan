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
