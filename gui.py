from __future__ import annotations

import logging
import math
import os

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog, messagebox

logger = logging.getLogger(__name__)

# ── Side display label for no-prefix variables ────────────────────────────
_NO_SIDE = "—"


# ══════════════════════════════════════════════════════════════════════════
#  Small UI helpers
# ══════════════════════════════════════════════════════════════════════════

def _card(parent, title: str) -> ctk.CTkFrame:
    """Labelled card frame used as a section container."""
    frame = ctk.CTkFrame(parent)
    ctk.CTkLabel(
        frame, text=title,
        font=ctk.CTkFont(size=11, weight="bold"), text_color="gray",
    ).pack(anchor="w", padx=12, pady=(10, 4))
    return frame


# ══════════════════════════════════════════════════════════════════════════
#  App — 4-screen ROM analysis application
# ══════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    """
    Four-screen ROM analysis application.

    Screen 1 — Study Configuration: movement selection + laterality.
    Screen 2 — File Import: one C3D row per movement+side combination.
    Screen 3 — Segmentation: C3DSegmentationWindow per movement+side (modal).
    Screen 4 — Summary & Export: table, chart, CSV, report.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("ROM Analyzer — Vicon Nexus")
        self.geometry("800x740")       # fallback before zoomed kicks in
        self.resizable(True, True)
        self.state("zoomed")           # open maximized on Windows
        self.bind("<F11>", lambda e: self.attributes("-fullscreen",
                                                     not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # ── Persistent session state ──────────────────────────────────────
        # Screen 1
        self._movement_vars: dict[str, ctk.BooleanVar] = {}
        self._laterality_var = ctk.StringVar(value="bilateral")

        # Screen 2 — list of import-row dicts, one per (movement, side) combo
        # Each dict: mv_name, side, loaded, angle_data, frame_rate, events,
        #            file_lbl (widget), status_lbl (widget)
        self._import_rows: list[dict] = []
        self._process_btn: ctk.CTkButton | None = None   # "Process All →"

        # Screen 3 / 4 — keyed by (mv_name, side)
        self._processed: dict[tuple[str, str], dict] = {}

        # ── Persistent title bar ──────────────────────────────────────────
        ctk.CTkLabel(
            self, text="ROM Analyzer",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(20, 2))
        ctk.CTkLabel(
            self, text="Vicon Nexus  ·  Range of Motion Analysis",
            text_color="gray",
        ).pack(pady=(0, 12))

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        self._show_screen_1()

    # ── Screen helpers ─────────────────────────────────────────────────────

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 1 — Study Configuration
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_1(self) -> None:
        self._clear_container()
        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        # ── A: Movement selection ─────────────────────────────────────────
        card_mv = _card(f, "SELECT MOVEMENTS TO ANALYZE")
        card_mv.pack(fill="x", pady=(0, 8))

        from config import MOVEMENT_DEFINITIONS
        self._movement_vars.clear()

        for mv_name, mv_def in MOVEMENT_DEFINITIONS.items():
            row = ctk.CTkFrame(card_mv, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            var = ctk.BooleanVar(value=False)
            self._movement_vars[mv_name] = var

            is_optional = mv_def.get("optional", False)
            display = mv_name if not is_optional else f"{mv_name}  (not yet available)"
            cb = ctk.CTkCheckBox(
                row, text=display, variable=var, width=380,
                state="disabled" if is_optional else "normal",
            )
            cb.pack(side="left")

        # Select All / Deselect All
        sel_row = ctk.CTkFrame(card_mv, fg_color="transparent")
        sel_row.pack(anchor="w", padx=12, pady=(6, 10))
        ctk.CTkButton(sel_row, text="Select All", width=100,
                      command=self._select_all).pack(side="left", padx=(0, 8))
        ctk.CTkButton(sel_row, text="Deselect All", width=100,
                      command=self._deselect_all).pack(side="left")

        # ── B: Laterality ─────────────────────────────────────────────────
        card_lat = _card(f, "LATERALITY")
        card_lat.pack(fill="x", pady=(0, 8))

        lat_row = ctk.CTkFrame(card_lat, fg_color="transparent")
        lat_row.pack(anchor="w", padx=12, pady=(0, 10))

        for text, val, hint in [
            ("Bilateral",  "bilateral",  "one shared C3D per movement → extracts Left + Right"),
            ("Unilateral", "unilateral", "separate C3D per side per movement"),
        ]:
            col = ctk.CTkFrame(lat_row, fg_color="transparent")
            col.pack(side="left", padx=(0, 28))
            ctk.CTkRadioButton(
                col, text=text,
                variable=self._laterality_var, value=val,
            ).pack(anchor="w")
            ctk.CTkLabel(col, text=hint,
                         font=ctk.CTkFont(size=10), text_color="gray"
                         ).pack(anchor="w", padx=(22, 0))

        # ── C: Continue button ────────────────────────────────────────────
        ctk.CTkButton(
            f, text="Continue to File Import →",
            height=44, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._go_to_screen_2,
        ).pack(fill="x", pady=(8, 0))

    def _select_all(self) -> None:
        from config import MOVEMENT_DEFINITIONS
        for mv_name, var in self._movement_vars.items():
            if not MOVEMENT_DEFINITIONS[mv_name].get("optional", False):
                var.set(True)

    def _deselect_all(self) -> None:
        for var in self._movement_vars.values():
            var.set(False)

    def _go_to_screen_2(self) -> None:
        selected = [mv for mv, var in self._movement_vars.items() if var.get()]
        if not selected:
            messagebox.showerror(
                "No movements selected",
                "Please select at least one movement before continuing.",
            )
            return
        self._show_screen_2(selected)

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 2 — File Import
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_2(self, selected_movements: list[str]) -> None:
        self._clear_container()
        self._import_rows.clear()
        self._processed.clear()

        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        card_imp = _card(f, "IMPORT C3D FILES  (one file per row)")
        card_imp.pack(fill="x", pady=(0, 8))

        # Table header
        hdr = ctk.CTkFrame(card_imp, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(0, 4))
        for text, w in [("Movement", 200), ("Side", 60), ("File", 280),
                        ("", 80), ("", 30)]:
            ctk.CTkLabel(hdr, text=text, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side="left", padx=2)

        # Scrollable body
        scroll = ctk.CTkScrollableFrame(card_imp, height=320)
        scroll.pack(fill="x", padx=12, pady=(0, 8))

        from config import MOVEMENT_DEFINITIONS
        laterality = self._laterality_var.get()

        for mv_name in selected_movements:
            mv_def = MOVEMENT_DEFINITIONS[mv_name]
            has_prefix = mv_def["has_side_prefix"]

            # Build the list of (side_label, is_bilateral) tuples for this movement.
            # is_bilateral=True  → one file, both L+R extracted from it
            # is_bilateral=False → one file per row, single side extracted
            if not has_prefix:
                row_specs = [(_NO_SIDE, False)]
            elif laterality == "bilateral":
                row_specs = [("L+R", True)]   # one shared file, two results
            else:                              # unilateral → separate files
                row_specs = [("Left", False), ("Right", False)]

            for side_label, is_bilateral in row_specs:
                # Outer vertical container for main row + offset row
                row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=3)

                # ── Main info row ──────────────────────────────────────────
                main_row = ctk.CTkFrame(row_frame, fg_color="transparent")
                main_row.pack(fill="x")

                ctk.CTkLabel(main_row, text=mv_name, width=200,
                             anchor="w", font=ctk.CTkFont(size=11)
                             ).pack(side="left", padx=2)
                ctk.CTkLabel(main_row, text=side_label, width=60,
                             anchor="center", font=ctk.CTkFont(size=11)
                             ).pack(side="left", padx=2)

                file_lbl = ctk.CTkLabel(
                    main_row, text="No file selected", width=280,
                    anchor="w", font=ctk.CTkFont(size=10), text_color="gray",
                )
                file_lbl.pack(side="left", padx=2)

                offset_var = ctk.BooleanVar(value=False)
                row_data: dict = {
                    "mv_name": mv_name,
                    "side": side_label,
                    "bilateral": is_bilateral,
                    "loaded": False,
                    "angle_data": None,
                    "angle_data_left": None,
                    "angle_data_right": None,
                    "frame_rate": None,
                    "events": None,
                    "file_lbl": file_lbl,
                    "status_lbl": None,
                    "offset_var": offset_var,
                }
                self._import_rows.append(row_data)

                ctk.CTkButton(
                    main_row, text="Browse…", width=80,
                    command=lambda rd=row_data: self._browse_c3d(rd),
                ).pack(side="left", padx=4)

                status_lbl = ctk.CTkLabel(
                    main_row, text="✗", width=28,
                    font=ctk.CTkFont(size=14), text_color="#E05252",
                )
                status_lbl.pack(side="left", padx=2)
                row_data["status_lbl"] = status_lbl

                # ── Offset correction row (enabled after file load) ────────
                offset_row = ctk.CTkFrame(row_frame, fg_color="transparent")
                offset_row.pack(fill="x", padx=4, pady=(0, 2))

                # Indent to align with file column (movement + side widths)
                ctk.CTkLabel(offset_row, text="", width=268).pack(side="left")

                if is_bilateral:
                    off_left_var  = ctk.StringVar(value="0.0")
                    off_right_var = ctk.StringVar(value="0.0")
                    row_data["offset_left_var"]  = off_left_var
                    row_data["offset_right_var"] = off_right_var

                    off_left_entry  = ctk.CTkEntry(
                        offset_row, textvariable=off_left_var, width=60, state="disabled")
                    off_right_entry = ctk.CTkEntry(
                        offset_row, textvariable=off_right_var, width=60, state="disabled")

                    def _make_bilateral_toggle(cb_v, el, er):
                        def _toggle():
                            s = "normal" if cb_v.get() else "disabled"
                            el.configure(state=s)
                            er.configure(state=s)
                        return _toggle

                    off_cb = ctk.CTkCheckBox(
                        offset_row, text="Apply offset correction", width=180,
                        variable=offset_var, state="disabled",
                        command=_make_bilateral_toggle(offset_var, off_left_entry, off_right_entry),
                    )
                    off_cb.pack(side="left", padx=(0, 4))
                    ctk.CTkLabel(offset_row, text="L:",
                                 font=ctk.CTkFont(size=10)).pack(side="left")
                    off_left_entry.pack(side="left", padx=2)
                    ctk.CTkLabel(offset_row, text="R:",
                                 font=ctk.CTkFont(size=10)).pack(side="left", padx=(6, 0))
                    off_right_entry.pack(side="left", padx=2)
                    row_data["offset_cb"]          = off_cb
                    row_data["offset_left_entry"]  = off_left_entry
                    row_data["offset_right_entry"] = off_right_entry
                else:
                    off_entry_var = ctk.StringVar(value="0.0")
                    row_data["offset_entry_var"] = off_entry_var
                    off_entry = ctk.CTkEntry(
                        offset_row, textvariable=off_entry_var, width=70, state="disabled")

                    def _make_toggle(cb_v, entry):
                        def _toggle():
                            entry.configure(state="normal" if cb_v.get() else "disabled")
                        return _toggle

                    off_cb = ctk.CTkCheckBox(
                        offset_row, text="Apply offset correction", width=180,
                        variable=offset_var, state="disabled",
                        command=_make_toggle(offset_var, off_entry),
                    )
                    off_cb.pack(side="left", padx=(0, 4))
                    off_entry.pack(side="left", padx=2)
                    row_data["offset_cb"]    = off_cb
                    row_data["offset_entry"] = off_entry

                ctk.CTkLabel(
                    offset_row,
                    text="Enter the angle value at neutral position (0°)."
                         " This value will be subtracted from the entire curve.",
                    font=ctk.CTkFont(size=9), text_color="gray",
                ).pack(side="left", padx=(6, 0))

        # Navigation buttons
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(
            nav, text="← Back to Configuration", width=180,
            command=self._show_screen_1,
        ).pack(side="left")

        self._process_btn = ctk.CTkButton(
            nav, text="Process All →",
            height=40, width=160,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self._start_segmentation,
        )
        self._process_btn.pack(side="right")

    def _browse_c3d(self, row_data: dict) -> None:
        path = filedialog.askopenfilename(
            title=f"C3D for {row_data['mv_name']} — {row_data['side']}",
            filetypes=[("C3D files", "*.c3d"), ("All files", "*.*")],
        )
        if not path:
            return

        from data_processing import read_c3d, list_available_angles
        from config import MOVEMENT_DEFINITIONS

        try:
            c3d_data = read_c3d(path)
        except Exception as exc:
            messagebox.showerror("Load error", f"Could not read C3D file:\n{exc}")
            return

        mv_def = MOVEMENT_DEFINITIONS[row_data["mv_name"]]
        has_prefix = mv_def["has_side_prefix"]
        component = mv_def["component"]
        sulm_var = mv_def["sulm_variable"]
        model_outputs = c3d_data["model_outputs"]
        fname = os.path.basename(path)

        if row_data["bilateral"]:
            # Bilateral: extract Left AND Right from the same file
            var_left  = f"Left{sulm_var}"
            var_right = f"Right{sulm_var}"
            missing = [v for v in (var_left, var_right) if v not in model_outputs]
            if missing:
                available = list_available_angles(c3d_data)
                messagebox.showwarning(
                    "Variable(s) not found",
                    f"The following expected label(s) were not found in this C3D:\n"
                    f"  {chr(10).join(missing)}\n\n"
                    f"Available angle outputs:\n  "
                    + "\n  ".join(available),
                )
                return
            row_data["angle_data_left"]  = model_outputs[var_left][component, :].astype(float)
            row_data["angle_data_right"] = model_outputs[var_right][component, :].astype(float)
            row_data["angle_data"]       = row_data["angle_data_left"]  # convenience alias

        else:
            # Unilateral or no-prefix: extract the single expected variable
            side = row_data["side"]
            if has_prefix and side != _NO_SIDE:
                full_var = f"{side}{sulm_var}"   # "Left<var>" or "Right<var>"
            else:
                full_var = sulm_var

            if full_var not in model_outputs:
                available = list_available_angles(c3d_data)
                messagebox.showwarning(
                    "Variable not found",
                    f"Expected label  '{full_var}'  was not found in this C3D file.\n\n"
                    f"Available angle outputs:\n  "
                    + "\n  ".join(available),
                )
                return
            row_data["angle_data"] = model_outputs[full_var][component, :].astype(float)

        row_data["loaded"]     = True
        row_data["frame_rate"] = c3d_data["frame_rate"]
        row_data["events"]     = c3d_data.get("events", [])

        row_data["file_lbl"].configure(text=fname, text_color="white")
        row_data["status_lbl"].configure(text="✓", text_color="#4CAF50")
        if "offset_cb" in row_data:
            row_data["offset_cb"].configure(state="normal")

        self._update_process_btn()

    def _update_process_btn(self) -> None:
        all_loaded = all(r["loaded"] for r in self._import_rows)
        if self._process_btn is not None:
            self._process_btn.configure(
                state="normal" if all_loaded else "disabled")

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 3 — Segmentation (modal windows per movement+side)
    # ══════════════════════════════════════════════════════════════════════

    def _start_segmentation(self) -> None:
        from segmentation import C3DSegmentationWindow
        from data_processing import apply_offset, compute_extended_stats_array

        for row_data in self._import_rows:
            mv_name    = row_data["mv_name"]
            frame_rate = row_data["frame_rate"]
            events     = row_data["events"] or []
            offset_on  = row_data["offset_var"].get()

            if row_data["bilateral"]:
                try:
                    off_l = float(row_data["offset_left_var"].get()) if offset_on else 0.0
                except (ValueError, KeyError):
                    off_l = 0.0
                try:
                    off_r = float(row_data["offset_right_var"].get()) if offset_on else 0.0
                except (ValueError, KeyError):
                    off_r = 0.0

                sides_to_seg: list[tuple] = [
                    ("Left",
                     apply_offset(row_data["angle_data_left"], off_l) if offset_on
                     else row_data["angle_data_left"],
                     off_l if offset_on else None),
                    ("Right",
                     apply_offset(row_data["angle_data_right"], off_r) if offset_on
                     else row_data["angle_data_right"],
                     off_r if offset_on else None),
                ]
            else:
                try:
                    off = float(row_data["offset_entry_var"].get()) if offset_on else 0.0
                except (ValueError, KeyError):
                    off = 0.0
                ang = apply_offset(row_data["angle_data"], off) if offset_on else row_data["angle_data"]
                sides_to_seg = [(row_data["side"], ang, off if offset_on else None)]

            for side, angle_arr, offset_val in sides_to_seg:
                title = f"{mv_name} — {side}" if side != _NO_SIDE else mv_name

                win = C3DSegmentationWindow(
                    self,
                    movement_name=title,
                    angle_data=angle_arr,
                    frame_rate=frame_rate,
                    events=events,
                )
                self.wait_window(win)

                if win.result is not None:
                    segs = win.result.get("segments", [])
                    self._processed[(mv_name, side)] = {
                        "movement":   mv_name,
                        "side":       side,
                        "angle_data": angle_arr,
                        "frame_rate": frame_rate,
                        "offset":     offset_val,
                        "extended":   compute_extended_stats_array(angle_arr, segs),
                        **win.result,
                    }
                else:
                    logger.info("Segmentation cancelled for '%s' — %s.", mv_name, side)

        if not self._processed:
            messagebox.showinfo(
                "No results",
                "No movements were successfully segmented. "
                "Returning to the import screen.",
            )
            return

        self._show_screen_4()

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 4 — Summary & Export
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_4(self) -> None:
        self._clear_container()
        self._layout_vertical = True

        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        # ── Top bar: layout toggle ─────────────────────────────────────────
        top_bar = ctk.CTkFrame(f, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 4))

        self._layout_toggle_btn = ctk.CTkButton(
            top_bar, text="⬌ Horizontal layout", width=190,
            command=self._toggle_layout,
        )
        self._layout_toggle_btn.pack(side="right")

        # ── Content area (table + chart, reorganised by toggle) ────────────
        self._layout_content = ctk.CTkFrame(f, fg_color="transparent")
        self._layout_content.pack(fill="both", expand=True)

        self._layout_card_tbl = _card(self._layout_content, "RESULTS")
        self._build_summary_table(self._layout_card_tbl)

        self._layout_card_chart = _card(self._layout_content, "ROM OVERVIEW")
        self._build_rom_chart(self._layout_card_chart)

        self._apply_layout()

        # ── Bottom action bar ──────────────────────────────────────────────
        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))

        ctk.CTkButton(
            btn_row, text="Export CSV", width=130,
            command=self._export_csv,
        ).pack(side="left")
        ctk.CTkButton(
            btn_row, text="New Analysis →", width=150,
            font=ctk.CTkFont(weight="bold"),
            command=self._new_analysis,
        ).pack(side="right")
        ctk.CTkButton(
            btn_row, text="Generate Report", width=150,
            command=self._generate_report,
        ).pack(side="right", padx=4)

    def _apply_layout(self) -> None:
        content    = self._layout_content
        card_tbl   = self._layout_card_tbl
        card_chart = self._layout_card_chart

        card_tbl.grid_forget()
        card_chart.grid_forget()

        if self._layout_vertical:
            content.grid_rowconfigure(0, weight=1, minsize=0)
            content.grid_rowconfigure(1, weight=1, minsize=0)
            content.grid_columnconfigure(0, weight=1, minsize=0)
            content.grid_columnconfigure(1, weight=0, minsize=0)

            card_tbl.grid(row=0, column=0, columnspan=2,
                          sticky="nsew", pady=(0, 4))
            card_chart.grid(row=1, column=0, columnspan=2,
                            sticky="nsew")

            self._layout_toggle_btn.configure(text="⬌ Horizontal layout")
        else:
            content.grid_rowconfigure(0, weight=1, minsize=0)
            content.grid_rowconfigure(1, weight=0, minsize=0)
            content.grid_columnconfigure(0, weight=1, minsize=0)
            content.grid_columnconfigure(1, weight=1, minsize=0)

            card_tbl.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
            card_chart.grid(row=0, column=1, sticky="nsew")

            self._layout_toggle_btn.configure(text="⬍ Vertical layout")

    def _toggle_layout(self) -> None:
        self._layout_vertical = not self._layout_vertical
        self._apply_layout()

    def _build_summary_table(self, parent: ctk.CTkFrame) -> None:
        headers = ["Movement", "Side", "Metric", "N", "Mean (°)", "SD (°)", "Min (°)", "Max (°)"]
        col_w   = [180,       55,     65,        36,  70,         60,        60,        60]

        scroll = ctk.CTkScrollableFrame(parent, height=200)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # Header row
        for c, (h, w) in enumerate(zip(headers, col_w)):
            ctk.CTkLabel(scroll, text=h, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").grid(row=0, column=c, padx=2, pady=2, sticky="w")

        row_idx = 1
        offset_notes: list[str] = []

        for group_idx, ((mv_name, side), data) in enumerate(self._processed.items()):
            extended   = data.get("extended", {})
            offset_val = data.get("offset")

            if offset_val is not None:
                offset_notes.append(
                    f"{mv_name} ({side}): {offset_val:.1f}° subtracted"
                )

            bg = "#2A2D2E" if group_idx % 2 == 0 else "transparent"

            for sub_idx, (metric_label, stats) in enumerate([
                ("ROM",    extended.get("rom",    {})),
                ("Peak",   extended.get("peak",   {})),
                ("Valley", extended.get("valley", {})),
            ]):
                values  = stats.get("values", [])
                mean_v  = stats.get("mean", float("nan"))
                sd_v    = stats.get("sd",   0.0)
                min_v   = stats.get("min",  float("nan"))
                max_v   = stats.get("max",  float("nan"))

                row_vals = [
                    mv_name if sub_idx == 0 else "",
                    side    if sub_idx == 0 else "",
                    metric_label,
                    str(len(values)),
                    f"{mean_v:.1f}" if not math.isnan(mean_v) else "—",
                    f"{sd_v:.1f}",
                    f"{min_v:.1f}"  if not math.isnan(min_v)  else "—",
                    f"{max_v:.1f}"  if not math.isnan(max_v)  else "—",
                ]

                for c, (val, w) in enumerate(zip(row_vals, col_w)):
                    ctk.CTkLabel(scroll, text=val, width=w,
                                 font=ctk.CTkFont(size=11), anchor="w",
                                 fg_color=bg).grid(row=row_idx, column=c,
                                                   padx=2, pady=1, sticky="w")
                row_idx += 1

        # Offset footnote
        if offset_notes:
            note = ("* Offset correction applied (neutral position calibration): "
                    + "; ".join(offset_notes) + ".")
            ctk.CTkLabel(parent, text=note,
                         font=ctk.CTkFont(size=9), text_color="gray",
                         anchor="w", wraplength=780,
                         ).pack(fill="x", padx=12, pady=(0, 4))

    def _build_rom_chart(self, parent: ctk.CTkFrame) -> None:
        from plotting import plot_rom_summary

        # Build a flat string-keyed dict for the plotting function.
        # Key format: "Movement\n(Side)" for bilateral, "Movement" for no-side rows.
        chart_data: dict[str, dict] = {}
        for (mv_name, side), data in self._processed.items():
            key = f"{mv_name}\n({side})" if side != _NO_SIDE else mv_name
            chart_data[key] = data

        try:
            # Pass an empty normative dict — normative lines are not meaningful
            # when keys are composite strings; avoids accidental type errors.
            fig = plot_rom_summary(chart_data, normative={})
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 8))
        except Exception as exc:
            ctk.CTkLabel(parent, text=f"Chart unavailable: {exc}",
                         text_color="gray").pack(padx=12, pady=4)

    # ── Export ─────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._processed:
            return

        out_path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="ROM_Summary.csv",
        )
        if not out_path:
            return

        rows = []
        for (mv_name, side), data in self._processed.items():
            extended   = data.get("extended", {})
            offset_val = data.get("offset")

            for metric_key, metric_label in (
                ("rom", "ROM"), ("peak", "Peak"), ("valley", "Valley")
            ):
                stats  = extended.get(metric_key, {})
                values = stats.get("values", [])
                m      = stats.get("mean", float("nan"))
                s      = stats.get("sd",   0.0)
                mn     = stats.get("min",  float("nan"))
                mx     = stats.get("max",  float("nan"))

                rows.append({
                    "Movement":   mv_name,
                    "Side":       side,
                    "Metric":     metric_label,
                    "N_reps":     len(values),
                    "Mean_deg":   round(m,  2) if not math.isnan(m)  else None,
                    "SD_deg":     round(s,  2),
                    "Min_deg":    round(mn, 2) if not math.isnan(mn) else None,
                    "Max_deg":    round(mx, 2) if not math.isnan(mx) else None,
                    "Values_deg": ";".join(
                        f"{v:.2f}" if not math.isnan(v) else "nan" for v in values
                    ),
                    "Offset_deg": f"{offset_val:.2f}" if offset_val is not None else "",
                })

        pd.DataFrame(rows).to_csv(out_path, index=False)

        msg = f"CSV saved:\n{out_path}"
        offset_entries = [
            (mv, sd, d["offset"])
            for (mv, sd), d in self._processed.items()
            if d.get("offset") is not None
        ]
        if offset_entries:
            notes = [
                f"  {mv} ({sd}): {off:.1f}° subtracted (neutral position calibration)"
                for mv, sd, off in offset_entries
            ]
            msg += "\n\nOffset correction applied:\n" + "\n".join(notes)
        messagebox.showinfo("Saved", msg)

    def _generate_report(self) -> None:
        messagebox.showinfo("Coming soon", "Report generation will be available in a future version.")

    def _new_analysis(self) -> None:
        self._import_rows.clear()
        self._processed.clear()
        self._process_btn = None
        self._laterality_var.set("bilateral")
        self._show_screen_1()
