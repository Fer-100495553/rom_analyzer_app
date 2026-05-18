from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def extract_diff_vector(c3d_path: str, label: str) -> tuple[np.ndarray, float]:
    """
    Extracts a 3D difference vector from a C3D file.

    Points shape: (4, n_labels, n_frames) — rows 0=X, 1=Y, 2=Z, 3=residual.
    Subject prefix (e.g. 'Subject01:Diff_T8F_T8V') is stripped before matching.
    Frames where all three components are zero or residual < 0 are set to NaN.

    Returns:
        diff: np.ndarray shape (3, n_frames), dx dy dz in mm, invalid frames as NaN
        frame_rate: float
    """
    import ezc3d

    c3d = ezc3d.c3d(c3d_path)
    points = c3d["data"]["points"]  # (4, n_labels, n_frames)
    raw_labels = c3d["parameters"]["POINT"]["LABELS"]["value"]

    # Strip subject prefix (everything up to and including the last ':')
    clean_labels = [
        lbl.split(":")[-1] if ":" in lbl else lbl for lbl in raw_labels
    ]

    if label not in clean_labels:
        raise ValueError(
            f"Label '{label}' not found in C3D file '{c3d_path}'. "
            f"Available labels (stripped): {clean_labels}"
        )

    idx = clean_labels.index(label)
    try:
        rate_val   = c3d["parameters"]["POINT"]["RATE"]["value"]
        frame_rate = float(rate_val[0] if hasattr(rate_val, "__len__") else rate_val)
    except (KeyError, IndexError, TypeError, ValueError):
        frame_rate = float(c3d["header"]["frame_rate"])

    x = points[0, idx, :].astype(float)
    y = points[1, idx, :].astype(float)
    z = points[2, idx, :].astype(float)
    residual = points[3, idx, :]

    diff = np.stack([x, y, z], axis=0)  # (3, n_frames)

    all_zero = (x == 0) & (y == 0) & (z == 0)
    invalid = all_zero | (residual < 0)
    diff[:, invalid] = np.nan

    return diff, frame_rate


def compute_euclidean_distance(diff: np.ndarray) -> np.ndarray:
    """
    Frame-by-frame Euclidean distance from a (3, n_frames) array.
    NaN frames propagate: any NaN component → NaN distance.
    Returns np.ndarray shape (n_frames,) in mm.
    """
    return np.sqrt(np.sum(diff ** 2, axis=0))


def compute_validation_metrics(distance: np.ndarray) -> dict:
    """
    Returns dict with keys:
        mean_mm, sd_mm, rmse_mm, max_mm, p95_mm, n_frames, n_valid
    """
    n_frames = len(distance)
    n_valid = int(np.sum(~np.isnan(distance)))
    return {
        "mean_mm": float(np.nanmean(distance)),
        "sd_mm":   float(np.nanstd(distance)),
        "rmse_mm": float(np.sqrt(np.nanmean(distance ** 2))),
        "max_mm":  float(np.nanmax(distance)),
        "p95_mm":  float(np.nanpercentile(distance, 95)),
        "n_frames": n_frames,
        "n_valid":  n_valid,
    }


def compute_per_axis_mae(diff: np.ndarray) -> dict:
    """Returns dict with keys: mae_x_mm, mae_y_mm, mae_z_mm."""
    return {
        "mae_x_mm": float(np.nanmean(np.abs(diff[0]))),
        "mae_y_mm": float(np.nanmean(np.abs(diff[1]))),
        "mae_z_mm": float(np.nanmean(np.abs(diff[2]))),
    }
