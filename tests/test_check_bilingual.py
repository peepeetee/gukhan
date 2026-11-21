# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_bilingual", Path(__file__).parent.parent / "scripts" / "check_bilingual.py"
)
cb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cb)


def test_repository_messages_are_bilingual():
    assert cb.find_gaps() == []


def test_is_bilingual():
    assert cb.is_bilingual("파일을 찾을 수 없습니다 / file not found")
    assert cb.is_bilingual("入力 file not found")  # Hanja counts as Korean
    assert not cb.is_bilingual("file not found")
    assert not cb.is_bilingual("파일을 찾을 수 없습니다")


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_python_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "ROOT", tmp_path)
    p = write(
        tmp_path,
        "src/m.py",
        "import sys\n"
        "def f(ap):\n"
        "    print('gukhan: ', file=sys.stderr)\n"
        "    print('cannot write the file here', file=sys.stderr)\n"
        "    print('쓸 수 없습니다 / cannot write the file', file=sys.stderr)\n"
        "    ap.add_argument('--x', help='only an English help text')\n"
        "    raise ValueError('빈 파일입니다 비어 있는 파일은 안 됩니다')\n",
    )
    gaps = sorted(cb.python_gaps(p), key=lambda g: int(g.split(":")[1].split()[0]))
    assert len(gaps) == 3
    assert "[stderr] no Korean" in gaps[0] and "[help] no Korean" in gaps[1] and "[raise] no English" in gaps[2]


def test_js_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "ROOT", tmp_path)
    p = write(
        tmp_path,
        "extension/a.js",
        "throw new Error('Empty dictionary here');\n"
        "throw new Error('빈 사전입니다 / Empty dictionary');\n"
        "el.textContent = `${a}  ${b}`;\n",
    )
    assert len(cb.js_gaps(p)) == 1


def test_markdown_and_yaml_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "ROOT", tmp_path)
    prose = " ".join(["word"] * 12)
    md = write(tmp_path, "a.md", f"# A\n{prose}\n\n## B / 二\n{prose}\n\n```\n{prose}\n```\n## English\n{prose}\n")
    gaps = cb.markdown_gaps(md)
    assert len(gaps) == 1 and "# A" in gaps[0]
    form = write(tmp_path, "f.yml", "name: Bug / 오류\ndescription: A crash or a wrong file here\n")
    assert len(cb.yaml_gaps(form)) == 1
