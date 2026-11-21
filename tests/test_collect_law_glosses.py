# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "collect_law_glosses", Path(__file__).parent.parent / "scripts" / "collect_law_glosses.py"
)
cl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cl)


def test_simple_gloss():
    h, x, pairs = cl.to_item("법인이 분사무소(分事務所)를 설치한다.")
    assert h == "법인이 분사무소를 설치한다."
    assert x == "법인이 分事務所를 설치한다."
    assert pairs == [("분사무소", "分事務所")]


def test_longer_word_keeps_head_in_hangul():
    h, x, _ = cl.to_item("가족관계(關係)를 본다.")
    assert (h, x) == ("가족관계를 본다.", "가족關係를 본다.")


def test_unusable_sentences():
    assert cl.to_item("그냥 문장이다.") is None
    assert cl.to_item("상뇌증(狂牛病)이다.") is None  # excluded mismatch
    assert cl.to_item("자(子孫)이다.") is None  # Hanja longer than the Hangul word
    assert cl.to_item("大韓 의사(意思)이다.") is None  # stray Hanja


def test_clean_and_extract_limit_per_pair():
    assert cl.clean("**제1조** \\(목적\\)") == "제1조 (목적)"
    text = "\n".join(f"{i}번 자(子)이다." for i in range(5))
    assert len(cl.extract(text)) == cl.PER_PAIR
