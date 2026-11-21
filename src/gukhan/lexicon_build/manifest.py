# SPDX-License-Identifier: Apache-2.0
"""Build manifest: what went in, what came out, and the hashes to prove it."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gukhan import __version__

NOTICE_STDICT = "國立國語院 《標準國語大辭典》(stdict.korean.go.kr, CC BY-SA 2.0 KR)"
NOTICE_OPENDICT = "國立國語院 《우리말샘》(opendict.korean.go.kr, CC BY-SA 2.0 KR)"
NOTICE_WIKT = (
    "Wiktionary 寄與者들의 Korean 項目 (en.wiktionary.org, CC BY-SA 4.0; kaikki.org의 wiktextract 抽出本 使用)"
)
NOTICE_KOWIKI = "한국어 위키백과 기여자들의 문서 첫 문단 (ko.wikipedia.org, CC BY-SA 4.0)"
NOTICE_WIKIDATA = "Wikidata 어휘소 (www.wikidata.org, CC0 1.0)"
NOTICE_LAW = (
    "大韓民國 法令(국가법령정보센터 law.go.kr; legalize-kr 저장소 사본). 法令 原文은 公共著作物(저작권법 제7조)"
)
NOTICE_UNIHAN = "漢字 讀音은 Unicode Unihan database(Unicode License v3)를 사용하였습니다."


def licence_notice(
    *,
    stdict: bool,
    wiktextract: bool,
    unihan: bool,
    licence: str,
    opendict: bool = False,
    kowiki: bool = False,
    wikidata: bool = False,
    law: bool = False,
) -> str:
    parts = [
        n
        for n, used in (
            (NOTICE_STDICT, stdict),
            (NOTICE_OPENDICT, opendict),
            (NOTICE_WIKT, wiktextract),
            (NOTICE_KOWIKI, kowiki),
            (NOTICE_WIKIDATA, wikidata),
            (NOTICE_LAW, law),
        )
        if used
    ]
    text = (
        "이 사전 데이터는 " + "과 ".join(parts) + f"을(를) 바탕으로 만들어졌으며, {licence} 라이선스에 따라 配布됩니다."
    )
    if unihan:
        text += " " + NOTICE_UNIHAN
    return text


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe_input(path: Path) -> dict[str, Any]:
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file())
        return {
            "path": str(path),
            "kind": "directory",
            "files": [
                {"name": str(p.relative_to(path)), "bytes": p.stat().st_size, "sha256": sha256_of(p)} for p in files
            ],
        }
    return {"path": str(path), "kind": "file", "bytes": path.stat().st_size, "sha256": sha256_of(path)}


def write_manifest(
    out_dir: Path,
    *,
    stdict: Path | None,
    wiktextract: list[Path],
    opendict: Path | None = None,
    kowiki: Path | None = None,
    wikidata_lexemes: Path | None = None,
    law_glosses: Path | None = None,
    unihan: Path | None,
    unihan_version: str | None,
    licence: str,
    counts: dict[str, int],
    outputs: dict[str, Path],
    ranking_sources: dict[str, Path] | None = None,
) -> Path:
    manifest = {
        "format": "gukhan-lexicon-manifest/1",
        "builder": {"package": "gukhan", "version": __version__},
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "licence": licence,
        "notice": licence_notice(
            stdict=bool(stdict),
            opendict=bool(opendict),
            wiktextract=bool(wiktextract),
            kowiki=bool(kowiki),
            wikidata=bool(wikidata_lexemes),
            law=bool(law_glosses),
            unihan=bool(unihan),
            licence=licence,
        ),
        "sources": {
            "stdict": (
                {"name": "표준국어대사전 XML dump", "licence": "CC-BY-SA-2.0-KR", **describe_input(stdict)}
                if stdict
                else None
            ),
            "opendict": (
                {
                    "name": "우리말샘 XML dump",
                    "licence": "CC-BY-SA-2.0-KR",
                    "note": "contributor-edited; skipped: 방언, 북한어, 옛말 senses, 속담, 관용구, 용례",
                    **describe_input(opendict),
                }
                if opendict
                else None
            ),
            "wiktextract": [
                {
                    "name": "Wiktionary (English edition) Korean entries, wiktextract JSONL via kaikki.org",
                    "licence": "CC-BY-SA-4.0 AND GFDL-1.3",
                    **describe_input(p),
                }
                for p in wiktextract
            ],
            "kowiki": (
                {
                    "name": "Korean Wikipedia dump (article leads: Hangul + parenthesised Hanja)",
                    "licence": "CC-BY-SA-4.0 AND GFDL-1.3",
                    **describe_input(kowiki),
                }
                if kowiki
                else None
            ),
            "wikidata_lexemes": (
                {"name": "Wikidata lexeme dump", "licence": "CC0-1.0", **describe_input(wikidata_lexemes)}
                if wikidata_lexemes
                else None
            ),
            "law_glosses": (
                {
                    "name": "legalize-kr/legalize-kr statutes (mirror of law.go.kr), Hanja glosses of legal terms",
                    "licence": "public work (저작권법 제7조); mirror structure and metadata MIT",
                    **describe_input(law_glosses),
                }
                if law_glosses
                else None
            ),
            "unihan": (
                {
                    "name": "Unicode Unihan database",
                    "licence": "Unicode-3.0",
                    "version": unihan_version,
                    **describe_input(unihan),
                }
                if unihan
                else None
            ),
        },
        "counts": counts,
        "outputs": {
            name: {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256_of(p)} for name, p in outputs.items()
        },
    }
    for name, source in (ranking_sources or {}).items():
        licence_id = "CC-BY-SA-2.0-KR" if name == "krdict" else "KOGL-Type-1"
        manifest["sources"][name] = {"licence": licence_id, **describe_input(source)}
        title = "한국어기초사전" if name == "krdict" else "한국어 학습용 어휘 목록 (2003)"
        manifest["notice"] += f" 國立國語院 {title} ({licence_id}); 후보 정렬용 가공 / adapted for candidate ranking."
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
