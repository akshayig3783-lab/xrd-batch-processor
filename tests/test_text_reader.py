import numpy as np
import pytest

from xrdbatch.readers import UnsupportedFormatError, read_pattern
from xrdbatch.readers.text import read_text


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_reads_space_separated_xy(tmp_path):
    f = _write(tmp_path, "a.xy", "10.0 5\n10.02 6\n10.04 7\n10.06 8\n10.08 9\n")
    p = read_text(f)
    assert len(p.two_theta) == 5 and len(p.intensity) == 5
    assert p.two_theta[0] == 10.0
    assert p.name == "a"


def test_reads_csv_with_header(tmp_path):
    f = _write(tmp_path, "b.csv", "2Theta,Intensity\n20.0,100\n20.1,110\n20.2,120\n")
    p = read_text(f)
    assert list(p.two_theta) == [20.0, 20.1, 20.2]
    assert list(p.intensity) == [100, 110, 120]


def test_reads_german_decimal_comma_semicolon(tmp_path):
    f = _write(tmp_path, "c.txt", "Winkel;Intensität\n28,44;1520\n28,46;1490\n")
    p = read_text(f)
    assert p.two_theta[0] == pytest.approx(28.44)
    assert p.intensity[0] == 1520


def test_reads_rruff_header_and_wavelength(tmp_path):
    text = "##NAMES=Quartz\n##RRUFFID=R040031\n##X-RAY WAVELENGTH=1.541838\n20.00, 12\n20.01, 13\n##END=\n"
    p = read_text(_write(tmp_path, "q.txt", text))
    assert p.wavelength == pytest.approx(1.541838)
    assert list(p.two_theta) == [20.00, 20.01]


def test_cleans_unsorted_duplicates_nan(tmp_path):
    f = _write(tmp_path, "d.xy", "12 30\n10 10\n11 20\n11 40\nnan 5\n")
    p = read_text(f)
    assert list(p.two_theta) == [10, 11, 12]
    assert list(p.intensity) == [10, 30, 30]
    assert len(p.warnings) >= 1


def test_unsupported_extension_raises(tmp_path):
    f = _write(tmp_path, "x.foo", "1 2\n")
    with pytest.raises(UnsupportedFormatError, match=r"\.foo"):
        read_pattern(f)


def test_read_pattern_dispatches_text(tmp_path):
    f = _write(tmp_path, "e.dat", "1 2\n2 3\n")
    result = read_pattern(f)
    assert len(result) == 1 and isinstance(result[0].two_theta, np.ndarray)
