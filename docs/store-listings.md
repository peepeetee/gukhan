# Store listings / 스토어 등록 글

Texts and screenshot steps for the Chrome Web Store and Firefox Add-ons (AMO). Prepared 2026-11-21. **Nothing is submitted**;
accounts, fees and the upload are the owner's (see the owner steps at the top of `docs/RELEASE.md`).
Both listings describe the same extension, built by `scripts/package_extension.py`.

## Limits to respect

| Field | Chrome Web Store | Firefox Add-ons |
| --- | --- | --- |
| Name | 45 characters | 50 characters (check the form when uploading) |
| Summary | 132 characters | 250 characters |
| Screenshots | 1280x800 or 640x400, 1 to 5 | PNG or JPEG, at least one |
| Icon | 128 px (in `extension/icons/`) | 128 px, from the manifest |

## Name and summary / 이름과 요약

Name (both): **gukhan 國漢混用** (the Chrome listing may add the tagline: `gukhan 國漢混用 — Korean mixed-script reader`, 45 characters).

Chrome summary, English (under 132):
> Read Korean with Hanja: turns dictionary words into 國漢混用 on pages you choose. All local; nothing is sent.

Chrome summary, 한국어:
> 고른 사이트의 한자어를 國漢混用으로 보여 줍니다. 모든 처리는 기기 안에서 하며 아무것도 보내지 않습니다.

AMO summary, English (under 250):
> Shows Sino-Korean words in mixed Hangul-Hanja script (國漢混用) on the sites you choose, with optional Hanja glosses or ruby for learners. Works offline on your own dictionary; collects nothing.

AMO summary, 한국어:
> 고른 사이트의 한자어를 國漢混用으로 보여 주고, 學習者(학습자)를 위한 한자 倂記(병기)와 루비도 고를 수 있습니다. 사전은 기기 안에서만 쓰며 아무것도 수집하지 않습니다.

## Description, English (both stores)

> gukhan shows Sino-Korean words in mixed script (國漢混用). Turn it on for the sites you pick, and words that have a clear
> Hanja form are rewritten in place (`전기가` → 電氣가); the Hangul ending stays. Words with several possible Hanja are never
> guessed: they stay Hangul, underlined, and a small card lets you choose; your choice is remembered. Turn it off and the
> original text returns.
>
> For readers learning Hanja, the popup's output style chooses how each word is written: mixed 國軍, Hangul with Hanja
> 국군(國軍), Hanja with Hangul 國軍(국군), or ruby with the Hangul reading above each character. If you import the
> character list, the card also shows each Hanja's reading and meaning: the Korean 訓 and 音 (물 수 for 水) where known, else the English meaning.
>
> Private by design: matching happens inside your browser against a dictionary stored on your device. No account, no
> analytics, no network requests, no remote code. Access is asked for one site at a time and given back when you turn the
> site off.
>
> Limits, stated plainly: this browser version matches whole words plus a fixed list of particles and endings. It has no
> morphological analysis, so it is less accurate than the command-line tool, and it can write Hanja for a native word that
> shares its spelling with a Sino-Korean one (for example 사랑 as 舍廊) unless you keep it in Hangul. Code, links, form
> fields, frames and shadow DOM are skipped.
>
> The extension does not include a dictionary unless you use the bundled build; the dictionary is separate data under
> CC BY-SA, with its credits in the package. Open source (Apache-2.0): https://github.com/peepeetee/gukhan

## Description, 한국어 (both stores)

> 한자어를 國漢混用으로 보여 줍니다. 고른 사이트에서 한자가 분명한 낱말만 바꾸고(`전기가` → 電氣가) 어미는 한글로 둡니다.
> 한자가 여럿인 낱말은 추측하지 않고 밑줄만 긋고, 작은 카드에서 직접 고르면 기억합니다. 끄면 원문으로 돌아갑니다.
>
> 한자를 배우는 분을 위해 팝업의 出力 方式(출력 방식)에서 國軍·국군(國軍)·國軍(국군)·루비(한자 위에 한글 讀音)를 고를 수
> 있습니다. 漢字 目錄(목록)을 가져오면 카드에 한자마다 訓·音(물 수)이, 訓이 없는 한자는 音과 英語(영어) 뜻이 보입니다.
>
> 모든 처리는 기기 안에서 이루어지며 아무것도 보내지 않습니다. 계정, 分析(분석), 네트워크 요청, 원격 코드가 없고, 사이트
> 접근은 한 곳씩 허용받고 끄면 돌려줍니다.
>
> 限界(한계): 이 브라우저 版(판)은 낱말 全體(전체) 일치와 정해진 조사·어미 목록만 처리하므로 命令行(명령행) 道具(도구)보다
> 덜 정확하며, 固有語(고유어)가 한자어와 철자가 같으면(사랑→舍廊) 한글로 두도록 지정하지 않는 한 한자로 바뀔 수 있습니다.
> 코드, 링크, 입력란, 프레임, shadow DOM은 건너뜁니다.
>
> 사전은 별도 資料(자료)(CC BY-SA)이며 出處(출처)는 패키지에 들어 있습니다. 오픈 소스(Apache-2.0):
> https://github.com/peepeetee/gukhan

Category: Chrome, Productivity (Education is the alternative); AMO, "Language Support" if offered, else "Other".
Languages: Korean and English. Privacy policy URL:
<https://github.com/peepeetee/gukhan/blob/main/docs/privacy.md>.

## Privacy tab and permission answers (Chrome) / AMO data collection

Chrome single purpose: show Sino-Korean words in Korean web pages in mixed Hangul-Hanja script, on sites the user turns on.

| Permission | Justification |
| --- | --- |
| `storage` | Settings, saved choices, output style. |
| `unlimitedStorage` | The imported dictionary (hundreds of thousands of headwords) exceeds the default quota. |
| `activeTab` | The popup shows the current site's switch. |
| `scripting` | Registers the content script, the only way to rewrite page text, for the one site the user turned on. |
| Optional hosts `http://*/*`, `https://*/*` | Never granted at install; the browser asks about a single host when the user turns that site on, and the access is returned when it is turned off. |

Remote code: none. Data use: none collected, sold or transferred. AMO: the manifest declares
`data_collection_permissions: required: ["none"]`, so choose "no data collection".

## Notes for the AMO reviewer

> The add-on has no build step: the uploaded files are the source (`scripts/package_extension.py` only zips
> `extension/`, leaving out tests and the README). No minification, no remote code, no network requests
> (`connect-src 'self'`). Host access is optional and requested per site from the popup. The bundled dictionary, when
> present, is `dictionary/lexicon.tsv` with its CC BY-SA notice. Run `node extension/engine.test.mjs` for the unit
> tests and `node extension/firefox-smoke.cjs` for an installed-Firefox check. Minimum Firefox version 140.

A new version number is needed for every AMO upload (the manifest is at 0.1.1).

## Screenshots: how to take them / 畵面 撮影 方法

Take five at 1280x800 (browser window resized to that viewport; device scale 1). Use a public-domain or statute page the
project may show: a 法制處 law page, or a Korean Wikisource page of a pre-1962 author. Do not use a page with personal data,
login state or other people's names. Use a clean browser profile with only this extension.

1. **Before and after (the main shot).** Left: the page with the extension off. Right: the same paragraph with it on
   (`전기가` → 電氣가). If one image is needed, set the browser window to half width twice and join them side by side.
2. **Candidate card.** Click an underlined ambiguous word so the card is open with its choices, and, with the character
   list imported, the 音 and meaning line (`電 전 · electricity`).
3. **Output styles.** Open the popup and show *Output style* with `ruby` on; the page behind shows the reading above each Hanja.
4. **Per-site switch.** The popup on one site with the site switch on, showing that other sites stay off.
5. **Settings.** The dictionary and the saved-choices list, as the Settings page shows them.

Optional Chrome small promo tile, 440x280: the 國漢混用 mark on a plain background; text only, no screenshots.

How to capture: with the unpacked or bundled build loaded, press F12 → Ctrl+Shift+P → "Capture screenshot" in the exact
viewport size (device toolbar set to 1280x800), or use the browser's own screenshot tool in a 1280x800 window. Save PNGs as
`store/chrome-1.png` … and the same for Firefox; they are not committed to the repository (store art is not a source file).
Check each one for hostnames, bookmarks, profile pictures and tab titles before uploading.
