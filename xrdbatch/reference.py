"""Readers for reference peak lists (RRUFF .dif text files) used for validation."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def read_rruff_dif(path) -> pd.DataFrame:
    """Return a DataFrame with columns two_theta, intensity, sorted by intensity (strongest first).

    A RRUFF DIF file has free-text headers, then a table whose header line contains
    "2-THETA" followed by rows "2θ  intensity  d  h  k  l", ending at a line of "=".
    """
    rows, in_table = [], False
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if "2-THETA" in stripped.upper():
            in_table = True
            continue
        if not in_table:
            continue
        if stripped.startswith("="):
            break
        parts = stripped.split()
        if len(parts) >= 2 and _NUM.match(parts[0]) and _NUM.match(parts[1]):
            rows.append((float(parts[0]), float(parts[1])))
    if not rows:
        raise ValueError(f"{Path(path).name}: no peak table found (expected a '2-THETA' header).")
    table = pd.DataFrame(rows, columns=["two_theta", "intensity"])
    return table.sort_values("intensity", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- reflections from unit cell

_CELL_RE = re.compile(r"([a-z]+):\s*([0-9.]+)", re.IGNORECASE)


def read_rruff_cell(path) -> dict:
    """Read the ``##CELL PARAMETERS=`` header line of a RRUFF pattern file."""
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.upper().startswith("##CELL PARAMETERS="):
            values = {k.lower(): float(v) for k, v in _CELL_RE.findall(line)}
            system = re.search(r"crystal system:\s*([a-z]+)", line, re.IGNORECASE)
            cell = {k: values[k] for k in ("a", "b", "c", "alpha", "beta", "gamma")}
            cell["system"] = system.group(1).lower() if system else ""
            return cell
    raise ValueError(f"{Path(path).name}: no ##CELL PARAMETERS line found.")


def _reciprocal_metric(cell: dict) -> np.ndarray:
    a, b, c = cell["a"], cell["b"], cell["c"]
    al, be, ga = np.radians([cell["alpha"], cell["beta"], cell["gamma"]])
    g = np.array(
        [
            [a * a, a * b * np.cos(ga), a * c * np.cos(be)],
            [a * b * np.cos(ga), b * b, b * c * np.cos(al)],
            [a * c * np.cos(be), b * c * np.cos(al), c * c],
        ]
    )
    return np.linalg.inv(g)


# Reflection conditions (hexagonal axes). Only well-established general conditions are applied;
# leaving out a special condition can only add extra allowed positions, never remove real ones.
RULES = {
    "none": lambda h, k, l: True,
    "P3221": lambda h, k, l: not (h == 0 and k == 0 and l % 3 != 0),
    "R-3c": lambda h, k, l: (-h + k + l) % 3 == 0 and not (h == 0 and k == 0 and l % 6 != 0),
}


def allowed_two_theta(cell: dict, wavelength: float, tt_max: float = 90.0, rule: str = "none", max_index: int = 12):
    """Sorted unique 2θ positions (°) of all symmetry-allowed reflections up to ``tt_max``."""
    g_star = _reciprocal_metric(cell)
    d_min = wavelength / (2 * np.sin(np.radians(tt_max / 2)))
    allowed = RULES[rule]
    positions = set()
    r = range(-max_index, max_index + 1)
    for h in r:
        for k in r:
            for l in r:
                if (h, k, l) == (0, 0, 0) or not allowed(h, k, l):
                    continue
                hkl = np.array([h, k, l])
                d = 1 / np.sqrt(hkl @ g_star @ hkl)
                if d >= d_min:
                    positions.add(round(float(2 * np.degrees(np.arcsin(wavelength / (2 * d)))), 4))
    return sorted(positions)
