# Decision: Bruker .brml reader

- **Own parser** (stdlib `zipfile` + `xml.etree`), no extra dependency.
- `.brml` = zip; each scan is `Experiment*/RawData*.xml`. Points are `<Datum>` CSV rows.
  Column meaning comes from `<DataViews>`: the `VaryingRawDataView` with a `FieldDefinitions FieldName="TwoTheta"`
  gives the 2θ column (`Start` + position), the first `RecordedRawDataView` gives the counts column (`Start`).
- Wavelength: `WaveLengthAlpha1 Value="..."` (Å); anode: `<TubeMaterial>`.
- Public sample: `tests/data/sample.brml` from FAIRmat-NFDI/readers-xrd (Apache-2.0), a Cu 2θ–ω scan, 44–48°, 2001 points.
- Datasets with fewer than 2 points (e.g., fixed-PSD frames in reciprocal-space maps) are skipped with a warning.
- `.raw` (binary) is out of scope for now.
