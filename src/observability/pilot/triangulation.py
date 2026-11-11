"""Two-view ray triangulation and marker-wrist validation for the decision pilot."""

import json
from pathlib import Path

import numpy as np

from observability.assets import local_output

from .calibration import parse_mcal, project_points, world_to_camera
from .metrics import response_curve, risk_coverage

CONFIDENCE_THRESHOLD = 0.25
PRIMARY_NAMES = ("left_wrist_midpoint", "right_wrist_midpoint")


def _world_ray(pixel, camera):
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("OpenCV is required for distortion inversion") from error
    point = np.asarray(pixel, dtype=np.float64).reshape(1, 1, 2)
    normalized = cv2.undistortPoints(
        point,
        np.asarray(camera["K"], dtype=np.float64),
        np.asarray(camera["distortion"], dtype=np.float64),
    ).reshape(2)
    direction_camera = np.array([normalized[0], normalized[1], 1.0])
    rotation, _ = world_to_camera(camera, "motive_y_up")
    direction_world = rotation.T @ direction_camera
    direction_world /= np.linalg.norm(direction_world)
    return np.asarray(camera["camera_position_mm"], dtype=float), direction_world


def triangulate_rays(origin_a, direction_a, origin_b, direction_b):
    """Return midpoint, ray gap, and intersection angle for two forward rays."""
    origin_a = np.asarray(origin_a, dtype=float)
    origin_b = np.asarray(origin_b, dtype=float)
    direction_a = np.asarray(direction_a, dtype=float)
    direction_b = np.asarray(direction_b, dtype=float)
    direction_a /= np.linalg.norm(direction_a)
    direction_b /= np.linalg.norm(direction_b)
    cosine = float(np.dot(direction_a, direction_b))
    denominator = 1.0 - cosine * cosine
    if denominator < 1e-8:
        return None
    difference = origin_a - origin_b
    d = float(np.dot(direction_a, difference))
    e = float(np.dot(direction_b, difference))
    distance_a = (cosine * e - d) / denominator
    distance_b = (e - cosine * d) / denominator
    if distance_a <= 0 or distance_b <= 0:
        return None
    point_a = origin_a + distance_a * direction_a
    point_b = origin_b + distance_b * direction_b
    angle = float(np.degrees(np.arccos(np.clip(abs(cosine), 0.0, 1.0))))
    return {
        "xyz_mm": (point_a + point_b) / 2.0,
        "ray_gap_mm": float(np.linalg.norm(point_a - point_b)),
        "ray_angle_deg": angle,
    }


def _rank_correlation(first, second):
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if len(first) < 3 or np.std(first) == 0 or np.std(second) == 0:
        return None
    first_rank = np.argsort(np.argsort(first, kind="stable"), kind="stable")
    second_rank = np.argsort(np.argsort(second, kind="stable"), kind="stable")
    return float(np.corrcoef(first_rank, second_rank)[0, 1])


def evaluate_triangulation(
    sample,
    detector_manifest,
    output=Path("local/pilot/triangulation.json"),
):
    """Evaluate two-view wrist estimates and change transfer against marker midpoints."""
    private_manifest = json.loads(Path("local/pilot/manifest-private.json").read_text())
    root = Path(private_manifest["root"])
    predictions = np.load(detector_manifest["arrays"])
    item_lookup = {
        (item["take_id"], item["camera_index"], item["frame"]): index
        for index, item in enumerate(detector_manifest["items"])
    }
    observations = []
    change_reference = []
    change_estimate = []
    change_reference_vectors = []
    change_estimate_vectors = []
    oracle_errors = []
    per_take = []
    for record in sample["records"]:
        if record["reference_source"] != "marker_constructed":
            continue
        reference = np.load(record["reference_path"])
        names = reference["names"].tolist()
        cameras = parse_mcal(root / record["calibration_path"])
        camera_a = cameras[record["cameras"][0]["camera_serial"]]
        camera_b = cameras[record["cameras"][1]["camera_serial"]]
        take_estimates = {name: [] for name in PRIMARY_NAMES}
        take_references = {name: [] for name in PRIMARY_NAMES}
        take_frames = {name: [] for name in PRIMARY_NAMES}
        take_errors = []
        take_observations = []
        take_reference_vectors = []
        take_estimate_vectors = []
        for local_index, frame in enumerate(reference["frames"]):
            prediction_a = item_lookup[
                (record["take_id"], record["cameras"][0]["camera_index"], int(frame))
            ]
            prediction_b = item_lookup[
                (record["take_id"], record["cameras"][1]["camera_index"], int(frame))
            ]
            for name in PRIMARY_NAMES:
                reference_index = names.index(name)
                coco_index = int(reference["coco17_indices"][reference_index])
                confidence_a = float(
                    predictions["coco17_confidence"][prediction_a, coco_index]
                )
                confidence_b = float(
                    predictions["coco17_confidence"][prediction_b, coco_index]
                )
                if (
                    not reference["valid"][local_index, reference_index]
                    or confidence_a < CONFIDENCE_THRESHOLD
                    or confidence_b < CONFIDENCE_THRESHOLD
                ):
                    continue
                pixel_a = predictions["coco17_xy_px"][prediction_a, coco_index]
                pixel_b = predictions["coco17_xy_px"][prediction_b, coco_index]
                ray_a = _world_ray(pixel_a, camera_a)
                ray_b = _world_ray(pixel_b, camera_b)
                estimate = triangulate_rays(*ray_a, *ray_b)
                if estimate is None:
                    continue
                truth = reference["xyz_mm"][local_index, reference_index]
                oracle_pixel_a = project_points(truth[None], camera_a)[0]
                oracle_pixel_b = project_points(truth[None], camera_b)[0]
                oracle = triangulate_rays(
                    *_world_ray(oracle_pixel_a, camera_a),
                    *_world_ray(oracle_pixel_b, camera_b),
                )
                if oracle is None:
                    raise ValueError("oracle rays do not intersect forward")
                oracle_errors.append(float(np.linalg.norm(oracle["xyz_mm"] - truth)))
                error = float(np.linalg.norm(estimate["xyz_mm"] - truth))
                take_errors.append(error)
                take_estimates[name].append(estimate["xyz_mm"])
                take_references[name].append(truth)
                take_frames[name].append(int(frame))
                observation = {
                    "take_id": record["take_id"],
                    "session_id": record["session_id"],
                    "frame": int(frame),
                    "endpoint": name,
                    "error_mm": error,
                    "ray_gap_mm": estimate["ray_gap_mm"],
                    "ray_angle_deg": estimate["ray_angle_deg"],
                    "minimum_confidence": min(confidence_a, confidence_b),
                }
                observations.append(observation)
                take_observations.append(observation)
        for name in PRIMARY_NAMES:
            estimates = np.asarray(take_estimates[name])
            references = np.asarray(take_references[name])
            frames = np.asarray(take_frames[name])
            if len(frames) < 2:
                continue
            consecutive = np.diff(frames) == 1
            reference_change = np.linalg.norm(np.diff(references, axis=0), axis=1)
            estimated_change = np.linalg.norm(np.diff(estimates, axis=0), axis=1)
            change_reference.extend(reference_change[consecutive].tolist())
            change_estimate.extend(estimated_change[consecutive].tolist())
            change_reference_vectors.extend(
                np.diff(references, axis=0)[consecutive].tolist()
            )
            change_estimate_vectors.extend(
                np.diff(estimates, axis=0)[consecutive].tolist()
            )
            take_reference_vectors.extend(
                np.diff(references, axis=0)[consecutive].tolist()
            )
            take_estimate_vectors.extend(
                np.diff(estimates, axis=0)[consecutive].tolist()
            )
        take_reference_vectors = np.asarray(take_reference_vectors)
        take_estimate_vectors = np.asarray(take_estimate_vectors)
        take_gain = None
        take_direction = None
        if len(take_reference_vectors):
            denominator = np.sum(take_reference_vectors * take_reference_vectors)
            if denominator > 0:
                take_gain = float(
                    np.sum(take_reference_vectors * take_estimate_vectors) / denominator
                )
            reference_norm = np.linalg.norm(take_reference_vectors, axis=1)
            estimate_norm = np.linalg.norm(take_estimate_vectors, axis=1)
            nonzero = (reference_norm > 1e-8) & (estimate_norm > 1e-8)
            if nonzero.any():
                cosine = np.sum(
                    take_reference_vectors[nonzero] * take_estimate_vectors[nonzero],
                    axis=1,
                ) / (reference_norm[nonzero] * estimate_norm[nonzero])
                take_direction = float(np.median(cosine))
        take_error_values = [row["error_mm"] for row in take_observations]
        take_gap_values = [row["ray_gap_mm"] for row in take_observations]
        take_confidence_values = [
            1.0 - row["minimum_confidence"] for row in take_observations
        ]
        per_take.append(
            {
                "take_id": record["take_id"],
                "session_id": record["session_id"],
                "observations": len(take_errors),
                "median_error_mm": (
                    float(np.median(take_errors)) if take_errors else None
                ),
                "p90_error_mm": (
                    float(np.percentile(take_errors, 90)) if take_errors else None
                ),
                "ray_gap_error_rank_correlation": _rank_correlation(
                    take_gap_values, take_error_values
                ),
                "low_confidence_error_rank_correlation": _rank_correlation(
                    take_confidence_values, take_error_values
                ),
                "change_vector_gain": take_gain,
                "change_direction_cosine_median": take_direction,
            }
        )

    errors = np.asarray([row["error_mm"] for row in observations])
    ray_gap = np.asarray([row["ray_gap_mm"] for row in observations])
    low_confidence = 1.0 - np.asarray(
        [row["minimum_confidence"] for row in observations]
    )
    gap_risk = risk_coverage(errors, ray_gap)
    confidence_risk = risk_coverage(errors, low_confidence)
    transfer = response_curve(change_reference, change_estimate)
    reference_vectors = np.asarray(change_reference_vectors)
    estimate_vectors = np.asarray(change_estimate_vectors)
    reference_norm = np.linalg.norm(reference_vectors, axis=1)
    estimate_norm = np.linalg.norm(estimate_vectors, axis=1)
    nonzero = (reference_norm > 1e-8) & (estimate_norm > 1e-8)
    direction_cosine = np.sum(
        reference_vectors[nonzero] * estimate_vectors[nonzero], axis=1
    ) / (reference_norm[nonzero] * estimate_norm[nonzero])
    vector_gain = float(
        np.sum(reference_vectors * estimate_vectors)
        / np.sum(reference_vectors * reference_vectors)
    )
    oracle_max = float(np.max(oracle_errors))
    if oracle_max > 1e-3:
        raise ValueError("projection/triangulation oracle round-trip failed")
    result = {
        "schema": "optitrack-two-view-wrist-pilot-v1",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "takes": len(per_take),
        "observations": len(observations),
        "median_error_mm": float(np.median(errors)),
        "p90_error_mm": float(np.percentile(errors, 90)),
        "take_median_error_mm": {
            "median": float(
                np.median(
                    [
                        row["median_error_mm"]
                        for row in per_take
                        if row["median_error_mm"]
                    ]
                )
            )
        },
        "ray_gap_error_rank_correlation": _rank_correlation(ray_gap, errors),
        "low_confidence_error_rank_correlation": _rank_correlation(
            low_confidence, errors
        ),
        "ray_gap_aurc": gap_risk["aurc"],
        "confidence_aurc": confidence_risk["aurc"],
        "ray_gap_aurc_over_mean_error": float(gap_risk["aurc"] / np.mean(errors)),
        "confidence_aurc_over_mean_error": float(
            confidence_risk["aurc"] / np.mean(errors)
        ),
        "change_transfer": transfer,
        "change_vector_gain": vector_gain,
        "change_direction_cosine_median": float(np.median(direction_cosine)),
        "oracle_roundtrip_max_mm": oracle_max,
        "per_take": per_take,
        "observations_private": observations,
        "qualifications": [
            "Two-view triangulation is a calibrated laboratory estimate, not bone truth.",
            "Wrist marker midpoints have their own placement and soft-tissue error.",
            "Frame-level observations are nested within six opaque capture groups.",
        ],
    }
    output = local_output(Path(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result
