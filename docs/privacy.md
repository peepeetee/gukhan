# Privacy policy / 個人情報 處理方針 (개인정보 처리방침)

Effective 2026-11-05 (reviewed 2026-11-21, no change in behaviour) · 施行 2026年 11月 5日 · Applies to the gukhan 國漢混用 browser extension (Chrome and Firefox).

## English

**The extension collects nothing and sends nothing.** It has no server, no account, no analytics,
no advertising, no crash reporting and no sync. The authors never receive any data from it.

- **Page text.** When you switch the extension on (the global switch and the switch for that site
  must both be on), text on the page you are reading is matched against the dictionary *inside your
  browser*. The page text is not stored and does not leave your device. With either switch off, the
  content script returns at once and does not read the page.
- **Dictionary.** The dictionary you import (or the one bundled in the package) is kept in your
  browser's IndexedDB on your device. It holds only word lists (Korean headwords, Hanja, labels and
  credits taken from public dictionaries and statutes), never anything about you.
- **Your choices.** Picks, overrides, the switches and the site list are saved in the browser's
  extension storage (`chrome.storage.local`) on your device. Hostnames appear in that list only
  where you turned a site on.
- **Network.** The extension makes no network requests. Its content security policy
  (`connect-src 'self'`) lets extension pages read only their own packaged files, and it loads no
  remote code or fonts.
- **Permissions.** `storage` and `unlimitedStorage` hold your settings and the dictionary;
  `activeTab` lets the popup show the address of the tab you opened it on; the content script runs
  on HTTP(S) pages so it can rewrite text there once you enable it.
- **Third parties.** None. Nothing is sold, shared or transferred, for any purpose.
- **Deleting data.** Uninstalling the extension deletes everything it stored. Settings also lets you
  remove your choices.
- **Changes.** If this ever changes, the new policy is published in this file in the repository
  before a release that behaves differently, and the change appears in its git history.
- **Contact.** Open an issue at <https://github.com/peepeetee/gukhan/issues>; for a security
  matter, follow `SECURITY.md`.

Firefox manifest declaration: `data_collection_permissions: required: ["none"]`.
Chrome Web Store data-use disclosure: no user data collected; none sold or transferred; none used
for creditworthiness or lending.

## 國漢混用 (한국어)

**이 확장 프로그램은 아무것도 수집하지 않고 아무것도 보내지 않습니다.** 서버, 계정, 分析(분석), 廣告(광고),
오류 보고, 同期化(동기화)가 모두 없으며 製作者(제작자)는 어떤 資料(자료)도 받지 않습니다.

- **페이지 글.** 全體(전체) 스위치와 해당 사이트 스위치를 둘 다 켰을 때에만, 읽고 있는 페이지의 글을
  *브라우저 안에서* 사전과 대조합니다. 페이지 글은 저장되지 않고 기기 밖으로 나가지 않습니다.
  어느 하나라도 꺼져 있으면 페이지를 읽지 않습니다.
- **사전.** 가져온 사전(또는 패키지에 들어 있는 사전)은 기기의 브라우저 IndexedDB에 보관합니다. 사전에는 公開(공개) 辭典·法令에서 가져온 낱말·漢字·표지·出處만 들어 있고, 사용자에 관한 內容(내용)은 없습니다.
- **선택.** 고른 漢字(한자), 사용자 지정, 스위치, 사이트 목록은 기기의 확장 프로그램 저장소에 보관합니다.
  사이트 이름은 사용자가 켠 경우에만 목록에 들어갑니다.
- **네트워크.** 네트워크 要請(요청)을 하지 않습니다. 원격 코드나 글꼴도 불러오지 않습니다.
- **權限(권한).** `storage`·`unlimitedStorage`는 설정과 사전 보관용, `activeTab`은 팝업에 現在(현재) 탭의
  주소를 보이기 위한 것, 內容(콘텐츠) 스크립트는 켠 뒤 HTTP(S) 페이지의 글을 바꾸기 위한 것입니다.
- **第三者(제3자).** 없습니다. 판매·공유·전송을 하지 않습니다.
- **삭제.** 확장 프로그램을 지우면 보관한 資料(자료)가 모두 사라집니다. 설정에서 선택만 지울 수도 있습니다.
- **문의.** <https://github.com/peepeetee/gukhan/issues>
