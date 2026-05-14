"""
Tests for Trunk_Extended / Trunk Lateral Inclination pipeline.
"""
from __future__ import annotations

import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_processing import compute_trunk_extended_angles, list_available_angles


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_c3d_data(labels: list[str], n_frames: int = 200) -> dict:
    model_outputs = {
        lbl: np.zeros((3, n_frames), dtype=float)
        for lbl in labels
    }
    return {
        "frame_rate": 100,
        "n_frames":   n_frames,
        "point_labels": labels,
        "model_outputs": model_outputs,
        "events": [],
    }


def _build_trunk_c3d(
    lateral_deg: float = 0.0,
    n_frames: int = 100,
) -> dict:
    """
    Build a synthetic c3d_data dict where the trunk is tilted
    *lateral_deg* degrees to the right throughout the whole trial.

    Marker layout (all in mm, Y-up world frame):
      IJ          = sternal notch, placed above midLumbar along Z.
      LeftLumbar  = midLumbar shifted +X (left).
      RightLumbar = midLumbar shifted -X (right).

    Then the whole trunk frame is rotated by *lateral_deg* about its local
    Z-axis (lateral tilt), so after reference-frame subtraction the recovered
    lateral inclination should equal *lateral_deg*.
    """
    from scipy.spatial.transform import Rotation

    # Neutral trunk frame (all in mm)
    mid_lumbar = np.array([0.0, 0.0, 1000.0])
    ij_neutral = np.array([0.0, 0.0, 1500.0])   # 500 mm above midLumbar
    ll_neutral = np.array([100.0, 0.0, 1000.0])  # 100 mm to left (right = +X)
    rl_neutral = np.array([-100.0, 0.0, 1000.0])

    # Reference frame (frame 0) — neutral
    IJ_ref  = ij_neutral.copy()
    LL_ref  = ll_neutral.copy()
    RL_ref  = rl_neutral.copy()

    # Rotated frame (all subsequent frames) — tilted *lateral_deg* right
    # In ISB convention the lateral inclination is about the X-axis of the
    # trunk local frame.  We tilt IJ outward (positive right = -Y global tilt)
    R_tilt = Rotation.from_euler(
        "x", lateral_deg, degrees=True
    ).as_matrix()

    def _rotate_about_mid(pt: np.ndarray) -> np.ndarray:
        return mid_lumbar + R_tilt @ (pt - mid_lumbar)

    IJ_tilt  = _rotate_about_mid(ij_neutral)
    LL_tilt  = _rotate_about_mid(ll_neutral)
    RL_tilt  = _rotate_about_mid(rl_neutral)

    n = n_frames
    IJ_arr  = np.zeros((3, n))
    LL_arr  = np.zeros((3, n))
    RL_arr  = np.zeros((3, n))

    # Frame 0 = reference (neutral), frames 1..n-1 = tilted
    IJ_arr[:, 0]  = IJ_ref
    LL_arr[:, 0]  = LL_ref
    RL_arr[:, 0]  = RL_ref
    IJ_arr[:, 1:] = IJ_tilt[:, np.newaxis]
    LL_arr[:, 1:] = LL_tilt[:, np.newaxis]
    RL_arr[:, 1:] = RL_tilt[:, np.newaxis]

    model_outputs = {
        "IJ":          IJ_arr,
        "LeftLumbar":  LL_arr,
        "RightLumbar": RL_arr,
    }
    return {
        "frame_rate":   100,
        "n_frames":     n,
        "point_labels": ["IJ", "LeftLumbar", "RightLumbar"],
        "model_outputs": model_outputs,
        "events": [],
    }


# ── test_compute_trunk_extended_synthetic ─────────────────────────────────

def test_compute_trunk_extended_synthetic() -> None:
    """
    For a known lateral inclination of 10°, the mean recovered angle must
    be within 1° of 10°.
    """
    TARGET_DEG = 10.0
    c3d_data = _build_trunk_c3d(lateral_deg=TARGET_DEG, n_frames=120)

    result = compute_trunk_extended_angles(c3d_data, reference_frame_idx=0)

    lat = result["lateral_inclination"]
    valid = ~np.isnan(lat)
    assert valid.sum() >= 10, "Too few valid frames"

    mean_lat = float(np.nanmean(np.abs(lat[valid])))
    assert abs(mean_lat - TARGET_DEG) < 1.0, (
        f"Expected ~{TARGET_DEG}° lateral inclination, got {mean_lat:.2f}°"
    )


def test_compute_trunk_extended_returns_all_keys() -> None:
    c3d_data = _build_trunk_c3d(n_frames=50)
    result = compute_trunk_extended_angles(c3d_data)
    for key in ("flexion_extension", "lateral_inclination",
                "axial_rotation", "valid_frames"):
        assert key in result, f"Missing key: {key}"
    n = c3d_data["n_frames"]
    for k in ("flexion_extension", "lateral_inclination", "axial_rotation"):
        assert len(result[k]) == n
    assert len(result["valid_frames"]) == n


def test_compute_trunk_extended_missing_marker_raises() -> None:
    c3d_data = _make_c3d_data(["IJ", "LeftLumbar"])  # RightLumbar missing
    with pytest.raises(KeyError, match="RightLumbar"):
        compute_trunk_extended_angles(c3d_data)


def test_compute_trunk_extended_too_few_valid_raises() -> None:
    """All-zero markers → all frames invalid → ValueError."""
    c3d_data = _make_c3d_data(["IJ", "LeftLumbar", "RightLumbar"], n_frames=5)
    # 5 frames, all zero → fewer than 10 valid frames
    with pytest.raises(ValueError, match="valid frame"):
        compute_trunk_extended_angles(c3d_data)


# ── test_list_available_angles_includes_trunk ─────────────────────────────

def test_list_available_angles_includes_trunk() -> None:
    """
    When IJ, LeftLumbar, RightLumbar are present, list_available_angles
    must include 'Trunk Lateral Inclination'.
    """
    c3d_data = _build_trunk_c3d(n_frames=100)
    result = list_available_angles(c3d_data)
    assert "Trunk Lateral Inclination" in result


def test_list_available_angles_excludes_trunk_when_markers_absent() -> None:
    """Without trunk markers, 'Trunk Lateral Inclination' must not appear."""
    c3d_data = _make_c3d_data(["LThoraxAngles", "LACR"])
    result = list_available_angles(c3d_data)
    assert "Trunk Lateral Inclination" not in result
