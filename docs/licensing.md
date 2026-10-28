# Licensing

Decided 2026-10-28 (民國115年). Goal: widest possible adoption.

## Summary

| Part | Licence | Package |
| --- | --- | --- |
| Code (CLI, library, lexicon builder, Chrome extension) | Apache-2.0 | `gukhan` |
| Prebuilt lexicon data | CC BY-SA 2.0 KR | `gukhan-lexicon` (separate) |

The two never share a package. Anyone may embed the code in a product of any
licence; the lexicon file travels alongside it, unchanged, with its
attribution. Anyone who edits the lexicon data must publish their edits under
CC BY-SA 2.0 KR.

## Why Apache-2.0 rather than MIT

Both are permissive. Apache-2.0 adds an explicit patent grant, which larger
adopters' legal teams look for, and a `NOTICE` file that downstream must keep,
which is where the dictionary attributions live. It is also the licence of
Kiwi and mecab-ko-dic, so third-party notices stay uniform.

## Why not GPL-3.0

A GPL dependency or GPL code would require every program that links or bundles
gukhan to be GPL as well, which blocks embedding in non-GPL products and
contradicts the adoption goal. CI therefore fails on GPL/AGPL Python
dependencies. LGPL is allowed because it covers only the library itself.

## Why the lexicon is share-alike

Every word-level Sino-Korean source audited is CC BY-SA (표준국어대사전,
우리말샘, Wiktionary). Only the Unicode Unihan database (per-character
readings) is permissive, and characters alone cannot resolve word-level
homographs. Hence the lexicon is built from 표준국어대사전 and shipped
separately under its own licence. The builder in this repo lets anyone rebuild
it from the source; the build manifest records source versions and hashes.

## Rules for contributors

- Every source file carries an SPDX header:
  `# SPDX-License-Identifier: Apache-2.0`
- Add a row to `THIRD-PARTY-NOTICES.md` for every new dependency or data
  source, with the licence as stated on the source's own page.
- Never copy data from a source into this repository. Data goes through the
  builder into `gukhan-lexicon`.
- Nothing from UTagger: no code, binaries, dictionaries, or outputs, and no
  accuracy comparisons against it.

## Audit record

Licences were read from each source's own page on 2026-10-28. The 우리말샘
policy page could not be fetched automatically and was verified from a
browser capture the same day: CC BY-SA 2.0 KR, identical in substance to the
표준국어대사전 policy. The English Wiktionary copyright page could not be
fetched; its row in `THIRD-PARTY-NOTICES.md` rests on the Korean Wiktionary
page and should be re-checked in a browser before Wiktionary is used.
