from __future__ import annotations

import logging
import math
import os

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import filedialog, messagebox

import settings_manager
from translations import t

logger = logging.getLogger(__name__)

# ── Side display label for no-prefix variables ────────────────────────────
_NO_SIDE = "—"

# ── Widget keys excluded when saving/restoring import-row state ────────────
_ROW_WIDGET_KEYS = frozenset({
    "file_lbl", "status_lbl", "offset_cb",
    "offset_entry", "offset_left_entry", "offset_right_entry",
    "offset_var", "offset_entry_var", "offset_left_var", "offset_right_var",
})


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
        self.title(t("app_title"))
        self.geometry("800x740")
        self.resizable(True, True)
        self.state("zoomed")
        self.bind("<F11>", lambda e: self.attributes("-fullscreen",
                                                     not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

        # ── Persistent session state ──────────────────────────────────────
        self._movement_vars: dict[str, ctk.BooleanVar] = {}
        self._laterality_var = ctk.StringVar(value="bilateral")
        self._recording_type_var = ctk.StringVar(value="continuous")
        self._num_reps_var = ctk.IntVar(value=6)
        self._import_rows: list[dict] = []
        self._process_btn: ctk.CTkButton | None = None
        self._processed: dict[tuple[str, str], dict] = {}

        # Navigation state (used to re-render on language change)
        self._current_screen: int = 1
        self._selected_movements: list[str] = []

        # ── Persistent header ─────────────────────────────────────────────
        _hdr = ctk.CTkFrame(self, fg_color="transparent")
        _hdr.pack(fill="x", padx=20, pady=(20, 2))
        _hdr.grid_columnconfigure(0, weight=1)   # left spacer
        _hdr.grid_columnconfigure(1, weight=0)   # title (fixed width)
        _hdr.grid_columnconfigure(2, weight=1)   # right area (settings btn)

        self._title_lbl = ctk.CTkLabel(
            _hdr, text=t("app_title"),
            font=ctk.CTkFont(size=26, weight="bold"),
        )
        self._title_lbl.grid(row=0, column=0, columnspan=3, pady=(0, 2))

        self._subtitle_lbl = ctk.CTkLabel(
            _hdr, text=t("app_subtitle"), text_color="gray",
        )
        self._subtitle_lbl.grid(row=1, column=0, columnspan=3)

        # Settings button — top-right corner of the header
        _right_frame = ctk.CTkFrame(_hdr, fg_color="transparent")
        _right_frame.grid(row=0, column=2, rowspan=2, sticky="ne", pady=4)
        ctk.CTkButton(
            _right_frame, text="⚙", width=36, height=36,
            font=ctk.CTkFont(size=18),
            fg_color="transparent", border_width=1,
            command=self._open_settings,
        ).pack(anchor="e", padx=(0, 4))

        # Spacing after header
        ctk.CTkFrame(self, height=10, fg_color="transparent").pack()

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        self._show_screen_1()

    # ── Header refresh ─────────────────────────────────────────────────────

    def _refresh_header(self) -> None:
        self._title_lbl.configure(text=t("app_title"))
        self._subtitle_lbl.configure(text=t("app_subtitle"))
        self.title(t("app_title"))

    # ── Screen helpers ─────────────────────────────────────────────────────

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    def _rerender_current_screen(self) -> None:
        if self._current_screen == 1:
            self._show_screen_1()
        elif self._current_screen == 2:
            self._show_screen_2(self._selected_movements)
        elif self._current_screen == 4:
            self._show_screen_4()

    # ── Settings dialog ────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("settings_title"))
        dlg.geometry("340x260")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.lift()
        dlg.focus_force()

        # ── Language ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            dlg, text=t("settings_language_label"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(22, 6))

        lang_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        lang_frame.pack(anchor="w", padx=24)

        lang_var = ctk.StringVar(value=settings_manager.get("language"))
        for label, value in [("English", "en"), ("Español", "es")]:
            ctk.CTkRadioButton(
                lang_frame, text=label,
                variable=lang_var, value=value,
                command=lambda v=value: self._on_language_change(v, dlg),
            ).pack(side="left", padx=(0, 20))

        # ── Theme ─────────────────────────────────────────────────────────
        ctk.CTkLabel(
            dlg, text=t("settings_theme_label"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(20, 6))

        theme_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        theme_frame.pack(anchor="w", padx=24)

        theme_var = ctk.StringVar(value=settings_manager.get("theme"))
        for label_key, value in [
            ("settings_theme_system", "System"),
            ("settings_theme_dark",   "Dark"),
            ("settings_theme_light",  "Light"),
        ]:
            ctk.CTkRadioButton(
                theme_frame, text=t(label_key),
                variable=theme_var, value=value,
                command=lambda v=value: self._on_theme_change(v),
            ).pack(side="left", padx=(0, 16))

        # ── Close ─────────────────────────────────────────────────────────
        ctk.CTkButton(
            dlg, text=t("settings_close"),
            width=120, command=dlg.destroy,
        ).pack(pady=(26, 16))

    def _on_language_change(self, lang: str, dlg: ctk.CTkToplevel) -> None:
        settings_manager.set_language(lang)
        dlg.title(t("settings_title"))
        self._refresh_header()
        self._rerender_current_screen()

    def _on_theme_change(self, theme: str) -> None:
        settings_manager.set_theme(theme)
        ctk.set_appearance_mode(theme)

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 1 — Study Configuration
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_1(self) -> None:
        self._current_screen = 1
        self._clear_container()
        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        # ── A: Movement selection ─────────────────────────────────────────
        card_mv = _card(f, t("s1_card_movements"))
        card_mv.pack(fill="x", pady=(0, 8))

        from config import MOVEMENT_DEFINITIONS
        self._movement_vars.clear()

        for mv_name, mv_def in MOVEMENT_DEFINITIONS.items():
            row = ctk.CTkFrame(card_mv, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            var = ctk.BooleanVar(value=False)
            self._movement_vars[mv_name] = var

            is_optional = mv_def.get("optional", False)
            display = (mv_name if not is_optional
                       else f"{mv_name}  {t('s1_not_available')}")
            ctk.CTkCheckBox(
                row, text=display, variable=var, width=380,
                state="disabled" if is_optional else "normal",
            ).pack(side="left")

        sel_row = ctk.CTkFrame(card_mv, fg_color="transparent")
        sel_row.pack(anchor="w", padx=12, pady=(6, 10))
        ctk.CTkButton(sel_row, text=t("s1_select_all"), width=120,
                      command=self._select_all).pack(side="left", padx=(0, 8))
        ctk.CTkButton(sel_row, text=t("s1_deselect_all"), width=120,
                      command=self._deselect_all).pack(side="left")

        # ── B: Laterality ─────────────────────────────────────────────────
        card_lat = _card(f, t("s1_card_laterality"))
        card_lat.pack(fill="x", pady=(0, 8))

        lat_row = ctk.CTkFrame(card_lat, fg_color="transparent")
        lat_row.pack(anchor="w", padx=12, pady=(0, 10))

        for text_key, val, hint_key in [
            ("s1_bilateral",  "bilateral",  "s1_bilateral_hint"),
            ("s1_unilateral", "unilateral", "s1_unilateral_hint"),
        ]:
            col = ctk.CTkFrame(lat_row, fg_color="transparent")
            col.pack(side="left", padx=(0, 28))
            ctk.CTkRadioButton(
                col, text=t(text_key),
                variable=self._laterality_var, value=val,
            ).pack(anchor="w")
            ctk.CTkLabel(col, text=t(hint_key),
                         font=ctk.CTkFont(size=10), text_color="gray",
                         ).pack(anchor="w", padx=(22, 0))

        # ── C: Recording Type ─────────────────────────────────────────────
        card_rec = _card(f, t("s1_card_recording_type"))
        card_rec.pack(fill="x", pady=(0, 8))

        rec_row = ctk.CTkFrame(card_rec, fg_color="transparent")
        rec_row.pack(anchor="w", padx=12, pady=(0, 6))

        for text_key, val, hint_key in [
            ("s1_rec_continuous", "continuous", "s1_rec_continuous_hint"),
            ("s1_rec_individual", "individual", "s1_rec_individual_hint"),
        ]:
            col = ctk.CTkFrame(rec_row, fg_color="transparent")
            col.pack(side="left", padx=(0, 28))
            ctk.CTkRadioButton(
                col, text=t(text_key),
                variable=self._recording_type_var, value=val,
                command=self._on_recording_type_change,
            ).pack(anchor="w")
            ctk.CTkLabel(col, text=t(hint_key),
                         font=ctk.CTkFont(size=10), text_color="gray",
                         ).pack(anchor="w", padx=(22, 0))

        self._num_reps_row = ctk.CTkFrame(card_rec, fg_color="transparent")
        self._num_reps_row.pack(anchor="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            self._num_reps_row, text=t("s1_num_reps_label"),
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(self._num_reps_row, text="  ", width=4).pack(side="left")
        ctk.CTkButton(
            self._num_reps_row, text="−", width=28, height=28,
            command=lambda: self._num_reps_var.set(
                max(1, self._num_reps_var.get() - 1)),
        ).pack(side="left")
        self._num_reps_lbl = ctk.CTkLabel(
            self._num_reps_row, textvariable=self._num_reps_var,
            width=32, font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._num_reps_lbl.pack(side="left", padx=4)
        ctk.CTkButton(
            self._num_reps_row, text="+", width=28, height=28,
            command=lambda: self._num_reps_var.set(
                min(10, self._num_reps_var.get() + 1)),
        ).pack(side="left")

        self._on_recording_type_change()

        # ── D: Continue button ────────────────────────────────────────────
        ctk.CTkButton(
            f, text=t("s1_continue"),
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

    def _on_recording_type_change(self) -> None:
        is_individual = self._recording_type_var.get() == "individual"
        state = "normal" if is_individual else "disabled"
        for w in self._num_reps_row.winfo_children():
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _go_to_screen_2(self) -> None:
        selected = [mv for mv, var in self._movement_vars.items() if var.get()]
        if not selected:
            messagebox.showerror(
                t("s1_err_no_movements_title"),
                t("s1_err_no_movements_msg"),
            )
            return
        # Clear state on real navigation (not language re-render)
        self._import_rows.clear()
        self._processed.clear()
        self._show_screen_2(selected)

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 2 — File Import
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_2(self, selected_movements: list[str]) -> None:
        self._current_screen = 2
        self._selected_movements = selected_movements
        self._clear_container()

        is_individual = self._recording_type_var.get() == "individual"
        num_reps = self._num_reps_var.get() if is_individual else 1

        # Save loaded states before rebuilding widgets (language re-render)
        old_state: dict[tuple, dict] = {}
        for r in self._import_rows:
            key = (r["mv_name"], r["side"], r.get("rep_idx", 0))
            saved: dict = {k: v for k, v in r.items() if k not in _ROW_WIDGET_KEYS}
            for sv_key, plain_key in (
                ("offset_entry_var",  "_offset_entry"),
                ("offset_left_var",   "_offset_left"),
                ("offset_right_var",  "_offset_right"),
            ):
                if sv_key in r:
                    saved[plain_key] = r[sv_key].get()
            saved["_offset_enabled"] = r["offset_var"].get()
            old_state[key] = saved
        self._import_rows.clear()

        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        card_title = (t("s2_card_import_individual") if is_individual
                      else t("s2_card_import"))
        card_imp = _card(f, card_title)
        card_imp.pack(fill="x", pady=(0, 8))

        # Table header
        hdr = ctk.CTkFrame(card_imp, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(0, 4))
        hdr_cols = [
            (t("s2_hdr_movement"), 160),
            (t("s2_hdr_side"),      60),
        ]
        if is_individual:
            hdr_cols.append(("Rep", 46))
        hdr_cols += [
            (t("s2_hdr_file"), 260),
            ("", 80), ("", 30),
        ]
        for text, w in hdr_cols:
            ctk.CTkLabel(hdr, text=text, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side="left", padx=2)

        scroll = ctk.CTkScrollableFrame(card_imp, height=320)
        scroll.pack(fill="x", padx=12, pady=(0, 8))

        from config import MOVEMENT_DEFINITIONS
        laterality = self._laterality_var.get()

        for mv_name in selected_movements:
            mv_def = MOVEMENT_DEFINITIONS[mv_name]
            has_prefix = mv_def["has_side_prefix"]

            if not has_prefix:
                row_specs = [(_NO_SIDE, False)]
            elif laterality == "bilateral":
                row_specs = [("L+R", True)]
            else:
                row_specs = [("Left", False), ("Right", False)]

            for side_label, is_bilateral in row_specs:
                # In Individual mode: N file rows + shared offset row
                # In Continuous mode: 1 file row + offset row (existing logic)
                reps_range = range(num_reps) if is_individual else range(1)

                for rep_idx in reps_range:
                    row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
                    row_frame.pack(fill="x", pady=3)

                    main_row = ctk.CTkFrame(row_frame, fg_color="transparent")
                    main_row.pack(fill="x")

                    mv_display = mv_name if rep_idx == 0 else ""
                    ctk.CTkLabel(main_row, text=mv_display, width=160,
                                 anchor="w", font=ctk.CTkFont(size=11),
                                 ).pack(side="left", padx=2)

                    side_display = side_label if rep_idx == 0 else ""
                    ctk.CTkLabel(main_row, text=side_display, width=60,
                                 anchor="center", font=ctk.CTkFont(size=11),
                                 ).pack(side="left", padx=2)

                    if is_individual:
                        ctk.CTkLabel(
                            main_row,
                            text=t("s2_rep_label").format(n=rep_idx + 1),
                            width=46,
                            anchor="center", font=ctk.CTkFont(size=11),
                        ).pack(side="left", padx=2)

                    file_lbl = ctk.CTkLabel(
                        main_row, text=t("s2_no_file"), width=260,
                        anchor="w", font=ctk.CTkFont(size=10),
                        text_color="gray",
                    )
                    file_lbl.pack(side="left", padx=2)

                    offset_var = ctk.BooleanVar(value=False)
                    row_data: dict = {
                        "mv_name":          mv_name,
                        "side":             side_label,
                        "bilateral":        is_bilateral,
                        "rep_idx":          rep_idx,
                        "loaded":           False,
                        "filename":         "",
                        "angle_data":       None,
                        "angle_data_left":  None,
                        "angle_data_right": None,
                        "frame_rate":       None,
                        "events":           None,
                        "file_lbl":         file_lbl,
                        "status_lbl":       None,
                        "offset_var":       offset_var,
                        "is_individual":    is_individual,
                    }
                    self._import_rows.append(row_data)

                    ctk.CTkButton(
                        main_row, text=t("s2_browse"), width=80,
                        command=lambda rd=row_data: self._browse_c3d(rd),
                    ).pack(side="left", padx=4)

                    status_lbl = ctk.CTkLabel(
                        main_row, text="✗", width=28,
                        font=ctk.CTkFont(size=14), text_color="#E05252",
                    )
                    status_lbl.pack(side="left", padx=2)
                    row_data["status_lbl"] = status_lbl

                    # ── Offset correction row (first rep only in Individual) ─
                    show_offset = (not is_individual) or (rep_idx == 0)
                    if show_offset:
                        offset_row = ctk.CTkFrame(row_frame,
                                                  fg_color="transparent")
                        offset_row.pack(fill="x", padx=4, pady=(0, 2))

                        spacer_w = 268 if not is_individual else 272
                        ctk.CTkLabel(offset_row, text="",
                                     width=spacer_w).pack(side="left")

                        if is_bilateral:
                            off_left_var  = ctk.StringVar(value="0.0")
                            off_right_var = ctk.StringVar(value="0.0")
                            row_data["offset_left_var"]  = off_left_var
                            row_data["offset_right_var"] = off_right_var

                            off_left_entry  = ctk.CTkEntry(
                                offset_row, textvariable=off_left_var,
                                width=60, state="disabled")
                            off_right_entry = ctk.CTkEntry(
                                offset_row, textvariable=off_right_var,
                                width=60, state="disabled")

                            def _make_bilateral_toggle(cb_v, el, er):
                                def _toggle():
                                    s = "normal" if cb_v.get() else "disabled"
                                    el.configure(state=s)
                                    er.configure(state=s)
                                return _toggle

                            off_cb = ctk.CTkCheckBox(
                                offset_row, text=t("s2_offset_cb"), width=180,
                                variable=offset_var, state="disabled",
                                command=_make_bilateral_toggle(
                                    offset_var, off_left_entry,
                                    off_right_entry),
                            )
                            off_cb.pack(side="left", padx=(0, 4))
                            ctk.CTkLabel(offset_row, text="L:",
                                         font=ctk.CTkFont(size=10)).pack(
                                             side="left")
                            off_left_entry.pack(side="left", padx=2)
                            ctk.CTkLabel(offset_row, text="R:",
                                         font=ctk.CTkFont(size=10)).pack(
                                             side="left", padx=(6, 0))
                            off_right_entry.pack(side="left", padx=2)
                            row_data["offset_cb"]          = off_cb
                            row_data["offset_left_entry"]  = off_left_entry
                            row_data["offset_right_entry"] = off_right_entry
                        else:
                            off_entry_var = ctk.StringVar(value="0.0")
                            row_data["offset_entry_var"] = off_entry_var
                            off_entry = ctk.CTkEntry(
                                offset_row, textvariable=off_entry_var,
                                width=70, state="disabled")

                            def _make_toggle(cb_v, entry):
                                def _toggle():
                                    entry.configure(
                                        state="normal" if cb_v.get()
                                        else "disabled")
                                return _toggle

                            off_cb = ctk.CTkCheckBox(
                                offset_row, text=t("s2_offset_cb"), width=180,
                                variable=offset_var, state="disabled",
                                command=_make_toggle(offset_var, off_entry),
                            )
                            off_cb.pack(side="left", padx=(0, 4))
                            off_entry.pack(side="left", padx=2)
                            row_data["offset_cb"]    = off_cb
                            row_data["offset_entry"] = off_entry

                        ctk.CTkLabel(
                            offset_row, text=t("s2_offset_hint"),
                            font=ctk.CTkFont(size=9), text_color="gray",
                        ).pack(side="left", padx=(6, 0))

                    # Restore state if available
                    self._restore_row_state(
                        row_data,
                        old_state.get((mv_name, side_label, rep_idx)))

                # In Individual mode, share the offset_var from rep 0 with all
                # reps in this (mv_name, side_label) group so they use the same
                # offset when processing.
                if is_individual and num_reps > 1:
                    group = [r for r in self._import_rows
                             if r["mv_name"] == mv_name
                             and r["side"] == side_label]
                    if group:
                        shared_offset = group[0]["offset_var"]
                        for r in group[1:]:
                            r["offset_var"] = shared_offset
                            if "offset_entry_var" in group[0]:
                                r["offset_entry_var"] = (
                                    group[0]["offset_entry_var"])
                            if "offset_left_var" in group[0]:
                                r["offset_left_var"] = (
                                    group[0]["offset_left_var"])
                            if "offset_right_var" in group[0]:
                                r["offset_right_var"] = (
                                    group[0]["offset_right_var"])

        # Navigation buttons
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(
            nav, text=t("s2_back"), width=200,
            command=self._show_screen_1,
        ).pack(side="left")

        process_cmd = (self._start_individual_processing if is_individual
                       else self._start_segmentation)
        self._process_btn = ctk.CTkButton(
            nav, text=t("s2_process"),
            height=40, width=160,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=process_cmd,
        )
        self._process_btn.pack(side="right")
        self._update_process_btn()

    def _restore_row_state(self, row_data: dict, old: dict | None) -> None:
        """Re-apply a previously loaded file's state to newly built widgets."""
        if old is None or not old.get("loaded"):
            return

        for field in ("loaded", "filename", "angle_data", "angle_data_left",
                      "angle_data_right", "frame_rate", "events"):
            if field in old:
                row_data[field] = old[field]

        # Restore offset values
        row_data["offset_var"].set(old.get("_offset_enabled", False))
        if "_offset_entry" in old and "offset_entry_var" in row_data:
            row_data["offset_entry_var"].set(old["_offset_entry"])
        if "_offset_left" in old and "offset_left_var" in row_data:
            row_data["offset_left_var"].set(old["_offset_left"])
        if "_offset_right" in old and "offset_right_var" in row_data:
            row_data["offset_right_var"].set(old["_offset_right"])

        # Update widgets to reflect loaded state
        fname = old.get("filename", "…")
        row_data["file_lbl"].configure(text=fname, text_color="white")
        row_data["status_lbl"].configure(text="✓", text_color="#4CAF50")
        if "offset_cb" in row_data:
            row_data["offset_cb"].configure(state="normal")
            if old.get("_offset_enabled"):
                for entry_key in ("offset_entry", "offset_left_entry",
                                  "offset_right_entry"):
                    if entry_key in row_data:
                        row_data[entry_key].configure(state="normal")

    def _browse_c3d(self, row_data: dict) -> None:
        path = filedialog.askopenfilename(
            title=f"C3D — {row_data['mv_name']} / {row_data['side']}",
            filetypes=[("C3D files", "*.c3d"), ("All files", "*.*")],
        )
        if not path:
            return

        from data_processing import read_c3d, list_available_angles
        from config import MOVEMENT_DEFINITIONS

        try:
            c3d_data = read_c3d(path)
        except Exception as exc:
            messagebox.showerror(
                t("s2_load_error_title"),
                t("s2_load_error_msg").format(exc=exc),
            )
            return

        mv_def      = MOVEMENT_DEFINITIONS[row_data["mv_name"]]
        has_prefix  = mv_def["has_side_prefix"]
        component   = mv_def["component"]
        sulm_var    = mv_def["sulm_variable"]
        model_outputs = c3d_data["model_outputs"]
        fname = os.path.basename(path)

        if row_data["bilateral"]:
            var_left  = f"Left{sulm_var}"
            var_right = f"Right{sulm_var}"
            missing = [v for v in (var_left, var_right)
                       if v not in model_outputs]
            if missing:
                available = list_available_angles(c3d_data)
                messagebox.showwarning(
                    t("s2_vars_not_found_title"),
                    t("s2_vars_not_found_msg").format(
                        missing="\n  ".join(missing),
                        available="\n  ".join(available),
                    ),
                )
                return
            row_data["angle_data_left"]  = (
                model_outputs[var_left][component, :].astype(float))
            row_data["angle_data_right"] = (
                model_outputs[var_right][component, :].astype(float))
            row_data["angle_data"] = row_data["angle_data_left"]

        else:
            side = row_data["side"]
            full_var = (f"{side}{sulm_var}"
                        if has_prefix and side != _NO_SIDE else sulm_var)
            if full_var not in model_outputs:
                available = list_available_angles(c3d_data)
                messagebox.showwarning(
                    t("s2_var_not_found_title"),
                    t("s2_var_not_found_msg").format(
                        label=full_var,
                        available="\n  ".join(available),
                    ),
                )
                return
            row_data["angle_data"] = (
                model_outputs[full_var][component, :].astype(float))

        row_data["loaded"]     = True
        row_data["filename"]   = fname
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
                    off_l = (float(row_data["offset_left_var"].get())
                             if offset_on else 0.0)
                except (ValueError, KeyError):
                    off_l = 0.0
                try:
                    off_r = (float(row_data["offset_right_var"].get())
                             if offset_on else 0.0)
                except (ValueError, KeyError):
                    off_r = 0.0

                sides_to_seg: list[tuple] = [
                    ("Left",
                     apply_offset(row_data["angle_data_left"], off_l)
                     if offset_on else row_data["angle_data_left"],
                     off_l if offset_on else None),
                    ("Right",
                     apply_offset(row_data["angle_data_right"], off_r)
                     if offset_on else row_data["angle_data_right"],
                     off_r if offset_on else None),
                ]
            else:
                try:
                    off = (float(row_data["offset_entry_var"].get())
                           if offset_on else 0.0)
                except (ValueError, KeyError):
                    off = 0.0
                ang = (apply_offset(row_data["angle_data"], off)
                       if offset_on else row_data["angle_data"])
                sides_to_seg = [(row_data["side"], ang,
                                 off if offset_on else None)]

            for side, angle_arr, offset_val in sides_to_seg:
                title = (f"{mv_name} — {side}"
                         if side != _NO_SIDE else mv_name)

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
                        "extended":   compute_extended_stats_array(
                            angle_arr, segs),
                        **win.result,
                    }
                else:
                    logger.info("Segmentation cancelled for '%s' — %s.",
                                mv_name, side)

        if not self._processed:
            messagebox.showinfo(
                t("s3_no_results_title"),
                t("s3_no_results_msg"),
            )
            return

        self._show_screen_4()

    # ══════════════════════════════════════════════════════════════════════
    #  Individual mode processing
    # ══════════════════════════════════════════════════════════════════════

    def _start_individual_processing(self) -> None:
        from individual_review import IndividualReviewWindow
        from data_processing import apply_offset

        # Group rows by (mv_name, side)
        groups: dict[tuple[str, str], list[dict]] = {}
        for r in self._import_rows:
            key = (r["mv_name"], r["side"])
            groups.setdefault(key, []).append(r)

        for (mv_name, side), reps in groups.items():
            # Sort by rep_idx to keep order stable
            reps = sorted(reps, key=lambda r: r["rep_idx"])

            offset_on = reps[0]["offset_var"].get()

            if reps[0]["bilateral"]:
                # Bilateral Individual: process Left and Right separately
                for actual_side, data_key, off_key in [
                    ("Left",  "angle_data_left",  "offset_left_var"),
                    ("Right", "angle_data_right", "offset_right_var"),
                ]:
                    try:
                        off = (float(reps[0][off_key].get())
                               if offset_on else 0.0)
                    except (ValueError, KeyError):
                        off = 0.0

                    curves = [r[data_key] for r in reps if r[data_key] is not None]
                    if not curves:
                        continue

                    title = f"{mv_name} — {actual_side}"
                    win = IndividualReviewWindow(
                        self, title, curves,
                        offset_val=off if offset_on else None,
                    )
                    self.wait_window(win)

                    if win.result is not None:
                        self._processed[(mv_name, actual_side)] = {
                            "movement":   mv_name,
                            "side":       actual_side,
                            "angle_data": win.result["angle_data"],
                            "frame_rate": reps[0]["frame_rate"],
                            "offset":     win.result["offset"],
                            "extended":   win.result["extended"],
                            "segments":   [],
                        }
            else:
                try:
                    off = (float(reps[0]["offset_entry_var"].get())
                           if offset_on else 0.0)
                except (ValueError, KeyError):
                    off = 0.0

                curves = [r["angle_data"] for r in reps
                          if r["angle_data"] is not None]
                if not curves:
                    continue

                title = (f"{mv_name} — {side}"
                         if side != _NO_SIDE else mv_name)
                win = IndividualReviewWindow(
                    self, title, curves,
                    offset_val=off if offset_on else None,
                )
                self.wait_window(win)

                if win.result is not None:
                    self._processed[(mv_name, side)] = {
                        "movement":   mv_name,
                        "side":       side,
                        "angle_data": win.result["angle_data"],
                        "frame_rate": reps[0]["frame_rate"],
                        "offset":     win.result["offset"],
                        "extended":   win.result["extended"],
                        "segments":   [],
                    }

        if not self._processed:
            messagebox.showinfo(
                t("s3_no_results_title"),
                t("s3_no_results_msg"),
            )
            return

        self._show_screen_4()

    # ══════════════════════════════════════════════════════════════════════
    #  Screen 4 — Summary & Export
    # ══════════════════════════════════════════════════════════════════════

    def _show_screen_4(self) -> None:
        self._current_screen = 4
        self._clear_container()
        self._layout_vertical = True

        f = ctk.CTkFrame(self._container, fg_color="transparent")
        f.pack(fill="both", expand=True)

        # ── Top bar: layout toggle ─────────────────────────────────────────
        top_bar = ctk.CTkFrame(f, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 4))

        self._layout_toggle_btn = ctk.CTkButton(
            top_bar, text=t("s4_layout_horizontal"), width=190,
            command=self._toggle_layout,
        )
        self._layout_toggle_btn.pack(side="right")

        # ── Content area ──────────────────────────────────────────────────
        self._layout_content = ctk.CTkFrame(f, fg_color="transparent")
        self._layout_content.pack(fill="both", expand=True)

        self._layout_card_tbl   = _card(self._layout_content,
                                        t("s4_card_results"))
        self._build_summary_table(self._layout_card_tbl)

        self._layout_card_chart = _card(self._layout_content,
                                        t("s4_card_overview"))
        self._build_rom_chart(self._layout_card_chart)

        self._apply_layout()

        # ── Bottom action bar ──────────────────────────────────────────────
        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))

        ctk.CTkButton(
            btn_row, text=t("s4_export_csv"), width=130,
            command=self._export_csv,
        ).pack(side="left")
        ctk.CTkButton(
            btn_row, text=t("s4_new_analysis"), width=160,
            font=ctk.CTkFont(weight="bold"),
            command=self._new_analysis,
        ).pack(side="right")
        ctk.CTkButton(
            btn_row, text=t("s4_generate_report"), width=160,
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
            card_chart.grid(row=1, column=0, columnspan=2, sticky="nsew")

            self._layout_toggle_btn.configure(text=t("s4_layout_horizontal"))
        else:
            content.grid_rowconfigure(0, weight=1, minsize=0)
            content.grid_rowconfigure(1, weight=0, minsize=0)
            content.grid_columnconfigure(0, weight=1, minsize=0)
            content.grid_columnconfigure(1, weight=1, minsize=0)

            card_tbl.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
            card_chart.grid(row=0, column=1, sticky="nsew")

            self._layout_toggle_btn.configure(text=t("s4_layout_vertical"))

    def _toggle_layout(self) -> None:
        self._layout_vertical = not self._layout_vertical
        self._apply_layout()

    def _build_summary_table(self, parent: ctk.CTkFrame) -> None:
        headers = [
            t("s4_hdr_movement"), t("s4_hdr_side"), t("s4_hdr_metric"),
            t("s4_hdr_n"),        t("s4_hdr_mean"),  t("s4_hdr_sd"),
            t("s4_hdr_min"),      t("s4_hdr_max"),
        ]
        col_w = [180, 55, 65, 36, 70, 60, 60, 60]

        scroll = ctk.CTkScrollableFrame(parent, height=200)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        for c, (h, w) in enumerate(zip(headers, col_w)):
            ctk.CTkLabel(scroll, text=h, width=w,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").grid(row=0, column=c, padx=2, pady=2,
                                          sticky="w")

        row_idx = 1
        offset_notes: list[str] = []

        metric_labels = [
            (t("s4_metric_rom"),    "rom"),
            (t("s4_metric_peak"),   "peak"),
            (t("s4_metric_valley"), "valley"),
        ]

        for group_idx, ((mv_name, side), data) in enumerate(
                self._processed.items()):
            extended   = data.get("extended", {})
            offset_val = data.get("offset")

            if offset_val is not None:
                offset_notes.append(
                    f"{mv_name} ({side}): "
                    + t("s4_offset_subtracted").format(offset=offset_val)
                )

            bg = "#2A2D2E" if group_idx % 2 == 0 else "transparent"

            for sub_idx, (metric_label, metric_key) in enumerate(
                    metric_labels):
                stats  = extended.get(metric_key, {})
                values = stats.get("values", [])
                mean_v = stats.get("mean", float("nan"))
                sd_v   = stats.get("sd",   0.0)
                min_v  = stats.get("min",  float("nan"))
                max_v  = stats.get("max",  float("nan"))

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
                                                   padx=2, pady=1,
                                                   sticky="w")
                row_idx += 1

        if offset_notes:
            note = (t("s4_offset_note_prefix")
                    + "; ".join(offset_notes) + ".")
            ctk.CTkLabel(parent, text=note,
                         font=ctk.CTkFont(size=9), text_color="gray",
                         anchor="w", wraplength=780,
                         ).pack(fill="x", padx=12, pady=(0, 4))

    def _build_rom_chart(self, parent: ctk.CTkFrame) -> None:
        from plotting import plot_rom_summary

        chart_data: dict[str, dict] = {}
        for (mv_name, side), data in self._processed.items():
            key = f"{mv_name}\n({side})" if side != _NO_SIDE else mv_name
            chart_data[key] = data

        try:
            fig = plot_rom_summary(chart_data, normative={})
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True,
                                        padx=12, pady=(0, 8))
        except Exception as exc:
            ctk.CTkLabel(
                parent,
                text=t("s4_chart_unavailable").format(exc=exc),
                text_color="gray",
            ).pack(padx=12, pady=4)

    # ── Export ─────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        if not self._processed:
            return

        out_path = filedialog.asksaveasfilename(
            title=t("s4_csv_dialog_title"),
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
                ("rom",    t("s4_metric_rom")),
                ("peak",   t("s4_metric_peak")),
                ("valley", t("s4_metric_valley")),
            ):
                stats  = extended.get(metric_key, {})
                values = stats.get("values", [])
                m  = stats.get("mean", float("nan"))
                s  = stats.get("sd",   0.0)
                mn = stats.get("min",  float("nan"))
                mx = stats.get("max",  float("nan"))

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
                        f"{v:.2f}" if not math.isnan(v) else "nan"
                        for v in values
                    ),
                    "Offset_deg": (f"{offset_val:.2f}"
                                   if offset_val is not None else ""),
                })

        pd.DataFrame(rows).to_csv(out_path, index=False)

        msg = t("s4_csv_saved_msg").format(path=out_path)
        offset_entries = [
            (mv, sd, d["offset"])
            for (mv, sd), d in self._processed.items()
            if d.get("offset") is not None
        ]
        if offset_entries:
            notes = [
                t("s4_csv_offset_entry").format(mv=mv, sd=sd, off=off)
                for mv, sd, off in offset_entries
            ]
            msg += t("s4_csv_offset_applied").format(
                notes="\n".join(notes))
        messagebox.showinfo(t("s4_csv_saved_title"), msg)

    def _generate_report(self) -> None:
        messagebox.showinfo(t("s4_report_coming_title"),
                            t("s4_report_coming_msg"))

    def _new_analysis(self) -> None:
        self._import_rows.clear()
        self._processed.clear()
        self._process_btn = None
        self._laterality_var.set("bilateral")
        self._recording_type_var.set("continuous")
        self._num_reps_var.set(6)
        self._show_screen_1()
