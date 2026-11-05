# Release checklist / 配布 點檢表

State as of 2026-11-05 (updated after the owner's answers). Nothing has been published, tagged or uploaded. Items marked **you** need
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

1. **Over-conversion of native words: decided, ship as a known problem** (owner, 2026-11-05).
   On 님의 沈黙 the tool wrote Hanja where the author wrote Hangul 126 times in 585 words, among
   them 사랑 ("love") → 舍廊 ("men's quarters") at least 30 times. The README states it; repeat it
   in the release notes.
2. **en.wiktionary copyright page (open).** The Wiktionary row rests on the Wikimedia Terms of Use
   and the Korean Wiktionary page. The English page is blocked from both the cloud container and
   the laptop shell (HTTP 403 from the proxy) and the browser extension is not connected. Someone
   with a browser opens <https://en.wiktionary.org/wiki/Wiktionary:Copyrights>, saves it as PDF
   and drops it in the project folder; then the notice row can cite the page itself.
3. **Regression excerpts provenance.** STATUS.md still lists the original-edition check for
   李光洙, 玄鎭健 and 蔡萬植 as pending. These are test excerpts, not shipped data, but the
   release notes should not claim them as verified gold.
4. **Start-up time.** Loading the 704,912-entry lexicon took about 23 s for `gukhan t.md` in the
   cloud container (including Kiwi). Not measured on the laptop. If it feels slow for first users,
   consider a binary cache of the parsed lexicon after release; it does not block 0.1.0.
5. **Version number.** `pyproject.toml` still says `0.0.0`. Set `0.1.0` in the release PR; the
   extension is at 0.1.1 on its own track.
6. **Where the lexicon ships: this repository, as a second package.** `packaging/gukhan-lexicon/`
   is the template; the data is never committed, only attached to a GitHub release of this
   repository (the 118 MB `lexicon.tsv` is far below the 2 GiB asset limit) and turned into the
   PyPI package by `.github/workflows/release-lexicon.yml`. The pinned kaikki JSONL goes on the
   same release page.

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

## 4. Build and publish

Workflows are in the repository; they only run when you start them, and each publish job waits
for your approval. Steps only the account owner can do are marked **you**.

One-time setup (**you**, about ten minutes, in a browser):

1. Create a PyPI account if there is none, and enable two-factor authentication.
2. On PyPI, add two *pending publishers* (Account settings → Publishing): project `gukhan-lexicon`,
   workflow `release-lexicon.yml`, environment `pypi-lexicon`; and project `gukhan`, workflow
   `release-code.yml`, environment `pypi`. Owner `peepeetee`, repository `gukhan`. No token is
   created or stored anywhere.
3. On GitHub, Settings → Environments: create `pypi` and `pypi-lexicon`, each with yourself as
   required reviewer.

Lexicon (package size on the 2026-11-01 build: 37.7 MB wheel, under PyPI's 100 MB file limit):

1. **you** (or a laptop session, if `gh` is signed in there): create a GitHub release named
   `lexicon-data-20261101` and attach `lexicon.tsv`, `chars.tsv`, `manifest.json` from
   `gukhan-data\build\lexicon-20261101`, plus `kaikki.org-dictionary-Korean.jsonl` (the pinned
   Wiktionary input). Mark it a pre-release so it does not become the "latest" release.
2. Run the `release-lexicon` workflow (Actions tab) with that tag and version `0.1.0`; approve
   the publish step.

Code: open a release PR that sets `version = "0.1.0"` in `pyproject.toml`; after it merges,
push the tag `v0.1.0`; `release-code` builds it and waits for your approval. Publish the
lexicon first, because `gukhan[lexicon]` depends on it. Before the real uploads, a dry run
locally is the same as the workflow: `python scripts/package_lexicon.py build/lexicon --version
0.1.0 -o build/gukhan-lexicon && cd build/gukhan-lexicon && python -m build && twine check dist/*`.

An end-to-end check was run on 2026-11-05 in the cloud container with the real lexicon: both
wheels installed from files into a clean virtual environment and `gukhan` used the installed
lexicon by default. TestPyPI was not used; it needs its own account and publisher setup.

## 5. Stores

- Chrome Web Store: needs a developer account (one-time fee, charged by Google), the privacy
  policy `docs/privacy.md` hosted at a public URL (GitHub's rendered page works), and screenshots.
  The extension is in a separate thread.
- Firefox Add-ons: builds exist (0.1.1); a new version number is needed for every upload.
