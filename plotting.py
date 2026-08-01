from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from translations import t

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


def plot_trunk_inclination(
    trunk_angles: dict,
    frame_rate: int,
    title: str = "Trunk Lateral Inclination",
) -> Figure:
    """
    Single-panel trunk lateral inclination figure.

    NaN regions are shaded as grey vertical bands.  Returns the Figure;
    does not call plt.show().

    Args:
        trunk_angles: Output of :func:`data_processing.compute_trunk_extended_angles`.
        frame_rate:   Capture rate in Hz (used for time axis).
        title:        Plot title.
    """
    lat = trunk_angles["lateral_inclination"]
    n   = len(lat)
    t   = np.arange(n) / frame_rate

    fig = Figure(figsize=(10, 3.8), tight_layout=True)
    ax  = fig.add_subplot(111)

    ax.plot(t, lat, linewidth=2.0, color="tab:red", zorder=2)
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle="--",
               alpha=0.6, zorder=1)
    ax.set_ylabel(t("plot_lateral_incl_deg"), fontsize=10)
    ax.set_xlabel(t("col_time_s"), fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.grid(True, alpha=0.3, zorder=0)

    # Grey bands where data is NaN
    nan_mask = np.isnan(lat)
    if nan_mask.any():
        in_band    = False
        band_start = None
        for i, is_nan in enumerate(nan_mask):
            if is_nan and not in_band:
                band_start = t[i]
                in_band    = True
            elif not is_nan and in_band:
                ax.axvspan(band_start, t[i], color="grey",
                           alpha=0.25, zorder=0)
                in_band = False
        if in_band:
            ax.axvspan(band_start, t[-1], color="grey",
                       alpha=0.25, zorder=0)

    return fig


# ── C3D / numpy-based plots ───────────────────────────────────────────────

def plot_angle_curve(
    angle_data: np.ndarray,
    frame_rate: int,
    title: str,
    ylabel: str | None = None,
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
        xlabel = t("col_time_s")
    else:
        x = np.arange(n)
        xlabel = t("frame")

    ax.plot(x, angle_data, linewidth=1.2, color="#4A90D9", zorder=2)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel if ylabel is not None else t("angle_deg"), fontsize=10)
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
    xlabel = t("col_time_s") if use_time else t("frame")

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
                color="#E05252", ms=5, zorder=5, label=t("plot_peaks"))
    if valleys is not None and len(valleys):
        ax.plot(valleys * scale, angle_data[valleys], "^",
                color="#2D7A2D", ms=5, zorder=5, label=t("plot_valleys"))

    if (peaks is not None and len(peaks)) or (valleys is not None and len(valleys)):
        ax.legend(fontsize=8, loc="upper right")

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(t("angle_deg"), fontsize=10)
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
    ax.set_ylabel(t("ylabel_degrees"), fontsize=10)
    ax.set_title(t("plot_rom_mean_sd_title"), fontsize=11)
    ax.grid(True, axis="y", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    valid_tops = [m + s for m, s in zip(means, sds) if not np.isnan(m)]
    if valid_tops:
        ax.set_ylim(bottom=0, top=max(valid_tops) * 1.15)
    return fig


def plot_rom_raincloud(
    movements_data: dict,
    ax=None,
    ylabel: str = "°",
    metric_labels: list[tuple[str, str]] | None = None,
) -> Figure:
    """
    Three vertical raincloud subplots side-by-side, one per metric
    (ROM / peak / valley), each with its own Y scale.

    Args:
        movements_data: {mv_name: [(side, data_dict), ...]}
            data_dict["extended"][metric]["values"] → list[float] per repetition.
        ax: ignored — always creates a new Figure with 3 subplots.
        metric_labels: [(metric_key, display_label), ...] for the 3 subplots.
            Defaults to generic ROM/Peak/Valley translated labels.
    """
    from scipy.stats import gaussian_kde
    from matplotlib.patches import Rectangle, Patch

    if metric_labels is None:
        metric_labels = [
            ("rom",    t("s4_metric_rom")),
            ("peak",   t("s4_metric_peak")),
            ("valley", t("s4_metric_valley")),
        ]
    METRICS = metric_labels

    _COLOR      = {"Left": "#E74C3C", "Right": "#2ECC71"}
    _COLOR_DARK = {"Left": "#922B21", "Right": "#1A7A3C"}
    _DEFAULT      = "#4A90D9"
    _DEFAULT_DARK = "#1A5276"

    _V_AMP  = 0.30   # max violin half-width (x units)
    _BW     = 0.035  # boxplot x half-width
    _SC_OFF = 0.10   # scatter x offset from series center
    _SC_JIT = 0.03   # scatter jitter magnitude

    mv_name    = next(iter(movements_data))
    sides_data = movements_data[mv_name]
    n_sides    = len(sides_data)

    fig  = Figure(figsize=(8, 3.6))
    axes = fig.subplots(1, 3)
    fig.subplots_adjust(wspace=0.35, top=0.82)
    fig.suptitle(mv_name, fontsize=13, fontweight="bold")

    rng = np.random.default_rng(42)

    def _draw_series(
        cur_ax,
        vals: np.ndarray,
        x_c: float,
        color: str,
        color_dark: str,
    ) -> None:
        """Vertical raincloud: violin (left) + boxplot + scatter (right)."""
        if vals.size == 0:
            return

        # 1. Half-violin extending left from x_c
        if vals.size >= 2:
            kde     = gaussian_kde(vals, bw_method="scott")
            spread  = max(float(vals.std()) * 0.5, 0.5)
            y_grid  = np.linspace(vals.min() - spread, vals.max() + spread, 300)
            density = kde(y_grid)
            peak    = density.max()
            if peak > 0:
                kde_x = x_c - (density / peak) * _V_AMP
                cur_ax.fill_betweenx(y_grid, kde_x, x_c,
                                     color=color, alpha=0.45, zorder=2)
                cur_ax.plot(kde_x, y_grid, color=color, alpha=0.75,
                            linewidth=1.0, zorder=3)

        # 2. Vertical boxplot
        q1, q2, q3 = np.percentile(vals, [25, 50, 75])
        iqr      = q3 - q1
        fence_lo = q1 - 1.5 * iqr
        fence_hi = q3 + 1.5 * iqr
        w_lo = vals[vals >= fence_lo].min() if np.any(vals >= fence_lo) else q1
        w_hi = vals[vals <= fence_hi].max() if np.any(vals <= fence_hi) else q3

        cur_ax.plot([x_c, x_c], [w_lo, q1], color=color, lw=1.2, zorder=4)
        cur_ax.plot([x_c, x_c], [q3, w_hi], color=color, lw=1.2, zorder=4)
        for wy in (w_lo, w_hi):
            cur_ax.plot([x_c - _BW, x_c + _BW], [wy, wy],
                        color=color, lw=1.2, zorder=4)
        cur_ax.add_patch(Rectangle(
            (x_c - _BW, q1), 2 * _BW, q3 - q1,
            facecolor="white", edgecolor=color, linewidth=1.5, zorder=5,
        ))
        cur_ax.plot([x_c - _BW, x_c + _BW], [q2, q2],
                    color=color, lw=2.0, zorder=6)

        mean_val = float(vals.mean())
        cur_ax.text(x_c, w_hi, f"{mean_val:.1f}°",
                    ha="center", va="bottom", fontsize=10,
                    fontweight="bold", color=color_dark, zorder=7)

        outliers = vals[(vals < w_lo) | (vals > w_hi)]
        if outliers.size:
            cur_ax.scatter(np.full(outliers.size, x_c), outliers,
                           color=color, s=25, marker="D", alpha=0.85, zorder=7)

        # 3. Scatter jittered to the right of x_c
        jitter = rng.uniform(-_SC_JIT, _SC_JIT, size=vals.size)
        cur_ax.scatter(x_c + _SC_OFF + jitter, vals,
                       color=color, s=35, alpha=0.85, zorder=3)

    # ── Draw each metric in its own subplot ───────────────────────────────
    seen_sides: dict = {}
    for m_idx, (metric_key, metric_label) in enumerate(METRICS):
        cur_ax = axes[m_idx]
        cur_ax.set_title(metric_label, fontsize=10, fontweight="bold")

        x_positions: list[float] = []
        x_labels:    list[str]   = []

        for side, data in sides_data:
            seen_sides[side] = _COLOR.get(side, _DEFAULT)
            raw  = data.get("extended", {}).get(metric_key, {}).get("values", [])
            vals = np.array(
                [v for v in raw if v is not None and not np.isnan(float(v))],
                dtype=float,
            )
            if vals.size < 1:
                continue

            x_c = -0.22 if (n_sides > 1 and side == "Left") else (
                   0.22 if (n_sides > 1 and side == "Right") else 0.0)

            _draw_series(cur_ax, vals, x_c,
                         _COLOR.get(side, _DEFAULT),
                         _COLOR_DARK.get(side, _DEFAULT_DARK))
            x_positions.append(x_c)
            x_labels.append(side)

        # X ticks — side labels
        if x_positions:
            cur_ax.set_xticks(x_positions)
            cur_ax.set_xticklabels(x_labels, fontsize=9)
        cur_ax.set_xlim(-0.65, 0.65)
        cur_ax.tick_params(axis="x", length=0)

        # Y axis
        if m_idx == 0:
            cur_ax.set_ylabel(ylabel, fontsize=9)
        cur_ax.margins(y=0.2)
        cur_ax.spines["top"].set_visible(False)
        cur_ax.spines["right"].set_visible(False)
        cur_ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)

    # ── Legend on rightmost subplot ────────────────────────────────────────
    if len(seen_sides) > 1:
        handles = [Patch(facecolor=c, label=s) for s, c in seen_sides.items()]
        axes[2].legend(handles=handles, fontsize=8, loc="upper right")

    return fig
