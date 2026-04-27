from __future__ import annotations

import numpy as np
import pandas as pd


def load_file(path: str) -> pd.DataFrame | None:
    """
    Load a CSV or XLSX file and return a normalized DataFrame.

    TODO: adapt _normalize_columns() once the exact Vicon Nexus export
          column names are known. Currently renames the first two columns
          to generic 'Frame' and 'Angle' placeholders.
    """
    try:
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        elif path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        else:
            print(f"[load_file] Unsupported file type: {path}")
            return None
    except Exception as exc:
        print(f"[load_file] Failed to read {path}: {exc}")
        return None

    return _normalize_columns(df)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder column normalizer.

    Renames the first column to 'Frame' and the second to 'Angle'.
    If only one column exists, inserts a sequential Frame index.

    TODO: replace with actual Vicon Nexus column mapping once the
          export format is confirmed.
    """
    df = df.copy()
    cols = list(df.columns)

    if len(cols) == 0:
        return df

    if len(cols) == 1:
        df.insert(0, "Frame", range(len(df)))
        df.columns = ["Frame", cols[0]]
        return df

    cols[0] = "Frame"
    cols[1] = "Angle"
    df.columns = cols
    return df


def extract_segment(df: pd.DataFrame, start: float, end: float) -> pd.DataFrame:
    """Return all rows where the Frame value falls within [start, end]."""
    return df[(df["Frame"] >= start) & (df["Frame"] <= end)].copy()


def compute_rom(segment: pd.DataFrame) -> float:
    """ROM = max − min of the Angle column within one segment."""
    if segment.empty or "Angle" not in segment.columns:
        return float("nan")
    return float(segment["Angle"].max() - segment["Angle"].min())


def compute_rom_stats(
    df: pd.DataFrame,
    segments: list[tuple[float, float]],
) -> dict:
    """
    Compute per-repetition ROM and aggregate statistics for one movement.

    Parameters
    ----------
    df       : normalized DataFrame with at least 'Frame' and 'Angle' columns
    segments : list of (start_frame, end_frame) pairs from segmentation

    Returns
    -------
    dict with keys
        roms     – ROM value for each repetition (float, may be NaN)
        mean     – mean ROM across valid repetitions
        sd       – sample standard deviation (ddof=1); 0.0 if only one rep
        segments – the original (start, end) pairs passed in
    """
    roms = [compute_rom(extract_segment(df, s, e)) for s, e in segments]
    valid = [r for r in roms if not np.isnan(r)]

    return {
        "roms": roms,
        "mean": float(np.mean(valid)) if valid else float("nan"),
        "sd": float(np.std(valid, ddof=1)) if len(valid) > 1 else 0.0,
        "segments": segments,
    }
