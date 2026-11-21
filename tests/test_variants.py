# SPDX-License-Identifier: Apache-2.0

import json
import shutil
from pathlib import Path

import pytest

from gukhan.lexicon_build import unihan
from gukhan.lexicon_build.cli import main as build_main
from gukhan.regress import prepare as prep
from gukhan.regress import score as sc
from gukhan.regress.cli import main
from gukhan.regress.variants import Variants, load_variants

FIX = Path(__file__).parent / "fixtures"


def test_read_variants_pairs_kinds_and_tags():
    pairs = unihan.read_variants(FIX / "Unihan_Variants.txt")
    assert pairs == [
        ("体", "體", "z"),  # z wins over semantic
        ("嘆", "歎", "semantic"),  # one pair, smaller code point first, tags after < dropped
        ("絕", "絶", "z"),
        ("骨", "體", "semantic"),
    ]  # a character that lists itself, and other kinds (kSimplifiedVariant), are ignored


def test_read_variants_is_empty_without_the_file(tmp_path):
    assert unihan.read_variants(FIX / "Unihan_Readings.txt") == []
    (tmp_path / "Unihan_Readings.txt").write_text("U+4E00\tkHangul\t일:0E\n", encoding="utf-8")
    assert unihan.read_variants(tmp_path) == []


def test_read_variants_from_a_zip(tmp_path):
    import zipfile

    z = tmp_path / "Unihan.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(FIX / "Unihan_Variants.txt", "Unihan_Variants.txt")
        zf.write(FIX / "Unihan_Readings.txt", "Unihan_Readings.txt")
    assert ("絕", "絶", "z") in unihan.read_variants(z)


def test_variants_fold_group_and_transitivity():
    v = Variants([("絕", "絶"), ("絶", "X"), ("歎", "嘆")])
    assert v.fold("絕對") == v.fold("絶對") == v.fold("X對")
    assert v.fold("痛歎") == v.fold("痛嘆")
    assert v.group("絕")[0] == "絕" and set(v.group("絕")) == {"絕", "絶", "X"}
    assert v.group("山") == ["山"] and v.fold("山") == "山" and len(v) == 5
    assert v.fold("强") == "強"  # the built-in folds still apply


def test_load_variants_kinds(tmp_path):
    out = tmp_path / "b"
    assert (
        build_main(["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(_unihan_dir(tmp_path)), "-o", str(out)])
        == 0
    )
    both = load_variants(out)
    z_only = load_variants(out / "variants.tsv", ["z"])
    assert both.fold("痛歎") == both.fold("痛嘆")
    assert z_only.fold("痛歎") != z_only.fold("痛嘆") and z_only.fold("絕") == z_only.fold("絶")
    with pytest.raises(ValueError, match="semantc"):
        load_variants(out, ["semantc"])


def _unihan_dir(tmp_path):
    d = tmp_path / "unihan"
    d.mkdir()
    shutil.copy(FIX / "Unihan_Readings.txt", d)
    shutil.copy(FIX / "Unihan_Variants.txt", d)
    return d


def test_builder_writes_variants_tsv_and_manifest(tmp_path):
    out = tmp_path / "b"
    assert (
        build_main(["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(_unihan_dir(tmp_path)), "-o", str(out)])
        == 0
    )
    lines = (out / "variants.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#") and "絕\t絶\tz" in lines
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["counts"]["variant_pairs"] == 4 and m["outputs"]["variants"]["sha256"]
    # a plain Unihan_Readings.txt has no variants: no file, and no count
    out2 = tmp_path / "c"
    assert (
        build_main(
            ["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(FIX / "Unihan_Readings.txt"), "-o", str(out2)]
        )
        == 0
    )
    assert not (out2 / "variants.tsv").exists()


def _score(output: str, gold: str, fold=sc.fold_variants) -> sc.Tally:
    t = sc.Tally()
    sc.score_item(sc.Item("1", "s", "x", gold), output, t, (), fold)
    return t


def test_score_counts_a_variant_as_right_only_with_the_table():
    v = Variants([("絕", "絶"), ("歎", "嘆")])
    assert _score("絶對 痛嘆", "絕對 痛歎").wrong == 2  # the built-in folds do not know them
    t = _score("絶對 痛嘆", "絕對 痛歎", v.fold)
    assert (t.right, t.wrong) == (2, 0)
    assert _score("絶對", "絕對").chars_wrong == 1 and _score("絶對", "絕對", v.fold).chars_wrong == 0


def test_score_still_counts_a_real_error_with_the_table():
    v = Variants([("絕", "絶")])
    assert _score("電氣", "電器", v.fold).wrong == 1


def test_prepare_matches_a_variant_glyph_run(tmp_path):
    v = Variants([("絕", "絶")])
    words = prep.fold_words({"絶對": "절대", "對": "대"}, v)
    chars = {"絕": ["절"], "絶": ["절"], "對": ["대"]}
    # 絕對 is the word 絶對; without the table the run is read character by character (and 絕 loses the initial rule)
    assert prep.prepare("絕對", chars, {"絶對": "절대"}).hangul == "절대"
    assert prep.prepare("絕對", {"絕": ["절"], "對": ["대"]}, words, v).hangul == "절대"
    # a character without a reading takes the reading of its variant
    assert prep.prepare("絕", {"絶": ["절"]}, {}, v).hangul == "절"
    assert prep.prepare("絕", {"絶": ["절"]}, {}).unknown == ["絕"]


def test_cli_score_with_variants(tmp_path, capsys):
    items = tmp_path / "items.tsv"
    items.write_text("# id\tsource\thangul\tmixed\ns-1\ts\t전기\t電氣\ns-2\ts\t전기\t電氣\n", encoding="utf-8")
    lex = tmp_path / "lexicon.tsv"
    lex.write_text("# gukhan lexicon\n", encoding="utf-8")
    table = tmp_path / "variants.tsv"
    table.write_text("# header\n氣\t气\tz\n", encoding="utf-8")
    assert main(["score", str(items), "--variants", str(table), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["variants"] == f"{table} (z,semantic)"
    assert main(["score", str(items), "--variants", str(tmp_path / "none.tsv")]) == 2
    assert main(["score", str(items), "--variants", str(table), "--variant-kinds", "bogus"]) == 2
