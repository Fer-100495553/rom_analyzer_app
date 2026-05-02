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
