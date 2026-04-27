from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

# Palette for repetition shading / bar colors
_REP_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8",
]


def plot_kinematic_curve(
    df: pd.DataFrame,
    movement_name: str,
    segments: list[tuple[float, float]] | None = None,
) -> Figure:
    """
    Kinematic angle curve with optional shaded repetition segments.

    Parameters
    ----------
    df            : DataFrame with 'Frame' (x) and 'Angle' (y) columns
    movement_name : used as the plot title
    segments      : list of (start_frame, end_frame) pairs to shade
    """
    fig = Figure(figsize=(10, 3.8), tight_layout=True)
    ax = fig.add_subplot(111)

    x_col = df.columns[0]
    y_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    ax.plot(df[x_col], df[y_col], linewidth=1.2, color="#4A90D9", zorder=2)

    if segments:
        for i, (s, e) in enumerate(segments):
            color = _REP_COLORS[i % len(_REP_COLORS)]
            ax.axvspan(s, e, alpha=0.22, color=color, zorder=1)
            ax.text(
                (s + e) / 2, 0.97, f"R{i + 1}",
                fontsize=8, ha="center", va="top",
                transform=ax.get_xaxis_transform(), color=color,
            )

    ax.set_xlabel(x_col, fontsize=10)
    ax.set_ylabel("Angle (°)", fontsize=10)
    ax.set_title(movement_name, fontsize=11)
    ax.grid(True, alpha=0.3, zorder=0)
    return fig


def plot_rom_bars(results: dict) -> Figure:
    """
    Horizontal bar chart of mean ROM ± SD for each movement.

    Parameters
    ----------
    results : {movement: {"mean": float, "sd": float, ...}}
    """
    movements = list(results.keys())
    means = [results[m]["mean"] for m in movements]
    sds = [results[m]["sd"] for m in movements]

    fig = Figure(figsize=(8, 4.5), tight_layout=True)
    ax = fig.add_subplot(111)

    x = np.arange(len(movements))
    ax.bar(
        x, means, yerr=sds, capsize=6,
        color="#4A90D9",
        error_kw={"elinewidth": 1.5, "capthick": 1.5},
        zorder=3,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(movements, rotation=22, ha="right", fontsize=9)
    ax.set_ylabel("ROM (°)", fontsize=10)
    ax.set_title("Range of Motion — Mean ± SD", fontsize=11)
    ax.grid(True, axis="y", alpha=0.3, zorder=0)
    return fig


def save_figure(fig: Figure, path: str, dpi: int = 150) -> None:
    """Save a Figure to a file (PNG, PDF, SVG, …)."""
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
