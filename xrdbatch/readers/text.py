"""Reader for two-column text exports: .xy, .csv, .txt, .dat.

Handles whitespace, tab, comma and semicolon delimiters, German decimal commas
(``28,44;1520``, ``28,44<TAB>1520``, ``28,44 1520``), header lines, and RRUFF
``##KEY=value`` headers.
"""

from __future__ import annotations

import re
from pathlib import Path

from xrdbatch.pattern import Pattern, clean

_WAVELENGTH_RE = re.compile(r"WAVE\s*LENGTH[^0-9=:]*[=:]?\s*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE)
_PLAUSIBLE_WAVELENGTH = (0.3, 3.0)  # Å; covers Ag, Mo, Cu, Co, Fe, Cr tubes


def _candidates(line: str):
    """Ways to split one data line, most specific first."""
    if ";" in line:
        yield [part.replace(",", ".") for part in line.split(";")]
    if "\t" in line:
        yield [part.replace(",", ".") for part in line.split("\t")]
    if "," in line:
        yield line.split(",")
        yield [part.replace(",", ".") for part in line.split()]
    yield line.split()


def _parse_xy(line: str) -> tuple[float, float] | None:
    for parts in _candidates(line):
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            continue
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            continue
    return None


def _wavelength(line: str, warnings: list[str]) -> float | None:
    match = _WAVELENGTH_RE.search(line)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    lo, hi = _PLAUSIBLE_WAVELENGTH
    if not lo <= value <= hi:
        warnings.append(f"Ignored implausible wavelength {value} in header (expected {lo}–{hi} Å).")
        return None
    return value


def read_text(path) -> Pattern:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    tt, y = [], []
    wavelength = None
    header_warnings: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        is_comment = line.startswith(("#", "!", "'"))
        xy = None if is_comment else _parse_xy(line)
        if xy is None:
            if wavelength is None:
                wavelength = _wavelength(line, header_warnings)
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
        warnings=header_warnings + warnings,
    )
