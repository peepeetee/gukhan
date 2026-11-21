# SPDX-License-Identifier: Apache-2.0
"""Flag user-facing text that lacks its Korean or its English half.

    python scripts/check_bilingual.py          # exit 1 and list the gaps

A message is bilingual when it holds Korean (Hangul or Hanja, so mixed script counts) and at least
one English word. Checked, so a new message cannot be added in one language only:

- Python (``src/``): the text of ``raise X(...)``, ``print(..., file=...)``, ``parser.error(...)``
  and the ``help`` / ``description`` / ``epilog`` of argparse. Strings shorter than 12 letters
  (a program-name prefix such as ``gukhan: ``) are ignored.
- JavaScript (``extension/``): ``new Error('…')`` and ``….textContent = '…'`` string literals.
- Markdown for readers (README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, the privacy policy, the
  extension and regression READMEs, the PR template): every ``#``/``##`` section with some English
  prose (code blocks excluded) must also hold Korean. Maintainer notes (docs/PLAN.md, RELEASE.md …)
  are not checked section by section.
- GitHub issue forms: ``name``, ``description``, ``label``, ``placeholder``, ``about`` values.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KOREAN = re.compile(r"[가-힣一-鿿]")
ENGLISH = re.compile(r"[A-Za-z]{3,}")
LETTERS = re.compile(r"[A-Za-z가-힣一-鿿]")
FENCE = re.compile(r"(?ms)^```.*?^```")
READER_DOCS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "docs/privacy.md",
    "extension/README.md",
    "tests/regression/README.md",
    ".github/pull_request_template.md",
)
MIN_LETTERS = 12  # shorter strings are prefixes and labels, not messages
MIN_PROSE_WORDS = 8


def is_bilingual(text: str) -> bool:
    return bool(KOREAN.search(text)) and bool(ENGLISH.search(text))


def is_message(text: str) -> bool:
    """Prose, not a prefix or a label: enough letters and a space between two words."""
    text = re.sub(r"\$\{[^}]*\}", "", text)  # JavaScript template placeholders
    return len(LETTERS.findall(text)) >= MIN_LETTERS and bool(re.search(r"\w\s+\w", text))


def _string_parts(node: ast.AST) -> str:
    return " ".join(n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str))


def python_gaps(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    gaps = []
    for node in ast.walk(tree):
        target: ast.AST | None = None
        kind = ""
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            target, kind = node.exc, "raise"
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "print" and any(k.arg == "file" for k in node.keywords):
                target, kind = node, "stderr"
            elif isinstance(f, ast.Attribute) and f.attr == "error":
                target, kind = node, "error"
            elif isinstance(f, ast.Attribute) and f.attr in ("add_argument", "add_parser", "add_subparsers"):
                helps = [k.value for k in node.keywords if k.arg in ("help", "description", "epilog")]
                if helps:
                    target, kind = helps[0], "help"
            elif isinstance(f, ast.Attribute) and f.attr == "ArgumentParser":
                helps = [k.value for k in node.keywords if k.arg in ("description", "epilog")]
                if helps:
                    target, kind = helps[0], "help"
        if target is None:
            continue
        text = _string_parts(target)
        if is_message(text) and not is_bilingual(text):
            gaps.append(f"{path.relative_to(ROOT)}:{node.lineno} [{kind}] {_missing(text)}: {text.strip()[:90]!r}")
    return gaps


def _missing(text: str) -> str:
    return "no Korean" if not KOREAN.search(text) else "no English"


JS_MESSAGE = re.compile(r"""(?:new Error\(|\.textContent\s*=\s*)\s*(['"`])((?:\\.|(?!\1).)*)\1""")


def js_gaps(path: Path) -> list[str]:
    gaps = []
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        for m in JS_MESSAGE.finditer(line):
            text = m.group(2)
            if is_message(text) and not is_bilingual(re.sub(r"\$\{[^}]*\}", "", text)):
                gaps.append(f"{path.relative_to(ROOT)}:{n} [js] {_missing(text)}: {text[:90]!r}")
    return gaps


def markdown_gaps(path: Path) -> list[str]:
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    gaps = []
    for section in re.split(r"(?m)^(?=#{1,2} )", text):
        words = ENGLISH.findall(section)
        if section.startswith("## English"):
            continue  # the English half of a two-halves page; its Korean half follows
        if len(words) >= MIN_PROSE_WORDS and not KOREAN.search(section):
            title = section.split("\n", 1)[0][:60]
            gaps.append(f"{path.relative_to(ROOT)} [section] no Korean ({len(words)} English words): {title!r}")
    return gaps


YAML_FIELD = re.compile(r"^\s*(?:-\s*)?(name|description|label|placeholder|about|value):\s*(.+?)\s*$")


def yaml_gaps(path: Path) -> list[str]:
    gaps = []
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = YAML_FIELD.match(line)
        if m and is_message(m.group(2)) and not is_bilingual(m.group(2)):
            gaps.append(f"{path.relative_to(ROOT)}:{n} [form] {_missing(m.group(2))}: {m.group(2)[:90]!r}")
    return gaps


def find_gaps(root: Path = ROOT) -> list[str]:
    gaps: list[str] = []
    for p in sorted((root / "src").rglob("*.py")):
        gaps += python_gaps(p)
    for p in sorted((root / "extension").glob("*.js")):
        gaps += js_gaps(p)
    for name in READER_DOCS:
        gaps += markdown_gaps(root / name)
    for p in sorted((root / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
        gaps += yaml_gaps(p)
    return gaps


def main() -> int:
    gaps = find_gaps()
    for g in gaps:
        print(g)
    if gaps:
        print(
            f"\n{len(gaps)} text(s) lack Korean or English / 韓國語 또는 英語가 빠진 글 {len(gaps)}個", file=sys.stderr
        )
        return 1
    print("every checked message and section has both Korean and English / 모두 韓英 對譯이 있습니다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
