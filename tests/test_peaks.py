import numpy as np
import pytest

from conftest import gaussian
from xrdbatch.constants import WAVELENGTHS
from xrdbatch.pattern import Pattern
from xrdbatch.peaks import COLUMNS, d_spacing, find_peaks_table, resolve_wavelength, scherrer_size_nm

CU = WAVELENGTHS["Cu Kα1"]


def test_wavelength_constants():
    assert WAVELENGTHS == {"Cu Kα1": 1.5406, "Co Kα1": 1.78897, "Mo Kα1": 0.70932}


def test_d_spacing_si_111():
    assert d_spacing(28.443, CU) == pytest.approx(3.1356, abs=1e-3)


def test_scherrer_known_value():
    expected = 0.9 * 0.15406 / (np.radians(0.2) * np.cos(np.radians(15)))
    assert scherrer_size_nm(0.2, 30.0, CU) == pytest.approx(expected, rel=1e-2)
    assert expected == pytest.approx(41.1, abs=0.1)


def test_finds_synthetic_peaks():
    tt = np.round(np.arange(20, 60.0001, 0.01), 4)
    y = gaussian(tt, 30.0, 1.0, 0.1) + gaussian(tt, 45.0, 0.5, 0.15)
    table = find_peaks_table(Pattern("s", tt, y), CU)
    assert len(table) == 2
    assert table["two_theta"].tolist() == pytest.approx([30.0, 45.0], abs=0.02)
    assert table["fwhm"].tolist() == pytest.approx([2.3548 * 0.1, 2.3548 * 0.15], rel=0.05)
    assert table["rel_intensity"].max() == pytest.approx(100)
    assert (table["pattern"] == "s").all()


def test_flat_pattern_returns_empty_table():
    rng = np.random.default_rng(1)
    tt = np.arange(20, 60, 0.02)
    table = find_peaks_table(Pattern("flat", tt, 100 + rng.normal(0, 0.5, tt.size)), CU, prominence=0.5)
    assert len(table) == 0
    assert list(table.columns) == COLUMNS


def test_all_zero_pattern_returns_empty_table():
    tt = np.arange(20, 60, 0.02)
    assert len(find_peaks_table(Pattern("zero", tt, np.zeros_like(tt)), CU)) == 0


def test_columns_exact():
    assert COLUMNS == ["pattern", "two_theta", "d_spacing", "intensity", "rel_intensity", "fwhm", "crystallite_size_nm", "ka2_shoulder"]


def test_resolve_wavelength_prefers_file():
    tt = np.arange(3.0)
    assert resolve_wavelength(Pattern("a", tt, tt, wavelength=1.78897), CU) == (1.78897, "file")
    assert resolve_wavelength(Pattern("b", tt, tt), CU) == (CU, "user")


def test_flags_cu_ka2_shoulder():
    # Kα1 peak at 47.59°, Kα2 partner where Bragg's law puts it for λ = 1.544390 Å, half the height
    d = 1.540562 / (2 * np.sin(np.radians(47.59 / 2)))
    ka2_tt = 2 * np.degrees(np.arcsin(1.544390 / (2 * d)))
    tt = np.round(np.arange(46, 49, 0.005), 4)
    y = gaussian(tt, 47.59, 1.0, 0.03) + gaussian(tt, ka2_tt, 0.5, 0.03)
    table = find_peaks_table(Pattern("c", tt, y), CU)
    assert table["ka2_shoulder"].tolist() == [False, True]


def test_no_ka2_flag_for_unrelated_peaks():
    tt = np.round(np.arange(20, 60.0001, 0.01), 4)
    y = gaussian(tt, 30.0, 1.0, 0.1) + gaussian(tt, 45.0, 0.5, 0.15)
    assert not find_peaks_table(Pattern("s", tt, y), CU)["ka2_shoulder"].any()
