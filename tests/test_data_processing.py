"""
Tests for data_processing.py — C3D reading and angle extraction.
"""
from __future__ import annotations

import sys
import os

import numpy as np
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_processing import (
    list_available_angles,
    extract_angle_curve,
    extract_angle_curve_sided,
    compute_rom_stats_array,
    detect_events,
    compute_thorax_trunk_pair,
    _unfold_norm_signal,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_c3d_data(labels: list[str], n_frames: int = 200) -> dict:
    """Build a minimal c3d_data dict for testing."""
    model_outputs = {
        lbl: np.random.default_rng(0).random((3, n_frames)).astype(float)
        for lbl in labels
    }
    return {
        "frame_rate": 100,
        "n_frames": n_frames,
        "point_labels": labels,
        "model_outputs": model_outputs,
        "events": [],
    }


# ── list_available_angles ──────────────────────────────────────────────────

def test_list_available_angles_filters_markers() -> None:
    labels = [
        "LThoraxAngles", "RThoraxAngles",
        "LHumerothoracic_ZXY_Op1",
        "LACR", "LSHO", "RSHO",      # raw markers — should be excluded
        "LElbowAngles_Op1",
    ]
    data = _make_c3d_data(labels)
    result = list_available_angles(data)

    assert "LThoraxAngles" in result
    assert "RThoraxAngles" in result
    assert "LHumerothoracic_ZXY_Op1" in result
    assert "LElbowAngles_Op1" in result
    assert "LACR" not in result
    assert "LSHO" not in result
    assert "RSHO" not in result


def test_list_available_angles_empty() -> None:
    data = _make_c3d_data(["LACR", "RSHO", "LANK"])
    assert list_available_angles(data) == []


# ── extract_angle_curve ────────────────────────────────────────────────────

def test_extract_angle_curve_exact_match() -> None:
    rng = np.random.default_rng(42)
    arr = rng.random((3, 150))
    data = _make_c3d_data(["LThoraxAngles"])
    data["model_outputs"]["LThoraxAngles"] = arr

    result = extract_angle_curve(data, "LThoraxAngles", 1)
    np.testing.assert_array_almost_equal(result, arr[1, :])


def test_extract_angle_curve_left_prefix() -> None:
    rng = np.random.default_rng(7)
    arr = rng.random((3, 100))
    data = _make_c3d_data(["LElbowAngles_Op1"])
    data["model_outputs"]["LElbowAngles_Op1"] = arr

    # Ask without prefix — should find "L" prefixed variant
    result = extract_angle_curve(data, "ElbowAngles_Op1", 0)
    np.testing.assert_array_almost_equal(result, arr[0, :])


def test_extract_angle_curve_missing_raises() -> None:
    data = _make_c3d_data(["LACR"])
    with pytest.raises(KeyError, match="not found"):
        extract_angle_curve(data, "ElbowAngles_Op1", 0)


# ── extract_angle_curve_sided ──────────────────────────────────────────────

def test_extract_angle_curve_sided_L() -> None:
    rng = np.random.default_rng(1)
    arr_l = rng.random((3, 80))
    arr_r = rng.random((3, 80))
    labels = ["LHumerothoracic_ZXY_Op1", "RHumerothoracic_ZXY_Op1"]
    data = _make_c3d_data(labels, n_frames=80)
    data["model_outputs"]["LHumerothoracic_ZXY_Op1"] = arr_l
    data["model_outputs"]["RHumerothoracic_ZXY_Op1"] = arr_r

    result = extract_angle_curve_sided(
        data, "Humerothoracic_ZXY_Op1", 0, side="L")
    np.testing.assert_array_almost_equal(result, arr_l[0, :])


def test_extract_angle_curve_sided_R() -> None:
    rng = np.random.default_rng(2)
    arr_r = rng.random((3, 80))
    labels = ["RHumerothoracic_ZXY_Op1"]
    data = _make_c3d_data(labels, n_frames=80)
    data["model_outputs"]["RHumerothoracic_ZXY_Op1"] = arr_r

    result = extract_angle_curve_sided(
        data, "Humerothoracic_ZXY_Op1", 0, side="R")
    np.testing.assert_array_almost_equal(result, arr_r[0, :])


# ── compute_rom_stats_array ────────────────────────────────────────────────

def test_compute_rom_stats_array_basic() -> None:
    # 20° amplitude sine over 400 samples (2 full cycles).
    # Each 100-sample segment covers half a period: ROM ≈ amplitude = 20°.
    t = np.linspace(0, 4 * np.pi, 400)
    signal = 20.0 * np.sin(t)

    segments = [(0, 99), (100, 199), (200, 299), (300, 399)]
    stats = compute_rom_stats_array(signal, segments)

    assert len(stats["roms"]) == 4
    assert abs(stats["mean"] - 20.0) < 2.0   # half-period ROM ≈ amplitude
    assert stats["sd"] >= 0.0
    assert isinstance(stats["outlier_flags"], list)
    assert len(stats["outlier_flags"]) == 4


def test_compute_rom_stats_array_nan_segment() -> None:
    signal = np.array([float("nan")] * 50 + list(range(50)), dtype=float)
    segments = [(0, 49), (50, 99)]
    stats = compute_rom_stats_array(signal, segments)

    assert np.isnan(stats["roms"][0])
    assert not np.isnan(stats["roms"][1])


# ── _unfold_norm_signal ────────────────────────────────────────────────────

def test_unfold_recovers_sine_from_abs_sine() -> None:
    """
    |sin(t)| should unfold back to ±sin(t) (up to initial-sign polarity).
    We verify the unfolded signal matches the original sin(t) in shape,
    tolerating a global sign flip if initial_sign=-1.
    """
    t = np.linspace(0, 4 * np.pi, 400)
    original = np.sin(t)
    norm = np.abs(original)

    unfolded = _unfold_norm_signal(norm, initial_sign=1.0, threshold=0.15, order=5)

    # Allow global sign flip: check both polarities
    err_pos = np.max(np.abs(unfolded - original))
    err_neg = np.max(np.abs(unfolded + original))
    assert min(err_pos, err_neg) < 0.15, (
        f"Unfolded signal does not match ±sin(t); "
        f"min error={min(err_pos, err_neg):.4f}"
    )


def test_unfold_initial_sign_positive() -> None:
    """First segment must carry the requested initial sign."""
    norm = np.abs(np.sin(np.linspace(0, 2 * np.pi, 200)))
    unfolded = _unfold_norm_signal(norm, initial_sign=1.0, threshold=0.15, order=5)
    # First value is sin(0)≈0, check a slightly later frame
    assert unfolded[10] > 0.0


def test_unfold_initial_sign_negative() -> None:
    """First segment must carry negative initial sign when requested."""
    norm = np.abs(np.sin(np.linspace(0, 2 * np.pi, 200)))
    unfolded = _unfold_norm_signal(norm, initial_sign=-1.0, threshold=0.15, order=5)
    assert unfolded[10] < 0.0


def test_unfold_no_flip_above_threshold() -> None:
    """Minima above threshold must NOT trigger a sign flip."""
    # Signal oscillates between 20 and 30 — never close to zero
    t = np.linspace(0, 4 * np.pi, 300)
    norm = 25.0 + 5.0 * np.sin(t)
    unfolded = _unfold_norm_signal(norm, initial_sign=1.0, threshold=15.0, order=5)
    # No flip → all values positive
    assert np.all(unfolded > 0.0)


# ── compute_thorax_trunk_pair ──────────────────────────────────────────────

def _make_thorax_c3d(
    thorax_x: np.ndarray,
    thorax_y: np.ndarray,
    trunk_z_raw: np.ndarray,
) -> dict:
    """Build a minimal c3d_data dict with ThoraxAngles and Trunk_Inclination_Angle."""
    n = len(thorax_x)
    thorax_arr = np.zeros((3, n))
    thorax_arr[0, :] = thorax_x
    thorax_arr[1, :] = thorax_y

    trunk_arr = np.zeros((3, n))
    # trunk_z_raw is the value BEFORE the 90° offset correction
    trunk_arr[2, :] = trunk_z_raw

    return {
        "frame_rate": 100,
        "n_frames": n,
        "point_labels": ["ThoraxAngles", "Trunk_Inclination_Angle"],
        "model_outputs": {
            "ThoraxAngles": thorax_arr,
            "Trunk_Inclination_Angle": trunk_arr,
        },
        "events": [],
    }


def test_thorax_trunk_pair_initial_sign_from_trunk_z() -> None:
    """
    When trunk_z (after -90 offset) is positive in the first 10 frames,
    the first segment of thorax_norm_signed must be positive.
    """
    n = 300
    t = np.linspace(0, 4 * np.pi, n)
    thorax_x = np.abs(np.sin(t)) * 20.0
    thorax_y = np.zeros(n)
    # trunk_z after offset = +10 → raw = 100
    trunk_z_raw = np.full(n, 100.0)

    data = _make_thorax_c3d(thorax_x, thorax_y, trunk_z_raw)
    result = compute_thorax_trunk_pair(data, zero_threshold=3.0)

    assert result["thorax_norm_signed"][10] > 0.0


def test_thorax_trunk_pair_initial_sign_negative() -> None:
    """
    When trunk_z (after -90 offset) is negative in the first 10 frames,
    the first segment of thorax_norm_signed must be negative.
    """
    n = 300
    t = np.linspace(0, 4 * np.pi, n)
    thorax_x = np.abs(np.sin(t)) * 20.0
    thorax_y = np.zeros(n)
    # trunk_z after offset = -10 → raw = 80
    trunk_z_raw = np.full(n, 80.0)

    data = _make_thorax_c3d(thorax_x, thorax_y, trunk_z_raw)
    result = compute_thorax_trunk_pair(data, zero_threshold=3.0)

    assert result["thorax_norm_signed"][10] < 0.0


def test_thorax_trunk_pair_trunk_z_offset_removed() -> None:
    """trunk_inclination_z in the output must have 90° subtracted."""
    n = 100
    trunk_z_raw = np.full(n, 100.0)
    data = _make_thorax_c3d(np.ones(n), np.zeros(n), trunk_z_raw)
    result = compute_thorax_trunk_pair(data)
    np.testing.assert_allclose(result["trunk_inclination_z"], 10.0)


def test_thorax_trunk_pair_missing_thorax_raises() -> None:
    data = _make_c3d_data(["Trunk_Inclination_Angle"])
    with pytest.raises(KeyError, match="ThoraxAngles"):
        compute_thorax_trunk_pair(data)


def test_thorax_trunk_pair_missing_trunk_raises() -> None:
    data = _make_c3d_data(["ThoraxAngles"])
    with pytest.raises(KeyError, match="Trunk_Inclination_Angle"):
        compute_thorax_trunk_pair(data)


# ── detect_events ──────────────────────────────────────────────────────────

def test_detect_events_empty() -> None:
    data = _make_c3d_data(["LThoraxAngles"])
    assert detect_events(data) == []


def test_detect_events_returns_stored() -> None:
    data = _make_c3d_data(["LThoraxAngles"])
    data["events"] = [
        {"name": "Event", "frame": 50, "time": 0.5},
        {"name": "Event", "frame": 150, "time": 1.5},
    ]
    events = detect_events(data)
    assert len(events) == 2
    assert events[0]["frame"] == 50
    assert events[1]["time"] == 1.5
