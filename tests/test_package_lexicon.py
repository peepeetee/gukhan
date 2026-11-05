# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

from gukhan.lexicon import Lexicon

SPEC = importlib.util.spec_from_file_location(
    "package_lexicon", Path(__file__).parent.parent / "scripts" / "package_lexicon.py"
)
pl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pl)

HEADER = "# gukhan lexicon\tlicence=CC-BY-SA-4.0\tmanifest=manifest.json\n# hangul\thanja\tpos\tsource\tsense\tweight\n"
ROW = "전기\t電氣\t명사\tstdict:1\t에너지의 하나\t3\n"


def make_build(tmp_path, *, licence="CC-BY-SA-4.0", rows=ROW, extra=None, sources=None):
    src = tmp_path / "build"
    src.mkdir()
    (src / "lexicon.tsv").write_text(HEADER.replace("CC-BY-SA-4.0", licence) + rows, encoding="utf-8")
    (src / "chars.tsv").write_text("# hanja\treadings\n電\t전:E\n", encoding="utf-8")
    manifest = {
        "licence": licence,
        "notice": "credit text",
        "sources": sources or {"stdict": {"path": "C:\\data\\stdict", "files": [{"name": "a.xml", "sha256": "ab"}]}},
    }
    (src / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (src / "rejects.tsv").write_text("x\n", encoding="utf-8")
    for name in extra or ():
        (src / name).write_text("raw", encoding="utf-8")
    return src


def test_stage_ships_only_built_lexicon_and_scrubs_paths(tmp_path):
    out = tmp_path / "pkg"
    assert pl.main([str(make_build(tmp_path)), "--version", "0.1.0", "-o", str(out)]) == 0
    files = {p.name for p in (out / "src" / "gukhan_lexicon" / "data").iterdir()}
    assert files == {"lexicon.tsv", "chars.tsv", "manifest.json"}
    assert 'version = "0.1.0"' in (out / "pyproject.toml").read_text(encoding="utf-8")
    manifest = json.loads((out / "src" / "gukhan_lexicon" / "data" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"]["stdict"]["path"] == "stdict"
    assert manifest["sources"]["stdict"]["files"][0]["sha256"] == "ab"
    assert "credit text" in (out / "NOTICE.txt").read_text(encoding="utf-8")
    assert not list(out.rglob("*.xml"))


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"extra": ["436578.xml"]}, "raw dictionary dumps"),
        ({"extra": ["dump.zip"]}, "raw dictionary dumps"),
        ({"licence": "GPL-3.0"}, "not one of"),
        ({"rows": ROW.replace("에너지의 하나", "<example>에너지</example>")}, "markup"),
        ({"rows": ROW.replace("에너지의 하나", "가" * 201)}, "excerpt over"),
        ({"rows": ""}, "no rows"),
        ({"licence": "CC-BY-SA-2.0-KR", "sources": {"wiktextract": [{"path": "k.jsonl"}]}}, "Wiktionary"),
    ],
)
def test_stage_refuses(tmp_path, capsys, kwargs, message):
    out = tmp_path / "pkg"
    assert pl.main([str(make_build(tmp_path, **kwargs)), "--version", "0.1.0", "-o", str(out)]) == 2
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_licence_header_must_match_manifest(tmp_path, capsys):
    src = make_build(tmp_path)
    text = (src / "lexicon.tsv").read_text(encoding="utf-8").replace("licence=CC-BY-SA-4.0", "licence=CC-BY-SA-2.0-KR")
    (src / "lexicon.tsv").write_text(text, encoding="utf-8")
    assert pl.main([str(src), "--version", "0.1.0", "-o", str(tmp_path / "pkg")]) == 2
    assert "header" in capsys.readouterr().err


def test_installed_lexicon_is_used_when_present(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "gukhan_lexicon", None)  # import fails
    assert Lexicon.installed() is None
    (tmp_path / "lexicon.tsv").write_text(ROW, encoding="utf-8")
    fake = types.SimpleNamespace(lexicon_path=lambda: tmp_path / "lexicon.tsv")
    monkeypatch.setitem(sys.modules, "gukhan_lexicon", fake)
    assert "전기" in Lexicon.installed()
