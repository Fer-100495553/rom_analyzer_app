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
    },
    "Shoulder Abd/Add": {
        "sulm_variable": "Humerothoracic_XZY_Op1",
        "component": 0,
        "description": "Shoulder abduction/adduction (XZY Rotation 1)",
        "has_side_prefix": True,
    },
    "Shoulder Int/Ext Rot": {
        "sulm_variable": "Humerothoracic_ZXY_Op1",
        "component": 2,
        "description": "Shoulder internal/external rotation (ZXY Rotation 3)",
        "has_side_prefix": True,
    },
    "Elbow Flex/Ext": {
        "sulm_variable": "Elbow_Op1",
        "component": 0,
        "description": "Elbow flexion/extension (Rotation 1)",
        "has_side_prefix": True,
    },
    "Thorax Lateral Incl.": {
        "sulm_variable": "ThoraxAngles",
        "component": 1,
        "description": "Thorax lateral inclination (Rotation 2)",
        "has_side_prefix": False,
    },
    "Trunk Extended Lateral Incl.": {
        "sulm_variable": "Trunk_Extended",
        "component": 1,
        "description": "Extended trunk lateral inclination (Rotation 2) — NOT YET AVAILABLE",
        "has_side_prefix": False,
        "optional": True,
    },
    "Trunk Lateral Inclination": {
        "type": "computed",
        "compute_fn": "compute_trunk_extended_angles",
        "primary_key": "lateral_inclination",
        "label": "Trunk Lateral Inclination",
        "unit": "°",
        "has_side_prefix": False,
        "sulm_variable": None,
        "component": None,
        "description": "Trunk lateral inclination computed from IJ/LeftLumbar/RightLumbar markers",
    },
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
    "Thorax Lateral Incl.":        {"max": 30,  "label": "Per side"},
    "Trunk Extended Lateral Incl.":{"max": 35,  "label": "Per side"},
    "Trunk Lateral Inclination":   {"max": 35,  "label": "Per side"},
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
