# Local-model suggestions / 局所 모델 提案 (optional)

## English

gukhan never guesses. A flagged word keeps its Hangul and lists the dictionary's candidates. If you
run a language model on your own computer, gukhan can ask it to *suggest* one of those candidates.
The suggestion is a hint for you, not a decision.

What this is, and is not:

- **Off by default.** Nothing is sent anywhere unless you pass `--llm-url`. There is no model, no
  download and no extra dependency: gukhan uses only Python's standard library to talk to a server
  you started yourself.
- **Localhost only.** The URL must point to this computer (`127.0.0.1`, `::1`, `localhost`). Any other
  host is refused unless you add `--llm-allow-remote`, which means your sentences are sent there.
  Proxy settings are ignored, so a localhost address is never routed through a proxy.
- **The model sees one sentence and the candidates.** For each flagged word it gets that word's
  sentence (marked `[like this]`, at most about 300 characters each side) and the dictionary's
  candidates with their definitions. Not the document, not your override file.
- **It must choose a listed candidate or abstain.** An answer that is not a number inside the list
  counts as an abstention, so the model cannot add a reading the dictionary lacks.
- **Hints are labelled.** In a report (`--report out.tsv` or `.md`) an extra column shows
  `國歌 (llm:name, unconfirmed)`. In `gukhan review` the hint is printed under the candidates; you
  accept it by typing `y`, or answer as usual. Enter still does nothing and nothing is preselected.
- **Never silently applied.** The converted text is unchanged unless you pass `--llm-apply`, which
  writes the model's picks into the output (and the report then says `applied`). It cannot be
  combined with `--mark`.
- **A broken server does not break conversion.** If the server is unreachable or answers nonsense,
  gukhan prints one notice and carries on without suggestions.

Set-up with llama.cpp or Ollama (any OpenAI-compatible server works):

```
llama-server -m your-model.gguf --port 8080          # llama.cpp
gukhan text.md --llm-url http://127.0.0.1:8080/v1 --report flags.md

ollama serve                                         # Ollama; pull a model first
gukhan review text.md --overrides my.overrides \
    --llm-url http://127.0.0.1:11434/v1 --llm-model your-model
```

Measure a model before trusting it. `gukhan-regress score tests/regression/*.tsv --lexicon build/lexicon
--llm-url http://127.0.0.1:8080/v1` adds a line `suggest: asked=… right=… wrong=… abstained=…`, counted
against the published text and never applied. No model has been measured by the project yet, so no
accuracy figure is claimed for any model.

For code: `gukhan.suggest.MockBackend({"의원": "議員"})` is a fixed answer table for tests; any object with
`name` and `suggest(sentence, word, candidates) -> int | None` is a backend.

## 한국어

gukhan은 추측하지 않습니다. flag된 낱말은 한글로 남고 辭典의 後補가 나열됩니다. 自己 컴퓨터에서 言語
모델을 돌린다면, 그 後補 가운데 하나를 모델이 *提案*하게 할 수 있습니다. 提案은 사람을 위한 參考일 뿐
決定이 아닙니다.

- **기본은 꺼짐.** `--llm-url` 을 주지 않으면 아무것도 어디로도 보내지 않습니다. 모델도 내려받기도 追加
  依存도 없고, 직접 띄운 서버와는 Python 標準 라이브러리로만 통신합니다.
- **localhost 만.** 주소는 이 컴퓨터(`127.0.0.1`, `::1`, `localhost`)여야 합니다. 다른 주소는
  `--llm-allow-remote` 를 주어야 하며, 그러면 文章이 그곳으로 보내집니다. proxy 設定은 無視합니다.
- **모델이 보는 것은 한 文章과 後補.** flag된 낱말마다 그 낱말이 든 文章(`[이렇게]` 표시, 앞뒤 各 300字
  안팎)과 辭典의 後補·뜻풀이만 받습니다. 文書 全體나 override file은 보내지 않습니다.
- **나열된 後補 중 하나를 고르거나 棄權.** 목록 안의 番號가 아닌 答은 棄權으로 處理되므로 辭典에 없는
  讀法을 모델이 더할 수 없습니다.
- **提案은 표시됩니다.** 報告(`--report`)에는 `國歌 (llm:name, unconfirmed)` 欄이 추가됩니다. `gukhan
  review` 에서는 後補 아래에 提案이 나오고 `y` 로 受容하거나 평소처럼 答합니다. Enter는 여전히 아무
  것도 하지 않으며 미리 선택된 것은 없습니다.
- **조용히 適用되지 않음.** `--llm-apply` 를 줄 때만 모델의 選擇이 出力에 쓰이고 報告에 `applied` 로
  남습니다. `--mark` 와는 함께 쓸 수 없습니다.
- **서버가 고장나도 變換은 계속.** 서버에 닿지 않거나 엉뚱한 答이면 한 번 알리고 提案 없이 繼續합니다.

llama.cpp 나 Ollama 設定 例는 위 English 節의 命令을 그대로 쓰면 됩니다(OpenAI 互換 서버면 무엇이든
可能). 믿기 前에 모델을 測定하세요: `gukhan-regress score … --llm-url …` 은 `suggest: asked=… right=…
wrong=… abstained=…` 줄을 더하며, 發表된 글과 견주어 세기만 하고 適用하지는 않습니다. 이 project는 아직
어떤 모델도 測定하지 않았으므로 모델의 正確度 數値를 主張하지 않습니다.
