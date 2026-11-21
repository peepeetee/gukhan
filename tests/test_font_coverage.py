# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_font_coverage", Path(__file__).parent.parent / "scripts" / "check_font_coverage.py"
)
cfc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cfc)


def test_only_ideographs_count_not_punctuation_or_jamo(tmp_path):
    items = tmp_path / "items.tsv"
    items.write_text(
        "# id\tsource\thangul\tmixed\n"
        "1\ts\t대한민국ㆍ헌법\t大韓民國ㆍ憲法｢\n"  # arae-a, a corner bracket and Extension B/G characters follow
        "2\ts\t희귀\t\U00020000\U00030000\n",
        encoding="utf-8",
    )
    counts = cfc.items_hanja([items])
    assert set(counts) == set("大韓民國憲法") | {"\U00020000", "\U00030000"}
    assert "ㆍ" not in counts and "｢" not in counts


def test_lexicon_hanja_reads_the_second_column(tmp_path):
    lexicon = tmp_path / "lexicon.tsv"
    lexicon.write_text("# hangul\thanja\n전기\t電氣\t명사\ns\n사랑\t사랑\n", encoding="utf-8")
    assert set(cfc.lexicon_hanja(lexicon)) == set("電氣")


def test_one_source_of_characters_is_required(capsys):
    assert cfc.main(["x.otf"]) == 2  # neither --lexicon nor --items (or fontTools missing): refused
