# SPDX-License-Identifier: Apache-2.0
"""Reading and rewriting a ZIP container (.docx, .epub) so that every part but the converted ones is unchanged."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from . import FormatError

MAX_ENTRIES = 20_000
MAX_TOTAL = 1 << 30  # 1 GiB of uncompressed data, against zip bombs
MAX_PART = 256 << 20


@dataclass
class Entry:
    """One archive member as read: its header fields and its bytes."""

    info: zipfile.ZipInfo
    data: bytes


def read_zip(data: bytes) -> list[Entry]:
    """All members of the archive, in order, with size limits and encrypted members refused."""
    try:
        zin = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise FormatError("zip file이 아닙니다 / not a valid zip container") from e
    with zin:
        infos = zin.infolist()
        if len(infos) > MAX_ENTRIES or sum(i.file_size for i in infos) > MAX_TOTAL:
            raise FormatError("file이 너무 큽니다 / the archive is too large (limit 1 GiB, 20000 parts)")
        out: list[Entry] = []
        for info in infos:
            if info.flag_bits & 0x1:
                raise FormatError("암호화된 file은 읽을 수 없습니다 / encrypted archives are not supported")
            if info.file_size > MAX_PART:
                raise FormatError(f"{info.filename}: 部分이 너무 큽니다 / a part is too large")
            try:
                with zin.open(info) as fh:
                    body = fh.read(info.file_size + 1)
            except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as e:
                raise FormatError(f"{info.filename}: 읽을 수 없습니다 / cannot read this part ({e})") from e
            if len(body) != info.file_size:
                raise FormatError(f"{info.filename}: 크기가 맞지 않습니다 / size does not match the header")
            out.append(Entry(info, body))
    return out


def write_zip(entries: list[Entry], replaced: dict[int, bytes]) -> bytes:
    """A new archive with the same members in the same order; ``replaced`` maps an index to new bytes.

    Names, order, compression method, timestamps, attributes and comments are kept; extra fields are not
    (they only describe the old layout), so ZIP64 and timestamp extensions are rewritten by the library.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zout:
        for i, entry in enumerate(entries):
            old = entry.info
            info = zipfile.ZipInfo(old.filename, old.date_time)
            info.compress_type = old.compress_type
            info.external_attr = old.external_attr
            info.create_system = old.create_system
            info.comment = old.comment
            zout.writestr(info, replaced.get(i, entry.data))
    return buf.getvalue()
