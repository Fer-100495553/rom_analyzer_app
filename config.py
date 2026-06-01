from __future__ import annotations

# ── Movement definitions — VERIFIED from C3D exploration report ───────────
#
# sulm_variable   : C3D label suffix after the side prefix (e.g. "LeftHumerothoracic_ZXY_Op1")
# component       : Euler component index: 0 = X (Rot1), 1 = Y (Rot2), 2 = Z (Rot3)
# has_side_prefix : True  → label in C3D is "Left<var>" / "Right<var>"
#                   False → label in C3D is "<var>" with no prefix (e.g. ThoraxAngles)
# optional        : True  → variable may not exist in the file yet
MOVEMENT_DEFINITIONS: dict[str, dict] = {
    "Shoulder Flex/Ext": {
        "sulm_variable": "Humerothoracic_ZXY_Op1",
        "component": 0,
        "description": "Shoulder flexion/extension (ZXY Rotation 1)",
        "has_side_prefix": True,
        "display_name_key": "mv_shoulder_flex_ext",
        "peak_label_key":   "mv_peak_flexion",
        "valley_label_key": "mv_valley_extension",
    },
    "Shoulder Abd/Add": {
        "sulm_variable": "Humerothoracic_XZY_Op1",
        "component": 0,
        "description": "Shoulder abduction/adduction (XZY Rotation 1)",
        "has_side_prefix": True,
        "display_name_key": "mv_shoulder_abd_add",
        "peak_label_key":   "mv_peak_abduction",
        "valley_label_key": "mv_valley_adduction",
    },
    "Shoulder Int/Ext Rot": {
        "sulm_variable": "Humerothoracic_ZXY_Op1",
        "component": 2,
        "description": "Shoulder internal/external rotation (ZXY Rotation 3)",
        "has_side_prefix": True,
        "display_name_key": "mv_shoulder_int_ext_rot",
        "peak_label_key":   "mv_peak_int_rot",
        "valley_label_key": "mv_valley_ext_rot",
    },
    "Elbow Flex/Ext": {
        "sulm_variable": "Elbow_Op1",
        "component": 0,
        "description": "Elbow flexion/extension (Rotation 1)",
        "has_side_prefix": True,
        "display_name_key": "mv_elbow_flex_ext",
        "peak_label_key":   "mv_peak_flexion",
        "valley_label_key": "mv_valley_extension",
    },
    "Thorax Lateral Inclination": {
        "type": "computed_pair",
        "compute_fn": "compute_thorax_trunk_pair",
        "primary_key": "thorax_norm_signed",
        "pair_key": "trunk_inclination_z",
        "pair_name": "Trunk Extended Lateral Inclination",
        "pair_data_key": "angle_data",
        "label": "Thorax Lateral Inclination",
        "unit": "°",
        "has_side_prefix": False,
        "sulm_variable": None,
        "component": None,
        "description": "Thorax lateral inclination (Euclidean norm of ThoraxAngles X+Y, signed via Trunk Inclination Angle Z)",
        "display_name_key": "mv_thorax_lat_incl",
        "peak_label_key":   "mv_peak_left",
        "valley_label_key": "mv_valley_right",
    },
    "Trunk Extended Lateral Inclination": {
        "type": "computed_pair",
        "compute_fn": "compute_thorax_trunk_pair",
        "primary_key": "trunk_inclination_z",
        "pair_key": "thorax_norm_signed",
        "pair_name": "Thorax Lateral Inclination",
        "pair_data_key": "angle_data_trunk",
        "label": "Trunk Extended Lateral Inclination",
        "unit": "°",
        "has_side_prefix": False,
        "sulm_variable": None,
        "component": None,
        "description": "Trunk extended lateral inclination from Trunk_Inclination_Angle Z component",
        "display_name_key": "mv_trunk_ext_lat_incl",
        "peak_label_key":   "mv_peak_left",
        "valley_label_key": "mv_valley_right",
    },
}

# Movements that always share one C3D file and one UI row.
# Key = group label shown on screen 1. Value = ordered list of movement names.
MOVEMENT_PAIR_GROUPS: dict[str, list[str]] = {
    "Thorax / Trunk Extended Lateral Inclination": [
        "Trunk Extended Lateral Inclination",
        "Thorax Lateral Inclination",
    ],
}

# Side prefixes are full words (verified from C3D label names)
SIDE_PREFIXES: dict[str, str] = {
    "left": "Left",
    "right": "Right",
}

# ── Segmentation defaults ─────────────────────────────────────────────────
DEFAULT_MIN_PROMINENCE: int = 15    # degrees
DEFAULT_MIN_DISTANCE: int = 50      # frames
DEFAULT_OUTLIER_THRESHOLD: int = 2  # standard deviations

# Backward-compatibility aliases used by data_processing.py and segmentation.py
DEFAULT_PROMINENCE: int = DEFAULT_MIN_PROMINENCE
OUTLIER_SD_THRESHOLD: int = DEFAULT_OUTLIER_THRESHOLD

# Trunk lateral inclination has a smaller amplitude than arm movements,
# so lower detection thresholds are needed.
TRUNK_LATERAL_MIN_PROMINENCE: int = 5   # degrees
TRUNK_LATERAL_MIN_DISTANCE: int = 30    # frames at 100 Hz

# ── Normative ROM reference values (degrees, healthy subjects) ────────────
NORMATIVE_ROM: dict[str, dict] = {
    "Shoulder Flex/Ext":           {"max": 170, "label": "Flexion"},
    "Shoulder Abd/Add":            {"max": 170, "label": "Abduction"},
    "Shoulder Int/Ext Rot":        {"max": 155, "label": "Total (Int+Ext)"},
    "Elbow Flex/Ext":              {"max": 140, "label": "Flexion"},
    "Thorax Lateral Inclination":            {"max": 35,  "label": "Per side"},
    "Trunk Extended Lateral Inclination":   {"max": 35,  "label": "Per side"},
}

# ── Label-filtering keywords ──────────────────────────────────────────────
# Used by list_available_angles() to separate model outputs from raw markers.
ANGLE_KEYWORDS: list[str] = [
    "Angles",
    "Humerothoracic",
    "Elbow",
    "Thorax",
    "Clavicle",
    "Trunk",
]

# ── Misc ──────────────────────────────────────────────────────────────────
DEFAULT_FRAME_RATE: int = 100
