# Chrome Web Store listing / 크롬 웹 스토어 등록 자료

Draft prepared 2026-11-05. **Not submitted.** The person submits it (developer account, one-time
registration fee and the upload are theirs).

## Name check (2026-11-05)

- PyPI: `gukhan` and `gukhan-lexicon` both returned 404 (free) from the cloud container.
- npm: `gukhan` returned 404 (free).
- Chrome Web Store: could not be searched from the cloud container (connection refused). **To do by
  hand:** open <https://chromewebstore.google.com/search/gukhan> and `국한 國漢`, and look for
  similar names. Related prior art found earlier: `dahlia/gukhanmun` (Rust, GPL-3.0, Hanja→Hangul);
  a different tool and direction, but a similar name, so keep the listing name distinctive.
- Proposed listing name (45-character limit): **gukhan 國漢混用 — Korean mixed-script reader**
  (the manifest `name` stays `gukhan 國漢混用`).

## Package

`python scripts/package_extension.py gukhan-chrome-0.1.1.zip --target chrome`

The Chrome manifest drops the Firefox-only keys; it declares no host access at install (hosts are `optional_host_permissions`, asked for one site at a time); the full smoke test passes
against the unpacked store build (`GUKHAN_EXT=<dir> node extension/browser-smoke.cjs`). For a
build with a bundled dictionary add `--dictionary <lexicon dir> --no-definitions` (CC BY-SA
notice is written beside it). The code-only build asks the reader to import a dictionary first.

## Listing text

Moved to `docs/store-listings.md` (Chrome and Firefox, Korean and English, with the privacy tab answers and screenshot steps).

## Assets still needed from the person

Screenshots and the optional promo tile: steps in `docs/store-listings.md`. 128 px icon is in `extension/icons/`.
