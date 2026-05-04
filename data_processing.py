from __future__ import annotations

import logging
import os
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── CSV / Excel (legacy) ──────────────────────────────────────────────────

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
            logger.warning("Unsupported file type: %s", path)
            return None
    except Exception as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return None
    return _normalize_columns(df)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder column normalizer.

    Renames the first column to 'Frame' and the second to 'Angle'.
    If only one column exists, inserts a sequential Frame index.
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

    Args:
        df:       Normalized DataFrame with at least 'Frame' and 'Angle' columns.
        segments: List of (start_frame, end_frame) pairs from segmentation.

    Returns:
        Dict with keys: roms, mean, sd, segments.
    """
    roms = [compute_rom(extract_segment(df, s, e)) for s, e in segments]
    valid = [r for r in roms if not np.isnan(r)]
    return {
        "roms": roms,
        "mean": float(np.mean(valid)) if valid else float("nan"),
        "sd": float(np.std(valid, ddof=1)) if len(valid) > 1 else 0.0,
        "segments": segments,
    }


def compute_rom_stats_array(
    angle_data: np.ndarray,
    segments: list[tuple[int, int]],
) -> dict:
    """
    Compute per-repetition ROM and statistics from a 1D numpy angle array.

    Args:
        angle_data: 1D numpy array of angle values in degrees.
        segments:   List of (start_frame, end_frame) integer pairs.

    Returns:
        Dict with keys: roms, mean, sd, segments, outlier_flags.
    """
    from config import OUTLIER_SD_THRESHOLD

    roms: list[float] = []
    for s, e in segments:
        chunk = angle_data[s:e + 1]
        valid_chunk = chunk[~np.isnan(chunk)]
        if valid_chunk.size == 0:
            roms.append(float("nan"))
        else:
            roms.append(float(np.nanmax(chunk) - np.nanmin(chunk)))

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


def apply_offset(angle_curve: np.ndarray, offset_value: float) -> np.ndarray:
    """Subtract offset_value from the entire angle curve (neutral position calibration)."""
    return angle_curve - float(offset_value)


def compute_extended_stats_array(
    angle_data: np.ndarray,
    segments: list[tuple[int, int]],
) -> dict:
    """
    Compute per-repetition ROM, peak angle, and valley angle statistics.

    Args:
        angle_data: 1D numpy array of angle values in degrees.
        segments:   List of (start_frame, end_frame) integer pairs.

    Returns:
        Dict with keys ``rom``, ``peak``, ``valley``.  Each value is a dict
        with ``values``, ``mean``, ``sd``, ``min``, ``max``.
    """
    roms: list[float] = []
    peaks: list[float] = []
    valleys: list[float] = []

    for s, e in segments:
        chunk = angle_data[s : e + 1]
        valid_chunk = chunk[~np.isnan(chunk)]
        if valid_chunk.size == 0:
            roms.append(float("nan"))
            peaks.append(float("nan"))
            valleys.append(float("nan"))
        else:
            roms.append(float(np.nanmax(chunk) - np.nanmin(chunk)))
            peaks.append(float(np.nanmax(chunk)))
            valleys.append(float(np.nanmin(chunk)))

    def _agg(values: list[float]) -> dict:
        valid = np.array([v for v in values if not np.isnan(v)])
        return {
            "values": values,
            "mean": float(np.mean(valid))         if valid.size > 0 else float("nan"),
            "sd":   float(np.std(valid, ddof=1))  if valid.size > 1 else 0.0,
            "min":  float(np.min(valid))           if valid.size > 0 else float("nan"),
            "max":  float(np.max(valid))           if valid.size > 0 else float("nan"),
        }

    return {
        "rom":    _agg(roms),
        "peak":   _agg(peaks),
        "valley": _agg(valleys),
    }


# ── C3D reading ───────────────────────────────────────────────────────────

def read_c3d(filepath: str) -> dict:
    """
    Read a Vicon Nexus C3D file exported from the Southampton Upper Limb Model.

    Label prefixes before a colon (e.g. ``"Fernando_grab3:LThoraxAngles"``)
    are stripped automatically so downstream code works with plain names.

    Args:
        filepath: Absolute or relative path to the .c3d file.

    Returns:
        Dict with keys:
            frame_rate    (int)
            n_frames      (int)
            point_labels  (list[str])  – cleaned label names
            model_outputs (dict[str, np.ndarray])  – label → (3, n_frames)
            events        (list[dict]) – from _extract_events()
    """
    try:
        import ezc3d  # noqa: F401 — checked here so the error is readable
    except ImportError as exc:
        raise ImportError(
            "ezc3d is required for C3D reading. "
            "Install with: pip install ezc3d"
        ) from exc

    import ezc3d as _ezc3d
    filepath = os.path.normpath(os.path.abspath(filepath))
    print(f"DEBUG read_c3d: {repr(filepath)}")
    c = _ezc3d.c3d(filepath)

    # ── labels ────────────────────────────────────────────────────────────
    raw_labels: list[str] = c["parameters"]["POINT"]["LABELS"]["value"]
    point_data: np.ndarray = c["data"]["points"]  # (4, n_labels, n_frames)

    n_labels = min(len(raw_labels), point_data.shape[1])
    n_frames = point_data.shape[2]

    # Try POINT RATE first, fall back to header frame_rate
    try:
        rate_val = c["parameters"]["POINT"]["RATE"]["value"]
        frame_rate = int(float(rate_val[0]) if hasattr(rate_val, "__len__") else float(rate_val))
    except (KeyError, IndexError, TypeError, ValueError):
        frame_rate = int(c["header"]["frame_rate"])

    clean_labels: list[str] = [
        lbl.split(":")[-1].strip() if ":" in lbl else lbl.strip()
        for lbl in raw_labels[:n_labels]
    ]

    model_outputs: dict[str, np.ndarray] = {}
    for i, lbl in enumerate(clean_labels):
        # Rows 0-2: X, Y, Z.  Row 3: residual — discarded.
        model_outputs[lbl] = point_data[:3, i, :].copy()

    events = _extract_events(c, frame_rate)

    logger.info(
        "C3D loaded: %d labels, %d frames @ %d Hz, %d events — %s",
        len(clean_labels), n_frames, frame_rate, len(events), filepath,
    )

    return {
        "frame_rate": frame_rate,
        "n_frames": n_frames,
        "point_labels": clean_labels,
        "model_outputs": model_outputs,
        "events": events,
    }


def _extract_events(c: object, frame_rate: int) -> list[dict]:
    """
    Parse Nexus event markers from an ezc3d object.

    Returns:
        List of dicts: {"name": str, "frame": int, "time": float}.
    """
    events: list[dict] = []
    try:
        params = c["parameters"]
        if "EVENT" not in params:
            return events

        ev = params["EVENT"]
        raw_times = ev.get("TIMES", {}).get("value", [])
        labels: list[str] = ev.get("LABELS", {}).get("value", [])

        # TIMES is a 2-row array: row 0 = context index, row 1 = time (s)
        if hasattr(raw_times, "ndim"):
            times_arr: np.ndarray = np.asarray(raw_times, dtype=float)
            if times_arr.ndim == 2 and times_arr.shape[0] >= 2:
                time_values = times_arr[1, :]
            else:
                time_values = times_arr.ravel()
        elif raw_times and isinstance(raw_times[0], (list, tuple)):
            time_values = [float(t) for t in raw_times[1]]
        else:
            time_values = [float(t) for t in raw_times]

        for i, t in enumerate(time_values):
            frame = int(round(float(t) * frame_rate))
            name = labels[i] if i < len(labels) else f"Event_{i}"
            events.append({"name": name.strip(), "frame": frame, "time": float(t)})

    except Exception as exc:
        logger.warning("Could not parse C3D events: %s", exc)

    return events


def extract_angle_curve(
    c3d_data: dict,
    variable_name: str,
    component_index: int,
) -> np.ndarray:
    """
    Extract a 1D angle curve from C3D model output data.

    Tries the variable name as-is, then with ``L`` and ``R`` prefixes.

    Args:
        c3d_data:        Output of :func:`read_c3d`.
        variable_name:   SULM variable name without side prefix.
        component_index: Euler component: 0 = X, 1 = Y, 2 = Z.

    Returns:
        1D float numpy array of length n_frames.

    Raises:
        KeyError: If the variable is not found under any prefix.
    """
    model_outputs = c3d_data["model_outputs"]

    for prefix in ("", "L", "R", "l", "r"):
        key = prefix + variable_name
        if key in model_outputs:
            if prefix:
                logger.debug("Variable '%s' found as '%s'", variable_name, key)
            return model_outputs[key][component_index, :].astype(float)

    raise KeyError(
        f"Variable '{variable_name}' not found in C3D data.\n"
        f"Available labels: {list(model_outputs.keys())}"
    )


def extract_angle_curve_sided(
    c3d_data: dict,
    variable_name: str,
    component_index: int,
    side: str,
) -> np.ndarray:
    """
    Extract an angle curve for a specific body side.

    Args:
        side: ``"L"``, ``"R"``, or ``"Both"`` (returns L when both exist).

    Returns:
        1D float numpy array of length n_frames.
    """
    model_outputs = c3d_data["model_outputs"]

    if side in ("L", "R"):
        key = side + variable_name
        if key in model_outputs:
            return model_outputs[key][component_index, :].astype(float)
        # Soft fallback — variable may not be prefixed in this file
        logger.warning(
            "Side '%s' not found for '%s'; trying without prefix.", side, variable_name
        )

    return extract_angle_curve(c3d_data, variable_name, component_index)


def list_available_angles(c3d_data: dict) -> list[str]:
    """
    Return only SULM model output labels, filtering out raw marker trajectories.

    Uses keyword matching against :data:`config.ANGLE_KEYWORDS`.

    Args:
        c3d_data: Output of :func:`read_c3d`.

    Returns:
        Filtered list of label strings.
    """
    from config import ANGLE_KEYWORDS
    return [
        lbl for lbl in c3d_data["point_labels"]
        if any(kw in lbl for kw in ANGLE_KEYWORDS)
    ]


def detect_events(c3d_data: dict) -> list[dict]:
    """
    Return the Nexus event markers stored in the C3D file.

    Args:
        c3d_data: Output of :func:`read_c3d`.

    Returns:
        List of dicts: ``{"name": str, "frame": int, "time": float}``.
    """
    return c3d_data.get("events", [])


def compute_individual_stats(angle_curves: list[np.ndarray]) -> dict:
    """
    Compute ROM, peak, and valley statistics for Individual recording mode.

    Each element in *angle_curves* is the full angle array for one repetition
    (a single C3D file).  ROM = max − min of the whole curve.

    Args:
        angle_curves: List of 1-D numpy arrays, one per repetition.

    Returns:
        Same structure as :func:`compute_extended_stats_array`:
        ``{"rom": {...}, "peak": {...}, "valley": {...}}``.
        Also adds ``"curves"`` key with the original arrays for plotting.
    """
    roms: list[float] = []
    peaks: list[float] = []
    valleys: list[float] = []

    for curve in angle_curves:
        valid = curve[~np.isnan(curve)]
        if valid.size == 0:
            roms.append(float("nan"))
            peaks.append(float("nan"))
            valleys.append(float("nan"))
        else:
            peaks.append(float(np.nanmax(curve)))
            valleys.append(float(np.nanmin(curve)))
            roms.append(peaks[-1] - valleys[-1])

    def _agg(values: list[float]) -> dict:
        valid = np.array([v for v in values if not np.isnan(v)])
        return {
            "values": values,
            "mean": float(np.mean(valid))        if valid.size > 0 else float("nan"),
            "sd":   float(np.std(valid, ddof=1)) if valid.size > 1 else 0.0,
            "min":  float(np.min(valid))          if valid.size > 0 else float("nan"),
            "max":  float(np.max(valid))          if valid.size > 0 else float("nan"),
        }

    return {
        "rom":    _agg(roms),
        "peak":   _agg(peaks),
        "valley": _agg(valleys),
        "curves": angle_curves,
    }


def get_side_prefix(side: str) -> str:
    """
    Return the full-word side prefix used in SULM C3D label names.

    SULM labels use full words, not single letters:
    ``"Left"`` / ``"Right"`` (not ``"L"`` / ``"R"``).

    Args:
        side: ``"left"`` or ``"right"`` (case-insensitive).
              Any other value returns an empty string (no prefix).

    Returns:
        ``"Left"``, ``"Right"``, or ``""`` for no-prefix variables.

    Examples:
        >>> get_side_prefix("left")
        'Left'
        >>> get_side_prefix("Right")
        'Right'
        >>> get_side_prefix("—")
        ''
    """
    from config import SIDE_PREFIXES
    return SIDE_PREFIXES.get(side.lower(), "")
