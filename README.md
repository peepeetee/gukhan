# gukhan · 國漢混用

Hangul → Hanja mixed-script converter. 한글 文章을 國漢文混用體로 바꿔 주는 道具입니다.
將韓文諺文轉為國漢混用文的工具。

Status: pre-alpha. Nothing works yet; this commit sets up the licence and
project policy. Accuracy numbers will come only from the public regression set
(milestone 4), never from marketing.

## How it works (planned)

text → morphological analysis → lemma lookup in a Sino-Korean lexicon →
choose Hanja (user override list, then rule, then flag) → re-attach Hangul
endings. Unresolved homographs are flagged, never guessed. Runs on a laptop CPU
with no neural model. The Chrome extension processes text locally and sends
nothing anywhere.

## Licence

- Code: [Apache-2.0](LICENSE). Keep the [NOTICE](NOTICE) file with any copy.
- Lexicon data: distributed separately as `gukhan-lexicon` under
  CC BY-SA 2.0 KR, built from 國立國語院 《標準國語大辭典》 and the Unicode
  Unihan database.

See [docs/licensing.md](docs/licensing.md) for the reasoning and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for every source.
