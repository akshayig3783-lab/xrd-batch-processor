"""The Pattern data model shared by every stage of the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Pattern:
    """One diffraction pattern: 2θ (degrees) against intensity (counts or arbitrary units).

    ``wavelength`` (Å) is set only when the source file states it.
    ``warnings`` collects human-readable notes about data problems found while reading.
    """

    name: str
    two_theta: np.ndarray
    intensity: np.ndarray
    wavelength: float | None = None
    metadata: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def clean(two_theta, intensity) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Drop NaN/inf rows, sort by 2θ and average intensities at duplicate 2θ values."""
    tt = np.asarray(two_theta, dtype=float)
    y = np.asarray(intensity, dtype=float)
    warnings: list[str] = []

    finite = np.isfinite(tt) & np.isfinite(y)
    if not finite.all():
        warnings.append(f"Dropped {int((~finite).sum())} row(s) with missing or non-numeric values.")
        tt, y = tt[finite], y[finite]

    if tt.size > 1 and np.any(np.diff(tt) < 0):
        warnings.append("2θ values were not in ascending order; data was sorted.")

    unique_tt, inverse, counts = np.unique(tt, return_inverse=True, return_counts=True)
    if unique_tt.size < tt.size:
        warnings.append(f"Averaged {tt.size - unique_tt.size} duplicate 2θ value(s).")
    sums = np.bincount(inverse, weights=y, minlength=unique_tt.size)
    return unique_tt, sums / counts, warnings


def make_unique_names(patterns: list[Pattern]) -> list[Pattern]:
    """Rename repeated names to "name (2)", "name (3)", … so results never overwrite each other."""
    seen: dict[str, int] = {}
    for p in patterns:
        count = seen.get(p.name, 0) + 1
        seen[p.name] = count
        if count > 1:
            p.name = f"{p.name} ({count})"
    return patterns
