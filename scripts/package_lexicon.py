# SPDX-License-Identifier: Apache-2.0
"""Stage the ``gukhan-lexicon`` package from a lexicon build, refusing anything that is not the built lexicon.

    python scripts/package_lexicon.py build/lexicon --version 0.1.0 -o build/gukhan-lexicon-0.1.0
    cd build/gukhan-lexicon-0.1.0 && python -m build

The input is the output folder of ``gukhan-lexicon-build``. Only ``lexicon.tsv``, ``chars.tsv`` and
``manifest.json`` are copied (``rejects.tsv`` is not shipped). The script stops, writing nothing, if

* the folder holds anything else that looks like a source dump (``.xml``, ``.zip``, ``.jsonl``, ``.gz`` ...),
* ``manifest.json`` names no licence, or one other than CC-BY-SA-4.0 / CC-BY-SA-2.0-KR, or the first
  line of ``lexicon.tsv`` states a different one,
* a row has markup, or a definition excerpt longer than 200 characters (the builder writes at most
  80; longer text would suggest a source's full entry or usage example got through),
* the manifest says Wiktionary went in but the licence is not CC-BY-SA-4.0.

Local paths in the manifest are reduced to their last component. Run ``python -m build`` and
``twine check`` on the result yourself; nothing here uploads.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "packaging" / "gukhan-lexicon"
SHIP = ("lexicon.tsv", "chars.tsv", "manifest.json")
IGNORED = {
    "rejects.tsv",
    "char-info.tsv",
    "variants.tsv",
}  # not shipped in the Python package (the extension imports char-info.tsv; variants.tsv is for gukhan-regress)
LICENCES = {"CC-BY-SA-4.0", "CC-BY-SA-2.0-KR"}
MAX_SENSE = 200
MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
CC_URL = {
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC-BY-SA-2.0-KR": "https://creativecommons.org/licenses/by-sa/2.0/kr/",
}


class PackageError(Exception):
    pass


def scrub_paths(node):
    """Reduce any ``path`` value in the manifest to its last component (drop the builder's local folders)."""
    if isinstance(node, dict):
        return {
            k: (re.split(r"[\\/]", v)[-1] if k == "path" and isinstance(v, str) else scrub_paths(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [scrub_paths(v) for v in node]
    return node


def check_build(src: Path) -> dict:
    """Validate a build folder; return its manifest. Raises PackageError with the reason."""
    if not src.is_dir():
        raise PackageError(f"not a folder: {src}")
    stray = sorted(p.name for p in src.iterdir() if p.name not in SHIP and p.name not in IGNORED)
    if stray:
        raise PackageError(
            "the build folder holds files that are not the built lexicon: "
            + ", ".join(stray)
            + " (raw dictionary dumps must never go into the package)"
        )
    for name in SHIP:
        if not (src / name).is_file():
            raise PackageError(f"missing {name}")
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    licence = manifest.get("licence")
    if licence not in LICENCES:
        raise PackageError(f"manifest licence {licence!r} is not one of {sorted(LICENCES)}")
    if not manifest.get("notice"):
        raise PackageError("manifest has no attribution notice")
    if manifest.get("sources", {}).get("wiktextract") and licence != "CC-BY-SA-4.0":
        raise PackageError("Wiktionary is in the build but the licence is not CC-BY-SA-4.0")
    with (src / "lexicon.tsv").open(encoding="utf-8") as fh:
        first = fh.readline()
        m = re.search(r"licence=(\S+)", first)
        if not first.startswith("# gukhan lexicon") or not m or m.group(1) != licence:
            raise PackageError(f"lexicon.tsv header does not state licence {licence}: {first.strip()!r}")
        rows = 0
        for n, line in enumerate(fh, 2):
            if line.startswith("#") or not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            rows += 1
            if MARKUP.search(line):
                raise PackageError(f"lexicon.tsv line {n}: markup in a row (an XML fragment from a dump?)")
            if len(cols) > 4 and len(cols[4]) > MAX_SENSE:
                raise PackageError(f"lexicon.tsv line {n}: definition excerpt over {MAX_SENSE} characters")
    if rows == 0:
        raise PackageError("lexicon.tsv has no rows")
    return manifest


def stage(src: Path, out: Path, version: str) -> Path:
    manifest = scrub_paths(check_build(src))
    if out.exists():
        raise PackageError(f"{out} already exists; choose a new folder")
    shutil.copytree(TEMPLATE, out)
    pyproject = out / "pyproject.toml"
    pyproject.write_text(pyproject.read_text(encoding="utf-8").replace("@VERSION@", version), encoding="utf-8")
    data = out / "src" / "gukhan_lexicon" / "data"
    data.mkdir(parents=True)
    shutil.copyfile(src / "lexicon.tsv", data / "lexicon.tsv")
    shutil.copyfile(src / "chars.tsv", data / "chars.tsv")
    (data / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    licence = manifest["licence"]
    (out / "NOTICE.txt").write_text(
        f"{manifest['notice']}\n\nLicence of the data files: {licence} ({CC_URL[licence]}).\n"
        "The attribution above must be kept with any copy or adaptation of the data. The Python module\n"
        "gukhan_lexicon/__init__.py is Apache-2.0. Sources and their licences: THIRD-PARTY-NOTICES.md at\n"
        "https://github.com/peepeetee/gukhan, and data/manifest.json.\n",
        encoding="utf-8",
    )
    shutil.copyfile(ROOT / "THIRD-PARTY-NOTICES.md", out / "THIRD-PARTY-NOTICES.md")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build", type=Path, help="output folder of gukhan-lexicon-build")
    ap.add_argument("--version", help="package version, e.g. 0.1.0")
    ap.add_argument("-o", "--out", type=Path, help="new folder to stage the package in")
    ap.add_argument("--check-only", action="store_true", help="validate the build folder and stop")
    args = ap.parse_args(argv)
    try:
        if args.check_only:
            m = check_build(args.build)
            print(f"ok: {m['licence']}, {m.get('counts', {}).get('entries', '?')} entries")
            return 0
        if not (args.version and args.out):
            ap.error("--version and -o are required unless --check-only")
        out = stage(args.build, args.out, args.version)
    except (PackageError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"staged {out}; next: cd {out} && python -m build && twine check dist/*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
