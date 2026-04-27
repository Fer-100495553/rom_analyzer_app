from __future__ import annotations

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

MOVEMENTS: list[str] = [
    "Shoulder Flexion-Extension",
    "Shoulder Abduction-Adduction",
    "Shoulder Rotation",
    "Elbow Flexion-Extension",
    "Trunk Inclination",
]


class _Spinbox(ctk.CTkFrame):
    """Integer spinbox: CTkEntry with − / + buttons."""

    def __init__(self, parent, min_val: int = 1, max_val: int = 99, initial: int = 6, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._min = min_val
        self._max = max_val

        ctk.CTkButton(self, text="−", width=28, command=self._decrement).pack(side="left")
        self._entry = ctk.CTkEntry(self, width=52, justify="center")
        self._entry.insert(0, str(initial))
        self._entry.pack(side="left", padx=4)
        ctk.CTkButton(self, text="+", width=28, command=self._increment).pack(side="left")

    def get(self) -> int:
        try:
            return int(self._entry.get())
        except ValueError:
            return self._min

    def _increment(self) -> None:
        v = min(self.get() + 1, self._max)
        self._entry.delete(0, "end")
        self._entry.insert(0, str(v))

    def _decrement(self) -> None:
        v = max(self.get() - 1, self._min)
        self._entry.delete(0, "end")
        self._entry.insert(0, str(v))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ROM Analyzer — Vicon Nexus")
        self.geometry("620x740")
        self.resizable(False, False)

        # State
        self.movement_vars: dict[str, ctk.BooleanVar] = {}
        self.loaded_files: dict[str, object] = {}   # movement → DataFrame
        self.segments: dict[str, list] = {}          # movement → [(start, end), …]
        self._file_labels: dict[str, ctk.CTkLabel] = {}

        self._build_ui()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="ROM Analyzer",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(22, 2))
        ctk.CTkLabel(
            self, text="Vicon Nexus  ·  Range of Motion Analysis",
            text_color="gray",
        ).pack(pady=(0, 16))

        self._section_movements()
        self._section_config()
        self._section_data()
        self._section_actions()

    def _section_movements(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            frame, text="MOVEMENTS",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="gray",
        ).pack(anchor="w", padx=12, pady=(10, 4))

        for movement in MOVEMENTS:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            var = ctk.BooleanVar(value=False)
            self.movement_vars[movement] = var
            ctk.CTkCheckBox(row, text=movement, variable=var, width=270).pack(side="left")

            lbl = ctk.CTkLabel(
                row, text="", text_color="#888888",
                font=ctk.CTkFont(size=11),
            )
            lbl.pack(side="left", padx=8)
            self._file_labels[movement] = lbl

        ctk.CTkFrame(frame, height=8, fg_color="transparent").pack()

    def _section_config(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            frame, text="CONFIGURATION",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="gray",
        ).pack(anchor="w", padx=12, pady=(10, 6))

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(anchor="w", padx=12, pady=(0, 10))
        ctk.CTkLabel(inner, text="Repetitions:").pack(side="left", padx=(0, 8))
        self.spinbox = _Spinbox(inner, initial=6)
        self.spinbox.pack(side="left")

    def _section_data(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            frame, text="DATA",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="gray",
        ).pack(anchor="w", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            frame,
            text="For each selected movement, choose its CSV/XLSX file and\n"
                 "then mark repetition boundaries in the segmentation window.",
            text_color="gray", justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        ctk.CTkButton(
            frame, text="Import & Segment Files",
            command=self._import_and_segment,
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _section_actions(self) -> None:
        ctk.CTkButton(
            self, text="Generate Report",
            height=44, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._generate_report,
        ).pack(fill="x", padx=20, pady=(16, 20))

    # ── callbacks ──────────────────────────────────────────────────────────

    def _import_and_segment(self) -> None:
        selected = [m for m, v in self.movement_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("No selection",
                                   "Select at least one movement before importing.")
            return

        n_reps = self._get_n_reps()
        if n_reps is None:
            return

        from data_processing import load_file
        from segmentation import SegmentationWindow

        for movement in selected:
            path = filedialog.askopenfilename(
                title=f"File for: {movement}",
                filetypes=[
                    ("CSV / Excel", "*.csv *.xlsx *.xls"),
                    ("All files", "*.*"),
                ],
            )
            if not path:
                continue

            df = load_file(path)
            if df is None:
                messagebox.showerror("Load error",
                                     f"Could not read the file for:\n{movement}")
                continue

            self.loaded_files[movement] = df
            fname = os.path.basename(path)
            self._file_labels[movement].configure(
                text=f"✓ {fname}", text_color="#4CAF50")

            win = SegmentationWindow(self, movement, df, n_reps)
            self.wait_window(win)

            if win.segments:
                self.segments[movement] = win.segments
                n = len(win.segments)
                self._file_labels[movement].configure(
                    text=f"✓ {fname}  [{n} rep{'s' if n != 1 else ''}]",
                    text_color="#4CAF50",
                )
            else:
                self._file_labels[movement].configure(
                    text=f"⚠ {fname}  [no segments]",
                    text_color="#FFA500",
                )

    def _generate_report(self) -> None:
        if not self.segments:
            messagebox.showwarning(
                "No data",
                "Import files and complete segmentation before generating the report.",
            )
            return

        from data_processing import compute_rom_stats
        from report_generator import generate_pdf

        results: dict = {}
        for movement, segs in self.segments.items():
            df = self.loaded_files.get(movement)
            if df is not None:
                results[movement] = compute_rom_stats(df, segs)

        if not results:
            messagebox.showwarning("No results", "No ROM data available to report.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Save Report",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="ROM_Report.pdf",
        )
        if not out_path:
            return

        try:
            generate_pdf(results, out_path, loaded_files=self.loaded_files)
            messagebox.showinfo("Done", f"Report saved:\n{out_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not generate report:\n{exc}")

    # ── helpers ────────────────────────────────────────────────────────────

    def _get_n_reps(self) -> int | None:
        n = self.spinbox.get()
        if n < 1:
            messagebox.showerror("Invalid value",
                                 "Number of repetitions must be ≥ 1.")
            return None
        return n
