# SPDX-License-Identifier: Apache-2.0
"""Download revision-pinned research material separately from regression gold."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from fetch_corpus import fetch, wikitext_to_text

API = "https://ko.wikisource.org/w/api.php"
WORKS = {
    "lee-gwang-su": ("이광수", ["무정", "소년의 비애", "윤광호", "금강산유기"]),
    "hyeon-jin-geon": ("현진건", ["운수 좋은 날", "빈처", "술 권하는 사회", "B사감과 러브레터"]),
    "chae-man-sik": ("채만식", ["치숙", "레디메이드 인생", "태평천하", "탁류"]),
    "han-yong-un": ("한용운", ["님의 침묵", "조선 독립의 서", "조선 청년에게"]),
}
SCANS = {
    "lee-gwang-su": ["CNTS-00076805881 金剛山遊記.pdf"],
    "han-yong-un": ["CNTS-00076805684 님의 沈黙.pdf"],
}


def query(**params):
    return json.loads(fetch(API + "?" + urllib.parse.urlencode({"format": "json", **params})))


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def page_url(title: str, revision: int | None = None) -> str:
    return "https://ko.wikisource.org/w/index.php?" + urllib.parse.urlencode(
        {"title": title, **({"oldid": revision} if revision else {})}
    )


def snapshot(title: str, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    metadata = folder / "metadata.json"
    if metadata.exists():
        return json.loads(metadata.read_text(encoding="utf-8"))
    data = query(action="query", titles=title, prop="revisions", rvprop="ids|timestamp|content", rvslots="main")
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page:
        raise ValueError("page does not exist: " + title)
    revision = page["revisions"][0]
    raw = revision["slots"]["main"]["*"]
    (folder / "source.wiki").write_text(raw, encoding="utf-8")
    text = wikitext_to_text(raw)
    (folder / "reading-copy.txt").write_text(text, encoding="utf-8")
    write_json(folder / "api-response.json", data)
    row = {
        "title": page["title"],
        "revision": revision["revid"],
        "timestamp": revision["timestamp"],
        "url": page_url(page["title"], revision["revid"]),
        "sha256": hashlib.sha256((folder / "source.wiki").read_bytes()).hexdigest(),
        "characters": len(text),
        "hanja_characters": len(re.findall(r"[\u3400-\u9fff]", text)),
        "status": "unverified-transcription",
        "eligible_for_regression": False,
        "scan_transclusion": bool(re.search(r"<pages\b", raw)),
        "licence_templates": sorted(set(re.findall(r"\{\{(PD[^|}\n]*)", raw))),
        "note": "Reading copy strips markup and may omit templates/transclusions. Compare raw source and scans.",
    }
    write_json(metadata, row)
    return row


def children(title: str) -> list[str]:
    result, continuation = [], {}
    while True:
        data = query(action="query", list="allpages", apnamespace=0, apprefix=title + "/", aplimit=500, **continuation)
        result.extend(p["title"] for p in data.get("query", {}).get("allpages", []))
        continuation = data.get("continue")
        if not continuation:
            return result


def download_scan(title: str, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    metadata = folder / "metadata.json"
    if metadata.exists():
        return json.loads(metadata.read_text(encoding="utf-8"))
    data = query(action="query", titles="파일:" + title, prop="imageinfo", iiprop="url|size|sha1|extmetadata")
    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    write_json(folder / "source-metadata.json", data)
    content = fetch(info["url"])
    if not content.startswith(b"%PDF-") or len(content) != info["size"]:
        raise ValueError("incomplete or non-PDF download")
    if hashlib.sha1(content).hexdigest() != info["sha1"]:
        raise ValueError("source SHA-1 mismatch")
    (folder / "scan.pdf").write_bytes(content)
    row = {
        "title": title,
        "url": info["descriptionurl"],
        "download_url": info["url"],
        "bytes": len(content),
        "pages": info.get("pagecount"),
        "sha256": hashlib.sha256(content).hexdigest(),
        "source_sha1": info["sha1"],
        "licence_as_reported": info.get("extmetadata", {}).get("LicenseShortName", {}).get("value"),
        "status": "scan-downloaded-needs-transcription",
        "eligible_for_regression": False,
    }
    write_json(metadata, row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--scans", action="store_true", help="also download the two original-edition PDFs (about 152 MB)"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    for slug, (author, works) in WORKS.items():
        tasks = [("저자:" + author, args.out / slug / "author")]
        for number, title in enumerate(works, 1):
            folder = args.out / slug / f"work-{number:02d}"
            tasks.append((title, folder / "main"))
            try:
                tasks.extend((name, folder / f"part-{i:03d}") for i, name in enumerate(children(title), 1))
            except Exception as error:
                failures.append({"title": title, "stage": "chapter discovery", "error": str(error)})
        for title, folder in tasks:
            try:
                row = snapshot(title, folder)
                records.append({"author": author, "folder": str(folder.relative_to(args.out)), **row})
                print(author, title, row["characters"], flush=True)
            except Exception as error:
                failures.append({"title": title, "stage": "snapshot", "error": str(error)})
        if args.scans:
            for i, title in enumerate(SCANS.get(slug, []), 1):
                folder = args.out / slug / f"scan-{i:02d}"
                try:
                    row = download_scan(title, folder)
                    records.append({"author": author, "folder": str(folder.relative_to(args.out)), **row})
                    print("SCAN", title, row["bytes"], flush=True)
                except Exception as error:
                    failures.append({"title": title, "stage": "scan", "error": str(error)})
    manifest = {"collected_at": datetime.now(timezone.utc).isoformat(), "records": records, "failures": failures}
    write_json(args.out / "catalogue.json", manifest)
    lines = [
        "# 문학 자료 / Literature collection",
        "",
        "연구용 수집본: 회귀 정답 아님 / Research copies, not regression gold.",
        "",
        "Source text and dates are preserved verbatim. Catalogue dates use CE.",
        "",
        "| Author | Material | Status | Local folder |",
        "| --- | --- | --- | --- |",
    ]
    for row in records:
        lines.append(
            f"| {row['author']} | [{row['title']}]({row['url']}) | {row['status']} | "
            f"[{row['folder']}]({row['folder']}/) |"
        )
    lines += ["", "## 다운로드 오류 / Download failures", "", *(json.dumps(e, ensure_ascii=False) for e in failures)]
    (args.out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} records; {len(failures)} failures", flush=True)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
