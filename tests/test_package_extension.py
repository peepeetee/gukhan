# SPDX-License-Identifier: Apache-2.0
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "package_extension", Path(__file__).parent.parent / "scripts" / "package_extension.py"
)
pkg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pkg)

LEXICON = "# header\n연구\t研究\t명사\tstdict:1\t조사하는 일\t3\t1\t7\n전기\t電氣\t명사\tstdict:2\t에너지\t0\t0\t0\n"


def make_dictionary(tmp_path):
    (tmp_path / "lexicon.tsv").write_text(LEXICON, encoding="utf-8")
    manifest = {"licence": "CC-BY-SA-2.0-KR", "notice": "credit", "outputs": {"lexicon": {"sha256": "stale"}}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_strip_definitions_keeps_ranking_columns():
    lines = pkg.strip_definitions(LEXICON).splitlines()
    assert lines[0] == "# header"
    assert lines[1] == "연구\t研究\t\t\t\t3\t1\t7"


def test_package_with_dictionary(tmp_path):
    out = tmp_path / "x.xpi"
    assert pkg.main([str(out), "--dictionary", str(make_dictionary(tmp_path)), "--no-definitions"]) == 0
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert {"manifest.json", "LICENSE.txt", "dictionary/lexicon.tsv", "dictionary/NOTICE.txt"} <= names
        assert not any(n.endswith(("test.mjs", "smoke.cjs", "README.md")) for n in names)
        data = z.read("dictionary/lexicon.tsv")
        meta = json.loads(z.read("dictionary/manifest.json"))
    assert meta["outputs"]["lexicon"]["sha256"] == hashlib.sha256(data).hexdigest()  # recomputed for the stripped file
    assert "omits" in meta["notice"]


def test_package_without_dictionary(tmp_path):
    out = tmp_path / "x.xpi"
    assert pkg.main([str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert not any(n.startswith("dictionary/") for n in z.namelist())


def test_chrome_target_manifest(tmp_path):
    out = tmp_path / "c.zip"
    assert pkg.main([str(out), "--target", "chrome"]) == 0
    with zipfile.ZipFile(out) as z:
        m = json.loads(z.read("manifest.json"))
    assert m["manifest_version"] == 3
    assert "browser_specific_settings" not in m and "host_permissions" not in m
    assert "scripts" not in m["background"] and m["background"]["service_worker"] == "worker.js"
    assert m["content_scripts"][0]["matches"] == ["http://*/*", "https://*/*"]


def test_firefox_target_keeps_gecko_keys(tmp_path):
    out = tmp_path / "f.xpi"
    assert pkg.main([str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert "browser_specific_settings" in json.loads(z.read("manifest.json"))


def test_strip_definitions_does_not_split_rows_at_unicode_line_separators():
    text = "연구\t研究\t명사\ts\ta b\u0085c\t3\n"
    assert pkg.strip_definitions(text) == "연구\t研究\t\t\t\t3\n"
