"""Plots, file exports and the HTML report."""

from __future__ import annotations

import base64
import re
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402

from xrdbatch.constants import SCHERRER_CAVEAT  # noqa: E402
from xrdbatch.pattern import Pattern  # noqa: E402
from xrdbatch.processing import ProcessingSettings  # noqa: E402

_TEMPLATES = Path(__file__).parent / "templates"


def plot_pattern(p: Pattern, peaks: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(p.two_theta, p.intensity, lw=1, color="#1f4e79")
    if len(peaks):
        ax.scatter(peaks["two_theta"], peaks["intensity"], marker="v", color="#c0392b", zorder=3, s=25)
    ax.set_xlabel("2θ (°)")
    ax.set_ylabel("Intensity")
    ax.set_title(p.name)
    fig.tight_layout()
    return fig


def plot_overlay(patterns: list[Pattern], stacked: bool = False, offset: float = 1.1) -> plt.Figure:
    """Overlay all patterns; ``stacked`` shifts each one up by ``offset`` × the largest maximum."""
    fig, ax = plt.subplots(figsize=(8, 4 + (0.4 * len(patterns) if stacked else 0)))
    shift = offset * max((float(p.intensity.max()) for p in patterns if len(p.intensity)), default=1.0)
    for i, p in enumerate(patterns):
        ax.plot(p.two_theta, p.intensity + (i * shift if stacked else 0), lw=1, label=p.name)
    ax.set_xlabel("2θ (°)")
    ax.set_ylabel("Intensity" + (" (offset)" if stacked else ""))
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def _sheet_name(name: str, used: set[str]) -> str:
    base = re.sub(r"[\[\]:*?/\\]", "_", name)[:31] or "pattern"
    candidate, n = base, 1
    while candidate in used:
        suffix = f"_{n}"
        candidate, n = base[: 31 - len(suffix)] + suffix, n + 1
    used.add(candidate)
    return candidate


def peaks_to_excel(tables: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    used: set[str] = {"All"}
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, table in tables.items():
            table.to_excel(writer, sheet_name=_sheet_name(name, used), index=False)
        frames = [t for t in tables.values() if len(t)]
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        combined.to_excel(writer, sheet_name="All", index=False)
    return buffer.getvalue()


def processed_to_csv(p: Pattern) -> bytes:
    return pd.DataFrame({"two_theta": p.two_theta, "intensity": p.intensity}).to_csv(index=False).encode("utf-8")


def _figure_to_base64(fig: plt.Figure) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def figure_to_png(fig: plt.Figure) -> bytes:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    return buffer.getvalue()


def build_html_report(
    patterns: list[Pattern],
    tables: dict[str, pd.DataFrame],
    settings: ProcessingSettings,
    wavelengths: dict[str, tuple[float, str]],
) -> str:
    env = Environment(loader=FileSystemLoader(_TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
    sections = []
    for p in patterns:
        table = tables.get(p.name, pd.DataFrame())
        wl, source = wavelengths.get(p.name, (None, "user"))
        sections.append(
            {
                "name": p.name,
                "image": _figure_to_base64(plot_pattern(p, table)),
                "table": table.round(4).to_html(index=False, classes="peaks", border=0),
                "wavelength": wl,
                "source": "from file" if source == "file" else "user setting",
                "warnings": p.warnings,
            }
        )
    overview = _figure_to_base64(plot_overlay(patterns, stacked=True)) if patterns else None
    return env.get_template("report.html.j2").render(
        overview=overview,
        sections=sections,
        settings=vars(settings),
        caveat=SCHERRER_CAVEAT,
    )
