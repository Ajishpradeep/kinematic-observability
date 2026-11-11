"""Construct wrist references and estimate calibrated wrist positions."""

from functools import lru_cache
from pathlib import Path

import numpy as np

from observability.assets import sha256
from observability.pilot.calibration import parse_mcal, project_points, world_to_camera
from observability.pilot.motive import load_positions, read_schema
from observability.pilot.references import paired_midpoint
from observability.pilot.triangulation import _world_ray, triangulate_rays

from .design import read_json

REFERENCES = ("midpoint", "fitted", "radial", "ulnar")
METHODS = ("view_a", "view_b", "two_view")
MARKER_NAMES = ("LRSP", "RRSP", "LUSP", "RUSP")
BONE_NAMES = ("LHand", "RHand")
COCO17_WRISTS = (9, 10)
DEPTH_ANCHOR_MM = (0.0, 1000.0, 0.0)


def on_depth_plane(ray, camera, anchor=DEPTH_ANCHOR_MM):
    """Intersect a forward pixel ray with the camera-Z plane through anchor."""
    origin, direction = ray
    normal = world_to_camera(camera)[0][2]
    denominator = normal @ direction
    if denominator <= 1e-8:
        return None
    distance = normal @ (np.asarray(anchor) - origin) / denominator
    return origin + distance * direction if distance > 0 else None


def _positions(path, entity_type, names, frames, schema):
    result = np.full(frames.shape + (len(names), 3), np.nan)
    available = [
        block["semantic_name"]
        for block in schema["blocks"]
        if block["entity_type"] == entity_type and block["semantic_name"] in names
    ]
    if len(set(available)) != len(available):
        raise ValueError("ambiguous duplicate reference channels")
    if not available:
        return result, [False] * len(names)
    source = load_positions(path, entity_type=entity_type, semantic_names=names)
    index = {name: i for i, name in enumerate(source["semantic_names"])}
    valid = (frames >= 0) & (frames < len(source["positions"]))
    for target, name in enumerate(names):
        if name in index:
            result[..., target, :][valid] = source["positions"][
                frames[valid], index[name]
            ]
    return result, [name in index for name in names]


def references(path, frames):
    schema = read_schema(path)
    meta = schema["metadata"]
    if (meta.get("Length Units"), meta.get("Coordinate Space")) != (
        "Millimeters",
        "Global",
    ):
        raise ValueError("expected Motive global millimeter positions")
    marker, marker_schema = _positions(path, "Marker", MARKER_NAMES, frames, schema)
    fitted, fitted_schema = _positions(path, "Bone", BONE_NAMES, frames, schema)
    radial, ulnar = marker[..., :2, :], marker[..., 2:, :]
    return {
        "midpoint": paired_midpoint(radial, ulnar)["xyz"],
        "fitted": fitted,
        "radial": radial,
        "ulnar": ulnar,
    }, {
        "midpoint": [a and b for a, b in zip(marker_schema[:2], marker_schema[2:])],
        "fitted": fitted_schema,
        "radial": marker_schema[:2],
        "ulnar": marker_schema[2:],
    }


def estimate(pixel, confidence, cameras):
    """Map common COCO17 wrists to two independent 1-view paths and a 2-view path."""
    frames = pixel.shape[1]
    xyz = np.full((3, frames, 2, 3), np.nan)
    wrist_score = np.full((3, frames, 2), np.nan)
    ray_gap = np.full((3, frames, 2), np.nan)
    for frame in range(frames):
        for side in range(2):
            rays = [None, None]
            for view, camera in enumerate(cameras):
                xy = pixel[view, frame, side]
                score = confidence[view, frame, side]
                if not np.isfinite(xy).all() or not np.isfinite(score) or score <= 0:
                    continue
                rays[view] = _world_ray(xy, camera)
                position = on_depth_plane(rays[view], camera)
                if position is not None:
                    xyz[view, frame, side] = position
                    wrist_score[view, frame, side] = 1 - score
            if all(ray is not None for ray in rays):
                triangulated = triangulate_rays(*rays[0], *rays[1])
                if triangulated is not None:
                    xyz[2, frame, side] = triangulated["xyz_mm"]
                    wrist_score[2, frame, side] = 1 - confidence[:, frame, side].min()
                    ray_gap[2, frame, side] = triangulated["ray_gap_mm"]
    return xyz, wrist_score, ray_gap


@lru_cache(maxsize=16)
def _read_calibration(path, expected_hash):
    if sha256(path) != expected_hash:
        raise ValueError("calibration changed after observation")
    return parse_mcal(path)


def projection_support(projected, cameras):
    """Identify reference pixels inside both calibrated image rectangles."""
    limits = np.array([[camera["width"], camera["height"]] for camera in cameras])
    return ((projected >= 0) & (projected < limits[:, None, None, :])).all(axis=(0, 3))


def measure_take(record, root, observations, design_hash):
    take = record["take_id"]
    metadata = read_json(observations / f"{take}.json")
    path = observations / f"{take}.npz"
    if metadata["config"]["design_sha256"] != design_hash:
        raise ValueError("observation belongs to a different frozen design")
    if sha256(path) != metadata["arrays_sha256"]:
        raise ValueError("observations changed after inference")
    source = metadata["source_sha256"]
    body = root / record["body_csv"]
    if sha256(body) != source["body_csv"]:
        raise ValueError("Motive CSV changed after observation")
    frame = np.asarray(record["windows"], dtype=int).reshape(-1)
    calibration = _read_calibration(root / record["calibration"], source["calibration"])
    cameras = [calibration[view["camera_serial"]] for view in record["views"]]
    ref, schema = references(body, frame[None, :] + np.arange(-1, 2)[:, None])
    with np.load(path) as data:
        if not np.array_equal(frame, data["frames"]):
            raise ValueError("detector frame schedule differs from design")
        confidence = data["confidence"][..., COCO17_WRISTS]
        pixels = data["xy"][..., COCO17_WRISTS, :]
        detections = data["detections"]
        decoded = data["decoded"]
    xyz, wrist_score, ray_gap = estimate(pixels, confidence, cameras)
    midpoint = ref["midpoint"][1]
    projected = np.stack([project_points(midpoint, camera) for camera in cameras])
    supported = projection_support(projected, cameras)
    oracle, _, _ = estimate(
        np.where(supported[None, ..., None], projected, np.nan),
        np.ones_like(confidence),
        cameras,
    )
    valid = np.isfinite(midpoint).all(axis=-1)
    error = np.linalg.norm(oracle[2][supported] - midpoint[supported], axis=-1)
    if supported.any():
        if not np.isfinite(error).all() or np.max(error) > 1e-3:
            raise ValueError("marker projection oracle did not round-trip")
    return {
        "take_id": take,
        "group": record["group"],
        "fps": record["fps"],
        "decoded": decoded,
        "detections": detections,
        "confidence": confidence,
        "pixels": pixels,
        "xyz": xyz,
        "wrist_score": wrist_score,
        "ray_gap": ray_gap,
        "reference": ref,
        "reference_schema": schema,
        "oracle": oracle,
        "oracle_supported_positions": int(supported.sum()),
        "oracle_outside_common_image": int((valid & ~supported).sum()),
        "oracle_max_error_mm": float(error.max()) if len(error) else 0.0,
        "observation_manifest_sha256": sha256(observations / f"{take}.json"),
        "observation_config": metadata["config"],
    }


def measure_split(design, observations, split):
    root = Path(design["root"])
    for record in design["records"]:
        if record["status"] == "scheduled" and record["split"] == split:
            yield measure_take(record, root, observations, design["sha256"])
