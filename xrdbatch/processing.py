"""Pattern clean-up: crop, smooth, background subtraction, normalisation.

Every function returns a new Pattern and leaves its input unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from scipy import sparse
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
from scipy.signal import savgol_filter
from scipy.sparse.linalg import spsolve

from xrdbatch.pattern import Pattern


def _with(p: Pattern, two_theta=None, intensity=None, **metadata) -> Pattern:
    return replace(
        p,
        two_theta=p.two_theta if two_theta is None else two_theta,
        intensity=p.intensity if intensity is None else intensity,
        metadata={**p.metadata, **metadata},
        warnings=list(p.warnings),
    )


def crop(p: Pattern, tt_min: float | None, tt_max: float | None) -> Pattern:
    lo = -np.inf if tt_min is None else tt_min
    hi = np.inf if tt_max is None else tt_max
    mask = (p.two_theta >= lo) & (p.two_theta <= hi)
    return _with(p, p.two_theta[mask], p.intensity[mask])


def smooth(p: Pattern, window: int = 11, polyorder: int = 3) -> Pattern:
    """Savitzky–Golay smoothing. The window is made odd and no longer than the data."""
    n = len(p.intensity)
    window = min(int(window), n if n % 2 else n - 1)
    if window % 2 == 0:
        window -= 1
    if window <= polyorder:
        return _with(p)
    return _with(p, intensity=savgol_filter(p.intensity, window, polyorder))


def _als_baseline(y: np.ndarray, lam: float, p_asym: float, iterations: int = 10) -> np.ndarray:
    """Asymmetric least squares baseline (Eilers & Boelens, 2005)."""
    n = len(y)
    d = sparse.diags([1.0, -2.0, 1.0], [0, -1, -2], shape=(n, n - 2), format="csc")
    penalty = (lam * d.dot(d.T)).tocsc()
    w = np.ones(n)
    z = y
    for _ in range(iterations):
        weights = sparse.diags(w, 0, format="csc")
        z = spsolve(weights + penalty, w * y)
        w = p_asym * (y > z) + (1 - p_asym) * (y < z)
    return np.asarray(z)


def _rolling_min_baseline(y: np.ndarray, window: int) -> np.ndarray:
    """Morphological opening (min then max filter), then a moving average to smooth the steps."""
    window = max(3, min(int(window), len(y)))
    opened = maximum_filter1d(minimum_filter1d(y, window, mode="nearest"), window, mode="nearest")
    return uniform_filter1d(opened, window, mode="nearest")


def subtract_background(
    p: Pattern,
    method: Literal["als", "rolling_min", "none"] = "als",
    lam: float = 1e5,
    p_asym: float = 0.01,
    window: int = 101,
) -> Pattern:
    if method == "none" or len(p.intensity) < 3:
        return _with(p)
    if method == "als":
        background = _als_baseline(p.intensity, lam, p_asym)
    elif method == "rolling_min":
        background = _rolling_min_baseline(p.intensity, window)
    else:
        raise ValueError(f"Unknown background method: {method}")
    corrected = np.clip(p.intensity - background, 0, None)
    return _with(p, intensity=corrected, background=background)


def normalise(p: Pattern, mode: Literal["max", "area", "none"] = "max") -> Pattern:
    if mode == "none":
        return _with(p)
    if mode == "max":
        scale = np.max(p.intensity)
    elif mode == "area":
        scale = np.trapezoid(p.intensity, p.two_theta)
    else:
        raise ValueError(f"Unknown normalisation mode: {mode}")
    if not np.isfinite(scale) or scale <= 0:
        return _with(p)
    return _with(p, intensity=p.intensity / scale)


@dataclass(frozen=True)
class ProcessingSettings:
    tt_min: float | None = None
    tt_max: float | None = None
    smooth_window: int = 11
    smooth_polyorder: int = 3
    background: Literal["als", "rolling_min", "none"] = "als"
    als_lam: float = 1e5
    als_p: float = 0.01
    rolling_window: int = 101
    normalise: Literal["max", "area", "none"] = "max"


def process(p: Pattern, settings: ProcessingSettings) -> Pattern:
    """Apply crop → smooth → background → normalise."""
    out = crop(p, settings.tt_min, settings.tt_max)
    if settings.smooth_window > 1:
        out = smooth(out, settings.smooth_window, settings.smooth_polyorder)
    out = subtract_background(out, settings.background, settings.als_lam, settings.als_p, settings.rolling_window)
    return normalise(out, settings.normalise)
