# Security review / 保安 檢討 (2026-11-21)

A pass over the browser extension and over how the command line handles files. What was checked, what was
found, what changed, and what is left on purpose. 拡張 프로그램과 CLI의 file 處理를 살펴본 結果입니다.

## Extension / 擴張 프로그램

Checked: how the content script changes a page, the content security policy, permissions, messages, and what
a hostile page or a hostile dictionary file can make it do. 敵對的 頁面(적대적 페이지)을 가정했습니다.

| Finding / 發見 | Result / 措置 |
| --- | --- |
| No `innerHTML`, `eval`, inline script or remote code anywhere; page text only ever goes into `textContent` or `createTextNode`. | Nothing to fix. Kept. |
| A script on the page could click the candidate buttons (the card's shadow root is reachable) or fire a click on a converted word. A click on a candidate saves a choice in `chrome.storage.local`, and that choice applies on **every** site, so a page could change the reader's saved choices. | Fixed: every handler (word hover, click, keys; candidate buttons) ignores events whose `isTrusted` is false. The browser smoke test dispatches forged events and checks nothing opens and nothing is saved; it fails without the fix. |
| Extension-page policy allowed more than needed. | `default-src 'self'; script-src 'self'; object-src 'none'; connect-src 'self'; base-uri 'none'; form-action 'none'`. |
| The message handler checked only that a tab sent the message. | Also requires the sender to be this extension. Batches stay limited to 100 texts of 20,000 characters. |
| A document without `<body>` (SVG, XML) made the content script throw. | It now does nothing there. |
| Hostile text: the matcher is linear in the text (no backtracking patterns); words are looked up as keys of a `Map` or with `Object.hasOwn`, so a word cannot reach a prototype; the card shows candidate text with `textContent`. | Nothing to fix. |

Left on purpose / 意圖的으로 둠:

- ~~Host access to every `http(s)` site~~ — done afterwards: no site is requested at install; the popup asks the browser
  for one host at a time (`optional_host_permissions`) and the content script is registered for that host only.
- `activeTab` stays: it lets the popup read the address of the tab it was opened on.
- A page with hundreds of thousands of Hangul text nodes makes the background worker work for a long time;
  it cannot read or change anything because of that, so there is no limit yet.
- The import in Settings trusts the dictionary the reader selects: the manifest hash shows that the two files
  belong together, not who made them. Import only builds you trust.

## Command line / 命令行

| Finding / 發見 | Result / 措置 |
| --- | --- |
| `--in-place` on a symlink replaced the link with a regular file, and the new file lost the old file's permissions (a private `0600` file became world-readable). | The target of the link is replaced and the link stays; the permissions are copied. |
| The temporary file had a fixed name (`.name.gukhan-tmp`): in a shared folder someone could plant a symlink there and have the write go through it. | `tempfile.mkstemp` (exclusive, unpredictable name). |
| The backup was copied to `name.bak` after an `exists()` check: a dangling symlink at that name passed the check and was written through. | The backup is created exclusively (`x`); `lexists` in the checks. `--out-dir` outputs are created exclusively too. |
| `-o` or `--report` naming the input overwrote it with no backup, although the tool promises not to overwrite without an explicit flag. | Refused, pointing to `--in-place`. `-o` and `--report` may not name the same file either. |
| `gukhan review` and reports print context from the input: an input with escape sequences could drive the reader's terminal (window title, colours, on some terminals the clipboard). | Control characters, line separators and bidirectional overrides in shown context become `�`. Converted text written to a file or stdout is the document itself and is not altered. |
| Reading: only regular files are opened (a FIFO or device is refused by `is_file`), input must be UTF-8, nothing is executed or fetched. | Nothing to fix. |

Tests: `tests/test_cli.py` (symlink, permissions, planted links, same-file refusal, terminal escapes) and
`extension/browser-smoke.cjs` (forged events). Report a problem through the process in `SECURITY.md`.
