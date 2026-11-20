from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from conftest import gaussian
from xrdbatch.pattern import Pattern
from xrdbatch.peaks import find_peaks_table
from xrdbatch.processing import ProcessingSettings
from xrdbatch.report import (
    build_html_report,
    peaks_to_excel,
    plot_overlay,
    plot_pattern,
    processed_to_csv,
)


@pytest.fixture
def batch():
    tt = np.round(np.arange(20, 60.0001, 0.02), 4)
    a = Pattern("alpha", tt, gaussian(tt, 30, 1.0, 0.1))
    b = Pattern("beta", tt, gaussian(tt, 40, 0.8, 0.1))
    tables = {p.name: find_peaks_table(p, 1.5406) for p in (a, b)}
    return [a, b], tables


def test_excel_roundtrip(batch):
    _, tables = batch
    sheets = pd.read_excel(BytesIO(peaks_to_excel(tables)), sheet_name=None)
    assert set(sheets) == {"alpha", "beta", "All"}
    assert len(sheets["All"]) == 2


def test_excel_sheet_names_are_sanitised():
    t = {"a/b:c*d?" + "x" * 40: pd.DataFrame({"two_theta": [1.0]})}
    sheets = pd.read_excel(BytesIO(peaks_to_excel(t)), sheet_name=None)
    assert all(len(name) <= 31 and "/" not in name for name in sheets)


def test_csv_roundtrip(batch):
    (a, _), _ = batch
    df = pd.read_csv(BytesIO(processed_to_csv(a)))
    assert list(df.columns) == ["two_theta", "intensity"]
    assert np.allclose(df["intensity"], a.intensity, atol=1e-9)


def test_html_report_contains_essentials(batch):
    patterns, tables = batch
    html = build_html_report(patterns, tables, ProcessingSettings(), {"alpha": (1.5406, "user"), "beta": (1.78897, "file")})
    for text in ["alpha", "beta", "<img", "instrumental broadening", "1.5406", "1.78897", "from file"]:
        assert text in html


def test_overlay_stacked_offsets(batch):
    patterns, _ = batch
    fig = plot_overlay(patterns, stacked=True)
    minima = [line.get_ydata().min() for line in fig.axes[0].get_lines()]
    assert minima == sorted(minima) and minima[0] < minima[1]


def test_plot_pattern_marks_peaks(batch):
    (a, _), tables = batch
    fig = plot_pattern(a, tables["alpha"])
    assert len(fig.axes[0].collections) >= 1
