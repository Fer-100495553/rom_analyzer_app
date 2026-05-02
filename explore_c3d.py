"""
explore_c3d.py — Inspect a Vicon Nexus C3D file and print a structured report.

Usage:
    python explore_c3d.py <path_to_file.c3d>

Output is printed to stdout AND saved to c3d_exploration_report.txt in the
same directory as this script.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

import numpy as np

# ── keywords that identify SULM model-output labels ──────────────────────
ANGLE_KEYWORDS = ["Angle", "Humerothoracic", "Elbow", "Thorax", "Clavicle"]
N_PREVIEW = 10          # number of frame values shown per label/component
COMPONENTS = ("X", "Y", "Z")


def _strip_prefix(label: str) -> str:
    """Remove any 'SubjectName:' prefix from a C3D label."""
    return label.split(":")[-1].strip() if ":" in label else label.strip()


def _is_angle_label(label: str) -> bool:
    return any(kw in label for kw in ANGLE_KEYWORDS)


def explore(c3d_path: str) -> str:
    """
    Read the C3D file and build the full report as a string.

    Args:
        c3d_path: Absolute or relative path to the .c3d file.

    Returns:
        Multi-line report string.
    """
    import ezc3d

    c = ezc3d.c3d(c3d_path)

    lines: list[str] = []

    def say(*args, **kwargs) -> None:
        lines.append(" ".join(str(a) for a in args))

    # ── header ────────────────────────────────────────────────────────────
    say("=" * 72)
    say("C3D EXPLORATION REPORT")
    say(f"File : {os.path.abspath(c3d_path)}")
    say("=" * 72)

    # ── frame rate & frame count ──────────────────────────────────────────
    try:
        rate_raw = c["parameters"]["POINT"]["RATE"]["value"]
        frame_rate = float(rate_raw[0]) if hasattr(rate_raw, "__len__") else float(rate_raw)
    except (KeyError, IndexError, TypeError):
        frame_rate = float(c["header"]["frame_rate"])

    point_data: np.ndarray = c["data"]["points"]   # (4, n_labels, n_frames)
    n_frames = point_data.shape[2]
    n_labels = point_data.shape[1]

    say()
    say(f"Frame rate : {frame_rate:.1f} Hz")
    say(f"Frames     : {n_frames}  ({n_frames / frame_rate:.2f} s)")

    # ── all point labels ──────────────────────────────────────────────────
    raw_labels: list[str] = c["parameters"]["POINT"]["LABELS"]["value"]
    clean_labels: list[str] = [_strip_prefix(l) for l in raw_labels[:n_labels]]

    say()
    say("-" * 72)
    say(f"POINT LABELS  ({len(clean_labels)} total)")
    say("-" * 72)
    for i, lbl in enumerate(clean_labels):
        marker = "  ★" if _is_angle_label(lbl) else ""
        say(f"  [{i:>3}]  {lbl}{marker}")
    say()
    say("  ★ = SULM model-output label (angle / kinematics)")

    # ── events ────────────────────────────────────────────────────────────
    say()
    say("-" * 72)
    say("EVENTS")
    say("-" * 72)

    events_found = False
    try:
        params = c["parameters"]
        if "EVENT" in params:
            ev = params["EVENT"]
            raw_times = ev.get("TIMES", {}).get("value", [])
            ev_labels: list[str] = ev.get("LABELS", {}).get("value", [])
            contexts: list[str] = ev.get("CONTEXTS", {}).get("value", [])

            if hasattr(raw_times, "ndim"):
                times_arr = np.asarray(raw_times, dtype=float)
                time_values = times_arr[1, :] if (times_arr.ndim == 2 and times_arr.shape[0] >= 2) \
                              else times_arr.ravel()
            elif raw_times and isinstance(raw_times[0], (list, tuple)):
                time_values = [float(t) for t in raw_times[1]]
            else:
                time_values = [float(t) for t in raw_times]

            for i, t in enumerate(time_values):
                frame = int(round(float(t) * frame_rate))
                name = ev_labels[i] if i < len(ev_labels) else f"Event_{i}"
                ctx = contexts[i] if i < len(contexts) else ""
                say(f"  [{i:>3}]  {name:<20}  t={float(t):.4f} s  frame={frame:>5}  ctx={ctx}")
                events_found = True
    except Exception as exc:
        say(f"  (could not parse events: {exc})")

    if not events_found:
        say("  No events found in this file.")

    # ── angle / SULM label detail ─────────────────────────────────────────
    say()
    say("-" * 72)
    say("SULM MODEL OUTPUT LABELS — first 10 values of component 0 (X / Rot1)")
    say("-" * 72)

    angle_labels = [(i, lbl) for i, lbl in enumerate(clean_labels) if _is_angle_label(lbl)]

    if not angle_labels:
        say("  None found — check ANGLE_KEYWORDS or label names.")
    else:
        for idx, lbl in angle_labels:
            say()
            say(f"  Label [{idx:>3}]: {lbl}")
            arr = point_data[:3, idx, :]   # (3, n_frames)
            for comp_i, comp_name in enumerate(COMPONENTS):
                vals = arr[comp_i, :N_PREVIEW]
                val_str = "  ".join(f"{v:9.3f}" for v in vals)
                say(f"    {comp_name}: {val_str}")

            # Per-component range over the whole trial
            say(f"    Ranges over {n_frames} frames:")
            for comp_i, comp_name in enumerate(COMPONENTS):
                col = arr[comp_i, :]
                valid = col[~np.isnan(col)]
                if valid.size:
                    say(f"      {comp_name}: min={valid.min():9.3f}  "
                        f"max={valid.max():9.3f}  "
                        f"mean={valid.mean():9.3f}  "
                        f"std={valid.std():7.3f}")
                else:
                    say(f"      {comp_name}: all NaN")

    # ── analog channels (informational) ───────────────────────────────────
    try:
        analog_labels = c["parameters"]["ANALOG"]["LABELS"]["value"]
        say()
        say("-" * 72)
        say(f"ANALOG CHANNELS  ({len(analog_labels)} total, not expanded)")
        say("-" * 72)
        for i, lbl in enumerate(analog_labels[:20]):
            say(f"  [{i:>3}]  {lbl}")
        if len(analog_labels) > 20:
            say(f"  … and {len(analog_labels) - 20} more")
    except KeyError:
        pass

    say()
    say("=" * 72)
    say("END OF REPORT")
    say("=" * 72)

    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python explore_c3d.py <path_to_file.c3d>")
        sys.exit(1)

    c3d_path = sys.argv[1]
    if not os.path.isfile(c3d_path):
        print(f"Error: file not found: {c3d_path}")
        sys.exit(1)

    report = explore(c3d_path)
    print(report)

    out_path = Path(__file__).parent / "c3d_exploration_report.txt"
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {out_path}")


if __name__ == "__main__":
    main()
