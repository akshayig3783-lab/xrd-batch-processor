"""Reader for two-column text exports: .xy, .csv, .txt, .dat.

Handles whitespace, comma and semicolon delimiters, German decimal commas
(``28,44;1520``), header lines, and RRUFF ``##KEY=value`` headers.
"""

from __future__ import annotations

import re
from pathlib import Path

from xrdbatch.pattern import Pattern, clean

_WAVELENGTH_RE = re.compile(r"WAVELENGTH\s*[=:]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def _split(line: str) -> list[str]:
    if ";" in line:
        return [part.replace(",", ".") for part in line.split(";")]
    if "," in line:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 2:
            return parts
    if "\t" in line:
        return line.split("\t")
    return line.split()


def _parse_xy(line: str) -> tuple[float, float] | None:
    parts = [p.strip() for p in _split(line) if p.strip()]
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def read_text(path) -> Pattern:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    tt, y = [], []
    wavelength = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("#", "!", "'")):
            match = _WAVELENGTH_RE.search(line)
            if match:
                wavelength = float(match.group(1))
            continue
        xy = _parse_xy(line)
        if xy is None:
            continue
        tt.append(xy[0])
        y.append(xy[1])

    if len(tt) < 2:
        raise ValueError(f"{path.name}: found fewer than 2 numeric (2θ, intensity) rows.")

    two_theta, intensity, warnings = clean(tt, y)
    return Pattern(
        name=path.stem,
        two_theta=two_theta,
        intensity=intensity,
        wavelength=wavelength,
        metadata={"source": path.name, "format": "text"},
        warnings=warnings,
    )
