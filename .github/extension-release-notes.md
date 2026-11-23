Browser extension builds of gukhan 國漢混用 (Korean Hangul → mixed Hangul-Hanja), code only.

**Files**
- `gukhan-chrome-<version>.zip`: Chrome / Chromium (Manifest V3). Unzip and load unpacked at `chrome://extensions` (Developer mode), or use it as the Chrome Web Store upload.
- `gukhan-firefox-<version>.xpi`: Firefox 140 or newer. Unsigned: install temporarily from `about:debugging`, or from a Firefox Developer / Nightly build with `xpinstall.signatures.required` off.
- `SHA256SUMS.txt`: checksums.

**Dictionary.** These builds contain no dictionary. On first use, import `lexicon.tsv` and `manifest.json` (from the `gukhan-lexicon` package or its data release) on the Settings page. The dictionary is a separate work under CC BY-SA; the extension code is Apache-2.0.

**Privacy.** Everything runs inside your browser; nothing is sent anywhere (see `docs/privacy.md`). Host access is requested per site.

**Known limits.** Matching is exact whole-word matching without morphological analysis, so it converts fewer words than the command-line tool. See `extension/README.md` and the accuracy table in the README.
