"""Render shear-force, bending-moment and deflection diagrams as base64 PNGs."""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")  # headless rendering

import matplotlib.pyplot as plt  # noqa: E402

from .analysis import AnalysisResult  # noqa: E402


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def _style(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Position along beam (m)")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="#333", linewidth=1)


def render_diagrams(result: AnalysisResult) -> dict:
    """Return a dict of base64 PNG data URIs keyed by diagram name."""
    x = result.x

    fig_s, ax_s = plt.subplots(figsize=(7, 2.8))
    ax_s.fill_between(x, result.shear, color="#2563eb", alpha=0.25)
    ax_s.plot(x, result.shear, color="#2563eb", linewidth=2)
    _style(ax_s, "Shear Force Diagram", "Shear (kN)")
    shear_png = _fig_to_base64(fig_s)

    fig_m, ax_m = plt.subplots(figsize=(7, 2.8))
    ax_m.fill_between(x, result.moment, color="#dc2626", alpha=0.22)
    ax_m.plot(x, result.moment, color="#dc2626", linewidth=2)
    ax_m.annotate(
        f"Mmax = {result.max_moment:.1f} kN·m",
        xy=(result.max_moment_position, result.max_moment),
        xytext=(10, -14),
        textcoords="offset points",
        fontsize=9,
        color="#dc2626",
    )
    _style(ax_m, "Bending Moment Diagram", "Moment (kN·m)")
    moment_png = _fig_to_base64(fig_m)

    fig_d, ax_d = plt.subplots(figsize=(7, 2.8))
    ax_d.fill_between(x, result.deflection_mm, color="#059669", alpha=0.22)
    ax_d.plot(x, result.deflection_mm, color="#059669", linewidth=2)
    _style(ax_d, "Deflection Diagram", "Deflection (mm)")
    deflection_png = _fig_to_base64(fig_d)

    return {
        "shear": shear_png,
        "moment": moment_png,
        "deflection": deflection_png,
    }
