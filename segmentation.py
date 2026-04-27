from __future__ import annotations

import customtkinter as ctk
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import messagebox


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
        # Top bar: status + action buttons
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
        ctk.CTkButton(
            top, text="Clear", width=72,
            command=self._clear_all,
        ).pack(side="right", pady=7)
        ctk.CTkButton(
            top, text="Undo", width=72,
            command=self._undo_last,
        ).pack(side="right", padx=(0, 4), pady=7)

        # Matplotlib canvas
        self.fig = Figure(figsize=(9.5, 4.0), tight_layout=True)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=6)

        # Matplotlib navigation toolbar (pan / zoom)
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

        self.ax.plot(
            self.df[x_col], self.df[y_col],
            linewidth=1.3, color="#4A90D9", zorder=2,
        )
        self.ax.set_xlabel(x_col, fontsize=10)
        self.ax.set_ylabel("Angle (°)", fontsize=10)
        self.ax.set_title(self.movement_name, fontsize=11, pad=8)
        self.ax.grid(True, alpha=0.3, zorder=1)
        self.canvas.draw_idle()

    # ── event handlers ─────────────────────────────────────────────────────

    def _on_click(self, event) -> None:
        if event.inaxes != self.ax:
            return
        if self._nav.mode:  # pan or zoom is active — ignore clicks
            return

        idx = len(self._markers)
        is_start = idx % 2 == 0
        color = "#3DB85E" if is_start else "#E05252"
        rep_num = idx // 2 + 1
        label = f"S{rep_num}" if is_start else f"E{rep_num}"

        vl = self.ax.axvline(
            x=event.xdata, color=color,
            linestyle="--", linewidth=1.6, alpha=0.85, zorder=3,
        )
        txt = self.ax.text(
            event.xdata, 0.97, label,
            color=color, fontsize=8, ha="center", va="top",
            transform=self.ax.get_xaxis_transform(), zorder=4,
        )

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
