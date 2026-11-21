# Changelog / 變更 記錄

All notable changes to gukhan are recorded here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/). Dates are CE. Nothing has been released yet (the version is `0.0.0`),
so everything merged so far is listed under *Unreleased*, grouped by area; pull request numbers are in parentheses.
아직 公開한 版이 없어 只今까지 합쳐진 모든 變更이 *Unreleased*에 領域別로 있습니다.

## [Unreleased]

### Added

#### Converter and command line / 變換器와 命令行
- Hangul → Hanja converter and the `gukhan` command: morphological analysis with Kiwi (CoNg model), longest-match
  lexicon lookup, never guessing (ambiguous words are flagged and left in Hangul), user override file with phrase
  and keep-Hangul lines (#2, #10).
- Evidence rules that narrow a flag's candidates deterministically, with `--rules` to choose them (#14); the
  `field` rule from a lexicon domain column (#45) and the `sense` rule from definition nouns (#48).
- `gukhan review`: interactive choice of the Hanja for each flagged word in context, answers appended to the
  override file at once (#15).
- Several input files with `--out-dir` or `--in-place` (a `.bak` backup by default, never an implicit overwrite) (#50).
- `--report` (TSV or Markdown) with line, column and context; `--mark` shows flagged words inline (#2).
- `--version` also reports kiwipiepy, its model type and the installed lexicon (#52).
- Optional local-model suggestions for flagged words through an OpenAI-compatible localhost backend, with a mock
  backend; suggestions are shown, never applied unless `--llm-apply` (#62, #63).
- Library example in the README, run by a test.
- Override and review guide whose commands and outputs are run by the test suite (#60).
- Markdown protection (code, links, HTML comments, script and style blocks), byte-exact I/O (line endings and BOM
  kept), and handling of decomposed Hangul and zero-width characters (#35, #39, #46, #47).
- `--jobs` / `--workers` for parallel analysis; conversion of long text in pieces (#37, #64).
- Korean and English in every user-facing message, enforced by `scripts/check_bilingual.py` (#59).
- Input formats beyond plain text and Markdown: HTML and XHTML (text nodes only), Word `.docx` (runs, headers,
  footers, footnotes, endnotes and comments; a word split over runs is converted whole and formatting is kept),
  EPUB (chapters and table of contents) and SRT/WebVTT subtitles (cue text only, timing untouched), chosen by
  extension or `--format`, with `gukhan.formats` for Python and round-trip tests that check nothing but the
  converted words changes (`docs/formats.md`).
- Output styles for Hanja learners: `--style mixed|gloss|hanja-gloss|ruby` and `gukhan.styles` (`docs/styles.md`);
  it works with every input format, and `ruby` (HTML `<ruby>`, one pair per Hanja) is refused for Word and
  subtitles.
- Output styles for Hanja learners: `--style mixed|gloss|hanja-gloss|ruby` and `gukhan.styles` (`docs/styles.md`);
  it works with every input format, and `ruby` (HTML `<ruby>`, one pair per Hanja) is refused for Word and
  subtitles.
- Browser extension: the four output styles in the popup (live, per reader) and, with an imported `char-info.tsv`
  (new builder output from Unihan, also bundled by `package_extension.py`), the reading and English meaning of each
  Hanja on the candidate card.
- Full type annotations, a `py.typed` marker, `mypy --strict` in CI, a public API defined by `__all__`
  (`docs/api-policy.md`) and an API reference; a static documentation site built from `docs/` in CI (not deployed).

#### Lexicon builder / 辭典 builder
- `gukhan-lexicon-build`: reproducible lexicon with a manifest from 標準國語大辭典 (`--stdict`), 우리말샘
  (`--opendict`), the kaikki Wiktionary dump (`--wiktextract`) and Unihan, never downloading anything (#2, #12).
- Ranking sources (韓國語基礎辭典 levels, learner word list) (#8); Korean Wikipedia names and Wikidata lexemes (#26).
- Native 標準國語大辭典 headwords become homograph candidates per part of speech, so 사랑 is no longer 舍廊 (#53, #58).
- Optional statute-gloss source and `law-overrides.txt` (#55).
- A lexicon `domain` column (#45).
- Hand-written sample lexicon for development and tests (#2).

#### Regression set and scoring / 回歸 test set
- `gukhan-regress prepare|score` and `tests/regression/sources.tsv`; 1948, 1952 and 1954 constitutions, the
  1919 documents and 님의 沈黙 (1926, batches 1–19) as regression items (#4, #6, #12, #16–#48).
- Modern-law regression set from statutory Hanja glosses, split into halves (#54, #55).
- Resumable literature collection with revision and scan checksums (#8).
- Non-blocking 1 MB throughput benchmark in CI (#60).

#### Browser extension / 확장 프로그램
- Chrome and Firefox (≥ 140) extension that converts pages locally with whole-word matching, particle and phrase
  matching, a dictionary in IndexedDB, an unobtrusive candidate card, icons and packaging script (#8, #19, #22–#24, #28).
- Optional bundled dictionary (full or without definitions) loaded on first run (#29).
- Chrome Web Store build target, privacy policy and listing draft (#32, #19).
- Per-site access granted at runtime, none at install (#66).
- Lazy conversion near the viewport with a node cap, and a notice for characters the page's font cannot draw
  (#67); font note with measured coverage.
- Reads the lexicon's domain column and native-twin candidates (#57).

#### Release and project / 公開 準備
- Apache-2.0 licence, notices and licensing policy, CI licence check (#1); data distribution assessment (#11).
- Release workflows (manual, approval-gated), release checklist, lexicon packaging (#33, #34).
- Release dry run in CI: build both packages, `twine check`, clean-venv smoke test (#65).
- CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue and pull-request templates (#51).

### Changed / 變更
- Conversion is about 18× faster on 1 MB with identical output (#64).
- Candidate ranking, strict part-of-speech matching, weights and gloss cleanup in the builder (#3, #5, #6).
- `峯` and `峰` score as the same glyph (#21).
- README accuracy figures are rescored on each lexicon change and come only from `gukhan-regress score`
  (#56, #61).

### Fixed / 修訂
- Phrase matching across spaces; duplicate lexicon entries merged (#3).
- Real 標準國語大辭典 XML dump: homonym numbers and Hangul tails in headwords (#7).
- Converted words no longer flash back to Hangul on pages that keep changing (#30, #31).
- Tabs and line breaks inside lexicon fields cannot shift TSV columns; a truncated or corrupt input exits 2
  and names the file (#42, #44).
- Reports and review contexts stay on one line with CRLF and tabs; pipes in candidates are escaped (#39).
- Windows consoles: UTF-8 output on all three command lines even under a legacy code page (#65).

### Security / 보안
- The CLI never writes through a symlink or over its own input: exclusive creates for backups and new files,
  atomic in-place writes that keep permissions, control and bidirectional characters sanitised in displayed
  context (#65).
- Extension: only the extension's own pages may change per-site access, page events must be trusted, and no host
  permission is held at install (#65, #66). See `docs/security-review.md`.
- The extension sends nothing anywhere; see `docs/privacy.md`.
