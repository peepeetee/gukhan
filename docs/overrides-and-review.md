# Override file and `gukhan review` / 사용자 지정 file과 檢討 도구

gukhan never guesses. A word the dictionary and the rules cannot settle (電氣 or 傳記?) stays in Hangul and is
*flagged*. You settle it once, in a plain text file, and every later run reuses the answer. This guide shows the
file, the interactive `gukhan review` that writes it for you, and a complete example you can repeat; the commands
and outputs below are run by the test suite (`tests/test_docs_examples.py`), so they stay true.

한국어: gukhan은 추측하지 않습니다. 辭典과 規則으로 가려지지 않는 낱말(電氣인가 傳記인가)은 한글로 남고 flag됩니다.
사용자가 평문 file에 한 번만 決定하면 다음부터 그대로 쓰입니다. 이 文書는 그 file, 그것을 대신 써 주는
`gukhan review`, 따라 해 볼 수 있는 全體 例를 보여 줍니다. 아래 命令과 出力은 test가 實行해 確認합니다.

## The example / 例

The files are in `docs/examples/`: a nine-line hand-written lexicon and a three-line text. Run every command from
the repository root. 例示用 辭典과 글입니다.

```
$ cat docs/examples/input.txt
전기 공학 연구소의 의사는 전기를 연구한다.
이순신의 전기는 이론이 아니다.
의사의 전기 연구.
```

`전기` is both 電氣 (electricity) and 傳記 (biography); `의사` is both 醫師 (physician) and 意思 (intention).
`--mark` shows each flagged word in place with its candidates:

```
$ gukhan docs/examples/input.txt --lexicon docs/examples/lexicon.tsv --mark
전기{傳記|電氣} 工學 研究所의 의사{意思|醫師}는 전기{傳記|電氣}를 研究한다.
이순신의 전기{傳記|電氣}는 理論이 아니다.
의사{意思|醫師}의 전기{傳記|電氣} 研究.
變換 5 · flag 6 · 檢討 1 · 維持 0
```

The last line counts words converted (變換), flagged, left for review (檢討: names and words with no entry, here
이순신) and kept in Hangul (維持). 變換 5 · flag 6 · 檢討 1 · 維持 0 / 變換 · flag · 檢討 · 維持 = converted · flagged ·
review · kept.

## The override file / 사용자 지정 file

One decision per line. `#` starts a comment; a tab may replace `=`; the file is UTF-8 (a byte-order mark is
accepted).

| Line | Meaning / 뜻 |
| --- | --- |
| `의사 = 醫師` | always this Hanja for this word / 이 낱말은 늘 이 漢字 |
| `전기 공학 = 電氣 工學` | a phrase; matched before single words / 句는 單語보다 먼저 맞춤 |
| `의사 = -` | keep this word in Hangul / 한글 維持 |
| `이순신 = 李舜臣` | add a word the lexicon lacks / 辭典에 없는 낱말 追加 |

Rules, all checked by the tool:

- The Hanja must be as long as the Hangul (spaces are ignored): `의사 = 醫` is refused with exit code 2 and a
  message naming the line. 길이가 다르면 오류입니다.
- Keys are compared without spaces, so `전기 공학` and `전기공학` are one key.
- An override beats every rule and the dictionary. It applies to the whole word wherever it appears.
- Several files can be given, `--overrides team.txt --overrides mine.txt`; a later file wins over an earlier one,
  and a later line wins over an earlier line in the same file.
- Share the file: it is plain text, so it can be committed, reviewed and merged like any other.

Writing it by hand:

```
$ cat by-hand.txt
의사 = 醫師
전기 공학 = 電氣 工學
이순신 = 李舜臣
$ gukhan docs/examples/input.txt --lexicon docs/examples/lexicon.tsv --overrides by-hand.txt --mark
電氣 工學 研究所의 醫師는 전기{傳記|電氣}를 研究한다.
李舜臣의 전기{傳記|電氣}는 理論이 아니다.
醫師의 전기{傳記|電氣} 研究.
變換 8 · flag 3 · 檢討 0 · 維持 0
```

The phrase `전기 공학` is settled and so are 의사 and 이순신; the three single 전기 stay flagged, because the text uses
the word in two senses and no whole-word answer is right for both.

## `gukhan review`

```
gukhan review input.txt --lexicon build/lexicon/ --overrides my.txt
```

It shows every flagged word, most frequent first, with up to three contexts and numbered candidates, and appends
your answer to the override file **at once**: if you quit or the terminal dies nothing is lost, and the next run
asks only about what is left. Nothing is preselected and Enter does nothing. 낱말마다 文脈과 後補를 보이고, 答을
即時 file에 덧붙입니다.

| Answer | Effect / 效果 |
| --- | --- |
| `2` | candidate 2 for this word everywhere / 後補 2番을 모든 곳에 |
| `n2` | candidate 2, only where this word is followed by the same next word (writes a phrase) / 다음 낱말까지 句로 |
| `p2` | candidate 2, only after the same previous word / 앞 낱말부터 句로 |
| `k` | keep Hangul everywhere (`word = -`) / 한글 維持 |
| `s` | skip for now / 지금은 건너뜀 |
| `u` | undo the last answer (also removes its line) / 마지막 答 取消 |
| `q` | save and quit (Ctrl-C and end of input do the same) / 저장하고 끝냄 |
| `李舜臣` | type the Hanja yourself; its length must match / 漢字를 직접 입력 |

`n` and `p` need a neighbour that is itself a word the tool handles, separated by at most one space; otherwise it
says so and asks again. Add `--include-review` to be asked also about names and words with no entry (type their
Hanja). 辭典에 없는 낱말도 물으려면 `--include-review`.

A session on the example (what you type is after `>`):

```
[1/3] 전기  ×4
  …[전기] 공학 연구소의 의사는 전기를 연구한…
  …전기 공학 연구소의 의사는 [전기]를 연구한다. 이순신의 전기는 이론이…
  … 의사는 전기를 연구한다. 이순신의 [전기]는 이론이 아니다. 의사의 전기 연구…
  1) 傳記  biography
  2) 電氣  electricity
> n2

[2/3] 의사  ×2
  …전기 공학 연구소의 [의사]는 전기를 연구한다. 이순신의 전기는…
  …. 이순신의 전기는 이론이 아니다. [의사]의 전기 연구. …
  1) 意思  intention
  2) 醫師  physician
> 2

[3/3] 이순신  ×1
  … 연구소의 의사는 전기를 연구한다. [이순신]의 전기는 이론이 아니다. 의사의 전…
  (no candidates / 後補 없음: type the Hanja)
> 李舜臣

3 件 저장 / saved → my.txt
```

The first context of 전기 is followed by 공학, so `n2` made a phrase. The file now holds:

```
$ cat my.txt
전기 공학 = 電氣 工學  # review: phrase, n
의사 = 醫師  # review: word
이순신 = 李舜臣  # review: typed
```

Run again and only the three single 전기 are left. The text means electricity once and biography once, so the
honest answer is `k`: keep them in Hangul rather than be wrong in one place.

```
$ gukhan review docs/examples/input.txt --lexicon docs/examples/lexicon.tsv --overrides my.txt
[1/1] 전기  ×3
  …전기 공학 연구소의 의사는 [전기]를 연구한다. 이순신의 전기는 이론이…
  … 의사는 전기를 연구한다. 이순신의 [전기]는 이론이 아니다. 의사의 전기 연구…
  …신의 전기는 이론이 아니다. 의사의 [전기] 연구. …
  1) 傳記  biography
  2) 電氣  electricity
> k

1 件 저장 / saved → my.txt
$ gukhan docs/examples/input.txt --lexicon docs/examples/lexicon.tsv --overrides my.txt
電氣 工學 研究所의 醫師는 전기를 研究한다.
李舜臣의 전기는 理論이 아니다.
醫師의 전기 研究.
變換 8 · flag 0 · 檢討 0 · 維持 3
```

Nothing is flagged any more and nothing was guessed. A phrase can still settle one place later: with
a line such as `전기 연구 = 電氣 研究` added below `전기 = -`, the phrase wins where the two words
stand next to each other and the other 전기 stay in Hangul:

```
醫師의 電氣 研究.
```

Phrases need adjacent words; a word whose neighbour is separated by a particle can only be settled for the whole
text. 句는 붙어 있는 낱말에만 맞고, 助詞가 끼면 낱말 全體로만 決定할 수 있습니다.

## Ready-made lists / 準備된 目錄

`gukhan-lexicon-build --law-glosses` also writes `law-overrides.txt`: words the statutes gloss the same way in at
least three statutes. It uses the same syntax and is meant for legal text only (a statute's 意思 is not every
text's), so pass it explicitly: `--overrides law-overrides.txt`. 法律 文書用 目錄이며, 일부러 지정할 때만 쓰입니다.
