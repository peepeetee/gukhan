# SPDX-License-Identifier: Apache-2.0
"""Build manifest: what went in, what came out, and the hashes to prove it."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gukhan import __version__

LICENCE_NOTICE = (
    "이 사전 데이터는 國立國語院 《標準國語大辭典》(stdict.korean.go.kr)을 바탕으로 만들어졌으며, "
    "크리에이티브 커먼즈 저작자표시-동일조건변경허락 2.0 대한민국 라이선스(CC BY-SA 2.0 KR)에 따라 配布됩니다. "
    "漢字 讀音은 Unicode Unihan database(Unicode License v3)를 사용하였습니다."
)


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
            "files": [{"name": str(p.relative_to(path)), "bytes": p.stat().st_size, "sha256": sha256_of(p)} for p in files],
        }
    return {"path": str(path), "kind": "file", "bytes": path.stat().st_size, "sha256": sha256_of(path)}


def write_manifest(
    out_dir: Path,
    *,
    stdict: Path,
    unihan: Path | None,
    unihan_version: str | None,
    counts: dict[str, int],
    outputs: dict[str, Path],
) -> Path:
    manifest = {
        "format": "gukhan-lexicon-manifest/1",
        "builder": {"package": "gukhan", "version": __version__},
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "licence": "CC-BY-SA-2.0-KR",
        "notice": LICENCE_NOTICE,
        "sources": {
            "stdict": {"name": "표준국어대사전 XML dump", "licence": "CC-BY-SA-2.0-KR", **describe_input(stdict)},
            "unihan": (
                {"name": "Unicode Unihan database", "licence": "Unicode-3.0", "version": unihan_version, **describe_input(unihan)}
                if unihan
                else None
            ),
        },
        "counts": counts,
        "outputs": {name: {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256_of(p)} for name, p in outputs.items()},
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
