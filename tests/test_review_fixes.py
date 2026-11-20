"""Regression tests for findings from the final review."""

import numpy as np
import pytest

from conftest import gaussian
from xrdbatch.pattern import Pattern, make_unique_names
from xrdbatch.peaks import find_peaks_table
from xrdbatch.processing import ProcessingSettings, process
from xrdbatch.readers.text import read_text

CU = 1.5406


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# 1 (critical): crop that leaves no data must not crash
def test_process_crop_outside_data_returns_empty_pattern(synthetic):
    p = process(synthetic, ProcessingSettings(tt_min=100, tt_max=160))
    assert len(p.two_theta) == 0


# 2: noise-only pattern through the real pipeline gives no peaks
def test_noise_only_pattern_has_no_peaks_after_processing():
    rng = np.random.default_rng(3)
    tt = np.round(np.arange(10, 80, 0.02), 4)
    p = process(Pattern("noise", tt, 100 + rng.normal(0, 3, tt.size)), ProcessingSettings())
    assert len(find_peaks_table(p, CU)) == 0


def test_real_peak_on_noise_still_found_after_processing(synthetic):
    table = find_peaks_table(process(synthetic, ProcessingSettings()), CU)
    assert len(table) == 1
    assert table["two_theta"].iloc[0] == pytest.approx(30.0, abs=0.02)


# 3: FWHM of overlapping peaks measured at half height, not half prominence
def test_fwhm_of_overlapping_peaks():
    tt = np.round(np.arange(28, 32, 0.005), 4)
    y = gaussian(tt, 30.0, 1.0, 0.1) + gaussian(tt, 30.35, 0.5, 0.1)
    table = find_peaks_table(Pattern("pair", tt, y), CU)
    assert len(table) == 2
    assert table["fwhm"].tolist() == pytest.approx([0.2355, 0.2355], rel=0.10)


# 4: German decimal comma with tab or space delimiters
@pytest.mark.parametrize("sep", ["\t", " "])
def test_decimal_comma_with_tab_or_space(tmp_path, sep):
    p = read_text(_write(tmp_path, "g.txt", f"28,44{sep}1520\n28,46{sep}1490\n"))
    assert p.two_theta.tolist() == pytest.approx([28.44, 28.46])
    assert p.intensity.tolist() == [1520, 1490]


# 5: decimal-comma wavelength and implausible wavelengths
def test_decimal_comma_wavelength(tmp_path):
    p = read_text(_write(tmp_path, "w.txt", "# Wavelength: 1,5406\n20 1\n21 2\n"))
    assert p.wavelength == pytest.approx(1.5406)


def test_wavelength_header_without_comment_marker(tmp_path):
    p = read_text(_write(tmp_path, "w2.txt", "Wavelength=1.789\n20 1\n21 2\n"))
    assert p.wavelength == pytest.approx(1.789)


def test_implausible_wavelength_ignored_with_warning(tmp_path):
    p = read_text(_write(tmp_path, "w3.txt", "# WAVELENGTH=15406\n20 1\n21 2\n"))
    assert p.wavelength is None
    assert any("wavelength" in w.lower() for w in p.warnings)


# 6: duplicate pattern names get unique suffixes
def test_make_unique_names():
    tt = np.arange(3.0)
    ps = [Pattern("S1", tt, tt), Pattern("S1", tt, tt), Pattern("S2", tt, tt), Pattern("S1", tt, tt)]
    assert [p.name for p in make_unique_names(ps)] == ["S1", "S1 (2)", "S2", "S1 (3)"]
