# SPDX-License-Identifier: Apache-2.0
"""Local-model suggestions: hints only, loopback only, never applied without --llm-apply."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from gukhan import report, suggest
from gukhan.analyser import ListAnalyser
from gukhan.cli import main as cli_main
from gukhan.convert import Converter, Kind
from gukhan.lexicon import Entry, Lexicon
from gukhan.review import Reviewer

LEX = Lexicon(
    [
        Entry("국가", "國家", "명사", "t", "나라"),
        Entry("국가", "國歌", "명사", "t", "나라를 상징하는 노래"),
        Entry("안전", "安全", "명사", "t", "위험이 없음"),
    ]
)
TEXT = "국가 안전 보장.\n둘째 국가는 노래다."
TOKENS = [("국가", "NNG"), ("안전", "NNG"), ("국가", "NNG")]


def convert(text=TEXT, tokens=TOKENS):
    c = Converter(LEX, None, ListAnalyser(tokens))
    return c, c.convert(text)


def test_sentence_around_is_one_sentence_with_the_word_marked():
    start = TEXT.index("국가", 5)
    assert suggest.sentence_around(TEXT, start, start + 2) == "둘째 [국가]는 노래다."
    assert suggest.sentence_around(TEXT, 0, 2) == "[국가] 안전 보장."
    long = "가" * 1000 + "국가" + "나" * 1000
    assert len(suggest.sentence_around(long, 1000, 1002)) <= 2 * suggest.MAX_SENTENCE + 4


def test_parse_choice_accepts_a_leading_number_only():
    assert suggest.parse_choice("2") == 2
    assert suggest.parse_choice(" 1. 國家") == 1
    assert suggest.parse_choice("0") is None
    assert suggest.parse_choice("I think 2") is None
    assert suggest.parse_choice("") is None


def test_mock_backend_picks_among_candidates_only():
    _, r = convert()
    m = suggest.MockBackend({"국가": "國歌"})
    s = suggest.collect_suggestions(m, TEXT, r)
    assert [v.hanja for v in s.values()] == ["國歌", "國歌"] and all(v.index == 2 for v in s.values())
    # the model saw the sentence, the word and the candidates, nothing else
    assert m.calls[0] == ("[국가] 안전 보장.", "국가", ["國家", "國歌"])
    # an answer outside the dictionary's list is an abstention
    assert suggest.collect_suggestions(suggest.MockBackend({"국가": "國價"}), TEXT, r) == {}


def test_out_of_range_numbers_abstain():
    class Wild:
        name = "wild"

        def suggest(self, sentence, word, candidates):
            return 9

    _, r = convert()
    assert suggest.collect_suggestions(Wild(), TEXT, r) == {}


def test_failure_is_reported_once_and_conversion_is_untouched():
    c, r = convert()
    errors: list[str] = []
    s = suggest.collect_suggestions(suggest.MockBackend(fail="down"), TEXT, r, on_error=errors.append)
    assert s == {} and errors == ["down"]
    assert r.text == c.convert(TEXT).text  # nothing about the conversion changed


def test_suggestions_are_not_applied_unless_asked():
    c, r = convert()
    s = suggest.collect_suggestions(suggest.MockBackend({"국가": "國歌"}), TEXT, r)
    assert "國" not in r.text.replace("安全", "")
    applied = suggest.apply_suggestions(TEXT, r, {k: v for k, v in s.items()})
    assert applied == "國歌 安全 보장.\n둘째 國歌는 노래다."


def test_report_marks_suggestions_as_unconfirmed():
    _, r = convert()
    s = suggest.collect_suggestions(suggest.MockBackend({"국가": "國歌"}), TEXT, r)
    tsv = report.to_tsv(TEXT, r, s)
    assert "\tsuggestion\n" in tsv and "國歌 (mock, unconfirmed)" in tsv
    assert "unconfirmed" in report.to_markdown(TEXT, r, s)
    assert "suggestion" not in report.to_tsv(TEXT, r)  # no backend, no column


def test_loopback_guard():
    assert suggest.is_loopback("http://127.0.0.1:8080/v1") and suggest.is_loopback("http://localhost:11434")
    assert suggest.is_loopback("http://[::1]:8080")
    assert not suggest.is_loopback("http://192.168.0.5:8080") and not suggest.is_loopback("http://example.com/v1")
    with pytest.raises(ValueError):
        suggest.OpenAIChatBackend("http://example.com/v1")
    with pytest.raises(ValueError):
        suggest.OpenAIChatBackend("file:///etc/passwd")
    suggest.OpenAIChatBackend("http://example.com/v1", allow_remote=True)


class FakeServer:
    """A tiny OpenAI-compatible endpoint on localhost that answers with a fixed string."""

    def __init__(self, answer="2"):
        self.requests: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "body": body})
                out = json.dumps({"choices": [{"message": {"content": answer}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.close()


def test_openai_backend_end_to_end_with_a_local_server(server):
    b = suggest.OpenAIChatBackend(server.url, "tiny")
    _, r = convert()
    s = suggest.collect_suggestions(b, TEXT, r)
    assert [v.hanja for v in s.values()] == ["國歌", "國歌"] and b.name == "llm:tiny"
    req = server.requests[0]
    assert req["path"] == "/v1/chat/completions" and req["body"]["model"] == "tiny"
    assert req["body"]["temperature"] == 0 and req["body"]["stream"] is False
    user = req["body"]["messages"][1]["content"]
    assert "[국가] 안전 보장." in user and "1. 國家" in user and "2. 國歌" in user
    assert "둘째" not in user  # only the sentence of this word, not the document
    assert len(server.requests) == 2  # the second 국가 has another sentence; same-sentence repeats are cached


def test_unreachable_server_raises_suggest_error():
    b = suggest.OpenAIChatBackend("http://127.0.0.1:9/v1", timeout=1)
    with pytest.raises(suggest.SuggestError):
        b.suggest("[국가]", "국가", LEX.candidates("국가"))


def test_cli_report_only_by_default_then_explicit_apply(server, tmp_path, capsys):
    src = tmp_path / "a.txt"
    src.write_text("국가 안전 보장.", encoding="utf-8")
    rep = tmp_path / "r.tsv"
    lex = tmp_path / "lex.tsv"
    lex.write_text(
        "국가\t國家\t명사\tt\t나라\n국가\t國歌\t명사\tt\t노래\n안전\t安全\t명사\tt\t\n",
        encoding="utf-8",
    )
    args = [str(src), "--lexicon", str(lex), "--llm-url", server.url, "--report", str(rep)]
    assert cli_main(args) == 0
    out = capsys.readouterr()
    assert "國歌" not in out.out and "unconfirmed" in rep.read_text(encoding="utf-8")
    assert cli_main([*args, "--llm-apply"]) == 0
    out = capsys.readouterr()
    assert out.out.startswith("國歌") and "applied" in rep.read_text(encoding="utf-8")


def test_cli_refuses_remote_and_inconsistent_flags(tmp_path, capsys):
    src = tmp_path / "a.txt"
    src.write_text("국가", encoding="utf-8")
    assert cli_main([str(src), "--llm-url", "http://example.com/v1"]) == 2
    assert cli_main([str(src), "--llm-apply"]) == 2
    assert cli_main([str(src), "--llm-url", "http://127.0.0.1:1/v1", "--llm-apply", "--mark"]) == 2


def test_cli_does_nothing_networked_by_default(tmp_path, monkeypatch, capsys):
    import urllib.request

    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", boom)
    src = tmp_path / "a.txt"
    src.write_text("국가 안전", encoding="utf-8")
    assert cli_main([str(src)]) == 0


def reviewer(tmp_path, answers, backend):
    it = iter(answers)
    shown: list[str] = []
    path = tmp_path / "my.overrides"
    conv = Converter(LEX, None, ListAnalyser(TOKENS))
    r = Reviewer(conv, TEXT, path, input_fn=lambda _p: next(it), output_fn=shown.append, backend=backend)
    return r, path, shown


def test_review_shows_a_suggestion_but_enter_and_numbers_stay_human(tmp_path):
    r, path, shown = reviewer(tmp_path, ["", "1"], suggest.MockBackend({"국가": "國歌"}))
    # an empty answer is rejected as before; the human's own choice (1 = 國家) wins over the hint
    r.run()
    assert any("suggestion (unconfirmed, mock): 國歌" in line for line in shown)
    assert "국가 = 國家" in path.read_text(encoding="utf-8")


def test_review_y_accepts_the_suggestion_and_records_it(tmp_path):
    r, path, shown = reviewer(tmp_path, ["y"], suggest.MockBackend({"국가": "國歌"}))
    r.run()
    text = path.read_text(encoding="utf-8")
    assert "국가 = 國歌" in text and "accepted suggestion, mock" in text


def test_review_y_without_a_suggestion_is_refused(tmp_path):
    r, path, shown = reviewer(tmp_path, ["y", "s"], suggest.MockBackend({}))
    r.run()
    assert any("no suggestion to accept" in line for line in shown) and not path.exists()


def test_review_backend_failure_turns_it_off_and_review_goes_on(tmp_path):
    r, path, shown = reviewer(tmp_path, ["2"], suggest.MockBackend(fail="down"))
    r.run()
    assert any("continuing without suggestions" in line for line in shown)
    assert "국가 = 國歌" in path.read_text(encoding="utf-8")


def test_kind_of_decisions_is_unchanged_by_suggestions():
    _, r = convert()
    assert [d.kind for d in r.decisions].count(Kind.FLAGGED) == 2


def test_regress_scores_suggestions_without_applying_them(server, tmp_path, capsys):
    from gukhan.regress.cli import main as regress_main

    lex = tmp_path / "lex.tsv"
    lex.write_text("국가\t國家\t명사\tt\t나라\n국가\t國歌\t명사\tt\t노래\n", encoding="utf-8")
    items = tmp_path / "items.tsv"
    items.write_text("t1\ts\t국가 노래\t國歌 노래\nt2\ts\t국가 안전\t國家 안전\n", encoding="utf-8")
    assert regress_main(["score", str(items), "--lexicon", str(lex), "--llm-url", server.url]) == 0
    out = capsys.readouterr().out
    assert "suggest: asked=2 right=1 wrong=1 over=0 abstained=0 (not applied" in out
    assert "right=0" in out.splitlines()[0]  # the converter itself still abstained on both
    assert regress_main(["score", str(items), "--lexicon", str(lex), "--llm-url", "http://example.com/v1"]) == 2
