from __future__ import annotations

import math
import os
import tempfile
from datetime import date

from fpdf import FPDF

from plotting import plot_kinematic_curve, plot_rom_bars, save_figure

# Page geometry (A4 portrait, 15 mm margins → 180 mm usable width)
_PAGE_W = 180

# Column widths for the summary table (sum = 180 mm)
_COL_W = [68, 18, 24, 24, 23, 23]
_COL_HEADERS = ["Movement", "Reps", "Mean (°)", "SD (°)", "Min (°)", "Max (°)"]


class _ROMReport(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 9, "Range of Motion Analysis — Vicon Nexus",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"Report generated: {date.today().isoformat()}",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def generate_pdf(
    results: dict,
    out_path: str,
    loaded_files: dict | None = None,
) -> None:
    """
    Build and save the ROM analysis PDF.

    Parameters
    ----------
    results      : {movement: {"roms": [...], "mean": float, "sd": float,
                               "segments": [...]}}
    out_path     : destination path for the PDF
    loaded_files : optional {movement: DataFrame} — if supplied, a page
                   with kinematic curves is appended to the report
    """
    pdf = _ROMReport(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _write_summary_table(pdf, results)

    with tempfile.TemporaryDirectory() as tmpdir:
        # ROM bar chart
        bar_path = os.path.join(tmpdir, "rom_bars.png")
        save_figure(plot_rom_bars(results), bar_path)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "ROM Overview", new_x="LMARGIN", new_y="NEXT")
        pdf.image(bar_path, x=15, w=_PAGE_W)
        pdf.ln(4)

        # Kinematic curves — one per movement
        if loaded_files:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, "Kinematic Curves", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            for movement, df in loaded_files.items():
                if movement not in results:
                    continue
                segs = results[movement].get("segments", [])
                curve_path = os.path.join(
                    tmpdir, f"curve_{_safe_name(movement)}.png")
                save_figure(plot_kinematic_curve(df, movement, segs), curve_path)

                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, movement, new_x="LMARGIN", new_y="NEXT")
                pdf.image(curve_path, x=15, w=_PAGE_W)
                pdf.ln(5)

        pdf.output(out_path)


# ── internal helpers ───────────────────────────────────────────────────────

def _write_summary_table(pdf: FPDF, results: dict) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "ROM Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Header row
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(52, 120, 184)
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(_COL_W, _COL_HEADERS):
        pdf.cell(w, 8, h, border=1, fill=True)
    pdf.ln()

    # Data rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    for i, (movement, stats) in enumerate(results.items()):
        fill = i % 2 == 0
        pdf.set_fill_color(237, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)

        valid = [r for r in stats["roms"] if not math.isnan(r)]
        row = [
            movement,
            str(len(stats["roms"])),
            f"{stats['mean']:.1f}" if not math.isnan(stats["mean"]) else "—",
            f"{stats['sd']:.1f}",
            f"{min(valid):.1f}" if valid else "—",
            f"{max(valid):.1f}" if valid else "—",
        ]
        for w, v in zip(_COL_W, row):
            pdf.cell(w, 7, v, border=1, fill=fill)
        pdf.ln()

    pdf.ln(8)


def _safe_name(s: str) -> str:
    """Strip non-alphanumeric characters for use in a filename."""
    return "".join(c if c.isalnum() else "_" for c in s)
