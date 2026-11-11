"""Outcome-neutral repeatability audit of admitted SAM-derived 3D rows."""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from observability.assets import local_output

MHR = {
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_hip": 9,
    "right_hip": 10,
    "left_knee": 11,
    "right_knee": 12,
    "left_ankle": 13,
    "right_ankle": 14,
    "right_wrist": 41,
    "left_wrist": 62,
    "left_olecranon": 63,
    "right_olecranon": 64,
    "left_cubital_fossa": 65,
    "right_cubital_fossa": 66,
    "left_acromion": 67,
    "right_acromion": 68,
}

REPEATABILITY = {"minimum_identity_rows": 5, "minimum_reliability": 0.75}


def _distance(joints, first, second):
    return np.linalg.norm(joints[:, MHR[first]] - joints[:, MHR[second]], axis=1)


def _distribution(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return {
        "n": int(len(values)),
        "median": float(np.median(values)) if len(values) else None,
        "p10": float(np.percentile(values, 10)) if len(values) else None,
        "p90": float(np.percentile(values, 90)) if len(values) else None,
    }


def _reliability(identity_values):
    groups = [np.asarray(values) for values in identity_values if len(values) >= 5]
    if len(groups) < 2:
        return {"identities": len(groups), "reliability": None}
    means = np.asarray([np.mean(values) for values in groups])
    within = float(np.mean([np.var(values, ddof=1) for values in groups]))
    between = float(np.var(means, ddof=1))
    reliability = between / (between + within) if between + within > 0 else 0.0
    return {
        "identities": len(groups),
        "rows": int(sum(len(values) for values in groups)),
        "between_variance": between,
        "within_variance": within,
        "reliability": reliability,
        "identity_median_within_sd": float(
            np.median([np.std(values, ddof=1) for values in groups])
        ),
    }


def audit_sam_rows(
    root,
    output=Path("local/pilot/sam-repeatability.json"),
    max_rows_per_shard=2500,
):
    """Audit shape-ratio stability without claiming pseudo-label accuracy."""
    root = Path(root)
    files = sorted(root.glob("*.npz"))
    if not files:
        raise ValueError("SAM row root has no NPZ shards")
    ratios = defaultdict(list)
    by_identity = defaultdict(lambda: defaultdict(list))
    offsets = defaultdict(list)
    source_rows = defaultdict(int)
    sampled_rows = 0
    valid_rows = 0
    for path in files:
        with np.load(path) as shard:
            required = {"source", "group", "person", "j70", "vis70"}
            if not required.issubset(shard.files):
                continue
            rows = len(shard["j70"])
            if not rows:
                continue
            count = min(max_rows_per_shard, rows)
            indices = np.linspace(0, rows - 1, count, dtype=int)
            joints = shard["j70"][indices].astype(np.float32)
            visible = shard["vis70"][indices]
            source = str(shard["source"].item())
            groups = shard["group"][indices].astype(str)
            people = shard["person"][indices].astype(str)
            source_rows[source] += rows
            sampled_rows += count
            needed = np.asarray(sorted(set(MHR.values())), dtype=int)
            valid = visible[:, needed].all(axis=1) & np.isfinite(joints[:, needed]).all(
                axis=(1, 2)
            )
            if not valid.any():
                continue
            joints = joints[valid]
            groups = groups[valid]
            people = people[valid]
            valid_rows += len(joints)
            upper_left = _distance(joints, "left_shoulder", "left_elbow")
            upper_right = _distance(joints, "right_shoulder", "right_elbow")
            fore_left = _distance(joints, "left_elbow", "left_wrist")
            fore_right = _distance(joints, "right_elbow", "right_wrist")
            thigh_left = _distance(joints, "left_hip", "left_knee")
            thigh_right = _distance(joints, "right_hip", "right_knee")
            shank_left = _distance(joints, "left_knee", "left_ankle")
            shank_right = _distance(joints, "right_knee", "right_ankle")
            values = {
                "left_forearm_fraction": fore_left / (upper_left + fore_left),
                "right_forearm_fraction": fore_right / (upper_right + fore_right),
                "left_shank_fraction": shank_left / (thigh_left + shank_left),
                "right_shank_fraction": shank_right / (thigh_right + shank_right),
            }
            for name, value in values.items():
                ratios[name].extend(value.tolist())
                for group, person, item in zip(groups, people, value):
                    by_identity[name][(source, group, person)].append(float(item))
            offsets["left_shoulder_to_acromion_mm"].extend(
                (1000.0 * _distance(joints, "left_shoulder", "left_acromion")).tolist()
            )
            offsets["right_shoulder_to_acromion_mm"].extend(
                (
                    1000.0 * _distance(joints, "right_shoulder", "right_acromion")
                ).tolist()
            )
            left_elbow_surface = 0.5 * (
                joints[:, MHR["left_olecranon"]] + joints[:, MHR["left_cubital_fossa"]]
            )
            right_elbow_surface = 0.5 * (
                joints[:, MHR["right_olecranon"]]
                + joints[:, MHR["right_cubital_fossa"]]
            )
            offsets["left_elbow_to_surface_midpoint_mm"].extend(
                (
                    1000.0
                    * np.linalg.norm(
                        joints[:, MHR["left_elbow"]] - left_elbow_surface, axis=1
                    )
                ).tolist()
            )
            offsets["right_elbow_to_surface_midpoint_mm"].extend(
                (
                    1000.0
                    * np.linalg.norm(
                        joints[:, MHR["right_elbow"]] - right_elbow_surface, axis=1
                    )
                ).tolist()
            )

    repeatability = {
        name: _reliability(list(identities.values()))
        for name, identities in by_identity.items()
    }
    result = {
        "schema": "sam-pseudo-shape-repeatability-v1",
        "shards": len(files),
        "source_rows": dict(sorted(source_rows.items())),
        "sampled_rows": sampled_rows,
        "fully_visible_rows": valid_rows,
        "shape_ratio_distribution": {
            name: _distribution(values) for name, values in ratios.items()
        },
        "repeatability": repeatability,
        "anatomical_correspondence_offsets": {
            name: _distribution(values) for name, values in offsets.items()
        },
        "frozen_interpretation": REPEATABILITY,
        "stable_enough_for_personalisation_pilot": all(
            value["reliability"] is not None
            and value["reliability"] >= REPEATABILITY["minimum_reliability"]
            for value in repeatability.values()
        ),
        "qualifications": [
            "These are SAM-derived pseudo labels, not independent anatomical truth.",
            "Group-plus-person is a repeat key, not a verified human identity.",
            "Sampling is deterministic within each shard and does not admit source datasets.",
            "Repeatability can reject instability but cannot establish accuracy.",
        ],
    }
    output = local_output(Path(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
