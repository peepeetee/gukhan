# Data distribution assessment / 資料 配布 評價

Assessed 2026-10-28 from each source's own terms page. Local inventory and
per-file SHA-256 values live outside the repo in `gukhan-data/DATASETS.md`
and `gukhan-data/datasets.json` (3.4 GB, 775 files, all held in full).

한국어 요약: 코드(Apache-2.0)와 사전 데이터(CC BY-SA)는 계속 분리합니다.
國立國語院 (National Institute of Korean Language) 사전 원본 XML은 용례와
크기 문제로 재배포하지 않고, 빌드된 lexicon만 `gukhan-lexicon`으로 배포합니다.
Unihan과 학습용 어휘 목록은 작고 허용적이므로 `gukhan-lexicon` 저장소에
그대로 둘 수 있습니다. Kiwi 모델은 pip 의존성이므로 배포하지 않습니다.

## Summary

| Dataset | Licence (from source page) | Share-alike | Size | Raw redistributable? | Recommendation |
| --- | --- | --- | ---: | --- | --- |
| 標準國語大辭典 (Standard Korean Language Dictionary) XML, 88 chunks | CC BY-SA 2.0 KR | Yes | 689 MB | In principle, but source-cited 用例 (usage examples) and media are excluded by the policy, and the raw XML contains them | Not shipped. Built lexicon only, in `gukhan-lexicon`. Builder may fetch from the pinned mirror commit on request; never silently |
| 韓國語基礎辭典 (Korean Basic Dictionary) XML, 11 chunks | CC BY-SA 2.0 KR | Yes | 387 MB | Same as above | Not shipped. Only vocabulary levels enter the lexicon |
| 우리말샘 (Urimalsaem) XML, 25 chunks | CC BY-SA 2.0 KR | Yes | 1,861 MB | Same as above; contributor entries also CC BY-SA 2.0 KR | Not shipped. Held locally for a later builder stage |
| 韓國語 學習用 語彙 目錄 (2003 learner vocabulary list) | KOGL Type 1 (公共누리 第1類型) | No (attribution only) | 132 KB | Yes | Ship the raw file in the `gukhan-lexicon` repo with attribution; ranks also enter the lexicon |
| Wiktionary Korean entries, kaikki.org wiktextract JSONL | CC BY-SA 4.0 + GFDL 1.3 (Wikimedia Terms of Use) | Yes | 208 MB | Yes, with attribution and share-alike | Release asset of `gukhan-lexicon` (pinned copy for reproducible builds). Not in any repo |
| Unicode Unihan 18.0.0 | Unicode License v3 | No | 8 MB | Yes, with the notice | Ship in the `gukhan-lexicon` repo (small, permissive); builder also accepts the versioned unicode.org URL |
| Kiwi model files (kiwipiepy_model 0.24.0) | Apache-2.0 (code and models) | No | 88 MB | Yes | Not shipped by us: it is a pip dependency, installed with `kiwipiepy>=0.24`. Keep its NOTICE in `THIRD-PARTY-NOTICES.md` |
| Regression corpus texts (constitutions, 1919 texts, 1926 preface) | Public domain (著作權法 第7條; authors died before 1956) | No | 1.4 MB | Extracted text yes; raw HTML pages no (site chrome) | Reviewed excerpts stay in `tests/regression/` in the gukhan repo, as now. `.raw` files never |
| Literature snapshots (4 authors, 154 Wikisource pages) | Works public domain; transcription layer CC BY-SA 4.0 | Transcriptions: yes | 8 MB | Yes, with Wikisource attribution | Not shipped yet (research copies, not gold). When excerpts are promoted to regression items, cite the pinned oldid |
| Literature scans (2 PDFs from Wikimedia Commons) | Public domain (PD-South Korea, PD-scan) | No | 152 MB | Yes | Not shipped. Stable Commons URLs and SHA-1 are recorded; user fetches |

## Licence findings per source

### 國立國語院 dumps (標準國語大辭典, 韓國語基礎辭典, 우리말샘)

All three policy pages state that every text not marked otherwise is under
CC BY-SA 2.0 KR (크리에이티브 커먼즈 저작자표시-동일조건변경허락 2.0 대한민국),
commercial use included, with two carve-outs:

- 用例 (usage examples) with a cited source remain with the original rights
  holder and need separate permission.
- Media files (images, audio, pronunciations) have individual terms and are
  not open.

The spellcheck-ko mirror redistributes the raw XML and states the same
licence and the same carve-outs. The raw dumps do contain source-cited
examples, so a redistribution by us would have to strip them first. The
builder already excludes examples; the built lexicon (headword, Hanja form,
part of speech, level, rank) is therefore clean and is the thing to ship.

Attribution obligation: name 國立國語院 and the dictionary, link the policy
page, state CC BY-SA 2.0 KR. Share-alike: an adapted lexicon must be CC BY-SA.
CC BY-SA 2.0 KR clause 4(b) allows release of adaptations under a later
version, which is why a build that also includes Wiktionary becomes
CC BY-SA 4.0.

### 學習用 語彙 目錄 (learner vocabulary list)

The download page states KOGL Type 1: free use, modification and commercial
use with source attribution. No share-alike. The local copy is byte-identical
to the file the page serves today. Attribution: "國立國語院, 한국어 학습용
어휘 목록 (2003), KOGL Type 1".

### Wiktionary via kaikki.org

The Wikimedia Terms of Use dual-license text contributions under
CC BY-SA 4.0 and GFDL. kaikki.org adds no licence of its own and asks for a
citation of Ylonen, *Wiktextract* (LREC 2022). Redistribution of the raw
JSONL is allowed with attribution to Wiktionary contributors and share-alike.
The upstream file is regenerated about weekly without versioned URLs, so a
reproducible build needs the exact copy pinned: hence the release-asset
recommendation.

### Unicode Unihan

Unicode License v3: permissive, requires only that the copyright and
permission notice travel with the data. Compatible with both the Apache-2.0
code and the CC BY-SA lexicon.

### Kiwi models

PyPI metadata gives `License-Expression: Apache-2.0`; the Kiwi NOTICE states
that the trained model files are Apache-2.0 and that the training corpora
(21世紀 世宗計劃, 모두의 말뭉치) are not redistributed. We never ship the
models; pip does.

### Corpus and literature

Korean Copyright Act article 7 excludes constitutions, statutes and official
documents from protection. 韓龍雲 died in 1944, 玄鎭健 in 1943, 李光洙 and
蔡萬植 in 1950, so their works are public domain in Korea. Wikisource
transcriptions are contributed under CC BY-SA 4.0; a faithful transcription
adds no copyrightable content, but citing the Wikisource revision is both
courteous and the only way to reproduce the text. Both scans are marked
public domain on Commons with SHA-1 values we verified.

## Combined-licence consequence

| Build inputs | Lexicon licence |
| --- | --- |
| 標準國語大辭典 only (+ Unihan, learner list) | CC BY-SA 2.0 KR |
| Any build that includes Wiktionary | CC BY-SA 4.0 |
| Adding 韓國語基礎辭典 or 우리말샘 | No change (same 2.0 KR, upgradeable) |

KOGL Type 1 and Unicode inputs are attribution-only and do not affect the
result. The Apache-2.0 code never bundles the lexicon, so its licence is
unaffected by any of the above.

## Where each artefact lives

- `gukhan` repo (Apache-2.0): code, `tests/regression/` excerpts, this
  assessment. No dictionary data.
- `gukhan-lexicon` repo and package (CC BY-SA): built `lexicon.tsv`,
  `chars.tsv`, `manifest.json`, `Unihan.zip`, the learner list, the notice
  text from `THIRD-PARTY-NOTICES.md`.
- `gukhan-lexicon` release assets: the pinned kaikki JSONL used for each
  release, so that anyone can rebuild bit-for-bit.
- Never distributed by us: the three 國立國語院 dumps, the Kiwi models, raw
  HTML pages, scans. The manifest records where to get them and what hash to
  expect. The builder downloads nothing unless the user passes an explicit
  fetch flag.

## Open item found during inventory

The combined lexicon built on 2026-10-28 read 87 of the 88 標準國語大辭典
chunks; the last chunk (`436578.xml`, 1,578 items) was missing locally and
has now been fetched and verified. The lexicon should be rebuilt before the
next release so that `manifest.json` covers all 436,578 items.
