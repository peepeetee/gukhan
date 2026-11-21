# SPDX-License-Identifier: Apache-2.0
"""Edge cases the main tests left uncovered: console, archive limits, Unihan, manifest sources, regress errors."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from gukhan import console
from gukhan.formats import FormatError, ziputil
from gukhan.lexicon_build import unihan, wikidata_lexemes
from gukhan.lexicon_build.manifest import write_manifest
from gukhan.regress.cli import main as regress_main

FIXTURES = Path(__file__).parent / "fixtures"


class _Stream:
    def __init__(self, error: type[Exception] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.error = error

    def reconfigure(self, **kwargs: object) -> None:
        if self.error:
            raise self.error("closed")
        self.calls.append(kwargs)


def test_utf8_streams_reconfigures_and_survives_odd_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    out, err = _Stream(), _Stream()
    monkeypatch.setattr(console.sys, "stdout", out)
    monkeypatch.setattr(console.sys, "stderr", err)
    console.utf8_streams()
    assert out.calls == [{"encoding": "utf-8", "errors": "replace", "newline": ""}]
    assert err.calls == [{"encoding": "utf-8", "errors": "replace", "newline": None}]
    monkeypatch.setattr(console.sys, "stdout", _Stream(ValueError))  # already read from
    monkeypatch.setattr(console.sys, "stderr", io.StringIO())  # no reconfigure at all
    console.utf8_streams()


def _zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "hello")
    return buf.getvalue()


def test_read_zip_refuses_oversize_parts_and_archives(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _zip()
    assert [e.info.filename for e in ziputil.read_zip(data)] == ["a.txt"]
    monkeypatch.setattr(ziputil, "MAX_PART", 3)
    with pytest.raises(FormatError, match="too large"):
        ziputil.read_zip(data)
    monkeypatch.setattr(ziputil, "MAX_PART", 1 << 20)
    monkeypatch.setattr(ziputil, "MAX_ENTRIES", 0)
    with pytest.raises(FormatError, match="too large"):
        ziputil.read_zip(data)
    with pytest.raises(FormatError, match="not a valid zip"):
        ziputil.read_zip(b"not a zip")


def test_read_zip_refuses_encrypted_and_corrupt_members() -> None:
    data = bytearray(_zip())
    # set the "encrypted" flag bit in the central directory header (signature PK\x01\x02, flags at offset 8)
    central = data.rindex(b"PK\x01\x02")
    data[central + 8] |= 0x1
    with pytest.raises(FormatError, match="encrypted"):
        ziputil.read_zip(bytes(data))
    broken = bytearray(_zip())
    local = broken.index(b"hello")
    broken[local : local + 5] = b"hullo"  # content changes, so the CRC no longer matches
    with pytest.raises(FormatError, match="cannot read"):
        ziputil.read_zip(bytes(broken))


def test_unihan_reads_directory_zip_and_plain_file(tmp_path: Path) -> None:
    source = FIXTURES / "Unihan_Readings.txt"
    from_file, _ = unihan.read_khangul(source)
    folder = tmp_path / "dir"
    folder.mkdir()
    (folder / "Unihan_Readings.txt").write_bytes(source.read_bytes())
    archive = tmp_path / "Unihan.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(source, "Unihan_Readings.txt")
    assert unihan.read_khangul(folder)[0] == from_file
    assert unihan.read_khangul(archive)[0] == from_file
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="Unihan_Readings"):
        unihan.read_khangul(empty)
    other = tmp_path / "other.zip"
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("readme.txt", "x")
    with pytest.raises(FileNotFoundError, match="Unihan_Readings"):
        unihan.read_khangul(other)


def test_unihan_version_is_read_from_a_dated_header(tmp_path: Path) -> None:
    path = tmp_path / "Unihan_Readings.txt"
    path.write_text(
        "# Unihan_Readings.txt\n# Date: 2025-08-01 12:00:00 GMT\nU+4E00\tkHangul\t일:0E\n", encoding="utf-8"
    )
    readings, version = unihan.read_khangul(path)
    assert readings["一"] == ["일"] and version == "dated 2025-08-01"
    path.write_text(
        "# Unihan_Readings.txt\n# Date: 2025-08-01\n# Unicode version 17.0.0\nU+4E00\tkHangul\t일:0E\n",
        encoding="utf-8",
    )
    assert unihan.read_khangul(path)[1] == "17.0.0"


def test_manifest_records_ranking_sources(tmp_path: Path) -> None:
    krdict, learner = tmp_path / "krdict", tmp_path / "learner.tsv"
    krdict.mkdir()
    (krdict / "001.xml").write_text("<x/>", encoding="utf-8")
    learner.write_text("가\t1\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    lexicon = out / "lexicon.tsv"
    lexicon.write_text("가\t家\n", encoding="utf-8")
    path = write_manifest(
        out, stdict=None, wiktextract=[], unihan=None, unihan_version=None, licence="CC-BY-SA-2.0-KR",
        counts={"entries": 1}, outputs={"lexicon": lexicon}, ranking_sources={"krdict": krdict, "learner": learner},
    )  # fmt: skip
    text = path.read_text(encoding="utf-8")
    assert "CC-BY-SA-2.0-KR" in text and "KOGL-Type-1" in text and "한국어기초사전" in text and "학습용 어휘" in text


def test_regress_score_reports_missing_files_and_bad_rules(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert regress_main(["score", str(tmp_path / "missing.tsv")]) == 2
    assert "not found" in capsys.readouterr().err
    items = tmp_path / "items.tsv"
    items.write_text("t-1\tt\t전기\t電氣\n", encoding="utf-8")
    assert regress_main(["score", str(items), "--rules", "no-such-rule"]) == 2
    assert "gukhan-regress:" in capsys.readouterr().err


def test_wikidata_lexeme_dump_formats_and_usage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import bz2
    import gzip

    body = b'[\n{"id": "L1", "type": "lexeme"},\nnot json,\n{"id": "L2"}\n]\n'
    plain, packed, zipped = tmp_path / "l.json", tmp_path / "l.json.bz2", tmp_path / "l.json.gz"
    plain.write_bytes(body)
    packed.write_bytes(bz2.compress(body))
    zipped.write_bytes(gzip.compress(body))
    for path in (plain, packed, zipped):
        assert [x["id"] for x in wikidata_lexemes.iter_lexemes(path)] == ["L1", "L2"], path.name
    assert wikidata_lexemes.main([]) == 2
    assert "usage" in capsys.readouterr().err
