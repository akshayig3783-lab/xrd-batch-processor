"""Validate detected peak positions on real RRUFF powder patterns.

Each mineral needs sample_data/<name>.txt (RRUFF "XY - Processed"). The reference is the RRUFF
.dif peak list when present, otherwise the reflection positions calculated from the refined
unit cell in the file header plus the space group's reflection conditions.
"""

from pathlib import Path

import pytest

from xrdbatch.peaks import find_peaks_table
from xrdbatch.processing import ProcessingSettings, process
from xrdbatch.readers import read_pattern
from xrdbatch.reference import allowed_two_theta, read_rruff_cell, read_rruff_dif

DATA = Path(__file__).parent.parent / "sample_data"
TOLERANCE_DEG = 0.05
RRUFF_WAVELENGTH = 1.541838  # Å, Cu Kα weighted average used by RRUFF powder patterns
MINERALS = {"quartz": "P3221", "corundum": "R-3c", "calcite": "R-3c"}


def validate(name: str, n_peaks: int = 5):
    """Return [(detected 2θ, nearest reference 2θ, Δ)] for the n strongest detected peaks."""
    path = DATA / f"{name}.txt"
    pattern = read_pattern(path)[0]
    table = find_peaks_table(process(pattern, ProcessingSettings()), RRUFF_WAVELENGTH)
    strongest = table.sort_values("intensity", ascending=False)["two_theta"].head(n_peaks)
    dif = DATA / f"{name}.dif"
    if dif.exists():
        reference = read_rruff_dif(dif)["two_theta"].tolist()
    else:
        reference = allowed_two_theta(read_rruff_cell(path), RRUFF_WAVELENGTH, tt_max=95, rule=MINERALS[name])
    rows = []
    for found in strongest:
        ref = min(reference, key=lambda r: abs(r - found))
        rows.append((found, ref, found - ref))
    return rows


@pytest.mark.parametrize("mineral", list(MINERALS))
def test_top_peaks_match_reference(mineral):
    if not (DATA / f"{mineral}.txt").exists():
        pytest.skip(f"RRUFF pattern for {mineral} not in sample_data/")
    rows = validate(mineral)
    assert len(rows) == 5
    for found, ref, delta in rows:
        assert abs(delta) <= TOLERANCE_DEG, f"{mineral}: found {found:.3f}°, nearest reference {ref:.3f}°"


def test_dif_parser(tmp_path):
    f = tmp_path / "x.dif"
    f.write_text(
        "      Quartz\n  CELL PARAMETERS: 4.91 4.91 5.40\n"
        "            2-THETA      INTENSITY    D-SPACING   H   K   L\n"
        "              20.86         21.50       4.2550   1   0   0\n"
        "              26.64        100.00       3.3435   1   0   1\n"
        "     ==========================================================\n"
    )
    assert read_rruff_dif(f)["two_theta"].tolist() == [26.64, 20.86]
