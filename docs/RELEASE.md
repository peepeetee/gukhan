# Release checklist / 配布 點檢表

State as of 2026-11-05. Nothing has been published, tagged or uploaded. Items marked **you** need
the project owner (accounts, tokens, decisions); the rest is done in the repository.

## 1. Names

| Where | Status |
| --- | --- |
| PyPI `gukhan` | free (HTTP 404 on 2026-11-05; also 404 on 2026-10-28) |
| PyPI `gukhan-lexicon` | free (HTTP 404 on 2026-11-05) |
| Chrome Web Store, store listing name | not checked here (the extension work covers it) |
| Trademark | not cleared. GitHub has other repos named `gukhan`; `dahlia/gukhanmun` is a distinct reverse-direction project |

A free PyPI name is only reserved by uploading. PyPI treats `gukhan-lexicon` and `gukhan_lexicon`
as the same name.

## 2. Before tagging (blockers and decisions)

1. **Over-conversion of native words (decision: you).** On 님의 沈黙 the tool wrote Hanja where the
   author wrote Hangul 126 times in 585 words, among them 사랑 ("love") → 舍廊 ("men's quarters")
   at least 30 times (README, regression set). Either fix it before release (an evidence rule or a
   default override for a short list of common native words) or ship with it stated as a known
   problem. The README already states it.
2. **en.wiktionary copyright page (you).** The Wiktionary row rests on the Wikimedia Terms of Use
   and the Korean Wiktionary page; the English page did not load from the cloud (HTTP 403 from the
   proxy). Open <https://en.wiktionary.org/wiki/Wiktionary:Copyrights> in a browser and save a
   capture to the project folder so the licence can be read from the page itself (as was done for
   우리말샘).
3. **Regression excerpts provenance.** STATUS.md still lists the original-edition check for
   李光洙, 玄鎭健 and 蔡萬植 as pending. These are test excerpts, not shipped data, but the
   release notes should not claim them as verified gold.
4. **Start-up time.** Loading the 704,912-entry lexicon took about 23 s for `gukhan t.md` in the
   cloud container (including Kiwi). Not measured on the laptop. If it feels slow for first users,
   consider a binary cache of the parsed lexicon after release; it does not block 0.1.0.
5. **Version number.** `pyproject.toml` still says `0.0.0`. Set `0.1.0` in the release PR; the
   extension is at 0.1.1 on its own track.
6. **gukhan-lexicon repository (you).** `docs/data-distribution.md` plans a separate repository
   for the lexicon, with the pinned kaikki JSONL as a release asset. It does not exist yet.
   Creating it, and uploading the 208 MB JSONL, needs your GitHub account.

## 3. Licence checks (done 2026-11-05)

- `NOTICE`: said the lexicon is CC BY-SA 2.0 KR; now states CC BY-SA 4.0 (the build includes
  Wiktionary) and names every source.
- `THIRD-PARTY-NOTICES.md`: added the runtime dependencies that kiwipiepy installs (numpy, tqdm
  with MPL-2.0 and MIT) which were missing; marked the Korean Wikipedia and Wikidata rows as not
  in the released lexicon (the 2026-11-01 manifest lists neither).
- The `gukhan` wheel contains code and the 7.7 KB hand-written sample lexicon only (no dictionary
  data, checked by listing the wheel).
- The `gukhan-lexicon` wheel contains `lexicon.tsv`, `chars.tsv`, `manifest.json`, `NOTICE.txt`,
  `THIRD-PARTY-NOTICES.md` and `UNICODE-LICENSE.txt` (the Unicode License v3 text with the notice
  from the Unihan files). `scripts/package_lexicon.py` refuses anything else: raw dumps (`.xml`,
  `.zip`, `.jsonl`), a licence other than CC BY-SA, markup in a row, a definition excerpt over 200
  characters (the real lexicon's longest is 80), a Wiktionary build not marked CC BY-SA 4.0. It
  ran clean on the 2026-11-01 build; tests cover each refusal.
- Local paths (`C:\claude_workspace\...`) in the build manifest are cut to file names when
  staging, so they do not reach PyPI. The notice text in the manifest names 標準國語大辭典,
  우리말샘, Wiktionary, 韓國語基礎辭典, the learner list and Unihan.
- Not yet checked: how PyPI's licence classifier shows `CC-BY-SA-4.0 AND Apache-2.0` (a valid SPDX
  expression; `twine check` passes).

## 4. Build and publish (you, in this order)

Lexicon (package size on the 2026-11-01 build: 37.7 MB wheel, under PyPI's 100 MB file limit):

```
gukhan-lexicon-build --stdict <stdict dir> --opendict <opendict dir> \
    --wiktextract kaikki.org-dictionary-Korean.jsonl --unihan Unihan.zip \
    --krdict <krdict dir> --learner-list learner.txt -o build/lexicon
python scripts/package_lexicon.py build/lexicon --check-only
python scripts/package_lexicon.py build/lexicon --version 0.1.0 -o build/gukhan-lexicon-0.1.0
cd build/gukhan-lexicon-0.1.0 && python -m build && twine check dist/*
```

Code (after the version bump merges):

```
python -m build && twine check dist/*
```

Upload to TestPyPI first, install both from there in a clean virtual environment, run
`gukhan sample.md` and look at the result. Then upload to PyPI, `gukhan-lexicon` first, because
`gukhan[lexicon]` depends on it. Prefer PyPI trusted publishing from a GitHub workflow over an
API token on a laptop. Then tag `v0.1.0` and create the GitHub release; the release notes should
quote the README accuracy table and the known problems.

An end-to-end check was run on 2026-11-05 in the cloud container with the real lexicon: both
wheels installed from files into a clean virtual environment and `gukhan` used the installed
lexicon by default.

## 5. Stores

- Chrome Web Store: needs a developer account (one-time fee, charged by Google), the privacy
  policy `docs/privacy.md` hosted at a public URL (GitHub's rendered page works), and screenshots.
  The extension is in a separate thread.
- Firefox Add-ons: builds exist (0.1.1); a new version number is needed for every upload.
