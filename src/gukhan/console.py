# SPDX-License-Identifier: Apache-2.0
"""Console setup shared by every command."""

from __future__ import annotations

import sys


def utf8_streams() -> None:
    """Redirected output is UTF-8 on every platform (Windows would use cp949 and fail on rare Hanja)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace", newline="" if stream is sys.stdout else None)
            except (ValueError, OSError):  # a stream that has already been read from or is closed
                pass
