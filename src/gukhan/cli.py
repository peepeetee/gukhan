# SPDX-License-Identifier: Apache-2.0
"""``gukhan``: convert a Hangul text file to 國漢文混用體."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from . import __version__, report, rules
from .convert import Converter
from .lexicon import Lexicon
from .overrides import Overrides


def _err(msg: str) -> int:
    print(f"gukhan: {msg}", file=sys.stderr)
    return 2


def _read(path: Path) -> str:
    """The file's text exactly as written: UTF-8, line endings untouched (no CRLF → LF rewrite)."""
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _read_error(path: Path, e: Exception) -> str:
    if isinstance(e, UnicodeDecodeError):
        return f"{path}: UTF-8이 아닙니다 / not UTF-8 text; save it as UTF-8 (for CP949: iconv -f cp949 -t utf-8)"
    return f"{path}: {e.strerror or e}"


def _utf8_streams() -> None:
    """Redirected output is UTF-8 on every platform (Windows would use cp949 and fail on rare Hanja)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace", newline="" if stream is sys.stdout else None)
            except (ValueError, OSError):  # a stream that has already been read from or is closed
                pass


def _dist_version(name: str) -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def version_text() -> str:
    """What a bug report needs: gukhan, the analyser and its model type, and the installed lexicon."""
    from .analyser import KIWI_MODEL_TYPE

    return (
        f"gukhan {__version__}\n"
        f"kiwipiepy {_dist_version('kiwipiepy')}, model {KIWI_MODEL_TYPE}\n"
        f"gukhan-lexicon {_dist_version('gukhan-lexicon')}"
    )


class _Version(argparse.Action):
    """Like ``action="version"`` but keeps the line breaks (argparse would reflow them)."""

    def __call__(self, parser, namespace, values, option_string=None):
        sys.stdout.write(version_text() + "\n")
        parser.exit()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gukhan",
        description="한글 文章을 國漢文混用體로 變換합니다 / Convert Hangul text to Hangul-Hanja mixed script.",
    )
    ap.add_argument(
        "input",
        nargs="*",
        type=Path,
        help="input file (Markdown or plain text); several need --in-place or --out-dir; omit with --stdin",
    )
    ap.add_argument("--stdin", action="store_true", help="read text from standard input / 標準 入力에서 읽기")
    ap.add_argument("-o", "--output", type=Path, help="write converted text here instead of stdout")
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite each input with its conversion; the original is first kept as FILE.bak "
        "(see --backup-suffix, --no-backup) / 原本은 FILE.bak 으로 保存",
    )
    ap.add_argument("--backup-suffix", default=".bak", help="suffix of the backup --in-place keeps (default .bak)")
    ap.add_argument("--no-backup", action="store_true", help="with --in-place: do not keep the original")
    ap.add_argument(
        "--out-dir", type=Path, help="write each converted file into this directory (created) under its own name"
    )
    ap.add_argument(
        "--lexicon", type=Path, help="lexicon.tsv or its directory (default: installed gukhan-lexicon, else a sample)"
    )
    ap.add_argument("--overrides", type=Path, action="append", default=[], help="override file; repeatable, later wins")
    ap.add_argument("--report", type=Path, help="write flagged words and review list (.tsv or .md by extension)")
    ap.add_argument("--mark", action="store_true", help="show flagged words inline as 전기{電氣|傳記}")
    ap.add_argument("--review-all", action="store_true", help="also list every common noun with no entry")
    ap.add_argument(
        "--min-weight",
        type=int,
        default=None,
        help="flag a lone candidate whose weight is below this (default 12 on a weighted lexicon, 0 otherwise)",
    )
    ap.add_argument(
        "--rules",
        default="default",
        help="evidence rules that narrow a flag's candidates: default, all, none, or names "
        f"({', '.join(sorted(rules.ALL))}), comma separated; see docs/PLAN.md §5",
    )
    ap.add_argument("--version", action=_Version, nargs=0, help="show the versions of gukhan, Kiwi and the lexicon")
    return ap


def review_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="gukhan review",
        description="flag된 낱말의 漢字를 文脈 속에서 직접 고릅니다 / Pick the Hanja for flagged words in context. "
        "Answers are appended to the override file; nothing is guessed.",
    )
    ap.add_argument("input", type=Path, help="the same file you convert")
    ap.add_argument(
        "--overrides", type=Path, required=True, help="override file to read and append to (created if absent)"
    )
    ap.add_argument(
        "--lexicon", type=Path, help="lexicon.tsv or its directory (default: installed gukhan-lexicon, else a sample)"
    )
    ap.add_argument("--rules", default="default", help="same as for conversion")
    ap.add_argument("--include-review", action="store_true", help="also ask about words with no entry (type the Hanja)")
    args = ap.parse_args(argv)
    from .review import Reviewer

    if not args.input.is_file():
        return _err(f"file을 찾을 수 없습니다 / file not found: {args.input}")
    try:
        text = _read(args.input)
    except (OSError, UnicodeDecodeError) as e:
        return _err(_read_error(args.input, e))
    try:
        lexicon = Lexicon.load(args.lexicon) if args.lexicon else (Lexicon.installed() or Lexicon.sample())
        overrides = Overrides.load(args.overrides) if args.overrides.exists() else Overrides()
        use_rules = rules.parse_rules(args.rules)
    except (OSError, ValueError) as e:
        return _err(str(e))
    conv = Converter(lexicon, overrides, use_rules=use_rules)
    return Reviewer(conv, text, args.overrides, include_review=args.include_review).run()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    _utf8_streams()
    if argv and argv[0] == "review":
        return review_main(argv[1:])
    args = build_parser().parse_intermixed_args(argv)
    if args.stdin == bool(args.input):
        return _err("入力 file 하나 또는 --stdin 을 指定하세요 / give one input file or --stdin")
    jobs = _plan(args)
    if isinstance(jobs, int):
        return jobs
    texts: dict[Path | None, str] = {}
    reading = Path("<stdin>")
    try:
        if args.stdin:
            texts[None] = sys.stdin.buffer.read().decode("utf-8") if hasattr(sys.stdin, "buffer") else sys.stdin.read()
        else:
            for path, _ in jobs:
                reading = path
                texts[path] = _read(path)
    except (OSError, UnicodeDecodeError) as e:
        return _err(_read_error(reading, e))

    try:
        lexicon = Lexicon.load(args.lexicon) if args.lexicon else Lexicon.installed()
    except (OSError, ValueError) as e:
        return _err(f"辭典을 읽을 수 없습니다 / cannot read lexicon: {e}")
    overrides = Overrides()
    for p in args.overrides:
        try:
            overrides.update(Overrides.load(p))
        except (OSError, ValueError) as e:
            return _err(f"override file 誤謬 / override file error ({p}): {e}")

    if lexicon is None:
        lexicon = Lexicon.sample()
        print(
            "注意: 內藏 sample 辭典을 使用합니다. 實際 變換에는 gukhan-lexicon 을 設置하거나 --lexicon 을 指定하세요 / "
            "Note: using the bundled sample lexicon; install gukhan-lexicon or pass --lexicon for real use.",
            file=sys.stderr,
        )
    try:
        use_rules = rules.parse_rules(args.rules)
    except ValueError as e:
        return _err(str(e))
    conv = Converter(
        lexicon,
        overrides if args.overrides else None,
        review_all=args.review_all,
        min_weight=args.min_weight,
        use_rules=use_rules,
    )

    status = 0
    for path, target in jobs if not args.stdin else [(None, args.output)]:
        text = texts[path]
        result = conv.convert(text, mark=args.mark)
        try:
            if args.in_place and path is not None:
                if not args.no_backup:
                    shutil.copy2(path, _backup_path(path, args.backup_suffix))
                _write_atomic(path, result.text)
            elif target is not None:
                if args.out_dir:
                    target.parent.mkdir(parents=True, exist_ok=True)
                _write(target, result.text)
            else:
                sys.stdout.write(result.text)
            if args.report:
                suffix = args.report.suffix.lower()
                body = report.to_markdown(text, result) if suffix == ".md" else report.to_tsv(text, result)
                _write(args.report, body)
        except OSError as e:
            print(f"gukhan: 쓸 수 없습니다 / cannot write: {e.filename or path} {e.strerror or e}", file=sys.stderr)
            status = 2
            continue
        s = report.summary(result)
        print(
            (f"{path}: " if len(jobs) > 1 else "")
            + f"變換 {s['converted']} · flag {s['flagged']} · 檢討 {s['review']} · 維持 {s['kept']}"
            + (f" → {args.report}" if args.report else ""),
            file=sys.stderr,
        )
    return status


def _backup_path(path: Path, suffix: str) -> Path:
    return path.with_name(path.name + suffix)


def _write_atomic(path: Path, text: str) -> None:
    """Replace ``path`` in one step, so an interrupted run never leaves half a file."""
    tmp = path.with_name(f".{path.name}.gukhan-tmp")
    try:
        _write(tmp, text)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _plan(args: argparse.Namespace) -> list[tuple[Path, Path | None]] | int:
    """Check the options and inputs together before anything is read or written.

    Returns ``(input, output)`` pairs (output None: stdout, or in place), or an exit status.
    """
    many = len(args.input) > 1
    if args.in_place and args.out_dir:
        return _err("--in-place 와 --out-dir 는 함께 쓸 수 없습니다 / --in-place and --out-dir are exclusive")
    if (args.in_place or args.out_dir) and args.output:
        return _err("-o 는 --in-place, --out-dir 와 함께 쓸 수 없습니다 / -o cannot be combined with them")
    if (args.in_place or args.out_dir) and args.stdin:
        return _err("--stdin 은 --in-place, --out-dir 와 함께 쓸 수 없습니다 / --stdin cannot be combined with them")
    if (args.no_backup or args.backup_suffix != ".bak") and not args.in_place:
        return _err("--no-backup, --backup-suffix 는 --in-place 에서만 / only meaningful with --in-place")
    if many and not (args.in_place or args.out_dir):
        return _err(
            "파일이 여럿이면 --in-place 또는 --out-dir 이 必要합니다 / several files need --in-place or --out-dir "
            "(gukhan never overwrites without an explicit flag)"
        )
    if many and args.report:
        return _err("--report 는 파일 하나일 때만 / --report works with a single input file")
    if args.in_place and not args.no_backup and not args.backup_suffix:
        return _err("--backup-suffix 가 비었습니다 / the backup suffix is empty; use --no-backup to skip backups")
    jobs: list[tuple[Path, Path | None]] = []
    seen: dict[Path, Path] = {}
    for path in args.input:
        if not path.is_file():
            return _err(f"file을 찾을 수 없습니다 / file not found: {path}")
        key = path.resolve()
        if key in seen:
            return _err(f"같은 file이 두 번 있습니다 / listed twice: {path}")
        seen[key] = path
        target = None
        if args.out_dir:
            target = args.out_dir / path.name
            if target.resolve() == key:
                return _err(f"出力이 入力을 덮어씁니다 / output would overwrite its input: {path}; use --in-place")
        if args.in_place and not args.no_backup and _backup_path(path, args.backup_suffix).exists():
            return _err(
                f"백업이 이미 있습니다 / backup already exists: {_backup_path(path, args.backup_suffix)} "
                "(move it away, or choose --backup-suffix / --no-backup)"
            )
        jobs.append((path, target if args.out_dir else args.output))
    if args.out_dir:
        names = [t.name for _, t in jobs if t]
        if len(names) != len(set(names)):
            return _err("--out-dir 에서 file 이름이 겹칩니다 / two inputs have the same file name")
        for _, t in jobs:
            if t and t.exists():
                return _err(f"出力 file이 이미 있습니다 / output exists, not overwriting: {t}")
    return jobs


if __name__ == "__main__":
    sys.exit(main())
