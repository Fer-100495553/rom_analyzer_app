from __future__ import annotations

import math
import numpy as np
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from translations import t

# Colours for up to 10 repetitions
_REP_COLOURS = [
    "#4C9BE8", "#E8734C", "#4CE87A", "#E8D44C", "#C44CE8",
    "#4CE8D4", "#E84C6E", "#8EE84C", "#E8974C", "#4C6EE8",
]
_EXCLUDED_COLOUR = "#555555"


class IndividualReviewWindow(ctk.CTkToplevel):
    """
    Modal window that shows N repetition curves superimposed for one
    movement+side combination in Individual recording mode.

    Attributes:
        result: None if cancelled, else dict with keys:
            "extended"   – output of compute_individual_stats (after exclusions)
            "excluded"   – list of 0-based rep indices excluded by the user
            "angle_data" – first included curve (for compatibility with Screen 4)
    """

    def __init__(
        self,
        parent,
        movement_name: str,
        curves: list[np.ndarray],
        *,
        offset_val: float | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(t("ir_title").format(movement=movement_name))
        self.geometry("900x680")
        self.resizable(True, True)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._movement_name = movement_name
        self._curves = curves
        self._offset_val = offset_val
        self._excluded: set[int] = set()
        self._exclude_mode = False
        self.result = None

        # Per-rep raw ROM/Peak/Valley (full curve, no segments)
        self._rep_rom: list[float] = []
        self._rep_peak: list[float] = []
        self._rep_valley: list[float] = []
        for c in curves:
            valid = c[~np.isnan(c)]
            if valid.size == 0:
                self._rep_rom.append(float("nan"))
                self._rep_peak.append(float("nan"))
                self._rep_valley.append(float("nan"))
            else:
                pk = float(np.nanmax(c))
                vl = float(np.nanmin(c))
                self._rep_rom.append(pk - vl)
                self._rep_peak.append(pk)
                self._rep_valley.append(vl)

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main.grid_rowconfigure(0, weight=3)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # ── Plot area ──────────────────────────────────────────────────────
        plot_frame = ctk.CTkFrame(main)
        plot_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self._fig, self._ax = plt.subplots(figsize=(8, 4), tight_layout=True)
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._draw_plot()

        # ── Summary table ──────────────────────────────────────────────────
        tbl_frame = ctk.CTkFrame(main)
        tbl_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self._tbl_frame = tbl_frame
        self._build_table()

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(main, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew")

        ctk.CTkButton(
            btn_row, text=t("ir_cancel"), width=130,
            command=self._on_cancel,
        ).pack(side="left")

        self._exclude_btn = ctk.CTkButton(
            btn_row, text=t("ir_exclude"), width=180,
            command=self._toggle_exclude_mode,
        )
        self._exclude_btn.pack(side="left", padx=8)

        self._hint_lbl = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=10), text_color="gray",
        )
        self._hint_lbl.pack(side="left", padx=4)

        ctk.CTkButton(
            btn_row, text=t("ir_accept"), width=160,
            font=ctk.CTkFont(weight="bold"),
            command=self._on_accept,
        ).pack(side="right")

    # ── Plot ───────────────────────────────────────────────────────────────

    def _draw_plot(self) -> None:
        ax = self._ax
        ax.clear()
        ax.set_title(self._movement_name, fontsize=12)
        ax.set_xlabel("Frame")
        ax.set_ylabel("Angle (°)")

        for i, curve in enumerate(self._curves):
            colour = (_EXCLUDED_COLOUR if i in self._excluded
                      else _REP_COLOURS[i % len(_REP_COLOURS)])
            alpha = 0.25 if i in self._excluded else 0.9
            label = t("ir_hdr_rep") + f" {i + 1}"
            if i in self._excluded:
                label += f"  {t('ir_excluded_label')}"
            x = np.arange(len(curve))
            ax.plot(x, curve, color=colour, alpha=alpha, linewidth=1.5,
                    label=label)

            if i not in self._excluded:
                pk_idx = int(np.nanargmax(curve))
                vl_idx = int(np.nanargmin(curve))
                pk_val = curve[pk_idx]
                vl_val = curve[vl_idx]
                ax.plot(pk_idx, pk_val, marker="^", color="red",
                        markersize=7, zorder=5)
                ax.annotate(f"{pk_val:.1f}°",
                            xy=(pk_idx, pk_val),
                            xytext=(4, 4), textcoords="offset points",
                            fontsize=7, color="red")
                ax.plot(vl_idx, vl_val, marker="v", color="#4C9BE8",
                        markersize=7, zorder=5)
                ax.annotate(f"{vl_val:.1f}°",
                            xy=(vl_idx, vl_val),
                            xytext=(4, -10), textcoords="offset points",
                            fontsize=7, color="#4C9BE8")

        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, alpha=0.3)
        self._canvas.draw()

    # ── Table ──────────────────────────────────────────────────────────────

    def _build_table(self) -> None:
        for w in self._tbl_frame.winfo_children():
            w.destroy()

        headers = [t("ir_hdr_rep"), t("ir_hdr_rom"),
                   t("ir_hdr_peak"), t("ir_hdr_valley")]
        col_w = [80, 90, 90, 90]

        scroll = ctk.CTkScrollableFrame(self._tbl_frame, height=130)
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        for c, (h, w) in enumerate(zip(headers, col_w)):
            ctk.CTkLabel(
                scroll, text=h, width=w,
                font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
            ).grid(row=0, column=c, padx=2, pady=2, sticky="w")

        active_roms: list[float] = []
        active_peaks: list[float] = []
        active_valleys: list[float] = []

        self._row_frames: list[ctk.CTkFrame] = []

        for i in range(len(self._curves)):
            excluded = i in self._excluded
            rom_v  = self._rep_rom[i]
            pk_v   = self._rep_peak[i]
            vl_v   = self._rep_valley[i]

            if not excluded:
                active_roms.append(rom_v)
                active_peaks.append(pk_v)
                active_valleys.append(vl_v)

            colour = _EXCLUDED_COLOUR if excluded else _REP_COLOURS[i % len(_REP_COLOURS)]
            rep_label = t("ir_hdr_rep") + f" {i + 1}"
            if excluded:
                rep_label += f"  {t('ir_excluded_label')}"

            row_vals = [
                rep_label,
                f"{rom_v:.1f}" if not math.isnan(rom_v) else "—",
                f"{pk_v:.1f}"  if not math.isnan(pk_v)  else "—",
                f"{vl_v:.1f}"  if not math.isnan(vl_v)  else "—",
            ]

            row_frame = ctk.CTkFrame(scroll, fg_color="transparent",
                                     cursor="hand2" if self._exclude_mode else "")
            row_frame.grid(row=i + 1, column=0, columnspan=4,
                           sticky="ew", pady=1)
            self._row_frames.append(row_frame)

            if self._exclude_mode:
                row_frame.bind("<Button-1>",
                               lambda e, idx=i: self._toggle_rep(idx))

            for c, (val, w) in enumerate(zip(row_vals, col_w)):
                lbl = ctk.CTkLabel(
                    row_frame, text=val, width=w,
                    font=ctk.CTkFont(size=11), anchor="w",
                    text_color=colour,
                )
                lbl.grid(row=0, column=c, padx=2, pady=1, sticky="w")
                if self._exclude_mode:
                    lbl.bind("<Button-1>",
                             lambda e, idx=i: self._toggle_rep(idx))

        # Mean ± SD row
        def _fmt_mean_sd(vals: list[float]) -> str:
            valid = [v for v in vals if not math.isnan(v)]
            if not valid:
                return "—"
            m = np.mean(valid)
            s = np.std(valid, ddof=1) if len(valid) > 1 else 0.0
            return f"{m:.1f} ± {s:.1f}"

        mean_row = i + 2  # after last rep row
        summary_vals = [
            t("ir_row_mean"),
            _fmt_mean_sd(active_roms),
            _fmt_mean_sd(active_peaks),
            _fmt_mean_sd(active_valleys),
        ]
        for c, (val, w) in enumerate(zip(summary_vals, col_w)):
            ctk.CTkLabel(
                scroll, text=val, width=w,
                font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
            ).grid(row=mean_row, column=c, padx=2, pady=(4, 2), sticky="w")

    # ── Exclude logic ──────────────────────────────────────────────────────

    def _toggle_exclude_mode(self) -> None:
        self._exclude_mode = not self._exclude_mode
        self._hint_lbl.configure(
            text=t("ir_exclude_mode_hint") if self._exclude_mode else "")
        self._exclude_btn.configure(
            fg_color=("#3a7ebf" if self._exclude_mode
                      else ctk.ThemeManager.theme["CTkButton"]["fg_color"]))
        self._build_table()

    def _toggle_rep(self, idx: int) -> None:
        if idx in self._excluded:
            self._excluded.discard(idx)
        else:
            self._excluded.add(idx)
        self._draw_plot()
        self._build_table()

    # ── Accept / Cancel ────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        from data_processing import compute_individual_stats, apply_offset

        active_curves = [
            c for i, c in enumerate(self._curves)
            if i not in self._excluded
        ]
        if not active_curves:
            active_curves = list(self._curves)

        if self._offset_val is not None:
            active_curves = [apply_offset(c, self._offset_val)
                             for c in active_curves]

        extended = compute_individual_stats(active_curves)

        self.result = {
            "extended":   extended,
            "excluded":   sorted(self._excluded),
            "angle_data": active_curves[0],
            "offset":     self._offset_val,
            "segments":   [],
        }
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.grab_release()
        self.destroy()
