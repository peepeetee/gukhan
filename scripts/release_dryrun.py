# SPDX-License-Identifier: Apache-2.0
"""Release dry run: build gukhan and gukhan-lexicon, check them, install them into a clean venv, smoke-test.

    python scripts/release_dryrun.py            # needs `pip install build twine`; nothing is uploaded

1. builds the sdist and wheel of gukhan and of gukhan-lexicon (staged from a tiny hand-written lexicon,
   never a real build) with ``python -m build``;
2. runs ``twine check`` on all four files;
3. looks inside them: the licence files and the sample lexicon are in the wheel, and neither archive holds
   tests, build output, virtual environments or dictionary dumps;
4. installs both wheels into a fresh venv (kiwipiepy comes from PyPI) and, from an empty folder, runs
   ``gukhan --version``, a conversion with the installed lexicon, and the other entry points.

한국어: gukhan과 gukhan-lexicon의 sdist·wheel을 만들어 twine으로 檢査하고, 새 venv에 設置해 簡單히 實行해 봅니다.
아무것도 올리지 않습니다 / Nothing is published.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_DIRS = {"build", ".venv", ".git", ".github", "browser-profile", "node_modules", "__pycache__"}
FORBIDDEN_SUFFIXES = (".xml", ".zip", ".jsonl", ".gz", ".pyc")
HEADER = "# gukhan lexicon\tlicence=CC-BY-SA-4.0\tmanifest=manifest.json\n# hangul\thanja\tpos\tsource\tsense\tweight\n"
ROWS = "봉수\t烽燧\t명사\tdryrun\t\t1\n"
SAMPLE_TEXT = "봉수 이야기.\n"


class DryRunError(Exception):
    pass


def run(cmd: list[str], cwd: Path | None = None) -> str:
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise DryRunError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))}\n{p.stdout}\n{p.stderr}")
    return p.stdout


def build(src: Path, out: Path) -> list[Path]:
    run([sys.executable, "-m", "build", "--outdir", str(out), str(src)])
    files = sorted(out.iterdir())
    if sorted(f.suffix for f in files) != [".gz", ".whl"]:
        raise DryRunError(f"expected one sdist and one wheel in {out}, found {[f.name for f in files]}")
    return files


def names(archive: Path) -> list[str]:
    if archive.suffix == ".whl":
        with zipfile.ZipFile(archive) as z:
            return z.namelist()
    with tarfile.open(archive) as t:
        return t.getnames()


def inspect(archive: Path, must_have: tuple[str, ...]) -> None:
    listing = names(archive)
    for needle in must_have:
        if not any(needle in n for n in listing):
            raise DryRunError(f"{archive.name} lacks {needle}")
    bad = [
        n
        for n in listing
        if FORBIDDEN_DIRS & set(n.replace("\\", "/").split("/")[:-1]) or n.endswith(FORBIDDEN_SUFFIXES)
    ]
    # setuptools puts tests/test_*.py in an sdist; fixtures, regression texts and anything else must not follow
    bad += [n for n in listing if "/tests/" in n and not n.endswith((".py", "/"))]
    if bad:
        raise DryRunError(f"{archive.name} holds files that must not be published: {bad[:5]}")
    print(f"  {archive.name}: {len(listing)} files, content checked")


def smoke(wheels: list[Path], work: Path) -> None:
    env = work / "venv"
    venv.create(env, with_pip=True)
    py = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    bindir = py.parent
    run([str(py), "-m", "pip", "install", "--quiet", *map(str, wheels)])
    empty = work / "empty"
    empty.mkdir()
    ver = run([str(py), "-m", "gukhan.cli", "--version"], cwd=empty)
    if "gukhan" not in ver:
        raise DryRunError(f"--version printed {ver!r}")
    sample = empty / "in.txt"
    sample.write_text(SAMPLE_TEXT, encoding="utf-8")
    out = run([str(py), "-m", "gukhan.cli", str(sample)], cwd=empty)
    if "烽燧" not in out:
        raise DryRunError(f"installed lexicon was not used; output: {out!r}")
    code = (
        "import gukhan_lexicon as g, gukhan.lexicon as L;"
        "m=g.manifest();assert m['licence'];"
        "assert L.Lexicon.installed() is not None"
    )
    run([str(py), "-I", "-c", code], cwd=empty)
    for entry in ("gukhan", "gukhan-lexicon-build", "gukhan-regress"):
        exe = bindir / (entry + (".exe" if sys.platform == "win32" else ""))
        run([str(exe), "--help"], cwd=empty)
    print("  smoke test passed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", type=Path, help="work in this (new or empty) folder and keep it")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        work = args.keep or Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        try:
            print("== gukhan")
            code = build(ROOT, work / "dist-code")
            print("== gukhan-lexicon (staged from a tiny hand-written lexicon)")
            src = work / "lexicon-build"
            src.mkdir()
            (src / "lexicon.tsv").write_text(HEADER + ROWS, encoding="utf-8")
            (src / "chars.tsv").write_text("# hanja\treadings\n烽\t봉\n燧\t수\n", encoding="utf-8")
            (src / "manifest.json").write_text(
                '{"licence": "CC-BY-SA-4.0", "notice": "dry run", "sources": {}}', "utf-8"
            )
            sys.path.insert(0, str(ROOT / "scripts"))
            import package_lexicon

            staged = work / "gukhan-lexicon"
            if package_lexicon.main([str(src), "--version", "0.0.0", "-o", str(staged)]) != 0:
                raise DryRunError("package_lexicon refused the dry-run lexicon")
            lex = build(staged, work / "dist-lexicon")
            print("== twine check")
            run([sys.executable, "-m", "twine", "check", "--strict", *map(str, code + lex)])
            print("== contents")
            for f in code:
                inspect(f, ("LICENSE", "NOTICE", "sample_lexicon.tsv") if f.suffix == ".whl" else ("LICENSE", "NOTICE"))
            for f in lex:
                inspect(f, ("NOTICE", "lexicon.tsv", "manifest.json"))
            print("== clean install and smoke test")
            smoke([f for f in code + lex if f.suffix == ".whl"], work)
        except DryRunError as e:
            print(f"release dry run FAILED / 豫行 失敗: {e}", file=sys.stderr)
            return 1
    print("release dry run passed; nothing was published / 豫行 通過, 아무것도 올리지 않았습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
