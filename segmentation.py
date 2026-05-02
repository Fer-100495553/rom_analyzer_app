from __future__ import annotations

import logging
from typing import Callable

import customtkinter as ctk
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import messagebox

logger = logging.getLogger(__name__)

# ── Palette ────────────────────────────────────────────────────────────────
_REP_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
    "#FFEAA7", "#DDA0DD", "#98D8C8",
]


# ═══════════════════════════════════════════════════════════════════════════
#  Pure segmentation helpers (no GUI)
# ═══════════════════════════════════════════════════════════════════════════

def detect_peaks_valleys(
    angle_data: np.ndarray,
    min_prominence: float,
    min_distance: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Detect peaks (maxima) and valleys (minima) in an angle curve.

    Args:
        angle_data:      1D array of angle values in degrees.
        min_prominence:  Minimum peak prominence in degrees.
        min_distance:    Minimum number of frames between successive peaks.

    Returns:
        Tuple ``(peaks, valleys)`` — arrays of frame indices.
    """
    from scipy.signal import find_peaks  # deferred so import error is late

    clean = np.where(np.isnan(angle_data), np.nanmean(angle_data), angle_data)
    peaks, _ = find_peaks(clean, prominence=min_prominence, distance=min_distance)
    valleys, _ = find_peaks(-clean, prominence=min_prominence, distance=min_distance)
    return peaks, valleys


def auto_segment(
    angle_data: np.ndarray,
    min_prominence: float,
    min_distance: int,
    cycle_from: str = "valley",
) -> tuple[list[tuple[int, int]], np.ndarray, np.ndarray]:
    """
    Automatically detect repetition boundaries in an angle curve.

    Args:
        angle_data:      1D angle array.
        min_prominence:  Minimum peak prominence (degrees).
        min_distance:    Minimum inter-peak distance (frames).
        cycle_from:      ``"valley"`` (valley-to-valley) or ``"peak"``
                         (peak-to-peak).

    Returns:
        Tuple ``(segments, peaks, valleys)`` where *segments* is a list of
        ``(start_frame, end_frame)`` integer pairs.
    """
    peaks, valleys = detect_peaks_valleys(angle_data, min_prominence, min_distance)

    anchors = valleys if cycle_from == "valley" else peaks
    segments: list[tuple[int, int]] = []
    for i in range(len(anchors) - 1):
        segments.append((int(anchors[i]), int(anchors[i + 1])))

    return segments, peaks, valleys


def compute_rep_roms(
    angle_data: np.ndarray,
    segments: list[tuple[int, int]],
) -> list[float]:
    """
    Compute ROM (max − min) for each repetition segment.

    Args:
        angle_data: 1D angle array.
        segments:   List of (start_frame, end_frame) pairs.

    Returns:
        List of ROM values (float), one per segment.
    """
    roms: list[float] = []
    for s, e in segments:
        chunk = angle_data[s : e + 1]
        valid = chunk[~np.isnan(chunk)]
        if valid.size == 0:
            roms.append(float("nan"))
        else:
            roms.append(float(np.max(valid) - np.min(valid)))
    return roms


def compute_stats_from_roms(
    roms: list[float],
    segments: list[tuple[int, int]],
) -> dict:
    """
    Aggregate ROM statistics and flag outliers.

    Args:
        roms:     Per-repetition ROM values.
        segments: Corresponding (start, end) frame pairs.

    Returns:
        Dict with keys: roms, mean, sd, segments, outlier_flags.
    """
    from config import OUTLIER_SD_THRESHOLD

    valid = np.array([r for r in roms if not np.isnan(r)])
    mean = float(np.mean(valid)) if valid.size > 0 else float("nan")
    sd = float(np.std(valid, ddof=1)) if valid.size > 1 else 0.0

    outlier_flags: list[bool] = []
    for r in roms:
        if np.isnan(r) or sd == 0.0:
            outlier_flags.append(False)
        else:
            outlier_flags.append(abs(r - mean) > OUTLIER_SD_THRESHOLD * sd)

    return {
        "roms": roms,
        "mean": mean,
        "sd": sd,
        "segments": segments,
        "outlier_flags": outlier_flags,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  C3DSegmentationWindow — unified 3-mode segmentation dialog
# ═══════════════════════════════════════════════════════════════════════════

class C3DSegmentationWindow(ctk.CTkToplevel):
    """
    Modal segmentation window for C3D angle data.

    Supports three modes selectable via radio buttons:
      - **Auto**   — scipy peak/valley detection with adjustable parameters.
      - **Manual** — interactive click-to-place markers (left-click add,
                     right-click remove nearest).
      - **Events** — maps Nexus event pairs to repetition boundaries.

    After the user clicks "Accept", ``self.result`` holds the stats dict
    (see :func:`compute_stats_from_roms`) or ``None`` if cancelled.
    """

    def __init__(
        self,
        parent,
        movement_name: str,
        angle_data: np.ndarray,
        frame_rate: int,
        events: list[dict] | None = None,
        on_accept: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(f"Segmentation — {movement_name}")
        self.geometry("1020x720")
        self.grab_set()
        self.lift()
        self.focus_force()

        self._movement_name = movement_name
        self._angle_data = angle_data.astype(float)
        self._frame_rate = frame_rate
        self._events = events or []
        self._on_accept = on_accept

        # Public result
        self.result: dict | None = None

        # Mode
        self._mode_var = ctk.StringVar(value="auto")

        # Auto state
        self._peaks: np.ndarray = np.array([], dtype=int)
        self._valleys: np.ndarray = np.array([], dtype=int)
        self._auto_segments: list[tuple[int, int]] = []

        # Manual state
        self._markers: list[float] = []          # raw x (frame) values
        self._marker_artists: list[tuple] = []   # (vline, text) per marker

        # Current accepted segments
        self._segments: list[tuple[int, int]] = []

        self._build_ui()
        self._switch_mode()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ─ Canvas area ───────────────────────────────────────────────────
        self.fig = Figure(figsize=(9.8, 3.6), tight_layout=True)
        self.ax = self.fig.add_subplot(111)

        self._canvas = FigureCanvasTkAgg(self.fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(10, 0))

        nav_frame = ctk.CTkFrame(self, height=30)
        nav_frame.pack(fill="x", padx=10)
        nav_frame.pack_propagate(False)
        self._nav = NavigationToolbar2Tk(self._canvas, nav_frame)
        self._nav.update()

        self._cid = self._canvas.mpl_connect("button_press_event", self._on_canvas_click)

        # ─ Mode selector ─────────────────────────────────────────────────
        mode_bar = ctk.CTkFrame(self)
        mode_bar.pack(fill="x", padx=10, pady=(6, 0))

        ctk.CTkLabel(mode_bar, text="Mode:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=(8, 4))
        for txt, val in [("Auto-detect", "auto"), ("Manual", "manual"), ("From Events", "events")]:
            ctk.CTkRadioButton(
                mode_bar, text=txt, variable=self._mode_var, value=val,
                command=self._switch_mode,
            ).pack(side="left", padx=6)

        # ─ Mode-specific panels ───────────────────────────────────────────
        self._panel_container = ctk.CTkFrame(self, height=100)
        self._panel_container.pack(fill="x", padx=10, pady=4)
        self._panel_container.pack_propagate(False)

        self._panel_auto = self._build_auto_panel(self._panel_container)
        self._panel_manual = self._build_manual_panel(self._panel_container)
        self._panel_events = self._build_events_panel(self._panel_container)

        # ─ Stats display ─────────────────────────────────────────────────
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=10, pady=(0, 4))
        self._stats_lbl = ctk.CTkLabel(
            stats_frame,
            text="  No segments yet.",
            font=ctk.CTkFont(size=11),
            justify="left",
        )
        self._stats_lbl.pack(anchor="w", padx=8, pady=4)

        # ─ Action buttons ─────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self)
        btn_bar.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_bar, text="Accept & Continue",
            fg_color="#2D7A2D", hover_color="#1F5C1F",
            font=ctk.CTkFont(weight="bold"), width=160,
            command=self._accept,
        ).pack(side="right", padx=8, pady=6)
        ctk.CTkButton(
            btn_bar, text="Cancel", width=90,
            command=self.destroy,
        ).pack(side="right", pady=6)
        ctk.CTkButton(
            btn_bar, text="Reset", width=90,
            command=self._reset,
        ).pack(side="left", padx=8, pady=6)

        self._draw_base_curve()

    # ── Mode panels ────────────────────────────────────────────────────────

    def _build_auto_panel(self, parent) -> ctk.CTkFrame:
        from config import DEFAULT_PROMINENCE, DEFAULT_MIN_DISTANCE
        f = ctk.CTkFrame(parent, fg_color="transparent")

        # Prominence row
        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", padx=6, pady=(4, 0))
        ctk.CTkLabel(row1, text="Prominence (°):", width=120).pack(side="left")
        self._prom_var = ctk.DoubleVar(value=DEFAULT_PROMINENCE)
        self._prom_lbl = ctk.CTkLabel(row1, text=f"{DEFAULT_PROMINENCE:.0f}°", width=36)
        slider_p = ctk.CTkSlider(
            row1, from_=2, to=60, variable=self._prom_var, width=220,
            command=lambda v: self._prom_lbl.configure(text=f"{float(v):.0f}°"),
        )
        slider_p.pack(side="left", padx=4)
        self._prom_lbl.pack(side="left", padx=2)

        # Min distance row
        row2 = ctk.CTkFrame(f, fg_color="transparent")
        row2.pack(fill="x", padx=6, pady=(2, 0))
        ctk.CTkLabel(row2, text="Min distance (fr):", width=120).pack(side="left")
        self._dist_var = ctk.IntVar(value=DEFAULT_MIN_DISTANCE)
        self._dist_lbl = ctk.CTkLabel(row2, text=f"{DEFAULT_MIN_DISTANCE}", width=36)
        slider_d = ctk.CTkSlider(
            row2, from_=10, to=300, variable=self._dist_var, width=220,
            command=lambda v: self._dist_lbl.configure(text=f"{int(v)}"),
        )
        slider_d.pack(side="left", padx=4)
        self._dist_lbl.pack(side="left", padx=2)

        # Cycle type + detect button
        row3 = ctk.CTkFrame(f, fg_color="transparent")
        row3.pack(fill="x", padx=6, pady=(4, 4))
        ctk.CTkLabel(row3, text="Cycle from:", width=80).pack(side="left")
        self._cycle_var = ctk.StringVar(value="valley")
        ctk.CTkRadioButton(row3, text="Valley→Valley", variable=self._cycle_var,
                           value="valley").pack(side="left", padx=6)
        ctk.CTkRadioButton(row3, text="Peak→Peak", variable=self._cycle_var,
                           value="peak").pack(side="left", padx=4)
        ctk.CTkButton(
            row3, text="Detect", width=80,
            command=self._run_auto_detection,
        ).pack(side="right", padx=8)

        return f

    def _build_manual_panel(self, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(
            row,
            text="Left-click = add marker (alternating start/end)  ·  "
                 "Right-click = remove nearest marker",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(side="left")
        ctk.CTkButton(row, text="Undo", width=70, command=self._manual_undo).pack(
            side="right", padx=4)
        ctk.CTkButton(row, text="Clear", width=70, command=self._manual_clear).pack(
            side="right", padx=4)
        self._manual_status = ctk.CTkLabel(
            f, text="  0 markers placed.", font=ctk.CTkFont(size=11))
        self._manual_status.pack(anchor="w", padx=8)
        return f

    def _build_events_panel(self, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        if not self._events:
            ctk.CTkLabel(
                f, text="  No events found in this C3D file.",
                text_color="gray",
            ).pack(anchor="w", padx=8, pady=8)
            return f

        unique_labels = sorted({e["name"] for e in self._events})

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(row, text="Start event:", width=90).pack(side="left")
        self._ev_start_var = ctk.StringVar(
            value=unique_labels[0] if unique_labels else "")
        ctk.CTkOptionMenu(row, values=unique_labels, variable=self._ev_start_var,
                          width=140).pack(side="left", padx=4)
        ctk.CTkLabel(row, text="End event:", width=80).pack(side="left", padx=(12, 0))
        self._ev_end_var = ctk.StringVar(
            value=unique_labels[-1] if len(unique_labels) > 1 else unique_labels[0])
        ctk.CTkOptionMenu(row, values=unique_labels, variable=self._ev_end_var,
                          width=140).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Map Events", width=100,
                      command=self._map_events).pack(side="right", padx=8)

        info = ", ".join(
            f"{e['name']}@{e['frame']}" for e in self._events[:8]
        )
        if len(self._events) > 8:
            info += f" … (+{len(self._events) - 8} more)"
        ctk.CTkLabel(f, text=f"  Events: {info}",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(
            anchor="w", padx=8)
        return f

    # ── Mode switching ──────────────────────────────────────────────────────

    def _switch_mode(self) -> None:
        mode = self._mode_var.get()
        for panel in (self._panel_auto, self._panel_manual, self._panel_events):
            panel.pack_forget()
        if mode == "auto":
            self._panel_auto.pack(fill="x")
        elif mode == "manual":
            self._panel_manual.pack(fill="x")
        else:
            self._panel_events.pack(fill="x")
        self._reset()

    # ── Canvas drawing ──────────────────────────────────────────────────────

    def _draw_base_curve(self) -> None:
        self.ax.clear()
        n = len(self._angle_data)
        time_arr = np.arange(n) / self._frame_rate
        self.ax.plot(time_arr, self._angle_data,
                     linewidth=1.2, color="#4A90D9", zorder=2)
        self.ax.set_xlabel("Time (s)", fontsize=10)
        self.ax.set_ylabel("Angle (°)", fontsize=10)
        self.ax.set_title(self._movement_name, fontsize=11)
        self.ax.grid(True, alpha=0.3, zorder=0)
        self._canvas.draw_idle()

    def _redraw_with_segments(
        self,
        segments: list[tuple[int, int]],
        peaks: np.ndarray | None = None,
        valleys: np.ndarray | None = None,
        roms: list[float] | None = None,
    ) -> None:
        self._draw_base_curve()

        for i, (s, e) in enumerate(segments):
            color = _REP_COLORS[i % len(_REP_COLORS)]
            ts, te = s / self._frame_rate, e / self._frame_rate
            self.ax.axvspan(ts, te, alpha=0.22, color=color, zorder=1)
            label = f"R{i + 1}"
            if roms and i < len(roms) and not np.isnan(roms[i]):
                label += f"\n{roms[i]:.1f}°"
            self.ax.text(
                (ts + te) / 2, 0.97, label,
                fontsize=7, ha="center", va="top",
                transform=self.ax.get_xaxis_transform(), color=color,
            )

        if peaks is not None and peaks.size:
            tp = peaks / self._frame_rate
            self.ax.plot(tp, self._angle_data[peaks], "v", color="#E05252",
                         ms=6, zorder=5, label="peaks")
        if valleys is not None and valleys.size:
            tv = valleys / self._frame_rate
            self.ax.plot(tv, self._angle_data[valleys], "^", color="#2D7A2D",
                         ms=6, zorder=5, label="valleys")

        self._canvas.draw_idle()

    def _redraw_manual_markers(self) -> None:
        self._draw_base_curve()
        # Shade complete pairs
        pairs = list(zip(self._markers[::2], self._markers[1::2]))
        for i, (s, e) in enumerate(pairs):
            color = _REP_COLORS[i % len(_REP_COLORS)]
            ts, te = s / self._frame_rate, e / self._frame_rate
            self.ax.axvspan(ts, te, alpha=0.22, color=color, zorder=1)

        # Redraw existing marker lines
        self._marker_artists.clear()
        for idx, x in enumerate(self._markers):
            is_start = idx % 2 == 0
            color = "#3DB85E" if is_start else "#E05252"
            rep_num = idx // 2 + 1
            label = f"S{rep_num}" if is_start else f"E{rep_num}"
            t = x / self._frame_rate
            vl = self.ax.axvline(t, color=color, linestyle="--",
                                 linewidth=1.5, alpha=0.85, zorder=3)
            txt = self.ax.text(
                t, 0.97, label, color=color, fontsize=7,
                ha="center", va="top",
                transform=self.ax.get_xaxis_transform(), zorder=4,
            )
            self._marker_artists.append((vl, txt))
        self._canvas.draw_idle()

    # ── Canvas click handler ───────────────────────────────────────────────

    def _on_canvas_click(self, event) -> None:
        if self._mode_var.get() != "manual":
            return
        if event.inaxes != self.ax:
            return
        if self._nav.mode:
            return

        t = event.xdata  # time in seconds
        x_frame = t * self._frame_rate  # fractional frame index

        if event.button == 1:  # left click — add
            self._markers.append(x_frame)
        elif event.button == 3:  # right click — remove nearest
            if not self._markers:
                return
            times = [m / self._frame_rate for m in self._markers]
            nearest = int(np.argmin(np.abs(np.array(times) - t)))
            self._markers.pop(nearest)

        self._redraw_manual_markers()
        self._update_manual_status()
        self._compute_and_show_stats_manual()

    # ── Auto mode ──────────────────────────────────────────────────────────

    def _run_auto_detection(self) -> None:
        prom = float(self._prom_var.get())
        dist = int(self._dist_var.get())
        cycle = self._cycle_var.get()

        try:
            segs, peaks, valleys = auto_segment(
                self._angle_data, prom, dist, cycle_from=cycle)
        except Exception as exc:
            messagebox.showerror("Detection error", str(exc), parent=self)
            return

        self._auto_segments = segs
        self._peaks = peaks
        self._valleys = valleys
        self._segments = segs

        roms = compute_rep_roms(self._angle_data, segs)
        self._redraw_with_segments(segs, peaks, valleys, roms)
        self._update_stats(segs, roms)

    # ── Manual mode ────────────────────────────────────────────────────────

    def _manual_undo(self) -> None:
        if self._markers:
            self._markers.pop()
            self._redraw_manual_markers()
            self._update_manual_status()
            self._compute_and_show_stats_manual()

    def _manual_clear(self) -> None:
        self._markers.clear()
        self._marker_artists.clear()
        self._draw_base_curve()
        self._update_manual_status()
        self._stats_lbl.configure(text="  No segments yet.")

    def _update_manual_status(self) -> None:
        n = len(self._markers)
        pairs = n // 2
        self._manual_status.configure(
            text=f"  {n} markers placed → {pairs} complete repetition(s).")

    def _compute_and_show_stats_manual(self) -> None:
        pairs = list(zip(self._markers[::2], self._markers[1::2]))
        if not pairs:
            return
        segs = [(int(s), int(e)) for s, e in pairs]
        roms = compute_rep_roms(self._angle_data, segs)
        self._segments = segs
        self._update_stats(segs, roms)

    # ── Events mode ────────────────────────────────────────────────────────

    def _map_events(self) -> None:
        if not self._events:
            return
        start_label = self._ev_start_var.get()
        end_label = self._ev_end_var.get()

        starts = sorted(
            e["frame"] for e in self._events if e["name"] == start_label)
        ends = sorted(
            e["frame"] for e in self._events if e["name"] == end_label)

        # Show all events as vertical lines first
        self._draw_base_curve()
        for ev in self._events:
            t = ev["frame"] / self._frame_rate
            color = "#3DB85E" if ev["name"] == start_label else "#E05252"
            self.ax.axvline(t, color=color, linestyle=":", linewidth=1.2,
                            alpha=0.7, zorder=3)
            self.ax.text(t, 0.02, ev["name"], fontsize=6, color=color,
                         rotation=90, transform=self.ax.get_xaxis_transform())

        segs: list[tuple[int, int]] = []
        for s in starts:
            # Pair with the next end that comes after this start
            valid_ends = [e for e in ends if e > s]
            if valid_ends:
                segs.append((s, valid_ends[0]))

        if not segs:
            messagebox.showwarning(
                "No segments",
                f"No complete pairs found between '{start_label}' and '{end_label}'.",
                parent=self,
            )
            self._canvas.draw_idle()
            return

        self._segments = segs
        roms = compute_rep_roms(self._angle_data, segs)
        self._redraw_with_segments(segs, roms=roms)
        self._update_stats(segs, roms)

    # ── Stats ──────────────────────────────────────────────────────────────

    def _update_stats(
        self,
        segments: list[tuple[int, int]],
        roms: list[float],
    ) -> None:
        if not segments:
            self._stats_lbl.configure(text="  No segments yet.")
            return

        valid = [r for r in roms if not np.isnan(r)]
        mean = np.mean(valid) if valid else float("nan")
        sd = np.std(valid, ddof=1) if len(valid) > 1 else 0.0

        rom_str = "  ".join(
            f"R{i+1}: {r:.1f}°" if not np.isnan(r) else f"R{i+1}: —"
            for i, r in enumerate(roms)
        )
        self._stats_lbl.configure(
            text=f"  {len(segments)} rep(s)  |  Mean: {mean:.1f}° ± {sd:.1f}°  "
                 f"|  {rom_str}",
        )

    # ── Accept / Reset ─────────────────────────────────────────────────────

    def _accept(self) -> None:
        mode = self._mode_var.get()

        if mode == "manual":
            pairs = list(zip(self._markers[::2], self._markers[1::2]))
            self._segments = [(int(s), int(e)) for s, e in pairs]

        if not self._segments:
            messagebox.showwarning(
                "No segments",
                "Please detect or mark at least one repetition before accepting.",
                parent=self,
            )
            return

        roms = compute_rep_roms(self._angle_data, self._segments)
        self.result = compute_stats_from_roms(roms, self._segments)

        if self._on_accept:
            self._on_accept(self.result)

        self.destroy()

    def _reset(self) -> None:
        self._segments = []
        self._auto_segments = []
        self._peaks = np.array([], dtype=int)
        self._valleys = np.array([], dtype=int)
        self._markers.clear()
        self._marker_artists.clear()
        self._draw_base_curve()
        self._stats_lbl.configure(text="  No segments yet.")
        if hasattr(self, "_manual_status"):
            self._manual_status.configure(text="  0 markers placed.")


# ═══════════════════════════════════════════════════════════════════════════
#  SegmentationWindow — legacy manual-only window (CSV workflow)
# ═══════════════════════════════════════════════════════════════════════════

class SegmentationWindow(ctk.CTkToplevel):
    """
    Modal window showing an interactive kinematic curve.
    The user clicks to place alternating start (green) / end (red) markers
    that delimit each repetition. Pairs are collected as (start_x, end_x).
    """

    def __init__(
        self,
        parent,
        movement_name: str,
        df: pd.DataFrame,
        n_reps: int,
    ):
        super().__init__(parent)
        self.title(f"Segmentation — {movement_name}")
        self.geometry("980x580")
        self.grab_set()
        self.lift()
        self.focus_force()

        self.movement_name = movement_name
        self.df = df
        self.n_reps = n_reps

        # Public result — populated only on Confirm
        self.segments: list[tuple[float, float]] = []

        # Internal marker state
        self._markers: list[float] = []
        self._marker_artists: list[tuple] = []  # (vline, text) per marker

        self._build_ui()
        self._draw_curve()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, height=46)
        top.pack(fill="x", padx=10, pady=(10, 0))
        top.pack_propagate(False)

        self._status_lbl = ctk.CTkLabel(
            top, text=self._status_text(),
            font=ctk.CTkFont(size=12),
        )
        self._status_lbl.pack(side="left", padx=12)

        ctk.CTkButton(
            top, text="Confirm", width=94,
            fg_color="#2D7A2D", hover_color="#1F5C1F",
            command=self._confirm,
        ).pack(side="right", padx=8, pady=7)
        ctk.CTkButton(top, text="Clear", width=72, command=self._clear_all).pack(
            side="right", pady=7)
        ctk.CTkButton(top, text="Undo", width=72, command=self._undo_last).pack(
            side="right", padx=(0, 4), pady=7)

        self.fig = Figure(figsize=(9.5, 4.0), tight_layout=True)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=6)

        nav_frame = ctk.CTkFrame(self, height=32)
        nav_frame.pack(fill="x", padx=10, pady=(0, 8))
        nav_frame.pack_propagate(False)
        self._nav = NavigationToolbar2Tk(self.canvas, nav_frame)
        self._nav.update()

        self.canvas.mpl_connect("button_press_event", self._on_click)

    # ── drawing ────────────────────────────────────────────────────────────

    def _draw_curve(self) -> None:
        self.ax.clear()
        x_col = self.df.columns[0]
        y_col = self.df.columns[1] if len(self.df.columns) > 1 else self.df.columns[0]
        self.ax.plot(self.df[x_col], self.df[y_col],
                     linewidth=1.3, color="#4A90D9", zorder=2)
        self.ax.set_xlabel(x_col, fontsize=10)
        self.ax.set_ylabel("Angle (°)", fontsize=10)
        self.ax.set_title(self.movement_name, fontsize=11, pad=8)
        self.ax.grid(True, alpha=0.3, zorder=1)
        self.canvas.draw_idle()

    # ── event handlers ─────────────────────────────────────────────────────

    def _on_click(self, event) -> None:
        if event.inaxes != self.ax:
            return
        if self._nav.mode:
            return

        idx = len(self._markers)
        is_start = idx % 2 == 0
        color = "#3DB85E" if is_start else "#E05252"
        rep_num = idx // 2 + 1
        label = f"S{rep_num}" if is_start else f"E{rep_num}"

        vl = self.ax.axvline(x=event.xdata, color=color,
                             linestyle="--", linewidth=1.6, alpha=0.85, zorder=3)
        txt = self.ax.text(event.xdata, 0.97, label,
                           color=color, fontsize=8, ha="center", va="top",
                           transform=self.ax.get_xaxis_transform(), zorder=4)
        self._markers.append(event.xdata)
        self._marker_artists.append((vl, txt))
        self.canvas.draw_idle()
        self._update_status()

    def _undo_last(self) -> None:
        if not self._markers:
            return
        self._markers.pop()
        vl, txt = self._marker_artists.pop()
        vl.remove()
        txt.remove()
        self.canvas.draw_idle()
        self._update_status()

    def _clear_all(self) -> None:
        for vl, txt in self._marker_artists:
            vl.remove()
            txt.remove()
        self._markers.clear()
        self._marker_artists.clear()
        self.canvas.draw_idle()
        self._update_status()

    def _confirm(self) -> None:
        pairs = list(zip(self._markers[::2], self._markers[1::2]))
        if len(pairs) < self.n_reps:
            messagebox.showwarning(
                "Insufficient markers",
                f"Expected {self.n_reps} complete repetition pairs.\n"
                f"Currently have {len(pairs)} complete pair(s).",
                parent=self,
            )
            return
        self.segments = pairs[: self.n_reps]
        self.destroy()

    # ── helpers ────────────────────────────────────────────────────────────

    def _status_text(self) -> str:
        n = len(self._markers)
        needed = self.n_reps * 2
        if n >= needed:
            return f"  {n}/{needed} markers placed — ready. Click Confirm."
        next_type = "start  (green)" if n % 2 == 0 else "end  (red)"
        return (
            f"  {n}/{needed} markers placed.  "
            f"Next: rep {n // 2 + 1} {next_type}."
        )

    def _update_status(self) -> None:
        self._status_lbl.configure(text=self._status_text())
