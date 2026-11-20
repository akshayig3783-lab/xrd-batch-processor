"""Streamlit front end for xrdbatch. Run with:  streamlit run app.py"""

from __future__ import annotations

import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from xrdbatch.constants import SCHERRER_CAVEAT, WAVELENGTHS
from xrdbatch.pattern import make_unique_names
from xrdbatch.peaks import find_peaks_table, resolve_wavelength
from xrdbatch.processing import ProcessingSettings, process
from xrdbatch.readers import read_pattern, supported_extensions
from xrdbatch.report import build_html_report, figure_to_png, peaks_to_excel, plot_pattern, processed_to_csv

SAMPLE_DIR = Path(__file__).parent / "sample_data"

st.set_page_config(page_title="XRD Batch Processor", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=False)
def load_file(name: str, data: bytes):
    """Read one uploaded file; returns (patterns, error message or None)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.write_bytes(data)
        try:
            patterns = read_pattern(path)
        except Exception as exc:  # one bad file must never stop the batch
            return [], f"{name}: {exc}"
    for p in patterns:
        p.metadata.setdefault("source", name)
    return patterns, None


@st.cache_data(show_spinner=False)
def analyse(p, settings: ProcessingSettings, ui_wavelength: float, prominence: float, k: float):
    """Process one pattern and find its peaks; cached so unchanged settings cost nothing on rerun."""
    q = process(p, settings)
    if len(q.two_theta) < 3:
        return None, None, None, f"{p.name}: no data left inside the selected 2θ range."
    wl, source = resolve_wavelength(p, ui_wavelength)
    return q, find_peaks_table(q, wl, prominence=prominence, k=k), (wl, source), None


def demo_files() -> list[tuple[str, bytes]]:
    exts = set(supported_extensions())
    return [(f.name, f.read_bytes()) for f in sorted(SAMPLE_DIR.iterdir()) if f.suffix.lower() in exts]


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1 · Data")
    uploads = st.file_uploader(
        "Upload XRD files", type=[e.lstrip(".") for e in supported_extensions()], accept_multiple_files=True
    )
    if st.button("Load demo data", key="demo"):
        st.session_state["use_demo"] = True
    if st.session_state.get("use_demo") and st.button("Clear demo data", key="clear_demo"):
        st.session_state["use_demo"] = False
        st.rerun()

    st.header("2 · Instrument")
    tube = st.selectbox("Wavelength (used when the file doesn't state one)", [*WAVELENGTHS, "Custom"])
    ui_wavelength = (
        st.number_input("Custom wavelength (Å)", 0.1, 5.0, 1.5406, step=0.0001, format="%.5f")
        if tube == "Custom"
        else WAVELENGTHS[tube]
    )

    st.header("3 · Processing")
    tt_range = st.slider("2θ range (°)", 0.0, 160.0, (0.0, 160.0), step=0.5)
    smooth_window = st.slider("Smoothing window (points, 1 = off)", 1, 51, 11, step=2)
    background = st.selectbox(
        "Background", ["als", "rolling_min", "none"],
        format_func={"als": "Asymmetric least squares", "rolling_min": "Rolling minimum", "none": "None"}.get,
    )
    als_lam = st.select_slider("ALS stiffness λ", [1e3, 1e4, 1e5, 1e6, 1e7], value=1e5, format_func=lambda v: f"{v:.0e}")
    norm = st.selectbox("Normalise", ["max", "area", "none"])

    st.header("4 · Peaks")
    prominence = st.slider("Minimum prominence (% of max)", 1, 50, 5) / 100
    k = st.number_input("Scherrer constant K", 0.5, 1.5, 0.9, step=0.01)

settings = ProcessingSettings(
    tt_min=tt_range[0], tt_max=tt_range[1], smooth_window=smooth_window, background=background,
    als_lam=als_lam, normalise=norm,
)

# ---------------------------------------------------------------- load
files = [(u.name, u.getvalue()) for u in (uploads or [])]
if st.session_state.get("use_demo"):
    files += demo_files()

st.title("XRD Batch Processor")
st.caption("Batch background removal, peak finding, d-spacing, FWHM and Scherrer size for X-ray diffraction patterns.")

if not files:
    st.info("Upload .xy / .csv / .txt / .dat / Bruker .brml files in the sidebar, or click **Load demo data**.")
    st.stop()

raw, errors = [], []
for name, data in files:
    patterns, error = load_file(name, data)
    raw.extend(patterns)
    if error and not patterns:
        errors.append(error)
for error in errors:
    st.warning(f"Could not read {error}")
if not raw:
    st.stop()
make_unique_names(raw)

processed, tables, wavelengths = [], {}, {}
for p in raw:
    try:
        q, table, wl_info, problem = analyse(p, settings, ui_wavelength, prominence, k)
    except Exception as exc:  # one bad pattern must never stop the batch
        q, problem = None, f"{p.name}: processing failed ({exc})"
    if q is None:
        st.warning(problem)
        continue
    processed.append(q)
    wavelengths[q.name] = wl_info
    tables[q.name] = table

if not processed:
    st.stop()

# ---------------------------------------------------------------- tabs
overview, peaks_tab, export = st.tabs(["Overview", "Peaks", "Export"])

with overview:
    stacked = st.toggle("Stacked view", value=False)
    shift = 1.1 * max(float(q.intensity.max()) for q in processed)
    fig = go.Figure()
    for i, q in enumerate(processed):
        fig.add_trace(go.Scatter(x=q.two_theta, y=q.intensity + (i * shift if stacked else 0), mode="lines", name=q.name))
    fig.update_layout(xaxis_title="2θ (°)", yaxis_title="Intensity", height=520, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{len(processed)} pattern(s) · {sum(len(t) for t in tables.values())} peaks found")

with peaks_tab:
    st.caption(SCHERRER_CAVEAT)
    for q in processed:
        wl, source = wavelengths[q.name]
        st.subheader(q.name)
        st.caption(f"Wavelength: {wl:.5f} Å ({'from file' if source == 'file' else 'sidebar setting'})")
        for w in q.warnings:
            st.warning(w)
        st.dataframe(tables[q.name].round(4), use_container_width=True, hide_index=True)

def build_zip() -> bytes:
    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        for q in processed:
            safe = "".join(c if c.isalnum() or c in "-_#" else "_" for c in q.name)
            z.writestr(f"{safe}_processed.csv", processed_to_csv(q))
            z.writestr(f"{safe}.png", figure_to_png(plot_pattern(q, tables[q.name])))
    return zbuf.getvalue()


with export:
    st.dataframe(pd.concat(tables.values(), ignore_index=True).round(4), hide_index=True, use_container_width=True)
    # Export files are built only on request: plots for many patterns are slow to render.
    if st.button("Prepare download files", key="prepare_exports"):
        with st.spinner("Building Excel, ZIP and HTML report…"):
            excel, zipped = peaks_to_excel(tables), build_zip()
            html = build_html_report(processed, tables, settings, wavelengths)
        st.download_button(
            "Peak tables (Excel)", excel, "xrd_peaks.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
        )
        st.download_button("Processed data + plots (ZIP)", zipped, "xrd_processed.zip", "application/zip", on_click="ignore")
        st.download_button("HTML report", html, "xrd_report.html", "text/html", on_click="ignore")
