"""Reference constructions that preserve availability and construction provenance."""

import numpy as np

MARKER_REFERENCE_SPECS = (
    ("left_shoulder_surface", 5, ("LCAJ",)),
    ("right_shoulder_surface", 6, ("RCAJ",)),
    ("left_elbow_midpoint", 7, ("LHLE", "LHME")),
    ("right_elbow_midpoint", 8, ("RHLE", "RHME")),
    ("left_wrist_midpoint", 9, ("LRSP", "LUSP")),
    ("right_wrist_midpoint", 10, ("RRSP", "RUSP")),
    ("left_knee_midpoint", 13, ("LFLE", "LFME")),
    ("right_knee_midpoint", 14, ("RFLE", "RFME")),
    ("left_ankle_midpoint", 15, ("LFAL", "LTAM")),
    ("right_ankle_midpoint", 16, ("RFAL", "RTAM")),
)

FITTED_REFERENCE_SPECS = (
    ("left_shoulder_origin", 5, "LUArm"),
    ("right_shoulder_origin", 6, "RUArm"),
    ("left_elbow_origin", 7, "LFArm"),
    ("right_elbow_origin", 8, "RFArm"),
    ("left_wrist_origin", 9, "LHand"),
    ("right_wrist_origin", 10, "RHand"),
    ("left_knee_origin", 13, "LShin"),
    ("right_knee_origin", 14, "RShin"),
    ("left_ankle_origin", 15, "LFoot"),
    ("right_ankle_origin", 16, "RFoot"),
)


def paired_midpoint(first, second):
    """Construct a midpoint only when both landmarks are directly observed."""
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if first.shape != second.shape or first.ndim < 1 or first.shape[-1] != 3:
        raise ValueError("landmark arrays must share shape (..., 3)")
    valid = np.isfinite(first).all(axis=-1) & np.isfinite(second).all(axis=-1)
    midpoint = np.full(first.shape, np.nan, dtype=float)
    midpoint[valid] = (first[valid] + second[valid]) / 2.0
    provenance = np.full(valid.shape, "missing", dtype="U16")
    provenance[valid] = "paired_direct"
    return {"xyz": midpoint, "valid": valid, "provenance": provenance}


def marker_joint_references(positions, semantic_names, strict=False):
    """Construct explicit marker references aligned to a COCO17 index subset."""
    positions = np.asarray(positions, dtype=float)
    if positions.ndim != 3 or positions.shape[2] != 3:
        raise ValueError("positions must have shape (frames, markers, 3)")
    if positions.shape[1] != len(semantic_names):
        raise ValueError("semantic_names must match the marker dimension")
    indices = {name: index for index, name in enumerate(semantic_names)}
    missing = sorted(
        {
            marker
            for _, _, markers in MARKER_REFERENCE_SPECS
            for marker in markers
            if marker not in indices
        }
    )
    if missing and strict:
        raise ValueError("required marker semantics missing: {}".format(missing))
    xyz = np.full((len(positions), len(MARKER_REFERENCE_SPECS), 3), np.nan)
    provenance = []
    for output_index, (_, _, markers) in enumerate(MARKER_REFERENCE_SPECS):
        if any(marker not in indices for marker in markers):
            provenance.append("unavailable_semantic")
            continue
        if len(markers) == 1:
            xyz[:, output_index] = positions[:, indices[markers[0]]]
            provenance.append("direct_surface_marker")
        else:
            midpoint = paired_midpoint(
                positions[:, indices[markers[0]]],
                positions[:, indices[markers[1]]],
            )
            xyz[:, output_index] = midpoint["xyz"]
            provenance.append("paired_anatomical_midpoint")
    return {
        "xyz": xyz,
        "valid": np.isfinite(xyz).all(axis=2),
        "names": [spec[0] for spec in MARKER_REFERENCE_SPECS],
        "coco17_indices": np.asarray(
            [spec[1] for spec in MARKER_REFERENCE_SPECS], dtype=int
        ),
        "provenance": np.asarray(provenance),
    }


def fitted_joint_references(positions, semantic_names):
    """Keep Motive fitted origins as a distinct, model-derived reference stratum."""
    positions = np.asarray(positions, dtype=float)
    if positions.ndim != 3 or positions.shape[2] != 3:
        raise ValueError("positions must have shape (frames, bones, 3)")
    indices = {name: index for index, name in enumerate(semantic_names)}
    missing = [name for _, _, name in FITTED_REFERENCE_SPECS if name not in indices]
    if missing:
        raise ValueError("required fitted origins missing: {}".format(missing))
    xyz = np.stack(
        [positions[:, indices[name]] for _, _, name in FITTED_REFERENCE_SPECS],
        axis=1,
    )
    return {
        "xyz": xyz,
        "valid": np.isfinite(xyz).all(axis=2),
        "names": [spec[0] for spec in FITTED_REFERENCE_SPECS],
        "coco17_indices": np.asarray(
            [spec[1] for spec in FITTED_REFERENCE_SPECS], dtype=int
        ),
        "provenance": np.asarray(
            ["motive_fitted_origin"] * len(FITTED_REFERENCE_SPECS)
        ),
    }
