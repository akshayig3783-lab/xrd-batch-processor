"""Readers for reference peak lists (RRUFF .dif text files) used for validation."""

from __future__ import annotations

import re
from pathlib import Path

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
