"""Validate peak positions against RRUFF reference peak lists.

Each mineral needs two files in sample_data/: <name>.txt (processed XY pattern) and <name>.dif.
Tests are skipped for minerals whose files are not present.
"""

from pathlib import Path

import pytest

from xrdbatch.peaks import find_peaks_table, resolve_wavelength
from xrdbatch.processing import ProcessingSettings, process
from xrdbatch.readers import read_pattern
from xrdbatch.reference import read_rruff_dif

DATA = Path(__file__).parent.parent / "sample_data"
TOLERANCE_DEG = 0.05
MINERALS = ["quartz", "corundum", "calcite"]


def validate(name: str, n_peaks: int = 5):
    pattern = read_pattern(DATA / f"{name}.txt")[0]
    reference = read_rruff_dif(DATA / f"{name}.dif")
    wavelength, _ = resolve_wavelength(pattern, 1.541838)
    table = find_peaks_table(process(pattern, ProcessingSettings()), wavelength)
    rows = []
    for ref_tt in reference["two_theta"].head(n_peaks):
        found = table["two_theta"].iloc[(table["two_theta"] - ref_tt).abs().argmin()] if len(table) else float("nan")
        rows.append((ref_tt, found, found - ref_tt))
    return rows


@pytest.mark.parametrize("mineral", MINERALS)
def test_top_peaks_match_reference(mineral):
    if not (DATA / f"{mineral}.txt").exists() or not (DATA / f"{mineral}.dif").exists():
        pytest.skip(f"RRUFF files for {mineral} not in sample_data/")
    for ref_tt, found, delta in validate(mineral):
        assert abs(delta) <= TOLERANCE_DEG, f"{mineral}: reference {ref_tt:.3f}°, found {found:.3f}°"


def test_dif_parser(tmp_path):
    f = tmp_path / "x.dif"
    f.write_text(
        "      Quartz\n  CELL PARAMETERS: 4.91 4.91 5.40\n"
        "            2-THETA      INTENSITY    D-SPACING   H   K   L\n"
        "              20.86         21.50       4.2550   1   0   0\n"
        "              26.64        100.00       3.3435   1   0   1\n"
        "     ==========================================================\n"
    )
    t = read_rruff_dif(f)
    assert t["two_theta"].tolist() == [26.64, 20.86]
