# gukhan browser preview / 브라우저 시험판

Load this folder with Chrome's `chrome://extensions` → Developer mode → Load unpacked.
Open extension settings and select `lexicon.tsv` and its matching `manifest.json`.
Enable the global switch and the current site's switch in the popup. Click or press
Enter on an underlined word to inspect candidates and save a choice. Disable the
switch to restore the original text. Settings also let you edit or remove choices.

한국어: Chrome 확장 프로그램 관리에서 개발자 모드를 켜고 이 폴더를 로드하세요.
설정에서 사전과 manifest를 함께 가져온 뒤 전체 스위치와 사이트 스위치를 켜세요.
밑줄 단어를 누르면 후보를 보고 선택을 저장할 수 있습니다. 끄면 원문으로 돌아갑니다.

Firefox (140 or later): the same folder works. Open `about:debugging` → This Firefox →
Load Temporary Add-on and pick `manifest.json`; the manifest carries both `service_worker`
(Chrome) and `scripts` (Firefox event page) and a fixed add-on id. `firefox-smoke.cjs`
drives real headless Firefox through Selenium in CI (`firefox` job); it has not been run
outside CI yet. Firefox may suspend the background page, which re-parses the dictionary on
each wake.

This is an exact whole-word preview, without Kiwi morphology. Words with attached
particles and endings usually remain unchanged. Ambiguous forms and single-syllable
words remain Hangul until the user chooses. CLI regression scores do not apply.
Code, links, controls and editable regions are skipped. Cross-frame and shadow-root
content is not supported. Dynamic pages may conflict with DOM rewriting; turn the
site off if its layout or interaction changes.

한국어: 형태소 분석 없는 완전 일치 방식이므로 조사·어미가 붙으면 보류될 수 있습니다.
CLI 정확도 수치를 브라우저에 적용할 수 없습니다. 동적 페이지에서 문제가 생기면
사이트 스위치를 끄세요. 프레임과 Shadow DOM 내부는 지원하지 않습니다.

No network requests, telemetry, remote code, or sync. `storage` saves local settings;
`unlimitedStorage` holds the separately imported dictionary; `activeTab` identifies the
current site for the popup. Content scripts cover HTTP(S) pages but return immediately
unless both switches are enabled. The imported manifest's attribution is shown in settings.

한국어: 네트워크 전송·분석·동기화가 없습니다. 사전과 설정은 기기에 저장됩니다.
별도 사전의 저작권 표시는 설정에 표시됩니다. 코드와 사전은 별도 패키지입니다.

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
