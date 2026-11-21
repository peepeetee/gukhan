# Variant glyphs / 異體字

A print from 1924 may write 絕對 and 痛歎 where the dictionary (標準國語大辭典) has 絶對 and 痛嘆. These are the same
words in another glyph form or another standard form. Without a table, scoring counts the converter's 絶對 as wrong
against a gold text with 絕對, and `gukhan-regress prepare` does not find the word 絶對 in a run written 絕對.
1924年 印刷物은 絕對·痛歎으로 쓰는데 사전은 絶對·痛嘆이라, 表가 없으면 올바른 변환도 틀린 것으로 셉니다.

## The table / 表

`gukhan-lexicon-build --unihan Unihan.zip` writes `variants.tsv` next to `chars.tsv` when the archive (or directory)
holds `Unihan_Variants.txt`. Lines are `hanja<TAB>variant<TAB>kind`, each unordered pair once:

| kind | Unihan field | meaning | example |
| --- | --- | --- | --- |
| `z` | `kZVariant` | glyph forms of one character | 絕 絶 |
| `semantic` | `kSemanticVariant` | interchangeable in some uses; looser | 歎 嘆 |

Unihan is under the Unicode licence already in `THIRD-PARTY-NOTICES.md`. The file is for the regression tools and is not
shipped in the `gukhan-lexicon` package; it does not change the lexicon or the converter's output.
Unihan 라이선스는 이미 告知에 있습니다. 이 file은 回歸 道具用이며 辭典 package에는 넣지 않습니다.

## Scoring / 採點

```
gukhan-regress score tests/regression/your-set.tsv --lexicon build/lexicon --variants build/lexicon/variants.tsv
```

A word that differs from the gold only by variants is *right*, and a candidate offered in a variant form counts as
offered. Characters of a group are compared by one canonical character (the smallest code point of a connected group), so
a chain A~B~C is one group. The semantic list is looser and can hide a real mistake (it joins characters that differ in
some senses), so `--variant-kinds z` uses glyph forms only; the default is both. The built-in fold of a few dozen
common forms (强/強, 眞/真 …) always applies. The JSON output names the table used under `variants`.

## Matching input that already has Hanja / 漢字가 든 입력

`gukhan-regress prepare --variants variants.tsv --lexicon …` segments a run of Hanja by longest word of the lexicon,
and compares in folded form: 絕對 finds the entry 絶對 and is read 절대, with the initial-sound rule from the word. A
character with no reading of its own takes the reading of a variant (絕 from 絶). The gold text itself is not changed.
The converter (`gukhan`) leaves Hanja in its input as it is and has no such option.
