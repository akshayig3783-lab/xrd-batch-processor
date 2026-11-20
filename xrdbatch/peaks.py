"""Peak detection plus derived quantities: d-spacing (Bragg), FWHM, Scherrer crystallite size."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import median_filter
from scipy.signal import find_peaks, peak_widths

from xrdbatch.pattern import Pattern

COLUMNS = ["pattern", "two_theta", "d_spacing", "intensity", "rel_intensity", "fwhm", "crystallite_size_nm"]


def resolve_wavelength(p: Pattern, ui_wavelength: float) -> tuple[float, str]:
    """Use the wavelength stored in the file when there is one, otherwise the user's choice."""
    if p.wavelength is not None:
        return float(p.wavelength), "file"
    return float(ui_wavelength), "user"


def d_spacing(two_theta_deg, wavelength):
    """Bragg's law, first order: d = λ / (2 sin θ). Same unit as λ (Å)."""
    theta = np.radians(np.asarray(two_theta_deg, dtype=float) / 2)
    return wavelength / (2 * np.sin(theta))


def scherrer_size_nm(fwhm_deg, two_theta_deg, wavelength, k: float = 0.9):
    """Scherrer: τ = Kλ / (β cos θ), β = FWHM in radians, λ in Å → τ in nm."""
    beta = np.radians(np.asarray(fwhm_deg, dtype=float))
    theta = np.radians(np.asarray(two_theta_deg, dtype=float) / 2)
    return k * (wavelength / 10) / (beta * np.cos(theta))


NOISE_FACTOR = 6.0  # a peak's prominence must exceed this many noise standard deviations


def noise_sigma(y: np.ndarray, step: float) -> float:
    """Robust noise level: MAD of the residual after a ~1° running median removes peaks and background."""
    size = max(5, int(round(1.0 / step)) | 1)
    residual = y - median_filter(y, size=size, mode="nearest")
    return float(1.4826 * np.median(np.abs(residual - np.median(residual))))


def _half_width(tt: np.ndarray, y: np.ndarray, i: int, half: float, direction: int) -> float | None:
    """Distance in 2θ from peak i to where y falls below ``half``; None if a neighbouring peak rises first."""
    j = i
    while 0 <= j + direction < len(y):
        k = j + direction
        if y[k] < half:
            # linear interpolation between j (above half) and k (below half)
            x = tt[j] + (tt[k] - tt[j]) * (y[j] - half) / (y[j] - y[k])
            return abs(x - tt[i])
        if y[k] > y[j] and y[j] < y[i]:  # climbing into the next peak before reaching half height
            return None
        j = k
    return None


def _fwhm_at_half_height(tt: np.ndarray, y: np.ndarray, i: int) -> float:
    """FWHM at half the peak's height above zero (data is background-subtracted).

    When one side is blocked by an overlapping peak, assume symmetry and double the other side.
    """
    half = y[i] / 2
    left = _half_width(tt, y, i, half, -1)
    right = _half_width(tt, y, i, half, +1)
    if left is not None and right is not None:
        return left + right
    if left is not None or right is not None:
        return 2 * (left if left is not None else right)
    _, _, lo, hi = peak_widths(y, [i], rel_height=0.5)
    positions = np.arange(len(tt))
    return float(np.interp(hi[0], positions, tt) - np.interp(lo[0], positions, tt))


def find_peaks_table(
    p: Pattern,
    wavelength: float,
    prominence: float = 0.05,
    min_distance_deg: float = 0.1,
    k: float = 0.9,
) -> pd.DataFrame:
    """Find peaks; ``prominence`` is a fraction of the pattern's maximum intensity."""
    y = np.asarray(p.intensity, dtype=float)
    tt = np.asarray(p.two_theta, dtype=float)
    peak_max = np.max(y) if y.size else 0.0
    if y.size < 3 or peak_max <= 0:
        return pd.DataFrame(columns=COLUMNS)

    step = float(np.median(np.diff(tt)))
    distance = max(1, int(round(min_distance_deg / step)))
    threshold = max(prominence * peak_max, NOISE_FACTOR * noise_sigma(y, step))
    idx, _ = find_peaks(y, prominence=threshold, distance=distance)
    if idx.size == 0:
        return pd.DataFrame(columns=COLUMNS)

    fwhm = np.array([_fwhm_at_half_height(tt, y, i) for i in idx])
    peak_tt = tt[idx]
    intensity = y[idx]
    table = pd.DataFrame(
        {
            "pattern": p.name,
            "two_theta": peak_tt,
            "d_spacing": d_spacing(peak_tt, wavelength),
            "intensity": intensity,
            "rel_intensity": 100 * intensity / intensity.max(),
            "fwhm": fwhm,
            "crystallite_size_nm": scherrer_size_nm(fwhm, peak_tt, wavelength, k),
        }
    )
    return table[COLUMNS].sort_values("two_theta").reset_index(drop=True)
