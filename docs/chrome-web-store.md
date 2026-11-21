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

Summary (132-character limit):
> Read Korean with Hanja: turns dictionary words into 國漢混用 on pages you choose. All local; nothing is sent.

Description (English):
> gukhan shows Sino-Korean words in mixed script (國漢混用). Turn it on for the sites you pick, and
> words that have a clear Hanja form are rewritten in place (`전기가` → 電氣가); the Hangul ending
> stays. Words with several possible Hanja are never guessed: they stay Hangul, underlined, and a
> small card lets you choose; your choice is remembered. Turn it off and the original text returns.
>
> Private by design: matching happens inside your browser against a dictionary stored on your
> device. No account, no analytics, no network requests, no remote code.
>
> Limits: this browser version matches whole words plus a fixed list of particles and endings. It
> has no morphological analysis, so it is less accurate than the command-line tool. Code, links,
> form fields, frames and shadow DOM are skipped.
>
> Open source (Apache-2.0): https://github.com/peepeetee/gukhan. The dictionary is separate data
> under CC BY-SA.

Description (한국어):
> 한자어를 國漢混用으로 보여 줍니다. 고른 사이트에서 한자가 분명한 낱말만 바꾸고(`전기가` → 電氣가) 어미는
> 한글로 둡니다. 한자가 여럿인 낱말은 추측하지 않고 밑줄만 긋고, 작은 카드에서 직접 고르면 기억합니다.
> 끄면 원문으로 돌아갑니다. 모든 처리는 기기 안에서 이루어지며 아무것도 보내지 않습니다.

Category: Productivity (or Accessibility/Education). Language: Korean + English.

## Privacy tab answers

- Single purpose: show Sino-Korean words in Korean web pages in mixed Hangul-Hanja script, on sites
  the user turns on.
- Permission justifications: `storage`: settings and choices. `unlimitedStorage`: the imported
  dictionary (hundreds of thousands of headwords) exceeds the default quota. `activeTab`: popup shows
  the current site's switch. `scripting`: registers the content script, the only way to rewrite page
  text, for the one site the user turned on. Optional host access (`http://*/*`, `https://*/*`): never
  granted at install; the browser asks about a single host when the user turns that site on, and the
  access is given back when it is turned off.
- Remote code: none. Data use: collects none; none sold or transferred; none used for unrelated
  purposes or creditworthiness.
- Privacy policy URL: <https://github.com/peepeetee/gukhan/blob/main/docs/privacy.md>

## Assets still needed from the person

Screenshots (1280x800, at least one) of a Korean page before and after, and optionally a 440x280
small promo tile. 128 px icon is in `extension/icons/`.
