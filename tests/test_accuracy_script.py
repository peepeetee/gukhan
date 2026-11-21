# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("accuracy", Path(__file__).parent.parent / "scripts" / "accuracy.py")
assert SPEC and SPEC.loader
acc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acc)


def counts(wrong: int, right: int = 10, flagged: int = 5) -> dict[str, int]:
    return {
        "words": right + wrong + flagged,
        "right": right,
        "wrong": wrong,
        "flagged": flagged,
        "partial": 0,
        "over": 0,
    }


def run(sets: dict[str, dict[str, int]]) -> dict[str, object]:
    return {"gukhan": "x", "lexicon_entries": 3, "sets": sets}


def test_compare_shows_changes_new_and_removed_sets():
    base = run({"a": counts(1), "gone": counts(0)})
    head = run({"a": counts(1, right=12), "b": counts(0)})
    table, failures = acc.compare(base, head, 2)
    assert failures == []
    assert "| a | 18 (+2) | 12 (+2) | 1 | 5 | 0 | 0 |" in table
    assert "| b | 15 (new) |" in table and "| gone | removed |" in table


def test_compare_gates_only_held_out_sets_by_the_threshold():
    base = run({"law-heldout": counts(5), "law-tuning": counts(5)})
    worse = run({"law-heldout": counts(8), "law-tuning": counts(50)})  # tuning set may move freely
    table, failures = acc.compare(base, worse, 2)
    assert len(failures) == 1 and failures[0].startswith("law-heldout: wrong 5 → 8")
    assert "(held out)" in table
    _, ok = acc.compare(base, run({"law-heldout": counts(7), "law-tuning": counts(5)}), 2)
    assert ok == []  # +2 is within the threshold
    _, none = acc.compare(base, run({"law-heldout": counts(1), "law-tuning": counts(5)}), 0)
    assert none == []  # fewer wrong words never fail


def test_compare_exit_code_and_summary_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    base, head, summary = tmp_path / "b.json", tmp_path / "h.json", tmp_path / "s.md"
    base.write_text(json.dumps(run({"x-heldout": counts(0)})), encoding="utf-8")
    head.write_text(json.dumps(run({"x-heldout": counts(4)})), encoding="utf-8")
    assert acc.main(["compare", str(base), str(head), "--summary", str(summary)]) == 1
    assert "x-heldout" in summary.read_text(encoding="utf-8") and "got worse" in capsys.readouterr().out
    assert acc.main(["compare", str(base), str(head), "--max-wrong-increase", "4"]) == 0
    assert acc.main(["compare", str(base), str(tmp_path / "missing.json")]) == 2


def test_score_scores_each_file_as_its_own_set(tmp_path: Path):
    folder = tmp_path / "reg"
    folder.mkdir()
    (folder / "one.tsv").write_text("# id\tsource\thangul\tmixed\none-1\tone\t전기 연구\t전기 硏究\n", encoding="utf-8")
    (folder / "sources.tsv").write_text("not\tan\titems\tfile\n", encoding="utf-8")
    (folder / "empty.tsv").write_text("# nothing\n", encoding="utf-8")
    out = tmp_path / "scores.json"
    lexicon = Path(__file__).parent / "fixtures" / "mini_lexicon.tsv"
    assert acc.main(["score", str(lexicon), "-o", str(out), "--regression", str(folder)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert list(data["sets"]) == ["one"] and data["sets"]["one"]["words"] >= 1
    assert data["lexicon_entries"] > 0 and data["gukhan"].endswith("__init__.py")
    assert acc.main(["score", str(tmp_path / "nope"), "-o", str(out)]) == 2
