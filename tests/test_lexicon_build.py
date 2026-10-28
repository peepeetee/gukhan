# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

from gukhan.lexicon_build import stdict, unihan
from gukhan.lexicon_build.cli import main
from gukhan.lexicon_build.hangul import initial_sound_variants

FIX = Path(__file__).parent / "fixtures"


def test_initial_sound_variants():
    assert "이" in initial_sound_variants("리")
    assert "노" in initial_sound_variants("로")
    assert "여" in initial_sound_variants("녀")
    assert initial_sound_variants("가") == {"가"}


def test_align_mixed_and_phrase():
    assert stdict.align("책상다리", "冊床--") == "冊床다리"
    assert stdict.align("작전 계획", "作戰計劃") == "作戰 計劃"
    assert stdict.align("전기", "電氣氣") is None
    assert stdict.align("전기", "電") is None


def test_unihan_fixture():
    readings, version = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    assert version == "16.0.0"
    assert readings["理"] == ["리"]


def test_parse_with_validation():
    readings, _ = unihan.read_khangul(FIX / "Unihan_Readings.txt")
    entries, rejects, stats = stdict.parse(FIX / "stdict_sample.xml", readings)
    forms = {(e.hangul, e.hanja) for e in entries}
    assert ("전기", "電氣") in forms and ("전기", "傳記") in forms and ("전기", "前期") in forms
    assert ("책상다리", "冊床다리") in forms
    assert ("작전 계획", "作戰 計劃") in forms
    assert ("이론", "理論") in forms  # 頭音法則: 理 reads 리, written 이
    assert not any(e.hangul == "사과" for e in entries)  # 고유어 skipped
    reasons = {r.hangul: r.reason for r in rejects}
    assert "nawn" not in reasons
    assert "align" in reasons["나쁜"]
    assert "reads" in reasons["오류"]
    assert stats.items == 9 and stats.rejected == 2
    assert next(e for e in entries if e.hanja == "電氣").sense.startswith("물질")


def test_cli_builds_deterministic_outputs(tmp_path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    for out in (out1, out2):
        rc = main(
            ["--stdict", str(FIX / "stdict_sample.xml"), "--unihan", str(FIX / "Unihan_Readings.txt"), "-o", str(out)]
        )
        assert rc == 0
    assert (out1 / "lexicon.tsv").read_bytes() == (out2 / "lexicon.tsv").read_bytes()
    m = json.loads((out1 / "manifest.json").read_text(encoding="utf-8"))
    assert m["licence"] == "CC-BY-SA-2.0-KR"
    assert m["sources"]["stdict"]["sha256"] == m["sources"]["stdict"]["sha256"]
    assert m["sources"]["unihan"]["version"] == "16.0.0"
    assert m["counts"]["entries"] == 6
    assert m["outputs"]["lexicon"]["sha256"]
    text = (out1 / "lexicon.tsv").read_text(encoding="utf-8")
    assert text.startswith("# gukhan lexicon")
    assert "전기\t電氣\t명사\tstdict:1001" in text
    assert (out1 / "chars.tsv").exists()


def test_cli_rejects_wrong_schema(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<root><thing>x</thing></root>", encoding="utf-8")
    assert main(["--stdict", str(bad), "-o", str(tmp_path / "o")]) == 2
