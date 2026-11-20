"""Reader for Bruker DIFFRAC ``.brml`` files.

A ``.brml`` is a zip archive. Each scan is stored as ``Experiment*/RawData<n>.xml``,
with one ``<Datum>`` comma-separated row per measured point. The ``<DataViews>``
block says which column holds 2θ and which holds the detector counts.
See docs/decisions/bruker-reader.md.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from xrdbatch.pattern import Pattern, clean

_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
_RAWDATA_RE = re.compile(r"RawData(\d+)\.xml$", re.IGNORECASE)


def _parse_xml(data: bytes) -> ET.Element:
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        # Some DIFFRAC files declare no encoding but contain Windows-1252 characters (e.g. "°").
        return ET.fromstring(data.decode("cp1252", errors="replace").encode("utf-8"))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_columns(root: ET.Element) -> tuple[int, int]:
    """Return (two_theta_column, counts_column) from the DataViews block."""
    tt_col = counts_col = None
    for view in root.iter():
        if _local(view.tag) != "RawDataView":
            continue
        start = int(view.get("Start", "0"))
        kind = view.get(_XSI_TYPE, "")
        if kind == "VaryingRawDataView" and tt_col is None:
            fields = [f.get("FieldName") for f in view.iter() if _local(f.tag) == "FieldDefinitions"]
            if "TwoTheta" in fields:
                tt_col = start + fields.index("TwoTheta")
        elif kind == "RecordedRawDataView" and counts_col is None:
            counts_col = start
    if tt_col is None or counts_col is None:
        raise ValueError("could not find 2θ and counts columns in DataViews")
    return tt_col, counts_col


def _instrument_info(root: ET.Element) -> tuple[float | None, str | None]:
    wavelength = anode = None
    for el in root.iter():
        name = _local(el.tag)
        if name == "WaveLengthAlpha1" and wavelength is None and el.get("Value"):
            wavelength = float(el.get("Value"))
        elif name == "TubeMaterial" and anode is None and el.text:
            anode = el.text.strip()
    return wavelength, anode


def _read_dataset(root: ET.Element) -> tuple[list[float], list[float]]:
    tt_col, counts_col = _find_columns(root)
    tt, y = [], []
    for datum in root.iter():
        if _local(datum.tag) != "Datum" or not datum.text:
            continue
        values = datum.text.split(",")
        tt.append(float(values[tt_col]))
        y.append(float(values[counts_col]))
    return tt, y


def read_brml(path) -> list[Pattern]:
    path = Path(path)
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"{path.name} is not a valid .brml file (not a zip archive).") from exc

    with archive:
        members = sorted(
            (m for m in archive.namelist() if _RAWDATA_RE.search(m)),
            key=lambda m: (m.split("/")[0], int(_RAWDATA_RE.search(m).group(1))),
        )
        if not members:
            raise ValueError(f"{path.name} is not a valid .brml file (no RawData*.xml inside).")

        datasets, skipped = [], 0
        for member in members:
            root = _parse_xml(archive.read(member))
            tt, y = _read_dataset(root)
            if len(tt) < 2:
                skipped += 1
                continue
            datasets.append((member, root, tt, y))

    if not datasets:
        raise ValueError(f"{path.name}: no scan with at least 2 points (2D/area-detector frames are not supported).")

    patterns = []
    for i, (member, root, tt, y) in enumerate(datasets, start=1):
        wavelength, anode = _instrument_info(root)
        two_theta, intensity, warnings = clean(tt, y)
        if skipped:
            warnings.append(f"Skipped {skipped} dataset(s) with fewer than 2 points.")
        name = path.stem if len(datasets) == 1 else f"{path.stem}#{i}"
        patterns.append(
            Pattern(
                name=name,
                two_theta=two_theta,
                intensity=intensity,
                wavelength=wavelength,
                metadata={
                    "source": path.name,
                    "format": "brml",
                    "dataset": member,
                    "anode": anode,
                    "scan_range": (float(two_theta[0]), float(two_theta[-1])),
                    "step": float((two_theta[-1] - two_theta[0]) / (len(two_theta) - 1)),
                },
                warnings=warnings,
            )
        )
    return patterns
