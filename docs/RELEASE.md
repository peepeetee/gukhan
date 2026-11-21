# Release checklist / 配布 點檢表

## Owner steps, in order (about an hour in total)

Everything the repository can do is done or listed below; these steps need your accounts. The only cost is the Chrome Web Store's one-time
registration fee, charged by Google.

1. **GitHub settings (5 min).** Repository → Settings → Environments → *New environment*: `pypi` and `pypi-lexicon`; in
   each, tick *Required reviewers* and add yourself.
2. **PyPI (10 min).** Sign in at <https://pypi.org>, enable two-factor authentication. Account settings → *Publishing* →
   *Add a new pending publisher*, twice: project `gukhan-lexicon`, owner `peepeetee`, repository `gukhan`, workflow
   `release-lexicon.yml`, environment `pypi-lexicon`; and project `gukhan`, workflow `release-code.yml`, environment `pypi`.
   No token is created.
3. **Lexicon data release (10 min, or ask the laptop session).** On GitHub → Releases → *Draft a new release*, tag
   `lexicon-data-20261101`, tick *pre-release*, attach `lexicon.tsv`, `chars.tsv`, `manifest.json` from
   `gukhan-data\build\lexicon-20261101`, and `kaikki.org-dictionary-Korean.jsonl`. Also attach `char-info.tsv` if the build has
   one (a build made after #71 does); the workflow ignores it, the extension's bundled build uses it.
4. **Publish the lexicon.** Actions → *release-lexicon* → *Run workflow*: tag above, version `0.1.0`; when it waits,
   open it and *Approve*. Check <https://pypi.org/project/gukhan-lexicon/>.
5. **Release PR for the code.** Ask for it ("open the 0.1.0 release PR": sets `version = "0.1.0"`, dates the changelog,
   copies `docs/release-notes-0.1.0.md`). After it merges, push the tag `v0.1.0` (GitHub → Releases → new release with
   tag `v0.1.0`, target main); Actions → *release-code* waits for your approval; approve. Do step 4 first.
6. **Chrome Web Store (20 min).** <https://chrome.google.com/webstore/devconsole>: register (one-time fee, two-factor on).
   Search the store for `gukhan` and `국한 國漢` first (the name could not be searched from the cloud). *New item* →
   upload `gukhan-chrome-0.1.1.zip` (`python scripts/package_extension.py gukhan-chrome-0.1.1.zip --target chrome`).
   Paste texts, permission answers and the privacy URL from `docs/store-listings.md`; take screenshots by its steps.
   Submit for review.
7. **Firefox Add-ons (15 min).** <https://addons.mozilla.org/developers/>: sign in, *Submit a new add-on*, *On this
   site*, upload the `.xpi` from `python scripts/package_extension.py gukhan-0.1.1.xpi` (no `--target`), listed.
   Choose "no data collection", paste the texts and the reviewer notes from `docs/store-listings.md`. Every upload needs
   a new version number.
8. **Wiktionary copyright page.** Open <https://en.wiktionary.org/wiki/Wiktionary:Copyrights> in a browser, save as PDF
   into the project folder, and tell the laptop session so the notice can cite it.
9. **Last look.** In a normal browser profile, try the extension by hand on three real pages (a news article, a law page,
   a blog) before pressing *Submit*; the smoke tests cannot judge how a page looks.

State as of 2026-11-21. Nothing has been published, tagged or uploaded. Items marked **you** below need
the project owner (accounts, tokens, decisions); the rest is done in the repository.

## 1. Names

| Where | Status |
| --- | --- |
| PyPI `gukhan` | free (HTTP 404 on 2026-11-21; also 2026-11-05 and 2026-10-28) |
| PyPI `gukhan-lexicon` | free (HTTP 404 on 2026-11-21; also 2026-11-05) |
| Chrome Web Store, store listing name | not checked here (the extension work covers it) |
| Trademark | not cleared. GitHub has other repos named `gukhan`; `dahlia/gukhanmun` is a distinct reverse-direction project |

A free PyPI name is only reserved by uploading. PyPI treats `gukhan-lexicon` and `gukhan_lexicon`
as the same name.

## 2. Before tagging (blockers and decisions)

1. **Over-conversion of native words: ship as a known problem** (owner, 2026-11-05; reduced since). On 님의 沈黙 the tool
   wrote Hanja where the author wrote Hangul 126 times in 585 words on 2026-11-05, among them 사랑 → 舍廊. Since native
   headwords are kept per part of speech (#58) it is `over` 84 in 943 words (2026-11-21), 사랑 is no longer converted, and the
   README table is the only source of figures. `docs/release-notes-0.1.0.md` repeats the problem and links the table.
2. **en.wiktionary copyright page (open).** The Wiktionary row rests on the Wikimedia Terms of Use
   and the Korean Wiktionary page. The English page is blocked from both the cloud container and
   the laptop shell (HTTP 403 from the proxy) and the browser extension is not connected. Someone
   with a browser opens <https://en.wiktionary.org/wiki/Wiktionary:Copyrights>, saves it as PDF
   and drops it in the project folder; then the notice row can cite the page itself.
3. **Regression excerpts provenance.** STATUS.md still lists the original-edition check for
   李光洙, 玄鎭健 and 蔡萬植 as pending. These are test excerpts, not shipped data; the release notes
   draft says they are not verified gold.
4. **Start-up time.** Re-measured on 2026-11-21 in the cloud container with a real 708,455-entry lexicon (built from the
   NIKL dumps alone): `gukhan t.md` takes about 6.8 s, of which the lexicon load is 3.8-4.2 s (it was 4.8-5.2 s before
   the parse fast path). The 23 s measured on 2026-11-05 included other work and is not repeatable. Not measured on the
   laptop. A binary cache of the parsed lexicon remains an option after release; it does not block 0.1.0.
5. **Version number.** `pyproject.toml` still says `0.0.0` on purpose: it is set to `0.1.0` in the release PR (owner
   step 5), after the lexicon is on PyPI. The extension is at 0.1.1 on its own track.
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

- Chrome Web Store and Firefox Add-ons: the listing texts (Korean and English), permission answers, reviewer notes and
  screenshot steps are in `docs/store-listings.md`; the owner does the accounts, fee, screenshots and upload (owner steps
  6 and 7). The privacy policy `docs/privacy.md` is served by GitHub's rendered page.
- The extension builds are 0.1.1 for both stores; a new version number is needed for every upload.
