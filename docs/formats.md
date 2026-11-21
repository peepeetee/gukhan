# Input formats / 入力 形式

`gukhan` converts plain text and Markdown, and also HTML, Word (`.docx`), EPUB and subtitle files (SRT, WebVTT).
The format follows the file extension; `--format` overrides it (and is needed with `--stdin`).
확장자로 形式을 判斷하며, `--format`으로 直接 指定할 수 있습니다 (`--stdin`에서는 必須).

| Extension | `--format` | What is converted | What is copied untouched |
| --- | --- | --- | --- |
| `.md`, `.txt`, other | `text` | prose; code, links, URLs are protected (docs/overrides-and-review.md) | |
| `.html`, `.htm`, `.xhtml` | `html` | text nodes | tags, attributes (`alt`, `title`…), comments, doctype, `<script>`, `<style>`, `<pre>`, `<code>`, `<kbd>`, `<samp>`, `<textarea>`, ruby readings, entities |
| `.docx` | `docx` | the text of Word runs in the body, headers, footers, footnotes, endnotes and comments | styles, formatting, images, field codes, deleted text, ruby readings, document properties, every other part |
| `.epub` | `epub` | XHTML chapters and the table of contents (`.ncx`) | the package file and metadata, images, styles, fonts; the member order and the stored `mimetype` |
| `.srt`, `.vtt` | `srt`, `vtt` | the text lines of each cue | cue numbers and identifiers, timing and settings, `WEBVTT` header, `NOTE`, `STYLE`, `REGION`, tags such as `<i>`, `<v Name>`, `<00:01.500>`, `{\an8}`, line endings |

## How it works / 作動 方式

The file is read into *flows*: a paragraph, a table cell, a list item, a subtitle cue. Inline markup inside a
flow does not break it, so `국<b>군</b>은` or a Word paragraph split over several runs is analysed as one
sentence, and each converted character goes back into the run or text node it came from, with its formatting.
A new block (`<p>`, `<li>`, `<br>`, a Word paragraph) starts a new flow. Entities, tabs and line breaks
inside a flow are kept as they are and count as a single non-Hangul character.
段落 單位로 分析하므로 글자 사이에 標識가 있어도 낱말은 하나로 變換되고, 書式은 그대로 남습니다.

Everything else is written back exactly as read. gukhan's tests check that for every format: the output has the same
length as the input, every changed character was a Hangul syllable that became a Hanja, and a second run
changes nothing. A `.docx` or `.epub` in which nothing converts is returned byte for byte; otherwise only the
changed parts are rewritten, and the archive keeps its members, their order, compression, names and timestamps
(ZIP extra fields are not carried over).

## Things to know / 알아 둘 것

- **UTF-8 only.** HTML, XHTML, subtitles and the XML inside Word and EPUB files must be UTF-8; anything else is
  refused with a message rather than guessed. UTF-8이 아니면 거부합니다.
- **Every input is checked before anything is written**, as with Markdown; a damaged or encrypted archive, or one
  that is not a Word or EPUB file, stops the run with exit code 2.
- **Size limits** on archives (1 GiB uncompressed, 20,000 members, 256 MiB per part) guard against zip bombs.
- **`--report`** lists flagged words with line and column in the *extracted prose* (the text nodes, runs or cues
  joined with line breaks), not in the markup; `--mark` puts `{…}` after the flagged word in the run that holds it.
- **Not supported** for these formats: `--llm-url` suggestions and `gukhan review` (convert with `--report` and put
  your decisions in the override file). Other encodings (EUC-KR/CP949), legacy `.doc`, PDF and `.odt` are out of scope.
- **Metadata is left alone**: the `<title>` of an HTML page is converted (it is a text node), but an EPUB's
  `content.opf` and a Word file's document properties are not.

```
gukhan page.html -o page.hanja.html
gukhan thesis.docx --in-place            # the original is kept as thesis.docx.bak
gukhan book.epub subs/*.srt --out-dir converted/
cat page.html | gukhan --stdin --format html > out.html
```

## From Python / 라이브러리

```python
from gukhan import Converter, formats

doc = formats.load("html", open("page.html", encoding="utf-8", newline="").read())
done = formats.convert_document(doc, Converter(), mark=False)
done.output  # the converted HTML
done.source_text  # the extracted prose the report offsets refer to
```

`formats.load` takes `str` for `html`, `srt` and `vtt`, and `bytes` for `docx` and `epub`.
