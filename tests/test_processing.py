import numpy as np
import pytest

from xrdbatch.processing import (
    ProcessingSettings,
    crop,
    normalise,
    process,
    smooth,
    subtract_background,
)


def _region(p, lo, hi):
    m = (p.two_theta >= lo) & (p.two_theta <= hi)
    return p.intensity[m]


def test_crop_limits(synthetic):
    p = crop(synthetic, 20, 40)
    assert p.two_theta.min() >= 20 and p.two_theta.max() <= 40


def test_smooth_preserves_peak_position(synthetic):
    p = smooth(synthetic)
    assert p.two_theta[np.argmax(p.intensity)] == pytest.approx(30.0, abs=0.02)


def test_smooth_window_larger_than_data_is_safe(synthetic):
    short = crop(synthetic, 29.9, 30.0)
    assert len(smooth(short, window=101).intensity) == len(short.intensity)


def test_background_removed(synthetic):
    p = subtract_background(synthetic, method="als")
    assert abs(np.median(_region(p, 50, 70))) <= 10
    assert p.intensity.max() == pytest.approx(1000, rel=0.10)
    assert np.all(p.intensity >= 0)
    assert "background" in p.metadata


def test_rolling_min_background_also_works(synthetic):
    p = subtract_background(synthetic, method="rolling_min")
    assert abs(np.median(_region(p, 50, 70))) <= 20
    assert p.intensity.max() == pytest.approx(1000, rel=0.10)


def test_normalise_max(synthetic):
    assert normalise(synthetic, "max").intensity.max() == pytest.approx(1)


def test_normalise_area(synthetic):
    p = normalise(synthetic, "area")
    assert np.trapezoid(p.intensity, p.two_theta) == pytest.approx(1)


def test_functions_do_not_mutate_input(synthetic):
    before = synthetic.intensity.copy()
    process(synthetic, ProcessingSettings())
    assert np.array_equal(synthetic.intensity, before)
    assert "background" not in synthetic.metadata


def test_process_defaults_end_normalised(synthetic):
    p = process(synthetic, ProcessingSettings(tt_min=20, tt_max=40))
    assert p.intensity.max() == pytest.approx(1)
    assert p.two_theta.min() >= 20
