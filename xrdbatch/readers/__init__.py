"""File readers. ``read_pattern`` picks the reader from the file extension."""

from __future__ import annotations

from pathlib import Path

from xrdbatch.pattern import Pattern
from xrdbatch.readers.text import read_text

TEXT_EXTENSIONS = {".xy", ".csv", ".txt", ".dat"}


class UnsupportedFormatError(ValueError):
    """Raised when no reader handles the file's extension."""


def _readers():
    readers = {ext: lambda p: [read_text(p)] for ext in TEXT_EXTENSIONS}
    return readers


def supported_extensions() -> list[str]:
    return sorted(_readers())


def read_pattern(path) -> list[Pattern]:
    """Read one file and return its patterns (a Bruker file may hold several scans)."""
    path = Path(path)
    ext = path.suffix.lower()
    reader = _readers().get(ext)
    if reader is None:
        raise UnsupportedFormatError(
            f"Unsupported file type '{ext}' ({path.name}). Supported: {', '.join(supported_extensions())}"
        )
    return reader(path)
