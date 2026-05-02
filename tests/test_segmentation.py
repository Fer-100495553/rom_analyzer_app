"""
Tests for segmentation.py — peak detection and ROM computation.
"""
from __future__ import annotations

import sys
import os

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from segmentation import (
    detect_peaks_valleys,
    auto_segment,
    compute_rep_roms,
    compute_stats_from_roms,
)


# ── Synthetic signal helpers ───────────────────────────────────────────────

def _sine_signal(
    n_cycles: int = 5,
    amplitude: float = 45.0,
    offset: float = 20.0,
    fps: int = 100,
    duration_s: float = 10.0,
) -> np.ndarray:
    """
    Sine wave with known number of peaks and valleys.

    Returns a signal with `n_cycles` complete cycles at 100 Hz for
    `duration_s` seconds.  Peak value = offset + amplitude,
    valley value = offset - amplitude.
    """
    t = np.linspace(0, duration_s, int(fps * duration_s), endpoint=False)
    return offset + amplitude * np.sin(2 * np.pi * n_cycles / duration_s * t)


# ── detect_peaks_valleys ───────────────────────────────────────────────────

def test_detect_peaks_correct_count() -> None:
    signal = _sine_signal(n_cycles=5, fps=100, duration_s=10.0)
    peaks, valleys = detect_peaks_valleys(signal, min_prominence=10.0,
                                          min_distance=50)
    # 5 complete cycles → 5 peaks and 5 valleys
    assert len(peaks) == 5
    assert len(valleys) == 5


def test_detect_peaks_values_near_max() -> None:
    amplitude = 45.0
    offset = 20.0
    signal = _sine_signal(n_cycles=3, amplitude=amplitude, offset=offset,
                          fps=100, duration_s=9.0)
    peaks, valleys = detect_peaks_valleys(signal, min_prominence=10.0,
                                          min_distance=50)
    # Peak values should be close to offset + amplitude
    for p in peaks:
        assert abs(signal[p] - (offset + amplitude)) < 3.0
    # Valley values should be close to offset - amplitude
    for v in valleys:
        assert abs(signal[v] - (offset - amplitude)) < 3.0


def test_detect_peaks_prominence_filters() -> None:
    # Signal with large peaks plus small noise bumps
    rng = np.random.default_rng(99)
    base = _sine_signal(n_cycles=3, amplitude=40.0, fps=100, duration_s=6.0)
    noise = rng.uniform(-2, 2, len(base))
    signal = base + noise

    peaks_strict, _ = detect_peaks_valleys(signal, min_prominence=30.0,
                                           min_distance=80)
    peaks_loose, _ = detect_peaks_valleys(signal, min_prominence=1.0,
                                          min_distance=5)
    assert len(peaks_strict) <= len(peaks_loose)
    assert len(peaks_strict) >= 3   # at least the 3 main cycles


# ── auto_segment ───────────────────────────────────────────────────────────

def test_auto_segment_valley_to_valley() -> None:
    signal = _sine_signal(n_cycles=4, fps=100, duration_s=8.0)
    segs, peaks, valleys = auto_segment(
        signal, min_prominence=10.0, min_distance=50, cycle_from="valley")

    # 4 valleys → 3 valley-to-valley segments
    assert len(segs) == len(valleys) - 1
    for s, e in segs:
        assert s < e


def test_auto_segment_peak_to_peak() -> None:
    signal = _sine_signal(n_cycles=4, fps=100, duration_s=8.0)
    segs, peaks, valleys = auto_segment(
        signal, min_prominence=10.0, min_distance=50, cycle_from="peak")

    assert len(segs) == len(peaks) - 1
    for s, e in segs:
        assert s < e


def test_auto_segment_returns_correct_types() -> None:
    signal = _sine_signal(n_cycles=3, fps=100, duration_s=6.0)
    segs, peaks, valleys = auto_segment(signal, min_prominence=10.0,
                                        min_distance=50)
    assert isinstance(segs, list)
    assert isinstance(peaks, np.ndarray)
    assert isinstance(valleys, np.ndarray)
    for s, e in segs:
        assert isinstance(s, int)
        assert isinstance(e, int)


# ── compute_rep_roms ───────────────────────────────────────────────────────

def test_compute_rep_roms_known_signal() -> None:
    amplitude = 30.0
    signal = _sine_signal(n_cycles=4, amplitude=amplitude, offset=0.0,
                          fps=100, duration_s=8.0)
    segs, _, _ = auto_segment(signal, min_prominence=15.0, min_distance=50,
                               cycle_from="valley")

    roms = compute_rep_roms(signal, segs)
    for r in roms:
        # ROM per full cycle ≈ 2 * amplitude
        assert abs(r - 2 * amplitude) < 5.0, f"ROM {r:.1f} far from expected {2*amplitude}"


def test_compute_rep_roms_nan_for_empty_segment() -> None:
    signal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    roms = compute_rep_roms(signal, [(10, 20)])  # out-of-bounds → empty slice
    assert np.isnan(roms[0])


# ── compute_stats_from_roms ────────────────────────────────────────────────

def test_compute_stats_mean_sd() -> None:
    roms = [40.0, 42.0, 38.0, 41.0, 39.0]
    segments = [(i * 100, i * 100 + 99) for i in range(5)]
    stats = compute_stats_from_roms(roms, segments)

    assert abs(stats["mean"] - np.mean(roms)) < 0.01
    assert abs(stats["sd"] - np.std(roms, ddof=1)) < 0.01
    assert stats["outlier_flags"] == [False] * 5


def test_compute_stats_outlier_flagged() -> None:
    # With n=5 and threshold=2 SD, a single outlier's z-score is bounded by
    # (n-1)/sqrt(n) ≈ 1.79 — masking prevents detection.  Use n=9 so the
    # outlier's z-score exceeds 2 SD and is genuinely flagged.
    roms = [40.0, 41.0, 40.5, 39.5, 42.0, 40.0, 41.5, 39.0, 100.0]
    segments = [(i * 100, i * 100 + 99) for i in range(9)]
    stats = compute_stats_from_roms(roms, segments)

    # The 100.0 value must be flagged as outlier (z > 2 SD with 9 samples)
    assert stats["outlier_flags"][-1] is True
    # Normal values must not be flagged
    assert not any(stats["outlier_flags"][:8])


def test_compute_stats_single_rep() -> None:
    roms = [45.0]
    stats = compute_stats_from_roms(roms, [(0, 99)])
    assert stats["mean"] == 45.0
    assert stats["sd"] == 0.0
    assert stats["outlier_flags"] == [False]
