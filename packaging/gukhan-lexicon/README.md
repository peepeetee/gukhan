# gukhan-lexicon

The prebuilt Sino-Korean lexicon that [gukhan](https://github.com/peepeetee/gukhan) (國漢混用)
uses to turn Hangul into mixed script. `pip install gukhan-lexicon` makes `gukhan` use it
automatically; `gukhan_lexicon.data_dir()` returns the folder for `gukhan --lexicon`.

**Licence of the data: CC BY-SA 4.0** (the build includes Wiktionary). It also contains material
from 國立國語院 《標準國語大辭典》 and 《우리말샘》 (CC BY-SA 2.0 KR, adaptations may be released
under a later version) and Unicode Unihan readings (Unicode License v3). The exact attribution
text is in `NOTICE.txt` and in `data/manifest.json` (`notice`); keep it with any copy. If you
edit the data, publish your edits under the same licence. The Python module that locates the
files is Apache-2.0.

한국어: 이 辭典 資料는 CC BY-SA 4.0으로 配布됩니다. `NOTICE.txt`의 出處 表示를 함께 保存하세요.

The package holds only the built lexicon (headword, Hanja form, part of speech, a definition
excerpt of at most 80 characters, ranking columns), not the source dictionaries, their usage
examples or any media.
