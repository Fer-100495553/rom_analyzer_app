from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

# Palette for repetition shading / bar colors
_REP_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8",
]


# ── Legacy CSV-based plots (kept) ─────────────────────────────────────────

def plot_kinematic_curve(
    df: pd.DataFrame,
    movement_name: str,
    segments: list[tuple[float, float]] | None = None,
) -> Figure:
    """
    Kinematic angle curve with optional shaded repetition segments.

    Args:
        df:            DataFrame with 'Frame' (x) and 'Angle' (y) columns.
        movement_name: Used as the plot title.
        segments:      List of (start_frame, end_frame) pairs to shade.
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

    Args:
        results: ``{movement: {"mean": float, "sd": float, …}}``.
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


# ── C3D / numpy-based plots ───────────────────────────────────────────────

def plot_angle_curve(
    angle_data: np.ndarray,
    frame_rate: int,
    title: str,
    ylabel: str = "Angle (°)",
    use_time: bool = True,
) -> Figure:
    """
    Plot a single angle curve from a 1D numpy array.

    Args:
        angle_data: 1D float array of angle values in degrees.
        frame_rate: Capture frame rate in Hz (used for time axis).
        title:      Plot title string.
        ylabel:     Y-axis label.
        use_time:   If True, x-axis shows seconds; otherwise frame indices.
    """
    fig = Figure(figsize=(10, 3.8), tight_layout=True)
    ax = fig.add_subplot(111)

    n = len(angle_data)
    if use_time:
        x = np.arange(n) / frame_rate
        xlabel = "Time (s)"
    else:
        x = np.arange(n)
        xlabel = "Frame"

    ax.plot(x, angle_data, linewidth=1.2, color="#4A90D9", zorder=2)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.grid(True, alpha=0.3, zorder=0)
    return fig


def plot_segmented_curve(
    angle_data: np.ndarray,
    segments: list[tuple[int, int]],
    frame_rate: int,
    title: str,
    peaks: np.ndarray | None = None,
    valleys: np.ndarray | None = None,
    roms: list[float] | None = None,
    use_time: bool = True,
) -> Figure:
    """
    Angle curve with colored shading per repetition, peak/valley markers,
    and optional ROM labels.

    Args:
        angle_data: 1D float array.
        segments:   List of (start_frame, end_frame) pairs.
        frame_rate: Capture frame rate in Hz.
        title:      Plot title.
        peaks:      Frame indices of detected peaks (marked with triangles).
        valleys:    Frame indices of detected valleys.
        roms:       ROM value per segment for legend labels.
        use_time:   If True, x-axis shows seconds.
    """
    fig = Figure(figsize=(10, 4.0), tight_layout=True)
    ax = fig.add_subplot(111)

    n = len(angle_data)
    scale = 1.0 / frame_rate if use_time else 1.0
    x = np.arange(n) * scale
    xlabel = "Time (s)" if use_time else "Frame"

    ax.plot(x, angle_data, linewidth=1.2, color="#4A90D9", zorder=2)

    for i, (s, e) in enumerate(segments):
        color = _REP_COLORS[i % len(_REP_COLORS)]
        xs, xe = s * scale, e * scale
        ax.axvspan(xs, xe, alpha=0.22, color=color, zorder=1)

        label = f"R{i + 1}"
        if roms and i < len(roms) and not np.isnan(roms[i]):
            label += f"\n{roms[i]:.1f}°"
        ax.text(
            (xs + xe) / 2, 0.97, label,
            fontsize=7, ha="center", va="top",
            transform=ax.get_xaxis_transform(), color=color,
        )

    if peaks is not None and len(peaks):
        ax.plot(peaks * scale, angle_data[peaks], "v",
                color="#E05252", ms=5, zorder=5, label="Peaks")
    if valleys is not None and len(valleys):
        ax.plot(valleys * scale, angle_data[valleys], "^",
                color="#2D7A2D", ms=5, zorder=5, label="Valleys")

    if (peaks is not None and len(peaks)) or (valleys is not None and len(valleys)):
        ax.legend(fontsize=8, loc="upper right")

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel("Angle (°)", fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.grid(True, alpha=0.3, zorder=0)
    return fig


def plot_rom_summary(
    movements_dict: dict,
    normative: dict[str, float] | None = None,
) -> Figure:
    """
    Bar chart with mean ROM ± SD per movement and optional normative reference lines.

    Args:
        movements_dict: ``{movement_name: {"mean": float, "sd": float, …}}``.
        normative:      Optional ``{movement_name: float}`` reference values.
    """
    from config import NORMATIVE_ROM as _NORM

    if normative is None:
        normative = _NORM

    movements = list(movements_dict.keys())
    means = [movements_dict[m].get("mean", float("nan")) for m in movements]
    sds = [movements_dict[m].get("sd", 0.0) for m in movements]

    fig = Figure(figsize=(max(7, len(movements) * 1.4), 4.8), tight_layout=True)
    ax = fig.add_subplot(111)

    x = np.arange(len(movements))
    bars = ax.bar(
        x, means, yerr=sds, capsize=6,
        color=[_REP_COLORS[i % len(_REP_COLORS)] for i in range(len(movements))],
        error_kw={"elinewidth": 1.5, "capthick": 1.5},
        zorder=3, alpha=0.85,
    )

    # Normative reference lines
    for i, mv in enumerate(movements):
        ref = normative.get(mv)
        if ref is not None:
            ax.hlines(ref, x[i] - 0.4, x[i] + 0.4,
                      colors="#555555", linewidths=1.5, linestyles="--", zorder=4)

    # Value labels above bars
    for bar, mean in zip(bars, means):
        if not np.isnan(mean):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{mean:.1f}°",
                ha="center", va="bottom", fontsize=8,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(movements, rotation=18, ha="right", fontsize=9)
    ax.set_ylabel("ROM (°)", fontsize=10)
    ax.set_title("Range of Motion — Mean ± SD", fontsize=11)
    ax.grid(True, axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    valid_tops = [m + s for m, s in zip(means, sds) if not np.isnan(m)]
    if valid_tops:
        ax.set_ylim(bottom=0, top=max(valid_tops) * 1.15)
    return fig
