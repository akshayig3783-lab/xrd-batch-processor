# XRD Batch Processor

**Turn a folder of X-ray diffraction scans into peak tables, d-spacings, FWHM and crystallite sizes in seconds — instead of an afternoon in EVA, Origin or Excel.**

🔗 **Live demo:** _coming soon_ · ![tests](https://github.com/akshayig3783-lab/xrd-batch-processor/actions/workflows/tests.yml/badge.svg)

<!-- docs/demo.gif goes here -->

## Why
Labs routinely measure dozens of samples — temperature series, composition series, repeat measurements. Processing them one by one (background, peak positions, widths, Bragg and Scherrer calculations) is slow and error-prone. This tool does the whole batch with the same, documented settings, and exports results ready for a lab book or paper.

## Features
- **Batch upload** of many patterns at once; one bad file never stops the batch.
- **Formats:** `.xy`, `.csv`, `.txt`, `.dat` (whitespace, comma or semicolon; German decimal commas like `28,44;1520`; RRUFF headers) and **Bruker DIFFRAC `.brml`** (multi-scan files supported).
- **Processing:** 2θ crop, Savitzky–Golay smoothing, background removal (asymmetric least squares or rolling minimum), normalisation (max/area).
- **Peaks:** position, **d-spacing** (Bragg), intensity, relative intensity, **FWHM** (measured at half height, robust to overlapping peaks), **Scherrer crystallite size**.
- **Kα2 shoulder detection** (Cu, Co, Mo): peaks sitting at the Kα2 position of a stronger peak are flagged, so they aren't mistaken for extra phases.
- **Noise-aware:** a robust noise estimate keeps blank or amorphous samples from producing fake peaks.
- **Wavelengths:** Cu, Co, Mo Kα1 or custom — and the wavelength stored in the file wins when present (shown per pattern).
- **Plots:** interactive overlay and **stacked view** for series.
- **Export:** Excel peak tables, processed CSV + PNG plots (ZIP), self-contained HTML report with all settings.

## Quick start
```bash
git clone https://github.com/akshayig3783-lab/xrd-batch-processor.git
cd xrd-batch-processor
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
Click **Load demo data** to try it without your own files.

## Validation
The automated test suite runs the full pipeline (default settings) on real powder patterns from the [RRUFF database](https://rruff.info) and checks the five strongest detected peaks of each mineral against reflection positions **calculated from the refined unit cell** in each file (Bragg's law + space-group reflection conditions; Cu Kα, λ = 1.541838 Å). Tolerance: ±0.05° 2θ.

| Mineral | Found 2θ (°) | Calculated 2θ (°) | Δ (°) |
|---|---|---|---|
| quartz | 26.680 | 26.664 | +0.016 |
| quartz | 20.900 | 20.876 | +0.024 |
| quartz | 36.580 | 36.577 | +0.003 |
| quartz | 68.350 | 68.379 | -0.029 |
| quartz | 45.830 | 45.837 | -0.007 |
| corundum | 35.210 | 35.172 | +0.038 |
| corundum | 25.640 | 25.591 | +0.049 |
| corundum | 43.410 | 43.380 | +0.030 |
| corundum | 57.560 | 57.537 | +0.023 |
| corundum | 37.840 | 37.798 | +0.042 |
| calcite | 29.480 | 29.443 | +0.037 |
| calcite | 47.590 | 47.579 | +0.011 |
| calcite | 36.040 | 36.019 | +0.021 |
| calcite | 39.480 | 39.465 | +0.015 |
| calcite | 48.590 | 48.577 | +0.013 |

All 15 within tolerance (max |Δ| = 0.049°). Regenerate with `python scripts/validation_table.py`.

Run the tests: `python -m pytest --cov=xrdbatch`

## Supported formats
| Format | Status |
|---|---|
| `.xy` / `.csv` / `.txt` / `.dat` | ✅ |
| Bruker `.brml` | ✅ tested on a public sample file — **if you have a `.brml` from your instrument, please open an issue; I'd like to test with it** |
| Bruker `.raw`, PANalytical `.xrdml`, Rigaku `.rasx` | planned |

## Limitations
- **No phase identification** (needs licensed databases such as ICDD PDF-4+) and **no Rietveld refinement**.
- **Scherrer sizes are not corrected for instrumental broadening or microstrain** — treat them as lower-bound estimates.
- Single-crystal, texture, residual-stress and reflectometry analyses are out of scope.
- 2D/area-detector frames (e.g. reciprocal-space maps) are skipped.
- Kα2 contributions are **flagged, not stripped**; widths of Kα1 peaks with an unresolved Kα2 shoulder are slightly overestimated.

## Project structure
```
xrdbatch/readers/   one reader per file format → Pattern
xrdbatch/processing.py   crop, smooth, background, normalise (pure functions)
xrdbatch/peaks.py        peaks, d-spacing, FWHM, Scherrer
xrdbatch/report.py       plots, Excel/CSV export, HTML report
app.py                   Streamlit interface
tests/                   pytest suite (synthetic data with known answers + RRUFF references)
```

## Data credits
- RRUFF Project — Lafuente B, Downs R T, Yang H, Stone N (2015) *The power of databases: the RRUFF project.* In: Highlights in Mineralogical Crystallography, De Gruyter, pp 1–30.
- Bruker sample file from [FAIRmat-NFDI/readers-xrd](https://github.com/FAIRmat-NFDI/readers-xrd) (Apache-2.0).

## Licence
MIT
