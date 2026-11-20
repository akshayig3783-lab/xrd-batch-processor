import zipfile
from pathlib import Path

import numpy as np
import pytest

from xrdbatch.readers import read_pattern
from xrdbatch.readers.bruker import read_brml

SAMPLE = Path(__file__).parent / "data" / "sample.brml"

_RAW = """<?xml version="1.0"?>
<RawData xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <DataRoutes><DataRoute>
    <Datum>1,1,{a},10</Datum>
    <Datum>1,1,{b},20</Datum>
    <Datum>1,1,{c},30</Datum>
    <DataViews>
      <RawDataView xsi:type="FixedRawDataView" Start="0" Length="1" LogicName="MeasuredTime" />
      <RawDataView xsi:type="FixedRawDataView" Start="1" Length="1" LogicName="AbsorptionFactor" />
      <RawDataView xsi:type="VaryingRawDataView" Start="2" Length="1">
        <Varying><FieldDefinitions FieldName="TwoTheta" AxisId="TwoTheta" /></Varying>
      </RawDataView>
      <RawDataView xsi:type="RecordedRawDataView" Start="3" Length="1" />
    </DataViews>
  </DataRoute></DataRoutes>
  <FixedInformation><Instrument><PrimaryTracks><TrackInfoData><MountedOptics><InfoData>
    <Tube><TubeMaterial>Co</TubeMaterial><WaveLengthAlpha1 Value="1.78897" /></Tube>
  </InfoData></MountedOptics></TrackInfoData></PrimaryTracks></Instrument></FixedInformation>
</RawData>
"""


def _make_brml(path, n_datasets):
    with zipfile.ZipFile(path, "w") as z:
        for i in range(n_datasets):
            z.writestr(f"Experiment0/RawData{i}.xml", _RAW.format(a=10 + i, b=11 + i, c=12 + i))
    return path


def test_brml_returns_patterns():
    result = read_brml(SAMPLE)
    assert len(result) >= 1
    p = result[0]
    assert len(p.two_theta) == len(p.intensity) == 2001
    assert np.all(np.diff(p.two_theta) > 0)
    assert p.two_theta[0] == pytest.approx(44.0)
    assert p.two_theta[-1] == pytest.approx(48.0)


def test_brml_reads_wavelength():
    p = read_brml(SAMPLE)[0]
    assert p.wavelength == pytest.approx(1.5406)
    assert p.metadata["anode"] == "Cu"


def test_brml_multiple_datasets(tmp_path):
    result = read_brml(_make_brml(tmp_path / "x.brml", 2))
    assert [p.name for p in result] == ["x#1", "x#2"]
    assert list(result[1].two_theta) == [11, 12, 13]
    assert list(result[0].intensity) == [10, 20, 30]
    assert result[0].wavelength == pytest.approx(1.78897)


def test_brml_single_dataset_named_by_stem(tmp_path):
    assert read_brml(_make_brml(tmp_path / "y.brml", 1))[0].name == "y"


def test_brml_corrupt_zip_raises_clear_error(tmp_path):
    bad = tmp_path / "bad.brml"
    bad.write_bytes(b"not a zip at all")
    with pytest.raises(ValueError, match="not a valid .brml"):
        read_brml(bad)


def test_read_pattern_dispatches_brml():
    assert read_pattern(SAMPLE)[0].metadata["format"] == "brml"
