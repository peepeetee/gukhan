# Performance / 處理 速度

Measured with `scripts/benchmark.py` (a deterministic 1 MB Korean text, a lexicon padded to 200k entries),
on a 4-core container, Python 3.13, kiwipiepy 0.24.1 (`cong` model). The figures are for trend-watching;
CI runs the same script, non-blocking. 1 MB 글을 4코어 container에서 잰 값이며, 傾向을 보기 위한 것입니다.

| 1 MB text | Seconds | MB/s | Output |
| --- | --- | --- | --- |
| Before (2026-11-21, PR #60) | 50.4 | 0.020 | reference |
| After, 1 Kiwi thread | 7.1 | 0.141 | identical |
| After, 4 Kiwi threads (default) | 2.7–2.8 | 0.36–0.37 | identical |

Four 1 MB files, `gukhan a b c d --out-dir out`: 14.9 s in one process (4 Kiwi threads), 10.8 s with
`--jobs 4` (four processes, one Kiwi thread each). Small batches gain nothing from `--jobs`: each process
loads the lexicon and the model first (about 5 s and 2.5 s with a real lexicon). 작은 묶음에는 `--jobs`가 도움이 안 됩니다.

## What was slow, and what changed / 무엇이 느렸고 무엇을 바꿨나

1. **The evidence pass ran Kiwi on the whole text in one call.** The `field` rule needs a first pass to count
   the words of each dictionary field, and that pass called Kiwi once on a whole segment, while the real pass
   cut the text into pieces of about 2000 characters because Kiwi's time grows faster than linearly with
   the length of one call. At 1 MB the evidence pass alone took 35 of the 50 seconds. It now uses the same
   pieces, and the analysis of a piece is kept (up to 3 million characters) so the real pass finds it ready.
2. **Pieces are analysed in batches on several threads.** Kiwi's own multi-text call (`tokenize(list)`)
   analyses each text on its own, so the tokens are exactly those of one call per text; the batch only runs
   them on `--workers` threads (default: the cores, at most 4).
3. **Two small things in Python.** The analyser builds tokens with their position instead of copying every
   token afterwards; `Token` uses `__slots__`.
4. **`--jobs N` for several files**: worker processes (`spawn`, never fork, because Kiwi has threads), each with
   its own Converter. Output order and bytes are the same as one process.

## Output is unchanged / 出力은 그대로

- A test lexicon was built from every gold pair of every regression set (2,501 pairs, a fifth of them labelled
  with a dictionary field so the `field` rule is exercised). For each regression file the items were
  converted as the scorer does, and the file was converted again as one long document; with a 300 KB
  benchmark text that is 55 results, each compared in text, decision offsets, kinds, Hanja, reasons and
  candidate counts. All 55 are equal before and after.
- The full 1 MB benchmark text: the converted text and the decisions have the same SHA-256 before and after.
- Tests: batching analyses each distinct piece once; 1 and 4 Kiwi threads give equal results; `--jobs 2`
  gives byte-identical files and summary lines in input order.
- The one change of procedure is the evidence pass: it now analyses pieces instead of the whole segment.
  Kiwi's tokens for a whole text and for its pieces can differ (they did, in a probe on 300 KB), so in theory a
  field count could move by a word; in every comparison above it did not.

## Tried and left alone / 試했으나 바꾸지 않은 것

- **Lexicon load** (4.6 s for 700k entries) is spread over parsing, 700k `Entry` objects and the index; a fast path
  that skips per-field stripping gained nothing and was dropped. A cache file would help, at the price of a
  second file format to keep valid; not done.
- **Caching repeated sentences.** The cache is by exact piece, which is what the two passes need. Sentence-level
  caching would change what Kiwi sees around a sentence, and real books rarely repeat sentences.
- **Kiwi options** that change the analysis (`model_type`, typo handling, dialects) are not speed settings here.
  `num_workers` is the only one used, because it cannot change the result.
