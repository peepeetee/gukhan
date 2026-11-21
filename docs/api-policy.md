# API policy / API 方針

## What is public / 公開 範圍

The public API is exactly the names in `gukhan.__all__`, plus the names in the `__all__` of these modules:
`gukhan.convert`, `gukhan.lexicon`, `gukhan.overrides`, `gukhan.analyser`, `gukhan.report`, `gukhan.review`,
`gukhan.suggest` and `gukhan.formats`. The command lines (`gukhan`, `gukhan review`, `gukhan-lexicon-build`, `gukhan-regress`),
their options and exit codes, the override-file syntax and the lexicon TSV columns are public too.
Everything else (names starting with `_`, `gukhan.rules`, `gukhan.segments`, `gukhan.console`, the
`gukhan.lexicon_build` and `gukhan.regress` modules as Python imports) is internal and may change in any release.

公開 API는 `gukhan.__all__`과 위 module의 `__all__`에 있는 이름, 命令行(CLI)의 選項·終了 code, 사용자 지정 file의
文法, 辭典 TSV의 칸입니다. 그 밖의 것은 內部用이며 언제든 바뀔 수 있습니다.

The package ships a `py.typed` marker and is checked with `mypy --strict` in CI; the annotations of the public
API are part of the contract.

## Versioning / 版 番號

gukhan follows [Semantic Versioning](https://semver.org/). Before 1.0.0, a minor version (0.x) may change the public API,
but only as described below; from 1.0.0 on, only a major version removes or changes the meaning of a public name.
Conversion *results* are not part of the API contract: a better lexicon or rule may change what a text converts to,
and the changelog says so. Output formats (the `--report` TSV and Markdown columns) are API.

## Deprecation / 廢止

1. A public name that is going away first stays for at least one minor version (and not less than 90 days),
   emitting a `DeprecationWarning` that names the replacement and the version that removes it, and the
   changelog lists it under **Deprecated**.
2. It is removed in the version announced, and the changelog lists it under **Removed**.
3. A security fix may break this rule; the changelog says why.

廢止할 公開 이름은 적어도 한 minor 版(90日 以上) 동안 `DeprecationWarning`과 함께 남고, 대체 이름과 除去 版을 밝힙니다.

## Adding to the API / 追加

New public names go into `__all__` with a docstring and type annotations in the same change, and into the
[API reference](api.md). A test (`tests/test_public_api.py`) fails when an exported name is missing or undocumented.
