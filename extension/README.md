# gukhan browser preview / 브라우저 시험판

Load this folder with Chrome's `chrome://extensions` → Developer mode → Load unpacked,
or with Firefox 140 or newer at `about:debugging#/runtime/this-firefox` → Load Temporary
Add-on → choose `manifest.json` in this folder. One manifest serves both browsers.
Firefox removes a temporary add-on when it closes; a permanent install needs a signed
package from addons.mozilla.org (not published yet).
Open extension settings and select `lexicon.tsv` and its matching `manifest.json`.
Enable the global switch and the current site's switch in the popup. Click or press
Enter on an underlined word to inspect candidates and save a choice. Disable the
switch to restore the original text. Settings also let you edit or remove choices.

한국어: Chrome 확장 프로그램 관리에서 개발자 모드를 켜고 이 폴더를 로드하세요.
Firefox 140 이상은 about:debugging → 이 Firefox → 임시 부가 기능 로드에서 이 폴더의
manifest.json을 고르세요. 임시 부가 기능은 Firefox를 닫으면 사라지며, 영구 설치에는
addons.mozilla.org 서명이 필요합니다(아직 게시하지 않았습니다).
설정에서 사전과 manifest를 함께 가져온 뒤 전체 스위치와 사이트 스위치를 켜세요.
밑줄 단어를 누르면 후보를 보고 선택을 저장할 수 있습니다. 끄면 원문으로 돌아갑니다.

This preview has no morphology model. It matches whole words, plus a fixed list of
particles and endings (가, 는, 에서, 하는, 된 …): the stem must be a dictionary word and the
particle stays in Hangul (`전기가` → 電氣가 once 전기 is decided). Anything else with an
ending stays unchanged. Phrase entries (`전기 공학 = 電氣 工學`, in the dictionary or in your
choices) match words separated by one space. Ambiguous words and single-syllable words stay
Hangul until the user chooses. CLI regression scores do not apply.
Code, links, controls and editable regions are skipped. Cross-frame and shadow-root
content is not supported. Dynamic pages may conflict with DOM rewriting; turn the
site off if its layout or interaction changes.

한국어: 형태소 분석이 없습니다. 완전 일치와 정해진 조사·어미 목록만 처리하며, 그 밖의 어미는 그대로 둡니다.
句(「전기 공학 = 電氣 工學」)는 한 칸 띄어 쓴 낱말에 적용됩니다.
CLI 정확도 수치를 브라우저에 적용할 수 없습니다. 동적 페이지에서 문제가 생기면
사이트 스위치를 끄세요. 프레임과 Shadow DOM 내부는 지원하지 않습니다.

No network requests, telemetry, remote code, or sync. `storage` saves local settings;
`unlimitedStorage` holds the separately imported dictionary; `activeTab` identifies the
current site for the popup. Content scripts cover HTTP(S) pages but return immediately
unless both switches are enabled. The imported manifest's attribution is shown in settings.

한국어: 네트워크 전송·분석·동기화가 없습니다. 사전과 설정은 기기에 저장됩니다.
별도 사전의 저작권 표시는 설정에 표시됩니다. 코드와 사전은 별도 패키지입니다.

Firefox: the manifest carries `browser_specific_settings.gecko` (id, minimum version 140,
`data_collection_permissions: none`) and lists `worker.js` under both `service_worker`
(Chrome) and `scripts` (Firefox event page). Chrome may show a harmless warning about the
unknown `browser_specific_settings` key. `node extension/firefox-smoke.cjs` runs the same
flow in an installed Firefox over Marionette (set `FIREFOX_BIN` if needed); it passed on
2026-10-29 in Firefox 158 on Windows 11. The imported dictionary is kept in IndexedDB, one record per headword (a 626k-headword import takes about a minute once);
the background page reads only the words a page needs, so it does not re-parse anything when it wakes.
Dictionaries imported before this change must be imported again. Privacy policy: `docs/privacy.md`.

Validation: `node --test extension/engine.test.mjs` for the matching engine, and
`node extension/browser-smoke.cjs` for a real Chromium run through Playwright
(dictionary import with manifest check, candidate panel, saved override, protected
`<pre>`/`<input>` text, toggle restore, per-site switch). CI runs both in
`.github/workflows/extension.yml`. The smoke test first passed on 2026-10-28 in
headless Chromium on Linux (Playwright 1.63.0); Windows and a headed browser are
still unverified. Install Playwright with `npm install --prefix build/browser-check
playwright && npx --prefix build/browser-check playwright install chromium` if it
is not on the system.

한국어: 엔진 단위 시험과 Playwright 실제 브라우저 시험을 CI에서 실행합니다.
Linux 헤드리스 Chromium에서는 통과했고 Windows와 일반 창 모드는 아직 확인하지 않았습니다.
