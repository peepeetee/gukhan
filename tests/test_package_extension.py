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


ROOT = Path(__file__).resolve().parent.parent


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


def test_package_with_character_list(tmp_path):
    d = make_dictionary(tmp_path)
    (d / "char-info.tsv").write_text("# hanja\treadings\tmeaning\n國\t국\tcountry, nation\n", encoding="utf-8")
    out = tmp_path / "x.xpi"
    assert pkg.main([str(out), "--dictionary", str(d)]) == 0
    with zipfile.ZipFile(out) as z:
        info = z.read("dictionary/char-info.tsv")
        meta = json.loads(z.read("dictionary/manifest.json"))
    assert meta["outputs"]["char_info"] == {
        "name": "char-info.tsv",
        "bytes": len(info),
        "sha256": hashlib.sha256(info).hexdigest(),  # what the options page checks before importing it
    }
    plain = tmp_path / "y.xpi"
    (d / "char-info.tsv").unlink()
    assert pkg.main([str(plain), "--dictionary", str(d)]) == 0
    with zipfile.ZipFile(plain) as z:
        assert "dictionary/char-info.tsv" not in z.namelist()
        assert "char_info" not in json.loads(z.read("dictionary/manifest.json"))["outputs"]


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
    assert "content_scripts" not in m  # registered per site at runtime, never for every site
    assert m["optional_host_permissions"] == ["http://*/*", "https://*/*"]


def test_no_build_has_access_to_any_site_at_install():
    """Hosts are granted one at a time by the reader (popup toggle); the manifest asks for none up front."""
    m = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    assert "host_permissions" not in m and "content_scripts" not in m
    assert sorted(m["permissions"]) == ["activeTab", "scripting", "storage", "unlimitedStorage"]
    assert m["optional_host_permissions"] == ["http://*/*", "https://*/*"]


def test_firefox_target_keeps_gecko_keys(tmp_path):
    out = tmp_path / "f.xpi"
    assert pkg.main([str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert "browser_specific_settings" in json.loads(z.read("manifest.json"))


def test_strip_definitions_does_not_split_rows_at_unicode_line_separators():
    text = "연구\t研究\t명사\ts\ta b\u0085c\t3\n"
    assert pkg.strip_definitions(text) == "연구\t研究\t\t\t\t3\n"


def test_strip_definitions_keeps_the_domain_column():
    text = "작전\t作戰\t명사\tlaw:가법\t뜻\t0\t0\t0\t법률\n"
    assert pkg.strip_definitions(text) == "작전\t作戰\t\t\t\t0\t0\t0\t법률\n"


def test_extension_version_is_semver_and_documented():
    import re

    manifest = json.loads((pkg.EXT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    # The extension is on its own version track (docs/RELEASE.md), but every place that names a build must follow it,
    # and once the code is released its major.minor may not be behind the code's.
    assert f"gukhan-chrome-{version}.zip" in (pkg.ROOT / "docs" / "chrome-web-store.md").read_text(encoding="utf-8")
    code = re.search(r'^version = "([\d.]+)"', (pkg.ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    assert code
    if code.group(1) != "0.0.0":
        assert tuple(map(int, version.split(".")[:2])) >= tuple(map(int, code.group(1).split(".")[:2]))
