# Security policy / 保安 政策

## Reporting a vulnerability / 脆弱點 報告

Please report privately through GitHub: **Security → Report a vulnerability** on this repository
(a private security advisory). Do not open a public issue for a vulnerability. This is a volunteer project, so
no response time is promised; confirmed problems are fixed as soon as practical and credited
unless you prefer otherwise.

## Scope / 範圍

- The `gukhan` command line tool and library, the lexicon builder, and the browser extension.
- The extension processes page text locally and sends nothing off the device. A way to make it
  send data, load remote code, or read pages the user did not enable it for is in scope.
- Pages it converts are untrusted input: a page that can run script through the extension's
  popup or conversion output is in scope.
- Out of scope: bugs in dependencies (report them upstream), and wrong or missing Hanja
  (open an ordinary issue).

## Supported versions / 支援 版本

Only the latest release receives fixes while the project is pre-1.0.
