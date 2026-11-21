# SPDX-License-Identifier: Apache-2.0
"""Zip extension/ into an installable .xpi/.zip without tests or the README.

    python scripts/package_extension.py build/gukhan-0.1.0.xpi
    python scripts/package_extension.py out.xpi --dictionary build/lexicon
    python scripts/package_extension.py out.xpi --dictionary build/lexicon --no-definitions
    python scripts/package_extension.py gukhan-chrome.zip --target chrome   # Chrome Web Store upload

``--dictionary DIR`` (lexicon.tsv + manifest.json from gukhan-lexicon-build) bundles the dictionary
under ``dictionary/``; the add-on loads it on first run. ``--no-definitions`` first blanks the
part-of-speech, source and definition columns, which makes the dictionary about five times smaller;
the candidate card then lists only the Hanja. The dictionary keeps its own licence: a notice file is
written next to it. The zip has manifest.json at its root, as addons.mozilla.org and Firefox expect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extension"
SKIP = ("engine.test.mjs", "a11y.test.mjs", "browser-smoke.cjs", "firefox-smoke.cjs", "bundled-smoke.cjs", "README.md")


def strip_definitions(text: str) -> str:
    """Blank columns 3-5 (pos, source, sense); keep hangul, hanja and the ranking columns."""
    out = []
    lines = text.split("\n")  # not splitlines(): a U+2028 or U+0085 inside a gloss is not a row break
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        if line.startswith("#") or not line:
            out.append(line)
            continue
        p = line.split("\t")
        p[2:5] = ["", "", ""]
        out.append("\t".join(p))
    return "\n".join(out) + "\n"


def chrome_manifest(text: str) -> str:
    """The Chrome Web Store flavour of manifest.json.

    Drops what only Firefox reads (``browser_specific_settings``, the event-page ``scripts`` list)
    so the store shows no unknown-key warnings. The manifest asks for no site at install: the reader turns
    a site on in the popup, the browser asks about that one host (``optional_host_permissions``), and the
    worker registers the content script for it. ``activeTab`` lets the popup read the current address.
    """
    m = json.loads(text)
    m.pop("browser_specific_settings", None)
    m.pop("host_permissions", None)  # none declared; kept so a stray one never reaches the store
    m["background"].pop("scripts", None)
    m["minimum_chrome_version"] = "116"
    return json.dumps(m, ensure_ascii=False, indent=2) + "\n"


def dictionary_files(directory: Path, no_definitions: bool) -> dict[str, bytes]:
    text = (directory / "lexicon.tsv").read_text(encoding="utf-8")
    meta = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if no_definitions:
        text = strip_definitions(text)
        meta["notice"] += (
            " (이 版에서는 品詞·出處·뜻풀이를 뺐습니다 / this build omits part of speech, source and definitions.)"
        )
    data = text.encode("utf-8")
    meta["outputs"] = {
        "lexicon": {"name": "lexicon.tsv", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    }
    files = {}
    info = directory / "char-info.tsv"  # reading and meaning of each Hanja, for the candidate card
    if info.exists():
        info_data = info.read_bytes()
        meta["outputs"]["char_info"] = {
            "name": "char-info.tsv",
            "bytes": len(info_data),
            "sha256": hashlib.sha256(info_data).hexdigest(),
        }
        files["dictionary/char-info.tsv"] = info_data
    notice = (
        f"{meta['notice']}\n\nLicence: {meta.get('licence', '')}. The dictionary data is separate from the add-on's\n"
        "Apache-2.0 code (see LICENSE.txt) and keeps its own licence; see https://github.com/peepeetee/gukhan\n"
    )
    return {
        **files,
        "dictionary/lexicon.tsv": data,
        "dictionary/manifest.json": json.dumps(meta, ensure_ascii=False, indent=1).encode("utf-8"),
        "dictionary/NOTICE.txt": notice.encode("utf-8"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("--dictionary", type=Path, help="directory with lexicon.tsv and manifest.json to bundle")
    ap.add_argument(
        "--no-definitions", action="store_true", help="bundle the dictionary without pos/source/definitions"
    )
    ap.add_argument(
        "--target", choices=("firefox", "chrome"), default="firefox", help="manifest flavour (default: firefox)"
    )
    args = ap.parse_args(argv)
    if args.no_definitions and not args.dictionary:
        ap.error("--no-definitions needs --dictionary")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(EXT.rglob("*")):
            if not path.is_file() or path.name in SKIP:
                continue
            name = path.relative_to(EXT).as_posix()
            if name == "manifest.json" and args.target == "chrome":
                z.writestr(name, chrome_manifest(path.read_text(encoding="utf-8")))
            else:
                z.write(path, name)
        z.write(ROOT / "LICENSE", "LICENSE.txt")
        if args.dictionary:
            for name, data in dictionary_files(args.dictionary, args.no_definitions).items():
                z.writestr(name, data)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
